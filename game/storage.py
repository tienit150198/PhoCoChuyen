"""SQLite persistence with atomic commands, revision guards and idempotency.

Concurrency (see Store.command): the CPU-heavy part of a command (parse the save,
apply the reducer, validate, serialize) runs WITHOUT the database write lock. The
write lock is only taken for a short compare-and-set: the new save is stored only
if the save's revision is still the one the command was computed from, else the
command is computed again from the newer save (optimistic concurrency). Receipts,
the revision guard and "internal" commands behave exactly as with one big lock.

Connections are pooled per Store (opening one costs ~1 ms: schema parsing and
PRAGMAs), and never carried across os.fork() (see _Pool).
"""
from __future__ import annotations
import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
try:import fcntl
except ImportError:fcntl=None  # Windows: one process, the thread lock is enough
from .engine import GameError,new_state,apply_action,public_state,validate_state,validate_career,migrate_state,needs_migration,tree_copy,stamped,BUILD
from .journey import enable_story

SCHEMA=4
SAVE_FORMATS=("mot-ngay-lam-nghe/save-v1","mot-ngay-lam-nghe/save-v2","mot-ngay-lam-nghe/save-v3","mot-ngay-lam-nghe/save-v4")
BUSY_MS=12000          # a write that must happen waits this long for the lock
QUICK_MS=250           # best-effort writes (timestamps) give up after this instead of queueing
OPTIMISTIC_TRIES=4     # then fall back to computing under the write lock
# A command on a save stamped with this build (engine.BUILD) re-validates only what it
# changed (see Store._compute and serialize); every FULL_EVERY-th revision validates all.
FULL_EVERY=max(1,int(os.environ.get("VALIDATE_FULL_EVERY","50") or 50))
# A save that was created but never played can be stored as this marker instead of a
# ~90 KB fresh state; it becomes a real state at its first command (parse_state).
# Reading the marker is always supported; WRITING it needs LAZY_SAVES=1, to be turned
# on only once no older server version shares the database (they cannot parse it).
FRESH=""
PRAGMAS=("PRAGMA foreign_keys=ON",f"PRAGMA busy_timeout={BUSY_MS}",
         "PRAGMA synchronous=NORMAL",       # safe with WAL: no fsync per commit, only at checkpoints
         "PRAGMA temp_store=MEMORY","PRAGMA cache_size=-4000",
         "PRAGMA mmap_size=268435456","PRAGMA journal_size_limit=67108864")

class Conflict(GameError):
    pass

def _digest(text:str)->str:
    return hashlib.blake2b(text.encode(),digest_size=10).hexdigest()

SEPARATORS=(",",":")  # compact: ~10% fewer bytes to store, read and parse than ", " / ": "

def _dumps(v)->str:
    return json.dumps(v,ensure_ascii=False,allow_nan=False,separators=SEPARATORS)

def serialize(raw:dict,known:dict|None=None,full:bool=False)->str:
    """The save as stored: exactly json.dumps(raw, ensure_ascii=False, separators=
    SEPARATORS), with each career serialized on its own so that its digest can be
    kept in raw["check"].

    `known`: career digests of the stored save the command started from, when that
    save is stamped by this build. A career whose digest moved was changed by the
    command and is validated here (validate_career raises GameError); the others are
    byte for byte what already passed. `full`: raw passed validate_state in full.
    With either, the save is stamped (build + digests); otherwise the stamp is dropped."""
    careers=raw.get("careers")
    if type(careers) is not dict or any(type(k) is not str for k in careers):
        raw.pop("check",None)
        return _dumps(raw)
    pieces=[];digests={}
    for cid,c in careers.items():
        try:piece=_dumps(c)
        except ValueError:
            validate_career(c,cid);raise  # NaN/Infinity: the same GameError as a full validation
        d=_digest(piece)
        if known is not None and known.get(cid)!=d:validate_career(c,cid)
        pieces.append(_dumps(cid)+":"+piece);digests[cid]=d
    if known is not None or full:raw["check"]=dict(build=BUILD,careers=digests)
    else:raw.pop("check",None)
    return "{"+",".join(_dumps(k)+":"+("{"+",".join(pieces)+"}" if k=="careers" else _dumps(v)) for k,v in raw.items())+"}"

_ORPHANS:list=[]  # connections inherited across fork(): never used, never closed in the child

class _Pool:
    """Idle connections of one Store. A connection is used by one thread at a time."""
    def __init__(self,size:int):
        self.size=size;self.idle=[];self.lock=threading.Lock();self.pid=os.getpid()

    def take(self):
        with self.lock:
            if self.pid!=os.getpid():  # forked: the parent's connections are not ours
                _ORPHANS.extend(self.idle);self.idle=[];self.pid=os.getpid()
            return self.idle.pop() if self.idle else None

    def give(self,db)->bool:
        if self.pid!=os.getpid() or db._pid!=self.pid:return False
        try:
            if db.in_transaction:db.rollback()  # like close(): an uncommitted transaction is discarded
            if db.row_factory is not sqlite3.Row:db.row_factory=sqlite3.Row
        except sqlite3.Error:return False
        with self.lock:
            if len(self.idle)>=self.size:return False
            self.idle.append(db);return True

    def clear(self):
        with self.lock:
            idle,self.idle=self.idle,[]
        for db in idle:
            try:sqlite3.Connection.close(db)
            except sqlite3.Error:pass

class ClosingConnection(sqlite3.Connection):
    """sqlite's context manager commits but does not close; close after both.
    close() hands a pooled connection back to its Store instead of closing it."""
    _pool=None
    _pid=None
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

    def close(self):
        pool=self._pool
        if pool is not None and pool.give(self):return
        if self._pid not in (None,os.getpid()):  # inherited across fork: leave it alone
            _ORPHANS.append(self);return
        super().close()

class Store:
    def __init__(self,path:Path|str,story:bool=False):
        self.path=str(path)
        # Real servers run the story (careers unlock along one journey). Tests and
        # dev sweeps keep every workplace open (see server.py / MNL_DEV).
        self.story=story
        self._pool=_Pool(max(0,int(os.environ.get("DB_POOL","12") or 12)))
        # Writers of this process queue here (woken as soon as the lock is free) instead
        # of all polling SQLite's busy handler, which sleeps up to 100 ms between tries
        # and lets newcomers overtake: under load that starved some writes for seconds.
        # Worker processes (WORKERS>1) queue the same way on an flock() of a file next
        # to the database, opened per process (a descriptor inherited across fork would
        # be shared, and flock would not tell the workers apart).
        self._wlock=threading.RLock();self._depth=0;self._lockfd=None;self._lockpid=None
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
              sid TEXT PRIMARY KEY, csrf TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
              state TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS receipts (
              sid TEXT NOT NULL, request_id TEXT NOT NULL, request_hash TEXT NOT NULL,
              result TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(sid,request_id), FOREIGN KEY(sid) REFERENCES sessions(sid)
            );
            -- Optional accounts (additive, v0.5+): an account owns one save (sessions.sid).
            -- Each signed-in device holds its own random token + CSRF in `logins`, mapped to that save.
            CREATE TABLE IF NOT EXISTS accounts (
              uid INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, display TEXT NOT NULL,
              pw TEXT NOT NULL, sid TEXT UNIQUE NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS logins (
              token TEXT PRIMARY KEY, sid TEXT NOT NULL, csrf TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS logins_sid ON logins(sid);
            -- Player feedback ("Góp ý", game/player_feedback.py): private notes to the operator.
            CREATE TABLE IF NOT EXISTS player_feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT NOT NULL, account TEXT,
              kind TEXT NOT NULL, text TEXT NOT NULL, context TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'new', reply TEXT,
              created_at REAL NOT NULL, updated_at REAL NOT NULL, replied_at REAL
            );
            CREATE INDEX IF NOT EXISTS player_feedback_sid ON player_feedback(sid, id);
            CREATE INDEX IF NOT EXISTS player_feedback_status ON player_feedback(status, id);
            """)

    def connect(self):
        db=self._pool.take()
        if db is None:
            db=sqlite3.connect(self.path,timeout=BUSY_MS/1000,factory=ClosingConnection,check_same_thread=False)
            db.row_factory=sqlite3.Row
            for pragma in PRAGMAS:db.execute(pragma)
            db._pool,db._pid=self._pool,os.getpid()
        return db

    def close_pool(self)->None:
        """Close idle connections (the server calls this before forking workers)."""
        self._pool.clear()

    def writing(self,wait_ms:int=BUSY_MS)->bool:
        """Take the writer turn (threads of this process, then processes sharing the
        database); False after `wait_ms`. Release with done_writing()."""
        deadline=time.monotonic()+wait_ms/1000
        if not self._wlock.acquire(timeout=wait_ms/1000):return False
        if self._depth==0 and fcntl is not None:
            try:
                if self._lockpid!=os.getpid():
                    self._lockfd=os.open(self.path+"-writer.lock",os.O_RDWR|os.O_CREAT,0o644);self._lockpid=os.getpid()
                while True:
                    try:fcntl.flock(self._lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        if time.monotonic()>=deadline:self._wlock.release();return False
                        time.sleep(.002)
            except OSError:
                pass  # no lock file (read-only directory...): SQLite's own lock still protects the data
        self._depth+=1
        return True

    def done_writing(self)->None:
        self._depth-=1
        if self._depth==0 and fcntl is not None and self._lockfd is not None and self._lockpid==os.getpid():
            try:fcntl.flock(self._lockfd,fcntl.LOCK_UN)
            except OSError:pass
        self._wlock.release()

    def transaction(self,fn,best_effort_ms:int|None=None):
        """Run fn(db) inside BEGIN IMMEDIATE and commit. With `best_effort_ms`, wait at
        most that long for the write lock and return None instead of failing: for
        timestamps and other writes no request should ever fail (or queue) for."""
        if not self.writing(BUSY_MS if best_effort_ms is None else best_effort_ms):
            if best_effort_ms is None:raise sqlite3.OperationalError("database is locked")
            return None
        try:return self._transaction(fn,best_effort_ms)
        finally:self.done_writing()

    def _transaction(self,fn,best_effort_ms:int|None):
        db=self.connect()
        try:
            if best_effort_ms is not None:db.execute(f"PRAGMA busy_timeout={int(best_effort_ms)}")
            try:
                db.execute("BEGIN IMMEDIATE")
                out=fn(db)
                db.commit()
                return out
            except sqlite3.OperationalError:
                db.rollback()
                if best_effort_ms is None:raise
                return None
            except BaseException:
                db.rollback();raise
        finally:
            if best_effort_ms is not None:
                try:db.execute(f"PRAGMA busy_timeout={BUSY_MS}")
                except sqlite3.Error:pass
            db.close()

    @staticmethod
    def digest(token:str)->str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _resolve(db,h:str)->tuple[str,str|None]:
        row=db.execute("SELECT (SELECT sid FROM logins WHERE token=?1) AS lsid,(SELECT csrf FROM logins WHERE token=?1) AS lcsrf,"
                       "EXISTS(SELECT 1 FROM accounts WHERE sid=?1) AS owned",(h,)).fetchone()
        if row["lsid"]:return row["lsid"],row["lcsrf"]
        if row["owned"]:return "revoked:"+h,None
        return h,None

    def resolve(self,token:str)->tuple[str,str|None]:
        """Save id (sid) behind a cookie token, plus the device's own CSRF when
        the token is an account login. An anonymous token maps to its own hash.
        A save that now belongs to an account is only reachable through a login
        row, so the pre-registration cookie stops working once rotated."""
        with self.connect() as db:
            return self._resolve(db,self.digest(token))

    def key(self,token:str)->str:
        return self.resolve(token)[0]

    def parse_state(self,text:str,sid:str)->dict:
        """The stored save as a (private) dict. A never-played save (FRESH) is
        rebuilt the same way every time: the story seed comes from its sid."""
        if text==FRESH:
            state=new_state()
            if self.story:enable_story(state,int(hashlib.sha256(("seed:"+sid).encode()).hexdigest()[:8],16)%2**31)
            return state
        return json.loads(text)

    def session(self,token:str|None=None)->tuple[str,str,bool]:
        if token and isinstance(token,str) and len(token)==64:
            h=self.digest(token)
            with self.connect() as db:
                sid,login_csrf=self._resolve(db,h)
                row=db.execute("SELECT csrf FROM sessions WHERE sid=?",(sid,)).fetchone()
                stale=bool(login_csrf and row and db.execute("SELECT seen_at<datetime('now','-1 hour') FROM logins WHERE token=?",(h,)).fetchone()[0])
            if row:
                # "Last seen" of a signed-in device: hourly and best-effort, never a reason to fail.
                if stale:self.transaction(lambda db:db.execute("UPDATE logins SET seen_at=CURRENT_TIMESTAMP WHERE token=?",(h,)),QUICK_MS)
                return token,login_csrf or row["csrf"],False
        token=secrets.token_hex(32);csrf=secrets.token_hex(24);sid=self.digest(token)
        # LAZY_SAVES=1: the save itself is created at the first command (FRESH), so a visit
        # that never plays costs ~200 bytes, not ~90 KB.
        lazy=os.environ.get("LAZY_SAVES","0").strip().lower() in ("1","true","yes","on")
        text=FRESH if lazy else json.dumps(self.parse_state(FRESH,sid),ensure_ascii=False)
        with self.connect() as db:
            db.execute("INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)",(sid,csrf,text))
        return token,csrf,True

    def csrf(self,token:str)->str:
        """Only the CSRF of a session (no save parsing): enough to guard a command."""
        with self.connect() as db:
            sid,login_csrf=self._resolve(db,self.digest(token))
            row=db.execute("SELECT csrf FROM sessions WHERE sid=?",(sid,)).fetchone()
        if not row:raise GameError("Phiên chơi không còn tồn tại. Tải lại trang nhé.","session_missing")
        return login_csrf or row["csrf"]

    def read(self,token:str)->tuple[dict,int,str]:
        with self.connect() as db:
            sid,login_csrf=self._resolve(db,self.digest(token))
            row=db.execute("SELECT csrf,revision,state FROM sessions WHERE sid=?",(sid,)).fetchone()
        if not row:raise GameError("Phiên chơi không còn tồn tại. Tải lại trang nhé.","session_missing")
        csrf=login_csrf or row["csrf"]
        state=self.parse_state(row["state"],sid)
        revision=row["revision"]
        for _ in range(OPTIMISTIC_TRIES):
            if not needs_migration(state):return state,revision,csrf
            # Migrate outside the write lock; store it only if nobody changed the save meanwhile.
            migrated=migrate_state(state,owned=True);validate_state(migrated)
            text=serialize(migrated,None,True)
            if self.transaction(lambda db:db.execute("UPDATE sessions SET state=?,revision=? WHERE sid=? AND revision=?",(text,revision+1,sid,revision)).rowcount):
                return migrated,revision+1,csrf
            with self.connect() as db:
                row=db.execute("SELECT revision,state FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:raise GameError("Phiên chơi không còn tồn tại. Tải lại trang nhé.","session_missing")
            state,revision=self.parse_state(row["state"],sid),row["revision"]
        return state,revision,csrf

    def command(self,token:str,request_id:str,expected:int|None,career:str|None,action:str,payload:dict,internal:bool=False)->dict:
        """Apply one action atomically. `internal` commands come from the server
        itself (AI reviewer answers); they skip the revision guard because the
        reducer checks their own preconditions."""
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:raise GameError("Mã thao tác không hợp lệ.")
        if not (internal and expected is None) and type(expected) is not int:raise GameError("Thiếu phiên bản tiến trình.")
        if not isinstance(action,str) or not isinstance(payload,dict):raise GameError("Thao tác không hợp lệ.")
        fingerprint=hashlib.sha256(json.dumps([career,action,payload],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        h=self.digest(token)
        for _ in range(OPTIMISTIC_TRIES):
            # 1. A consistent snapshot of the save and of this request's receipt, without any lock.
            with self.connect() as db:
                sid,_=self._resolve(db,h)
                row=db.execute("SELECT s.revision AS revision,s.state AS state,r.request_hash AS rhash,r.result AS rresult FROM sessions s "
                               "LEFT JOIN receipts r ON r.sid=s.sid AND r.request_id=? WHERE s.sid=?",(request_id,sid)).fetchone()
            if not row:raise GameError("Phiên chơi không tồn tại.","session_missing")
            if row["rhash"] is not None:return self._replay(sid,row,fingerprint)
            if expected is not None and row["revision"]!=expected:raise Conflict("Tiến trình đã thay đổi ở tab khác. Đã đồng bộ lại; hãy xem trạng thái trước khi thao tác tiếp.","revision_conflict")
            # 2. The heavy part, lock-free.
            try:
                raw,result,serialized=self._compute(sid,row["state"],career,action,tree_copy(payload),internal,row["revision"])
            except GameError:
                if self._moved(sid,request_id,row["revision"]):continue  # judged on a save that has moved on: look again
                raise
            receipt=json.dumps(result,ensure_ascii=False)
            # 3. Short compare-and-set under the write lock.
            if self._store(sid,row["revision"],serialized,request_id,fingerprint,receipt):
                return dict(state=public_state(raw,migrated=True),revision=row["revision"]+1,result=result,replayed=False)
        return self._command_locked(sid,request_id,expected,career,action,payload,internal,fingerprint)

    def _replay(self,sid:str,row,fingerprint:str)->dict:
        if row["rhash"]!=fingerprint:raise Conflict("Mã thao tác đã dùng cho nội dung khác.","idempotency_conflict")
        return dict(state=public_state(self.parse_state(row["state"],sid)),revision=row["revision"],result=json.loads(row["rresult"]),replayed=True)

    def _compute(self,sid:str,text:str,career,action:str,payload:dict,internal:bool,revision:int)->tuple[dict,dict,str]:
        raw=self.parse_state(text,sid)
        if action=="import_save" and not internal:
            envelope=payload.get("save")
            if not isinstance(envelope,dict) or envelope.get("format") not in SAVE_FORMATS:raise GameError("Không phải tệp lưu của Phố Có Chuyện.","invalid_save")
            candidate=envelope.get("state")
            if isinstance(candidate,dict):candidate.pop("check",None)  # an import is always migrated and fully validated
            try:
                candidate=migrate_state(candidate);validate_state(candidate)
                # An imported backup joins the story at its own progress; it cannot switch the story off.
                if self.story and not candidate["journey"]["story"]:enable_story(candidate);validate_state(candidate)
            except GameError:raise
            except (TypeError,ValueError,KeyError,AttributeError,RecursionError) as exc:
                raise GameError("Cấu trúc tệp lưu không hợp lệ.","invalid_save") from exc
            # Recoverable UI-only state is not accepted as a full backup.
            raw=candidate;known,full=None,True
            result=dict(message="Đã khôi phục bản lưu. Tiến trình trước đó được thay thế sau khi kiểm tra thành công.")
        else:
            # A save stamped by this build passed all its checks when stored: the reducer then checks
            # only what lies outside the careers, and _serialize checks each career the command
            # changed (its digest moved). Every FULL_EVERY-th revision checks everything.
            known=raw["check"].get("careers") if stamped(raw) and (revision+1)%FULL_EVERY and not needs_migration(raw) else None
            if type(known) is not dict:known=None
            raw,result=apply_action(raw,career,action,payload,internal=internal,owned=True,scoped=known is not None)
            full=False
            if known is None:
                # First command of this build on the save, a fresh save or the periodic check: stamp it
                # only if it passes every check (the action itself may not have validated anything).
                try:validate_state(raw);full=True
                except GameError:pass
        serialized=serialize(raw,known,full)
        if len(serialized)>3*1024*1024 and len(serialized.encode())>14*1024*1024:raise GameError("Bản lưu quá lớn. Xóa bớt ảnh trong album trước khi nhập.")
        return raw,result,serialized

    def _moved(self,sid:str,request_id:str,revision:int)->bool:
        with self.connect() as db:
            row=db.execute("SELECT revision FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:return False
            return row["revision"]!=revision or bool(db.execute("SELECT 1 FROM receipts WHERE sid=? AND request_id=?",(sid,request_id)).fetchone())

    def _store(self,sid:str,revision:int,serialized:str,request_id:str,fingerprint:str,receipt:str)->bool:
        """Compare-and-set: write the new save and its receipt only if the save is still at `revision`."""
        if not self.writing():raise sqlite3.OperationalError("database is locked")
        db=self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=? AND revision=?",
                          (serialized,revision+1,sid,revision)).rowcount!=1:
                db.rollback();return False
            db.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)",(sid,request_id,fingerprint,receipt))
            db.commit();return True
        except sqlite3.IntegrityError:  # the same request id landed first: the caller replays it
            db.rollback();return False
        except BaseException:
            db.rollback();raise
        finally:
            db.close();self.done_writing()

    def _command_locked(self,sid:str,request_id:str,expected,career,action:str,payload:dict,internal:bool,fingerprint:str)->dict:
        """The save keeps changing under us (a burst of writes to this one save):
        compute under the write lock, like before optimistic commands."""
        if not self.writing():raise sqlite3.OperationalError("database is locked")
        db=self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT s.revision AS revision,s.state AS state,r.request_hash AS rhash,r.result AS rresult FROM sessions s "
                           "LEFT JOIN receipts r ON r.sid=s.sid AND r.request_id=? WHERE s.sid=?",(request_id,sid)).fetchone()
            if not row:raise GameError("Phiên chơi không tồn tại.","session_missing")
            if row["rhash"] is not None:
                db.rollback();return self._replay(sid,row,fingerprint)
            if expected is not None and row["revision"]!=expected:raise Conflict("Tiến trình đã thay đổi ở tab khác. Đã đồng bộ lại; hãy xem trạng thái trước khi thao tác tiếp.","revision_conflict")
            raw,result,serialized=self._compute(sid,row["state"],career,action,payload,internal,row["revision"])
            revision=row["revision"]+1
            db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?",(serialized,revision,sid))
            db.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)",(sid,request_id,fingerprint,json.dumps(result,ensure_ascii=False)))
            db.commit()
            return dict(state=public_state(raw,migrated=True),revision=revision,result=result,replayed=False)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close();self.done_writing()

    def delete(self,token:str)->bool:
        """Erase a player's save and receipts (privacy request / "Xóa dữ liệu"),
        plus the account and every device signed in to it."""
        sid=self.key(token)
        with self.connect() as db:
            db.execute("DELETE FROM receipts WHERE sid=?",(sid,))
            db.execute("DELETE FROM logins WHERE sid=?",(sid,))
            db.execute("DELETE FROM accounts WHERE sid=?",(sid,))
            n=db.execute("DELETE FROM sessions WHERE sid=?",(sid,)).rowcount
        return bool(n)

    def _batches(self,select_sql:str,args:tuple,delete_sql:str,batch:int=500,pause:float=.02)->int:
        """Delete rows (by rowid) in small transactions so the write lock is held briefly."""
        total=0
        while True:
            def step(db):
                ids=[r[0] for r in db.execute(select_sql+f" LIMIT {int(batch)}",args)]
                for i in range(0,len(ids),200):
                    part=ids[i:i+200]
                    db.execute(delete_sql%",".join("?"*len(part)),part)
                return len(ids)
            n=self.transaction(step)
            total+=n
            if n<batch:return total
            time.sleep(pause)

    def prune(self,idle_days:int=180,receipt_days:int=3)->dict:
        """Drop idempotency receipts after a few days and anonymous saves idle for
        months. Account saves are kept; only their idle device logins expire."""
        age=(f"-{int(idle_days)} days",)
        r=self._batches("SELECT rowid FROM receipts WHERE created_at<datetime('now',?)",(f"-{int(receipt_days)} days",),"DELETE FROM receipts WHERE rowid IN (%s)")
        with self.connect() as db:
            idle="updated_at<datetime('now',?) AND sid NOT IN (SELECT sid FROM accounts)"
            stale=[row["sid"] for row in db.execute(f"SELECT sid FROM sessions WHERE {idle}",age)]
        n=0
        for i in range(0,len(stale),50):
            part=stale[i:i+50]
            def drop(db):
                marks=",".join("?"*len(part))
                db.execute(f"DELETE FROM receipts WHERE sid IN ({marks})",part)
                return db.execute(f"DELETE FROM sessions WHERE sid IN ({marks}) AND {idle}",(*part,*age)).rowcount
            n+=self.transaction(drop)
        with self.connect() as db:
            db.execute("DELETE FROM logins WHERE seen_at<datetime('now',?) OR sid NOT IN (SELECT sid FROM sessions)",age)
        return dict(receipts=r,sessions=n)

    def prune_receipts(self,days:float=2,keep:int=200)->int:
        """Idempotency receipts only need to outlive a client's retries: keep the
        last `keep` per save and nothing older than `days`."""
        n=self._batches("SELECT rowid FROM receipts WHERE created_at<datetime('now',?)",(f"-{int(days*24*60)} minutes",),"DELETE FROM receipts WHERE rowid IN (%s)")
        with self.connect() as db:
            heavy=[r[0] for r in db.execute("SELECT sid FROM receipts GROUP BY sid HAVING COUNT(*)>?",(int(keep),))]
        for sid in heavy:
            n+=self.transaction(lambda db:db.execute("DELETE FROM receipts WHERE sid=? AND rowid NOT IN (SELECT rowid FROM receipts WHERE sid=? ORDER BY rowid DESC LIMIT ?)",
                                                      (sid,sid,int(keep))).rowcount)
        return n

    def prune_guests(self,days:float=3,batch:int=50)->int:
        """Abandoned guest saves: no account, no signed-in device, no public name,
        never really played (revision <= 1 and no progress in the save) and idle for
        `days`. Deleted with their receipts, a small batch per transaction."""
        from .accounts import has_progress
        with self.connect() as db:
            named="OR sid IN (SELECT sid FROM profiles WHERE name IS NOT NULL)" if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='profiles'").fetchone() else ""
        cond=(f"revision<=1 AND updated_at<datetime('now',?) AND NOT (sid IN (SELECT sid FROM accounts) OR sid IN (SELECT sid FROM logins) {named})")
        age=f"-{int(days*24*60)} minutes"
        deleted,last=0,0
        while True:
            with self.connect() as db:
                rows=db.execute(f"SELECT rowid,sid,state FROM sessions WHERE rowid>? AND {cond} ORDER BY rowid LIMIT ?",(last,age,int(batch))).fetchall()
            if not rows:return deleted
            last=rows[-1]["rowid"]
            doomed=[]
            for r in rows:
                try:
                    if r["state"]==FRESH or not has_progress(json.loads(r["state"])):doomed.append(r["sid"])
                except (ValueError,TypeError,AttributeError):
                    continue  # unreadable: leave it for a human
            if doomed:
                def drop(db):
                    n=0
                    for sid in doomed:  # re-checked under the lock: it may have been played meanwhile
                        if not db.execute(f"SELECT 1 FROM sessions WHERE sid=? AND {cond}",(sid,age)).fetchone():continue
                        db.execute("DELETE FROM receipts WHERE sid=?",(sid,))
                        n+=db.execute("DELETE FROM sessions WHERE sid=?",(sid,)).rowcount
                    return n
                deleted+=self.transaction(drop)
                time.sleep(.02)

    def checkpoint(self)->None:
        """PASSIVE WAL checkpoint: never waits for readers or writers."""
        with self.connect() as db:
            db.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchall()
