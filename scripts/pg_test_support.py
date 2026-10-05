"""Disposable PostgreSQL setup for browser and package checks."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_env(**values):
    """Require the scratch endpoint and share one test-run id with child servers."""
    url = (os.environ.get('TEST_DATABASE_URL') or '').strip()
    if not url.startswith(('postgresql://', 'postgres://')):
        raise SystemExit('Set TEST_DATABASE_URL to a disposable PostgreSQL database before running this check.')
    os.environ.pop('DATABASE_URL', None)
    from game import db
    db._test_run()
    return dict(os.environ, **values)


def test_connect(namespace):
    test_env()
    from game.storage import Store
    return Store(namespace).connect()


def schema_for(namespace):
    test_env()
    from game.storage import Store
    return Store(namespace).pg.schema
