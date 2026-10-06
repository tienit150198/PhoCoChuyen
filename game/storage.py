"""PostgreSQL persistence (see game/db.py) with atomic
commands, revision guards and idempotency.

Concurrency (see Store.command): the CPU-heavy part of a command (parse the save,
apply the reducer, validate, serialize) runs WITHOUT the database write lock. The
write lock is only taken for a short compare-and-set: the new save is stored only
if the save's revision is still the one the command was computed from, else the
command is computed again from the newer save (optimistic concurrency). Receipts,
the revision guard and "internal" commands behave exactly as with one big lock.

PostgreSQL: no global writer turn. A command's compare-and-set locks only its own
save (SELECT ... FOR UPDATE on the sessions row, then the revision check, in one
transaction), so different players never wait for each other and one player's
commands are serialized. Connections come from game.db.PgPool.
"""
from __future__ import annotations
import hashlib
import contextvars
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re
import secrets
import sys
import threading
import time
from pathlib import Path
from .engine import GameError,new_state,apply_action,public_state,validate_state,validate_career,migrate_state,needs_migration,tree_copy,stamped,BUILD
from .journey import enable_story
from . import archive as ar
from . import leaderboard as lb
from . import marriage as mr
from . import retention as rt
from . import kpi
from .content import CAREERS
from . import db as dbm
from . import fastjson as fj
from . import pg_schema
from . import settle_scope

SAVE_FORMATS=("mot-ngay-lam-nghe/save-v1","mot-ngay-lam-nghe/save-v2","mot-ngay-lam-nghe/save-v3","mot-ngay-lam-nghe/save-v4")
BUSY_MS=12000          # a write that must happen waits this long for the lock
QUICK_MS=250           # best-effort writes (timestamps) give up after this instead of queueing
OPTIMISTIC_TRIES=4     # then fall back to computing under the write lock
# A command on a save stamped with this build (engine.BUILD) re-validates only what it
# changed (see Store._compute and serialize); every FULL_EVERY-th revision validates all.
FULL_EVERY=max(1,int(os.environ.get("VALIDATE_FULL_EVERY","200") or 200))
# A moved career is re-validated without the pieces it did not change (game/settle_scope.py).
# SCOPED_CAREER_VALIDATION=0 validates every moved career in full again, as 1.7.15 did.
SCOPED_CAREERS=os.environ.get("SCOPED_CAREER_VALIDATION","1").strip().lower() not in ("0","false","no","off")
# HTTP keep-alive connections have their own thread budget. Only a few commands
# should hold parsed + serialized saves at once, before waiting for the PG pool.
# Share this budget across Store instances in one process, never across workers.
try:COMMAND_CONCURRENCY=max(1,min(64,int(os.environ.get("COMMAND_CONCURRENCY","4") or 4)))
except ValueError:COMMAND_CONCURRENCY=4
_COMMAND_GATE=threading.BoundedSemaphore(COMMAND_CONCURRENCY)
_COMMAND_POOL=ThreadPoolExecutor(max_workers=COMMAND_CONCURRENCY,thread_name_prefix="save-command")
_COMMAND_LOCAL=threading.local()


def _reset_command_gate():
    global _COMMAND_GATE,_COMMAND_POOL,_COMMAND_LOCAL
    _COMMAND_GATE=threading.BoundedSemaphore(COMMAND_CONCURRENCY)
    # No executor thread/lock from the parent may be reused after fork.
    _COMMAND_POOL=ThreadPoolExecutor(max_workers=COMMAND_CONCURRENCY,thread_name_prefix="save-command")
    _COMMAND_LOCAL=threading.local()


def _run_admitted(store,args):
    _COMMAND_LOCAL.active=True
    try:return store._admitted_command(*args)
    finally:_COMMAND_LOCAL.active=False


if hasattr(os,"register_at_fork"):
    os.register_at_fork(after_in_child=_reset_command_gate)

# A save that was created but never played can be stored as this marker instead of a
# ~90 KB fresh state; it becomes a real state at its first command (parse_state).
# Reading the marker is always supported; WRITING it needs LAZY_SAVES=1, to be turned
# on only once no older server version shares the database (they cannot parse it).
FRESH=""

class Conflict(GameError):
    pass

ARCHIVE_IMPORT_MAX=200000       # archive rows accepted with an imported backup
ARCHIVE_ROW_MAX=2*1024*1024     # characters of one archived row (album photos are the largest)

TRANSIENT=("accounting_view",)  # result parts only for the answer on the wire (Học kế toán's own view): not kept in receipts


def _receipt(result:dict)->str:
    """The stored receipt of a command: its result without the transient views (a replay answers without them;
    the client asks again, see public/js/v4/accounting-school.js)."""
    return fj.dumps({k:v for k,v in result.items() if k not in TRANSIENT} if any(k in result for k in TRANSIENT) else result)


def _archive_rows(box,careers_before:dict,raw:dict,default:str)->list:
    """(career, kind, day, row_json) for what the command cut off, oldest first per list.
    A row's owner is a career record (found by identity, in the save before or after
    the command), a career id, "" (the journey) or None (the acting career)."""
    if not box.rows:return []
    ids={id(c):cid for cid,c in careers_before.items()}
    if isinstance(raw.get("careers"),dict):ids.update({id(c):cid for cid,c in raw["careers"].items()})
    out=[]
    for owner,kind,row in box.rows:
        career=owner if isinstance(owner,str) else ids.get(id(owner),default) if owner is not None else default
        day=row.get("day") if isinstance(row,dict) else row[0] if isinstance(row,list) and row and type(row[0]) is int else None
        out.append((career or "",kind,day if type(day) is int else None,_dumps(row)))
    return out

SLOW_MS=float(os.environ.get("SLOW_COMMAND_MS","1500"))  # [slow-cmd] above this; [slow-lock]/[slow-write] above half
SLOW_LOG_PER_MINUTE=int(os.environ.get("SLOW_LOG_PER_MINUTE","20") or 0)  # per process; 0 = no cap
_slow_budget=[0.0,0,0]  # [minute started, lines written in it, lines dropped since the last one written]

def _slow_log(line:str)->None:
    """Write a [slow-*] line, at most SLOW_LOG_PER_MINUTE per process and minute: an overloaded
    server makes every command slow, and thousands of lines a minute only add to the load.
    The next line written counts the ones dropped."""
    b=_slow_budget;now=time.monotonic()
    if now-b[0]>=60:b[0]=now;b[1]=0
    if SLOW_LOG_PER_MINUTE>0 and b[1]>=SLOW_LOG_PER_MINUTE:
        b[2]+=1;return
    b[1]+=1;dropped=b[2];b[2]=0
    sys.stderr.write(line+(f" (+{dropped} slow lines dropped)" if dropped else "")+"\n")

def _slow(action,career,size,t0,t1,t2,t3,t4)->None:
    """Log the phases of a slow command (read, compute, store, public view), for tuning."""
    total=(t4-t0)*1000
    if total<SLOW_MS:return
    ms=lambda a,b:round((b-a)*1000)
    _slow_log(f"[slow-cmd] {total:.0f}ms {action} {career} save={size//1024}KB read={ms(t0,t1)} compute={ms(t1,t2)} store={ms(t2,t3)} view={ms(t3,t4)} pid={os.getpid()}")

def _write_archive(db,sid:str,rows:list)->None:
    """Append rows to each (career, kind) history of this save, inside the caller's transaction."""
    nxt={};pending=[]
    sql="INSERT INTO archive(sid,career,kind,seq,day,row) VALUES(?,?,?,?,?,?)"
    def flush():
        if len(pending)==1:db.execute(sql,pending[0])
        elif pending:db.executemany(sql,pending)
        pending.clear()
    for career,kind,day,row in rows:
        if kind.startswith(ar.FORGET):  # erased by the player: nothing of it is kept
            flush()  # preserve append/delete order, including a forget inside this batch
            kind=kind[len(ar.FORGET):];db.execute("DELETE FROM archive WHERE sid=? AND career=? AND kind=?",(sid,career,kind));nxt.pop((career,kind),None);continue
        k=(career,kind)
        if k not in nxt:
            nxt[k]=db.execute("SELECT COALESCE(MAX(seq)+1,0) FROM archive WHERE sid=? AND career=? AND kind=?",(sid,career,kind)).fetchone()[0]
        pending.append((sid,career,kind,nxt[k],day,row))
        nxt[k]+=1
        if len(pending)>=512:flush()
    flush()

def _imported_archive(rows)->list:
    """Archive rows of an imported backup (the "archive" of an export), checked."""
    if rows is None:return []
    if not isinstance(rows,list) or len(rows)>ARCHIVE_IMPORT_MAX:raise GameError("Phần lưu trữ của tệp không hợp lệ.","invalid_save")
    out=[]
    for r in sorted((r for r in rows if isinstance(r,dict)),key=lambda r:(str(r.get("career")),str(r.get("kind")),r.get("seq") if type(r.get("seq")) is int else 0)):
        career,kind,day=r.get("career"),r.get("kind"),r.get("day")
        if not (career=="" or career in CAREERS) or not isinstance(kind,str) or not 1<=len(kind)<=80 or "row" not in r:
            raise GameError("Phần lưu trữ của tệp không hợp lệ.","invalid_save")
        row=_dumps(r["row"])
        if len(row)>ARCHIVE_ROW_MAX:raise GameError("Phần lưu trữ của tệp quá lớn.","invalid_save")
        out.append((career,kind,day if type(day) is int else None,row))
    if len(out)!=len(rows):raise GameError("Phần lưu trữ của tệp không hợp lệ.","invalid_save")
    return out

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
    out=serialize_bytes(raw,known,full)
    return out if type(out) is str else out.decode('utf-8')


SaveText=dbm.Utf8Text  # a save's text as UTF-8 bytes, sent as a text parameter (game/db.py)
_SURROGATE=re.compile(rb"\xed[\xa0-\xbf]")  # a lone surrogate, written by 'surrogatepass'


def serialize_bytes(raw:dict,known:dict|None=None,full:bool=False,snap:dict|None=None)->SaveText|str:
    """serialize(), as SaveText: the same text, UTF-8. `snap` (game/settle_scope.py): pieces of
    careers before the command; a moved career is then validated with the pieces that did not
    change skipped. A text with a lone surrogate (it cannot be stored: psycopg refuses to encode
    it) comes back as the str serialize() always gave, so storing it fails exactly as before."""
    careers=raw.get("careers")
    if type(careers) is not dict or any(type(k) is not str for k in careers):
        raw.pop("check",None)
        return _dumps(raw)
    # orjson (game/fastjson.py, same bytes) writes the careers when a NaN/Infinity cannot slip
    # through as null: `full` (validate_state checked every number) or `known` (a career whose
    # text moved is validated below, finite numbers included; one whose text did not move is
    # the stored text). Otherwise json writes them and refuses NaN/Infinity (ValueError).
    # The stored text stays exactly json's: a career whose text is the stored one is json's
    # text already; any other goes through fj.canonical (a few float formats differ).
    fast=fj.FAST and (full or known is not None)
    pieces=[];digests={}
    for cid,c in careers.items():
        same=frozenset()
        if fast:
            out=fj.dumps_raw(c)
            d=hashlib.blake2b(out,digest_size=10).hexdigest()  # = _digest(the career's text)
            if known is None or known.get(cid)!=d:
                before=snap.get(cid) if snap and known is not None else None
                if before is not None:same=settle_scope.same(before,c)[0]  # what of the record did not change
                try:exact=fj.canonical(out,c)
                except ValueError:
                    validate_career(c,cid);raise  # NaN/Infinity
                if exact is not out:out,d=exact,hashlib.blake2b(exact,digest_size=10).hexdigest()
            # Keep compact UTF-8 until the final decode. A single emoji otherwise
            # expands every intermediate Python string to four bytes/character.
            # Copy the bytes to shed any spare capacity retained by the encoder.
            piece=memoryview(out).tobytes()
        else:
            try:piece=_dumps(c)
            except ValueError:
                validate_career(c,cid);raise  # NaN/Infinity: the same GameError as a full validation
            d=_digest(piece)
            piece=piece.encode()
        if known is not None and known.get(cid)!=d:
            if same:validate_career(c,cid,same=same)
            else:validate_career(c,cid)
        pieces.extend((_dumps(cid).encode(),b":",piece,b","));digests[cid]=d
    if known is not None or full:raw["check"]=dict(build=BUILD,careers=digests)
    else:raw.pop("check",None)
    if pieces:pieces.pop()
    body=[b"{"]
    for k,v in raw.items():
        body.extend((_dumps(k).encode('utf-8','surrogatepass'),b":"))
        if k=="careers":body.extend((b"{",*pieces,b"}"))
        else:body.append(_dumps(v).encode('utf-8','surrogatepass'))
        body.append(b",")
    if len(body)>1:body.pop()
    body.append(b"}")
    out=SaveText(b"".join(body))
    if b"\xed" in out and _SURROGATE.search(out):return out.decode('utf-8','surrogatepass')
    return out


def _places(raw:dict):
    """work_visits.places of a computed save (see Store._store); None if it fails, so the commit
    computes it under the lock as before and fails, or not, exactly as before."""
    from . import work_visits
    try:return work_visits.places(raw)
    except Exception:  # noqa: BLE001 - the commit hook raises it again, in its usual place
        return None


def _snapshot_row(r):
    """The command's snapshot row (fetched with text_bytes: the save's text and the receipt stay
    UTF-8 bytes, both parsed by fastjson) with the request hash as text again."""
    if r is None:return None
    rhash=r["rhash"]
    return dict(revision=r["revision"],state=r["state"],rhash=rhash.decode() if isinstance(rhash,bytes) else rhash,rresult=r["rresult"],
                acct=bool(r["acct"]) if "acct" in r.keys() else False)


def _commit_before(raw:dict)->dict:
    """Detached inputs read by transaction hooks, captured before the reducer mutates.

    Keep this projection in step with rentals/home_guests/accounts.command_commit
    and player_service_tasks.transitions. No inventory, history or NPC task payload
    is needed by those hooks. The CAS revision proves this is the locked row's state.
    """
    j=raw.get('journey') or {}
    own=(j.get('home') or {}).get('own')
    careers={}
    for cid,c in (raw.get('careers') or {}).items():
        tasks=[dict(id=t.get('id'),career=t.get('career'),status=t.get('status'),
                    player_order=dict(id=t['player_order']['id']))
               for t in c.get('tasks',[]) if t.get('player_order')]
        jobs=[dict(id=r.get('id'),status=r.get('status')) for r in c.get('player_service_jobs',[])]
        if tasks or jobs:careers[cid]=dict(tasks=tasks,player_service_jobs=jobs)
    visitors=[dict(id=r.get('id'),status=r.get('status'))
              for st in (j.get('quay') or {}).get('stalls',[])
              for r in st.get('business',{}).get('visitor_orders',[])]
    return dict(name=raw.get('name'),careers=careers,journey=dict(story=j.get('story'),
        life_day=j.get('life_day',0),home=dict(own={k:own.get(k) for k in ('id','kind')} if isinstance(own,dict) else None),
        quay=dict(stalls=[dict(business=dict(visitor_orders=visitors))])))

class Store:
    def __init__(self,path:Path|str,story:bool=False):
        # This path names the test schema and process locks; it never holds data.
        self.path=str(path)
        # Real servers run the story; dev sweeps keep every workplace open.
        self.story=story
        self.pg=dbm.pool_for(self.path)
        self.backend="pg"
        db=self.pg.connect()
        try:pg_schema.ensure(db)
        finally:db.close()
        mr.bind(self)

    def connect(self):
        return self.pg.connect()

    def close_pool(self)->None:
        """Close idle connections before forking workers or finishing tests."""
        self.pg.clear()

    def transaction(self,fn,best_effort_ms:int|None=None):
        """BEGIN, fn(db), COMMIT. Best-effort writes use a short row-lock timeout
        and return None on a database timeout instead of failing the request."""
        db=self.connect()
        try:
            db.begin()
            if best_effort_ms is not None:db.set_local("lock_timeout",f"{max(1,int(best_effort_ms))}ms")
            out=fn(db)
            db.commit()
            return out
        except dbm.OperationalError:
            db.rollback()
            if best_effort_ms is None:raise
            return None
        except BaseException:
            db.rollback();raise
        finally:
            db.close()

    @staticmethod
    def digest(token:str)->str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _resolve(db,h:str)->tuple[str,str|None]:
        row=db.execute("SELECT (SELECT sid FROM logins WHERE token=?) AS lsid,(SELECT csrf FROM logins WHERE token=?) AS lcsrf,"
                       "EXISTS(SELECT 1 FROM accounts WHERE sid=?) AS owned",(h,h,h)).fetchone()
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
        if text==FRESH or text==b"":  # the text may come as UTF-8 bytes (Store._command)
            state=new_state()
            if self.story:enable_story(state,int(hashlib.sha256(("seed:"+sid).encode()).hexdigest()[:8],16)%2**31)
            return state
        return fj.loads(text)

    def session(self,token:str|None=None)->tuple[str,str,bool]:
        if token and isinstance(token,str) and len(token)==64:
            h=self.digest(token)
            with self.connect() as db:
                sid,login_csrf=self._resolve(db,h)
                row=db.execute("SELECT csrf FROM sessions WHERE sid=?",(sid,)).fetchone()
                stale=bool(login_csrf and row and db.execute(f"SELECT seen_at<{dbm.UTC_INTERVAL_TEXT} FROM logins WHERE token=?",("-1 hour",h)).fetchone()[0])
            if row:
                # "Last seen" of a signed-in device: hourly and best-effort, never a reason to fail.
                if stale:self.transaction(lambda db:db.execute("UPDATE logins SET seen_at=CURRENT_TIMESTAMP WHERE token=?",(h,)),QUICK_MS)
                return token,login_csrf or row["csrf"],False
        token=secrets.token_hex(32);csrf=secrets.token_hex(24);sid=self.digest(token)
        # LAZY_SAVES=1: the save itself is created at the first command (FRESH), so a visit
        # that never plays costs ~200 bytes, not ~90 KB.
        lazy=os.environ.get("LAZY_SAVES","0").strip().lower() in ("1","true","yes","on")
        text=FRESH if lazy else fj.dumps(self.parse_state(FRESH,sid))
        with self.connect() as db:
            db.execute("INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)",(sid,csrf,text))
            rt.write_marks(db,sid,[("created",None,None)],1)  # Giữ chân: the first step of the funnel, same transaction
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
            before=dict(state["careers"]) if isinstance(state.get("careers"),dict) else {}
            with ar.collect() as box:
                migrated=migrate_state(state,owned=True)
            validate_state(migrated)
            text=serialize(migrated,None,True);cut=_archive_rows(box,before,migrated,"")
            def write(db):
                if not db.execute("UPDATE sessions SET state=?,revision=? WHERE sid=? AND revision=?",(text,revision+1,sid,revision)).rowcount:return False
                _write_archive(db,sid,cut);return True
            if self.transaction(write):
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
        args=(token,request_id,expected,career,action,payload,internal)
        if getattr(_COMMAND_LOCAL,"active",False):
            return self._admitted_command(*args)  # nested internal work owns a slot already
        with _COMMAND_GATE:
            # Reuse allocation arenas as well as limiting active saves. A semaphore
            # alone lets every keep-alive thread retain its own large JSON buffers.
            return _COMMAND_POOL.submit(contextvars.copy_context().run,_run_admitted,self,args).result()

    def _admitted_command(self,token,request_id,expected,career,action,payload,internal):
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100 or "\x00" in request_id:raise GameError("Mã thao tác không hợp lệ.")
        if not (internal and expected is None) and type(expected) is not int:raise GameError("Thiếu phiên bản tiến trình.")
        if not isinstance(action,str) or not isinstance(payload,dict):raise GameError("Thao tác không hợp lệ.")
        fingerprint=hashlib.sha256(json.dumps([career,action,payload],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        h=self.digest(token)
        who=[None]  # the save id once resolved: rt.count() of a rejected command
        try:
            out=self._command(h,who,request_id,expected,career,action,payload,internal,fingerprint)
        except GameError as e:
            kpi.econ_drop()
            if who[0] and not internal and e.code!="session_missing":rt.count(self,who[0],career,action,e)
            raise
        except BaseException:
            kpi.econ_drop();raise
        if out.get("replayed"):kpi.econ_drop()
        else:kpi.econ_commit(self)  # 📊 xu created/destroyed by this command: a dict update, written every 30 s
        if not internal and not out.get("replayed"):rt.count(self,who[0],career,action)  # Giữ chân: a dict update, written every few seconds
        return out

    def _command(self,h:str,who:list,request_id:str,expected,career,action:str,payload:dict,internal:bool,fingerprint:str)->dict:
        if action == 'jr_deco_skin':
            from . import home_decor
            return home_decor.command(self,h,who,request_id,expected,career,action,payload,internal,fingerprint)
        t0=time.perf_counter()
        for _ in range(OPTIMISTIC_TRIES):
            # 1. A consistent snapshot of the save and of this request's receipt, without any lock.
            with self.connect() as db:
                sid,_=self._resolve(db,h)
                row=_snapshot_row(db.execute("SELECT s.revision AS revision,s.state AS state,r.request_hash AS rhash,r.result AS rresult,"
                               "EXISTS(SELECT 1 FROM accounts a WHERE a.sid=s.sid) AS acct FROM sessions s "
                               "LEFT JOIN receipts r ON r.sid=s.sid AND r.request_id=? WHERE s.sid=?",(request_id,sid),text_bytes=True).fetchone())
            if not row:raise GameError("Phiên chơi không tồn tại.","session_missing")
            who[0]=sid
            if row["rhash"] is not None:return self._replay(sid,row,fingerprint)
            if expected is not None and row["revision"]!=expected:raise Conflict("Tiến trình đã thay đổi ở tab khác. Đã đồng bộ lại; hãy xem trạng thái trước khi thao tác tiếp.","revision_conflict")
            # 2. The heavy part, lock-free.
            t1=time.perf_counter()
            before_out=[]
            try:
                raw,result,serialized,cut,board,steps=self._compute(sid,row["state"],career,action,tree_copy(payload),internal,row["revision"],before_out=before_out)
            except GameError:
                if self._moved(sid,request_id,row["revision"]):continue  # judged on a save that has moved on: look again
                raise
            receipt=_receipt(result)
            # The save's part of the work-visit snapshots (an account's places), before the lock.
            projected=_places(raw) if row["acct"] else None
            # 3. Short compare-and-set under the write lock.
            t2=time.perf_counter()
            if self._store(sid,row["revision"],serialized,request_id,fingerprint,receipt,cut,board,steps,action=action,career=career,result=result,after=raw,before=before_out[0],projected=projected):
                t3=time.perf_counter()
                lb.remember(sid,row["revision"]+1,board[0])
                if steps[0]:rt.emit_marks(sid,*steps)
                view=public_state(raw,migrated=True)
                _slow(action,career,len(row["state"] or ""),t0,t1,t2,t3,time.perf_counter())
                return dict(state=view,revision=row["revision"]+1,result=result,replayed=False)
        with self.connect() as db:
            sid,_=self._resolve(db,h)
        who[0]=sid
        return self._command_locked(sid,request_id,expected,career,action,payload,internal,fingerprint)

    def _replay(self,sid:str,row,fingerprint:str)->dict:
        if row["rhash"]!=fingerprint:raise Conflict("Mã thao tác đã dùng cho nội dung khác.","idempotency_conflict")
        # A freshly parsed save is private: migrated in place, not copied whole first (public_state(state) would).
        state=migrate_state(self.parse_state(row["state"],sid),owned=True)
        return dict(state=public_state(state,migrated=True),revision=row["revision"],result=fj.loads(row["rresult"]),replayed=True)

    def _compute(self,sid:str,text:str,career,action:str,payload:dict,internal:bool,revision:int,*,before_out:list|None=None)->tuple[dict,dict,str,list,tuple,tuple]:
        """(new save, result, its text, archive rows, board, steps): what the command cut off from the
        save's lists, to be written in the same transaction as the save (see game/archive.py),
        board = (the save's leaderboard rows, whether a number on a board moved) (game/leaderboard.py)
        and steps = ([(milestone, career, detail)], life day): the funnel steps this command crossed
        (game/retention.py: a dozen counters read from the save before and after, no extra parse)."""
        raw=self.parse_state(text,sid)
        if before_out is not None:before_out.append(_commit_before(raw))
        before=dict(raw["careers"]) if isinstance(raw.get("careers"),dict) else {}
        hit=lb.recall(sid,revision)
        ranked=hit if hit is not None else lb.summary(raw)  # read before the reducer changes raw in place
        marked=rt.marks(raw,ranked) if rt.ENABLED and action!="import_save" else None  # likewise
        x0=kpi.xu(raw) if action not in kpi.ECON_SKIP else None  # likewise: the xu held before (a few dict reads)
        with ar.collect() as box:
            raw,result,full,known,extra,snap=self._apply(raw,text,career,action,payload,internal,revision)
        kpi.econ_mark(action,x0,kpi.xu(raw) if x0 is not None else None)
        serialized=serialize_bytes(raw,known,full,snap)
        del snap
        if type(serialized) is str:
            if len(serialized)>3*1024*1024 and len(serialized.encode())>14*1024*1024:raise GameError("Bản lưu quá lớn. Xóa bớt ảnh trong album trước khi nhập.")
        elif len(serialized)>14*1024*1024:raise GameError("Bản lưu quá lớn. Xóa bớt ảnh trong album trước khi nhập.")  # bytes: the same limit
        ranks=lb.summary(raw)
        steps=(rt.reached(marked,rt.marks(raw,ranks)),rt.life_day(raw)) if marked else ((),None)
        # An imported backup's own archive is older than anything its migration moved out.
        return raw,result,serialized,extra+_archive_rows(box,before,raw,career if career in CAREERS else ""),(ranks,ranks!=ranked or (hit is None and lb.heal(ranks))),steps

    def _apply(self,raw:dict,text:str,career,action:str,payload:dict,internal:bool,revision:int):
        extra=[]
        if action=="import_save" and not internal:
            envelope=payload.get("save")
            if not isinstance(envelope,dict) or envelope.get("format") not in SAVE_FORMATS:raise GameError("Không phải tệp lưu của Phố Có Chuyện.","invalid_save")
            candidate=envelope.get("state")
            if isinstance(candidate,dict):candidate.pop("check",None)  # an import is always migrated and fully validated
            try:
                candidate=migrate_state(candidate)
                from .player_service_tasks import scrub_import
                scrub_import(candidate)
                validate_state(candidate)
                # An imported backup joins the story at its own progress; it cannot switch the story off.
                if self.story and not candidate["journey"]["story"]:enable_story(candidate);validate_state(candidate)
            except GameError:raise
            except (TypeError,ValueError,KeyError,AttributeError,RecursionError) as exc:
                raise GameError("Cấu trúc tệp lưu không hợp lệ.","invalid_save") from exc
            imported=_imported_archive(envelope.get("archive"))
            # The replaced save is not lost: it goes to the archive whole, before the backup's own archive.
            ar.record([raw],"replaced_save",ar.JOURNEY)
            extra=imported
            # Recoverable UI-only state is not accepted as a full backup.
            raw=candidate;known,full=None,True
            result=dict(message="Đã khôi phục bản lưu. Tiến trình trước đó được thay thế sau khi kiểm tra thành công.")
        else:
            # A save stamped by this build passed all its checks when stored: the reducer then checks
            # only what lies outside the careers, and _serialize checks each career the command
            # changed (its digest moved). Every FULL_EVERY-th revision checks everything.
            checked=raw["check"].get("careers") if stamped(raw) and not needs_migration(raw) else None
            if type(checked) is not dict:checked=None
            known=checked if (revision+1)%FULL_EVERY else None
            # The careers settlement may touch, cut into pieces before the reducer changes them:
            # serialize then re-validates only the pieces a moved career changed (game/settle_scope.py).
            snap=settle_scope.snapshot(raw,known,career) if known is not None and SCOPED_CAREERS else None
            # A periodic audit still starts from a save this build validated.
            # Keep intermediate checks scoped, then audit ALL final careers once
            # below, outside apply_action's scope, before serialization/commit.
            raw,result=apply_action(raw,career,action,payload,internal=internal,owned=True,scoped=checked is not None)
            full=False
            if known is None:
                if checked is not None:
                    validate_state(raw);full=True
                    return raw,result,full,known,extra,None
                # First command of this build on the save, a fresh save or the periodic check: stamp it
                # only if it passes every check (the action itself may not have validated anything).
                try:validate_state(raw);full=True
                except GameError:pass
            return raw,result,full,known,extra,snap
        return raw,result,full,known,extra,None

    def _moved(self,sid:str,request_id:str,revision:int)->bool:
        with self.connect() as db:
            row=db.execute("SELECT revision FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:return False
            return row["revision"]!=revision or bool(db.execute("SELECT 1 FROM receipts WHERE sid=? AND request_id=?",(sid,request_id)).fetchone())

    def _store(self,sid:str,revision:int,serialized:str,request_id:str,fingerprint:str,receipt:str,cut:list=(),board:tuple|None=None,steps:tuple=((),None),action:str='',career=None,result=None,after=None,before=None,projected=None)->bool:
        """Compare-and-set: write the new save, its archive rows, its leaderboard rows, its receipt and the
        funnel steps it crossed (game/retention.py) only if the save is still at `revision`.
        `projected`: work_visits.places(after), computed before the lock (None: computed inside)."""
        tw=time.perf_counter()
        tx=time.perf_counter()
        db=None
        try:
            db=self.connect()
            db.begin();self._patient(db)
            # Lock this save's row only, then check the revision.
            fields='revision,state' if action and before is None else 'revision'
            row=db.execute(f"SELECT {fields} FROM sessions WHERE sid=? FOR UPDATE",(sid,)).fetchone()
            tl=time.perf_counter()
            if (tl-tw)*1000>=SLOW_MS/2:_slow_log(f"[slow-lock] waited {(tl-tw)*1000:.0f}ms for this save's row lock (connection {(tx-tw)*1000:.0f}ms) pid={os.getpid()}")
            tx=tl
            if not row or row[0]!=revision:
                db.rollback();return False
            if action:
                from . import work_visits
                if before is None:before=self.parse_state(row['state'],sid)
                current=after if after is not None else self.parse_state(serialized,sid)
                from . import rentals
                rentals.command_commit(db,sid,before,current,action)
                work_visits.command_commit(db,sid,before,current,career,action,result or {},projected=projected if after is not None else None)
            if db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=? AND revision=?",
                          (serialized,revision+1,sid,revision)).rowcount!=1:
                db.rollback();return False
            if action:
                from . import home_guests
                home_guests.command_commit(db,sid,before,current,action)
            if action == 'settings':
                from . import accounts
                accounts.sync_character_name(db,sid,before,current)
            _write_archive(db,sid,cut)
            if board and board[1]:lb.write(db,sid,board[0])  # only when a number on a board moved
            if steps[0]:rt.write_marks(db,sid,steps[0],steps[1])  # rare: only when a funnel step was crossed
            db.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)",(sid,request_id,fingerprint,receipt))
            from .home_decor import notify
            notify(db,sid,action)
            db.commit()
            te=(time.perf_counter()-tx)*1000
            if te>=SLOW_MS/2:_slow_log(f"[slow-write] {te:.0f}ms to write {len(serialized)//1024}KB + {len(cut)} archive rows pid={os.getpid()}")
            return True
        except dbm.IntegrityError:  # the same request id landed first: the caller replays it
            db.rollback();return False
        except BaseException:
            if db is not None:db.rollback()
            raise
        finally:
            if db is not None:db.close()

    def _patient(self,db)->None:
        """Give commands a longer row-lock timeout than best-effort writes.
        Commands on one save serialize on that row; other saves remain free."""
        cfg=self.pg.settings
        lock=max(BUSY_MS,int(cfg.get("lock_timeout") or 0))
        stmt=int(cfg.get("statement_timeout") or 0)
        stmt=stmt if stmt==0 or stmt>=lock+5000 else lock+5000  # the lock wait counts toward it
        db.raw.execute("SELECT set_config('lock_timeout',%s,true),set_config('statement_timeout',%s,true)",(f"{lock}ms",f"{stmt}ms"))

    def _command_locked(self,sid:str,request_id:str,expected,career,action:str,payload:dict,internal:bool,fingerprint:str)->dict:
        """The save keeps changing under us (a burst of writes to this one save):
        compute under the write lock, like before optimistic commands."""
        db=None
        try:
            db=self.connect()
            db.begin();self._patient(db)
            row=_snapshot_row(db.execute("SELECT s.revision AS revision,s.state AS state,r.request_hash AS rhash,r.result AS rresult FROM sessions s "
                           "LEFT JOIN receipts r ON r.sid=s.sid AND r.request_id=? WHERE s.sid=?"+dbm.for_update(db,"s"),(request_id,sid),text_bytes=True).fetchone())
            if not row:raise GameError("Phiên chơi không tồn tại.","session_missing")
            if row["rhash"] is not None:
                db.rollback();return self._replay(sid,row,fingerprint)
            if expected is not None and row["revision"]!=expected:raise Conflict("Tiến trình đã thay đổi ở tab khác. Đã đồng bộ lại; hãy xem trạng thái trước khi thao tác tiếp.","revision_conflict")
            before_out=[]
            raw,result,serialized,cut,board,steps=self._compute(sid,row["state"],career,action,payload,internal,row["revision"],before_out=before_out)
            revision=row["revision"]+1
            from . import work_visits
            before=before_out[0]
            from . import rentals
            rentals.command_commit(db,sid,before,raw,action)
            work_visits.command_commit(db,sid,before,raw,career,action,result)
            db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?",(serialized,revision,sid))
            from . import home_guests
            home_guests.command_commit(db,sid,before,raw,action)
            if action == 'settings':
                from . import accounts
                accounts.sync_character_name(db,sid,before,raw)
            _write_archive(db,sid,cut)
            if board[1]:lb.write(db,sid,board[0])
            if steps[0]:rt.write_marks(db,sid,steps[0],steps[1])
            db.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)",(sid,request_id,fingerprint,_receipt(result)))
            from .home_decor import notify
            notify(db,sid,action)
            db.commit()
            lb.remember(sid,revision,board[0])
            if steps[0]:rt.emit_marks(sid,*steps)
            return dict(state=public_state(raw,migrated=True),revision=revision,result=result,replayed=False)
        except Exception:
            if db is not None:db.rollback()
            raise
        finally:
            if db is not None:db.close()

    def delete(self,token:str)->bool:
        """Erase a player's save and receipts (privacy request / "Xóa dữ liệu"),
        plus the account and every device signed in to it."""
        sid=self.key(token)
        with self.connect() as db:
            # A command in flight finishes before its archive/receipt rows are erased.
            db.begin();db.execute("SELECT 1 FROM sessions WHERE sid=? FOR UPDATE",(sid,))
            from . import rentals
            rentals.forget(db,sid)
            from .work_visits import forget
            forget(db,sid)
            from . import home_guests
            home_guests.forget(db,sid)
            db.execute("DELETE FROM archive WHERE sid=?",(sid,))
            db.execute("DELETE FROM receipts WHERE sid=?",(sid,))
            lb.forget(db,[sid])
            db.execute("DELETE FROM logins WHERE sid=?",(sid,))
            db.execute("DELETE FROM tiktok_flows WHERE source_sid=? OR target_uid IN (SELECT uid FROM accounts WHERE sid=?)",(sid,sid))
            db.execute("DELETE FROM tiktok_identities WHERE sid=?",(sid,))
            db.execute("DELETE FROM accounts WHERE sid=?",(sid,))
            rt.forget(db,sid)  # stat rows are kept (anonymous once the save is gone)
            n=db.execute("DELETE FROM sessions WHERE sid=?",(sid,)).rowcount
        return bool(n)

    def _batches(self,table:str,where:str,args:tuple,batch:int=500,pause:float=.02)->int:
        """Delete matching rows in short transactions, using PostgreSQL ctid."""
        total=0
        while True:
            def step(db):
                return db.execute(f"DELETE FROM {table} WHERE ctid = ANY(ARRAY(SELECT ctid FROM {table} WHERE {where} LIMIT {int(batch)}))",args).rowcount
            n=self.transaction(step)
            total+=n
            if n<batch:return total
            time.sleep(pause)

    def prune(self,idle_days:int=180,receipt_days:int=3)->dict:
        """Drop idempotency receipts after a few days and anonymous saves idle for
        months. Account saves are kept; only their idle device logins expire."""
        age=(f"-{int(idle_days)} days",)
        r=self._batches("receipts",f"created_at<{dbm.UTC_INTERVAL_TEXT}",(f"-{int(receipt_days)} days",))
        with self.connect() as db:
            idle=f"updated_at<{dbm.UTC_INTERVAL_TEXT} AND sid NOT IN (SELECT sid FROM accounts)"
            stale=[row["sid"] for row in db.execute(f"SELECT sid FROM sessions WHERE {idle}",age)]
        n=0
        for i in range(0,len(stale),50):
            part=stale[i:i+50]
            def drop(db):
                marks=",".join("?"*len(part))
                gone=[r[0] for r in db.execute(f"SELECT sid FROM sessions WHERE sid IN ({marks}) AND {idle}"+dbm.for_update(db),(*part,*age))]
                if not gone:return 0
                marks2=",".join("?"*len(gone))
                db.execute(f"DELETE FROM archive WHERE sid IN ({marks2})",gone)
                db.execute(f"DELETE FROM receipts WHERE sid IN ({marks2})",gone)
                lb.forget(db,gone)
                return db.execute(f"DELETE FROM sessions WHERE sid IN ({marks2})",gone).rowcount
            n+=self.transaction(drop)
        with self.connect() as db:
            db.execute(f"DELETE FROM logins WHERE seen_at<{dbm.UTC_INTERVAL_TEXT} OR sid NOT IN (SELECT sid FROM sessions)",age)
        return dict(receipts=r,sessions=n)

    def prune_receipts(self,days:float=2,keep:int=200)->int:
        """Idempotency receipts only need to outlive a client's retries: keep the
        last `keep` per save and nothing older than `days`."""
        n=self._batches("receipts",f"created_at<{dbm.UTC_INTERVAL_TEXT}",(f"-{int(days*24*60)} minutes",))
        with self.connect() as db:
            heavy=[r[0] for r in db.execute("SELECT sid FROM receipts GROUP BY sid HAVING COUNT(*)>?",(int(keep),))]
        # Newest first; request_id breaks ties within one timestamp second.
        newest="SELECT request_id FROM receipts WHERE sid=? ORDER BY created_at DESC,request_id DESC LIMIT ?"
        for sid in heavy:
            n+=self.transaction(lambda db:db.execute(f"DELETE FROM receipts WHERE sid=? AND request_id NOT IN ({newest})",
                                                      (sid,sid,int(keep))).rowcount)
        return n

    def prune_guests(self,days:float=3,batch:int=50)->int:
        """Abandoned guest saves: no account, no signed-in device, no public name,
        never really played (revision <= 1 and no progress in the save) and idle for
        `days`. Deleted with their receipts, a small batch per transaction."""
        from .accounts import has_progress
        cond=f"revision<=1 AND updated_at<{dbm.UTC_INTERVAL_TEXT} AND NOT (sid IN (SELECT sid FROM accounts) OR sid IN (SELECT sid FROM logins) OR sid IN (SELECT sid FROM profiles WHERE name IS NOT NULL))"
        age=f"-{int(days*24*60)} minutes"
        deleted,last=0,""
        while True:
            with self.connect() as db:
                rows=db.execute(f"SELECT sid,state FROM sessions WHERE sid>? AND {cond} ORDER BY sid LIMIT ?",(last,age,int(batch))).fetchall()
            if not rows:return deleted
            last=rows[-1]["sid"]
            doomed=[]
            for r in rows:
                try:
                    if r["state"]==FRESH or not has_progress(fj.loads(r["state"])):doomed.append(r["sid"])
                except (ValueError,TypeError,AttributeError):
                    continue  # unreadable: leave it for a human
            if doomed:
                def drop(db):
                    n=0
                    for sid in doomed:  # re-checked under the lock: it may have been played meanwhile
                        if not db.execute(f"SELECT 1 FROM sessions WHERE sid=? AND {cond}"+dbm.for_update(db),(sid,age)).fetchone():continue
                        db.execute("DELETE FROM archive WHERE sid=?",(sid,))
                        db.execute("DELETE FROM receipts WHERE sid=?",(sid,))
                        lb.forget(db,[sid])
                        n+=db.execute("DELETE FROM sessions WHERE sid=?",(sid,)).rowcount
                    return n
                deleted+=self.transaction(drop)
                time.sleep(.02)

    def archive_export(self,token:str)->list:
        """Every archived row of this save, for the backup download (see /api/save/export)."""
        sid=self.key(token)
        with self.connect() as db:
            return [dict(career=r["career"],kind=r["kind"],seq=r["seq"],day=r["day"],row=fj.loads(r["row"]))
                    for r in db.execute("SELECT career,kind,seq,day,row FROM archive WHERE sid=? ORDER BY career,kind,seq",(sid,))]

    def archive_page(self,token:str,career:str,kind:str,before:int|None=None,skip:int=0,limit:int=50)->dict:
        """One page of a (career, kind) history, newest first: the archived rows, then (for
        the kinds in archive.IN_SAVE) the rows still in the save. Positions count from the
        oldest row (0) and never change, so `before` (the smallest position of the previous
        page) pages back; the first page can instead `skip` the newest rows already shown."""
        if not (career=="" or career in CAREERS):raise GameError("Nghề không hợp lệ.")
        if not isinstance(kind,str) or not 1<=len(kind)<=80:raise GameError("Loại sổ không hợp lệ.")
        limit=max(1,min(int(limit),200));skip=max(0,int(skip))
        # Only the kinds whose newest rows live in the save need the save itself.
        live=(ar.in_save(self.read(token)[0],career,kind) or []) if kind in ar.IN_SAVE else []
        sid=self.key(token)
        with self.connect() as db:
            stored=db.execute("SELECT COALESCE(MAX(seq)+1,0) FROM archive WHERE sid=? AND career=? AND kind=?",(sid,career,kind)).fetchone()[0]
            total=stored+len(live)
            end=min(total,max(0,before)) if before is not None else max(0,total-skip)
            start=max(0,end-limit)
            rows=[dict(pos=r["seq"],day=r["day"],row=fj.loads(r["row"])) for r in
                  db.execute("SELECT seq,day,row FROM archive WHERE sid=? AND career=? AND kind=? AND seq>=? AND seq<? ORDER BY seq",(sid,career,kind,start,min(end,stored)))]
        for pos in range(max(start,stored),end):
            row=live[pos-stored];day=row.get("day") if isinstance(row,dict) else None
            rows.append(dict(pos=pos,day=day if type(day) is int else None,row=row))
        rows.reverse()
        return dict(career=career,kind=kind,total=total,rows=rows,before=start if start>0 else None)

    def archive_tail(self,token:str,career:str,kind:str,before:int|None=None,limit:int=30)->dict:
        """The newest archived rows of a (career, kind) history whose position is below `before`
        (all when None), newest first, without reading the save: {rows: [{pos, day, row}], before}
        where `before` continues the paging (None: nothing older). Used by /api/board."""
        if not (career=="" or career in CAREERS):raise GameError("Nghề không hợp lệ.")
        limit=max(1,min(int(limit),100));sid=self.key(token)
        with self.connect() as db:
            end=db.execute("SELECT COALESCE(MAX(seq)+1,0) FROM archive WHERE sid=? AND career=? AND kind=?",(sid,career,kind)).fetchone()[0]
            if before is not None:end=min(end,max(0,int(before)))
            start=max(0,end-limit)
            rows=[dict(pos=r["seq"],day=r["day"],row=json.loads(r["row"])) for r in
                  db.execute("SELECT seq,day,row FROM archive WHERE sid=? AND career=? AND kind=? AND seq>=? AND seq<? ORDER BY seq DESC",(sid,career,kind,start,end))]
        return dict(rows=rows,before=start if start>0 else None)
