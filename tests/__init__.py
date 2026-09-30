# Tests make and delete many temp databases. Pooled idle connections would keep
# those files open, and Windows then refuses to delete them (WinError 32), leaving
# temp folders behind. Tests that need the pool set DB_POOL themselves.
import os

os.environ.setdefault("DB_POOL", "0")
