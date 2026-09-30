"""Versioned static assets for the game page.

The page (public/index.html) is rendered at serve time:
- every /js/, /css/, /i18n/ and /music/ URL carries ?v=<content hash> (12 hex of SHA-256);
- an import map sends every ES module to its ?v= URL, so relative and dynamic imports
  (careers, scenes) resolve to exactly the bytes this server release hashed;
- the static module graph of /js/app.js is announced with <link rel=modulepreload>
  (one flat round of requests instead of a 4-level import waterfall);
- public/js/boot.js is inlined (it starts /api/bootstrap and /api/content at once);
  the import map and boot script are allowed by CSP hashes, never by 'unsafe-inline'.

A ?v= URL may be cached for a year (immutable) because its bytes can never change:
the proxy serves it from a content-addressed copy (write_cas: <cas>/<hash>/<path>), and
a URL whose hash is not in that store falls back to the plain file with no-cache.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import posixpath
import re
import threading
import time
from pathlib import Path

VERSIONED_DIRS = ("js", "css", "i18n", "music", "icons")
VERSIONED_SUFFIXES = {".js", ".css", ".json", ".mp3", ".webp", ".png", ".svg"}
MAPPED_SUFFIXES = (".js", ".css", ".json", ".mp3")  # in the import map (modules + asset() lookups)
PRECOMPRESS = (".js", ".css", ".json", ".svg")  # text copies that get .gz/.br siblings in the store (precompress)
HASH_LEN = 12
RECHECK = 2.0  # seconds a snapshot is trusted before the files are stat()ed again
ENTRY = "/js/app.js"
IMMUTABLE = "public, max-age=31536000, immutable"
_IMPORT = re.compile(r"""^[ \t]*import\s*(?:[^;'"()]*?\bfrom\s*)?['"]([^'"]+)['"]""", re.M)
_EXPORT = re.compile(r"""^[ \t]*export\s[^;'"()]*?\bfrom\s*['"]([^'"]+)['"]""", re.M)
_ATTR_URL = re.compile(r"""((?:href|src)="|url\()(/(?:js|css|i18n|music|icons)/[^"?#)]+)("|\))""")
_INLINE_BOOT = re.compile(r"""<script[^>]*\bdata-inline\b[^>]*></script>""")


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:HASH_LEN]


def csp_hash(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def module_imports(source: str) -> list[str]:
    """Static import/export-from specifiers of an ES module (dynamic import() is left out)."""
    return [m.group(1) for rx in (_IMPORT, _EXPORT) for m in rx.finditer(source)]


class Snapshot:
    """One consistent view of public/: file hashes, the rendered page and its CSP."""
    def __init__(self, files: dict[str, str], build: str, version: str, importmap: str, preload: list[str], html: bytes, csp: str):
        self.files, self.build, self.version, self.importmap, self.preload, self.csp = files, build, version, importmap, preload, csp
        self.html = html
        self.html_gz = gzip.compress(html, 6)
        self.html_etag = '"' + hashlib.sha256(html).hexdigest()[:20] + '"'

    def url(self, path: str) -> str:
        h = self.files.get(path)
        return f"{path}?v={h}" if h else path


class WebAssets:
    def __init__(self, public: Path, base_csp: str, content_version=lambda: "", release: str = ""):
        self.public = Path(public)
        self.release = release
        self.base_csp = base_csp
        self.content_version = content_version
        self._lock = threading.Lock()
        self._hashes: dict[str, tuple[tuple[int, int], str]] = {}
        self._snap: Snapshot | None = None
        self._sig = None
        self._checked = 0.0

    # ---- scanning -----------------------------------------------------
    def _paths(self):
        for top in VERSIONED_DIRS:
            base = self.public / top
            if not base.is_dir():
                continue
            for root, dirs, names in os.walk(base):
                dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))
                for name in sorted(names):
                    if Path(name).suffix.lower() in VERSIONED_SUFFIXES and not name.startswith("."):
                        path = Path(root) / name
                        yield "/" + path.relative_to(self.public).as_posix(), path

    def _signature(self):
        sig = []
        for url, path in self._paths():
            try:
                st = path.stat()
            except OSError:
                continue
            sig.append((url, st.st_mtime_ns, st.st_size))
        try:
            st = (self.public / "index.html").stat()
            sig.append(("/index.html", st.st_mtime_ns, st.st_size))
        except OSError:
            pass
        sig.append(("content", self.content_version(), 0))
        return tuple(sig)

    def snapshot(self) -> Snapshot:
        now = time.monotonic()
        snap = self._snap
        if snap is not None and now - self._checked < RECHECK:
            return snap
        with self._lock:
            if self._snap is not None and time.monotonic() - self._checked < RECHECK:
                return self._snap
            sig = self._signature()
            if self._snap is None or sig != self._sig:
                self._snap = self._build(sig)
                self._sig = sig
            self._checked = time.monotonic()
            return self._snap

    def hash_of(self, url: str) -> str | None:
        return self.snapshot().files.get(url)

    def _file_hash(self, url: str, path: Path, key: tuple[int, int]) -> str:
        cached = self._hashes.get(url)
        if cached and cached[0] == key:
            return cached[1]
        h = content_hash(path.read_bytes())
        self._hashes[url] = (key, h)
        return h

    # ---- rendering ----------------------------------------------------
    def _build(self, sig) -> Snapshot:
        keys = {url: (mtime, size) for url, mtime, size in sig if url.startswith("/")}
        files: dict[str, str] = {}
        for url, path in self._paths():
            if url in keys and url != "/index.html":
                try:
                    files[url] = self._file_hash(url, path, keys[url])
                except OSError:
                    continue
        content = self.content_version() or ""
        build = hashlib.sha256(json.dumps([sorted(files.items()), content, self.release]).encode()).hexdigest()[:HASH_LEN]
        version = f"{self.release}+{build}" if self.release else build
        imports = {url: f"{url}?v={h}" for url, h in files.items() if url.endswith(MAPPED_SUFFIXES) and not url.startswith("/js/admin/")}
        importmap = json.dumps({"imports": imports}, separators=(",", ":"), sort_keys=True)
        preload = [f"{u}?v={files[u]}" for u in self.module_graph(ENTRY) if u in files]
        template = (self.public / "index.html").read_text(encoding="utf-8")
        boot_src = (self.public / "js" / "boot.js").read_text(encoding="utf-8").strip()
        if "</script" in boot_src.lower():
            raise ValueError("boot.js must not contain </script>")
        head = [f'<script type="importmap">{importmap}</script>',
                f'<meta name="mnl-version" content="{version}">']
        if content:
            head.append(f'<meta name="mnl-content" content="/api/content?v={content}">')
        head.append(f"<script>{boot_src}</script>")
        # app.js itself has its own <script type=module>; preload its whole static graph in one round.
        head += [f'<link rel="modulepreload" href="{u}">' for u in preload if not u.startswith(ENTRY + "?")]
        html = _INLINE_BOOT.sub(lambda _m: "\n  ".join(head), template, count=1)
        html = _ATTR_URL.sub(lambda m: m.group(1) + (f"{m.group(2)}?v={files[m.group(2)]}" if m.group(2) in files else m.group(2)) + m.group(3), html)
        csp = self.base_csp.replace("script-src 'self'", f"script-src 'self' {csp_hash(importmap)} {csp_hash(boot_src)}", 1)
        return Snapshot(files, build, version, importmap, preload, html.encode("utf-8"), csp)

    def module_graph(self, entry: str) -> list[str]:
        """The static import graph of `entry` (URL paths, breadth first, entry first)."""
        seen, order, queue = {entry}, [], [entry]
        while queue:
            url = queue.pop(0)
            order.append(url)
            try:
                source = (self.public / url.lstrip("/")).read_text(encoding="utf-8")
            except OSError:
                continue
            for spec in module_imports(source):
                if spec.startswith(("./", "../")):
                    dep = posixpath.normpath(posixpath.join(posixpath.dirname(url), spec))
                elif spec.startswith("/"):
                    dep = spec
                else:
                    continue
                if dep not in seen:
                    seen.add(dep)
                    queue.append(dep)
        return order

    # ---- content-addressed copies for the proxy -----------------------
    def write_cas(self, target: Path) -> int:
        """Copy every versioned file to <target>/<hash>/<path> (idempotent, atomic per file).
        The proxy serves /js/x.js?v=<hash> from there, so a ?v= URL always returns the
        bytes it names, even while a deploy swaps the files or after it (old open tabs)."""
        snap = self.snapshot()
        written = 0
        for url, h in snap.files.items():
            dest = Path(target) / h / url.lstrip("/")
            if dest.exists():
                continue
            data = (self.public / url.lstrip("/")).read_bytes()
            if content_hash(data) != h:  # changed under us: the next snapshot will copy it
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
            tmp.write_bytes(data)
            os.chmod(tmp, 0o644)
            os.replace(tmp, dest)
            written += 1
        return written

    def precompress(self, target: Path) -> int:
        """Write <file>.gz (and <file>.br when the `brotli` module is installed) next to each text copy in the
        content-addressed store, once: nginx serves them with gzip_static / brotli_static (maximum compression,
        no CPU per request; the English pack is 1.7 MB gzip, 1.2 MB brotli). Slow-ish (~1 s per release), so
        it runs in a background thread after the server is up; until then nginx compresses on the fly."""
        try:
            import brotli  # optional: apt install python3-brotli
        except ImportError:
            brotli = None
        made = 0
        for url, h in self.snapshot().files.items():
            if not url.endswith(PRECOMPRESS):
                continue
            src = Path(target) / h / url.lstrip("/")
            try:
                if not src.is_file() or src.stat().st_size < 1400:
                    continue
                data = None
                for ext, pack in ((".gz", lambda d: gzip.compress(d, 9, mtime=0)),
                                  (".br", (lambda d: brotli.compress(d, quality=9)) if brotli else None)):
                    dest = src.with_name(src.name + ext)
                    if pack is None or dest.exists():
                        continue
                    data = src.read_bytes() if data is None else data
                    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
                    tmp.write_bytes(pack(data))
                    os.chmod(tmp, 0o644)
                    os.replace(tmp, dest)
                    made += 1
            except OSError:
                continue
        return made
