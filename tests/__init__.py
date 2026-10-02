# Tests make and delete many temp databases. Pooled idle connections would keep
# those files open, and Windows then refuses to delete them (WinError 32), leaving
# temp folders behind. Tests that need the pool set DB_POOL themselves.
import os

os.environ.setdefault("DB_POOL", "0")
# 🔥 Nghề x3 (game/x3_week.py) follows the real calendar: off, so a test's wallet does not depend on the day it runs
# (tests/test_x3_week.py turns it on where it checks it).
os.environ.setdefault("MNL_X3_OFF", "1")
