"""Helpers for tests using isolated PostgreSQL schemas (TEST_DATABASE_URL)."""
import os
import unittest

from game import db as dbm


def on_pg() -> bool:
    return bool((os.environ.get('TEST_DATABASE_URL') or '').strip()) and not bool((os.environ.get('DATABASE_URL') or '').strip())


def columns(db, table: str) -> set:
    """Column names of a table in the current PostgreSQL schema."""
    return {r[0] for r in db.pg('SELECT column_name FROM information_schema.columns '
                                'WHERE table_schema = current_schema() AND table_name = %s', (table,))}


def primary_key(db, table: str) -> tuple:
    """Primary-key columns in their declared order in the current schema."""
    return tuple(r[0] for r in db.pg(
        'SELECT k.column_name FROM information_schema.table_constraints AS c '
        'JOIN information_schema.key_column_usage AS k '
        'ON k.constraint_catalog=c.constraint_catalog AND k.constraint_schema=c.constraint_schema '
        'AND k.constraint_name=c.constraint_name AND k.table_schema=c.table_schema AND k.table_name=c.table_name '
        "WHERE c.table_schema=current_schema() AND c.table_name=%s AND c.constraint_type='PRIMARY KEY' "
        'ORDER BY k.ordinal_position', (table,)))


pg_only = unittest.skipUnless(on_pg(), 'needs TEST_DATABASE_URL=postgresql://... (PostgreSQL 16)')
