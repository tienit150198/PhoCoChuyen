"""🏅 Danh hiệu tuần của Bảng xếp hạng: the top players of a board hold its weekly titles.

The owner (01/10): "bảng xếp hạng cũng có danh hiệu nhé, mỗi tuần sẽ có danh hiệu cho các top. Được cập nhật mỗi
ngày nhé" — the boards with titles include Chứng chỉ and Danh hiệu (game/leaderboard.py `certs`, `titles`), and
from 05/10 💰 Tài phú (`wealth`, "thêm top tài phú cho toàn server").

Who holds what
* Trải nghiệm (`all`), Danh hiệu (`titles`), Chứng chỉ (`certs`), Tài phú (`wealth`): three tiers each, top 1 /
  top 2–3 / top 4–10,
  with their own names (TIERS, BOARD_TITLES).
* Every workplace board: its top 1 is "🏆 Trùm <nghề>" (CAREER_NOUN).
* Only players the board shows (game/leaderboard.py _VISIBLE: accounts unless hidden, guests who opted in), in
  the board's own order. 💎 Sưu tầm (`collection`) too since 18/10, 🐾 Thú cưng (`pets`, game/pet_lb.py: the best pet's
  💪 lực chiến, from pet_board) since 19/10, 🏝️ Đảo đẹp (`island`, game/island_lb.py: the most beautiful island's
  points, from island_builds) since 19/10, 🪽 Cánh (`wings`, game/wing_lb.py: the điểm cánh of the wings owned, from
  wing_board) since 23/10, and 🦉 Online (`online`, game/online_board.py:
  play time this week, read from stat_play, not from the `leaderboard` table). Nothing is written into a save: holding a weekly title is a server fact (table
  `lb_weekly`), shown on the board, under the name in Phố nghề and on the name tag in Đi dạo.

When
* Once a day (Vietnam time, UTC+7): `refresh()` recomputes the holders from the boards (never while they are
  being rebuilt after a formula change: game/leaderboard.py backfill). It runs from the server's
  housekeeping loop (one process, every 30 s; the first pass after midnight does the work) and lazily from
  GET /api/leaderboard and /api/bootstrap, so a day is never skipped. Which process does it is settled in the
  database (compare-and-set of leaderboard_meta 'weekly'); every other process only reads.
* Monday 00:00 (Vietnam): the first refresh of a new week freezes the week that ended — the standings at that
  moment become that week's final holders (`final`=1, kept, never deleted) — then the new week starts from the
  same standings and moves with them, day by day.
* 🏆 Thưởng top tuần (owner 23/10): when a week is frozen, every final holder gets WEEKLY_REWARD xu once, as a system
  gift (game/system_gift.py, id lbw-<week>-<board>-<rank>: paid at the next load with its card); reward_week.

Table `lb_weekly` (PostgreSQL in game/pg_schema.py): one row per (week, board, rank). `final`=0 rows
are the current holders (the latest daily refresh), `final`=1 rows are past weeks. `title` holds the title text so
the live service (live/street.py) can show it without importing the game.
"""
from __future__ import annotations

import threading
import time

from .wedding_live import vn_day, vn_week, week_start, VN   # the Vietnam calendar ("Khách mời của tuần" uses it too)

META = 'weekly'                 # leaderboard_meta key: '<VN day>|<ISO week>' of the last refresh
ALL, TITLES, CERTS, WEALTH, COLLECTION, ONLINE, PETS, ISLAND = 'all', 'titles', 'certs', 'wealth', 'collection', 'online', 'pets', 'island'
WINGS = 'wings'                 # 🪽 game/wing_lb.py (23/10)
ARENA, PET_CUP, PET_WAR = 'arena', 'pet_cup', 'pet_war'   # ⚔️ game/pet_arena.py, 🏟️ game/pet_cup.py, 🛡️ game/pet_war.py (19/10)
RACE = ('race_drag_bike', 'race_drag_car', 'race_deo_bike', 'race_deo_car')   # 🏁 game/racing.py: the week's best times (22/10)
WEDDING = 'wedding'             # 💍 Khách mời của tuần (game/wedding_live.py race): weddings attended this week (owner 23/10)
FISH_BIG, FISH_DEX = 'fish_big', 'fish_dex'   # 🎣 game/fish_lb.py (owner 24/10): 🐋 this week's heaviest fish, 📖 species collected
TOP = 10                        # ranks that hold a title on the main boards
TIERS = ((1, 1), (2, 3), (4, 10))   # (first rank, last rank) of each tier
TIER_LABELS = ('Top 1', 'Top 2–3', 'Top 4–10')
BOARD_TITLES = {                # (emoji, name) per tier
    ALL: (('👑', 'Trùm cuối của phố'), ('🔥', 'Chiến thần cày cuốc'), ('⚡', 'Dân cày top 10')),
    TITLES: (('🏅', 'Vua săn danh hiệu'), ('✨', 'Nhà sưu tầm xịn sò'), ('🎖️', 'Hội săn danh hiệu')),
    CERTS: (('🎓', 'Thủ khoa của phố'), ('📜', 'Học bá chính hiệu'), ('🤓', 'Mọt sách có số má')),
    WEALTH: (('💎', 'Đại gia của phố'), ('💰', 'Đại gia mới nổi'), ('🤑', 'Hội nhà giàu')),
    # 18/10 (owner: "sưu tầm cũng có nè"): 💎 Sưu tầm (game/auction.py collection_score) holds titles like the others.
    COLLECTION: (('🏺', 'Bộ sưu tập huyền thoại'), ('🔨', 'Nhà sưu tầm đấu giá'), ('💠', 'Hội sưu tầm')),
    # 18/10 (owner: "cho top các bạn online nhiều nữa nhé, top 1 khung này"): 🦉 play time this week (game/online_board.py).
    ONLINE: (('🦉', 'Cú đêm của phố'), ('🌙', 'Thức cùng ánh trăng'), ('🏮', 'Hội cú đêm')),
    # 19/10 (owner: "bảng xếp hạng bên ngoài thêm bảng xếp hạng 'Thú cưng'"): 🐾 the best pet's 💪 lực chiến (game/pet_lb.py).
    PETS: (('🐉', 'Vua thú cưng của phố'), ('🦄', 'Sen cưng siêu cấp'), ('🐾', 'Hội sen yêu bé')),
    # 19/10 (owner: "Đảo đẹp nhất tuần", a title only): 🏝️ the most beautiful island's points (game/island_lb.py).
    ISLAND: (('🏝️', 'Đảo đẹp nhất phố'), ('🌴', 'Chủ đảo mộng mơ'), ('⛱️', 'Hội chủ đảo xinh')),
    # 23/10 (owner: "có hạng cánh nữa nhé, xếp hạng cánh ấy"): 🪽 the điểm cánh of the wings owned (game/wing_lb.py).
    WINGS: (('🪽', 'Đôi cánh số 1 phố'), ('🌟', 'Cánh thần thoại'), ('🕊️', 'Hội chắp cánh')),
    # 19/10 (owner: "thêm thi đua nữa nhé, kết hợp với pet ra tranh đấu với bang nữa"): ⚔️ the arena's weekly ladder
    # (game/pet_arena.py standings: the week's season rating), 🏟️ the latest weekly cup (game/pet_cup.py), 🛡️ the
    # fighters of the bang war's champion and runner-up (game/pet_war.py; its own two tiers, BOARD_TIERS).
    ARENA: (('🏆', 'Vua đấu trường tuần'), ('⚔️', 'Cao thủ đấu trường'), ('🛡️', 'Chiến binh đấu trường')),
    PET_CUP: (('👑', 'Vô địch giải pet tuần'), ('🥈', 'Top 3 giải pet tuần'), ('🎗️', 'Top 10 giải pet tuần')),
    # 🥉 25/10 (owner: "trận tranh hạng 3"): the third's fighters too (game/pet_war.py: the 3rd-place match's winner, or
    # with 3 bangs the semi-final's loser). No weekly xu for it (WEEKLY_REWARD has two tiers: reward_of gives 0).
    PET_WAR: (('🏆', 'Bang vô địch đấu pet'), ('🥈', 'Á quân bang chiến pet'), ('🥉', 'Hạng ba bang chiến pet')),
    # 22/10 (player #470 "thêm độ xe để đua xe"): 🏁 the week's best time-trial times of Đường đua Bến Mây, per track and
    # class (game/racing.py standings), top 1 and top 2–3 only.
    'race_drag_bike': (('🏁', 'Vua drag xe máy tuần'), ('🏍️', 'Top drag xe máy')),
    'race_drag_car': (('🏁', 'Vua drag ô tô tuần'), ('🚗', 'Top drag ô tô')),
    'race_deo_bike': (('⛰️', 'Vua đèo xe máy tuần'), ('🏍️', 'Top đèo xe máy')),
    'race_deo_car': (('⛰️', 'Vua đèo ô tô tuần'), ('🚗', 'Top đèo ô tô')),
    # 23/10 (owner: "cái đám cưới nữa, mình cho danh hiệu với khung riêng nhé"): 💍 the guests who went to the most
    # weddings this week (wedding_guests, the race of game/wedding_live.py), top 1 and top 2–3, with their own drawn
    # frames (public/js/v4/honour-frames.js DRAWN). Beside the race's own 🥇 Khách quý / 🎊 Ăn cưới chuyên nghiệp,
    # which last week's winners keep wearing this week (live/wedding.py).
    WEDDING: (('💒', 'Vua ăn cưới của tuần'), ('💐', 'Khách mời vàng của tuần')),
    # 24/10 (owner: "🐋 Cá lớn nhất … 📖 Bộ sưu tập cá … danh hiệu, khung riêng như các bảng khác"): game/fish_lb.py, with
    # their own drawn frames (public/js/v4/honour-frames.js DRAWN: water, waves, scales, a golden hook for top 1).
    FISH_BIG: (('🐋', 'Vua cá lớn của tuần'), ('🎣', 'Cần thủ cá khủng'), ('🐟', 'Hội săn cá lớn')),
    FISH_DEX: (('📖', 'Nhà sưu tập cá của tuần'), ('🐠', 'Bách khoa cá'), ('🐡', 'Hội sưu tầm cá')),
}
# A board whose tiers are not top 1 / 2–3 / 4–10: 🛡️ the five fighters of the champion bang, then the runner-up's five,
# then 🥉 the third's five (ranks 11–15: an older build's tier_of finds no tier there and shows no title for them).
BOARD_TIERS = {PET_WAR: ((1, 5), (6, 10), (11, 15)), **{b: ((1, 1), (2, 3)) for b in (*RACE, WEDDING)}}
BOARD_LABELS = {PET_WAR: ('Bang vô địch', 'Bang á quân', 'Bang hạng ba'), **{b: ('Top 1', 'Top 2–3') for b in (*RACE, WEDDING)}}
MAIN = (ALL, TITLES, CERTS, WEALTH, COLLECTION, ONLINE, PETS, ISLAND, WINGS, ARENA, PET_CUP, PET_WAR, *RACE, WEDDING, FISH_BIG, FISH_DEX)     # the order of honour (a name tag shows the best one: tier first, then this order)
CAREER_EMOJI = '🏆'
CAREER_NOUN = dict(
    milk_tea='trà sữa', grocery='tạp hóa', delivery='giao hàng', cafe_bakery='bánh & cà phê', florist='tiệm hoa',
    mother_baby='mẹ & bé', restaurant='mì cay', pet_care='chăm thú cưng', salon='salon tóc', repair='sửa đồ',
    farm='nông trại', homestay='homestay', clothing='shop quần áo', pet_shop='shop thú cưng', tra_da='trà đá',
    fruit='trái cây', garbage='thu gom rác', drain='thông cống', homemaker='nội trợ', ice_cream='tiệm kem', pho='quán phở', com='quán cơm', nail='tiệm nail', pagoda='việc chùa', photobooth='tiệm ảnh', library='thư viện', giupviec='giúp việc', naucom='bếp nhà khách', babysitter='trông trẻ', customer_care='chăm sóc khách', pharmacy='nhà thuốc',
    tour_guide='dẫn tour', teacher='bục giảng', accounting='sổ sách', pilot='buồng lái', flight_attendant='khoang khách', oil='giàn khoan',
    corp_accounting='kế toán doanh nghiệp', tax_payroll='thuế & lương', group_accounting='kế toán tập đoàn',
    hr_admin='nhân sự', secretary='thư ký', it_helpdesk='IT văn phòng', railway='gác chắn', nurse='khoa Nội', lighthouse='hải đăng', rescue='tổng đài cứu hộ', lifeguard='hồ bơi', police='công an phường', zpop='tiệm album', customs='hải quan', hotel='khách sạn', banquet='nhà hàng tiệc', reception='quầy lễ tân', teller='quầy giao dịch', research='viện nghiên cứu', radio='đài phát thanh', jewelry='tiệm vàng', car_dealer='đại lý xe', canteen='căn tin trường', stationery='tiệm văn phòng phẩm', moto='tiệm sửa xe', vet='phòng khám thú y', kol='studio nội dung', singer='phòng trà', actor='hãng phim', tuning='xưởng độ xe',
    lawyer='văn phòng luật', art_studio='xưởng vẽ', post_office='bưu điện', laundry='giặt ủi', restore='phục chế')
# A workplace whose top 1 is not a "Trùm": nobody is the boss of a pagoda (game/pagoda_voice.py).
CAREER_TITLE = dict(pagoda=('🪷', 'Siêng việc chùa nhất tuần'))
HOLDERS_SECONDS = 60.0          # how long a process trusts its copy of the current holders

# 🏆 Thưởng top tuần (owner 23/10: "từ giờ những người được top sẽ có thưởng riêng hằng tuần … riêng đám cưới cho cao
# hơn chút"; amounts set by the owner 24/10). Xu per tier of a board (BOARD_TIERS / TIERS order), paid once to each
# final holder of a frozen week (reward_week). One table to tune.
WEEKLY_REWARD = {
    WEDDING: (2_000_000, 1_000_000),          # 💍 top 1, top 2–3
    PET_WAR: (500_000, 200_000),              # 🛡️ each fighter of the champion bang (ranks 1–5), of the runner-up (6–10)
}
REWARD_DEFAULT = (1_000_000, 500_000, 200_000)   # any other board: top 1, top 2–3, top 4–10 (🏁 races: top 1, top 2–3)
REWARD_CAREER = 1_000_000       # 🏆 Trùm <nghề>: a workplace board's top 1
REWARD_FROM = '2026-W43'        # the first week paid (19–25/10/2026, frozen Monday 26/10): earlier weeks never are
REWARD_TITLE = '🏆 Thưởng top tuần'
REWARD_ID = 'lbw-'              # system_gifts id: lbw-<week>-<board>-<rank> (game/system_gift.py pays it on load)



def now() -> float:
    return time.time()


# ---------------------------------------------------------------- the titles
def tier_of(board: str, rank: int) -> int | None:
    """0, 1, 2 for the tiers of a main board; 0 for the top 1 of a workplace board; None for no title."""
    if board in BOARD_TITLES:
        return next((i for i, (lo, hi) in enumerate(BOARD_TIERS.get(board, TIERS)) if lo <= rank <= hi), None)
    return 0 if rank == 1 else None


def career_noun(board: str) -> str:
    from .content import CAREER_META
    noun = CAREER_NOUN.get(board)
    if noun:
        return noun
    short = (CAREER_META.get(board) or {}).get('short') or board
    return short[:1].lower() + short[1:]


def title_of(board: str, rank: int) -> dict | None:
    """{emoji, name, text, tier, label} of the title a rank holds on a board, or None."""
    tier = tier_of(board, rank)
    if tier is None:
        return None
    if board in BOARD_TITLES:
        emoji, name = BOARD_TITLES[board][tier]
        label = BOARD_LABELS.get(board, TIER_LABELS)[tier]
    elif board in CAREER_TITLE:
        (emoji, name), label = CAREER_TITLE[board], 'Top 1'
    else:
        emoji, name, label = CAREER_EMOJI, f'Trùm {career_noun(board)}', 'Top 1'
    return dict(emoji=emoji, name=name, text=f'{emoji} {name}', tier=tier, label=label)


def tiers_of(board: str) -> list:
    """The tiers of a board for the view: [{tier, label, emoji, name, ranks: (lo, hi)}]."""
    if board in BOARD_TITLES:
        tiers, labels = BOARD_TIERS.get(board, TIERS), BOARD_LABELS.get(board, TIER_LABELS)
        return [dict(tier=i, label=labels[i], emoji=e, name=n, lo=tiers[i][0], hi=tiers[i][1], reward=reward_of(board, tiers[i][0]))
                for i, (e, n) in enumerate(BOARD_TITLES[board])]
    t = title_of(board, 1)
    return [dict(tier=0, label='Top 1', emoji=t['emoji'], name=t['name'], lo=1, hi=1, reward=reward_of(board, 1))]


def reward_of(board: str, rank: int) -> int:
    """🏆 The weekly reward (xu) of a final holder of `rank` on `board`, 0 for none."""
    tier = tier_of(board, rank)
    if tier is None:
        return 0
    if board not in BOARD_TITLES:
        return REWARD_CAREER
    row = WEEKLY_REWARD.get(board, REWARD_DEFAULT)
    return int(row[tier]) if tier < len(row) else 0


def honour(board: str, rank: int) -> tuple:
    """Sort key: the best title first (tier, then main boards in MAIN order, then workplaces)."""
    tier = tier_of(board, rank)
    return (tier if tier is not None else 9, MAIN.index(board) if board in MAIN else len(MAIN), board)


# ---------------------------------------------------------------- daily refresh
def _boards() -> list:
    from .leaderboard import CAREER_IDS
    return list(MAIN) + sorted(CAREER_IDS)


def standings(db, t: float | None = None) -> list:
    """[(board, rank, sid, score)] of every title holder right now, from the boards as shown (🦉 Online: the week of `t`)."""
    from . import leaderboard as lb
    from . import online_board
    out = []
    for board in _boards():
        n = TOP if board in BOARD_TITLES else 1
        if board == ONLINE:
            out.extend(online_board.standings(db, now() if t is None else t, n))
            continue
        if board == PETS:
            from . import pet_lb
            out.extend(pet_lb.standings(db, n))
            continue
        if board == ISLAND:
            from . import island_lb
            out.extend(island_lb.standings(db, n, t))
            continue
        if board == WINGS:
            from . import wing_lb
            out.extend(wing_lb.standings(db, n))
            continue
        if board in (ARENA, PET_CUP, PET_WAR):   # ⚔️ 🏟️ 🛡️ not on the `leaderboard` table
            out.extend(_pet_standings(db, board, now() if t is None else t, n))
            continue
        if board in RACE:   # 🏁 the week of `t` (race_runs)
            out.extend(_race_standings(db, board, now() if t is None else t))
            continue
        if board == WEDDING:   # 💍 the week of `t` (wedding_guests)
            out.extend(_wedding_standings(db, now() if t is None else t))
            continue
        if board in (FISH_BIG, FISH_DEX):   # 🎣 🐋 the week of `t` (fish_best), 📖 the collection now (fish_dex)
            out.extend(_fish_standings(db, board, now() if t is None else t))
            continue
        rows = db.execute(f"SELECT l.sid,l.score {lb._FROM} WHERE l.board=? AND {lb._VISIBLE} {lb._ORDER} LIMIT ?", (board, n)).fetchall()
        out.extend((board, i + 1, r['sid'], int(r['score'])) for i, r in enumerate(rows))
    return out


def _pet_standings(db, board: str, t: float, n: int) -> list:
    try:
        if board == ARENA:
            from . import pet_arena
            return pet_arena.standings(db, t, n)
        if board == PET_CUP:
            from . import pet_cup
            return pet_cup.standings(db, n)
        from . import pet_war
        return pet_war.standings(db, t)
    except Exception:  # noqa: BLE001 - a fault here never costs the other boards their titles
        return []


def _race_standings(db, board: str, t: float) -> list:
    """🏁 [(board, rank, sid, ms)] of the week of `t`: its top 3 only (the race boards' titles)."""
    try:
        from . import racing
        return racing.standings(db, board, t, BOARD_TIERS[board][-1][1])
    except Exception:  # noqa: BLE001 - a fault here never costs the other boards their titles
        return []


def _wedding_standings(db, t: float) -> list:
    """💍 [(board, rank, sid, weddings)] of the week of `t`: its top 3 (the race's order: most weddings, then who got
    there first), only players the boards show (game/leaderboard.py _VISIBLE)."""
    try:
        from .leaderboard import _VISIBLE
        from .wedding_live import GUEST_MIN_MINUTES
        rows = db.execute('SELECT g.sid, COUNT(*) AS n, MAX(g.counted_at) AS last FROM wedding_guests g LEFT JOIN accounts a ON a.sid=g.sid '
                          f'LEFT JOIN leaderboard_players p ON p.sid=g.sid WHERE g.week=? AND g.ok=1 AND g.steps>=? AND {_VISIBLE} '
                          'GROUP BY g.sid ORDER BY n DESC, last ASC, g.sid LIMIT ?',
                          (vn_week(t), GUEST_MIN_MINUTES, BOARD_TIERS[WEDDING][-1][1])).fetchall()
        return [(WEDDING, i + 1, r['sid'], int(r['n'])) for i, r in enumerate(rows)]
    except Exception:  # noqa: BLE001 - a fault here never costs the other boards their titles
        return []


def _fish_standings(db, board: str, t: float) -> list:
    """🎣 [(board, rank, sid, score)]: 🐋 the week of `t` (grams), 📖 the collection now (species), top TOP."""
    try:
        from . import fish_lb
        return fish_lb.standings(db, board, t, TOP)
    except Exception:  # noqa: BLE001 - a fault here never costs the other boards their titles
        return []


def standings_online(db, t: float) -> list:
    from . import online_board
    return online_board.standings(db, t, TOP)


def _insert(db, week: str, rows: list, final: int, day: str, t: float) -> None:
    for board, rank, sid, score in rows:
        db.execute('INSERT INTO lb_weekly(week,board,rank,sid,score,title,final,day,at) VALUES(?,?,?,?,?,?,?,?,?) '
                   'ON CONFLICT(week,board,rank) DO UPDATE SET sid=excluded.sid,score=excluded.score,title=excluded.title,'
                   'final=excluded.final,day=excluded.day,at=excluded.at',
                   (week, board, rank, sid, score, title_of(board, rank)['text'], final, day, t))


_done: dict = {}                # database -> the day this process saw refreshed (no database read until tomorrow)
_pending: dict = {}             # database -> when this process last saw the boards still being rebuilt (backfill)
PENDING_SECONDS = 60.0
_lock = threading.Lock()


def _key(store) -> str:
    return str(getattr(store, 'path', None) or id(store))


def refresh(store, t: float | None = None, best_effort_ms: int | None = None) -> bool:
    """Recompute the holders once per Vietnam day; on the first day of a week, freeze the week that ended first.
    True when this call did it. Cheap when it is already done (a memo in the process, else one read)."""
    t = now() if t is None else t
    day, week, key = vn_day(t), vn_week(t), _key(store)
    if _done.get(key) == day:
        return False
    with _lock:
        if _done.get(key) == day or time.monotonic() - _pending.get(key, -1e9) < PENDING_SECONDS:
            return False
        from .leaderboard import VERSION
        with store.connect() as db:
            row = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (META,)).fetchone()
            built = db.execute("SELECT v FROM leaderboard_meta WHERE k='backfill'").fetchone()
        if row and row[0].split('|')[0] == day:
            _done[key] = day
            heal(store, t)   # done today by another process: perhaps an older build that knows only its own boards
            return False
        if built and built[0] != str(VERSION):   # the boards are being rebuilt (a new formula): wait for them
            _pending[key] = time.monotonic()
            return False
        prev = vn_week(week_start(t) - 3600)

        def step(db):
            cur = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (META,)).fetchone()
            last = cur[0] if cur else ''
            if last.split('|')[0] == day:
                return False
            mark = f'{day}|{week}'
            # Compare-and-set: of the processes that saw yesterday's mark, one moves it and does the work.
            claimed = (db.execute('UPDATE leaderboard_meta SET v=? WHERE k=? AND v=?', (mark, META, last)).rowcount if cur else
                       db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING', (META, mark)).rowcount)
            if claimed != 1:
                return False
            rows = standings(db, t)
            last_week = last.split('|')[1] if '|' in last else None
            if last_week and last_week != week:
                if last_week == prev:   # the week that just ended: its final holders are the standings at its end
                    db.execute('DELETE FROM lb_weekly WHERE final=0 AND week=?', (last_week,))
                    # 🦉 Online starts again from zero each week: the ended week's own totals
                    # ⚔️ the arena's ladder too: the ended week's own season
                    # 🏁 the race boards too: the ended week's own best times
                    # 💍 the wedding race too: the ended week's own guests
                    # 🐋 the fish board too: the ended week's own heaviest fish
                    ended = ([r for r in rows if r[0] not in (ONLINE, ARENA, WEDDING, FISH_BIG, *RACE)] + [r for r in standings_online(db, week_start(t) - 3600)]
                             + _pet_standings(db, ARENA, week_start(t) - 3600, TOP)
                             + [r for b in RACE for r in _race_standings(db, b, week_start(t) - 3600)]
                             + _wedding_standings(db, week_start(t) - 3600)
                             + _fish_standings(db, FISH_BIG, week_start(t) - 3600))
                    _insert(db, last_week, ended, 1, day, t)
                else:                   # a week long gone (the server was off): its last daily holders stand
                    db.execute('UPDATE lb_weekly SET final=1 WHERE final=0 AND week=?', (last_week,))
                reward_week(db, last_week, t)   # 🏆 the final holders' weekly rewards, once each
            db.execute('DELETE FROM lb_weekly WHERE final=0')
            _insert(db, week, rows, 0, day, t)
            from .live_chat import notify   # 🏅 the live service reads the holders again (live/honours.py `tt`)
            notify(db, dict(op='honours_lb'))
            return True
        did = store.transaction(step, best_effort_ms)
        if did is None:     # busy (best effort): try again on a later request
            return False
        _done[key] = day
        clear_cache()
        return bool(did)


# ---------------------------------------------------------------- mixed rollout (review fix 19/10)
# 2.4.60 refreshes only the boards it knows: its daily refresh deletes every current row (final=0) and writes its own
# boards back, its Monday freeze writes the ended week's finals of its boards only. The boards new since then are
# re-derived here, by the next process of this build that sees the day done (refresh above), once a process a day:
# * this week's current rows (final=0) of 🏝️ island, ⚔️ arena, 🏟️ pet_cup, 🛡️ pet_war (🏁 race, 🪽 wings): from their standings now;
# * the ended week's finals (final=1) of arena (that week's season), pet_cup (the latest cup of a week up to it) and
#   pet_war (the latest war over by the week's end): exact, as long as it runs before the next cup / war, so only on the
#   first day of the new week.
# What cannot be fixed from here: 🏝️ island's (and 🪽 wings', under 2.5.6) final row of an ended week frozen by 2.4.60 (the board is the islands'
# beauty *now*: the builds at the week's end are not kept), and the hours between 2.4.60's refresh and this heal, when
# those boards show no holder.
NEW_BOARDS = (ISLAND, ARENA, PET_CUP, PET_WAR, *RACE, WINGS, WEDDING, FISH_BIG, FISH_DEX)   # 🏁 RACE: new in 2.5.2 (2.5.1 neither refreshes nor freezes them), 🪽 WINGS in 2.5.7, 💍 WEDDING after 2.5.9, 🎣 FISH after 2.6.0
ENDED_BOARDS = (ARENA, PET_CUP, PET_WAR, *RACE, WEDDING, FISH_BIG)
HEAL_LOCK = 17863


def _new_standings(db, board: str, t: float) -> list:
    if board == ISLAND:
        from . import island_lb
        try:
            return island_lb.standings(db, TOP, t)
        except Exception:  # noqa: BLE001
            return []
    if board in RACE:
        return _race_standings(db, board, t)
    if board == WINGS:
        from . import wing_lb
        try:
            return wing_lb.standings(db, TOP)
        except Exception:  # noqa: BLE001
            return []
    if board == WEDDING:
        return _wedding_standings(db, t)
    if board in (FISH_BIG, FISH_DEX):
        return _fish_standings(db, board, t)
    return _pet_standings(db, board, t, TOP)


def _ended_standings(db, board: str, t: float, prev: str) -> list:
    try:
        if board == ARENA:
            return _pet_standings(db, ARENA, week_start(t) - 3600, TOP)
        if board in RACE:
            return _race_standings(db, board, week_start(t) - 3600)
        if board == WEDDING:
            return _wedding_standings(db, week_start(t) - 3600)
        if board == FISH_BIG:
            return _fish_standings(db, FISH_BIG, week_start(t) - 3600)
        if board == PET_CUP:
            from . import pet_cup
            return pet_cup.standings(db, TOP, prev)
        from . import pet_war
        return pet_war.standings(db, week_start(t))
    except Exception:  # noqa: BLE001
        return []


def heal(store, t: float | None = None) -> bool:
    """Re-derive the rows of NEW_BOARDS an older build's refresh or freeze left out (see above). True when it wrote."""
    t = now() if t is None else t
    day, week = vn_day(t), vn_week(t)
    prev = vn_week(week_start(t) - 3600)

    def run(db):
        db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (HEAL_LOCK, week))
        have = {r['board'] for r in db.execute('SELECT DISTINCT board FROM lb_weekly WHERE final=0 AND week=? AND board = ANY(?)',
                                               (week, list(NEW_BOARDS))).fetchall()}
        rows = [r for b in NEW_BOARDS if b not in have for r in _new_standings(db, b, t)]
        if rows:
            _insert(db, week, rows, 0, day, t)
        ended = []
        if t < week_start(t) + 86400 and db.execute('SELECT 1 FROM lb_weekly WHERE final=1 AND week=? LIMIT 1', (prev,)).fetchone():
            had = {r['board'] for r in db.execute('SELECT DISTINCT board FROM lb_weekly WHERE final=1 AND week=? AND board = ANY(?)',
                                                  (prev, list(ENDED_BOARDS))).fetchall()}
            ended = [r for b in ENDED_BOARDS if b not in had for r in _ended_standings(db, b, t, prev)]
            if ended:
                _insert(db, prev, ended, 1, day, t)
        # 🏆 a week an older build froze (it pays no reward), or a reward this process missed: paid once each
        paid = reward_week(db, prev, t)
        if rows or ended:
            from .live_chat import notify
            notify(db, dict(op='honours_lb'))
        return bool(rows or ended or paid)
    try:
        did = bool(store.transaction(run, 250))
    except Exception:  # noqa: BLE001 - a page or the housekeeping never fails because of this
        return False
    if did:
        clear_cache()
    return did


def reward_week(db, week: str | None, t: float | None = None) -> int:
    """🏆 Thưởng top tuần: one system gift (game/system_gift.py: paid at the holder's next load through the game's
    command path, with its private card) per final holder (week, board, rank) of a frozen week, from REWARD_FROM on.
    Idempotent: the gift's id is lbw-<week>-<board>-<rank> (primary key; ON CONFLICT DO NOTHING), so a second refresh,
    a heal or another process never pays twice. Admin accounts (ADMIN_USERS) and players the boards hide get nothing.
    Runs inside the caller's transaction; returns the gifts written."""
    if not isinstance(week, str) or week < REWARD_FROM:
        return 0
    rows = db.execute('SELECT board, rank, sid FROM lb_weekly WHERE final=1 AND week=?', (week,)).fetchall()
    if not rows:
        return 0
    have = {r['id'] for r in db.execute('SELECT id FROM system_gifts WHERE id LIKE ?', (f'{REWARD_ID}{week}-%',)).fetchall()}
    from .leaderboard import _privacy
    from .player_feedback import admin_users
    from .system_gift import valid_id
    admins, t, n = admin_users(), now() if t is None else t, 0
    for r in rows:
        board, rank, sid = r['board'], int(r['rank']), r['sid']
        gid, xu, ti = f'{REWARD_ID}{week}-{board}-{rank}', reward_of(board, rank), title_of(board, rank)
        if gid in have or not xu or not ti or not valid_id(gid) or not sid:
            continue
        p = _privacy(db, sid)
        if not p['visible']:
            continue
        if admins and p['account']:
            u = db.execute('SELECT username FROM accounts WHERE sid=?', (sid,)).fetchone()
            if u and str(u['username']).lower() in admins:
                continue
        text = (f'Tuần {week[-2:]} bạn giữ danh hiệu “{ti["text"]}” ({ti["label"]}). Phố gửi bạn {fmt_xu(xu)} xu thưởng '
                'top tuần. Tuần này giữ phong độ nha!')
        n += db.execute("INSERT INTO system_gifts(id, sid, coins, title, text, status, created) VALUES(?, ?, ?, ?, ?, 'pending', ?) "
                        'ON CONFLICT(id) DO NOTHING', (gid, sid, xu, REWARD_TITLE, text[:300], t)).rowcount
    return n


def fmt_xu(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def run_refresh(store) -> None:
    """Housekeeping (server.py _housekeeping): never raises."""
    import sys
    try:
        if refresh(store):
            sys.stderr.write(f'[lb_titles] weekly titles refreshed for {vn_day(now())}\n')
    except Exception as e:  # noqa: BLE001 - housekeeping must never take the server down
        sys.stderr.write(f'[lb_titles] refresh: {type(e).__name__}\n')


def ensure(store, t: float | None = None) -> None:
    """Request path: today's refresh if nobody did it yet (waits at most 250 ms for the write lock). Never raises."""
    try:
        refresh(store, t, best_effort_ms=250)
    except Exception:  # noqa: BLE001 - a page never fails because of the weekly titles
        pass


# ---------------------------------------------------------------- reading
_cache: dict = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def holders(store) -> dict:
    """{sid: [{board, rank, emoji, name, text, tier, label}, …best first]} of the current week (≤ 40 + one per workplace), cached
    HOLDERS_SECONDS per process."""
    t, key = time.monotonic(), _key(store)
    with _cache_lock:
        hit = _cache.get(key)
        if hit and t - hit[0] < HOLDERS_SECONDS:
            return hit[1]
    out: dict = {}
    try:
        with store.connect() as db:
            rows = db.execute('SELECT board,rank,sid FROM lb_weekly WHERE final=0').fetchall()
    except Exception:  # noqa: BLE001 - a database from before this table
        rows = []
    for r in rows:
        ti = title_of(r['board'], int(r['rank']))
        if ti:
            out.setdefault(r['sid'], []).append(dict(ti, board=r['board'], rank=int(r['rank'])))
    for v in out.values():
        v.sort(key=lambda x: honour(x["board"], x["rank"]))
    with _cache_lock:
        if len(_cache) > 96:
            _cache.clear()
        _cache[key] = (t, out)
    return out


def held(store, sid: str | None) -> list:
    """The weekly titles this save holds now, best first (empty for nobody)."""
    return list(holders(store).get(sid, ())) if sid else []


def best(store, sid: str | None) -> dict | None:
    """The one a name tag shows: {emoji, name}."""
    h = held(store, sid)
    return dict(emoji=h[0]['emoji'], name=h[0]['name']) if h else None


def _public(r, viewer: str | None) -> str:
    """The holder's name as the board shows it now (game/leaderboard.py privacy)."""
    from .leaderboard import GUEST_DEFAULT
    account = bool(r['acct'])
    name = r['display'] if account else r['gname']
    show = r['show']
    visible = bool(name) and bool(show if show is not None else (1 if account else GUEST_DEFAULT))
    return name if name and (visible or r['sid'] == viewer) else 'Một người chơi'


def board_view(store, board: str, viewer: str | None = None) -> dict:
    """The "Danh hiệu tuần" block of one board: this week's holders per tier, when it was last updated, and last
    week's final holders."""
    t = now()
    week, prev = vn_week(t), vn_week(week_start(t) - 3600)
    key, mono = ('view', _key(store), board, prev), time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
    if hit and mono - hit[0] < HOLDERS_SECONDS:   # the holders change once a day (refresh / heal clear this)
        rows = hit[1]
    else:
        with store.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT w.week,w.rank,w.sid,w.score,w.final,w.at,a.display,p.name AS gname,p.show,a.uid IS NOT NULL AS acct '
                                                'FROM lb_weekly w LEFT JOIN accounts a ON a.sid=w.sid LEFT JOIN leaderboard_players p ON p.sid=w.sid '
                                                'WHERE w.board=? AND (w.final=0 OR w.week=?) ORDER BY w.rank', (board, prev)).fetchall()]
        with _cache_lock:
            if len(_cache) > 96:
                _cache.clear()
            _cache[key] = (mono, rows)

    def tiers(rows):
        out = []
        for tr in tiers_of(board):
            got = [dict(rank=int(r['rank']), name=_public(r, viewer), me=r['sid'] == viewer)
                   for r in rows if tr['lo'] <= int(r['rank']) <= tr['hi']]
            out.append(dict(tr, holders=got))
        return out
    cur = [r for r in rows if not r['final']]
    last = [r for r in rows if r['final'] and r['week'] == prev]
    updated = max((float(r['at']) for r in cur), default=None)
    return dict(week=week, updated=updated, ends=week_start(t) + 7 * 86400, tiers=tiers(cur),
                last=dict(week=prev, tiers=tiers(last)) if last else None)


def fmt_updated(t: float | None) -> str | None:
    """'01/10 · 00:00' (Vietnam time), for logs and tests."""
    import datetime
    return datetime.datetime.fromtimestamp(t, VN).strftime('%d/%m · %H:%M') if t else None


def forget(db, marks: str, part: list) -> None:
    """Deleted saves (game/leaderboard.py forget, inside the caller's transaction): their weekly rows go with them."""
    db.execute(f"DELETE FROM lb_weekly WHERE sid IN ({marks})", part)
    clear_cache()
