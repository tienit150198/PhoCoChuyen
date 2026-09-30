#!/usr/bin/env python3
"""Move the game's SQLite data into PostgreSQL, keep it in sync, verify it, and
copy new progress back for a rollback (docs/POSTGRES.md has the runbook).

  pg_migrate.py init                      create the schema (game/pg_schema.py) + bookkeeping
  pg_migrate.py copy  [--max-mb-per-s N]  full copy, chunked, throttled, resumable
  pg_migrate.py sync                      delta sync (inserts, updates AND deletions)
  pg_migrate.py verify [--fast|--live]    compare counts + a hash of every row; exit 1 on mismatch
  pg_migrate.py reset-seq                 identity sequences past max(id) and sqlite_sequence
  pg_migrate.py finalize                  cutover: stat triggers + schema version + reset-seq (no FKs, by design)
  pg_migrate.py mark-cutover              PG is now the live database: copy/sync refuse to run
  pg_migrate.py reverse-sync --from-backup B --out NEW   PG -> a COPY of the SQLite backup (rollback)
  pg_migrate.py status                    progress of each table

Safety rules this tool keeps (production runs it next to the live game):
- SQLite is opened read-only (URI mode=ro). Every read is one short statement that is
  read to the end at once (fetchall): no read snapshot is ever held between chunks, so
  the WAL can always be checkpointed (a pinned snapshot grew the WAL to 2 GB once).
- No full-table count(*) / sum(length()) on the live file: progress uses rowid ranges.
- --max-mb-per-s and --pause-ms throttle the reads so the game keeps its (slow) disk.
- Secrets are never printed: the PostgreSQL URL comes from --pg-env-file (DATABASE_URL=...)
  or the DATABASE_URL environment variable. Output only has table names, ids and counts.
- Once `mark-cutover` ran, copy/sync refuse to overwrite PostgreSQL (use --force only on
  a fresh rehearsal database).

Runs with the system python3 and psycopg 3.1 (Ubuntu 24.04: python3-psycopg).
"""
from __future__ import annotations

import argparse
import datetime
import decimal
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = os.environ.get("GAME_DB", "/var/lib/mot-ngay-lam-nghe/game.sqlite3")
DEFAULT_PG_ENV = "/etc/mot-ngay-lam-nghe/pg.env"
LOCK_KEY = 73_001_017            # pg advisory lock: one pg_migrate at a time
META = "pgmig"                   # bookkeeping schema in PostgreSQL
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Delta strategy per table (the rest: key diff; no key: full replace).
REVISION = {"sessions": "revision"}            # key + version column: copy only changed versions
APPEND = {"receipts": "sid", "archive": "sid"}  # append + prune, grouped by save: rowid watermark + per-group counts
LAST = ("stat_births", "stat_active", "stat_fb_ack")  # derived by SQLite triggers: sync after their sources

try:
    import psycopg
    from psycopg import errors as pgerrors
except ImportError:  # the tests skip; the CLI explains
    psycopg = None
    pgerrors = None


class MigrationError(Exception):
    pass


def q(name: str) -> str:
    if not IDENT.match(name):
        raise MigrationError(f"bad identifier {name!r}")
    return '"' + name + '"'


def qcols(cols) -> str:
    return ",".join(q(c) for c in cols)


def norm(v):
    """One canonical Python value per stored value, equal on both sides for equal data."""
    if v is None or isinstance(v, str):
        return v
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() and abs(v) < 9.2e18 else v
    if isinstance(v, decimal.Decimal):
        return norm(int(v) if v == v.to_integral_value() else float(v))
    if isinstance(v, (bytes, bytearray, memoryview)):
        return bytes(v)
    if isinstance(v, datetime.datetime):
        if v.tzinfo is not None:
            v = v.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    return v


def to_sqlite(v):
    v = norm(v)
    return v


def row_bytes(row) -> int:
    n = 0
    for v in row:
        if isinstance(v, str):
            n += len(v)
        elif isinstance(v, (bytes, bytearray)):
            n += len(v)
        else:
            n += 8
    return n


def sha_text(s) -> str | None:
    if s is None:
        return None
    if isinstance(s, str):
        s = s.encode("utf-8", "surrogatepass")
    return hashlib.sha256(bytes(s)).hexdigest()


def short(key) -> str:
    """An id for the report: never player data, only (a prefix of) the row key."""
    parts = key if isinstance(key, (tuple, list)) else (key,)
    return "/".join(str(p)[:16] for p in parts)


# ---------------------------------------------------------------------------
# Output


class Reporter:
    def __init__(self, as_json: bool, quiet: bool = False):
        self.as_json, self.quiet = as_json, quiet
        self.last = 0.0

    def event(self, kind: str, force: bool = False, **fields):
        now = time.monotonic()
        if kind == "progress" and not force and now - self.last < 1.0:
            return
        if kind == "progress":
            self.last = now
        fields = dict(event=kind, t=round(time.time(), 3), **fields)
        if self.as_json:
            sys.stdout.write(json.dumps(fields, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        elif not self.quiet:
            body = " ".join(f"{k}={v}" for k, v in fields.items() if k not in ("event", "t"))
            sys.stderr.write(f"[{kind}] {body}\n")
            sys.stderr.flush()


class Throttle:
    """Keep the read rate under max_mb_per_s (0 = no cap) and pause between chunks."""

    def __init__(self, max_mb_per_s: float, pause_ms: float):
        self.rate = max_mb_per_s * 1e6 if max_mb_per_s and max_mb_per_s > 0 else 0
        self.pause = max(0.0, pause_ms / 1000)
        self.t0 = time.monotonic()
        self.bytes = 0
        self.slept = 0.0

    def spend(self, n: int):
        self.bytes += n
        wait = self.pause
        if self.rate:
            ahead = self.bytes / self.rate - (time.monotonic() - self.t0)
            wait = max(wait, ahead)
        if wait > 0:
            time.sleep(wait)
            self.slept += wait

    def mb_s(self) -> float:
        dt = time.monotonic() - self.t0
        return round(self.bytes / 1e6 / dt, 2) if dt > 0 else 0.0


# ---------------------------------------------------------------------------
# Table specs (from game/pg_schema.py, checked against both databases)


class Spec:
    def __init__(self, name, db, key, cols=None):
        self.name, self.db, self.key = name, db, tuple(key or ())
        self.cols = tuple(cols or ())
        self.version = REVISION.get(name)
        self.group = APPEND.get(name)
        if not self.key:
            self.strategy = "replace"
        elif self.version:
            self.strategy = "revision"
        elif self.group:
            self.strategy = "append"
        else:
            self.strategy = "diff"
        self.identity_always = False
        self.text_keys = ()

    def kidx(self):
        if getattr(self, "_kidx", None) is None or self._kcols != (self.cols, self.key):
            self._kidx, self._kcols = tuple(self.cols.index(k) for k in self.key), (self.cols, self.key)
        return self._kidx

    def keyof(self, row):
        return tuple(norm(row[i]) for i in self.kidx())

    def group_of(self, key):
        """The save (group) of a row key, for append tables."""
        return key[self.key.index(self.group)] if self.group in self.key else None

    def __repr__(self):
        return f"Spec({self.name},{self.strategy})"


def _field(t, *names, default=None):
    for n in names:
        if isinstance(t, dict) and n in t:
            return t[n]
        if not isinstance(t, dict) and hasattr(t, n):
            return getattr(t, n)
    return default


def _names(v):
    if v is None:
        return ()
    if isinstance(v, str):
        return tuple(x.strip() for x in v.split(",") if x.strip())
    if isinstance(v, dict):
        return tuple(v)
    out = []
    for c in v:
        out.append(c if isinstance(c, str) else (_field(c, "name") or c[0]))
    return tuple(out)


SCHEMA_FILE = None  # --schema-file / MNL_PG_SCHEMA_FILE: game/pg_schema.py outside a release tree


def load_schema(module: str | None = None):
    path = SCHEMA_FILE or os.environ.get("MNL_PG_SCHEMA_FILE")
    if path:
        if not Path(path).is_file():
            raise MigrationError(f"schema file {path} not found")
        spec = importlib.util.spec_from_file_location("mnl_pg_schema", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    sys.path.insert(0, str(ROOT))
    try:
        return importlib.import_module(module or "game.pg_schema")
    except ImportError as e:
        raise MigrationError(f"cannot import {module or 'game.pg_schema'} next to {ROOT} ({e}): pass --schema-file")


def specs_from(schema) -> list[Spec]:
    out = []
    for t in schema.TABLES:
        if isinstance(t, str):
            out.append(Spec(t, "limits" if t == "hits" else "main", ()))
            continue
        if isinstance(t, dict) and "source" in t and t["source"] is None:
            continue  # PostgreSQL-only table (mnl_meta)
        if not isinstance(t, dict) and getattr(t, "source", "main") is None:
            continue
        name = _field(t, "name", "table")
        db = str(_field(t, "source", "db", "database", "file", default=None) or ("limits" if name == "hits" else "main"))
        db = "limits" if "limit" in db else "main"
        out.append(Spec(name, db, _names(_field(t, "key", "pk", "primary_key", "keys")), _names(_field(t, "columns", "cols"))))
    first = [s for s in out if s.name in REVISION]
    last = [s for s in out if s.name in LAST]
    return first + [s for s in out if s not in first and s not in last] + last


def ensure_stages(schema, conn, stages):
    """Run some DDL stages of game/pg_schema.py (tables/indexes/constraints/triggers/tuning)."""
    fn = getattr(schema, "ensure", None)
    if callable(fn):
        if stages is None:
            fn(conn, force=True)
        else:
            known = {n for n, _ in getattr(schema, "STAGES", ())}
            fn(conn, stages=tuple(x for x in stages if not known or x in known))
    else:
        ddl = getattr(schema, "DDL", None) or getattr(schema, "SCHEMA", None)
        if not ddl:
            raise MigrationError("game/pg_schema.py has no ensure()/DDL")
        conn.execute(ddl if isinstance(ddl, str) else ";\n".join(ddl))
    conn.commit()


# ---------------------------------------------------------------------------
# SQLite side


class SQLiteSide:
    kind = "sqlite"

    def __init__(self, path: str, readonly: bool = True, busy_ms: int = 5000):
        self.path = path
        self.readonly = readonly
        if readonly:
            uri = "file:" + quote(str(Path(path).resolve()).replace("\\", "/")) + "?mode=ro"
            self.db = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=busy_ms / 1000,
                                      check_same_thread=False)
            self.db.execute("PRAGMA query_only=1")
        else:
            self.db = sqlite3.connect(path, isolation_level=None, timeout=busy_ms / 1000)
            self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute(f"PRAGMA busy_timeout={int(busy_ms)}")
        self.db.execute("PRAGMA cache_size=-16000")
        self._rowid = {}

    # Every read: one statement, fetched to the end, cursor closed -> no snapshot kept.
    def all(self, sql, args=()):
        cur = self.db.execute(sql, args)
        try:
            return cur.fetchall()
        finally:
            cur.close()

    def close(self):
        self.db.close()

    def tables(self) -> set:
        return {r[0] for r in self.all("SELECT name FROM sqlite_master WHERE type='table'")}

    def columns(self, table) -> list:
        return [r[1] for r in self.all(f"PRAGMA table_info({q(table)})")]

    def has_rowid(self, table) -> bool:
        if table not in self._rowid:
            try:
                self.all(f"SELECT rowid FROM {q(table)} LIMIT 0")
                self._rowid[table] = True
            except sqlite3.OperationalError:
                self._rowid[table] = False
        return self._rowid[table]

    def max_rowid(self, table) -> int:
        return self.all(f"SELECT max(rowid) FROM {q(table)}")[0][0] or 0 if self.has_rowid(table) else 0

    def count(self, table) -> int:
        return self.all(f"SELECT count(*) FROM {q(table)}")[0][0]

    def rowid_chunk(self, spec, after: int, limit: int, upto: int | None = None):
        extra = " AND rowid<=?" if upto is not None else ""
        args = (after, upto, limit) if upto is not None else (after, limit)
        return self.all(f"SELECT rowid,{qcols(spec.cols)} FROM {q(spec.name)} WHERE rowid>?{extra} "
                        f"ORDER BY rowid LIMIT ?", args)

    def key_chunk(self, spec, after, limit, cols=None):
        cols = cols or spec.cols
        k = qcols(spec.key)
        if after is None:
            return self.all(f"SELECT {qcols(cols)} FROM {q(spec.name)} ORDER BY {k} LIMIT ?", (limit,))
        marks = ",".join("?" * len(spec.key))
        cond = f"({k})>({marks})" if len(spec.key) > 1 else f"{k}>?"
        return self.all(f"SELECT {qcols(cols)} FROM {q(spec.name)} WHERE {cond} ORDER BY {k} LIMIT ?",
                        (*after, limit))

    def versions(self, spec) -> dict:
        k, v = spec.key[0], spec.version
        # (sid, revision) comes from the covering index stat_sessions_seen when it exists:
        # the table itself would drag every save's overflow pages along.
        return {r[0]: r[1] for r in self.all(f"SELECT {q(k)},{q(v)} FROM {q(spec.name)}")}

    def light(self, spec, cols) -> dict:
        k = spec.key[0]
        return {r[0]: tuple(norm(x) for x in r[1:]) for r in
                self.all(f"SELECT {q(k)},{qcols(cols)} FROM {q(spec.name)}")}

    def rows_by_keys(self, spec, keys, cols=None):
        cols = cols or spec.cols
        if not keys:
            return []
        if len(spec.key) == 1:
            marks = ",".join("?" * len(keys))
            return self.all(f"SELECT {qcols(cols)} FROM {q(spec.name)} WHERE {q(spec.key[0])} IN ({marks})",
                            [k[0] for k in keys])
        row = "(" + ",".join("?" * len(spec.key)) + ")"
        return self.all(f"SELECT {qcols(cols)} FROM {q(spec.name)} WHERE ({qcols(spec.key)}) IN "
                        f"(VALUES {','.join([row] * len(keys))})", [x for k in keys for x in k])

    def rows_by_groups(self, spec, groups):
        marks = ",".join("?" * len(groups))
        return self.all(f"SELECT {qcols(spec.cols)} FROM {q(spec.name)} WHERE {q(spec.group)} IN ({marks})",
                        list(groups))

    def group_counts(self, spec, chunk: int = 5000) -> dict:
        g, out, last = q(spec.group), {}, None
        while True:
            if last is None:
                rows = self.all(f"SELECT {g},count(*) FROM {q(spec.name)} GROUP BY {g} ORDER BY {g} LIMIT ?", (chunk,))
            else:
                rows = self.all(f"SELECT {g},count(*) FROM {q(spec.name)} WHERE {g}>? GROUP BY {g} ORDER BY {g} LIMIT ?",
                                (last, chunk))
            out.update(rows)
            if len(rows) < chunk:
                return out
            last = rows[-1][0]

    def all_rows(self, spec, chunk=5000):
        """Every row, in rowid chunks (small keyless tables)."""
        out, last = [], 0
        while True:
            rows = self.rowid_chunk(spec, last, chunk)
            out.extend(r[1:] for r in rows)
            if len(rows) < chunk:
                return out
            last = rows[-1][0]

    # --- writes (reverse-sync target only; never on the live file) ---
    def upsert(self, spec, rows):
        if not rows:
            return
        cols = qcols(spec.cols)
        marks = ",".join("?" * len(spec.cols))
        if spec.key:
            rest = [c for c in spec.cols if c not in spec.key]
            tail = (f" ON CONFLICT({qcols(spec.key)}) DO UPDATE SET " + ",".join(f"{q(c)}=excluded.{q(c)}" for c in rest)
                    if rest else f" ON CONFLICT({qcols(spec.key)}) DO NOTHING")
        else:
            tail = ""
        self.db.executemany(f"INSERT INTO {q(spec.name)}({cols}) VALUES({marks}){tail}",
                            [tuple(to_sqlite(v) for v in r) for r in rows])

    def delete_keys(self, spec, keys):
        for i in range(0, len(keys), 200):
            part = keys[i:i + 200]
            if len(spec.key) == 1:
                self.db.execute(f"DELETE FROM {q(spec.name)} WHERE {q(spec.key[0])} IN ({','.join('?' * len(part))})",
                                [k[0] for k in part])
            else:
                row = "(" + ",".join("?" * len(spec.key)) + ")"
                self.db.execute(f"DELETE FROM {q(spec.name)} WHERE ({qcols(spec.key)}) IN (VALUES {','.join([row] * len(part))})",
                                [x for k in part for x in k])

    def replace_all(self, spec, rows):
        self.db.execute(f"DELETE FROM {q(spec.name)}")
        self.upsert(spec, rows)

    def insert_rows(self, spec, rows):
        self.db.executemany(f"INSERT INTO {q(spec.name)}({qcols(spec.cols)}) VALUES({','.join('?' * len(spec.cols))})",
                            [tuple(to_sqlite(v) for v in r) for r in rows])

    def delete_copies(self, spec, items):
        """Delete n copies of each (row, n) of a keyless table."""
        cond = " AND ".join(f"{q(c)} IS ?" for c in spec.cols)
        for row, n in items:
            self.db.execute(f"DELETE FROM {q(spec.name)} WHERE rowid IN (SELECT rowid FROM {q(spec.name)} WHERE {cond} LIMIT ?)",
                            (*row, n))

    def save_triggers(self) -> list:
        """reverse-sync target: drop the triggers (they would re-derive stat_* rows that are synced
        from PostgreSQL anyway, and an upsert turns their INSERT OR IGNORE into a UNIQUE error)."""
        trig = self.all("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND sql IS NOT NULL")
        for name, _ in trig:
            self.db.execute(f"DROP TRIGGER IF EXISTS {q(name)}")
        return trig

    def restore_triggers(self, trig):
        for _, sql in trig:
            self.db.execute(sql)

    def begin(self):
        self.db.execute("BEGIN IMMEDIATE")

    def commit(self):
        self.db.execute("COMMIT")


# ---------------------------------------------------------------------------
# PostgreSQL side


def pg_url(args) -> str:
    if getattr(args, "pg", None):
        return args.pg
    env_file = getattr(args, "pg_env_file", None) or DEFAULT_PG_ENV
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    p = Path(env_file)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise MigrationError(f"no PostgreSQL URL: set DATABASE_URL or put DATABASE_URL=... in {env_file}")


class PGSide:
    kind = "pg"

    def __init__(self, url: str):
        if psycopg is None:
            raise MigrationError("psycopg is missing (apt install python3-psycopg)")
        try:
            self.db = psycopg.connect(url, autocommit=False, application_name="pg_migrate")
        except psycopg.OperationalError as e:
            # the message can contain the host but never the password; keep it short anyway
            raise MigrationError("cannot connect to PostgreSQL: " + str(e).splitlines()[0][:200]) from None
        self.db.execute("SET statement_timeout=0")
        self.db.commit()
        self.schema = self.one("SELECT current_schema()")[0]
        coll = self.one("SELECT datcollate FROM pg_database WHERE datname=current_database()")[0]
        # Key order must match SQLite's BINARY (= byte order): C/POSIX collation does, others need COLLATE "C".
        self.c_collation = coll in ("C", "POSIX")
        self.db.commit()
        self._types = None

    def one(self, sql, args=None):
        return self.db.execute(sql, args).fetchone()

    def all(self, sql, args=None):
        return self.db.execute(sql, args).fetchall()

    def close(self):
        try:
            self.db.rollback()
        finally:
            self.db.close()

    def lock(self) -> bool:
        ok = self.one("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,))[0]
        self.db.commit()
        return ok

    def types(self) -> dict:
        if self._types is None:
            rows = self.all("SELECT table_name,column_name,data_type,is_identity,identity_generation "
                            "FROM information_schema.columns WHERE table_schema=current_schema()")
            self.db.commit()
            t = {}
            for tbl, col, dt, ident, gen in rows:
                t.setdefault(tbl, {})[col] = (dt, ident == "YES" and gen == "ALWAYS")
            self._types = t
        return self._types

    def tables(self) -> set:
        return set(self.types())

    def columns(self, table) -> list:
        return list(self.types().get(table, {}))

    def order(self, spec) -> str:
        if self.c_collation:
            return qcols(spec.key)
        tt = self.types().get(spec.name, {})
        return ",".join(q(k) + (' COLLATE "C"' if tt.get(k, ("",))[0] in ("text", "character varying", "character") else "")
                        for k in spec.key)

    def count(self, table) -> int:
        n = self.one(f"SELECT count(*) FROM {q(table)}")[0]
        self.db.commit()
        return n

    def key_chunk(self, spec, after, limit, cols=None):
        cols = cols or spec.cols
        order = self.order(spec)
        if after is None:
            rows = self.all(f"SELECT {qcols(cols)} FROM {q(spec.name)} ORDER BY {order} LIMIT %s", (limit,))
        else:
            marks = ",".join(["%s"] * len(spec.key))
            if self.c_collation:
                cond = f"({qcols(spec.key)})>({marks})" if len(spec.key) > 1 else f"{q(spec.key[0])}>%s"
            else:
                cond = f"({order})>({marks})" if len(spec.key) > 1 else f"{order}>%s"
            rows = self.all(f"SELECT {qcols(cols)} FROM {q(spec.name)} WHERE {cond} ORDER BY {order} LIMIT %s",
                            (*after, limit))
        self.db.commit()
        return rows

    def versions(self, spec) -> dict:
        rows = self.all(f"SELECT {q(spec.key[0])},{q(spec.version)} FROM {q(spec.name)}")
        self.db.commit()
        return dict(rows)

    def light(self, spec, cols) -> dict:
        rows = self.all(f"SELECT {q(spec.key[0])},{qcols(cols)} FROM {q(spec.name)}")
        self.db.commit()
        return {r[0]: tuple(norm(x) for x in r[1:]) for r in rows}

    def _where_keys(self, spec, keys):
        if len(spec.key) == 1:
            return f"{q(spec.key[0])} = ANY(%s)", [[k[0] for k in keys]]
        row = "(" + ",".join(["%s"] * len(spec.key)) + ")"
        return f"({qcols(spec.key)}) IN (VALUES {','.join([row] * len(keys))})", [x for k in keys for x in k]

    def rows_by_keys(self, spec, keys, cols=None):
        if not keys:
            return []
        where, args = self._where_keys(spec, keys)
        rows = self.all(f"SELECT {qcols(cols or spec.cols)} FROM {q(spec.name)} WHERE {where}", args)
        self.db.commit()
        return rows

    def rows_by_groups(self, spec, groups):
        rows = self.all(f"SELECT {qcols(spec.cols)} FROM {q(spec.name)} WHERE {q(spec.group)} = ANY(%s)", (list(groups),))
        self.db.commit()
        return rows

    def group_counts(self, spec) -> dict:
        rows = self.all(f"SELECT {q(spec.group)},count(*) FROM {q(spec.name)} GROUP BY 1")
        self.db.commit()
        return dict(rows)

    def all_rows(self, spec):
        rows = self.all(f"SELECT {qcols(spec.cols)} FROM {q(spec.name)}")
        self.db.commit()
        return rows

    # --- writes: the caller owns the transaction (commit after bookkeeping) ---
    def overriding(self, spec) -> str:
        return " OVERRIDING SYSTEM VALUE" if spec.identity_always else ""

    def copy_rows(self, spec, rows):
        with self.db.cursor() as cur:
            with cur.copy(f"COPY {q(spec.name)} ({qcols(spec.cols)}) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row(r)

    def upsert(self, spec, rows):
        if not rows:
            return
        marks = ",".join(["%s"] * len(spec.cols))
        if spec.key:
            rest = [c for c in spec.cols if c not in spec.key]
            tail = (f" ON CONFLICT ({qcols(spec.key)}) DO UPDATE SET " + ",".join(f"{q(c)}=EXCLUDED.{q(c)}" for c in rest)
                    if rest else f" ON CONFLICT ({qcols(spec.key)}) DO NOTHING")
        else:
            tail = ""
        with self.db.cursor() as cur:
            cur.executemany(f"INSERT INTO {q(spec.name)} ({qcols(spec.cols)}){self.overriding(spec)} VALUES ({marks}){tail}",
                            [tuple(r) for r in rows])

    def delete_keys(self, spec, keys):
        for i in range(0, len(keys), 500):
            where, args = self._where_keys(spec, keys[i:i + 500])
            self.db.execute(f"DELETE FROM {q(spec.name)} WHERE {where}", args)

    def replace_all(self, spec, rows):
        self.db.execute(f"DELETE FROM {q(spec.name)}")
        if rows:
            self.copy_rows(spec, rows)

    def insert_rows(self, spec, rows):
        self.copy_rows(spec, rows)

    def delete_copies(self, spec, items):
        cond = " AND ".join(f"{q(c)} IS NOT DISTINCT FROM %s" for c in spec.cols)
        for row, n in items:
            self.db.execute(f"DELETE FROM {q(spec.name)} WHERE ctid IN (SELECT ctid FROM {q(spec.name)} WHERE {cond} LIMIT %s)",
                            (*row, n))

    def begin(self):
        pass  # psycopg opens the transaction on the first statement

    def commit(self):
        self.db.commit()

    # --- bookkeeping ---
    def ensure_meta(self):
        self.db.execute(f"CREATE SCHEMA IF NOT EXISTS {META}")
        self.db.execute(f"""CREATE TABLE IF NOT EXISTS {META}.progress (
            tbl text PRIMARY KEY, phase text NOT NULL, cursor text, rows bigint NOT NULL DEFAULT 0,
            bytes bigint NOT NULL DEFAULT 0, hwm bigint, started double precision, finished double precision,
            synced double precision)""")
        self.db.execute(f"CREATE TABLE IF NOT EXISTS {META}.touched (tbl text NOT NULL, k text NOT NULL, "
                        f"at double precision NOT NULL, PRIMARY KEY (tbl, k))")
        self.db.execute(f"CREATE TABLE IF NOT EXISTS {META}.meta (k text PRIMARY KEY, v text NOT NULL)")
        self.db.commit()

    def has_meta(self) -> bool:
        ok = self.one("SELECT to_regclass(%s) IS NOT NULL", (f"{META}.progress",))[0]
        self.db.commit()
        return ok

    def meta_get(self, k):
        if not self.has_meta():
            return None
        r = self.one(f"SELECT v FROM {META}.meta WHERE k=%s", (k,))
        self.db.commit()
        return r[0] if r else None

    def meta_set(self, k, v):  # inside the caller's transaction
        self.db.execute(f"INSERT INTO {META}.meta(k,v) VALUES(%s,%s) ON CONFLICT (k) DO UPDATE SET v=EXCLUDED.v", (k, str(v)))

    def progress(self, tbl):
        r = self.one(f"SELECT phase,cursor,rows,bytes,hwm FROM {META}.progress WHERE tbl=%s", (tbl,))
        self.db.commit()
        return dict(zip(("phase", "cursor", "rows", "bytes", "hwm"), r)) if r else None

    def set_progress(self, tbl, **f):  # inside the caller's transaction
        f.setdefault("phase", "copying")
        cols = list(f)
        self.db.execute(f"INSERT INTO {META}.progress(tbl,{','.join(cols)}) VALUES(%s,{','.join(['%s'] * len(cols))}) "
                        f"ON CONFLICT (tbl) DO UPDATE SET {','.join(f'{c}=EXCLUDED.{c}' for c in cols)}",
                        (tbl, *[f[c] for c in cols]))

    def touch(self, tbl, keys):  # inside the caller's transaction
        if not keys:
            return
        now = time.time()
        with self.db.cursor() as cur:
            cur.executemany(f"INSERT INTO {META}.touched(tbl,k,at) VALUES(%s,%s,%s) ON CONFLICT (tbl,k) DO UPDATE SET at=EXCLUDED.at",
                            [(tbl, json.dumps(list(k), ensure_ascii=False), now) for k in keys])

    def touched(self, tbl, since: float):
        rows = self.all(f"SELECT k FROM {META}.touched WHERE tbl=%s AND at>=%s", (tbl, since))
        self.db.commit()
        return [tuple(json.loads(r[0])) for r in rows]

    def drop_fks(self, tables) -> list:
        """The PG schema deliberately has no foreign keys (game/pg_schema.py; the game deletes
        children itself). A live copy/sync must not meet any (a receipt can arrive before its
        save), so any found on the game tables (added by hand) are dropped."""
        rows = self.all("SELECT conrelid::regclass::text, conname FROM pg_constraint WHERE contype='f' "
                        "AND connamespace=current_schema()::regnamespace AND conrelid::regclass::text = ANY(%s)", (list(tables),))
        for t, c in rows:
            self.db.execute(f"ALTER TABLE {q(t.strip(chr(34)))} DROP CONSTRAINT {q(c)}")
        self.db.commit()
        return [c for _, c in rows]

    def triggers(self, enable: bool, tables):
        self.db.rollback()  # also after a failed statement (called from finally blocks)
        for t in tables:
            self.db.execute(f"ALTER TABLE {q(t)} {'ENABLE' if enable else 'DISABLE'} TRIGGER USER")
        self.db.commit()


# ---------------------------------------------------------------------------
# The tool


class Migrator:
    def __init__(self, args, src_path=None, limits_path=None, readonly=True):
        self.args = args
        self.rep = Reporter(getattr(args, "json", False), getattr(args, "quiet", False))
        self.throttle = Throttle(getattr(args, "max_mb_per_s", 0) or 0, getattr(args, "pause_ms", 0) or 0)
        self.chunk_bytes = int((getattr(args, "chunk_mb", 8) or 8) * 1e6)
        self.pg = PGSide(pg_url(args))
        self.sqlite_path = src_path or args.sqlite
        self.limits_path = limits_path if limits_path is not None else (args.limits or limits_of(self.sqlite_path))
        self.sides = {"main": SQLiteSide(self.sqlite_path, readonly=readonly)}
        if self.limits_path and Path(self.limits_path).exists():
            self.sides["limits"] = SQLiteSide(self.limits_path, readonly=readonly)
        self.specs = []

    def close(self):
        for s in self.sides.values():
            s.close()
        self.pg.close()

    # --- setup ---
    def load_specs(self, need_pg_tables=True):
        schema = load_schema(getattr(self.args, "schema_module", None))
        specs = specs_from(schema)
        only = set(self.args.tables.split(",")) if getattr(self.args, "tables", None) else None
        pgt = self.pg.types()
        out = []
        for s in specs:
            if only and s.name not in only:
                continue
            side = self.sides.get(s.db)
            if side is None:
                self.rep.event("warn", table=s.name, msg=f"no {s.db} SQLite file: skipped")
                continue
            if s.name not in side.tables():
                self.rep.event("warn", table=s.name, msg="not in SQLite: skipped")
                continue
            if need_pg_tables and s.name not in pgt:
                raise MigrationError(f"table {s.name} missing in PostgreSQL: run init")
            scols = side.columns(s.name)
            pcols = list(pgt.get(s.name, {}))
            missing = [c for c in scols if pcols and c not in pcols]
            if missing:
                raise MigrationError(f"{s.name}: SQLite columns {missing} have no PostgreSQL column (data would be lost)")
            s.cols = tuple(c for c in scols if not pcols or c in pcols)
            if not s.key:
                s.key = self._pg_key(s.name)
                s.strategy = "replace" if not s.key else s.strategy if s.strategy != "replace" else "diff"
            bad = [k for k in s.key if k not in s.cols]
            if bad:
                raise MigrationError(f"{s.name}: key columns {bad} are not SQLite columns")
            s.identity_always = any(pgt.get(s.name, {}).get(c, ("", False))[1] for c in s.cols)
            out.append(s)
        self.specs = out
        return out

    def _pg_key(self, table):
        """Columns of the table's primary key (else its first unique index) in PostgreSQL."""
        idx = self.pg.all("""SELECT i.indkey::int2[] FROM pg_index i WHERE i.indrelid=to_regclass(%s)
                             AND (i.indisprimary OR i.indisunique) ORDER BY i.indisprimary DESC, i.indexrelid LIMIT 1""", (q(table),))
        if not idx:
            self.pg.db.commit()
            return ()
        names = dict(self.pg.all("SELECT attnum,attname FROM pg_attribute WHERE attrelid=to_regclass(%s) AND attnum>0", (q(table),)))
        self.pg.db.commit()
        return tuple(names[n] for n in idx[0][0])

    def guard_live(self):
        if self.pg.meta_get("cutover_at") and not getattr(self.args, "force", False):
            raise MigrationError("PostgreSQL is the live database since cutover (mark-cutover): refusing to overwrite it. "
                                 "Use reverse-sync for a rollback.")

    def get_lock(self):
        if not self.pg.lock():
            raise MigrationError("another pg_migrate is running (advisory lock held)")

    # --- init ---
    def init(self):
        """Tables, keys and TOAST/autovacuum tuning. Secondary indexes come after the copy;
        the stat_* triggers and the schema version at cutover (finalize): a live copy
        would double-count through them. There are no foreign keys, by design."""
        schema = load_schema(getattr(self.args, "schema_module", None))
        ensure_stages(schema, self.pg.db, ("tables", "tuning"))
        self.pg._types = None
        self.pg.ensure_meta()
        specs = self.load_specs()
        self.rep.event("init", tables=len(specs), collation_c=self.pg.c_collation)
        return dict(tables=len(specs))

    # --- copy ---
    def copy(self):
        self.guard_live()
        self.get_lock()
        self.pg.ensure_meta()
        specs = self.load_specs()
        restart = getattr(self.args, "restart", False)
        total_est = sum(Path(p).stat().st_size for p in self._files())
        t0 = time.monotonic()
        done_bytes = 0
        summary = {}
        self.pg.db.execute("SET synchronous_commit=off")  # durable at the end (see finish()); WAL still written
        self.pg.db.commit()
        self.pg.drop_fks([s.name for s in specs])
        self.pg.triggers(False, [s.name for s in specs])
        try:
            for s in specs:
                st = self.copy_table(s, restart, lambda n: None)
                done_bytes += st["bytes"]
                summary[s.name] = st
                el = time.monotonic() - t0
                rate = done_bytes / el if el > 0 else 0
                self.rep.event("progress", force=True, table=s.name, phase="copied", rows=st["rows"],
                               mb=round(st["bytes"] / 1e6, 1), total_mb=round(done_bytes / 1e6, 1),
                               mb_s=round(rate / 1e6, 2), eta_s=round(max(0, total_est - done_bytes) / rate) if rate else None)
        finally:
            self.pg.triggers(True, [s.name for s in specs])
            self.finish()
        ti = time.monotonic()
        ensure_stages(load_schema(getattr(self.args, "schema_module", None)), self.pg.db, ("indexes",))
        self.maintain(specs)
        self.rep.event("progress", force=True, phase="indexes+vacuum", seconds=round(time.monotonic() - ti, 1))
        el = time.monotonic() - t0
        out = dict(seconds=round(el, 1), mb=round(done_bytes / 1e6, 1), mb_s=round(done_bytes / 1e6 / el, 2) if el else 0,
                   rows=sum(v["rows"] for v in summary.values()), throttled_s=round(self.throttle.slept, 1))
        self.rep.event("copy-done", **out)
        return out

    def _files(self):
        out = []
        for p in (self.sqlite_path, self.limits_path):
            if p:
                for suf in ("", "-wal"):
                    if Path(str(p) + suf).exists():
                        out.append(str(p) + suf)
        return out

    def copy_table(self, s, restart, _cb):
        pg, side = self.pg, self.sides[s.db]
        prog = pg.progress(s.name)
        if prog and prog["phase"] in ("copied", "synced") and not restart:
            return dict(rows=0, bytes=0, skipped=True)
        if prog is None or restart:
            n = pg.one(f"SELECT EXISTS(SELECT 1 FROM {q(s.name)})")[0]
            if n and not restart and not getattr(self.args, "force", False):
                pg.db.rollback()
                raise MigrationError(f"{s.name}: PostgreSQL table is not empty and has no copy progress; "
                                     f"use --restart to truncate it")
            pg.db.execute(f"TRUNCATE {q(s.name)}")
            pg.set_progress(s.name, phase="copying", cursor=None, rows=0, bytes=0, hwm=None, started=time.time(), finished=None)
            pg.db.execute(f"DELETE FROM {META}.touched WHERE tbl=%s", (s.name,))
            pg.commit()
            prog = dict(phase="copying", cursor=None, rows=0, bytes=0, hwm=None)
        use_rowid = side.has_rowid(s.name)
        cursor = json.loads(prog["cursor"]) if prog["cursor"] else None
        rows_done, bytes_done = prog["rows"] or 0, prog["bytes"] or 0
        top = side.max_rowid(s.name) if use_rowid else 0
        limit, t0, got_bytes = 4, time.monotonic(), 0
        while True:
            t_read = time.monotonic()
            if use_rowid:
                raw = side.rowid_chunk(s, cursor or 0, limit)
                rows = [r[1:] for r in raw]
                nxt = raw[-1][0] if raw else cursor
            else:
                rows = side.key_chunk(s, tuple(cursor) if cursor else None, limit)
                nxt = list(s.keyof(rows[-1])) if rows else cursor
            read_ms = (time.monotonic() - t_read) * 1000
            if not rows:
                break
            nb = sum(row_bytes(r) for r in rows)
            try:
                pg.copy_rows(s, rows)
            except (pgerrors.UniqueViolation, pgerrors.ExclusionViolation):
                pg.db.rollback()   # a key moved to a later rowid meanwhile: upsert this chunk instead
                pg.upsert(s, rows)
            rows_done += len(rows)
            bytes_done += nb
            got_bytes += nb
            pg.set_progress(s.name, phase="copying", cursor=json.dumps(nxt), rows=rows_done, bytes=bytes_done,
                            hwm=nxt if use_rowid else None)
            pg.commit()
            cursor = nxt
            self.throttle.spend(nb)
            # aim each chunk at chunk_bytes, and keep every SQLite read short (< ~250 ms)
            avg = nb / len(rows)
            want = max(1, int(self.chunk_bytes / max(avg, 1)))
            if read_ms > 250:
                want = min(want, max(1, limit // 2))
            limit = max(1, min(20000, want, limit * 4))
            el = time.monotonic() - t0
            frac = (cursor / top) if use_rowid and top else None
            self.rep.event("progress", table=s.name, rows=rows_done, mb=round(bytes_done / 1e6, 1),
                           mb_s=round(got_bytes / 1e6 / el, 2) if el else None,
                           pct=round(100 * min(frac, 1), 1) if frac is not None else None,
                           eta_s=round(el / frac - el) if frac else None, chunk=limit)
        pg.set_progress(s.name, phase="copied", cursor=json.dumps(cursor), rows=rows_done, bytes=bytes_done,
                        hwm=cursor if use_rowid else None, finished=time.time())
        pg.commit()
        return dict(rows=rows_done, bytes=bytes_done)

    def finish(self):
        """Make every asynchronously committed chunk durable: one synchronous commit flushes the WAL."""
        self.pg.db.rollback()
        self.pg.ensure_meta()
        self.pg.db.execute("SET synchronous_commit=on")
        self.pg.meta_set("last_run", time.time())
        self.pg.commit()

    def maintain(self, specs):
        """VACUUM small/medium tables (visibility map -> index-only group counts), ANALYZE all."""
        self.pg.db.autocommit = True
        try:
            if getattr(self.args, "max_mb_per_s", 0):
                # a manual VACUUM is unthrottled by default: pace it like autovacuum so the game keeps the disk
                self.pg.db.execute("SET vacuum_cost_delay = '2ms'")
                self.pg.db.execute("SET vacuum_cost_limit = 400")
            for s in specs:
                self.pg.db.execute(f"{'ANALYZE' if s.name == 'sessions' else 'VACUUM (ANALYZE)'} {q(s.name)}")
        finally:
            self.pg.db.autocommit = False

    # --- sync (source -> target) ---
    def sync(self, reverse=False, target=None):
        """Bring the target up to date. Forward: live SQLite -> PG. Reverse: PG -> a SQLite copy."""
        if not reverse:
            self.guard_live()
        self.get_lock()
        self.pg.ensure_meta() if not reverse else None
        specs = self.load_specs()
        t0 = time.monotonic()
        stats = {}
        if not reverse:
            for s in specs:
                p = self.pg.progress(s.name)
                if not p or p["phase"] not in ("copied", "synced"):
                    raise MigrationError(f"{s.name}: not copied yet (run copy first)")
            self.pg.db.execute("SET synchronous_commit=off")
            self.pg.commit()
            self.pg.drop_fks([s.name for s in specs])
            self.pg.triggers(False, [s.name for s in specs])
        dirty = set()
        gone_saves = []
        try:
            for s in specs:
                ts = time.monotonic()
                if reverse:
                    src, dst = self.pg, target[s.db]
                else:
                    src, dst = self.sides[s.db], self.pg
                if s.strategy == "revision":
                    st = self.sync_revision(s, src, dst, reverse)
                    dirty = st.pop("dirty")
                    gone_saves.append((s, dst, st.pop("gone")))
                elif s.strategy == "append":
                    st = self.sync_append(s, src, dst, reverse, dirty)
                elif s.strategy == "diff":
                    st = self.sync_diff(s, src, dst, reverse)
                else:
                    st = self.sync_replace(s, src, dst, reverse)
                st["ms"] = round((time.monotonic() - ts) * 1000)
                stats[s.name] = st
                if not reverse:
                    self.pg.set_progress(s.name, phase="synced", synced=time.time())
                    self.pg.commit()
                self.rep.event("progress", force=True, table=s.name, **st)
            # deleted saves last, after their receipts/archive rows (children first, like the game)
            for s, dst, gone in gone_saves:
                for i in range(0, len(gone), 500):
                    self._write(s, dst, reverse, deletes=gone[i:i + 500], touch=gone[i:i + 500])
        finally:
            if not reverse:
                self.pg.triggers(True, [s.name for s in specs])
                self.finish()
        el = time.monotonic() - t0
        out = dict(seconds=round(el, 2),
                   upserted=sum(v.get("upserted", 0) for v in stats.values()),
                   deleted=sum(v.get("deleted", 0) for v in stats.values()),
                   mb=round(sum(v.get("bytes", 0) for v in stats.values()) / 1e6, 1),
                   tables={k: v for k, v in stats.items() if v.get("upserted") or v.get("deleted")})
        self.rep.event("sync-done" if not reverse else "reverse-sync-done", **out)
        return out

    def _write(self, s, dst, reverse, upserts=(), deletes=(), touch=(), replace=None):
        dst.begin()
        if replace is not None:
            dst.replace_all(s, replace)
        if deletes:
            dst.delete_keys(s, list(deletes))
        if upserts:
            dst.upsert(s, list(upserts))
        if not reverse and touch:
            self.pg.touch(s.name, list(touch))
        dst.commit()

    def _fetch_write(self, s, src, dst, reverse, keys, touch=True):
        """Fetch rows by key from the source in byte-bounded batches and upsert them."""
        done = nbytes = 0
        batch = 16 if s.strategy == "revision" else 400
        keys = list(keys)
        i = 0
        while i < len(keys):
            part = keys[i:i + batch]
            rows = src.rows_by_keys(s, part)
            nb = sum(row_bytes(r) for r in rows)
            self._write(s, dst, reverse, upserts=rows, touch=part if touch else ())
            done += len(rows)
            nbytes += nb
            i += len(part)
            self.throttle.spend(nb)
            if rows:
                avg = nb / len(rows)
                batch = max(1, min(500, int(self.chunk_bytes / max(avg, 1))))
        return done, nbytes

    def _repairs(self, s, reverse):
        """Keys (or saves) a verify found different although their version/count matched."""
        return [] if reverse else [k[0] for k in self.pg.touched(s.name + ":repair", 0)]

    def _repaired(self, s, reverse):
        if not reverse:
            self.pg.db.execute(f"DELETE FROM {META}.touched WHERE tbl=%s", (s.name + ":repair",))
            self.pg.commit()

    def sync_revision(self, s, src, dst, reverse):
        sv, dv = src.versions(s), dst.versions(s)
        changed = [(k,) for k, v in sv.items() if dv.get(k) != v]
        again = set(self._repairs(s, reverse)) - {k[0] for k in changed}
        changed += [(k,) for k in again if k in sv]
        gone = [(k,) for k in dv if k not in sv]
        n, nb = self._fetch_write(s, src, dst, reverse, changed)
        self._repaired(s, reverse)
        return dict(upserted=n, deleted=len(gone), bytes=nb, rows=len(sv), gone=gone,
                    dirty={k[0] for k in changed} | {k[0] for k in gone})

    def sync_append(self, s, src, dst, reverse, dirty):
        up = nb = 0
        groups = set()
        if not reverse:
            # 1) new rows past the rowid watermark (ON CONFLICT DO UPDATE also fixes a re-used key)
            side = src
            prog = self.pg.progress(s.name)
            hwm = prog["hwm"] or 0
            limit = 500
            while True:
                raw = side.rowid_chunk(s, hwm, limit)
                if not raw:
                    break
                rows = [r[1:] for r in raw]
                gi = s.cols.index(s.group)
                dst.upsert(s, rows)
                self.pg.touch(s.name, {(norm(r[gi]),) for r in rows})
                hwm = raw[-1][0]
                self.pg.set_progress(s.name, phase="synced", hwm=hwm)
                self.pg.commit()
                b = sum(row_bytes(r) for r in rows)
                up += len(rows)
                nb += b
                self.throttle.spend(b)
                limit = max(50, min(5000, int(self.chunk_bytes / max(b / len(rows), 1))))
        else:
            groups |= dirty
        groups |= set(self._repairs(s, reverse))
        # 2) per-save counts find deletions (prune, erase) and anything the watermark missed
        sc, dc = src.group_counts(s), dst.group_counts(s)
        groups |= {g for g, c in sc.items() if dc.get(g) != c}
        groups |= {g for g in dc if g not in sc}
        deleted = 0
        groups = sorted(groups)
        for i in range(0, len(groups), 100):
            part = groups[i:i + 100]
            srows = {s.keyof(r): r for r in src.rows_by_groups(s, part)}
            drows = {s.keyof(r): r for r in dst.rows_by_groups(s, part)}
            ups = [r for k, r in srows.items() if k not in drows or tuple(map(norm, drows[k])) != tuple(map(norm, r))]
            dels = [k for k in drows if k not in srows]
            if ups or dels:
                self._write(s, dst, reverse, upserts=ups, deletes=dels, touch=[(g,) for g in part])
            up += len(ups)
            deleted += len(dels)
            b = sum(row_bytes(r) for r in srows.values())
            nb += b
            self.throttle.spend(b)
        self._repaired(s, reverse)
        return dict(upserted=up, deleted=deleted, bytes=nb, groups_checked=len(groups))

    def merge(self, s, a, b, cols=None, chunk=5000):
        """Walk two key-ordered streams; yield (kind, key, row_a, row_b), kind in same/changed/only_a/only_b."""
        def stream(side):
            last = None
            prev = None
            while True:
                rows = side.key_chunk(s, last, chunk, cols)
                for r in rows:
                    k = s.keyof(r) if cols is None else tuple(norm(r[i]) for i in range(len(s.key)))
                    if prev is not None and not prev < k:
                        raise MigrationError(f"{s.name}: key order differs between SQLite and PostgreSQL "
                                             f"(collation?): cannot merge")
                    prev = k
                    yield k, r
                if len(rows) < chunk:
                    return
                last = prev
        ia, ib = stream(a), stream(b)
        ea, eb = next(ia, None), next(ib, None)
        while ea is not None or eb is not None:
            if eb is None or (ea is not None and ea[0] < eb[0]):
                yield "only_a", ea[0], ea[1], None
                ea = next(ia, None)
            elif ea is None or eb[0] < ea[0]:
                yield "only_b", eb[0], None, eb[1]
                eb = next(ib, None)
            else:
                same = tuple(map(norm, ea[1])) == tuple(map(norm, eb[1]))
                yield ("same" if same else "changed"), ea[0], ea[1], eb[1]
                ea, eb = next(ia, None), next(ib, None)

    def sync_diff(self, s, src, dst, reverse):
        ups, dels, n = [], [], 0
        up = de = nb = 0
        for kind, k, rs, rd in self.merge(s, src, dst):
            n += 1
            if kind in ("only_a", "changed"):
                ups.append(rs)
                nb += row_bytes(rs)
            elif kind == "only_b":
                dels.append(k)
            if len(ups) + len(dels) >= 1000:
                dels = self._confirm_gone(s, src, dels)
                self._write(s, dst, reverse, upserts=ups, deletes=dels, touch=[s.keyof(r) for r in ups] + dels)
                up += len(ups)
                de += len(dels)
                ups, dels = [], []
        dels = self._confirm_gone(s, src, dels)
        if ups or dels:
            self._write(s, dst, reverse, upserts=ups, deletes=dels, touch=[s.keyof(r) for r in ups] + dels)
        return dict(upserted=up + len(ups), deleted=de + len(dels), bytes=nb, rows=n)

    def _confirm_gone(self, s, src, keys):
        """Never delete on the merge's word alone: re-check the keys in the source."""
        if not keys:
            return keys
        still = set()
        for i in range(0, len(keys), 400):
            still |= {s.keyof(r) for r in src.rows_by_keys(s, keys[i:i + 400])}
        return [k for k in keys if k not in still]

    def sync_replace(self, s, src, dst, reverse):
        """Keyless tables (hits): a multiset diff. Only the missing copies are inserted and the
        surplus copies deleted, so a busy rate-limit table costs a few rows per sync."""
        from collections import Counter
        canon = lambda r: tuple(norm(v) for v in r)
        a = Counter(canon(r) for r in src.all_rows(s))
        b = Counter(canon(r) for r in dst.all_rows(s))
        add, drop = a - b, b - a
        if add or drop:
            dst.begin()
            dst.delete_copies(s, list(drop.items()))
            ins = [r for r, n in add.items() for _ in range(n)]
            if ins:
                dst.insert_rows(s, ins)
            dst.commit()
        return dict(upserted=sum(add.values()), deleted=sum(drop.values()), bytes=0, rows=sum(a.values()))

    # --- verify ---
    def verify(self):
        """Compare SQLite and PostgreSQL. Full: every row (sessions: sha256 of the save per sid).
        --fast: counts, (sid, revision) of every save, and the rows written by a sync since the
        last full verify. --live: while the game runs, saves whose revision moved are 'in flight'
        and other tables' differences are expected; they are queued so the next sync re-checks them."""
        fast, live = getattr(self.args, "fast", False), getattr(self.args, "live", False)
        self.get_lock()
        self.pg.ensure_meta()
        specs = self.load_specs()
        started = time.time()
        t0 = time.monotonic()
        since = float(self.pg.meta_get("verified_at") or 0) if fast else 0.0
        bad = inflight = 0
        tables = {}
        for s in specs:
            ts = time.monotonic()
            side = self.sides[s.db]
            moving = set()
            if s.strategy == "revision":
                r, keys, moving = self.verify_sessions(s, side, fast, since)
            elif s.strategy == "append" and fast and since:
                r, keys = self.verify_groups(s, side, since)
            elif s.strategy == "replace":
                r, keys = self.verify_replace(s, side)
            else:
                r, keys = self.verify_merge(s, side)
            if live and s.strategy != "revision":
                moving, keys = set(keys), []
            r["mismatch"] = len(keys) + (1 if not keys and not moving and r["sqlite_rows"] != r["pg_rows"] else 0)
            r["in_flight"] = len(moving)
            r["ids"] = [short(k) for k in keys[:10]]
            r["ms"] = round((time.monotonic() - ts) * 1000)
            bad += r["mismatch"]
            inflight += r["in_flight"]
            tables[s.name] = r
            # queue for the next sync: rows whose version/count looks equal but whose content differs
            if s.strategy in ("revision", "append"):
                rk = set(keys) | (set() if s.strategy == "revision" else set(moving))
                groups = {(k[0],) if s.strategy == "revision" else (s.group_of(k),) if len(k) > 1 else k for k in rk}
                if groups:
                    self.pg.touch(s.name + ":repair", sorted(groups))
                    self.pg.commit()
            self.rep.event("verify", force=True, table=s.name, **r)
        ok = bad == 0
        if ok and not fast:
            # a passing full verify is the baseline of the next fast one (rows a sync touches after `started`)
            self.pg.meta_set("verified_at", started)
            self.pg.commit()
        out = dict(ok=ok, mode="fast" if fast else "live" if live else "full", mismatches=bad, in_flight=inflight,
                   seconds=round(time.monotonic() - t0, 2), mb=round(self.throttle.bytes / 1e6, 1),
                   bad_tables=sorted(k for k, v in tables.items() if v["mismatch"]))
        self.rep.event("verify-done", **out)
        return out

    @staticmethod
    def _result(count_s, count_p, checked):
        return dict(sqlite_rows=count_s, pg_rows=count_p, checked=checked)

    def verify_sessions(self, s, side, fast, since):
        k = s.key[0]
        others = [c for c in s.cols if c not in (k, "state")]
        # (revision, updated_at) of every save: SQLite reads them from the covering index
        # stat_sessions_seen, never from the table (whose rows drag the saves' overflow pages)
        cheap = [c for c in others if c in (s.version, "updated_at")]
        sl, pl = side.light(s, cheap), self.pg.light(s, cheap)
        vi = cheap.index(s.version)
        bad = {x for x in sl if x not in pl or pl[x] != sl[x]} | {x for x in pl if x not in sl}
        moving = {x for x in bad if x in sl and x in pl and sl[x][vi] != pl[x][vi]}
        if self.args.live:
            bad -= moving
        else:
            moving = set()
        keys = [t[0] for t in self.pg.touched(s.name, since)] if fast and since else list(sl)
        keys = [x for x in keys if x in sl and x in pl and x not in moving]
        diff, moved = self._session_sums(s, side, keys, others)
        if self.args.live:
            # the save was written between the (sid, revision) pass and the hash pass: in flight
            moving |= set(moved)
            bad |= set(diff) - set(moved)
        else:
            bad |= set(diff)
        return self._result(len(sl), len(pl), len(keys)), [(x,) for x in sorted(bad)], {(x,) for x in moving}

    def _session_sums(self, s, side, keys, others):
        """sha256(state) + the other columns, SQLite (in Python) vs PostgreSQL (in the server)."""
        k = s.key[0]
        bad, moved = [], []
        vi = others.index(s.version)
        cols = [k] + others + ["state"]
        i, batch = 0, 16
        while i < len(keys):
            part = keys[i:i + batch]
            srows = side.all(f"SELECT {qcols(cols)} FROM {q(s.name)} WHERE {q(k)} IN ({','.join('?' * len(part))})", part)
            nb = sum(row_bytes(r) for r in srows)
            smap = {r[0]: (tuple(map(norm, r[1:-1])), sha_text(r[-1])) for r in srows}
            prow = self.pg.all(f"SELECT {q(k)},{qcols(others)},encode(sha256(convert_to({q('state')},'UTF8')),'hex') "
                               f"FROM {q(s.name)} WHERE {q(k)} = ANY(%s)", (part,))
            self.pg.db.commit()
            pmap = {r[0]: (tuple(map(norm, r[1:-1])), r[-1]) for r in prow}
            for x in part:
                if smap.get(x) != pmap.get(x):
                    bad.append(x)
                    if x in smap and x in pmap and smap[x][0][vi] != pmap[x][0][vi]:
                        moved.append(x)
            self.throttle.spend(nb)
            i += len(part)
            if srows:
                batch = max(1, min(256, int(self.chunk_bytes / max(nb / len(srows), 1))))
        return bad, moved

    def verify_groups(self, s, side, since):
        """Fast mode for append tables: per-save counts of every save, and every row of the
        saves a sync touched since the baseline."""
        sc, pc = side.group_counts(s), self.pg.group_counts(s)
        bad = {(g,) for g in set(sc) | set(pc) if sc.get(g) != pc.get(g)}
        groups = [t[0] for t in self.pg.touched(s.name, since)]
        for i in range(0, len(groups), 100):
            part = groups[i:i + 100]
            sr = {s.keyof(r): tuple(map(norm, r)) for r in side.rows_by_groups(s, part)}
            pr = {s.keyof(r): tuple(map(norm, r)) for r in self.pg.rows_by_groups(s, part)}
            bad |= {key for key in set(sr) | set(pr) if sr.get(key) != pr.get(key)}
        return self._result(sum(sc.values()), sum(pc.values()), len(groups)), sorted(bad)

    def verify_merge(self, s, side):
        n_s = n_p = nb = 0
        bad = []
        for kind, k, rs, rp in self.merge(s, side, self.pg):
            n_s += rs is not None
            n_p += rp is not None
            if kind != "same":
                bad.append(k)
            if rs is not None:
                nb += row_bytes(rs)
                if nb > 1_000_000:
                    self.throttle.spend(nb)
                    nb = 0
        self.throttle.spend(nb)
        return self._result(n_s, n_p, n_s), bad

    def verify_replace(self, s, side):
        key = lambda r: tuple((v is None, v if v is not None else 0) for v in map(norm, r))
        a = sorted(map(key, side.all_rows(s)))
        b = sorted(map(key, self.pg.all_rows(s)))
        return self._result(len(a), len(b), len(a)), ([] if a == b else [("*",)])

    # --- sequences, cutover mark ---
    def sqlite_sequences(self) -> dict:
        side = self.sides["main"]
        if "sqlite_sequence" not in side.tables():
            return {}
        return {n: int(v or 0) for n, v in side.all("SELECT name,seq FROM sqlite_sequence")}

    def reset_seq(self):
        """Identities continue after max(id) and after SQLite's sqlite_sequence (AUTOINCREMENT
        never reuses the id of a deleted row)."""
        self.get_lock()
        schema = load_schema(getattr(self.args, "schema_module", None))
        floors = self.sqlite_sequences()
        fn = getattr(schema, "reset_sequences", None)
        if callable(fn):
            nxt = fn(self.pg.db, floors)
            how = "pg_schema.reset_sequences"
        else:
            how, nxt = "generic", {}
            rows = self.pg.all("""SELECT c.table_name,c.column_name,pg_get_serial_sequence(quote_ident(c.table_name),c.column_name)
                                  FROM information_schema.columns c WHERE c.table_schema=current_schema()
                                  AND pg_get_serial_sequence(quote_ident(c.table_name),c.column_name) IS NOT NULL""")
            for t, c, seq in rows:
                top = max(self.pg.one(f"SELECT COALESCE(max({q(c)}),0) FROM {q(t)}")[0], floors.get(t, 0))
                self.pg.db.execute("SELECT setval(%s,%s,%s)", (seq, max(top, 1), top > 0))
                nxt[t] = top + 1
        self.pg.db.commit()
        self.rep.event("reset-seq", how=how, tables=len(nxt or {}))
        return dict(how=how, next_ids=nxt or {})

    def finalize(self):
        """Cutover, after the final sync + verify: the stat_* triggers (no foreign keys, by design),
        the schema version (the game's start-up ensure() is then a no-op), and the sequences."""
        self.get_lock()
        schema = load_schema(getattr(self.args, "schema_module", None))
        t0 = time.monotonic()
        ensure_stages(schema, self.pg.db, None)
        res = self.reset_seq()
        out = dict(seconds=round(time.monotonic() - t0, 2), **res)
        self.rep.event("finalize", seconds=out["seconds"])
        return out

    def mark_cutover(self):
        self.pg.ensure_meta()
        self.pg.meta_set("cutover_at", time.time())
        self.pg.commit()
        self.rep.event("cutover-marked")
        return dict(ok=True)

    def unmark_cutover(self):
        """Only for a cutover that never served a request on PostgreSQL (cutover.sh checks that PG
        still equals the SQLite file first): allows sync again for a new attempt."""
        self.pg.ensure_meta()
        self.pg.db.execute(f"DELETE FROM {META}.meta WHERE k='cutover_at'")
        self.pg.commit()
        self.rep.event("cutover-unmarked")
        return dict(ok=True)

    def status(self):
        self.pg.ensure_meta()
        rows = self.pg.all(f"SELECT tbl,phase,rows,bytes,hwm,finished,synced FROM {META}.progress ORDER BY tbl")
        self.pg.db.commit()
        out = dict(tables={r[0]: dict(phase=r[1], rows=r[2], mb=round((r[3] or 0) / 1e6, 1), hwm=r[4]) for r in rows},
                   cutover_at=self.pg.meta_get("cutover_at"), verified_at=self.pg.meta_get("verified_at"))
        self.rep.event("status", **out)
        return out


def limits_of(db_path: str) -> str:
    p = Path(db_path)
    return str(p.with_name(p.stem + "-limits.sqlite3"))


def backup_sqlite(src: str, dst: str):
    """Consistent copy of a SQLite file (online backup API), into a new file."""
    if Path(dst).exists():
        raise MigrationError(f"{dst} already exists: refusing to overwrite")
    s = sqlite3.connect("file:" + quote(str(Path(src).resolve()).replace("\\", "/")) + "?mode=ro", uri=True)
    d = sqlite3.connect(dst)
    try:
        s.backup(d, pages=4096, sleep=0.005)
    finally:
        d.close()
        s.close()


def reverse_sync(args, rep):
    """Rollback: PG (live since cutover) -> a NEW SQLite file made from the cutover snapshot.
    --from-backup B --out NEW: NEW is created with SQLite's backup API from B (B is only read).
    --out NEW --copy-ready: NEW is already a fresh copy of the snapshot (rollback.sh copies it)."""
    out = Path(args.out)
    live = Path(args.sqlite).resolve() if args.sqlite else None
    if live and out.resolve() == live:
        raise MigrationError("--out must not be the live SQLite file: reverse-sync only writes a copy")
    lim_out = args.limits_out
    if args.copy_ready:
        if not out.exists():
            raise MigrationError(f"{out} does not exist")
        if lim_out and not Path(lim_out).exists():
            lim_out = None
    else:
        if not args.from_backup:
            raise MigrationError("reverse-sync needs --from-backup (or --copy-ready)")
        bk = Path(args.from_backup)
        if out.resolve() == bk.resolve():
            raise MigrationError("--out must differ from the backup")
        backup_sqlite(str(bk), str(out))
        lim_bk = args.from_limits_backup or limits_of(str(bk))
        if Path(lim_bk).exists():
            lim_out = lim_out or limits_of(str(out))
            backup_sqlite(lim_bk, lim_out)
        else:
            lim_out = None
    m = Migrator(args, src_path=str(out), limits_path=lim_out or "", readonly=False)
    try:
        saved = {k: side.save_triggers() for k, side in m.sides.items()}
        res = m.sync(reverse=True, target=m.sides)
        for k, side in m.sides.items():
            side.restore_triggers(saved[k])
        for side in m.sides.values():  # one self-contained file: no -wal next to it
            mode = side.db.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            if str(mode).lower() != "delete":
                raise MigrationError(f"{side.path}: could not leave WAL mode ({mode})")
        res["out"] = str(out)
        res["limits_out"] = lim_out
        return res
    finally:
        m.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["init", "copy", "sync", "verify", "reset-seq", "finalize", "mark-cutover", "unmark-cutover", "reverse-sync", "status"])
    ap.add_argument("--sqlite", default=DEFAULT_DB, help="game database (default GAME_DB or %(default)s)")
    ap.add_argument("--limits", default=None, help="limits database (default: <game>-limits.sqlite3 next to it)")
    ap.add_argument("--pg", default=None, help=argparse.SUPPRESS)  # tests only: prefer DATABASE_URL / --pg-env-file
    ap.add_argument("--pg-env-file", default=DEFAULT_PG_ENV)
    ap.add_argument("--schema-module", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--schema-file", default=None, help="path of game/pg_schema.py (default: ../game/pg_schema.py next to this script)")
    ap.add_argument("--tables", default=None, help="comma-separated subset (debugging)")
    ap.add_argument("--max-mb-per-s", type=float, default=0, help="read throttle (0 = none)")
    ap.add_argument("--pause-ms", type=float, default=0, help="sleep between chunks")
    ap.add_argument("--chunk-mb", type=float, default=8, help="target bytes per chunk")
    ap.add_argument("--restart", action="store_true", help="copy: truncate and copy again from scratch")
    ap.add_argument("--force", action="store_true", help="ignore the cutover guard / non-empty target (rehearsal only)")
    ap.add_argument("--fast", action="store_true", help="verify: counts + rows changed since the last full verify")
    ap.add_argument("--live", action="store_true", help="verify while the game runs: changed saves are 'in flight'")
    ap.add_argument("--from-backup", help="reverse-sync: the SQLite backup taken at cutover")
    ap.add_argument("--from-limits-backup", help="reverse-sync: the limits backup (default next to --from-backup)")
    ap.add_argument("--out", help="reverse-sync: NEW SQLite file to create")
    ap.add_argument("--limits-out", help="reverse-sync: NEW limits file (default next to --out)")
    ap.add_argument("--copy-ready", action="store_true", help="reverse-sync: --out already is a fresh copy of the snapshot")
    ap.add_argument("--json", action="store_true", help="JSON lines on stdout (progress, eta, result)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    global SCHEMA_FILE
    SCHEMA_FILE = args.schema_file
    rep = Reporter(args.json, args.quiet)
    try:
        if args.command == "reverse-sync":
            if not args.out:
                raise MigrationError("reverse-sync needs --out (and --from-backup or --copy-ready)")
            res = reverse_sync(args, rep)
            ok = True
        else:
            m = Migrator(args)
            try:
                fn = {"init": m.init, "copy": m.copy, "sync": m.sync, "verify": m.verify, "reset-seq": m.reset_seq, "finalize": m.finalize,
                      "mark-cutover": m.mark_cutover, "unmark-cutover": m.unmark_cutover, "status": m.status}[args.command]
                res = fn()
            finally:
                m.close()
            ok = res.get("ok", True) if isinstance(res, dict) else True
        rep.event("result", command=args.command, ok=ok, **({k: v for k, v in res.items() if k not in ("tables", "ok")} if isinstance(res, dict) else {}))
        if not args.json and isinstance(res, dict):
            print(json.dumps(dict(res, command=args.command, ok=ok), ensure_ascii=False, default=str))
        return 0 if ok else 1
    except MigrationError as e:
        rep.event("error", msg=str(e))
        if not args.json:
            print(f"pg_migrate: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        rep.event("error", msg="interrupted (safe to run again: progress is kept)")
        return 130


if __name__ == "__main__":
    sys.exit(main())
