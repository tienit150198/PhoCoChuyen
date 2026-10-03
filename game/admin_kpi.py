"""📊 Tổng quan đầu tư: the operator page's numbers for a buyer or a franchisee, in one payload.

Computed by the admin job (admin_stats._Job.pass_kpi, every KPI_EVERY seconds while an operator looks), never on a
request: GET /api/admin/stats/section?name=invest serves the job's copy. Every part reads small stat tables or
indexes only, read-only, under its own time budget (admin_stats._read); a part that fails or runs out of time is
left out and named in `errors` (the page says so) instead of showing a wrong number.

Sources (no save is parsed here; the saves sample comes from the job's saves pass):
* stat_kpi_daily (game/kpi.py freeze): the finished days' numbers, frozen once, never changed;
* stat_births / stat_active / stat_players: today live and the cohorts;
* stat_counters (game/kpi.py): xu flows, devices, HTTP classes, latency, peaks, uptime, AI (collected from the
  release that adds them: the page says "đang thu thập từ <ngày>");
* stat_play / stat_play_daily (play time), stat_milestones, stat_actions (features), stat_acquisition, stat_loads,
  stat_client_errors, player_feedback, leaderboard, social tables (friends, couples, chat, weddings, dates).

Every number has an entry in DEFS (label, definition, formula, how it adds up over a period): the page shows it in
the ⓘ, the CSV and the printed report carry it. Exports (to_csv, and the page's printed report) are aggregates only
and hide any cell under SMALL players.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import math
import os
import time

from . import __version__
from . import admin_stats as st
from . import kpi
from . import retention as rt

KPI_MS = int(os.environ.get('ADMIN_STATS_KPI_MS', '20000') or 20000)        # all reads of one part
KPI_STATEMENT_MS = int(os.environ.get('ADMIN_STATS_KPI_STATEMENT_MS', '5000') or 5000)
MAX_DAYS = 400            # days on the series axis at most
SMALL = 5                 # exports: a count of players under this is shown as "<5", a percentage over fewer is hidden
FEW = 30                  # the page flags a percentage over fewer players than this ("ít dữ liệu")
PERIODS = (7, 30, 90, 0)  # 0 = since the start of the history
PARTS = ('growth', 'activity', 'retention', 'engagement', 'economy', 'quality', 'acquisition', 'infra')
LAUNCH_DAY = '2026-09-28'  # first public build (git history); the day log (stat_births) starts later
PLAY_EXACT_DAY = '2026-10-01'   # play time exact from 01/10 00:31 (before: estimated from receipts)
FEATURE_LABELS = dict(work='Làm nghề (phục vụ khách)', bank='Ngân hàng & đầu tư', learn='Học & chứng chỉ', home='Nhà & nội thất',
                      wardrobe='Tủ đồ & màu sắc', needs='Nhu cầu nhân vật', board='Bảng tin cư dân', life='Đời sống',
                      close='Thân thiết', story='Cốt truyện & sự kiện', fair='Hội chợ', risk='Bảo hiểm & tiệm vàng', jobs='Tìm việc / đổi nghề')


# ---------------------------------------------------------------- definitions (shown in the ⓘ and the exports)
def _d(label, d, f, unit='', agg='last', since=None, kind='n'):
    """label; d: what it means (plain words); f: how it is computed; unit; agg: how the period selector sums it
    (sum/avg/last/max); since: which collection start applies; kind: n (players), pct, xu, ms, min, num."""
    return dict(label=label, d=d, f=f, unit=unit, agg=agg, since=since, kind=kind)


DEFS = {
    # growth
    'saves_total': _d('Tổng bản lưu', 'Mọi bản lưu đang có trong cơ sở dữ liệu, kể cả người mở game rồi đi ngay và bot.',
                      'COUNT(*) FROM sessions'),
    'players_total': _d('Người đã chơi', 'Bản lưu có ít nhất một thao tác chơi thật của người chơi (không tính bản lưu chỉ được nâng cấp phiên bản khi mở lại).',
                        'sessions có revision > 0 và (có ngày hoạt động trong stat_active/stat_players, hoặc tạo trước khi có nhật ký ngày)'),
    'accounts_total': _d('Tài khoản', 'Người chơi đã đăng ký tài khoản (tên đăng nhập + mật khẩu).', 'COUNT(*) FROM accounts'),
    'guests_played': _d('Khách đã chơi', 'Người đã chơi nhưng chưa đăng ký tài khoản.', 'Người đã chơi − người có tài khoản'),
    'account_rate': _d('Tỉ lệ có tài khoản', 'Trong những người đã chơi, bao nhiêu phần trăm đã đăng ký.', 'bản lưu có tài khoản ÷ người đã chơi', '%', kind='pct'),
    'new_sessions': _d('Lượt mở game mới', 'Bản lưu mới được tạo trong ngày (mỗi trình duyệt/thiết bị mới một bản; gồm cả bot và người chỉ mở rồi đi).',
                       'stat_births theo ngày Việt Nam', agg='sum', since='births'),
    'new_players': _d('Người chơi mới', 'Bản lưu tạo trong ngày VÀ có thao tác chơi ngay trong ngày đó. Đây là "nhóm" (cohort) dùng để tính giữ chân.',
                      'stat_births ∩ stat_active cùng ngày; ngày đã qua: số đông cứng (stat_kpi_daily)', agg='sum', since='births'),
    'new_accounts': _d('Tài khoản mới', 'Tài khoản đăng ký trong ngày (giờ Việt Nam).', 'accounts.created_at (UTC) đổi sang ngày UTC+7', agg='sum'),
    'activation': _d('Tỉ lệ kích hoạt', 'Trong các lượt mở game mới, bao nhiêu phần trăm thực sự chơi ngay ngày đầu. Bot và người mở thử làm tỉ lệ này thấp.',
                     'người chơi mới ÷ lượt mở game mới', '%', agg='ratio:new_players/new_sessions', kind='pct', since='births'),
    'first_seen': _d('Lần đầu hoạt động', 'Người có ngày hoạt động đầu tiên (kể từ khi có nhật ký) rơi vào ngày này, gồm cả người tạo bản lưu trước đó.',
                     'stat_players.first_day', agg='sum', since='births'),
    'cum_players': _d('Người từng hoạt động (cộng dồn)', 'Tổng số người đã có ít nhất một ngày hoạt động tính đến hết ngày đó.',
                      'cộng dồn "lần đầu hoạt động"', since='births'),
    # activity
    'dau': _d('DAU', 'Số người chơi có thao tác trong ngày (giờ Việt Nam, 00:00–24:00).', 'COUNT(stat_active) theo ngày', agg='avg', since='births'),
    'wau': _d('WAU', 'Số người khác nhau có thao tác trong 7 ngày tính đến hết ngày đó.', 'COUNT(DISTINCT sid) stat_active, 7 ngày', since='births'),
    'mau': _d('MAU', 'Số người khác nhau có thao tác trong 30 ngày tính đến hết ngày đó.', 'COUNT(DISTINCT sid) stat_active, 30 ngày', since='births'),
    'stickiness': _d('Độ dính (DAU/MAU)', 'Một người chơi trong tháng quay lại trung bình bao nhiêu phần trăm số ngày. 20% ≈ 6 ngày/tháng.',
                     'DAU ÷ MAU của cùng ngày', '%', agg='avg', kind='pct', since='births'),
    'returning': _d('Người quay lại', 'DAU trừ người chơi mới của ngày đó.', 'DAU − người chơi mới', agg='avg', since='births'),
    'resurrected': _d('Người trở lại sau ≥7 ngày', 'Người hoạt động hôm nay mà lần hoạt động trước cách đó từ 8 ngày trở lên.',
                      'stat_players.last_day ≤ ngày − 8 trước khi cập nhật', agg='sum', since='kpi'),
    'peak_online': _d('Đỉnh người online', 'Số người có thao tác trong 5 phút gần nhất, lấy mức cao nhất trong ngày (đo mỗi phút).',
                      'MAX mỗi phút COUNT(sessions.updated_at ≥ now − 5 phút)', agg='max', since='counters'),
    'peak_cmd_min': _d('Đỉnh thao tác/phút', 'Số thao tác chơi mỗi phút của mọi tiến trình máy chủ, mức cao nhất trong ngày.',
                       'MAX mỗi phút (thao tác/phút)', agg='max', since='counters'),
    'play_players': _d('Người có thời gian chơi', 'Số người có ít nhất một thao tác được tính giờ trong ngày.', 'stat_play / stat_play_daily', agg='avg', since='play'),
    'avg_min': _d('Phút chơi / người / ngày', 'Thời gian chơi trung bình của một người trong một ngày. Một phiên kết thúc khi 5 phút không có thao tác.',
                  'tổng giây ÷ số người (ngày)', 'phút', agg='wavg:play_players', kind='min', since='play'),
    'median_min': _d('Trung vị phút chơi', 'Một nửa người chơi chơi ít hơn mức này mỗi ngày (không bị vài người chơi rất lâu kéo lên).',
                     'trung vị phân bố giây/người', 'phút', agg='avg', kind='min', since='play'),
    'sessions_pp': _d('Phiên / người / ngày', 'Số lần vào chơi (phiên) trung bình của một người trong ngày.', 'số phiên ÷ số người', agg='wavg:play_players', kind='num', since='play'),
    'hours_total': _d('Tổng giờ chơi', 'Tổng số giờ mọi người chơi trong ngày.', 'tổng giây ÷ 3600', 'giờ', agg='sum', kind='num', since='play'),
    'cmds': _d('Thao tác chơi', 'Số thao tác chơi (mỗi lần bấm làm gì đó trong game) đã ghi.', 'stat_play.cmds', agg='sum', kind='num', since='play'),
    # retention
    'd1': _d('Giữ chân D1', 'Trong người chơi mới của một ngày, bao nhiêu phần trăm quay lại chơi đúng 1 ngày sau. Chỉ tính các nhóm đã qua hết ngày đó.',
             'Σ quay lại ngày+1 ÷ Σ người chơi mới (các ngày đủ điều kiện)', '%', kind='pct', since='births'),
    'd3': _d('Giữ chân D3', 'Như D1 nhưng đúng 3 ngày sau.', 'tương tự, ngày+3', '%', kind='pct', since='births'),
    'd7': _d('Giữ chân D7', 'Như D1 nhưng đúng 7 ngày sau.', 'tương tự, ngày+7', '%', kind='pct', since='births'),
    'd14': _d('Giữ chân D14', 'Như D1 nhưng đúng 14 ngày sau.', 'tương tự, ngày+14', '%', kind='pct', since='births'),
    'd30': _d('Giữ chân D30', 'Như D1 nhưng đúng 30 ngày sau.', 'tương tự, ngày+30', '%', kind='pct', since='births'),
    'rolling': _d('Giữ chân cuốn (rolling)', 'Phần trăm người chơi mới còn quay lại vào ngày k HOẶC bất kỳ ngày nào sau đó (luôn ≥ giữ chân đúng ngày).',
                  'có stat_active ở ngày ≥ ngày đầu + k', '%', kind='pct', since='births'),
    'wk_churn': _d('Tỉ lệ rời bỏ tuần', 'Trong người chơi của tuần trước, bao nhiêu phần trăm không chơi tuần này.',
                   'wk_churned ÷ wk_prev (tuần thứ Hai–Chủ nhật)', '%', kind='pct', since='kpi'),
    'wk_retained_pct': _d('Giữ chân tuần', 'Trong người chơi của tuần trước, bao nhiêu phần trăm chơi tiếp tuần này.', 'wk_retained ÷ wk_prev', '%', kind='pct', since='kpi'),
    'conversion': _d('Khách → tài khoản', 'Trong người chơi mới của 30 ngày đã qua, bao nhiêu phần trăm hiện đã đăng ký tài khoản.',
                     'người chơi mới có dòng trong accounts ÷ người chơi mới', '%', kind='pct', since='births'),
    'lifetime_days': _d('Số ngày hoạt động / người', 'Mỗi người đã chơi bao nhiêu ngày khác nhau (từ khi có nhật ký).', 'stat_players.days', 'ngày', kind='num', since='kpi'),
    # engagement
    'feature': _d('Dùng tính năng', 'Trong người chơi hoạt động, bao nhiêu phần trăm dùng tính năng này (trung bình mỗi ngày).',
                  'người dùng nhóm thao tác trong ngày (stat_actions) ÷ DAU', '%', kind='pct', since='kpi'),
    'board_players': _d('Người trên bảng xếp hạng', 'Người có tên trên bảng tổng (mọi người đã làm ít nhất một nơi).', "leaderboard board='all'"),
    'mastered_pct': _d('Đã thành thạo ≥1 nghề', 'Phần trăm người trên bảng tổng đã lên cấp 3 ở ít nhất một nơi làm.', "mastered ≥ 1 ÷ người trên bảng", '%', kind='pct'),
    'work_days_median': _d('Ngày làm việc (trung vị)', 'Một nửa người chơi đã làm ít hơn số ngày trong game này (cộng mọi nơi làm).', "trung vị leaderboard.days (board='all')", 'ngày', kind='num'),
    'milestone': _d('Cột mốc', 'Trong mọi người đã mở game từ khi đo phễu (01/10), bao nhiêu phần trăm đã đạt cột mốc (một số người cũ được ước tính).',
                    'stat_milestones theo key ÷ số "Mở game"', '%', kind='pct'),
    'chat_msgs': _d('Tin nhắn chat', 'Tin nhắn người chơi gửi trong chat chung trong ngày (không tính tin quản trị).', 'chat_messages theo ngày, adm = 0', agg='sum', since='kpi'),
    'chat_senders': _d('Người nhắn tin', 'Số người khác nhau gửi ít nhất một tin trong ngày.', 'COUNT(DISTINCT pid)', agg='avg', since='kpi'),
    'chat_share': _d('Tỉ lệ người nhắn tin', 'Người nhắn tin ÷ DAU của ngày.', 'chat_senders ÷ dau', '%', agg='ratio:chat_senders/dau', kind='pct', since='kpi'),
    'friend_pairs': _d('Cặp bạn bè', 'Số cặp đã kết bạn với nhau.', 'COUNT(friends) ÷ 2'),
    'with_friend': _d('Người có bạn', 'Số người có ít nhất một bạn.', 'COUNT(DISTINCT friends.sid)'),
    'couples': _d('Cặp đôi', 'Số cặp đang yêu hoặc đã cưới (chưa chia tay).', "couples chưa kết thúc"),
    'married': _d('Đã cưới', 'Số cặp đã kết hôn.', 'couples.married_at có giá trị'),
    'weddings_done': _d('Đám cưới đã tổ chức', 'Tiệc cưới trực tiếp đã diễn ra.', "wedding_parties status = 'done'"),
    'dates_30d': _d('Hẹn hò 30 ngày', 'Số buổi hẹn hò trực tiếp giữa hai người chơi trong 30 ngày.', 'live_dates.at'),
    # economy
    'xu_in': _d('Xu tạo ra', 'Xu người chơi nhận được qua thao tác (lương, bán hàng, lãi, vay…). Tiền chuyển giữa ví, quỹ nơi làm và ngân hàng không tính.',
                'Σ mức tăng (ví + quỹ nơi làm + ngân hàng) mỗi thao tác', 'xu', agg='sum', kind='xu', since='counters'),
    'xu_out': _d('Xu tiêu đi', 'Xu người chơi chi ra qua thao tác (mua sắm, nhà, học, trả nợ…).', 'Σ mức giảm mỗi thao tác', 'xu', agg='sum', kind='xu', since='counters'),
    'xu_net': _d('Xu ròng', 'Xu tạo ra trừ xu tiêu đi. Dương kéo dài = lạm phát (mỗi người ngày càng nhiều xu).', 'xu_in − xu_out', 'xu', agg='sum', kind='xu', since='counters'),
    'xu_in_pp': _d('Xu tạo ra / DAU', 'Xu tạo ra trong ngày chia cho số người chơi hôm đó.', 'xu_in ÷ dau', 'xu', agg='ratio1:xu_in/dau', kind='xu', since='counters'),
    'wallet_median': _d('Ví trung vị (mẫu)', 'Số xu giữa của người chơi gần đây (mẫu 400 bản lưu thay đổi gần nhất, không phải mẫu ngẫu nhiên).',
                        'trung vị ví trong mẫu', 'xu', kind='xu', since='wallet'),
    'revenue': _d('Doanh thu', 'Game chưa có thanh toán, quảng cáo hay gói trả phí: doanh thu = 0. Không ước tính.', 'chưa bật'),
    # quality
    'feedback': _d('Góp ý', 'Góp ý người chơi gửi trong game theo ngày.', 'player_feedback.created_at', agg='sum'),
    'feedback_per_100': _d('Góp ý / 100 DAU', 'Mức độ người chơi lên tiếng.', 'góp ý ÷ dau × 100', agg='ratio100:feedback/dau', kind='num'),
    'err_per_1k': _d('Lỗi trình duyệt / 1000 thao tác', 'Lỗi JavaScript trình duyệt báo về, chia cho số thao tác chơi.',
                     'stat_client_errors ÷ thao tác × 1000 (bỏ lỗi do tiện ích/ứng dụng bên ngoài)', agg='ratio1000:client_errors/cmds', kind='num'),
    'client_errors': _d('Lỗi trình duyệt', 'Số lỗi JavaScript báo về trong ngày (không tính lỗi của Zalo/tiện ích).', 'Σ stat_client_errors.count', agg='sum'),
    'http_5xx_pct': _d('Lỗi máy chủ (5xx)', 'Phần trăm câu trả lời API là lỗi máy chủ (500–599, gồm 503 "đang bận").', 'http:5xx ÷ mọi câu trả lời API',
                       '%', agg='ratio100:http_5xx/http_all', kind='pct', since='counters'),
    'lat_p50': _d('Độ trễ thao tác p50', 'Một nửa thao tác chơi được máy chủ xử lý nhanh hơn mức này (không tính mạng).', 'trung vị biểu đồ cmd_ms (mốc trên của ô)', 'ms', agg='avg', kind='ms', since='counters'),
    'lat_p95': _d('Độ trễ thao tác p95', '95% thao tác nhanh hơn mức này.', 'phân vị 95 cmd_ms', 'ms', agg='avg', kind='ms', since='counters'),
    'lat_p99': _d('Độ trễ thao tác p99', '99% thao tác nhanh hơn mức này.', 'phân vị 99 cmd_ms', 'ms', agg='avg', kind='ms', since='counters'),
    'uptime': _d('Thời gian hoạt động', 'Phần trăm số phút trong ngày máy chủ đang chạy (đo mỗi phút).', 'up_min ÷ số phút đã qua của ngày', '%', agg='avg', kind='pct', since='counters'),
    'load_p50': _d('Thời gian tải trang p50', 'Từ lúc mở trang đến khung hình đầu tiên của game, 7 ngày, trung vị.', 'stat_loads metric frame', 'ms', kind='ms'),
    'ai_calls': _d('Lượt gọi AI', 'Số lần game gọi mô hình ngôn ngữ (mọi tiến trình).', 'stat_counters ai:calls', agg='sum', since='counters'),
    # acquisition
    'source': _d('Nguồn người chơi', 'Nơi người chơi đến từ (utm_source hoặc trang giới thiệu; không có = trực tiếp).', 'stat_acquisition'),
    'device': _d('Thiết bị', 'Loại máy / hệ điều hành / trình duyệt của lượt mở game mới (theo User-Agent). Bot tách riêng.', 'stat_counters dev_*', since='counters'),
    # infra
    'db_bytes': _d('Dung lượng cơ sở dữ liệu', 'Kích thước cơ sở dữ liệu trên đĩa.', 'pg_database_size / tệp SQLite', 'byte'),
    'save_size': _d('Kích thước bản lưu', 'Dung lượng một bản lưu trong mẫu (PostgreSQL: sau nén).', 'pg_column_size(state) / octet_length', 'byte'),
}


# ---------------------------------------------------------------- small helpers
def _pct(k, n, digits: int = 1):
    return round(100 * k / n, digits) if n else None


def wilson(k: int, n: int, z: float = 1.96):
    """95% confidence interval (percent) of k successes out of n (Wilson): honest with small n."""
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(100 * max(0.0, mid - half), 1), round(100 * min(1.0, mid + half), 1)]


def _axis(first: str | None, today: str) -> list[str]:
    if not first or first > today:
        return [today]
    d0 = max(datetime.date.fromisoformat(first), datetime.date.fromisoformat(today) - datetime.timedelta(days=MAX_DAYS - 1))
    n = (datetime.date.fromisoformat(today) - d0).days + 1
    return [(d0 + datetime.timedelta(days=i)).isoformat() for i in range(n)]


def _col(days: list, by_day: dict, key: str, cast=None):
    out = []
    for d in days:
        v = (by_day.get(d) or {}).get(key)
        out.append(None if v is None else (cast(v) if cast else v))
    return out


def _int(v):
    return None if v is None else int(round(v))


def _hist_q(hist: list, edges, q: float):
    """q-quantile of a latency histogram (bucket i: up to edges[i] ms, the last one above edges[-1]): the upper
    edge of the bucket that holds it (a conservative "under X ms")."""
    n = sum(hist)
    if not n:
        return None
    rank, seen = q * n, 0
    for i, c in enumerate(hist):
        seen += c
        if seen >= rank and c:
            return edges[i] if i < len(edges) else edges[-1] * 2
    return edges[-1] * 2


def _since(first_by: dict, key: str | None):
    return first_by.get(key) if key else None


# ---------------------------------------------------------------- the parts
def _meta(db, store, today: str) -> dict:
    tracked = st.tracked_since(db)
    first_active = db.execute('SELECT MIN(day) FROM stat_active').fetchone()[0]
    kpi_first = db.execute("SELECT MIN(day) FROM stat_kpi_daily WHERE key = '_done'").fetchone()[0]
    kpi_last = db.execute("SELECT MAX(day) FROM stat_kpi_daily WHERE key = '_done'").fetchone()[0]
    counters_first = db.execute('SELECT MIN(day) FROM stat_counters').fetchone()[0]
    first_by = {}
    for prefix, name in (('xu_', 'xu'), ('dev_', 'dev'), ('http:', 'http'), ('cmd_ms:', 'latency'), ('up_min', 'uptime'),
                         ('max:online5m', 'online'), ('ai:', 'ai')):
        hi = prefix[:-1] + chr(ord(prefix[-1]) + 1)
        first_by[name] = db.execute('SELECT MIN(day) FROM stat_counters WHERE key >= ? AND key < ?', (prefix, hi)).fetchone()[0]
    wallet = db.execute("SELECT MIN(day) FROM stat_kpi_daily WHERE key = 'wallet_median'").fetchone()[0]
    play_first = db.execute('SELECT MIN(day) FROM stat_play_daily').fetchone()[0] or db.execute('SELECT MIN(day) FROM stat_play').fetchone()[0]
    milestones = db.execute("SELECT MIN(at) FROM stat_milestones WHERE key = 'created' AND at IS NOT NULL").fetchone()[0]
    releases = []
    try:
        from . import whats_new
        releases = [dict(version=e['version'], date=e['date']) for e in whats_new.ENTRIES]
    except Exception:  # noqa: BLE001 - a missing list of releases is not worth the payload
        releases = []
    return dict(today=today, tz='Asia/Ho_Chi_Minh (UTC+7)', launch=LAUNCH_DAY, version=__version__,
                tracked_since=tracked, active_since=first_active, kpi_first=kpi_first, kpi_last=kpi_last,
                counters_since=counters_first, counters=first_by, wallet_since=wallet, play_since=play_first, play_exact=PLAY_EXACT_DAY,
                funnel_since=round(milestones, 3) if milestones else None, releases=releases[:40],
                since=dict(births=tracked, kpi=kpi_first, counters=counters_first, play=play_first, wallet=wallet),
                keep=dict(active_days=st.KEEP_DAYS, play_days=st.PLAY_KEEP_DAYS, actions_days=rt.ACTIONS_KEEP_DAYS))


def _daily(db, days: list, today: str) -> dict:
    """{day: {key: value}}: the frozen days, plus today (and any day the freeze has not reached yet) live."""
    by = kpi.frozen(db, days[0])
    for d in days:
        if '_done' not in (by.get(d) or {}) and (d == today or d >= plus_days(today, -kpi.FREEZE_DAYS)):
            live = kpi._base(db, d)
            by.setdefault(d, {}).update(live)
            by[d]['_live'] = 1
    return by


def plus_days(day: str, n: int) -> str:
    return kpi.plus(day, n)


def growth(db, days: list, by: dict, today: str) -> dict:
    who = st.players(db, 7, datetime.date.fromisoformat(today))
    first = {r[0]: int(r[1]) for r in db.execute('SELECT first_day, COUNT(*) FROM stat_players WHERE first_day >= ? GROUP BY first_day', (days[0],))}
    before = int(db.execute('SELECT COUNT(*) FROM stat_players WHERE first_day < ?', (days[0],)).fetchone()[0] or 0)
    # Today: stat_players only knows frozen days; today's first-timers are the active saves not in it yet.
    if today in days and '_done' not in (by.get(today) or {}):
        first[today] = int(db.execute('SELECT COUNT(*) FROM stat_active a WHERE a.day = ? AND NOT EXISTS '
                                      '(SELECT 1 FROM stat_players p WHERE p.sid = a.sid)', (today,)).fetchone()[0] or 0)
    cum, run = [], before
    for d in days:
        run += first.get(d, 0)
        cum.append(run)
    series = dict(new_sessions=_col(days, by, 'new_sessions', _int), new_players=_col(days, by, 'new_players', _int),
                  new_accounts=_col(days, by, 'new_accounts', _int), first_seen=[first.get(d, 0) for d in days], cum_players=cum)
    series['activation'] = [_pct(p, s) if p is not None and s else None for p, s in zip(series['new_players'], series['new_sessions'])]
    played = who['played']
    return dict(totals=dict(saves_total=who['total'], players_total=played, accounts_total=who['accounts'], guests_played=who['guests'],
                            account_saves=who['account_saves'], account_rate=_pct(who['account_saves'], played),
                            unplayed_migrated=who.get('unplayed_migrated', 0)),
                series=series, compare=_compare(days, series, ('new_sessions', 'new_players', 'new_accounts'), today))


def _compare(days: list, series: dict, keys, today: str) -> dict:
    """Last 7 / 30 complete days against the 7 / 30 before (sum, growth %); None where the earlier window is not
    fully in the history."""
    out = {}
    done = [i for i, d in enumerate(days) if d < today]
    for n in (7, 30):
        cur, prev = done[-n:], done[-2 * n:-n]
        row = {}
        for k in keys:
            a = sum(series[k][i] or 0 for i in cur) if len(cur) == n else None
            b = sum(series[k][i] or 0 for i in prev) if len(prev) == n else None
            row[k] = dict(now=a, before=b, growth=_pct(a - b, b) if a is not None and b else None)
        out[str(n)] = row
    return out


def _play_by_day(store, db, days: list, today: str) -> dict:
    """{day: play summary} from stat_play_daily (rolled days) and stat_play (recent days, the play section's cache)."""
    out = {}
    for d, players, secs, sessions, cmds, data in db.execute(
            'SELECT day, players, secs, sessions, cmds, data FROM stat_play_daily WHERE day >= ?', (days[0],)):
        try:
            extra = json.loads(data or '{}')
        except ValueError:
            extra = {}
        hist = st._hist()
        for b, c in (extra.get('per_player') or {}).items():
            try:
                hist[int(b)] += int(c)
            except (ValueError, IndexError):
                continue
        out[d] = dict(players=int(players), secs=int(secs), sessions=int(sessions), cmds=int(cmds), hours=extra.get('hours') or [0] * 24,
                      median=st._quantile(hist, .5))
    first = db.execute('SELECT MIN(day) FROM stat_play').fetchone()[0]
    est = {r[0] for r in db.execute('SELECT day FROM stat_play_est WHERE day >= ?', (days[0],))}
    for d in days:
        if d in out or first is None or d < first:
            continue
        p = st.play_day(db, d) if d == today else st._play_day_cached(store, db, d, None)
        out[d] = dict(players=p['players'], secs=p['secs'], sessions=p['sessions'], cmds=p['cmds'], hours=p['hours'],
                      median=st._quantile(p['per_player'], .5))
    for d in est:
        if d in out:
            out[d]['estimated'] = True
    return out


def activity(store, db, days: list, by: dict, counters: dict, today: str) -> dict:
    dau, mau = _col(days, by, 'dau', _int), _col(days, by, 'mau', _int)
    series = dict(dau=dau, wau=_col(days, by, 'wau', _int), mau=mau, returning=_col(days, by, 'returning', _int),
                  resurrected=_col(days, by, 'resurrected', _int),
                  stickiness=[_pct(a, m) if a is not None and m else None for a, m in zip(dau, mau)],
                  peak_online=[(counters.get(d) or {}).get('max:online5m') for d in days],
                  peak_cmd_min=[(counters.get(d) or {}).get('max:cmd_min') for d in days])
    play = _play_by_day(store, db, days, today)
    series['play_players'] = [play[d]['players'] if d in play else None for d in days]
    series['avg_min'] = [round(play[d]['secs'] / play[d]['players'] / 60, 1) if d in play and play[d]['players'] else None for d in days]
    series['median_min'] = [round(play[d]['median'] / 60, 1) if d in play and play[d]['median'] is not None else None for d in days]
    series['sessions_pp'] = [round(play[d]['sessions'] / play[d]['players'], 2) if d in play and play[d]['players'] else None for d in days]
    series['hours_total'] = [round(play[d]['secs'] / 3600, 1) if d in play else None for d in days]
    series['cmds'] = [play[d]['cmds'] if d in play else None for d in days]
    # Hour × weekday: average players active in each Vietnam hour, over the last 28 finished days with play data.
    grid = [[0.0] * 24 for _ in range(7)]
    seen = [0] * 7
    used = [d for d in days if d < today and d in play][-28:]
    for d in used:
        wd = datetime.date.fromisoformat(d).weekday()
        seen[wd] += 1
        for h, n in enumerate(play[d]['hours'][:24]):
            grid[wd][h] += n
    heat = [[round(grid[w][h] / seen[w], 1) if seen[w] else None for h in range(24)] for w in range(7)]
    per_hour = [round(sum(grid[w][h] for w in range(7)) / len(used), 1) if used else None for h in range(24)]
    peak_hour = max(range(24), key=lambda h: per_hour[h] or 0) if used else None
    hourly_peak = {}
    for d in days[-7:]:
        for k, v in (counters.get(d) or {}).items():
            if k.startswith('max:online5m:h'):
                h = int(k[-2:])
                hourly_peak[h] = max(hourly_peak.get(h, 0), int(v))
    return dict(series=series, heatmap=dict(grid=heat, days=len(used), start=used[0] if used else None, end=used[-1] if used else None,
                                            per_hour=per_hour, peak_hour=peak_hour),
                online_by_hour=[hourly_peak.get(h) for h in range(24)],
                estimated=[d for d in days if d in play and play[d].get('estimated')])


def retention(store, db, days: list, by: dict, today: str) -> dict:
    from . import admin_retention as ar
    t = datetime.date.fromisoformat(today)
    coh = ar.cohorts(store, db, t)
    curve = []
    for k in ar.COHORT_KS:
        have = [r for r in coh if r.get(f'k{k}') is not None]
        n, kept = sum(r['n'] for r in have), sum(r[f'k{k}'] for r in have)
        curve.append(dict(k=k, pct=_pct(kept, n), n=n, kept=kept, ci=wilson(kept, n), cohorts=sum(1 for x in have if x['n'])))
    # Frozen numerators reach further back than the 60 listed cohorts (every day since tracking).
    hist = []
    for d in days:
        row = by.get(d) or {}
        if row.get('new_players') is None or '_done' not in row:
            continue
        hist.append(dict(day=d, n=int(row['new_players']), **{f'k{k}': _int(row.get(f'ret_d{k}')) for k in ar.COHORT_KS}))
    curve_all = []
    for k in ar.COHORT_KS:
        have = [r for r in hist if r[f'k{k}'] is not None]
        n, kept = sum(r['n'] for r in have), sum(r[f'k{k}'] for r in have)
        curve_all.append(dict(k=k, pct=_pct(kept, n), n=n, ci=wilson(kept, n), cohorts=sum(1 for x in have if x['n'])))
    # Rolling: active on day k or any later day (cohorts whose day k is over), last 60 start days.
    start = kpi.plus(today, -(ar.COHORT_DAYS - 1))
    rolling = []
    for k in (1, 7, 14, 30):
        pk = ar._plus_sql(db, 'b.day', k)
        r = db.execute(f'SELECT COUNT(*), SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day >= {pk}) THEN 1 ELSE 0 END) '
                       'FROM stat_births b WHERE b.day >= ? AND b.day < ? AND EXISTS '
                       '(SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = b.day)', (start, kpi.plus(today, -k))).fetchone()
        n, kept = int(r[0] or 0), int(r[1] or 0)
        rolling.append(dict(k=k, pct=_pct(kept, n), n=n, ci=wilson(kept, n)))
    weekly = _weekly_cohorts(db, today)
    weeks = []
    for d in days:
        row = by.get(d) or {}
        if row.get('wk_active') is None:
            continue
        prev = int(row.get('wk_prev') or 0)
        weeks.append(dict(week=d, active=_int(row['wk_active']), prev=prev, retained=_int(row.get('wk_retained')), new=_int(row.get('wk_new')),
                          back=_int(row.get('wk_back')), churned=_int(row.get('wk_churned')), partial=bool(row.get('wk_partial')),
                          churn_pct=_pct(row.get('wk_churned') or 0, prev), retained_pct=_pct(row.get('wk_retained') or 0, prev)))
    # Guests who became accounts: new players of the last 30 finished days.
    c30 = db.execute('SELECT COUNT(*), SUM(CASE WHEN EXISTS (SELECT 1 FROM accounts c WHERE c.sid = b.sid) THEN 1 ELSE 0 END) FROM stat_births b '
                     'WHERE b.day >= ? AND b.day < ? AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = b.day)',
                     (kpi.plus(today, -30), today)).fetchone()
    n30, acc30 = int(c30[0] or 0), int(c30[1] or 0)
    life = db.execute('SELECT COUNT(*), SUM(days), SUM(CASE WHEN days = 1 THEN 1 ELSE 0 END), SUM(CASE WHEN days BETWEEN 2 AND 3 THEN 1 ELSE 0 END), '
                      'SUM(CASE WHEN days BETWEEN 4 AND 7 THEN 1 ELSE 0 END), SUM(CASE WHEN days BETWEEN 8 AND 14 THEN 1 ELSE 0 END), '
                      'SUM(CASE WHEN days >= 15 THEN 1 ELSE 0 END) FROM stat_players').fetchone()
    ln = int(life[0] or 0)
    bands = [dict(label=lab, n=int(v or 0), pct=_pct(int(v or 0), ln)) for lab, v in zip(('1 ngày', '2–3', '4–7', '8–14', '15+'), life[2:])]
    return dict(cohorts=coh, curve=curve, curve_all=curve_all, rolling=rolling, weekly=weekly, weeks=weeks,
                conversion=dict(n=n30, accounts=acc30, pct=_pct(acc30, n30), ci=wilson(acc30, n30)),
                lifetime=dict(players=ln, avg_days=round(int(life[1] or 0) / ln, 2) if ln else None, bands=bands))


def _weekly_cohorts(db, today: str, weeks: int = 10) -> dict:
    """New players grouped by the week they started (Monday..Sunday), and the share of each group active in each
    following week (0 = the start week itself, always 100%); a week not over yet is marked partial."""
    this = kpi.week_of(today)
    first = kpi.plus(this, -7 * (weeks - 1))
    groups: dict = {}
    for sid, born, day in db.execute(
            'SELECT b.sid, b.day, a.day FROM stat_births b JOIN stat_active a ON a.sid = b.sid AND a.day >= b.day '
            'WHERE b.day >= ? AND EXISTS (SELECT 1 FROM stat_active f WHERE f.sid = b.sid AND f.day = b.day)', (first,)):
        w0 = kpi.week_of(born)
        k = (datetime.date.fromisoformat(kpi.week_of(day)) - datetime.date.fromisoformat(w0)).days // 7
        g = groups.setdefault(w0, {})
        g.setdefault(k, set()).add(sid)
    rows = []
    for i in range(weeks):
        w0 = kpi.plus(first, 7 * i)
        g = groups.get(w0, {})
        n = len(g.get(0, ()))
        cells = []
        for k in range(weeks - i):
            wk = kpi.plus(w0, 7 * k)
            cells.append(dict(k=k, n=len(g.get(k, ())), pct=_pct(len(g.get(k, ())), n), partial=wk == this))
        rows.append(dict(week=w0, n=n, cells=cells))
    return dict(rows=rows, this_week=this)


def _counters_sum(counters: dict, days: list, prefix: str) -> dict:
    out: dict = {}
    for d in days:
        for k, v in (counters.get(d) or {}).items():
            if k.startswith(prefix):
                out[k[len(prefix):]] = out.get(k[len(prefix):], 0) + int(v)
    return out


def engagement(db, days: list, by: dict, today: str) -> dict:
    feats = {}
    dau = {d: (by.get(d) or {}).get('dau') for d in days}
    today_feats = kpi.features_day(db, today) if kpi._exists(db, 'stat_actions') else {}
    for f in kpi.FEATURE_KEYS:
        series = []
        for d in days:
            row = by.get(d) or {}
            v = today_feats.get(f'feat:{f}') if d == today and '_done' not in row else row.get(f'feat:{f}')
            series.append(_int(v))
        feats[f] = series
    last7 = [i for i, d in enumerate(days) if d < today][-7:]
    adoption = []
    for f in kpi.FEATURE_KEYS:
        users = sum(feats[f][i] or 0 for i in last7 if feats[f][i] is not None)
        base = sum(dau[days[i]] or 0 for i in last7 if feats[f][i] is not None)
        adoption.append(dict(key=f, label=FEATURE_LABELS.get(f, f), pct=_pct(users, base), players_days=users, dau_days=base))
    adoption.sort(key=lambda r: -(r['pct'] or 0))
    # Leaderboard: the overall board's rows (one per player) through its index.
    lb_rows = [(int(r[0]), int(r[1])) for r in db.execute("SELECT days, mastered FROM leaderboard WHERE board = 'all'")]
    n = len(lb_rows)
    work_days = sorted(r[0] for r in lb_rows)
    mastered = sum(1 for r in lb_rows if r[1] >= 1)
    names = st.career_names()
    careers = []
    if names:
        marks = ','.join('?' * len(names))
        for board, players, lv3, dsum in db.execute(
                f'SELECT board, COUNT(*), SUM(CASE WHEN level >= 3 THEN 1 ELSE 0 END), SUM(days) FROM leaderboard WHERE board IN ({marks}) GROUP BY board',
                tuple(names)):
            careers.append(dict(id=board, name=names.get(board, board), players=int(players), mastered=int(lv3 or 0),
                                mastered_pct=_pct(int(lv3 or 0), int(players)), avg_days=round(int(dsum or 0) / int(players), 1) if players else None))
    careers.sort(key=lambda r: -r['players'])
    created = int(db.execute("SELECT COUNT(*) FROM stat_milestones WHERE key = 'created'").fetchone()[0] or 0)
    ms = []
    for key, label in rt.MILESTONES:
        if key == 'created':
            continue
        c = int(db.execute('SELECT COUNT(*) FROM stat_milestones WHERE key = ?', (key,)).fetchone()[0] or 0)
        ms.append(dict(key=key, label=label, n=c, pct=_pct(c, created)))
    social = {}
    ex = lambda t: kpi._exists(db, t)
    if ex('friends'):
        r = db.execute('SELECT COUNT(*), COUNT(DISTINCT sid) FROM friends').fetchone()
        social.update(friend_pairs=int(r[0] or 0) // 2, with_friend=int(r[1] or 0))
    if ex('couples'):
        r = db.execute('SELECT SUM(CASE WHEN ended IS NULL THEN 1 ELSE 0 END), SUM(CASE WHEN married_at IS NOT NULL AND ended IS NULL THEN 1 ELSE 0 END), '
                       'COUNT(*) FROM couples').fetchone()
        social.update(couples=int(r[0] or 0), married=int(r[1] or 0), couples_ever=int(r[2] or 0))
    if ex('wedding_parties'):
        r = db.execute("SELECT COUNT(*), COALESCE(SUM(guests), 0) FROM wedding_parties WHERE status = 'done'").fetchone()
        social.update(weddings_done=int(r[0] or 0), wedding_guests=int(r[1] or 0))
    if ex('live_dates'):
        social['dates_30d'] = int(db.execute('SELECT COUNT(*) FROM live_dates WHERE at >= ?', (kpi.epoch_of(kpi.plus(today, -29)),)).fetchone()[0] or 0)
    chat = dict(chat_msgs=_col(days, by, 'chat_msgs', _int), chat_senders=_col(days, by, 'chat_senders', _int))
    chat['chat_share'] = [_pct(s, a) if s is not None and a else None for s, a in zip(chat['chat_senders'], [dau[d] for d in days])]
    return dict(features=dict(series=feats, adoption=adoption, labels=FEATURE_LABELS, days=len(last7)),
                board=dict(players=n, mastered=mastered, mastered_pct=_pct(mastered, n), work_days_median=st._pct(work_days, .5),
                           work_days_p90=st._pct(work_days, .9)),
                careers=careers, milestones=dict(created=created, steps=ms), social=social, chat=chat)


def economy(days: list, by: dict, counters: dict, saves: dict | None, today: str) -> dict:
    xin = [sum(v for k, v in (counters.get(d) or {}).items() if k.startswith('xu_in:')) if counters.get(d) else None for d in days]
    xout = [sum(v for k, v in (counters.get(d) or {}).items() if k.startswith('xu_out:')) if counters.get(d) else None for d in days]
    dau = _col(days, by, 'dau', _int)
    series = dict(xu_in=xin, xu_out=xout, xu_net=[None if a is None else a - (b or 0) for a, b in zip(xin, xout)],
                  xu_in_pp=[round(a / n, 1) if a is not None and n else None for a, n in zip(xin, dau)],
                  wallet_median=_col(days, by, 'wallet_median'), wallet_p90=_col(days, by, 'wallet_p90'), wallet_n=_col(days, by, 'wallet_n', _int))
    window = [d for d in days][-30:]
    ins, outs = _counters_sum(counters, window, 'xu_in:'), _counters_sum(counters, window, 'xu_out:')
    groups: dict = {}
    for name, src, sign in (('in', ins, 1), ('out', outs, -1)):
        for action, v in src.items():
            g = groups.setdefault(kpi.feature_of(action), dict(xu_in=0, xu_out=0))
            g['xu_in' if sign > 0 else 'xu_out'] += v
    by_group = [dict(key=k, label=FEATURE_LABELS.get(k, k), **v, net=v['xu_in'] - v['xu_out']) for k, v in groups.items()]
    by_group.sort(key=lambda r: -(r['xu_in'] + r['xu_out']))
    top = lambda src: [dict(action=a, xu=v) for a, v in sorted(src.items(), key=lambda kv: -kv[1])[:12]]
    return dict(series=series, groups=by_group, top_in=top(ins), top_out=top(outs), window_days=len(window), sample=_sample(saves),
                revenue=dict(enabled=False, value=0, note='Chưa có thanh toán, quảng cáo hay gói trả phí trong game.'))


def _sample(saves: dict | None) -> dict | None:
    """The wallet part of the job's saves sample (admin_stats pass_saves), or None before its first pass."""
    if not saves or not saves.get('economy'):
        return None
    e, s = saves['economy'], saves.get('sample') or {}
    n = int(e.get('sample') or 0)
    return dict(n=n, covers_since=s.get('covers_since'), kind=s.get('kind') or 'recent', wallet=e.get('wallet'), buckets=e.get('buckets'),
                debt=e.get('debt'), debt_pct=_pct(e.get('debt') or 0, n), debt_moe=_moe(e.get('debt') or 0, n),
                investors=e.get('investors'), investors_pct=_pct(e.get('investors') or 0, n), investors_moe=_moe(e.get('investors') or 0, n),
                scam_victims=e.get('scam_victims'), generated_at=saves.get('generated_at'))


def with_saves(inv: dict, saves: dict) -> dict:
    """A new saves sample into a computed payload (the job's saves pass ends after the overview's pass):
    the economy sample and the infra save sizes, nothing read again."""
    if inv.get('economy'):
        inv['economy']['sample'] = _sample(saves)
    if inv.get('infra'):
        inv['infra']['save_sizes'] = saves.get('sizes')
        inv['infra']['sample'] = saves.get('sample')
    return inv


def _moe(k: int, n: int):
    """± percentage points (95%) of a share in a sample of n; for the saves sample (a census of the recent players,
    not a random sample of all players): the page says what it covers."""
    if not n:
        return None
    p = k / n
    return round(196 * math.sqrt(p * (1 - p) / n), 1)


def quality(store, db, days: list, by: dict, counters: dict, cmds: list, today: str, now: float) -> dict:
    from . import admin_retention as ar
    t0 = kpi.epoch_of(days[0])
    fb_by: dict = {}
    for at, kind in db.execute('SELECT created_at, kind FROM player_feedback WHERE created_at >= ?', (t0,)):
        d = kpi.vn_day(float(at))
        row = fb_by.setdefault(d, {})
        row[kind] = row.get(kind, 0) + 1
    fb = [sum((fb_by.get(d) or {}).values()) if d >= days[0] else None for d in days]
    dau = _col(days, by, 'dau', _int)
    errs = {r[0]: int(r[1]) for r in db.execute('SELECT day, SUM(count) FROM stat_client_errors WHERE day >= ?' + ar._OURS + ' GROUP BY day',
                                                (days[0], *ar._OURS_ARGS))}
    client = [errs.get(d, 0) if d >= (min(errs) if errs else today) else None for d in days]
    lat = {}
    for d in days:
        hist = [0] * (len(st.CMD_EDGES) + 1)
        for k, v in (counters.get(d) or {}).items():
            if k.startswith('cmd_ms:'):
                try:
                    hist[min(int(k[7:]), len(hist) - 1)] += int(v)
                except ValueError:
                    continue
        if sum(hist):
            lat[d] = hist
    srv_cmds = {d: sum(h) for d, h in lat.items()}
    http_all = [sum(v for k, v in (counters.get(d) or {}).items() if k.startswith('http:')) or None for d in days]
    http_5 = [(counters.get(d) or {}).get('http:5xx', 0) if http_all[i] else None for i, d in enumerate(days)]
    up_first = next((d for d in days if (counters.get(d) or {}).get('up_min')), None)
    uptime = []
    for d in days:
        up = (counters.get(d) or {}).get('up_min')
        if not up or d == up_first:   # the first day began mid-day: no denominator
            uptime.append(None)
            continue
        minutes = 1440 if d < today else max(1, int((now - kpi.epoch_of(d)) // 60))
        uptime.append(round(min(100.0, 100 * up / minutes), 2))
    fbk = st.feedback(db, 30, now)
    series = dict(feedback=fb, feedback_per_100=[round(100 * f / a, 2) if f is not None and a else None for f, a in zip(fb, dau)],
                  client_errors=client,
                  err_per_1k=[round(1000 * e / c, 2) if e is not None and c else None for e, c in zip(client, [srv_cmds.get(d) or cmds[i] for i, d in enumerate(days)])],
                  http_all=http_all, http_5xx=http_5,
                  http_5xx_pct=[_pct(b, a, 3) if a else None for a, b in zip(http_all, http_5)],
                  lat_p50=[_hist_q(lat[d], st.CMD_EDGES, .5) if d in lat else None for d in days],
                  lat_p95=[_hist_q(lat[d], st.CMD_EDGES, .95) if d in lat else None for d in days],
                  lat_p99=[_hist_q(lat[d], st.CMD_EDGES, .99) if d in lat else None for d in days],
                  uptime=uptime)
    kinds = {}
    for d in days[-30:]:
        for k, v in (fb_by.get(d) or {}).items():
            kinds[k] = kinds.get(k, 0) + v
    loads = ar.loads(db, datetime.date.fromisoformat(today))
    return dict(series=series, feedback=dict(kinds=kinds, ack=fbk['ack'], open=fbk['open'], total=fbk['total']),
                loads=loads['week'], ai=st.ai_usage(store))


def acquisition(db, days: list, counters: dict, today: str) -> dict:
    from . import admin_retention as ar
    src = ar.sources(db, datetime.date.fromisoformat(today))
    window = days[-30:]
    out = dict(sources=src)
    for name, prefix in (('os', 'dev_os:'), ('form', 'dev_form:'), ('browser', 'dev_br:'), ('lang', 'lang:')):
        s = _counters_sum(counters, window, prefix)
        total = sum(s.values())
        out[name] = [dict(key=k, n=v, pct=_pct(v, total)) for k, v in sorted(s.items(), key=lambda kv: -kv[1])]
    bots = sum((counters.get(d) or {}).get('dev_bot', 0) for d in window)
    humans = sum(r['n'] for r in out['form'])
    out['bots'] = dict(n=bots, pct=_pct(bots, bots + humans))
    return out


def infra(store, saves: dict | None) -> dict:
    sysd = st._result(store).get('system') or {}
    srv = st.server_light(store)
    tables = sorted(sysd.get('tables') or [], key=lambda t: -(t.get('rows') or 0))
    return dict(database=sysd.get('database') or srv.get('database'), db_bytes=sysd.get('db_bytes') or srv.get('db_bytes'),
                tables=tables[:25], version=__version__, workers=int(os.environ.get('WORKERS', '1') or 1), cpus=os.cpu_count(),
                python=srv.get('python'), uptime=srv.get('uptime'), save_sizes=(saves or {}).get('sizes'),
                sample=(saves or {}).get('sample'), command=st.command_stats(store), system_at=sysd.get('generated_at'))


# ---------------------------------------------------------------- the payload
def compute(store, saves: dict | None = None, now: float | None = None) -> dict:
    t0 = time.perf_counter()
    now = time.time() if now is None else now
    today = kpi.vn_day(now)
    errors, timing = {}, {}
    out = dict(today=today, defs=DEFS, parts=list(PARTS), small=SMALL, few=FEW, periods=list(PERIODS))
    if saves is None:
        saves = st._result(store).get('saves')

    def part(name, fn):
        t = time.perf_counter()
        try:
            with st._read(store, KPI_MS, KPI_STATEMENT_MS) as db:
                return fn(db)
        except Exception as exc:  # noqa: BLE001 - one part failing leaves it out (named), never a wrong number
            st._log(f'kpi {name}', exc)
            errors[name] = st._brief(exc)
            return None
        finally:
            timing[name] = round((time.perf_counter() - t) * 1000, 1)
    meta = part('meta', lambda db: _meta(db, store, today)) or dict(today=today, since={}, counters={})
    out['meta'] = meta
    first = min([d for d in (meta.get('tracked_since'), meta.get('kpi_first'), meta.get('counters_since')) if d] or [today])
    days = _axis(first, today)
    out['days'] = days
    by = part('daily', lambda db: _daily(db, days, today)) or {}
    counters = part('counters', lambda db: kpi.read(db, days[0])) or {}
    for (d, k), n in kpi.pending(store).items():   # this process's last seconds
        if d >= days[0]:
            row = counters.setdefault(d, {})
            row[k] = max(row.get(k, 0), n) if k.startswith('max:') else row.get(k, 0) + n
    out['growth'] = part('growth', lambda db: growth(db, days, by, today))
    out['activity'] = part('activity', lambda db: activity(store, db, days, by, counters, today))
    out['retention'] = part('retention', lambda db: retention(store, db, days, by, today))
    out['engagement'] = part('engagement', lambda db: engagement(db, days, by, today))
    out['economy'] = part('economy', lambda db: economy(days, by, counters, saves, today))
    cmds = (out['activity'] or {}).get('series', {}).get('cmds') or [None] * len(days)
    out['quality'] = part('quality', lambda db: quality(store, db, days, by, counters, cmds, today, now))
    out['acquisition'] = part('acquisition', lambda db: acquisition(db, days, counters, today))
    out['infra'] = part('infra', lambda db: infra(store, saves))
    out['headline'] = headline(out)
    out['errors'], out['timing'] = errors, timing
    out['live_days'] = sorted(d for d, row in by.items() if row.get('_live'))
    return st._stamp(out, t0)


def _period(days: list, values: list, agg: str, n: int, today: str, extra: dict | None = None):
    """A series summed up over the last `n` complete days (0: all of them) by its DEFS rule."""
    idx = [i for i, d in enumerate(days) if d < today]
    if n:
        idx = idx[-n:]
    vals = [values[i] for i in idx if values[i] is not None]
    if not vals:
        return None
    if agg == 'sum':
        return sum(vals)
    if agg == 'max':
        return max(vals)
    if agg == 'last':
        return vals[-1]
    if agg.startswith(('ratio', 'wavg')) and extra is not None:
        kind, _, spec = agg.partition(':')
        if kind == 'wavg':
            w = extra.get(spec) or []
            pairs = [(values[i], w[i]) for i in idx if values[i] is not None and i < len(w) and w[i]]
            tw = sum(b for _, b in pairs)
            return round(sum(a * b for a, b in pairs) / tw, 2) if tw else None
        num, _, den = spec.partition('/')
        a, b = extra.get(num) or [], extra.get(den) or []
        pairs = [(a[i], b[i]) for i in idx if i < len(a) and i < len(b) and a[i] is not None and b[i]]
        tb = sum(y for _, y in pairs)
        scale = {'ratio1': 1, 'ratio1000': 1000}.get(kind, 100)   # ratio / ratio100: a percentage
        return round(scale * sum(x for x, _ in pairs) / tb, 2) if tb else None
    return round(sum(vals) / len(vals), 2)


def headline(out: dict) -> list:
    """The overview cards: the last 30 complete days unless said otherwise."""
    days, today = out.get('days') or [], out.get('today')
    g, a, r, e, q = (out.get(k) or {} for k in ('growth', 'activity', 'retention', 'economy', 'quality'))
    cards = []

    def card(key, value, sub='', n=None, ci=None, since=None):
        cards.append(dict(key=key, value=value, sub=sub, n=n, ci=ci, since=since))
    tot = g.get('totals') or {}
    card('players_total', tot.get('players_total'), f"{tot.get('accounts_total') or 0} tài khoản")
    gs, as_ = g.get('series') or {}, a.get('series') or {}
    card('new_players', _period(days, gs.get('new_players') or [], 'sum', 30, today), '30 ngày đã qua')
    card('dau', _period(days, as_.get('dau') or [], 'avg', 30, today), 'trung bình 30 ngày')
    card('mau', _period(days, as_.get('mau') or [], 'last', 0, today), 'hết hôm qua')
    card('stickiness', _period(days, as_.get('stickiness') or [], 'avg', 30, today), 'trung bình 30 ngày')
    card('avg_min', _period(days, as_.get('avg_min') or [], 'wavg:play_players', 30, today, as_), 'trung bình 30 ngày')
    for k in (1, 7, 30):
        c = next((x for x in (r.get('curve') or []) if x['k'] == k), None)
        if c:
            card(f'd{k}', c['pct'], f"{c['n']} người · {c['cohorts']} nhóm", n=c['n'], ci=c['ci'])
    conv = r.get('conversion') or {}
    card('conversion', conv.get('pct'), f"{conv.get('n') or 0} người mới 30 ngày", n=conv.get('n'), ci=conv.get('ci'))
    es = e.get('series') or {}
    card('xu_net', _period(days, es.get('xu_net') or [], 'sum', 30, today), '30 ngày đã qua', since='counters')
    qs = q.get('series') or {}
    card('lat_p95', _period(days, qs.get('lat_p95') or [], 'avg', 7, today), 'trung bình 7 ngày', since='counters')
    card('uptime', _period(days, qs.get('uptime') or [], 'avg', 30, today), '30 ngày đã qua', since='counters')
    card('revenue', 0, 'chưa bật')
    return cards


# ---------------------------------------------------------------- exports (aggregates only, small cells hidden)
def _cell(value, kind: str = 'num', n=None):
    """The exported text of one number: players under SMALL become "<5"; a percentage over fewer than SMALL
    players is left blank (its row says n)."""
    if value is None:
        return ''
    if kind == 'n' and isinstance(value, (int, float)) and 0 < value < SMALL:
        return f'<{SMALL}'
    if kind == 'pct' and n is not None and n < SMALL:
        return ''
    return value


def to_csv(d: dict, part: str = 'all') -> str:
    """One CSV text of a part (or all): a `# table` line, a header row, the rows, a blank line. Data as of
    `generated_at`; Vietnam days; no player ever named."""
    if part != 'all' and part not in PARTS:
        raise ValueError('part')
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    stamp = datetime.datetime.fromtimestamp(float(d.get('generated_at') or time.time()), kpi.VN).strftime('%Y-%m-%d %H:%M')
    w.writerow([f'# Phố Có Chuyện — Tổng quan đầu tư · số liệu lúc {stamp} (giờ Việt Nam, UTC+7) · phiên bản {d.get("meta", {}).get("version", "")}'])
    w.writerow([f'# Ô dưới {SMALL} người được ghi "<{SMALL}"; tỉ lệ trên dưới {SMALL} người để trống. Không có dữ liệu cá nhân.'])
    w.writerow([])
    defs = d.get('defs') or DEFS
    days, today = d.get('days') or [], d.get('today')

    def table(name, head, rows):
        w.writerow([f'# {name}'])
        w.writerow(head)
        for r in rows:
            w.writerow(['' if v is None else v for v in r])
        w.writerow([])

    def daily(name, src: dict, keys):
        keys = [k for k in keys if k in src]
        kinds = [(defs.get(k) or {}).get('kind', 'num') for k in keys]
        table(name, ['day'] + keys, [[day] + [_cell(src[k][i], kinds[j]) for j, k in enumerate(keys)] for i, day in enumerate(days)])
        rows = []
        for k, kind in zip(keys, kinds):
            agg = (defs.get(k) or {}).get('agg', 'last')
            rows.append([k, (defs.get(k) or {}).get('label', k), agg] +
                        [_cell(_period(days, src[k], agg, n, today, src), kind) for n in PERIODS])
        table(name + '_periods', ['metric', 'label', 'rule', 'last_7d', 'last_30d', 'last_90d', 'all'], rows)

    want = PARTS if part == 'all' else (part,)
    if part == 'all':
        table('headline', ['metric', 'label', 'value', 'note', 'n', 'ci95_low', 'ci95_high'],
              [[c['key'], (defs.get(c['key']) or {}).get('label', c['key']),
                _cell(c['value'], (defs.get(c['key']) or {}).get('kind', 'num'), c.get('n')), c.get('sub'), c.get('n'),
                *(c.get('ci') or ['', ''])] for c in d.get('headline') or []])
    for p in want:
        x = d.get(p)
        if not x:
            table(p, ['note'], [['không có số liệu (phần này chưa tính được)']])
            continue
        if p == 'growth':
            table('growth_totals', ['metric', 'label', 'value'],
                  [[k, (defs.get(k) or {}).get('label', k), _cell(v, (defs.get(k) or {}).get('kind', 'n'))] for k, v in x['totals'].items()])
            daily('growth_daily', x['series'], ('new_sessions', 'new_players', 'activation', 'new_accounts', 'first_seen', 'cum_players'))
        elif p == 'activity':
            daily('activity_daily', x['series'], ('dau', 'wau', 'mau', 'stickiness', 'returning', 'resurrected', 'peak_online', 'peak_cmd_min',
                                                  'play_players', 'avg_min', 'median_min', 'sessions_pp', 'hours_total', 'cmds'))
            hm = x['heatmap']
            table('activity_hour_weekday_avg_players', ['weekday'] + [f'{h:02d}h' for h in range(24)],
                  [[('T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN')[i]] + [v for v in row] for i, row in enumerate(hm['grid'])])
        elif p == 'retention':
            table('retention_curve_60d', ['k_day', 'pct', 'ci95_low', 'ci95_high', 'players', 'cohorts'],
                  [[c['k'], _cell(c['pct'], 'pct', c['n']), *((c['ci'] or ['', '']) if c['n'] >= SMALL else ['', '']), _cell(c['n'], 'n'), c['cohorts']]
                   for c in x['curve']])
            table('retention_curve_all', ['k_day', 'pct', 'players', 'cohorts'],
                  [[c['k'], _cell(c['pct'], 'pct', c['n']), _cell(c['n'], 'n'), c['cohorts']] for c in x['curve_all']])
            table('retention_rolling', ['k_day', 'pct', 'players'], [[c['k'], _cell(c['pct'], 'pct', c['n']), _cell(c['n'], 'n')] for c in x['rolling']])
            table('retention_daily_cohorts', ['day', 'players'] + [f'd{k}_pct' for k in (1, 3, 7, 14, 30)],
                  [[r['day'], _cell(r['n'], 'n')] + [_cell(r.get(f'd{k}'), 'pct', r['n']) for k in (1, 3, 7, 14, 30)] for r in x['cohorts']])
            table('retention_weekly_cohorts', ['week', 'players'] + [f'w{k}_pct' for k in range(10)],
                  [[r['week'], _cell(r['n'], 'n')] + [_cell(c['pct'], 'pct', r['n']) for c in r['cells']] for r in x['weekly']['rows']])
            table('retention_weeks', ['week', 'active', 'prev', 'retained', 'new', 'back', 'churned', 'churn_pct', 'partial'],
                  [[r['week'], _cell(r['active'], 'n'), _cell(r['prev'], 'n'), _cell(r['retained'], 'n'), _cell(r['new'], 'n'), _cell(r['back'], 'n'),
                    _cell(r['churned'], 'n'), _cell(r['churn_pct'], 'pct', r['prev']), int(r['partial'])] for r in x['weeks']])
            c = x['conversion']
            table('retention_conversion_30d', ['new_players', 'with_account', 'pct'], [[_cell(c['n'], 'n'), _cell(c['accounts'], 'n'), _cell(c['pct'], 'pct', c['n'])]])
            table('retention_lifetime_days', ['band', 'players', 'pct'], [[b['label'], _cell(b['n'], 'n'), _cell(b['pct'], 'pct', x['lifetime']['players'])]
                                                                         for b in x['lifetime']['bands']])
        elif p == 'engagement':
            table('engagement_features_7d', ['feature', 'label', 'pct_of_dau'], [[f['key'], f['label'], _cell(f['pct'], 'pct', f['dau_days'])]
                                                                               for f in x['features']['adoption']])
            b = x['board']
            table('engagement_board', ['players', 'mastered_1plus', 'mastered_pct', 'work_days_median', 'work_days_p90'],
                  [[_cell(b['players'], 'n'), _cell(b['mastered'], 'n'), _cell(b['mastered_pct'], 'pct', b['players']), b['work_days_median'], b['work_days_p90']]])
            table('engagement_careers', ['career', 'name', 'players', 'mastered_pct', 'avg_days'],
                  [[c['id'], c['name'], _cell(c['players'], 'n'), _cell(c['mastered_pct'], 'pct', c['players']), c['avg_days']] for c in x['careers']])
            table('engagement_milestones', ['step', 'label', 'players', 'pct_of_opened'],
                  [[m['key'], m['label'], _cell(m['n'], 'n'), _cell(m['pct'], 'pct', x['milestones']['created'])] for m in x['milestones']['steps']])
            table('engagement_social', ['metric', 'value'], [[k, _cell(v, 'n')] for k, v in x['social'].items()])
            daily('engagement_chat_daily', x['chat'], ('chat_msgs', 'chat_senders', 'chat_share'))
        elif p == 'economy':
            daily('economy_daily', x['series'], ('xu_in', 'xu_out', 'xu_net', 'xu_in_pp', 'wallet_median', 'wallet_p90', 'wallet_n'))
            table(f'economy_by_feature_{x["window_days"]}d', ['feature', 'label', 'xu_in', 'xu_out', 'net'],
                  [[g['key'], g['label'], g['xu_in'], g['xu_out'], g['net']] for g in x['groups']])
            table('economy_top_sources', ['action', 'xu'], [[t['action'], t['xu']] for t in x['top_in']])
            table('economy_top_sinks', ['action', 'xu'], [[t['action'], t['xu']] for t in x['top_out']])
            s = x.get('sample')
            if s:
                wl = s.get('wallet') or {}
                table('economy_saves_sample', ['sample_n', 'covers_since_utc', 'wallet_median', 'wallet_p90', 'wallet_avg', 'debt_pct', 'debt_moe_pp',
                                               'investors_pct', 'investors_moe_pp'],
                      [[s['n'], s.get('covers_since'), wl.get('median'), wl.get('p90'), wl.get('avg'), _cell(s.get('debt_pct'), 'pct', s['n']), s.get('debt_moe'),
                        _cell(s.get('investors_pct'), 'pct', s['n']), s.get('investors_moe')]])
            table('economy_revenue', ['enabled', 'value', 'note'], [[0, 0, x['revenue']['note']]])
        elif p == 'quality':
            daily('quality_daily', x['series'], ('feedback', 'feedback_per_100', 'client_errors', 'err_per_1k', 'http_5xx_pct', 'lat_p50', 'lat_p95',
                                                 'lat_p99', 'uptime'))
            ack = x['feedback']['ack']
            table('quality_feedback_30d', ['kind', 'notes'], [[k, v] for k, v in sorted(x['feedback']['kinds'].items())])
            table('quality_feedback_response', ['read_median_h', 'read_avg_h', 'read', 'waiting', 'oldest_wait_h', 'read_pct'],
                  [[ack.get('median_h'), ack.get('avg_h'), ack.get('n'), ack.get('waiting'), ack.get('oldest_wait_h'), ack.get('read_pct')]])
            ld = x['loads']
            table('quality_load_7d_ms', ['metric', 'loads', 'p50', 'p75', 'p90'], [[k, v['n'], v['p50'], v['p75'], v['p90']] for k, v in ld.items()])
        elif p == 'acquisition':
            for key in ('d7', 'd30'):
                table(f'acquisition_sources_{key}', ['source', 'players', 'share_pct', 'd1_pct', 'd7_pct'],
                      [[s['source'], _cell(s['n'], 'n'), s['share'], _cell(s['d1'], 'pct', s['d1_n']), _cell(s['d7'], 'pct', s['d7_n'])]
                       for s in x['sources'][key]])
            for key in ('os', 'form', 'browser', 'lang'):
                table(f'acquisition_{key}_30d', ['key', 'sessions', 'pct'], [[r['key'], _cell(r['n'], 'n'), r['pct']] for r in x[key]])
            table('acquisition_bots_30d', ['bot_sessions', 'pct'], [[x['bots']['n'], x['bots']['pct']]])
        elif p == 'infra':
            table('infra', ['metric', 'value'], [[k, x.get(k)] for k in ('database', 'db_bytes', 'version', 'workers', 'cpus', 'python', 'uptime')])
            ss = x.get('save_sizes') or {}
            table('infra_save_sizes', ['n', 'median_bytes', 'p90_bytes', 'max_bytes', 'stored'], [[ss.get('n'), ss.get('median'), ss.get('p90'), ss.get('max'), ss.get('stored')]])
            table('infra_tables', ['table', 'rows', 'approx'], [[t['name'], t['rows'], int(bool(t.get('approx')))] for t in x['tables']])
    table('definitions', ['metric', 'label', 'definition', 'formula', 'period_rule'],
          [[k, v['label'], v['d'], v['f'], v['agg']] for k, v in defs.items()])
    return buf.getvalue()
