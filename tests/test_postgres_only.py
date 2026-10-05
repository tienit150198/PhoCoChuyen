"""PostgreSQL-only runtime and operational entry points."""
import ast
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_START = re.compile(r'^\s*(?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|REPLACE|BEGIN|PRAGMA)\b', re.I)
SQL_QUOTES = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"")
LEGACY_SQL = re.compile(
    r'\bINSERT\s+OR\s+(?:IGNORE|REPLACE|ABORT|FAIL|ROLLBACK)\s+INTO\b|'
    r'\bBEGIN\s+(?:IMMEDIATE|EXCLUSIVE)\b|\bAUTOINCREMENT\b|\bWITHOUT\s+ROWID\b|'
    r'\bPRAGMA\s+[A-Z_]+\b(?:\s*[=(;]|\s*$)|'
    r'\b(?:datetime|julianday|strftime|last_insert_rowid|changes|total_changes|group_concat|pragma_[A-Z_]+)\s*\(|'
    r'\b(?:date|time)\s*\(\s*\x27\x27\s*,', re.I)


def legacy_sql(value):
    tokens = SQL_QUOTES.sub("''", value)
    return bool(SQL_START.search(tokens) and LEGACY_SQL.search(tokens))


class PostgresOnly(unittest.TestCase):
    def test_sql_guard_distinguishes_sql_from_python_and_coverage_comments(self):
        for sql in ("INSERT OR IGNORE INTO records VALUES (?)", "BEGIN IMMEDIATE",
                    "SELECT datetime('now', '-2 days')", "PRAGMA table_info(records)",
                    "SELECT strftime('%Y', 'now')", "SELECT date('now', '-1 day')",
                    "CREATE TABLE records(id INTEGER PRIMARY KEY AUTOINCREMENT)"):
            self.assertTrue(legacy_sql(sql), sql)
        for text in ("datetime.datetime(2026, 1, 1)", "time.strftime('%Y-%m-%d')",
                     "# pragma: no cover", "SELECT CURRENT_TIMESTAMP",
                     "PRAGMA is not supported by PostgreSQL", "INSERT OR REPLACE: write explicit ON CONFLICT",
                     "SELECT 'BEGIN IMMEDIATE datetime(''now'') INSERT OR IGNORE', date('2026-01-01')",
                     "INSERT INTO records VALUES (?) ON CONFLICT DO NOTHING"):
            self.assertFalse(legacy_sql(text), text)

    def test_runtime_and_tools_use_native_postgres_sql(self):
        statements = []
        files = [ROOT / 'server.py', *ROOT.glob('game/**/*.py'), *ROOT.glob('live/**/*.py'), *ROOT.glob('scripts/**/*.py')]
        for path in files:
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and legacy_sql(node.value):
                    statements.append(f'{path.relative_to(ROOT)}:{node.lineno}: {node.value[:100]}')
        self.assertEqual(statements, [], 'Use PostgreSQL SQL: ' + '; '.join(statements))

    def test_runtime_does_not_import_a_file_database_driver(self):
        imports = []
        files = [ROOT / 'server.py', *ROOT.glob('game/**/*.py'), *ROOT.glob('live/**/*.py'), *ROOT.glob('scripts/**/*.py')]
        for path in files:
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                modules = ([a.name for a in node.names] if isinstance(node, ast.Import)
                           else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
                if any(name.split('.')[0] == 'sqlite3' for name in modules):
                    imports.append(str(path.relative_to(ROOT)))
        self.assertEqual(imports, [], 'Active code must use PostgreSQL: ' + ', '.join(imports))

    def test_server_requires_database_url_without_creating_data_files(self):
        env = {k: v for k, v in os.environ.items() if k not in ('DATABASE_URL', 'TEST_DATABASE_URL')}
        env['PYTHONPATH'] = os.pathsep.join(filter(None, (str(ROOT), env.get('PYTHONPATH'))))
        with tempfile.TemporaryDirectory() as tmp:
            # server resolves .env from its own directory, independently of cwd.
            script = Path(tmp) / 'server.py'
            script.write_bytes((ROOT / 'server.py').read_bytes())
            run = subprocess.run([sys.executable, str(script), '--port', '0'], cwd=tmp,
                                 env=env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('DATABASE_URL', run.stdout + run.stderr)
            self.assertEqual(list(Path(tmp).rglob('*.sqlite3')), [])


if __name__ == '__main__':
    unittest.main()
