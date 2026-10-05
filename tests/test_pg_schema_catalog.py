"""The PostgreSQL catalog used for schema checks and identity maintenance."""
import tempfile
import unittest
from pathlib import Path

from game import pg_schema
from game.storage import Store
from tests.pg_support import pg_only


class CatalogShape(unittest.TestCase):
    def test_catalog_contains_only_runtime_metadata(self):
        names = [table['name'] for table in pg_schema.TABLES]
        self.assertEqual(len(names), len(set(names)))
        for table in pg_schema.TABLES:
            self.assertEqual(set(table), {'name', 'identity'}, table['name'])


@pg_only
class CatalogDatabase(unittest.TestCase):
    def test_catalog_matches_installed_tables_and_identity_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'catalog')
            try:
                with store.connect() as db:
                    names = {row[0] for row in db.pg(
                        "SELECT tablename FROM pg_tables WHERE schemaname=current_schema()")}
                    self.assertEqual(names, {table['name'] for table in pg_schema.TABLES})
                    identities = {(row[0], row[1]) for row in db.pg(
                        "SELECT table_name,column_name FROM information_schema.columns "
                        "WHERE table_schema=current_schema() AND is_identity='YES'")}
                    self.assertEqual(identities, {(table['name'], table['identity'])
                        for table in pg_schema.TABLES if table['identity']})
            finally:
                store.close_pool()
