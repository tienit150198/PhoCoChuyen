"""SQLite persistence with atomic commands, revision guards and idempotency."""
from __future__ import annotations
import hashlib
import json
import secrets
import sqlite3
from pathlib import Path
from .engine import GameError,new_state,apply_action,public_state,validate_state,migrate_state,needs_migration
from .journey import enable_story

SCHEMA=4
SAVE_FORMATS=("mot-ngay-lam-nghe/save-v1","mot-ngay-lam-nghe/save-v2","mot-ngay-lam-nghe/save-v3","mot-ngay-lam-nghe/save-v4")

class Conflict(GameError):
    pass

class ClosingConnection(sqlite3.Connection):
    """sqlite's context manager commits but does not close; close after both."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()

class Store:
    def __init__(self,path:Path|str,story:bool=False):
        self.path=str(path)
        # Real servers run the story (careers unlock along one journey). Tests and
        # dev sweeps keep every workplace open (see server.py / MNL_DEV).
        self.story=story
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
        db=sqlite3.connect(self.path,timeout=12,factory=ClosingConnection)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=12000")
        return db

    @staticmethod
    def digest(token:str)->str:
        return hashlib.sha256(token.encode()).hexdigest()

    def resolve(self,token:str)->tuple[str,str|None]:
        """Save id (sid) behind a cookie token, plus the device's own CSRF when
        the token is an account login. An anonymous token maps to its own hash.
        A save that now belongs to an account is only reachable through a login
        row, so the pre-registration cookie stops working once rotated."""
        h=self.digest(token)
        with self.connect() as db:
            row=db.execute("SELECT (SELECT sid FROM logins WHERE token=?1) AS lsid,(SELECT csrf FROM logins WHERE token=?1) AS lcsrf,"
                           "EXISTS(SELECT 1 FROM accounts WHERE sid=?1) AS owned",(h,)).fetchone()
        if row["lsid"]:return row["lsid"],row["lcsrf"]
        if row["owned"]:return "revoked:"+h,None
        return h,None

    def key(self,token:str)->str:
        return self.resolve(token)[0]

    def session(self,token:str|None=None)->tuple[str,str,bool]:
        if token and isinstance(token,str) and len(token)==64:
            sid,login_csrf=self.resolve(token)
            with self.connect() as db:
                row=db.execute("SELECT csrf FROM sessions WHERE sid=?",(sid,)).fetchone()
                if row:
                    if login_csrf:db.execute("UPDATE logins SET seen_at=CURRENT_TIMESTAMP WHERE token=?",(self.digest(token),))
                    return token,login_csrf or row["csrf"],False
        token=secrets.token_hex(32);csrf=secrets.token_hex(24)
        state=new_state()
        if self.story:enable_story(state,secrets.randbelow(2**31))
        with self.connect() as db:
            db.execute("INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)",(self.digest(token),csrf,json.dumps(state,ensure_ascii=False)))
        return token,csrf,True

    def read(self,token:str)->tuple[dict,int,str]:
        sid,login_csrf=self.resolve(token)
        with self.connect() as db:
            row=db.execute("SELECT * FROM sessions WHERE sid=?",(sid,)).fetchone()
        if not row:raise GameError("Phiên chơi không còn tồn tại. Tải lại trang nhé.","session_missing")
        csrf=login_csrf or row["csrf"]
        state=json.loads(row["state"])
        if needs_migration(state):
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row=db.execute("SELECT * FROM sessions WHERE sid=?",(sid,)).fetchone()
                state=migrate_state(json.loads(row["state"]));validate_state(state)
                # Increment only if this connection actually migrated it.
                changed=needs_migration(json.loads(row["state"]))
                revision=row["revision"]+int(changed)
                if changed:db.execute("UPDATE sessions SET state=?,revision=? WHERE sid=?",(json.dumps(state,ensure_ascii=False),revision,sid))
                db.commit()
                return state,revision,csrf
        return state,row["revision"],csrf

    def command(self,token:str,request_id:str,expected:int|None,career:str|None,action:str,payload:dict,internal:bool=False)->dict:
        """Apply one action atomically. `internal` commands come from the server
        itself (AI reviewer answers); they skip the revision guard because the
        reducer checks their own preconditions."""
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:raise GameError("Mã thao tác không hợp lệ.")
        if not (internal and expected is None) and type(expected) is not int:raise GameError("Thiếu phiên bản tiến trình.")
        if not isinstance(action,str) or not isinstance(payload,dict):raise GameError("Thao tác không hợp lệ.")
        fingerprint=hashlib.sha256(json.dumps([career,action,payload],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        sid=self.key(token)
        db=self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:raise GameError("Phiên chơi không tồn tại.","session_missing")
            previous=db.execute("SELECT * FROM receipts WHERE sid=? AND request_id=?",(sid,request_id)).fetchone()
            if previous:
                if previous["request_hash"]!=fingerprint:raise Conflict("Mã thao tác đã dùng cho nội dung khác.","idempotency_conflict")
                return dict(state=public_state(json.loads(row["state"])),revision=row["revision"],result=json.loads(previous["result"]),replayed=True)
            if expected is not None and row["revision"]!=expected:raise Conflict("Tiến trình đã thay đổi ở tab khác. Đã đồng bộ lại; hãy xem trạng thái trước khi thao tác tiếp.","revision_conflict")
            raw=json.loads(row["state"])
            if action=="import_save" and not internal:
                envelope=payload.get("save")
                if not isinstance(envelope,dict) or envelope.get("format") not in SAVE_FORMATS:raise GameError("Không phải tệp lưu của Phố Có Chuyện.","invalid_save")
                candidate=envelope.get("state")
                try:
                    candidate=migrate_state(candidate);validate_state(candidate)
                    # An imported backup joins the story at its own progress; it cannot switch the story off.
                    if self.story and not candidate["journey"]["story"]:enable_story(candidate);validate_state(candidate)
                except GameError:raise
                except (TypeError,ValueError,KeyError,AttributeError,RecursionError) as exc:
                    raise GameError("Cấu trúc tệp lưu không hợp lệ.","invalid_save") from exc
                # Recoverable UI-only state is not accepted as a full backup.
                raw=candidate
                result=dict(message="Đã khôi phục bản lưu. Tiến trình trước đó được thay thế sau khi kiểm tra thành công.")
            else:
                raw,result=apply_action(raw,career,action,payload,internal=internal)
            serialized=json.dumps(raw,ensure_ascii=False,allow_nan=False)
            if len(serialized.encode())>14*1024*1024:raise GameError("Bản lưu quá lớn. Xóa bớt ảnh trong album trước khi nhập.")
            revision=row["revision"]+1
            db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?",(serialized,revision,sid))
            db.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)",(sid,request_id,fingerprint,json.dumps(result,ensure_ascii=False)))
            db.commit()
            return dict(state=public_state(raw),revision=revision,result=result,replayed=False)
        except Exception:
            db.rollback()
            raise
        finally:db.close()

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

    def prune(self,idle_days:int=180,receipt_days:int=3)->dict:
        """Drop idempotency receipts after a few days and anonymous saves idle for
        months. Account saves are kept; only their idle device logins expire."""
        age=(f"-{int(idle_days)} days",)
        with self.connect() as db:
            r=db.execute("DELETE FROM receipts WHERE created_at<datetime('now',?)",(f"-{int(receipt_days)} days",)).rowcount
            idle="updated_at<datetime('now',?) AND sid NOT IN (SELECT sid FROM accounts)"
            stale=[row["sid"] for row in db.execute(f"SELECT sid FROM sessions WHERE {idle}",age)]
            for sid in stale:db.execute("DELETE FROM receipts WHERE sid=?",(sid,))
            n=db.execute(f"DELETE FROM sessions WHERE {idle}",age).rowcount
            db.execute("DELETE FROM logins WHERE seen_at<datetime('now',?) OR sid NOT IN (SELECT sid FROM sessions)",age)
        return dict(receipts=r,sessions=n)
