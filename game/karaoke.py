"""🎤 Phòng hát Mây, the game server's side (karaoke phase 1; design scratchpad KARAOKE_DESIGN.md, owner 06/10).

The rooms themselves run in the live service (live/karaoke.py, switch LIVE_KARAOKE, welcome flag `kara`): three
public themed rooms (Nhạc trẻ, Bolero · trữ tình, Nhạc quốc tế), at most ROOM_CAP people each, an overflow room when
one is full. Everyone in a room sees the same YouTube video at the same second (the official IFrame player on
youtube-nocookie.com, ads and branding intact), a song queue, the singer on the "sân khấu", reactions, a cheer meter,
bubbles, xu tips and a 10 s applause moment. v1 has no voice: nothing is recorded (Permissions-Policy keeps the mic off).
Plus 🧩 Đoán bài in the same rooms, text only: a host gives a short lyric line with blanks (≤ CLUE_WORDS words) or
emoji clues, the others type guesses; the first right one wins GUESS_XU from a fixed pool (a daily cap per player).

This module holds what needs the save or the database:
* parse_vid(link): the YouTube id of a link (watch?v=, youtu.be, shorts, embed, live, v; www./m./music.;
  youtube-nocookie.com; a bare 11-character id). Anything else (another host, youtube.com.evil.io, javascript:) is None.
  Only the id is ever stored or echoed, never the link.
* check_song (POST /api/karaoke/song {url}): oEmbed (no API key) with a short timeout and a cache (`kara_songs`,
  CACHE_OK_SECS / CACHE_BAD_SECS): 200 = playable (title and channel kept, the title through live/filters.py: heavy
  words become *, links and numbers •••), 401/403 = embedding blocked, 400/404 = gone; anything else (timeout, 5xx)
  is "thử lại" and is not cached. A banned song (an admin) is refused.
* queue (POST /api/karaoke/queue {rid}): one "lượt hát" ticket (`kara_tickets` kind 'queue'), QUEUE_XU from the
  wallet, the first ticket of each Vietnam day free; an unused ticket is handed back instead of a new one, so a
  refused `kara_add` never costs twice. The live service redeems the ticket (used=1) when the song joins a queue,
  and stamps `played` when it starts (the tips below check it).
* tip (POST /api/karaoke/tip {e, xu, rid}): TIP_CHIPS xu from the sender's wallet to the singer of a song that played
  in the last TIP_WINDOW seconds; the singer receives TIP_KEEP percent (a live_effects 'coins' row, paid on their next
  load), the rest is burned (a sink). Caps: TIP_SEND_DAY sent and TIP_GOT_DAY received per Vietnam day; accounts of
  ACCOUNT_DAYS; not to oneself; not between players who blocked each other. The live service hears it (NOTIFY
  op 'kara_tip') and shows it to the room.
* admin_view / admin_act (GET/POST /api/admin/karaoke): reports (`reports` kind 'kara', 🛟 'minor' first), banned
  songs, and the tools: skip, kick, close room, ban / unban song, mute (live_chat.act), keep (reviewed).
* forget(store, token): a player who deletes their data loses their tickets and reviews; their reports are kept
  anonymous like the chat's.

Money: through the journey wallet and its Sổ ví history (journey._wallet). The history kind 'karaoke' is accepted by
journey.validate from this build on (HISTORY_KINDS), but the rows are still WRITTEN with WRITE_KIND = 'life' (a kind
every build since 1.0 validates), so a rollback to 1.9.4 keeps loading every save this build wrote. Step 2 (a later
release, once rolling back past this one is no longer needed): set WRITE_KIND = KIND. One daily Sổ ví row per kind of
spend ("🎤 Phòng hát · 3 bài"), updated in place like the fair photo's, so the 120-row history does not fill up.
No new key in any save.

Tables (game/pg_schema.py, SCHEMA_VERSION 26): kara_songs, kara_tickets, kara_reviews.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import parse_qs, quote, urlsplit

KIND = 'karaoke'                 # journey.HISTORY_KINDS from this build on (step 1: accepted)
WRITE_KIND = 'life'              # what this build writes (an old kind: 1.9.4 validates it). Step 2: KIND.
QUEUE_XU = 2                     # a queued song (owner 06/10), the first of the day free
TIP_CHIPS = (5, 10, 20, 50)
TIP_KEEP = 80                    # percent the singer receives; the rest is burned (owner 06/10: 20%)
TIP_SEND_DAY = 200               # xu one player may tip per Vietnam day
TIP_GOT_DAY = 500                # xu one singer may receive from tips per Vietnam day
TIP_WINDOW = 15 * 60             # a tip goes to a song that started this recently
ACCOUNT_DAYS = 1                 # accounts this old (real days) may tip (bank_xfer.ACCOUNT_DAYS)
TICKET_DAYS = 1                  # an unused queue ticket stays valid this long
GUESS_XU = 5                     # 🧩 the first right guess (live/karaoke.py pays it through live_effects)
GUESS_DAY_CAP = 25               # xu one player may win from guesses per Vietnam day
GUESS_HOST_DAY = 10              # paid rounds one host may give per Vietnam day
ROOM_CAP = 30                    # people per public room (owner 06/10: "khoảng 30")
CLUE_WORDS = 12                  # a lyric clue: a short snippet, at most this many words (owner 06/10)
CLUE_LEN = 90
ANSWER_LEN = 60
ANSWERS_MAX = 3                  # "Nơi này có anh / Noi nay co anh": alternatives split by "/"
BLANK = '___'
TITLE_LEN = 100
CACHE_OK_SECS = 7 * 86400        # a playable song is checked again after a week
CACHE_BAD_SECS = 86400           # a blocked or gone one after a day
OEMBED = 'https://www.youtube.com/oembed?format=json&url='
OEMBED_TIMEOUT = 4.0
REASONS = ('spam', 'rude', 'private', 'scam', 'other', 'minor')   # live/chat.py REASONS ('minor' first in the queue)
SAFETY = 'minor'
REPORTS_MAX = 60
ADMIN_ACTS = ('skip', 'kick', 'close', 'ban', 'unban', 'mute', 'keep', 'end_round')
ROOM_RX = re.compile(r'kara:[a-z]{2,8}(?:-[2-9])?')
VID_RX = re.compile(r'[A-Za-z0-9_-]{11}')
RID_RX = re.compile(r'[A-Za-z0-9\-]{8,64}')
TICKET_RX = re.compile(r'k[qt]-[0-9a-f]{24}|kf-[0-9a-f]{24}-\d{8}')
PID_RX = re.compile(r'[0-9a-f]{16}')
HOSTS = ('youtube.com', 'youtube-nocookie.com')
LABEL_QUEUE = '🎤 Phòng hát'
LABEL_TIP = '🎤 Tặng xu ca sĩ'
DAY = 86400


class KaraError(Exception):
    def __init__(self, message: str, code: str = 'kara_error', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(cond, message: str, code: str = 'kara_error', status: int = 400):
    if not cond:
        raise KaraError(message, code, status)


def now() -> float:
    return time.time()


def vn_day(t: float | None = None) -> str:
    return time.strftime('%Y-%m-%d', time.gmtime((now() if t is None else t) + 7 * 3600))


def day_start(t: float | None = None) -> float:
    t = now() if t is None else t
    return t - ((t + 7 * 3600) % DAY)


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- links
def parse_vid(link) -> str | None:
    """The 11-character YouTube id of a link, or None (KARAOKE_DESIGN §4, the prototype's ytId)."""
    s = str(link or '').strip()
    if len(s) > 400:
        return None
    if VID_RX.fullmatch(s):
        return s
    try:
        u = urlsplit(s)
    except ValueError:
        return None
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password:
        return None
    try:
        port = u.port
    except ValueError:
        return None
    if port not in (None, 80, 443):
        return None
    host = re.sub(r'^(?:www|m|music)\.', '', u.hostname.lower())
    vid = None
    if host == 'youtu.be':
        vid = u.path[1:].split('/')[0]
    elif host in HOSTS:
        if u.path in ('/watch', '/watch/'):
            vid = (parse_qs(u.query).get('v') or [''])[0]
        else:
            m = re.match(r'^/(?:embed|shorts|live|v)/([A-Za-z0-9_-]{11})(?:[/?]|$)', u.path)
            vid = m.group(1) if m else None
    return vid if vid and VID_RX.fullmatch(vid) else None


def _filters():
    from live import filters   # pure (no I/O, no websockets): the chat's own cleaning and masking
    return filters


def clean_title(title) -> str:
    """A song title as players see it: one line, TITLE_LEN characters, heavy words as *, links/numbers •••."""
    f = _filters()
    t = f.clean(str(title or '')[:TITLE_LEN * 2].replace('\n', ' '), TITLE_LEN * 2, 1) or ''
    t = f.mask(t)[:TITLE_LEN].strip()
    return t or 'Bài hát YouTube'


# ---------------------------------------------------------------- 🧩 Đoán bài (pure; live/karaoke.py uses them)
def fold(text) -> str:
    """Lower case, no tone marks (đ → d), letters and digits only, one space between words."""
    t = unicodedata.normalize('NFD', str(text or '').lower()).replace('đ', 'd')
    t = ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn')
    t = re.sub(r"[^0-9a-z]+", ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


_FILLER = re.compile(r'^(?:bai|bai hat|la|la bai|chac la|hinh nhu|dap an|dap an la)\s+')


def answers(raw) -> list:
    """The host's answer: 1..ANSWERS_MAX alternatives split by '/', each folded; [] when unusable."""
    if not isinstance(raw, str) or not raw.strip() or len(raw) > ANSWER_LEN * 2:
        return []
    out = []
    for part in raw.split('/'):
        k = fold(part)
        if 2 <= len(k) <= ANSWER_LEN and k not in out:
            out.append(k)
    return out[:ANSWERS_MAX] if len(raw.strip()) <= ANSWER_LEN else []


def match(guess, keys: list) -> str:
    """'yes' (right), 'near' (close: told privately) or 'no'. Accent-insensitive and normalised: tone marks, case,
    punctuation and spacing never count; "bài …"/"là …" in front is ignored; a guess holding the whole answer counts;
    a small typo counts on longer answers (similarity ≥ 0.86 at 8+ letters)."""
    g = fold(guess)
    if not g or not keys:
        return 'no'
    g2 = _FILLER.sub('', g)
    best = 0.0
    for k in keys:
        if g in (k,) or g2 == k:
            return 'yes'
        if len(k) >= 4 and re.search(r'(?:^| )' + re.escape(k) + r'(?: |$)', g) and len(g) <= len(k) + 20:
            return 'yes'
        a, b = g2.replace(' ', ''), k.replace(' ', '')
        if a == b:
            return 'yes'
        r = difflib.SequenceMatcher(None, a, b).ratio()
        best = max(best, r)
        if len(b) >= 8 and r >= 0.86:
            return 'yes'
    return 'near' if best >= 0.72 else 'no'


def _is_emoji_char(ch: str) -> bool:
    cp = ord(ch)
    if ch in ('‍', '️', '⃣', ' '):
        return True
    if 0x1F1E6 <= cp <= 0x1F1FF or 0x1F3FB <= cp <= 0x1F3FF:   # flags, skin tones
        return True
    cat = unicodedata.category(ch)
    return cat == 'So' or (cat == 'Sm' and cp > 0x2000) or 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF


def _emoji_base(ch: str) -> bool:
    """A character that is one emoji by itself (not a joiner, a variation selector, a skin tone or a space)."""
    cp = ord(ch)
    if ch in ('‍', '️', '⃣', ' ') or 0x1F3FB <= cp <= 0x1F3FF:
        return False
    return _is_emoji_char(ch)


def check_clue(mode, clue) -> str:
    """A round's clue, cleaned; raises KaraError when it does not fit the mode.
    lyric: one line of at most CLUE_WORDS words (a short snippet, never a whole verse) with at least one blank
    (BLANK, or 2+ underscores, or …); emoji: emoji only (2 to 12 of them), no letters or digits."""
    need(mode in ('lyric', 'emoji'), 'Chọn đoán qua lời hoặc qua emoji nhé.', 'bad_mode')
    need(isinstance(clue, str) and 0 < len(clue) <= CLUE_LEN * 2, 'Gợi ý chưa hợp lệ.', 'bad_clue')
    f = _filters()
    text = f.clean(clue.replace('\n', ' '), CLUE_LEN * 2, 1)
    need(text, 'Gợi ý chưa hợp lệ.', 'bad_clue')
    if mode == 'emoji':
        need(all(_is_emoji_char(ch) for ch in text), 'Chỉ dùng emoji thôi nha 🙂', 'bad_clue')
        n = sum(1 for ch in text if _emoji_base(ch))
        need(2 <= n <= 12 and len(text) <= 64, 'Từ 2 tới 12 emoji nhé.', 'bad_clue')
        return text
    text = re.sub(r'_{2,}|…|\.{3,}', BLANK, text)
    words = text.split()
    need(len(words) <= CLUE_WORDS, f'Một câu ngắn thôi, tối đa {CLUE_WORDS} chữ.', 'clue_long')
    need(len(text) <= CLUE_LEN, f'Một câu ngắn thôi, tối đa {CLUE_LEN} ký tự.', 'clue_long')
    blanks = sum(1 for w in words if BLANK in w)
    need(blanks >= 1, 'Che ít nhất một chữ bằng ___ nhé.', 'no_blank')
    need(len(words) - blanks >= 2, 'Để lại vài chữ làm gợi ý nhé.', 'bad_clue')
    return f.mask(text)


def answer_words(keys: list) -> int:
    return len(keys[0].split()) if keys else 0


# ---------------------------------------------------------------- oEmbed (the network)
def _http_get(url: str, timeout: float) -> tuple:
    """(status, body bytes) of one GET; (0, b'') when the network fails. Tests replace this function."""
    req = urllib.request.Request(url, headers={'User-Agent': 'PhoCoChuyen/karaoke (+https://phocochuyen.io.vn)'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310 - a fixed https host
            return r.status, r.read(65536)
    except urllib.error.HTTPError as e:
        return e.code, b''
    except (urllib.error.URLError, OSError, ValueError):
        return 0, b''


def oembed(vid: str) -> tuple:
    """(ok, why, title, channel); ok None when YouTube did not answer (not cached)."""
    status, body = _http_get(OEMBED + quote(f'https://www.youtube.com/watch?v={vid}', safe=''), OEMBED_TIMEOUT)
    if status == 200:
        try:
            d = json.loads(body.decode('utf-8', 'replace'))
        except ValueError:
            d = {}
        return 1, '', str(d.get('title') or ''), str(d.get('author_name') or '')
    if status in (401, 403):
        return 0, 'blocked', '', ''
    if status in (400, 404):
        return 0, 'gone', '', ''
    return None, 'busy', '', ''


WHY_TEXT = dict(blocked='Video này không cho phát ngoài YouTube.', gone='Video không còn trên YouTube.',
                banned='Bài này đã bị tắt trong Phòng hát.')


def _song_view(r: dict) -> dict:
    ok = int(r['ok']) == 1 and not int(r['banned'])
    why = 'banned' if int(r['banned']) else (r['why'] or '')
    return dict(vid=r['vid'], title=r['title'], channel=r['channel'], ok=ok, why=why, text=WHY_TEXT.get(why, ''))


def song(store, vid: str) -> dict | None:
    with store.connect() as db:
        r = db.execute('SELECT * FROM kara_songs WHERE vid=?', (vid,)).fetchone()
    return dict(r) if r else None


def check_song(store, url, fetch_ok=lambda: True) -> dict:
    """POST /api/karaoke/song: {vid, title, channel, ok, why, text} for a pasted link (cached; one oEmbed call per new
    song). fetch_ok(): False when the outbound budget is spent (the server's shared rate limit)."""
    vid = parse_vid(url)
    need(vid, 'Link YouTube chưa đúng. Dán link bài hát nhé.', 'bad_link')
    t = now()
    r = song(store, vid)
    if r and (int(r['banned']) or t - float(r['checked_at']) < (CACHE_OK_SECS if int(r['ok']) else CACHE_BAD_SECS)):
        return _song_view(r)
    need(fetch_ok(), 'Đang kiểm tra nhiều bài quá, thử lại sau ít phút nhé.', 'busy', 429)
    ok, why, title, channel = oembed(vid)
    need(ok is not None, 'YouTube chưa trả lời, thử lại nhé.', 'busy', 503)
    title = clean_title(title) if ok else (r['title'] if r else '')
    channel = clean_title(channel)[:60] if ok and channel else ''

    def run(db):
        db.execute('INSERT INTO kara_songs(vid, title, channel, ok, why, checked_at) VALUES(?, ?, ?, ?, ?, ?) '
                   'ON CONFLICT(vid) DO UPDATE SET title=excluded.title, channel=excluded.channel, ok=excluded.ok, '
                   'why=excluded.why, checked_at=excluded.checked_at', (vid, title, channel, ok, why, t))
    store.transaction(run)
    return _song_view(song(store, vid))


# ---------------------------------------------------------------- money: the queue ticket and tips
def _who(store, token: str) -> tuple:
    from . import marriage as mr
    sid, display = mr.whoami(store, token)
    need(sid, 'Tải lại trang để bắt đầu phiên chơi.', 'session_missing', 401)
    need(display, 'Tạo tài khoản để hát cùng mọi người nhé.', 'account_required', 403)
    return sid, display


def _muted(db, sid: str) -> bool:
    r = db.execute('SELECT until FROM chat_mutes WHERE pid=?', (pid_of(sid),)).fetchone()
    return bool(r and float(r['until']) > now())


def _old_enough(db, sid: str) -> bool:
    r = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    if not r:
        return False
    cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now() - ACCOUNT_DAYS * DAY))
    return str(r['created_at']) <= cut


def _blocked(db, a_sid: str, b_sid: str) -> bool:
    a, b = pid_of(a_sid), pid_of(b_sid)
    if db.execute('SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?)', (a, b, b, a)).fetchone():
        return True
    return bool(db.execute('SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?)',
                           (a_sid, b_sid, b_sid, a_sid)).fetchone())


def _pay_row(j: dict, price: int, label: str, unit: str) -> int:
    """`price` out of the wallet into today's row for `label` (one a life day, updated in place like the fair photo's
    row), else a new row; returns the count now on it."""
    from . import journey as jr
    for row in reversed(j['history'][-12:]):
        if not isinstance(row, dict) or row.get('day') != j['life_day']:
            break
        m = re.fullmatch(re.escape(label) + r' · (\d{1,6}) ' + unit, str(row.get('label', '')))
        if row.get('kind') in (WRITE_KIND, KIND) and row.get('career') is None and m and abs(row['amount'] - price) <= 10**7:
            n = min(10**6, int(m.group(1)) + 1)
            j['wallet'] -= price
            row['amount'] -= price
            row['label'] = f'{label} · {n} {unit}'
            if j['wallet'] < 0:
                j['in_debt'] = True
            return n
    jr._wallet(j, -price, WRITE_KIND, f'{label} · 1 {unit}')
    return 1


def ticket_id(sid: str, rid: str, prefix: str = 'kq') -> str:
    return f'{prefix}-' + hashlib.sha256(f'{sid}|{rid}'.encode()).hexdigest()[:24]


def queue(store, token: str, d: dict) -> dict:
    """POST /api/karaoke/queue {rid}: a ticket for one song in any room. Free for the first of the Vietnam day, else
    QUEUE_XU from the wallet. An unused ticket of the last TICKET_DAYS is handed back instead (nothing paid)."""
    from . import marriage as mr
    sid, _ = _who(store, token)
    rid = d.get('rid')
    need(isinstance(rid, str) and RID_RX.fullmatch(rid), 'Mã lượt không hợp lệ. Tải lại trang nhé.', 'bad_rid')
    t, day = now(), vn_day()
    with store.connect() as db:
        need(not _muted(db, sid), 'Bạn đang bị tạm khóa chat, chưa xếp bài được.', 'muted', 403)
        old = db.execute("SELECT id, amount FROM kara_tickets WHERE sid=? AND kind='queue' AND used=0 AND at>? ORDER BY at LIMIT 1",
                         (sid, t - TICKET_DAYS * DAY)).fetchone()
        if old:
            return dict(ok=True, e=old['id'], price=0, again=True, changed=False)
        free = not db.execute("SELECT 1 FROM kara_tickets WHERE sid=? AND kind='queue' AND day=? LIMIT 1", (sid, day)).fetchone()
    if free:
        tid = f'kf-{hashlib.sha256(sid.encode()).hexdigest()[:24]}-{day.replace("-", "")}'
        try:
            store.transaction(lambda db: db.execute(
                "INSERT INTO kara_tickets(id, sid, kind, amount, day, at) VALUES(?, ?, 'queue', 0, ?, ?)", (tid, sid, day, t)))
        except Exception as e:  # noqa: BLE001 - a double tap: the first one made the free ticket
            from . import db as dbm
            if not isinstance(e, dbm.IntegrityError):
                raise
            raise KaraError('Thử lại nhé.', 'busy', 409) from None
        return dict(ok=True, e=tid, price=0, free=True, changed=False)
    tid = ticket_id(sid, rid)
    loaded = mr._read_state(store, sid)
    need(loaded, 'Không tìm thấy tiến trình.', 'session_missing', 404)

    def fn(s):
        j = s.get('journey') or {}
        need(j.get('story'), 'Phòng hát thu phí trong hành trình. Hôm nay bạn đã hát lượt miễn phí rồi.', 'not_story')
        need(int(j['wallet']) >= QUEUE_XU, f'Ví còn {max(0, int(j["wallet"]))} xu, chưa đủ {QUEUE_XU} xu xếp bài.', 'not_enough')
        _pay_row(j, QUEUE_XU, LABEL_QUEUE, 'bài')

    def ops(db):
        db.execute("INSERT INTO kara_tickets(id, sid, kind, amount, day, at) VALUES(?, ?, 'queue', ?, ?, ?)", (tid, sid, QUEUE_XU, day, t))
    from . import db as dbm
    try:
        mr._mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:   # the same rid again: that ticket exists (paid once)
        return dict(ok=True, e=tid, price=0, again=True, changed=False)
    except mr.MarriageError as e:
        raise KaraError(e.message, e.code, e.status) from None
    return dict(ok=True, e=tid, price=QUEUE_XU, changed=True)


def tip(store, token: str, d: dict) -> dict:
    """POST /api/karaoke/tip {e: the song's ticket, xu, rid}: xu from my wallet to its singer (TIP_KEEP %), once per rid."""
    from . import marriage as mr
    sid, display = _who(store, token)
    rid, e, xu = d.get('rid'), d.get('e'), d.get('xu')
    need(isinstance(rid, str) and RID_RX.fullmatch(rid), 'Mã giao dịch không hợp lệ. Tải lại trang nhé.', 'bad_rid')
    need(isinstance(e, str) and TICKET_RX.fullmatch(e), 'Bài này không còn trên sân khấu.', 'gone', 404)
    need(type(xu) is int and xu in TIP_CHIPS, f'Chọn {", ".join(map(str, TIP_CHIPS))} xu nhé.', 'bad_amount')
    tid = ticket_id(sid, rid, 'kt')
    t, day = now(), vn_day()
    with store.connect() as db:
        if db.execute('SELECT 1 FROM kara_tickets WHERE id=?', (tid,)).fetchone():
            return dict(ok=True, xu=0, again=True, changed=False)
        song_t = db.execute("SELECT sid, played FROM kara_tickets WHERE id=? AND kind='queue'", (e,)).fetchone()
        need(song_t and song_t['played'] is not None and float(song_t['played']) > t - TIP_WINDOW, 'Bài này không còn trên sân khấu.', 'gone', 404)
        singer = song_t['sid']
        need(singer != sid, 'Không tự tặng mình được nha 😄', 'self')
        need(not _muted(db, sid), 'Bạn đang bị tạm khóa chat.', 'muted', 403)
        need(_old_enough(db, sid), f'Tặng xu mở khi tài khoản đủ {ACCOUNT_DAYS} ngày.', 'too_new', 403)
        need(db.execute('SELECT 1 FROM accounts WHERE sid=?', (singer,)).fetchone(), 'Ca sĩ chưa có tài khoản.', 'gone', 404)
        need(not _blocked(db, sid, singer), 'Không tặng được cho người này.', 'blocked', 403)
        singer_name = mr._display(db, singer)
    got = xu * TIP_KEEP // 100
    loaded = mr._read_state(store, sid)
    need(loaded, 'Không tìm thấy tiến trình.', 'session_missing', 404)

    def fn(s):
        j = s.get('journey') or {}
        need(j.get('story'), 'Tặng xu chỉ có trong hành trình.', 'not_story')
        need(int(j['wallet']) >= xu, f'Ví còn {max(0, int(j["wallet"]))} xu.', 'not_enough')
        from . import journey as jr
        jr._wallet(j, -xu, WRITE_KIND, f'{LABEL_TIP} {singer_name}'[:120])

    def ops(db):
        db.execute('SELECT pg_advisory_xact_lock(17823, hashtext(?))', ('kara_tip:' + singer,))   # caps hold under concurrency
        sent = int(db.execute("SELECT COALESCE(SUM(amount), 0) FROM kara_tickets WHERE sid=? AND kind='tip' AND day=?", (sid, day)).fetchone()[0])
        need(sent + xu <= TIP_SEND_DAY, f'Hôm nay bạn tặng đủ {TIP_SEND_DAY} xu rồi.', 'cap')
        recv = int(db.execute("SELECT COALESCE(SUM(got), 0) FROM kara_tickets WHERE to_sid=? AND kind='tip' AND day=?", (singer, day)).fetchone()[0])
        need(recv + got <= TIP_GOT_DAY, 'Ca sĩ đã nhận đủ xu hôm nay rồi.', 'cap_got')
        db.execute("INSERT INTO kara_tickets(id, sid, kind, ref, to_sid, amount, got, day, at) VALUES(?, ?, 'tip', ?, ?, ?, ?, ?, ?)",
                   (tid, sid, e, singer, xu, got, day, t))
        db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, 'coins', ?, ?, 'pending', ?)",
                   ('ktip:' + tid, singer, got, json.dumps(dict(src='kara_tip'), separators=(',', ':')), t))
        db.execute('SELECT pg_notify(?, ?)', ('mnl_live', json.dumps(dict(op='kara_tip', e=e, frm=pid_of(sid), name=display[:24], to=pid_of(singer),
                                                                          xu=xu, got=got), ensure_ascii=False, separators=(',', ':'))))
    from . import db as dbm
    try:
        mr._mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:
        return dict(ok=True, xu=0, again=True, changed=False)
    except mr.MarriageError as err:
        raise KaraError(err.message, err.code, err.status) from None
    return dict(ok=True, xu=xu, got=got, to=singer_name, changed=True)


# ---------------------------------------------------------------- admin
def _notify(db, event: dict) -> None:
    db.execute('SELECT pg_notify(?, ?)', ('mnl_live', json.dumps(event, ensure_ascii=False, separators=(',', ':'))))


def admin_view(store) -> dict:
    """GET /api/admin/karaoke: open reports by target (🛟 'minor' first), with the song or the player's last bubbles
    in the rooms; banned songs."""
    with store.connect() as db:
        rows = db.execute("SELECT r.target, r.reason, r.at FROM reports r LEFT JOIN kara_reviews v ON v.target=r.target "
                          "WHERE r.kind='kara' AND (v.at IS NULL OR r.at > v.at) ORDER BY r.at DESC LIMIT 500").fetchall()
        items: dict = {}
        for r in rows:
            it = items.setdefault(r['target'], dict(target=r['target'], reasons={}, n=0, last=float(r['at'])))
            it['reasons'][r['reason']] = it['reasons'].get(r['reason'], 0) + 1
            it['n'] += 1
        out = sorted(items.values(), key=lambda x: (SAFETY not in x['reasons'], -x['last']))[:REPORTS_MAX]
        for it in out:
            kind, ref = it['target'].split(':', 1) if ':' in it['target'] else ('', it['target'])
            it['kind'], it['ref'], it['safety'] = kind, ref, SAFETY in it['reasons']
            if kind == 'v':
                s = db.execute('SELECT title, banned FROM kara_songs WHERE vid=?', (ref,)).fetchone()
                it['title'], it['banned'] = (s['title'], int(s['banned'])) if s else ('', 0)
            elif kind == 'p':
                msgs = db.execute("SELECT channel, name, text, at FROM chat_messages WHERE pid=? AND channel LIKE 'kara:%' ORDER BY id DESC LIMIT 5",
                                  (ref,)).fetchall()
                it['msgs'] = [dict(ch=m['channel'], name=m['name'], text=m['text'], at=float(m['at'])) for m in msgs]
                it['name'] = msgs[0]['name'] if msgs else ''
        banned = [dict(vid=r['vid'], title=r['title'], by=r['banned_by'] or '', at=float(r['banned_at'] or 0))
                  for r in db.execute('SELECT vid, title, banned_by, banned_at FROM kara_songs WHERE banned=1 ORDER BY banned_at DESC LIMIT 100').fetchall()]
    return dict(items=out, banned=banned, rooms=[f'kara:{k}' for k in ('tre', 'bolero', 'qt')], reasons=list(REASONS), now=now())


def admin_act(store, admin: str, data: dict) -> dict:
    """POST /api/admin/karaoke {act, room?, pid?, vid?, target?, minutes?}: skip / close / end_round a room, kick a
    player out of every room for an hour, ban / unban a song, mute (the chat's mute: no bubbles, no queue), keep (the
    reports on a target are reviewed). The live service applies room acts at once (NOTIFY op 'kara')."""
    act = data.get('act')
    need(act in ADMIN_ACTS, 'Thao tác không hợp lệ.')
    t = now()
    admin = str(admin or 'admin')[:40]
    if act == 'mute':
        from . import live_chat
        try:
            out = live_chat.act(store, admin, dict(op='mute', pid=data.get('pid'), minutes=data.get('minutes', 60), reason='Phòng hát'))
        except live_chat.ChatAdminError as e:
            raise KaraError(e.message, e.code, e.status) from None
        store.transaction(lambda db: _review(db, 'p:' + data['pid'], 'mute', admin, t))
        return out
    if act in ('ban', 'unban'):
        vid = data.get('vid')
        need(isinstance(vid, str) and VID_RX.fullmatch(vid), 'Mã bài không hợp lệ.')

        def run(db):
            if act == 'ban':
                db.execute("INSERT INTO kara_songs(vid, title, channel, ok, why, checked_at, banned, banned_by, banned_at) VALUES(?, '', '', 0, '', 0, 1, ?, ?) "
                           'ON CONFLICT(vid) DO UPDATE SET banned=1, banned_by=excluded.banned_by, banned_at=excluded.banned_at', (vid, admin, t))
                _review(db, 'v:' + vid, 'ban', admin, t)
                _notify(db, dict(op='kara', act='ban', vid=vid))
            else:
                db.execute('UPDATE kara_songs SET banned=0, banned_by=?, banned_at=? WHERE vid=?', (admin, t, vid))
        store.transaction(run)
        return dict(ok=True, act=act, vid=vid)
    if act == 'keep':
        target = data.get('target')
        need(isinstance(target, str) and re.fullmatch(r'(?:p:[0-9a-f]{16}|v:[A-Za-z0-9_-]{11})', target), 'Mục không hợp lệ.')
        store.transaction(lambda db: _review(db, target, 'keep', admin, t))
        return dict(ok=True, act=act, target=target)
    if act == 'kick':
        pid = data.get('pid')
        need(isinstance(pid, str) and PID_RX.fullmatch(pid), 'Người chơi không hợp lệ.')

        def run(db):
            _review(db, 'p:' + pid, 'kick', admin, t)
            _notify(db, dict(op='kara', act='kick', pid=pid))
        store.transaction(run)
        return dict(ok=True, act=act, pid=pid)
    room = data.get('room')
    need(isinstance(room, str) and ROOM_RX.fullmatch(room), 'Phòng không hợp lệ.')
    store.transaction(lambda db: _notify(db, dict(op='kara', act=act, room=room)))
    return dict(ok=True, act=act, room=room)


def _review(db, target: str, verdict: str, admin: str, t: float) -> None:
    db.execute('INSERT INTO kara_reviews(target, verdict, by_admin, at) VALUES(?, ?, ?, ?) ON CONFLICT(target) DO UPDATE SET '
               'verdict=excluded.verdict, by_admin=excluded.by_admin, at=excluded.at', (target, verdict, admin, t))


def forget(store, token: str) -> None:
    """A player deletes their data: their tickets and the reviews about them go; reports they made stay anonymous."""
    sid = store.key(token)
    pid = pid_of(sid)
    with store.connect() as db:
        db.execute('DELETE FROM kara_tickets WHERE sid=?', (sid,))
        db.execute('UPDATE kara_tickets SET to_sid=? WHERE to_sid=?', ('gone', sid))
        db.execute('DELETE FROM kara_reviews WHERE target=?', ('p:' + pid,))
        db.execute("UPDATE reports SET reporter='gone:' || md5(reporter || target) WHERE reporter=? AND kind='kara'", (pid,))
