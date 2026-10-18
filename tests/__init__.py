# PostgreSQL tests use TEST_DATABASE_URL and isolated schemas for temporary namespaces.
import asyncio
import os
import sys

if sys.platform == "win32":
    # psycopg async connections require add_reader(), unavailable on Proactor.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 🔥 Nghề x3 (game/x3_week.py) follows the real calendar: off, so a test's wallet does not depend on the day it runs
# (tests/test_x3_week.py turns it on where it checks it).
os.environ.setdefault("MNL_X3_OFF", "1")
# 📈 Lãi nhân viên theo thị trường / 🔥 nghề hot (game/staff_market.py) follow the real clock: ×1.00 and no hot career,
# so a staff order's money does not depend on the hour a test runs (tests/test_staff_market.py turns it on).
os.environ.setdefault("MNL_MARKET_OFF", "1")
# ⏰ Giờ vàng (game/golden_hour.py): a test's money must not depend on the hour it runs; tests/test_golden_hour.py turns it on.
os.environ.setdefault("MNL_GOLDEN_OFF", "1")
# 🎲 Chợ đen's first round of the day and its short windows (game/fair_boost.py) are gone since 16/10 (rate() is always
# None); the switch is kept harmless for older test trees.
os.environ.setdefault("MNL_BM_BOOST_OFF", "1")
# 💼 Lương kế toán ×5 ngày lễ (game/accounting_jobs.py) follows the real calendar too: off unless a test turns it on.
os.environ.setdefault("MNL_HOLIDAY_OFF", "1")
# 🎁 Quà cả phố (game/system_gift.py BROADCASTS) follows the real calendar: off, so a test's gifts and wallet do not
# depend on the day it runs (tests/test_system_gift.py turns it on where it checks it).
os.environ.setdefault("MNL_BROADCAST_OFF", "1")
# 🕶️ Chợ đen (game/fair_bm.py): no bảo kê gate and no arrests in the tests of the stalls' own rules (their scripted
# rounds); tests/test_black_market.py turns it on.
os.environ.setdefault("MNL_BM_OFF", "1")
# 🚔 Trại tạm giữ (game/jail.py): nobody jailed in the other tests (a raid or a false report would block their next
# commands); tests/test_jail.py and tests/test_black_market.py turn it on.
os.environ.setdefault("MNL_JAIL_OFF", "1")
os.environ.setdefault("MNL_WEALTH_FEE_OFF", "1")   # 🏛️ game/wealth_fee.py: tests with big sums test other things (test_wealth_fee turns it on)
# 💾 Nhập bản lưu (game/save_guard.py): many tests build a save by importing a crafted one; tests/test_save_guard.py
# turns the guard on where it checks it.
os.environ.setdefault("MNL_IMPORT_GUARD_OFF", "1")
# ⏱️ Ngày có lương/lãi theo giờ thật (game/interest_clock.py): a new save starts with the full allowance like an older one,
# so a test that closes many days in a few seconds is paid as before (tests/test_interest_clock.py checks START).
os.environ.setdefault("MNL_ICLOCK_FULL", "1")
