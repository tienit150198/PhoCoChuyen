# Tests make and delete many temp databases. Pooled idle connections would keep
# those files open, and Windows then refuses to delete them (WinError 32), leaving
# temp folders behind. Tests that need the pool set DB_POOL themselves.
import os

os.environ.setdefault("DB_POOL", "0")
# 🔥 Nghề x3 (game/x3_week.py) follows the real calendar: off, so a test's wallet does not depend on the day it runs
# (tests/test_x3_week.py turns it on where it checks it).
os.environ.setdefault("MNL_X3_OFF", "1")
# 💼 Lương kế toán ×5 ngày lễ (game/accounting_jobs.py) follows the real calendar too: off unless a test turns it on.
os.environ.setdefault("MNL_HOLIDAY_OFF", "1")
# 🎁 Quà cả phố (game/system_gift.py BROADCASTS) follows the real calendar: off, so a test's gifts and wallet do not
# depend on the day it runs (tests/test_system_gift.py turns it on where it checks it).
os.environ.setdefault("MNL_BROADCAST_OFF", "1")
