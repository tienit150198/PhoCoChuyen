"""Backend helpers for tests that run on SQLite (default) and on PostgreSQL
(TEST_DATABASE_URL=postgresql://..., see game/db.py and docs/POSTGRES.md)."""
import unittest

from game import db as dbm


def on_pg() -> bool:
    return dbm.database_url() is not None


def columns(db, table: str) -> set:
    """Column names of a table, on either backend."""
    if dbm.is_pg(db):
        return {r[0] for r in db.pg('SELECT column_name FROM information_schema.columns '
                                    'WHERE table_schema = current_schema() AND table_name = %s', (table,))}
    return {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}


sqlite_only = unittest.skipIf(on_pg(), 'SQLite-specific (writer turn, WAL, files); the PostgreSQL twin is in test_pg_backend')
pg_only = unittest.skipUnless(on_pg(), 'needs TEST_DATABASE_URL=postgresql://... (PostgreSQL 16)')
