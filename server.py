#!/usr/bin/env python3
"""Game server: Python 3.10+, standard library only.

Launch locally: python server.py --open
Public: put it behind an HTTPS reverse proxy, set ALLOWED_HOSTS=<domain> and
TRUST_PROXY=1 (see docs/DEPLOY.md). Static assets are restricted to public/.
Runtime state is never served as files; secrets stay in the server environment.
"""
from __future__ import annotations
import argparse
from collections import defaultdict,deque
import gzip
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import sys
import threading
import traceback
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import unquote,urlsplit,parse_qs
import webbrowser

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/"public"

def load_env():
    env=ROOT/".env"
    if not env.exists():return
    for line in env.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line:continue
        key,value=line.split("=",1)
        if key.strip().replace("_","").isalnum():os.environ.setdefault(key.strip(),value.strip().strip('"\''))
load_env()
from game import __version__
from game import ai
from game import social
from game import push
from game import accounts
from game import player_feedback as pfb
from game import board_ai
from game import admin_stats
from game.content import public_content,CAREERS
from game.engine import GameError,public_state
from game.storage import Store,Conflict
from game.dialogue import public_config,rephrase

MAX_BODY=16*1024*1024
COOKIE="mnl_session"
CSP=("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
     "connect-src 'self'; font-src 'self'; media-src 'self' blob:; worker-src 'self'; manifest-src 'self'; "
     "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
STATIC_TYPES={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",
              ".json":"application/json; charset=utf-8",".svg":"image/svg+xml",".png":"image/png",".webp":"image/webp",
              ".ico":"image/x-icon",".webmanifest":"application/manifest+json",".woff2":"font/woff2",".mp3":"audio/mpeg",".txt":"text/plain; charset=utf-8",
              ".xml":"application/xml; charset=utf-8"}
COMPRESSIBLE=(".html",".js",".css",".json",".svg",".webmanifest",".txt",".xml")
PAGES={"/privacy":"privacy.html","/terms":"terms.html","/admin":"admin.html","/":"index.html"}
env_flag=lambda k,d="0":os.environ.get(k,d).strip().lower() in ("1","true","yes","on")
STATIC_RECHECK=2.0  # seconds a resolved static route is trusted before its file is stat()ed again
# Budgets that must not multiply with WORKERS: AI spend, sign-in attempts, new saves, feedback.
SHARED_LIMITS=("ai","acct-","newsession:","fb:","fb-day:","fb-ip:")

class SharedLimits:
    """Sliding-window rate limits shared by all worker processes (WORKERS>1), kept in
    a small side database next to the game database. Only the rare, security-relevant
    keys above use it; per-request anti-spam limits stay in each process's memory."""
    def __init__(self,path:str):
        self.path=path
        db=self._db()
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS hits (k TEXT NOT NULL, at REAL NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS hits_k ON hits(k, at)")
        finally:db.close()

    def _db(self):
        db=sqlite3.connect(self.path,timeout=5,isolation_level=None)
        db.execute("PRAGMA synchronous=NORMAL")
        return db

    def hit(self,key:str,limit:int,seconds:float)->bool:
        now=time.time();db=None
        try:
            db=self._db()
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM hits WHERE k=? AND at<?",(key,now-seconds))
            ok=db.execute("SELECT COUNT(*) FROM hits WHERE k=?",(key,)).fetchone()[0]<limit
            if ok:db.execute("INSERT INTO hits(k,at) VALUES(?,?)",(key,now))
            db.execute("COMMIT")
            return ok
        except sqlite3.Error:
            # Fail closed (no extra AI spend or sign-in attempts), except for starting a new save.
            return key.startswith("newsession:")
        finally:
            if db is not None:db.close()

    def prune(self)->None:
        db=self._db()
        try:db.execute("DELETE FROM hits WHERE at<?",(time.time()-86400,))
        finally:db.close()

class GameServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True
    # A page load opens ~100 connections at once (one per static file behind a proxy
    # without upstream keep-alive); a short accept queue drops SYNs and the client only
    # retries after 1 s. The kernel caps this at net.core.somaxconn.
    request_queue_size=1024
    def __init__(self,address,store:Store,allowed_hosts:set[str]|None=None):
        super().__init__(address,Handler)
        self.store=store
        self.allowed_hosts=allowed_hosts or {"localhost","127.0.0.1","::1"}
        self.limits=defaultdict(deque)
        self.limits_lock=threading.Lock()
        self.static_cache={}
        self.static_routes={}
        self.shared_limits=None  # SharedLimits in worker processes (WORKERS>1)
        self.worker=0
        self._content=None
        self.trust_proxy=env_flag("TRUST_PROXY")
        social.ensure(store)
        push.ensure(store)
        admin_stats.ensure(store)

    def content_json(self)->str:
        """The static game catalogue (~0.4 MB of JSON), serialized once per process."""
        if self._content is None:self._content=json.dumps(public_content(),ensure_ascii=False,allow_nan=False)
        return self._content

    def rate_limit(self,key:str,limit:int,seconds:int=60)->bool:
        if self.shared_limits is not None and key.startswith(SHARED_LIMITS):
            return self.shared_limits.hit(key,limit,seconds)
        now=time.monotonic()
        with self.limits_lock:
            q=self.limits[key]
            while q and q[0]<now-seconds:q.popleft()
            if len(q)>=limit:return False
            q.append(now)
            if len(self.limits)>20000:
                stale=[k for k,v in self.limits.items() if not v or v[-1]<now-seconds]
                for k in stale:self.limits.pop(k,None)
            return True

class Handler(BaseHTTPRequestHandler):
    server_version="MotNgayLamNghe/"+__version__
    sys_version=""
    protocol_version="HTTP/1.1"

    def setup(self):
        super().setup();self.connection.settimeout(20)

    def log_message(self,format,*args):
        if not os.environ.get("QUIET"):
            # Never log cookies, request bodies, endpoint keys or dialogue text.
            sys.stderr.write("[%s] %s\n"%(self.log_date_time_string(),format%args))

    # ---- request helpers -------------------------------------------------
    def client_ip(self)->str:
        if self.server.trust_proxy:
            # The right-most entry is the one our own proxy appended; earlier ones are client-supplied.
            fwd=self.headers.get("X-Forwarded-For","").split(",")[-1].strip()
            if fwd:return fwd[:64]
        return self.client_address[0]

    def secure(self)->bool:
        if env_flag("COOKIE_SECURE"):return True
        return self.server.trust_proxy and self.headers.get("X-Forwarded-Proto","").lower()=="https"

    def respond(self,status:int,data:bytes,ctype:str,extra:dict|None=None,compress:bool=False,cache:str|None=None):
        if compress and len(data)>1400 and "gzip" in self.headers.get("Accept-Encoding",""):
            data=gzip.compress(data,5);extra=dict(extra or {},**{"Content-Encoding":"gzip"})
        self.send_response(status)
        self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Content-Security-Policy",CSP)
        self.send_header("Permissions-Policy","camera=(), microphone=(), geolocation=(), payment=()")
        self.send_header("Cross-Origin-Opener-Policy","same-origin")
        if self.secure():self.send_header("Strict-Transport-Security","max-age=31536000")
        if compress:self.send_header("Vary","Accept-Encoding")
        self.send_header("Cache-Control",cache or ("no-store" if self.path.startswith("/api/") else "no-cache"))
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.end_headers()
        if self.command!="HEAD":
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass

    def json(self,status:int,data:dict,extra:dict|None=None,raw:dict|None=None):
        """`raw`: extra top-level members whose values are already JSON text."""
        if isinstance(data,dict):data=dict(data,server_time=round(time.time(),3))
        body=json.dumps(data,ensure_ascii=False,allow_nan=False)
        if raw:body=body[:-1]+"".join(f",{json.dumps(k)}:{v}" for k,v in raw.items())+"}"
        self.respond(status,body.encode(),"application/json; charset=utf-8",extra,compress=True)

    def error(self,status:int,message:str,code:str="error"):
        self.json(status,dict(error=message,code=code))

    def valid_host(self)->bool:
        try:hostname=urlsplit("//"+self.headers.get("Host","")).hostname
        except ValueError:return False
        return bool(hostname in self.server.allowed_hosts or "*" in self.server.allowed_hosts)

    def token(self)->str|None:
        try:
            cookie=SimpleCookie();cookie.load(self.headers.get("Cookie",""))
            return cookie[COOKIE].value if COOKIE in cookie else None
        except Exception:return None

    def cookie(self,token:str,max_age:int=31536000)->str:
        return f"{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={max_age}"+("; Secure" if self.secure() else "")

    def require_session(self)->tuple[str,dict,int,str]:
        token=self.token()
        if not token:raise GameError("Tải lại trang để bắt đầu phiên chơi.","session_missing")
        state,revision,csrf=self.server.store.read(token)
        return token,state,revision,csrf

    def guarded(self,light:bool=False)->tuple[str,dict,int,str]:
        """`light`: only check the CSRF (state and revision come back as None); the
        command route loads the save itself, so parsing it here would be wasted work."""
        if not self.valid_host():raise PermissionError("Host không được phép.")
        if light:
            token=self.token()
            if not token:raise GameError("Tải lại trang để bắt đầu phiên chơi.","session_missing")
            session=(token,None,None,self.server.store.csrf(token))
        else:session=self.require_session()
        if not secrets.compare_digest(self.headers.get("X-Game-CSRF",""),session[3]):raise PermissionError("Mã bảo vệ phiên không hợp lệ. Tải lại trang nhé.")
        origin=self.headers.get("Origin")
        if origin:
            parsed=urlsplit(origin)
            if parsed.scheme not in ("http","https") or parsed.netloc!=self.headers.get("Host"):raise PermissionError("Không nhận thao tác từ website khác.")
        if self.headers.get("Sec-Fetch-Site") in ("cross-site",):raise PermissionError("Không nhận thao tác từ website khác.")
        return session

    # ---- static files -----------------------------------------------------
    def static_entry(self,route:str):
        """(signature, bytes, gzip bytes, etag, suffix, name) of a file under public/, or None."""
        rel=PAGES.get(route) or unquote(route).lstrip("/")
        try:path=(PUBLIC/rel).resolve()
        except (OSError,ValueError):return None
        suffix=path.suffix.lower()
        if not path.is_relative_to(PUBLIC.resolve()) or suffix not in STATIC_TYPES or not path.is_file():return None
        st=path.stat();key=str(path)
        cached=self.server.static_cache.get(key)
        if not cached or cached[0]!=(st.st_mtime_ns,st.st_size):
            raw=path.read_bytes()
            etag='"'+hashlib.sha1(raw).hexdigest()[:20]+'"'
            gz=gzip.compress(raw,6) if suffix in COMPRESSIBLE and len(raw)>1400 else None
            cached=((st.st_mtime_ns,st.st_size),raw,gz,etag,suffix,path.name)
            if len(self.server.static_cache)<600:self.server.static_cache[key]=cached
        return cached

    def static(self,route:str):
        # Hot path (a page load asks for ~100 files, mostly answered 304): a route resolved in
        # the last STATIC_RECHECK seconds skips resolve()/stat(); a deploy is picked up after that.
        now=time.monotonic();hit=self.server.static_routes.get(route)
        if hit and now-hit[1]<STATIC_RECHECK:cached=hit[0]
        else:
            cached=self.static_entry(route)
            if cached is None:self.error(404,"Không tìm thấy tài nguyên.");return
            if len(self.server.static_routes)<2000 or route in self.server.static_routes:self.server.static_routes[route]=(cached,now)
        _,raw,gz,etag,suffix,name=cached
        extra={"ETag":etag}
        if name=="sw.js":extra["Service-Worker-Allowed"]="/"
        if name=="admin.html":extra["X-Robots-Tag"]="noindex, nofollow"  # operator site (public/js/admin/)
        if self.headers.get("If-None-Match")==etag:
            self.send_response(304);self.send_header("ETag",etag);self.send_header("Cache-Control","no-cache");self.send_header("Content-Length","0");self.end_headers();return
        body=raw
        if gz is not None and "gzip" in self.headers.get("Accept-Encoding",""):
            body=gz;extra["Content-Encoding"]="gzip"
        if suffix in COMPRESSIBLE:extra["Vary"]="Accept-Encoding"
        cache="public, max-age=31536000, immutable" if suffix==".woff2" else "no-cache"
        self.respond(200,body,STATIC_TYPES[suffix],extra,cache=cache)

    # ---- routes -----------------------------------------------------------
    def do_HEAD(self):self.do_GET()

    def do_GET(self):
        if not self.valid_host():self.error(403,"Host không được phép.");return
        split=urlsplit(self.path);route=split.path
        try:
            if route=="/api/health":
                self.json(200,dict(status="ok",version=__version__,careers=len(CAREERS)));return
            if route=="/api/bootstrap":
                ip=self.client_ip()
                if not self.server.rate_limit("bootstrap:"+ip,120):self.error(429,"Chờ một chút rồi tải lại nhé.");return
                existing=self.token()
                if not existing and not self.server.rate_limit("newsession:"+ip,int(os.environ.get("NEW_SESSIONS_PER_MINUTE","20"))):
                    self.error(429,"Quá nhiều phiên mới từ mạng này. Chờ một chút nhé.");return
                token,csrf,created=self.server.store.session(existing)
                state,revision,_=self.server.store.read(token)
                if not created:
                    try:
                        if social.settle(self.server.store,token,state):state,revision,_=self.server.store.read(token)
                    except social.SocialError:pass
                extra={"Set-Cookie":self.cookie(token)} if created else {}
                self.json(200,dict(state=public_state(state),revision=revision,csrf=csrf,ai=dict(public_config(),configured=ai.available(),chat=True),
                                   social=social.bootstrap(self.server.store,token,state),push=push.public_config(),account=accounts.status(self.server.store,token),
                                   admin=pfb.is_admin(self.server.store,token)),extra,raw=dict(content=self.server.content_json()));return
            if route=="/api/state":
                _,state,revision,_=self.require_session();self.json(200,dict(state=public_state(state),revision=revision));return
            if route=="/api/save/export":
                _,state,revision,_=self.require_session()
                data=dict(format="mot-ngay-lam-nghe/save-v4",app_version=__version__,state=state)
                self.json(200,data,{"Content-Disposition":"attachment; filename=mot-ngay-lam-nghe-save.json"});return
            if route.startswith("/api/social/"):
                token,state,_,_=self.require_session()
                if not self.server.rate_limit("social-get:"+token,240):self.error(429,"Chậm lại một chút nhé.");return
                query={k:v[0] for k,v in parse_qs(split.query).items()}
                self.json(200,social.get(self.server.store,token,state,route[len("/api/social/"):],query));return
            if route=="/api/push/pending":
                token,state,_,_=self.require_session()
                self.json(200,dict(push.pending(self.server.store,token),lang=state["settings"].get("lang","vi")));return
            if route=="/api/board":  # Nhóm Cư Dân Phố feed (game/board_ai.py)
                _,state,_,_=self.require_session()
                if not self.server.rate_limit("board-get:"+self.token(),240):self.error(429,"Chậm lại một chút nhé.");return
                self.json(200,board_ai.get_view(state,{k:v[0] for k,v in parse_qs(split.query).items()}));return
            if route=="/api/feedback/mine":
                token,_,_,_=self.require_session()
                if not self.server.rate_limit("fb-mine:"+token,60):self.error(429,"Chậm lại một chút nhé.");return
                self.json(200,dict(items=pfb.list_mine(self.server.store,token),admin=pfb.is_admin(self.server.store,token)));return
            if route=="/api/admin/feedback":
                try:token,_,_,_=self.guarded()
                except PermissionError as e:self.error(403,str(e),"forbidden");return
                self.require_admin(token)
                query={k:v[0] for k,v in parse_qs(split.query).items()}
                self.json(200,pfb.list_admin(self.server.store,query.get("status"),query.get("kind"),query.get("before")));return
            if route=="/api/admin/stats":  # Thống kê (game/admin_stats.py): admin only, cached ~60 s
                try:token,_,_,_=self.guarded()
                except PermissionError as e:self.error(403,str(e),"forbidden");return
                self.require_admin(token)
                if not self.server.rate_limit("admin-stats:"+token,30):self.error(429,"Chậm lại một chút nhé.","rate_limited");return
                query={k:v[0] for k,v in parse_qs(split.query).items()}
                try:days=admin_stats.parse_range(query.get("range"))
                except ValueError:self.error(400,"Khoảng ngày chỉ nhận 7, 30 hoặc 90.","bad_range");return
                self.json(200,admin_stats.get(self.server.store,days,fresh=query.get("fresh")=="1"));return
            if route.startswith("/api/"):self.error(404,"Không có API này.");return
            self.static(route)
        except pfb.FeedbackError as e:self.error(e.status,e.message,e.code)
        except social.SocialError as e:self.error(e.status,e.message,e.code)
        except GameError as e:self.error(401 if e.code=="session_missing" else 400,e.message,e.code)
        except (OSError,ValueError):self.error(500,"Không đọc được dữ liệu. Kiểm tra thư mục storage và tải lại.")

    def do_POST(self):
        try:
            route=urlsplit(self.path).path
            token,state,revision,csrf=self.guarded(light=route=="/api/command")
            length=int(self.headers.get("Content-Length","0"))
            if not 0<length<=MAX_BODY:self.error(413,"Nội dung quá lớn hoặc trống.");self.close_connection=True;return
            if not self.headers.get("Content-Type","").startswith("application/json"):self.error(415,"Cần gửi JSON.");self.close_connection=True;return
            data=json.loads(self.rfile.read(length),parse_constant=lambda x:(_ for _ in ()).throw(ValueError("nonfinite")))
            if not isinstance(data,dict):raise GameError("Dữ liệu cần là đối tượng JSON.")
            max_commands=int(os.environ.get("COMMANDS_PER_MINUTE","360"))
            if route=="/api/command":
                if not self.server.rate_limit("cmd:"+token,max_commands):self.error(429,"Nhiều thao tác quá nhanh. Chờ một chút nhé.");return
                if length>256*1024 and data.get("action")!="import_save":self.error(413,"Thao tác quá lớn.");return
                result=self.server.store.command(token,data.get("request_id"),data.get("expected_revision"),data.get("career"),data.get("action"),data.get("payload",{}))
                self.json(200,result);return
            if length>64*1024:self.error(413,"Nội dung quá lớn.");return
            if route=="/api/ai/rephrase":
                if not self.ai_budget(token):self.json(200,dict(mode="scripted",reason="rate_limit"));return
                self.json(200,rephrase(state,data.get("career"),data.get("npc")));return
            if route=="/api/ai/chat":
                if not self.server.rate_limit("cmd:"+token,max_commands):self.error(429,"Nhiều thao tác quá nhanh. Chờ một chút nhé.");return
                self.json(200,self.ai_chat(token,state,revision,data));return
            if route=="/api/ai/interview":
                if not self.server.rate_limit("cmd:"+token,max_commands):self.error(429,"Nhiều thao tác quá nhanh. Chờ một chút nhé.");return
                self.json(200,self.ai_interview(token,revision,data));return
            if route=="/api/ai/class":
                if not self.server.rate_limit("cmd:"+token,max_commands):self.error(429,"Nhiều thao tác quá nhanh. Chờ một chút nhé.");return
                self.json(200,self.ai_class(token,state,revision,data));return
            if route=="/api/ai/board":  # Nhóm Cư Dân Phố: post/reply (+ AI replies), open (+ AI exchange)
                if not self.server.rate_limit("cmd:"+token,max_commands):self.error(429,"Nhiều thao tác quá nhanh. Chờ một chút nhé.");return
                self.json(200,board_ai.ai_board(self,token,state,revision,data));return
            if route=="/api/ai/support_call":
                if not self.server.rate_limit("cmd:"+token,max_commands):self.error(429,"Nhiều thao tác quá nhanh. Chờ một chút nhé.");return
                self.json(200,self.ai_support_call(token,state,revision,data));return
            if route=="/api/ai/feedback":
                self.json(200,self.ai_feedback(token,state,revision,data));return
            if route=="/api/ai/review":
                self.json(200,self.ai_review(token,state,revision,data));return
            if route=="/api/feedback":
                ip=self.client_ip();per10=int(os.environ.get("FEEDBACK_PER_10MIN","5"));per_day=int(os.environ.get("FEEDBACK_PER_DAY","30"))
                if not (self.server.rate_limit("fb:"+token,per10,600) and self.server.rate_limit("fb-day:"+token,per_day,86400) and self.server.rate_limit("fb-ip:"+ip,per10*4,600)):
                    self.error(429,"Bạn gửi góp ý hơi dồn dập. Nghỉ tay một lát rồi gửi tiếp nhé.","rate_limited");return
                self.json(200,pfb.submit(self.server.store,token,state,data,self.headers.get("User-Agent",""),__version__));return
            if route=="/api/admin/feedback":
                if not self.server.rate_limit("fb-admin:"+token,120):self.error(429,"Chậm lại một chút nhé.");return
                self.require_admin(token)
                self.json(200,dict(ok=True,item=pfb.update(self.server.store,data.get("id"),data.get("status"),data.get("reply"))));return
            if route=="/api/account/delete":
                if data.get("confirm")!="XOA":raise GameError("Gõ XOA để xác nhận xóa dữ liệu.")
                pfb.forget(self.server.store,token);social.forget(self.server.store,token);push.forget(self.server.store,token);self.server.store.delete(token)
                self.json(200,dict(deleted=True,message="Đã xóa toàn bộ dữ liệu chơi của bạn trên máy chủ."),{"Set-Cookie":self.cookie("",0)});return
            if route.startswith("/api/account/"):
                self.account_post(route[len("/api/account/"):],token,data);return
            if route.startswith("/api/social/"):
                if not self.server.rate_limit("social:"+token,60):self.error(429,"Nhiều thao tác quá nhanh. Chờ một chút nhé.");return
                self.json(200,social.post(self.server.store,token,state,route[len("/api/social/"):],data));return
            if route in ("/api/push/subscribe","/api/push/unsubscribe"):
                if not self.server.rate_limit("push:"+token,20):self.error(429,"Chờ một chút nhé.");return
                self.json(200,push.subscribe(self.server.store,token,data) if route.endswith("/subscribe") else push.unsubscribe(self.server.store,token,data));return
            self.error(404,"Không có API này.")
        except Conflict as e:
            try:
                _,current,rev,_=self.require_session();self.json(409,dict(error=e.message,code=e.code,state=public_state(current),revision=rev))
            except GameError:self.error(409,e.message,e.code)
        except PermissionError as e:self.error(403,str(e),"forbidden");self.close_connection=True
        except pfb.FeedbackError as e:self.error(e.status,e.message,e.code)
        except social.SocialError as e:self.error(e.status,e.message,e.code)
        except accounts.AccountError as e:self.error(e.status,e.message,e.code)
        except GameError as e:self.error(401 if e.code=="session_missing" else 400,e.message,e.code)
        except (ValueError,TypeError,KeyError,IndexError,RecursionError,AttributeError):self.error(400,"Dữ liệu không đúng cấu trúc hoặc bản lưu không hợp lệ.","invalid_data")
        except Exception as e:
            self.log_error("Internal error: %s",type(e).__name__)
            self.error(500,"Không thực hiện được thao tác. Tiến trình trước đó vẫn được giữ.","internal_error")

    def require_admin(self,token:str):
        """Feedback inbox: only signed-in accounts listed in ADMIN_USERS (403 for everyone else)."""
        if not self.server.rate_limit("fb-admin-get:"+token,240):raise pfb.FeedbackError("Chậm lại một chút nhé.","rate_limited",429)
        if not pfb.is_admin(self.server.store,token):raise pfb.FeedbackError("Chỉ người vận hành mới xem được mục này.","forbidden",403)

    # ---- optional accounts ------------------------------------------------
    def account_post(self,name:str,token:str,data:dict):
        """Register / login / logout / change password. Bodies are never logged."""
        store,ip,limit=self.server.store,self.client_ip(),self.server.rate_limit
        slow=lambda:accounts.AccountError("Thử quá nhiều lần. Chờ vài phút rồi thử lại nhé.","rate_limited",429)
        if name=="register":
            if not (limit("acct-reg:"+ip,5,600) and limit("acct-reg-h:"+ip,20,3600)):raise slow()
            out=accounts.register(store,token,data)
        elif name=="login":
            accounts.check_replace(store,token,data)
            user=data.get("username") if isinstance(data.get("username"),str) else ""
            user=user.strip().lower()[:32]
            if not (limit("acct-login:"+ip,10,60) and limit("acct-login-h:"+ip,60,3600) and limit("acct-user:"+user,5,60) and limit("acct-user-h:"+user,20,3600)):raise slow()
            out=accounts.login(store,token,data)
            if out.pop("drop_anonymous"):
                social.forget(store,token);push.forget(store,token);store.delete(token)
        elif name=="logout":
            accounts.logout(store,token)
            fresh,_,_=store.session(None)
            out=dict(token=fresh,message="Đã đăng xuất. Máy này bắt đầu một phiên chơi mới.")
        elif name=="password":
            if not limit("acct-pw:"+ip,10,600):raise slow()
            out=accounts.change_password(store,token,data)
        else:
            self.error(404,"Không có API này.");return
        fresh=out.pop("token",None)
        self.json(200,out,{"Set-Cookie":self.cookie(fresh)} if fresh else None)

    # ---- AI reviewer personas -------------------------------------------
    def ai_budget(self,token:str)->bool:
        return self.server.rate_limit("ai:"+token,int(os.environ.get("AI_PER_MINUTE","10"))) and self.server.rate_limit("ai-global",int(os.environ.get("AI_GLOBAL_PER_MINUTE","60")))

    def ai_chat_budget(self,token:str)->bool:
        """Free chat: per session per minute and per rolling day, plus the server-wide AI budget."""
        per_min=int(os.environ.get("AI_CHAT_PER_MINUTE","8"));per_day=int(os.environ.get("AI_CHAT_PER_DAY","200"))
        return (self.server.rate_limit("ai-chat:"+token,per_min) and self.server.rate_limit("ai-chat-day:"+token,per_day,86400)
                and self.server.rate_limit("ai-global",int(os.environ.get("AI_GLOBAL_PER_MINUTE","60"))))

    def ai_chat(self,token:str,state:dict,revision:int,data:dict)->dict:
        """POST /api/ai/chat: the scripted `talk` runs first (and is stored); an AI persona
        line then replaces the wording of that one stored NPC line when it passes the guards."""
        career,npc,text=data.get("career"),data.get("npc"),data.get("text")
        if career not in CAREERS:raise GameError("Nghề không hợp lệ.")
        if not isinstance(text,str) or not text.strip():raise GameError("Tin nhắn trống.")
        text=text.strip()
        if len(text)>200:raise GameError("Tin nhắn tối đa 200 ký tự nhé.")
        rid=data.get("request_id")
        if not (isinstance(rid,str) and 8<=len(rid)<=100):rid="ai-chat-"+secrets.token_hex(12)
        expected=data.get("expected_revision")
        out=self.server.store.command(token,rid,expected if type(expected) is int else revision,career,"talk",dict(npc=npc,text=text))
        canonical=str(out["result"].get("reply") or "")
        mode,reason,line="scripted",None,canonical
        if out.get("replayed"):reason="replayed"
        else:
            fresh,_,_=self.server.store.read(token)
            rows=fresh["careers"][career]["chats"].get(npc) or []
            history=rows[:-2][-8:]  # the pair just stored is this turn
            settings=fresh["settings"]
            if ai.abusive(text):allowed,why=True,None
            elif not settings.get("aiConsent"):allowed,why=False,"no_consent"
            elif not ai.available():allowed,why=False,"not_configured"
            elif not self.ai_chat_budget(token):allowed,why=False,"rate_limit"
            else:allowed,why=True,None
            if allowed:
                answer=ai.persona_reply(fresh,career,npc,text,canonical=canonical,history=history)
                reason=answer.get("reason")
                if answer["mode"] in ("ai","guard") and answer["text"]:
                    stored=self._store_chat_line(token,career,npc,canonical,answer["text"],answer["mode"])
                    if stored:
                        out=dict(out,state=stored[0],revision=stored[1]);mode,line=answer["mode"],answer["text"]
                    else:reason="superseded"
            else:reason=why
        result=dict(out["result"],reply=line,message=line)
        return dict(state=out["state"],revision=out["revision"],result=result,mode=mode,reason=reason,reply=line)

    def ai_support_call(self,token:str,state:dict,revision:int,data:dict)->dict:
        """POST /api/ai/support_call: one line of a customer-care phone call (Trạm Lắng Nghe).
        The rule-based `cs_call` command runs first and is stored (tone, SLA, satisfaction and a
        scripted customer line built from the case facts); an AI persona may then reword only that
        stored customer line when it passes the same guards as /api/ai/chat.
        request  {career:"customer_care", task, pick? | text? (1..200), request_id?, expected_revision?}
        response {state, revision, result:{reply, tone, tone_label, kept, intent, message}, mode:"ai"|"scripted"|"guard", reason, reply}"""
        from game.engine import cs_call_context
        if data.get("career","customer_care")!="customer_care":raise GameError("Cuộc gọi chỉ dùng ở trạm hỗ trợ.")
        task,pick,text=data.get("task"),data.get("pick"),data.get("text")
        if not isinstance(task,str) or not 1<=len(task)<=80:raise GameError("Thiếu mã vụ cần gọi.")
        payload=dict(task=task)
        if pick is not None:
            if not isinstance(pick,str) or not 1<=len(pick)<=20 or text is not None:raise GameError("Câu chọn không hợp lệ.")
            payload["pick"]=pick
        else:
            if not isinstance(text,str) or not text.strip():raise GameError("Tin nhắn trống.")
            text=text.strip()
            if len(text)>200:raise GameError("Tin nhắn tối đa 200 ký tự nhé.")
            payload["text"]=text
        rid=data.get("request_id")
        if not (isinstance(rid,str) and 8<=len(rid)<=100):rid="ai-call-"+secrets.token_hex(12)
        expected=data.get("expected_revision")
        out=self.server.store.command(token,rid,expected if type(expected) is int else revision,"customer_care","cs_call",payload)
        canonical=str(out["result"].get("reply") or "")
        mode,reason,line="scripted",None,canonical
        if out.get("replayed"):reason="replayed"
        else:
            fresh,_,_=self.server.store.read(token)
            info=cs_call_context(fresh,task)
            rows=(info or {}).get("history") or []
            said=rows[-2]["text"] if len(rows)>=2 and rows[-2]["role"]=="user" else (text or "")
            settings=fresh["settings"]
            if not info:allowed,why=False,"no_case"
            elif ai.abusive(said):allowed,why=True,None
            elif not settings.get("aiConsent"):allowed,why=False,"no_consent"
            elif not ai.available():allowed,why=False,"not_configured"
            elif not self.ai_chat_budget(token):allowed,why=False,"rate_limit"
            else:allowed,why=True,None
            if allowed:
                answer=ai.persona_reply(fresh,"customer_care",info["npc"],said,context=info["context"],canonical=canonical,
                                        history=rows[:-2][-8:],purpose="support_call")
                reason=answer.get("reason")
                if answer["mode"] in ("ai","guard") and answer["text"]:
                    stored=self._store_call_line(token,task,canonical,answer["text"],answer["mode"])
                    if stored:
                        out=dict(out,state=stored[0],revision=stored[1]);mode,line=answer["mode"],answer["text"]
                    else:reason="superseded"
            else:reason=why
        result=dict(out["result"],reply=line,message=line)
        return dict(state=out["state"],revision=out["revision"],result=result,mode=mode,reason=reason,reply=line)

    def _store_call_line(self,token:str,task:str,canonical:str,line:str,mode:str):
        """Reword the customer line just stored by `cs_call`, only if it is still the last scripted line."""
        store=self.server.store;sid=store.key(token);db=store.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:db.rollback();return None
            raw=store.parse_state(row["state"],sid)
            tasks=(((raw.get("careers") or {}).get("customer_care") or {}).get("tasks") or [])
            t=next((x for x in tasks if isinstance(x,dict) and x.get("id")==task),None)
            rows=(t or {}).get("call") or []
            last=rows[-1] if rows else None
            if not last or last.get("who")!="npc" or last.get("mode")!="scripted" or last.get("text")!=canonical:
                db.rollback();return None
            last.update(text=line[:600],mode=mode,canonical=canonical[:600])
            revision=row["revision"]+1
            db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?",(json.dumps(raw,ensure_ascii=False,allow_nan=False),revision,sid))
            db.commit()
            return public_state(raw),revision
        except Exception:
            db.rollback();raise
        finally:db.close()

    def _store_chat_line(self,token:str,career:str,npc:str,canonical:str,line:str,mode:str):
        """Reword the NPC line just stored by `talk`, only if it is still the last scripted line."""
        store=self.server.store;sid=store.key(token);db=store.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:db.rollback();return None
            raw=store.parse_state(row["state"],sid)
            rows=(((raw.get("careers") or {}).get(career) or {}).get("chats") or {}).get(npc) or []
            last=rows[-1] if rows else None
            if not last or last.get("role")!="npc" or last.get("mode")!="scripted" or last.get("text")!=canonical:
                db.rollback();return None
            last.update(text=line[:600],mode=mode,canonical=canonical[:600])
            revision=row["revision"]+1
            db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?",(json.dumps(raw,ensure_ascii=False,allow_nan=False),revision,sid))
            db.commit()
            return public_state(raw),revision
        except Exception:
            db.rollback();raise
        finally:db.close()

    # ---- AI interviewer (docs/superpowers/specs/2026-09-29-ai-interviewer-design.md) ----
    def ai_interview(self,token:str,revision:int,data:dict)->dict:
        """POST /api/ai/interview: `job_answer` / `job_followup` run first (rule-scored, stored
        scripted); an AI line then rewords the interviewer's newest line if it passes the guards."""
        from game import employment as emp
        career=data.get("career")
        if career not in CAREERS:raise GameError("Nghề không hợp lệ.")
        action,payload=emp.voice_command(data)
        rid=data.get("request_id")
        if not (isinstance(rid,str) and 8<=len(rid)<=100):rid="ai-iv-"+secrets.token_hex(12)
        expected=data.get("expected_revision")
        out=self.server.store.command(token,rid,expected if type(expected) is int else revision,career,action,payload)
        idx=out["result"].get("talk");mode,reason,line="scripted",None,None
        if out.get("replayed"):reason="replayed"
        elif type(idx) is int:
            fresh,_,_=self.server.store.read(token)
            pend=emp.pending_voice(fresh,career,idx)
            if not pend:reason="nothing_to_voice"
            else:
                line=pend["canonical"]
                if not fresh["settings"].get("aiConsent"):reason="no_consent"
                elif not ai.available():reason="not_configured"
                elif ai.abusive(pend["said"]):reason="unsafe_request"
                elif not self.ai_chat_budget(token):reason="rate_limit"
                else:
                    answer=emp.voice(fresh,career,pend);reason=answer.get("reason")
                    if answer["mode"]=="ai":
                        stored=self._store_interview_line(token,career,pend,answer["text"])
                        if stored:out=dict(out,state=stored[0],revision=stored[1]);mode,line=answer["mode"],answer["text"]
                        else:reason="superseded"
        return dict(state=out["state"],revision=out["revision"],result=out["result"],mode=mode,reason=reason,line=line)

    def _store_interview_line(self,token:str,career:str,pend:dict,line:str):
        """Reword talk[idx] of the open application, only if it still holds the same scripted line."""
        from game import employment as emp
        store=self.server.store;sid=store.key(token);db=store.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:db.rollback();return None
            raw=store.parse_state(row["state"],sid)
            if not emp.apply_voice(raw,career,pend["idx"],pend["field"],pend["canonical"],line):db.rollback();return None
            try:emp.validate(raw["careers"][career],career)
            except GameError:db.rollback();return None
            revision=row["revision"]+1
            db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?",(json.dumps(raw,ensure_ascii=False,allow_nan=False),revision,sid))
            db.commit()
            return public_state(raw),revision
        except Exception:
            db.rollback();raise
        finally:db.close()

    # ---- AI in the classroom (docs/superpowers/specs/2026-09-29-teacher-care-ai-design.md) ----
    def ai_class(self,token:str,state:dict,revision:int,data:dict)->dict:
        """POST /api/ai/class {kind:'pupil'|'parent', pupil, task?, op:'reply'|'voice', text?|option?}.
        op 'reply' runs `lesson_answer` / `cl_parent` first (rules decide the effect, the scripted
        reaction is stored); op 'voice' changes nothing but the wording. Then the newest pupil or
        parent line is reworded in character when AI is allowed and the line passes the guards."""
        from game import classroom
        from game import teach_lesson as TL
        kind,pupil,op,task=data.get("kind"),data.get("pupil"),data.get("op") or "reply",data.get("task")
        if kind not in ("pupil","parent"):raise GameError("Loại tin nhắn không hợp lệ.")
        if pupil not in classroom.PUPILS:raise GameError("Không có bạn này trong lớp.")
        if op not in ("reply","voice"):raise GameError("Thao tác không hợp lệ.")
        if kind=="pupil" and not (isinstance(task,str) and 0<len(task)<=64):raise GameError("Thiếu tiết học.")
        out=dict(state=public_state(state),revision=revision,result=dict(message=""));said=""
        if op=="reply":
            text,option=data.get("text"),data.get("option")
            if (text is None)==(option is None):raise GameError("Chọn một câu soạn sẵn hoặc gõ câu của bạn.")
            if text is not None:
                if not isinstance(text,str) or not text.strip():raise GameError("Tin nhắn trống.")
                text=text.strip()
                if len(text)>TL.ANSWER_MAX:raise GameError(f"Tối đa {TL.ANSWER_MAX} ký tự nhé.")
                said=text
            elif not (isinstance(option,str) and 0<len(option)<=8):raise GameError("Lựa chọn không hợp lệ.")
            body=dict(text=text) if text is not None else dict(option=option)
            action,payload=("lesson_answer",dict(task=task,**body)) if kind=="pupil" else ("cl_parent",dict(kid=pupil,**body))
            rid=data.get("request_id")
            if not (isinstance(rid,str) and 8<=len(rid)<=100):rid="ai-class-"+secrets.token_hex(12)
            expected=data.get("expected_revision")
            out=self.server.store.command(token,rid,expected if type(expected) is int else revision,"teacher",action,payload)
        mode,reason,line="scripted",None,str(out["result"].get("reply") or "")
        if out.get("replayed"):reason="replayed"
        else:
            fresh,_,_=self.server.store.read(token)
            job=classroom.voice_job(fresh,kind,pupil,task,op)
            if not job:reason="nothing_to_voice"
            else:
                line=job["canonical"]
                if said and ai.abusive(said):reason="unsafe_request"
                elif not fresh["settings"].get("aiConsent"):reason="no_consent"
                elif not ai.available():reason="not_configured"
                elif not self.ai_chat_budget(token):reason="rate_limit"
                else:
                    answer=TL.voice(fresh,job["who"],job["said"],context=job["context"],canonical=job["canonical"],history=job["history"],
                                    purpose=job["purpose"],direction=job["direction"])
                    reason=answer.get("reason")
                    if answer["mode"]=="ai":
                        stored=self._store_class_line(token,job["ref"],job["canonical"],answer["text"])
                        if stored:out=dict(out,state=stored[0],revision=stored[1]);mode,line=answer["mode"],answer["text"]
                        else:reason="superseded"
        result=dict(out["result"],reply=line)
        return dict(state=out["state"],revision=out["revision"],result=result,mode=mode,reason=reason,reply=line)

    def _store_class_line(self,token:str,ref:dict,canonical:str,line:str):
        """Reword one classroom line (pupil question/reaction or parent message), only if it is unchanged."""
        from game import classroom
        store=self.server.store;sid=store.key(token);db=store.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM sessions WHERE sid=?",(sid,)).fetchone()
            if not row:db.rollback();return None
            raw=store.parse_state(row["state"],sid)
            if not classroom.rewrite(raw,ref,canonical,line,"ai"):db.rollback();return None
            revision=row["revision"]+1
            db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=?",(json.dumps(raw,ensure_ascii=False,allow_nan=False),revision,sid))
            db.commit()
            return public_state(raw),revision
        except Exception:
            db.rollback();raise
        finally:db.close()

    def _feedback_post(self,state:dict,data:dict):
        career=data.get("career")
        if career not in CAREERS:raise GameError("Nghề không hợp lệ.")
        c=state["careers"][career];pid=data.get("post")
        post=next((p for p in c["feed"] if p.get("id")==pid and p.get("feedback")),None)
        return career,c,post

    def _internal(self,token:str,rid:str,career:str,action:str,payload:dict,fallback:tuple):
        try:return self.server.store.command(token,rid[:100],None,career,action,payload,internal=True)
        except (Conflict,GameError):
            # Someone (another tab, the auto-resolve tick) got there first.
            _,state,revision,_=self.server.store.read(token)
            return dict(state=public_state(state),revision=revision,result=dict(message=""),replayed=True)

    def ai_feedback(self,token:str,state:dict,revision:int,data:dict)->dict:
        career,c,post=self._feedback_post(state,data)
        if not post or post["feedback"]["status"]!="awaiting":
            return dict(state=public_state(state),revision=revision,result=dict(message=""),mode="none")
        proposal=None
        if state["settings"].get("aiConsent") and ai.available() and self.ai_budget(token):
            proposal=ai.feedback_decision(c,post,state["settings"].get("lang","vi"))
        payload=dict(post=post["id"],**(proposal or dict(mode="scripted")))
        rid="srv-fb-"+hashlib.sha256(f'{career}|{post["id"]}'.encode()).hexdigest()[:24]+f'-{post["feedback"]["rounds"]}'
        out=self._internal(token,rid,career,"fb_resolve",payload,(state,revision))
        return dict(out,mode="ai" if proposal else "scripted")

    def ai_review(self,token:str,state:dict,revision:int,data:dict)->dict:
        career,c,post=self._feedback_post(state,data)
        fb=(post or {}).get("feedback") or {}
        if not post or fb.get("voice")!="scripted" or fb.get("thread") or not state["settings"].get("aiConsent") or not ai.available():
            return dict(mode="none")
        if not self.ai_budget(token):return dict(mode="none",reason="rate_limit")
        text=ai.review_voice(c,post,state["settings"].get("lang","vi"))
        if not text:return dict(mode="none",reason="unavailable")
        rid="srv-rv-"+hashlib.sha256(f'{career}|{post["id"]}'.encode()).hexdigest()[:24]
        return dict(self._internal(token,rid,career,"fb_voice",dict(post=post["id"],text=text),(state,revision)),mode="ai")


def maintenance(store:Store,stop:threading.Event,limits:SharedLimits|None=None):
    """Background housekeeping (one process only): WAL checkpoints, pruning of
    receipts, abandoned guest saves and stale saves, due pushes.
    PRUNE_GUEST_DAYS (default 3, 0 = off): never-played guest saves idle that long.
    RECEIPT_DAYS (default 2) / RECEIPTS_PER_SAVE (default 200): idempotency receipts kept."""
    last_prune=last_hourly=0.0;last_checkpoint=time.time()
    def step(name,fn):
        try:fn()
        except Exception as e:  # never kill the server for housekeeping
            sys.stderr.write(f"[maintenance] {name}: {type(e).__name__}\n")
    while not stop.wait(30):
        now=time.time()
        if now-last_checkpoint>=60:
            last_checkpoint=now;step("checkpoint",store.checkpoint)
        if now-last_hourly>3600:
            last_hourly=now
            step("receipts",lambda:store.prune_receipts(float(os.environ.get("RECEIPT_DAYS","2")),int(os.environ.get("RECEIPTS_PER_SAVE","200"))))
            guest_days=float(os.environ.get("PRUNE_GUEST_DAYS","3") or 0)
            if guest_days>0:step("guests",lambda:store.prune_guests(guest_days))
            if limits:step("limits",limits.prune)
        if now-last_prune>6*3600:
            last_prune=now
            step("prune",lambda:(store.prune(int(os.environ.get("SESSION_IDLE_DAYS","180"))),social.prune(store),pfb.prune(store)))
        step("push",lambda:push.deliver_due(store))


def limits_path(db_path:str)->str:
    """The shared rate-limit database lives next to the game database (GAME_DB/--db),
    i.e. in the writable data directory, never beside the code."""
    db=Path(os.path.abspath(db_path))
    return str(db.with_name(db.stem+"-limits.sqlite3"))


def serve_workers(server:GameServer,store:Store,n:int,db_path:str)->int:
    """WORKERS=n: pre-fork n processes that all accept() on the one listening socket
    (like SO_REUSEPORT, but portable and it balances by who is free; no proxy change).
    Worker 0 alone runs housekeeping. AI, sign-in, new-save and feedback budgets are
    shared through SharedLimits; the LLM concurrency gate is split between workers.
    A worker that dies is restarted; SIGTERM/SIGINT stop them all."""
    limits=SharedLimits(limits_path(db_path))
    server.socket.setblocking(False)  # every worker wakes on a new connection; the others get EAGAIN
    store.close_pool()  # no SQLite connection may cross fork()
    children:dict[int,int]={};stopping=threading.Event()
    def spawn(i:int):
        pid=os.fork()
        if pid==0:
            code=1
            try:code=_worker(server,store,limits,i,n)
            except BaseException:traceback.print_exc()
            finally:os._exit(code)
        children[pid]=i
    def stop(signum,frame):
        stopping.set()
        for pid in list(children):
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    for i in range(n):spawn(i)
    while children:
        try:pid,status=os.wait()
        except ChildProcessError:break
        i=children.pop(pid,None)
        if i is not None and not stopping.is_set():
            sys.stderr.write(f"[workers] worker {i} stopped (status {status}); restarting\n");time.sleep(1);spawn(i)
    server.server_close()
    print("\nĐã dừng. Tiến trình đã lưu trong SQLite.")
    return 0


def _worker(server:GameServer,store:Store,limits:SharedLimits,i:int,n:int)->int:
    signal.signal(signal.SIGTERM,signal.SIG_DFL);signal.signal(signal.SIGINT,signal.default_int_handler)
    server.shared_limits=limits;server.worker=i
    ai._gate=threading.BoundedSemaphore(max(1,math.ceil(max(1,int(os.environ.get("LLM_CONCURRENCY","4") or 4))/n)))
    stop=threading.Event()
    if i==0:threading.Thread(target=maintenance,args=(store,stop,limits),daemon=True,name="maintenance").start()
    try:server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:pass
    finally:stop.set()
    return 0


def main():
    parser=argparse.ArgumentParser(description="Một ngày làm nghề — web game")
    parser.add_argument("--host",default=os.environ.get("HOST","127.0.0.1"))
    parser.add_argument("--port",type=int,default=int(os.environ.get("PORT","8765")))
    parser.add_argument("--open",action="store_true",help="Open the game in your default browser")
    parser.add_argument("--db",default=os.environ.get("GAME_DB",str(ROOT/"storage"/"game.sqlite3")))
    args=parser.parse_args()
    allowed={"localhost","127.0.0.1","::1",args.host}|set(filter(None,(h.strip() for h in os.environ.get("ALLOWED_HOSTS","").split(","))))
    if args.host=="0.0.0.0" and not os.environ.get("ALLOWED_HOSTS"):
        print("Public/LAN mode: set ALLOWED_HOSTS to your domain or IP in .env (see docs/DEPLOY.md).")
    # Real players get the journey story; MNL_DEV=1 (browser sweeps) keeps every workplace open.
    store=Store(args.db,story=os.environ.get("MNL_DEV")!="1")
    try:server=GameServer((args.host,args.port),store,allowed)
    except OSError as e:
        print(f"Không mở được cổng {args.port}: {e}. Thử --port 8766.");return 1
    # WORKERS=n (n>1, POSIX only): n processes share the port; see serve_workers().
    workers=max(1,int(os.environ.get("WORKERS","1") or 1)) if hasattr(os,"fork") else 1
    url=f"http://127.0.0.1:{server.server_port}"
    print(f"\n  PHỐ CÓ CHUYỆN · v{__version__}\n  Chơi tại: {url}\n  Lưu tại: {args.db}\n  AI phản hồi: {'bật' if ai.available() else 'tắt (lời thoại có sẵn)'} · Web push: {'bật' if push.public_config()['enabled'] else 'tắt'}"
          +(f" · {workers} tiến trình" if workers>1 else "")+"\n  Nhấn Ctrl+C để dừng.\n",flush=True)
    if args.open:threading.Timer(.5,lambda:webbrowser.open(url)).start()
    if workers>1:return serve_workers(server,store,workers,args.db)
    stop=threading.Event()
    threading.Thread(target=maintenance,args=(store,stop),daemon=True).start()
    try:server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:print("\nĐã dừng. Tiến trình đã lưu trong SQLite.")
    finally:stop.set();server.server_close()
    return 0

if __name__=="__main__":raise SystemExit(main())
