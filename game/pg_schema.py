"""Canonical PostgreSQL schema for game saves, accounts, live chat and shared limits.

Text columns use COLLATE "C" for stable byte ordering. Timestamps are UTC text in
'YYYY-MM-DD HH:MM:SS' format; `sessions.state` preserves the serialized JSON bytes.
Generated bigint identities allow explicit ids on restore. reset_sequences() can
advance them past restored rows and supplied sequence floors.

DDL stages create tables, indexes, statistics triggers and storage tuning.
ensure(conn) runs them idempotently at startup and records SCHEMA_VERSION in
`mnl_meta` so subsequent starts skip DDL and its locks. TABLES contains only the
runtime catalog needed to check table presence and maintain identity sequences.
"""
from __future__ import annotations

SCHEMA_VERSION = 75  # 75: review fixes of the 22/10 careers integration, new indexes only on this release's own tables (svc_orders_due_all: every due timer and money step of Phố dịch vụ, 'refund' included; svc_orders_working: 🏨 stays waiting for their row; svc_orders_buyer_alert: a buyer's talks and deliveries; birth_stays_pair: a player birth room in the market's pair caps; no FK, no backfill, nothing dropped, no save key); 74: 🎪 Hội chợ việc làm, a weekly town fair where every career opens a booth player to player (fair_events: one row per fair, weekly or opened by an admin, open → final with its leaderboard snapshot archived in the row, never deleted; fair_booths: one booth per player and fair, its career, the fair discount −10…−30 % on the provider's own Phố dịch vụ prices (never below the floor / NPC base: game/service_market.py quote), its mood (điểm gian hàng) from the shows and the oái oăm moments; fair_stamps: one 🎟️ stamp per visitor, fair and career (a completed order at that booth, or a show watched); fair_rewards: one row per visitor, fair and stamp tier (exactly once); fair_config: the admin's weekly switch and a one-off fair: game/town_fair.py; money stays svc_orders' (63), rewards are 🎨 Phong cách cosmetics through live_effects kind 'tfair' that 2.4.66 leaves pending; new tables and indexes only, no FK, no backfill, no save key, owner 21/10); 73: 📜 Nội quy bang, a bang's two rules texts (bang_code: one row per bang and kind, 'pub' 📢 the public rules shown outside the bang (the list, its page; what an applicant agrees to before joining) and 'in' 📜 the members-only rules, the text, its version (compare-and-set edits, the version an applicant saw), who and when, an admin hide that keeps the text; bang_code_hist: every edit, hide and show with the text of that version, append-only, the edits' rate limit; bang_code_seen: the versions each member has read (the 📜 Nội quy mới badge) and the public version they agreed to when joining or asking: game/bang_code.py; new tables and indexes only, no FK, no backfill, no save key: 2.4.66 never reads them, owner 21/10 "thiếu nội quy bang rồi", "công bố bên ngoài thì có nội quy bang riêng nữa, có text và giới hạn chữ"); 72: 🧰 Thợ phục chế, a restorer player restores another player's broken or worn things through Phố dịch vụ (restore_tickets: the thing a buyer brings, open → bound (to a svc_orders order, at the restorer's first bench step) → done (delivered) | dropped (withdrawn); a bound ticket whose order ended without delivery opens again; the bench steps and the grade: game/restore_service.py; a new table and indexes only, no FK, no backfill; save: only the optional journey.restored marks, which 2.4.66 keeps unread, owner 21/10); 71: 🔬 Đơn nghiên cứu, a Viện nghiên cứu player researches for another player (research_jobs: the three graded research steps of one Phố dịch vụ order, work → done, its quality and the name the researcher gave the result: game/research_lab.py; a new table and an index only, no FK, no backfill; save: only the optional journey.lab, which 2.4.66 keeps unread, owner 21/10); 70: 📻 Đài phát thanh Sóng Mây, players buy airtime from a radio player (radio_lines: every line a radio DJ put on the town ticker for another player, a shop ad 📢 or a song with a message 🎵, its text after moderation, its time window, hidden by the buyer, the DJ or an admin, never deleted: game/radio_station.py; the escrow and the 95/5 split stay in svc_orders (game/service_market.py); a new table and indexes only, no FK, no backfill, no save key: 2.4.66 and older never read it, owner 21/10); 69: 💒 Dịch vụ cưới từ người chơi, a couple hires other players for their wedding (wedsvc_jobs: one row per wedding order of Phố dịch vụ, the couple's brief, the provider's seven rolled work steps with their oái ăm demands, the answers, score and stars, the couple it serves: game/wed_services.py; money, escrow and the 5 % burn stay svc_orders' (63); a new table and indexes only, no FK, no backfill, no save key: 2.4.66 and older never read it, owner 21/10; 67–68: other branches' steps); 68: 🏨 Phòng cho người chơi, a homestay or hotel player rents rooms to other players through Phố dịch vụ (hotel_stays: one row per market order of a stay, booked → arrived → in → out | gone, the room, the arrival / night / check-out situations and the host's choices, the guest's satisfaction, the couple's partner and its rest step; hotel_hosts: a host's record (stays, satisfaction sum, situations handled / missed); hotel_rest: one rest a Vietnam day per player: game/hotel_stay.py; the money stays in svc_orders (63); new tables and indexes only, no FK, no backfill, no save key: the rest only moves journey.needs and journey.life.spirit values that 2.4.66 already validates, owner 21/10); 66: 📸 Chụp ảnh cho người chơi, a photographer player shoots another player (photo_studios: a photographer's prices, open flag, last network tag and record; photo_orders: every order, open → shoot → done | declined | cancelled | expired, the escrowed price, the look snapshot taken at order time and the session's shots; photos: the delivered photos (the game's own render data, no image bytes), the buyer's album (archived past 60, never deleted) and the photographer's portfolio; photo_pfp: a player's profile photo: game/photo_studio.py; new tables and indexes only, no FK, no backfill; save: only the optional journey.photo_wall, which 2.4.66 keeps unread, owner 21/10; 63–65: other branches' steps); 65: 🏥 Phòng sinh & nhận nuôi, a new shared child now costs money (birth_rooms: the birth room a homestay owner offers, one per save, price never below the 500 000 xu floor; birth_stays: every booking or adoption of a couple, proposed → booked → staying → born | declined | cancelled | refunded, at most one open per couple (partial unique index): game/birth.py; new tables and indexes only, no FK, no backfill, no save key: 2.4.66 and older never read them, owner 21/10); 63: 🛎️ Phố dịch vụ, players serve players across careers (svc_settings: a provider's offer per service, on/off, ×1–×10 or thương lượng; svc_orders: talks and escrow-backed orders talk → held → working → delivered | ready → done, refunds back in full; svc_reviews, svc_rep: ratings and each provider's reputation; svc_flags: a buyer's report within 24 h for the admin, never an automatic punishment; svc_net: keyed network tags of market users, never an address: game/service_market.py; work_service_orders.fee: the 5 % burned on a completed legacy order, ADD COLUMN IF NOT EXISTS with a constant default; work_reviews_provider index; new tables, one column and indexes only, no FK, no backfill, no save key: 2.4.66 never reads them, owner 21/10); 62: 🏝️ Đảo bang bought and upgraded from the fund (bangs.isle, isle_to, isle_started, isle_ready, isle_paid, isle_how: columns added with ADD COLUMN IF NOT EXISTS, constant defaults, no rewrite, no backfill; isle's default 1 is the grant: every bang written without it (before this release, or by a 2.4.64 process during the rollout) holds cấp 1 for free, a bang founded from now on is written with 0 and buys it; 2.4.64 never reads these columns, owner 21/10); 61: ⚔️ Thách đấu bang, bang against bang with pets any day (bang_chal_roster: a bang's standing roster, one pet a member in the order its officers set; bang_chal_team: a bang's challenge Elo, record and how it takes challenges; bang_chal: every challenge, open → done | declined | cancelled | expired, a played one with its five duels: game/bang_challenge.py; pet_power: each player's strongest pet power, the 💪 Chiến lực of the bang ranking, owner 21/10 "top bang thì bằng cách cống hiến và tính điểm chiến lực bằng pets": game/pet_arena.py power_commit, game/bang.py standings; new tables and indexes only, no FK, no backfill, no save key: 2.4.64 and older never read them, owner 21/10); 60: ⚔️ a bang's join rules (bangs.rules: join mode đóng / cần duyệt / tự động duyệt and the optional requirements, a JSON text column added with ADD COLUMN IF NOT EXISTS and a constant default '{}': no rewrite, no backfill; 2.4.60 never reads the bang tables, owner 20/10); 59: review fixes of the 19/10 integration (archive tables bang_log_old, bang_points_old, bang_stints_old, pet_arena_matches_old: rows past their keep are moved there by the housekeeping, never dropped; indexes bang_stints_bang_joined, bang_stints_left, bang_log_at, bang_points_at, pet_arena_matches_at for the Giờ vàng snapshot and those cheap batched moves; new tables and indexes only, no FK, no backfill, no save key: 2.4.60 and older never read them); 58: ⚔️ Đấu trường pet, 🏟️ Giải đấu pet tuần, 🛡️ Bang chiến pet (pet_arena, pet_arena_season, pet_arena_matches, pet_cup, pet_cup_entries, pet_war, pet_war_picks, pet_war_matches, pet_team_ladder, pet_team_rating: game/pet_arena.py, game/pet_cup.py, game/pet_war.py; new tables and indexes only, no FK, no backfill, no save key: 2.4.60 and older never read them, owner 19/10); 57: ⚔️ Bang, player guilds (bangs, bang_members, bang_stints, bang_asks, bang_fund, bang_points, bang_facilities, bang_items, bang_gh, bang_log, bang_week_win: game/bang.py, live/bangs.py; new tables and indexes only, no FK, no backfill: 2.4.60 and older never read them, owner 19/10); 56: 🏗️ Xây trên đảo + 🌍 đảo mở cửa (island_builds: the buildings on private islands, a copy of journey.islb written in the save's transaction; island_public, island_visitors: islands open to everyone and their visitors: game/island_build.py, game/island_trips.py, live/island.py; new tables and indexes only, no FK, no backfill: 2.4.60 and older never read them, owner 19/10); 55: 🗄️ chat_archive (Cả phố's messages past the newest 500, moved by live/chat.py prune_town; a new table only, no FK: older releases never read it, owner 17/10); 54: 🏝️ Đảo riêng trips with friends (island_trips, island_guests: game/island_trips.py, live/island.py; new tables and indexes only, no FK, no backfill: 2.4.34 and older never read them; 51 and 53: other branches' steps); 52: 🏗️ Công trình của phố (town_projects, town_gifts: game/town_projects.py; new tables and indexes only, no FK, no backfill: older releases never read them, owner 16/10); 50: 🎨 sticker packs (sticker_packs, sticker_pack_images: one pack of ≥ 12 stickers per account, owner 16/10 afternoon; new tables only); 49: 🎨 Thi làm sticker (sticker_entries, sticker_rewards: game/sticker_event.py; new tables only, no FK, owner 16/10); 48: 🛃 Hải quan across players (hq_roster: the customs ladder's seats and reviewers, game/cand_roster.py; hq_cases: warehouse inspections of players' shops, game/hq_ops.py; new tables and indexes only, no FK, no backfill: 2.4.26 and older never read them); 47: unused (the sticker contest took 49); 46: 💐 Thiệp 20/10 (ev2010_cards, ev2010_reports, ev2010_rewards: game/event2010.py; new tables only, no FK, no save key, owner 16/10 "làm 1 cái / riêng đi"); 45: 📜 old shared lời chúc on the wish trees (chua_card_marks, chua_card_prayers: 🙏 / reports / admin hide of chua_public_cards rows, game/chua_wish.py; new tables only, no FK, no backfill, owner 15/10 "đưa vào 1 cái đi"); 44: 🌳 Cây ước nguyện (chua_wishes, chua_wish_prayers: game/chua_wish.py; new tables only, owner 15/10); 43: 🏆 weekly Top lời index (fair_loss_week_win, net > 0: game/fair_loss.py view_win; index only, older releases ignore it); 42: explicit temple-card sharing (new table, no backfill); 41: 👮 the Chợ đen patrol (cand_stops.stake, cand_acts_by, cand_acts_day, cand_stops_open: game/cand_ops.py), a step of its own so a database already at 40 gains them; 40: 👮 Công an across players (cand_roster, cand_stops, cand_acts: game/cand_roster.py, game/cand_ops.py); 39: persistent unclaimed town treasure; 38: durable private feedback images; 37: shared town treasure; 36: weekly fair net-loss ledger; 35: verified competitive bark matches; 34: 🐕 Kéo co chó sủa (bark_tickets: game/dog_bark.py, live/dog_bark.py); 33: 🚔 Trại tạm giữ marks (jail_marks: game/jail.py); 32: 💌 Thiệp mời cưới cả phố (wed_invites, wed_invite_seen: game/wed_invite.py); 31: 🎨 Cho trang trí (home_deco_grants, home_deco_log: game/home_coop.py); 30: 🎙️ Phòng hát mic trực tiếp (account_birth: game/karaoke_mic.py); 29: 🔨 Nhà đấu giá (auction_lots, auction_bids: game/auction.py); 28: 🎆 Mạnh Thường Quân (lux_gifts: game/lux.py); 27: 🐾 Bé cưng của tuần (pet_board: game/pets.py; ensure() also creates any table missing); 26: 🎤 Phòng hát (kara_songs, kara_tickets, kara_reviews: game/karaoke.py, live/karaoke.py), on top of 25 (spend-1: donations, chat_style); 24: 🐢 chat slow mode (chat_slow: game/live_chat.py, live/chat.py); 22: synchronize character/account names; 21: chat replies; 20: friend home invitations.
                     # 2: leaderboard, marriage/friends/couple tables, stat_fb_created, stat_accounts_created; 3: stat_play;
                     # 4: system_gifts; 5: Giữ chân (game/retention.py: stat_milestones, stat_actions(_daily), stat_rollups,
                     # stat_leaves, stat_leave_last, stat_client_errors, stat_loads, stat_acquisition) and stat_play_daily;
                     # 6: live chat (chat_*, live_effects: game/live_chat.py, live/), 1.0.0;
                     # 7: dates (live_dates, date_bonds: game/live_dating.py, live/dating.py), 1.0.1
                     # 8: live weddings (wedding_dates, wedding_parties, wedding_guests, wedding_photos, wedding_race,
                     #    player_closeness: game/wedding_live.py, live/wedding.py), 1.1.0
                     # 9: weekly leaderboard titles (lb_weekly: game/lb_titles.py)
                     # 10: 📌 admin messages and the pinned message of Cả phố (chat_messages.adm, chat_pins:
                     #     game/live_chat.py, live/chat.py, scripts/chat_pin.py)
                     # 11: 😍 reactions (chat_reacts) and the admin-only original text (chat_messages.raw), 1.2.2
                     # 12: 🙂 chat faces (chat_faces: live/faces.py, live/chat.py)
                     # 13: 🗑️ "xóa ở phía tôi" (chat_hides: one message, chat_clears: a whole chat up to an id; live/chat.py)

# UTC timestamp text, independent of the connection's TimeZone.
NOW_TEXT = "to_char(statement_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"       # CURRENT_TIMESTAMP
UNIXEPOCH = "floor(extract(epoch FROM statement_timestamp()))"                                # unixepoch()
VN_DAY = "to_char((statement_timestamp() AT TIME ZONE 'UTC') + interval '7 hours', 'YYYY-MM-DD')"  # date('now','+7 hours')

# Play time (stat_play, the same rule as game/admin_stats.py SCHEMA): a command within PLAY_GAP seconds
# of the save's previous one that day continues the session (the gap counts as played); a longer gap
# starts a new session. Each session also counts PLAY_IDLE_TAIL seconds after its last command.
PLAY_GAP = 600
PLAY_IDLE_TAIL = 60

T = 'text COLLATE "C"'
ID = 'bigint GENERATED BY DEFAULT AS IDENTITY'

TABLES_DDL = f"""
CREATE TABLE IF NOT EXISTS mnl_meta (key {T} PRIMARY KEY, value {T} NOT NULL);

CREATE TABLE IF NOT EXISTS sessions (
  sid {T} PRIMARY KEY, csrf {T} NOT NULL, revision bigint NOT NULL DEFAULT 0,
  state {T} NOT NULL, updated_at {T} NOT NULL DEFAULT {NOW_TEXT}
);
-- Only explicitly shared temple cards; private save/archive rows are never backfilled.
CREATE TABLE IF NOT EXISTS chua_public_cards (
  position {ID} PRIMARY KEY,
  sid {T} NOT NULL REFERENCES sessions(sid) ON DELETE CASCADE,
  card_id {T} NOT NULL, card {T} NOT NULL,
  UNIQUE(sid, card_id)
);
CREATE TABLE IF NOT EXISTS receipts (
  sid {T} NOT NULL, request_id {T} NOT NULL, request_hash {T} NOT NULL,
  result {T} NOT NULL, created_at {T} NOT NULL DEFAULT {NOW_TEXT},
  PRIMARY KEY (sid, request_id)
);
CREATE TABLE IF NOT EXISTS accounts (
  uid {ID} PRIMARY KEY, username {T} UNIQUE NOT NULL, display {T} NOT NULL,
  pw {T} NOT NULL, sid {T} UNIQUE NOT NULL,
  created_at {T} NOT NULL DEFAULT {NOW_TEXT}, updated_at {T} NOT NULL DEFAULT {NOW_TEXT}
);
CREATE TABLE IF NOT EXISTS logins (
  token {T} PRIMARY KEY, sid {T} NOT NULL, csrf {T} NOT NULL,
  created_at {T} NOT NULL DEFAULT {NOW_TEXT}, seen_at {T} NOT NULL DEFAULT {NOW_TEXT}
);
CREATE TABLE IF NOT EXISTS tiktok_identities (
  client_key {T} NOT NULL, open_id {T} NOT NULL, uid bigint NOT NULL, sid {T} NOT NULL,
  display {T} NOT NULL, created_at {T} NOT NULL DEFAULT {NOW_TEXT},
  PRIMARY KEY(client_key,open_id), UNIQUE(client_key,uid)
);
CREATE TABLE IF NOT EXISTS tiktok_flows (
  state_hash {T} PRIMARY KEY, binding_hash {T} UNIQUE NOT NULL,
  source_token {T} NOT NULL, source_sid {T} NOT NULL, source_login bigint NOT NULL,
  mode {T} NOT NULL, client_key {T} NOT NULL, expires_at double precision NOT NULL,
  phase {T} NOT NULL, target_uid bigint, nonce_hash {T}
);
CREATE TABLE IF NOT EXISTS town_treasure_waves (
  bucket bigint PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS town_treasure_chests (
  id {T} PRIMARY KEY, bucket bigint NOT NULL REFERENCES town_treasure_waves(bucket) ON DELETE CASCADE,
  map_id {T} NOT NULL, x double precision NOT NULL, y double precision NOT NULL,
  winner {T}, won_at double precision, request_id {T}, result {T},
  UNIQUE(winner,request_id)
);
CREATE INDEX IF NOT EXISTS town_treasure_chests_bucket ON town_treasure_chests(bucket);
CREATE INDEX IF NOT EXISTS town_treasure_unclaimed_location ON town_treasure_chests(map_id,x,y,bucket,id) WHERE winner IS NULL;
CREATE INDEX IF NOT EXISTS town_treasure_claimed_age ON town_treasure_chests(won_at) WHERE winner IS NOT NULL;
CREATE TABLE IF NOT EXISTS town_treasure_presence (
  sid {T} PRIMARY KEY REFERENCES sessions(sid) ON DELETE CASCADE, lease {T} NOT NULL,
  map_id {T} NOT NULL, x double precision NOT NULL, y double precision NOT NULL,
  seen_at double precision NOT NULL, online bigint NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS town_treasure_presence_age ON town_treasure_presence(seen_at);
CREATE TABLE IF NOT EXISTS town_treasure_proofs (
  sid {T} PRIMARY KEY REFERENCES sessions(sid) ON DELETE CASCADE, chest_id {T} NOT NULL,
  proof_hash {T} NOT NULL, lease {T} NOT NULL, created_at double precision NOT NULL
);

CREATE TABLE IF NOT EXISTS player_feedback (
  id {ID} PRIMARY KEY, sid {T} NOT NULL, account {T},
  kind {T} NOT NULL, text {T} NOT NULL, context {T} NOT NULL DEFAULT '{{}}',
  status {T} NOT NULL DEFAULT 'new', reply {T},
  created_at double precision NOT NULL, updated_at double precision NOT NULL, replied_at double precision
);
-- Private feedback attachments live with the database, including rolling releases/backups.
-- No FK to sessions: idle guest cleanup must not delete submitted feedback/images.
CREATE TABLE IF NOT EXISTS player_feedback_images (
  id {T} PRIMARY KEY, feedback_id bigint NOT NULL REFERENCES player_feedback(id) ON DELETE CASCADE,
  position smallint NOT NULL CHECK(position BETWEEN 0 AND 2),
  mime {T} NOT NULL CHECK(mime IN ('image/png','image/jpeg','image/webp')),
  width integer NOT NULL CHECK(width BETWEEN 1 AND 10000), height integer NOT NULL CHECK(height BETWEEN 1 AND 10000),
  byte_size integer NOT NULL CHECK(byte_size BETWEEN 1 AND 2097152), data bytea NOT NULL,
  UNIQUE(feedback_id,position), CHECK(octet_length(data)=byte_size), CHECK(width::bigint*height<=12600000)
);
CREATE TABLE IF NOT EXISTS archive (
  sid {T} NOT NULL, career {T} NOT NULL, kind {T} NOT NULL, seq bigint NOT NULL,
  day bigint, row {T} NOT NULL, created_at double precision NOT NULL DEFAULT {UNIXEPOCH},
  CONSTRAINT archive_rows UNIQUE (sid, career, kind, seq)
);

CREATE TABLE IF NOT EXISTS profiles (
  pid {T} PRIMARY KEY, sid {T} UNIQUE NOT NULL, name {T}, name_key {T} UNIQUE, bio {T} NOT NULL DEFAULT '',
  avatar {T} NOT NULL DEFAULT '🌸', visible bigint NOT NULL DEFAULT 0, shop {T} NOT NULL DEFAULT '{{}}',
  served bigint NOT NULL DEFAULT 0, week_key {T} NOT NULL DEFAULT '', week_base bigint NOT NULL DEFAULT 0,
  reports bigint NOT NULL DEFAULT 0, hidden bigint NOT NULL DEFAULT 0,
  created double precision NOT NULL, updated double precision NOT NULL, seen double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS work_visit_places (
  id {T} PRIMARY KEY, owner {T} NOT NULL, kind {T} NOT NULL, target {T} NOT NULL,
  visibility {T} NOT NULL DEFAULT 'friends', data {T} NOT NULL, updated_at double precision NOT NULL,
  UNIQUE(owner,kind,target)
);
CREATE TABLE IF NOT EXISTS work_service_orders (
  id {T} PRIMARY KEY, place {T} NOT NULL, customer {T} NOT NULL, provider {T} NOT NULL,
  status {T} NOT NULL, price bigint NOT NULL CHECK(price >= 0), request_id {T} NOT NULL,
  fingerprint {T} NOT NULL, data {T} NOT NULL, created_at double precision NOT NULL,
  updated_at double precision NOT NULL, UNIQUE(customer,request_id)
);
CREATE TABLE IF NOT EXISTS work_service_reviews (
  order_id {T} PRIMARY KEY, place {T} NOT NULL, customer {T} NOT NULL, provider {T} NOT NULL,
  stars bigint NOT NULL CHECK(stars BETWEEN 1 AND 5), tags {T} NOT NULL, comment {T} NOT NULL,
  reply {T} NOT NULL DEFAULT '', created_at double precision NOT NULL, updated_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS visits (
  from_pid {T}, to_pid {T}, day {T}, at double precision, PRIMARY KEY (from_pid, to_pid, day)
);
CREATE TABLE IF NOT EXISTS previews (
  id {ID} PRIMARY KEY, from_pid {T} NOT NULL, to_pid {T} NOT NULL, career {T} NOT NULL, day {T} NOT NULL,
  stars bigint NOT NULL, text {T} NOT NULL, reply {T}, reply_at double precision, at double precision NOT NULL,
  reports bigint NOT NULL DEFAULT 0, hidden bigint NOT NULL DEFAULT 0, UNIQUE (from_pid, to_pid, day)
);
CREATE TABLE IF NOT EXISTS gifts (
  id {ID} PRIMARY KEY, from_pid {T} NOT NULL, to_pid {T} NOT NULL, sticker {T} NOT NULL, coins bigint NOT NULL,
  note {T} NOT NULL DEFAULT '', day {T} NOT NULL, at double precision NOT NULL, claimed bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS market (
  id {ID} PRIMARY KEY, seller {T} NOT NULL, career {T} NOT NULL, item {T} NOT NULL, qty bigint NOT NULL,
  price bigint NOT NULL, life_left bigint NOT NULL, unit_cost bigint NOT NULL, listed_day bigint NOT NULL,
  status {T} NOT NULL, buyer {T}, at double precision NOT NULL, sold_at double precision, settled bigint NOT NULL DEFAULT 0,
  reports bigint NOT NULL DEFAULT 0, hidden bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS board (
  id {ID} PRIMARY KEY, pid {T} NOT NULL, career {T} NOT NULL, kind {T} NOT NULL, text {T} NOT NULL,
  at double precision NOT NULL, reports bigint NOT NULL DEFAULT 0, hidden bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS comments (
  id {ID} PRIMARY KEY, post bigint NOT NULL, pid {T} NOT NULL, text {T} NOT NULL, at double precision NOT NULL,
  reports bigint NOT NULL DEFAULT 0, hidden bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS reactions (post bigint NOT NULL, pid {T} NOT NULL, emoji {T} NOT NULL, PRIMARY KEY (post, pid, emoji));
CREATE TABLE IF NOT EXISTS follows (pid {T} NOT NULL, target {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (pid, target));
CREATE TABLE IF NOT EXISTS blocks (pid {T} NOT NULL, target {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (pid, target));
CREATE TABLE IF NOT EXISTS reports (
  reporter {T} NOT NULL, kind {T} NOT NULL, target {T} NOT NULL, reason {T} NOT NULL, at double precision NOT NULL,
  PRIMARY KEY (reporter, kind, target)
);
CREATE TABLE IF NOT EXISTS inbox (
  id {ID} PRIMARY KEY, pid {T} NOT NULL, kind {T} NOT NULL, text {T} NOT NULL, ref {T}, at double precision NOT NULL,
  read bigint NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS push_subs (
  endpoint {T} PRIMARY KEY, sid {T} NOT NULL, created double precision NOT NULL, last_ok double precision,
  fails bigint NOT NULL DEFAULT 0, prefs {T} NOT NULL DEFAULT '{{}}'
);
CREATE TABLE IF NOT EXISTS push_queue (
  id {ID} PRIMARY KEY, sid {T} NOT NULL, kind {T} NOT NULL, body {T} NOT NULL, url {T} NOT NULL,
  at double precision NOT NULL, sent bigint NOT NULL DEFAULT 0, shown bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS push_daily (sid {T} PRIMARY KEY, day {T} NOT NULL);

CREATE TABLE IF NOT EXISTS stat_births (sid {T} PRIMARY KEY, day {T} NOT NULL);
CREATE TABLE IF NOT EXISTS stat_active (day {T} NOT NULL, sid {T} NOT NULL, PRIMARY KEY (day, sid));
CREATE TABLE IF NOT EXISTS stat_fb_ack (id bigint PRIMARY KEY, at double precision NOT NULL);
-- Play time per save per Vietnam day (game/admin_stats.py "Thời gian chơi"), kept by the trigger
-- stat_play_cmd on receipts (one receipt = one game command). Today's rows are updated on every
-- command: room on each page for HOT updates (no index write) and an early vacuum.
CREATE TABLE IF NOT EXISTS stat_play (
  day {T} NOT NULL, sid {T} NOT NULL, secs bigint NOT NULL, sessions bigint NOT NULL, cmds bigint NOT NULL,
  first_at double precision NOT NULL, last_at double precision NOT NULL, hours bigint NOT NULL DEFAULT 0,
  sess_at double precision NOT NULL, lens {T} NOT NULL DEFAULT '',
  PRIMARY KEY (day, sid)
) WITH (fillfactor = 90, autovacuum_vacuum_scale_factor = 0.01, autovacuum_analyze_scale_factor = 0.02);
CREATE TABLE IF NOT EXISTS stat_play_est (day {T} PRIMARY KEY, saves bigint NOT NULL, capped bigint NOT NULL, at double precision NOT NULL);
-- One row per finished day of stat_play, written before its per-player rows are purged (kept forever).
CREATE TABLE IF NOT EXISTS stat_play_daily (day {T} PRIMARY KEY, players bigint NOT NULL, secs bigint NOT NULL, sessions bigint NOT NULL,
  cmds bigint NOT NULL, data {T} NOT NULL, at double precision NOT NULL);

-- Giữ chân (game/retention.py): funnel steps per save (kept), commands per player per day (fillfactor:
-- today's rows are updated by each worker's flush, HOT), leave beacons, client errors, load times,
-- where new players came from. None of them is ever read to serve a player.
CREATE TABLE IF NOT EXISTS stat_milestones (
  sid {T} NOT NULL, key {T} NOT NULL, at double precision, day bigint, career {T}, detail {T}, PRIMARY KEY (sid, key)
);
CREATE TABLE IF NOT EXISTS stat_actions (
  day {T} NOT NULL, sid {T} NOT NULL, career {T} NOT NULL, action {T} NOT NULL, n integer NOT NULL, errors integer NOT NULL DEFAULT 0,
  err {T}, PRIMARY KEY (day, sid, career, action)
) WITH (fillfactor = 90, autovacuum_vacuum_scale_factor = 0.02, autovacuum_analyze_scale_factor = 0.05);
CREATE TABLE IF NOT EXISTS stat_actions_daily (
  day {T} NOT NULL, career {T} NOT NULL, action {T} NOT NULL, players bigint NOT NULL, n bigint NOT NULL, errors bigint NOT NULL,
  err {T}, PRIMARY KEY (day, career, action)
);
CREATE TABLE IF NOT EXISTS stat_rollups (kind {T} NOT NULL, day {T} NOT NULL, rows bigint NOT NULL, at double precision NOT NULL, PRIMARY KEY (kind, day));
CREATE TABLE IF NOT EXISTS stat_leaves (
  id {ID} PRIMARY KEY, sid {T} NOT NULL, at double precision NOT NULL, day {T} NOT NULL, payload {T} NOT NULL
);
CREATE TABLE IF NOT EXISTS stat_leave_last (sid {T} PRIMARY KEY, at double precision NOT NULL, payload {T} NOT NULL) WITH (fillfactor = 80);
CREATE TABLE IF NOT EXISTS stat_client_errors (
  day {T} NOT NULL, kind {T} NOT NULL, message_key {T} NOT NULL, screen {T} NOT NULL, count bigint NOT NULL,
  last_at double precision NOT NULL, sample {T}, PRIMARY KEY (day, kind, message_key, screen)
);
CREATE TABLE IF NOT EXISTS stat_loads (
  day {T} NOT NULL, metric {T} NOT NULL, net {T} NOT NULL, who {T} NOT NULL, cache {T} NOT NULL, tier {T} NOT NULL,
  bucket integer NOT NULL, n bigint NOT NULL, PRIMARY KEY (day, metric, net, who, cache, tier, bucket)
);
CREATE TABLE IF NOT EXISTS stat_acquisition (
  sid {T} PRIMARY KEY, at double precision NOT NULL, day {T} NOT NULL, source {T}, medium {T}, campaign {T}, ref_domain {T}
);

CREATE TABLE IF NOT EXISTS hits (k {T} NOT NULL, at double precision NOT NULL);

-- Bảng xếp hạng (game/leaderboard.py)
CREATE TABLE IF NOT EXISTS leaderboard (
  sid {T} NOT NULL, board {T} NOT NULL,
  score bigint NOT NULL, k1 bigint NOT NULL, k2 bigint NOT NULL,
  level bigint NOT NULL, days bigint NOT NULL, served bigint NOT NULL,
  stars bigint NOT NULL, mastered bigint NOT NULL,
  since double precision NOT NULL, updated double precision NOT NULL,
  PRIMARY KEY (sid, board)
);
CREATE TABLE IF NOT EXISTS leaderboard_players (
  sid {T} PRIMARY KEY, name {T}, show bigint, updated double precision NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS leaderboard_meta (k {T} PRIMARY KEY, v {T} NOT NULL);
-- 🏅 Danh hiệu tuần (game/lb_titles.py): the holders per (week, board, rank); final=0 now, final=1 past weeks (kept)
CREATE TABLE IF NOT EXISTS lb_weekly (
  week {T} NOT NULL, board {T} NOT NULL, rank bigint NOT NULL, sid {T} NOT NULL, score bigint NOT NULL,
  title {T} NOT NULL, final bigint NOT NULL DEFAULT 0, day {T} NOT NULL, at double precision NOT NULL,
  PRIMARY KEY (week, board, rank)
);

-- Hôn nhân (game/marriage.py), bạn bè (game/friends.py), vợ chồng (game/couple.py)
CREATE TABLE IF NOT EXISTS marriage_people (
  sid {T} PRIMARY KEY, code {T} UNIQUE NOT NULL, accept bigint NOT NULL DEFAULT 1,
  life_day bigint, pool {T}, remarry_after double precision NOT NULL DEFAULT 0,
  notice {T}, notice_at double precision, created double precision NOT NULL, updated double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS marriage_rings (
  id {T} PRIMARY KEY, sid {T} NOT NULL, tier {T} NOT NULL, price bigint NOT NULL,
  status {T} NOT NULL, at double precision NOT NULL, metal {T}, stone {T}
);
CREATE TABLE IF NOT EXISTS proposals (
  id {ID} PRIMARY KEY, from_sid {T} NOT NULL, to_sid {T} NOT NULL, ring {T} NOT NULL,
  message {T} NOT NULL, announce bigint NOT NULL DEFAULT 1, status {T} NOT NULL, at double precision NOT NULL, decided double precision
);
CREATE TABLE IF NOT EXISTS couples (
  id {ID} PRIMARY KEY, a {T} NOT NULL, b {T} NOT NULL, ring {T},
  status {T} NOT NULL, since double precision NOT NULL, married_at double precision, ended double precision, ended_by {T}
);
CREATE TABLE IF NOT EXISTS marriage_bonds (sid {T} PRIMARY KEY, couple bigint NOT NULL);
CREATE TABLE IF NOT EXISTS weddings (
  id {ID} PRIMARY KEY, couple bigint NOT NULL, status {T} NOT NULL,
  version bigint NOT NULL DEFAULT 1, planner {T}, plan {T} NOT NULL, quote {T} NOT NULL,
  split_a bigint NOT NULL DEFAULT 50, announce_a bigint NOT NULL DEFAULT 1, announce_b bigint NOT NULL DEFAULT 1,
  days bigint NOT NULL, target_a bigint, target_b bigint, due_at double precision,
  deposit_a bigint NOT NULL DEFAULT 0, deposit_b bigint NOT NULL DEFAULT 0, result {T},
  seen_a bigint NOT NULL DEFAULT 0, seen_b bigint NOT NULL DEFAULT 0,
  created double precision NOT NULL, confirmed_at double precision, done_at double precision
);
CREATE TABLE IF NOT EXISTS marriage_effects (
  id {T} PRIMARY KEY, sid {T} NOT NULL, kind {T} NOT NULL, amount bigint NOT NULL DEFAULT 0,
  label {T} NOT NULL DEFAULT '', data {T} NOT NULL DEFAULT '{{}}', status {T} NOT NULL,
  due double precision NOT NULL DEFAULT 0, at double precision NOT NULL, applied_at double precision
);
CREATE TABLE IF NOT EXISTS marriage_blocks (sid {T} NOT NULL, target {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (sid, target));
CREATE TABLE IF NOT EXISTS news (
  id {ID} PRIMARY KEY, kind {T} NOT NULL, ref {T} UNIQUE NOT NULL, text {T} NOT NULL,
  a {T}, b {T}, at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS friend_prefs (sid {T} PRIMARY KEY, findable bigint NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS friend_requests (
  id {ID} PRIMARY KEY, from_sid {T} NOT NULL, to_sid {T} NOT NULL, status {T} NOT NULL, at double precision NOT NULL, decided double precision
);
CREATE TABLE IF NOT EXISTS friends (sid {T} NOT NULL, friend {T} NOT NULL, since double precision NOT NULL, PRIMARY KEY (sid, friend));
CREATE TABLE IF NOT EXISTS home_guest_invites (
  id {T} PRIMARY KEY, owner {T} NOT NULL, guest {T} NOT NULL,
  home_id {T} NOT NULL, home_kind {T} NOT NULL,
  kind {T} NOT NULL CHECK (kind IN ('visit','stay')),
  status {T} NOT NULL CHECK (status IN ('pending','accepted','declined','revoked','left','expired')),
  created_at double precision NOT NULL, expires_at double precision,
  CHECK (owner <> guest)
);
CREATE TABLE IF NOT EXISTS friend_searches (sid {T} NOT NULL, at double precision NOT NULL);
CREATE TABLE IF NOT EXISTS joint_funds (couple bigint PRIMARY KEY, balance bigint NOT NULL DEFAULT 0, updated double precision NOT NULL);
CREATE TABLE IF NOT EXISTS joint_ledger (
  id {ID} PRIMARY KEY, couple bigint NOT NULL, sid {T}, kind {T} NOT NULL, amount bigint NOT NULL,
  balance bigint NOT NULL, label {T} NOT NULL DEFAULT '', ref {T} UNIQUE NOT NULL, status {T} NOT NULL DEFAULT 'done', at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS couple_requests (
  id {ID} PRIMARY KEY, couple bigint NOT NULL, from_sid {T} NOT NULL, to_sid {T} NOT NULL, kind {T} NOT NULL,
  amount bigint NOT NULL DEFAULT 0, note {T} NOT NULL DEFAULT '', loan bigint NOT NULL DEFAULT 0, debt bigint,
  status {T} NOT NULL, at double precision NOT NULL, decided double precision
);
CREATE TABLE IF NOT EXISTS couple_debts (
  id {ID} PRIMARY KEY, couple bigint NOT NULL, lender {T} NOT NULL, borrower {T} NOT NULL,
  amount bigint NOT NULL, repaid bigint NOT NULL DEFAULT 0, status {T} NOT NULL, note {T} NOT NULL DEFAULT '',
  ref {T} UNIQUE NOT NULL, at double precision NOT NULL, updated double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS couple_moments (
  id {ID} PRIMARY KEY, couple bigint NOT NULL, sid {T} NOT NULL, kind {T} NOT NULL, text {T} NOT NULL,
  key {T} UNIQUE NOT NULL, at double precision NOT NULL, seen bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS couple_stats (
  couple bigint PRIMARY KEY, happy bigint NOT NULL DEFAULT 0, streak bigint NOT NULL DEFAULT 0, best bigint NOT NULL DEFAULT 0,
  last_day bigint NOT NULL DEFAULT 0, today bigint NOT NULL DEFAULT 0
);

-- 👶 Shared family, mutual invitations and surviving parents' private custody copies.
CREATE TABLE IF NOT EXISTS family_children (
  couple bigint PRIMARY KEY, state {T} NOT NULL, revision bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS family_custody (
  child bigint NOT NULL, sid {T} NOT NULL, state {T} NOT NULL, revision bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (child,sid)
);
CREATE TABLE IF NOT EXISTS family_requests (
  id {ID} PRIMARY KEY, couple bigint NOT NULL, from_sid {T} NOT NULL, to_sid {T} NOT NULL,
  kind {T} NOT NULL, data {T} NOT NULL, status {T} NOT NULL DEFAULT 'pending', at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS family_receipts (
  sid {T} NOT NULL, rid {T} NOT NULL, op {T} NOT NULL, fingerprint {T} NOT NULL,
  result {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (sid,rid)
);

-- 🎁 Quà từ Phố Có Chuyện (game/system_gift.py): a gift from the operator to one save, pending -> applied -> seen
CREATE TABLE IF NOT EXISTS system_gifts (
  id {T} PRIMARY KEY, sid {T} NOT NULL, coins bigint NOT NULL, title {T} NOT NULL, text {T} NOT NULL,
  status {T} NOT NULL, created double precision NOT NULL, applied_at double precision, seen_at double precision,
  granted_by {T}
);
-- granted_by: the admin account that gave it from /admin ("🎁 Tặng xu"); NULL for scripts/grant_gift.py and older rows.
-- Added in 16 (nullable, no default: no table rewrite); earlier releases name their columns and never read it.
ALTER TABLE system_gifts ADD COLUMN IF NOT EXISTS granted_by {T};

-- 💬 Chat (the live service, live/; admin side in game/live_chat.py). Messages are kept: a player's own
-- delete empties the text (deleted=1); reports and the admin hide (hidden 1 = auto-hidden after 3 reports,
-- 2 = hidden by an admin) never remove a row.
CREATE TABLE IF NOT EXISTS chat_channels (
  id {T} PRIMARY KEY, kind {T} NOT NULL, title {T} NOT NULL DEFAULT '', owner_pid {T}, created double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_members (
  channel {T} NOT NULL, pid {T} NOT NULL, sid {T} NOT NULL, role {T} NOT NULL DEFAULT 'member', joined double precision NOT NULL,
  last_read bigint NOT NULL DEFAULT 0, muted_until double precision NOT NULL DEFAULT 0, pushed_at double precision NOT NULL DEFAULT 0,
  PRIMARY KEY (channel, pid)
);
CREATE TABLE IF NOT EXISTS chat_messages (
  id {ID} PRIMARY KEY, channel {T} NOT NULL, pid {T} NOT NULL, name {T} NOT NULL DEFAULT '', av {T} NOT NULL DEFAULT '',
  text {T} NOT NULL, at double precision NOT NULL, hidden bigint NOT NULL DEFAULT 0, deleted bigint NOT NULL DEFAULT 0,
  reports bigint NOT NULL DEFAULT 0, reviewed_at double precision, adm bigint NOT NULL DEFAULT 0, raw {T}
);
-- adm = 1: written by an admin (ADMIN_USERS) on Cả phố. Added in 10 (a constant default: no table rewrite).
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS adm bigint NOT NULL DEFAULT 0;
-- raw: what the player typed when the filter masked part of it (NULL when the text is as typed). Admins only,
-- never sent to players. Added in 11 (nullable, no default: no table rewrite); older rows stay NULL.
-- Since 13 a message its author takes back (Thu hồi) after somebody reported it keeps its text here for the admin.
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS raw {T};
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS reply_to bigint;
-- 🗄️ Cả phố's older messages (live/chat.py prune_town; SCHEMA_VERSION 55; owner 17/10 "giữ khoảng mấy trăm tin gần nhất,
-- cái cũ thì đưa vào đâu đấy"): moved here as they were, archived_at added. Never read by the game nor sent to players.
CREATE TABLE IF NOT EXISTS chat_archive (
  id bigint PRIMARY KEY, channel {T} NOT NULL, pid {T} NOT NULL, name {T} NOT NULL DEFAULT '', av {T} NOT NULL DEFAULT '',
  text {T} NOT NULL, at double precision NOT NULL, hidden bigint NOT NULL DEFAULT 0, deleted bigint NOT NULL DEFAULT 0,
  reports bigint NOT NULL DEFAULT 0, reviewed_at double precision, adm bigint NOT NULL DEFAULT 0, raw {T}, reply_to bigint,
  archived_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_mutes (
  pid {T} PRIMARY KEY, until double precision NOT NULL, by_admin {T} NOT NULL DEFAULT '', reason {T} NOT NULL DEFAULT '',
  at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_prefs (pid {T} PRIMARY KEY, online bigint NOT NULL DEFAULT 1, updated double precision NOT NULL);
-- 😍 Reactions (live/chat.py): one per player per message, replaced or removed by the player.
CREATE TABLE IF NOT EXISTS chat_reacts (
  msg bigint NOT NULL, pid {T} NOT NULL, emoji {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (msg, pid)
);
-- 📌 The pinned message of a channel (Cả phố only for now): one row, read by the live service by primary key.
CREATE TABLE IF NOT EXISTS chat_pins (
  channel {T} PRIMARY KEY, msg bigint NOT NULL, by_pid {T} NOT NULL, at double precision NOT NULL
);
-- 🙂 The face of a player's chat avatar (live/faces.py code of whitelisted ids), written by the live service only.
CREATE TABLE IF NOT EXISTS chat_faces (pid {T} PRIMARY KEY, code {T} NOT NULL, at double precision NOT NULL);
-- 🗑️ Deleted on one side only (live/chat.py): a message a player removed from their own screen, and a whole chat
-- emptied for one player (every message up to `upto`, the chat's newest id then). Nobody else's view changes; the
-- messages themselves stay (admins still see them). Written by the live service only.
CREATE TABLE IF NOT EXISTS chat_hides (pid {T} NOT NULL, msg bigint NOT NULL, at double precision NOT NULL, PRIMARY KEY (pid, msg));
CREATE TABLE IF NOT EXISTS chat_clears (
  channel {T} NOT NULL, pid {T} NOT NULL, upto bigint NOT NULL, at double precision NOT NULL, PRIMARY KEY (channel, pid)
);
-- 🐢 Slow mode set by an admin (game/live_chat.py, read by live/chat.py; SCHEMA_VERSION 24): one player may post on
-- Cả phố once per `every` seconds until `until`; the row with pid 'town' slows Cả phố for everyone. Never a ban.
CREATE TABLE IF NOT EXISTS chat_slow (
  pid {T} PRIMARY KEY, every double precision NOT NULL, until double precision NOT NULL, by_admin {T} NOT NULL DEFAULT '',
  at double precision NOT NULL
);
-- 🙏 Công đức Chùa Gió Lành (game/spend.py; SCHEMA_VERSION 25): one row per donation, written in the save's own
-- transaction (id '<pid>:<n>', idempotent). The weekly board reads it by week. A player who erases their data stays
-- on the board as anonymous (sid '').
CREATE TABLE IF NOT EXISTS donations (
  id {T} PRIMARY KEY, sid {T} NOT NULL, week {T} NOT NULL, amount bigint NOT NULL CHECK(amount > 0),
  wish {T} NOT NULL DEFAULT '', anon bigint NOT NULL DEFAULT 1, at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS donations_week ON donations(week, sid);
-- 🎨 Màu tên, khung hồ sơ, danh hiệu tuần worn now (game/spend.py writes it with the save; live/styles.py reads it by
-- pid and shows it as `st` beside the name). An expired item is ignored by its `_until` (unix seconds).
CREATE TABLE IF NOT EXISTS chat_style (
  pid {T} PRIMARY KEY, sid {T} NOT NULL, color {T} NOT NULL DEFAULT '', color_until double precision NOT NULL DEFAULT 0,
  frame {T} NOT NULL DEFAULT '', frame_until double precision NOT NULL DEFAULT 0, title {T} NOT NULL DEFAULT '',
  title_until double precision NOT NULL DEFAULT 0, at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS chat_style_sid ON chat_style(sid);
-- Rewards the live service grants (phase 3 dates, phase 2 lucky envelopes); the game server applies them on load.
CREATE TABLE IF NOT EXISTS live_effects (
  id {T} PRIMARY KEY, sid {T} NOT NULL, kind {T} NOT NULL, amount bigint NOT NULL DEFAULT 0, data {T} NOT NULL DEFAULT '{{}}',
  status {T} NOT NULL DEFAULT 'pending', at double precision NOT NULL, applied_at double precision
);
-- 💼 Hired players' shifts at someone's counter (game/quay_hire.py): one row per offer, guarded status changes.
CREATE TABLE IF NOT EXISTS quay_jobs (
  id {T} PRIMARY KEY, owner {T} NOT NULL, owner_name {T} NOT NULL, stall {T} NOT NULL, stall_name {T} NOT NULL,
  trade {T} NOT NULL, place {T} NOT NULL, wage bigint NOT NULL, value bigint NOT NULL, friend {T}, worker {T},
  status {T} NOT NULL, day {T} NOT NULL, taken_day {T}, at double precision NOT NULL, taken_at double precision,
  ended double precision, until double precision NOT NULL,
  tasks bigint NOT NULL DEFAULT 0, stars bigint NOT NULL DEFAULT 0, earned bigint NOT NULL DEFAULT 0
);
-- 💸 Transfers between friends (game/bank_xfer.py): one row per transfer (the audit log), guarded status changes;
CREATE TABLE IF NOT EXISTS quay_funding (
  job {T} PRIMARY KEY, owner {T} NOT NULL, rid {T}, fingerprint {T} NOT NULL,
  source {T} NOT NULL, couple bigint, UNIQUE(owner,rid)
);
-- the day counters move with conditional upserts (the caps hold under concurrency).
CREATE TABLE IF NOT EXISTS bank_xfers (
  id {T} PRIMARY KEY, code {T} NOT NULL, sender {T} NOT NULL, receiver {T} NOT NULL, from_name {T} NOT NULL,
  to_name {T} NOT NULL, amount bigint NOT NULL, note {T} NOT NULL DEFAULT '', src {T} NOT NULL, status {T} NOT NULL,
  day {T} NOT NULL, at double precision NOT NULL, done_at double precision
);
-- Prepaid player leases. Session rows are always locked before rental rows.
CREATE TABLE IF NOT EXISTS rentals (
  id {T} PRIMARY KEY, owner {T} NOT NULL, property {T} NOT NULL, kind {T} NOT NULL,
  owner_name {T} NOT NULL, tenant {T}, tenant_name {T} NOT NULL DEFAULT '',
  rent bigint NOT NULL, status {T} NOT NULL, start_day bigint, end_day bigint,
  at double precision NOT NULL, updated double precision NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS rentals_property_active ON rentals(owner,property) WHERE status IN ('listing','leased');
CREATE UNIQUE INDEX IF NOT EXISTS rentals_tenant_active ON rentals(tenant) WHERE status='leased';
CREATE INDEX IF NOT EXISTS rentals_market ON rentals(status,at);
CREATE INDEX IF NOT EXISTS rentals_owner ON rentals(owner,at);
CREATE INDEX IF NOT EXISTS rentals_tenant ON rentals(tenant,status);
CREATE TABLE IF NOT EXISTS rental_closed_accounts (sid {T} PRIMARY KEY);
CREATE TABLE IF NOT EXISTS rental_receipts (
  sid {T} NOT NULL, rid {T} NOT NULL, fingerprint {T} NOT NULL, result {T} NOT NULL,
  PRIMARY KEY(sid,rid)
);
CREATE TABLE IF NOT EXISTS bank_xfer_days (
  sid {T} NOT NULL, day {T} NOT NULL, sent bigint NOT NULL DEFAULT 0, n bigint NOT NULL DEFAULT 0,
  got bigint NOT NULL DEFAULT 0, PRIMARY KEY (sid, day)
);
-- 💕 Dates of the live service (live/dating.py; game/live_dating.py): one row per café date (pids a < b), and the
-- bond "đang tìm hiểu" of two saves (sids a < b) that both tapped ❤️.
CREATE TABLE IF NOT EXISTS live_dates (
  id {T} PRIMARY KEY, a {T} NOT NULL, b {T} NOT NULL, a_sid {T} NOT NULL, b_sid {T} NOT NULL, at double precision NOT NULL,
  ended double precision, how {T} NOT NULL DEFAULT '', same bigint NOT NULL DEFAULT 0, hits bigint NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS date_bonds (a {T} NOT NULL, b {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (a, b));
-- 💍 Live weddings (game/wedding_live.py, live/wedding.py): the couple's date for good (insert-only), the parties,
-- the guests who stayed 5 minutes, the group photos, the settled weekly race, closeness between players.
CREATE TABLE IF NOT EXISTS wedding_dates (
  couple bigint PRIMARY KEY, at double precision NOT NULL, source {T} NOT NULL, wedding bigint, created double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS wedding_parties (
  wedding bigint PRIMARY KEY, couple bigint NOT NULL, a {T} NOT NULL, b {T} NOT NULL, at double precision NOT NULL,
  status {T} NOT NULL DEFAULT 'booked', reminded double precision, guests bigint NOT NULL DEFAULT 0, done_at double precision,
  created double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS wedding_guests (
  wedding bigint NOT NULL, sid {T} NOT NULL, pid {T} NOT NULL, ok bigint NOT NULL DEFAULT 0, paid bigint NOT NULL DEFAULT 0,
  steps bigint NOT NULL DEFAULT 0, counted_at double precision NOT NULL, day {T} NOT NULL, week {T} NOT NULL,
  PRIMARY KEY (wedding, sid)
);
CREATE TABLE IF NOT EXISTS wedding_photos (
  wedding bigint NOT NULL, n bigint NOT NULL, sid {T} NOT NULL, at double precision NOT NULL, image {T}, PRIMARY KEY (wedding, n)
);
CREATE TABLE IF NOT EXISTS wedding_race (week {T} PRIMARY KEY, settled double precision NOT NULL, top {T} NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS player_closeness (
  sid {T} NOT NULL, other {T} NOT NULL, points bigint NOT NULL DEFAULT 0, updated double precision NOT NULL, PRIMARY KEY (sid, other)
);
-- 🎤 Phòng hát (game/karaoke.py, live/karaoke.py; SCHEMA_VERSION 26): the oEmbed cache of each YouTube id (only the id,
-- never a link; banned by an admin), the "lượt hát" tickets and tips (one row each, idempotent by id; a queue ticket is
-- redeemed by the live service (used) and stamped when its song starts (played)), and the admin's reviews of reports.
CREATE TABLE IF NOT EXISTS kara_songs (
  vid {T} PRIMARY KEY, title {T} NOT NULL DEFAULT '', channel {T} NOT NULL DEFAULT '', ok bigint NOT NULL DEFAULT 0,
  why {T} NOT NULL DEFAULT '', checked_at double precision NOT NULL DEFAULT 0, plays bigint NOT NULL DEFAULT 0,
  banned bigint NOT NULL DEFAULT 0, banned_by {T}, banned_at double precision
);
CREATE TABLE IF NOT EXISTS kara_tickets (
  id {T} PRIMARY KEY, sid {T} NOT NULL, kind {T} NOT NULL, amount bigint NOT NULL DEFAULT 0, got bigint NOT NULL DEFAULT 0,
  ref {T}, to_sid {T}, vid {T}, room {T}, used bigint NOT NULL DEFAULT 0, played double precision,
  day {T} NOT NULL, at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS kara_reviews (
  target {T} PRIMARY KEY, verdict {T} NOT NULL, by_admin {T} NOT NULL DEFAULT '', at double precision NOT NULL
);
-- 🐾 Bé cưng của tuần (game/pets.py; SCHEMA_VERSION 27): each player's best-cared pet of a Vietnam ISO week, written in
-- the save's own transaction on jr_pet_* commands. Cosmetic only. A player who erases their data leaves the board.
CREATE TABLE IF NOT EXISTS pet_board (
  sid {T} NOT NULL, week {T} NOT NULL, name {T} NOT NULL, breed {T} NOT NULL, coat bigint NOT NULL DEFAULT 0,
  acc {T} NOT NULL DEFAULT '[]', pts bigint NOT NULL DEFAULT 0, at double precision NOT NULL, PRIMARY KEY (sid, week)
);
CREATE INDEX IF NOT EXISTS pet_board_week ON pet_board(week, pts);
-- 🎆 Mạnh Thường Quân (game/lux.py; SCHEMA_VERSION 28): one row per public sponsorship (fireworks, a numbered bench or
-- lamp, the fair's or a ZPOP night's sponsor of the week, the school library fund), written in the save's own
-- transaction (id '<pid>:<n>', idempotent). `slot` ('ghe_da:7') is unique among plaques: a slot taken refuses the whole
-- command. The weekly board reads it by week. A player who erases their data stays as anonymous (sid '').
CREATE TABLE IF NOT EXISTS lux_gifts (
  id {T} PRIMARY KEY, sid {T} NOT NULL, week {T} NOT NULL, kind {T} NOT NULL, slot {T} NOT NULL DEFAULT '',
  size {T} NOT NULL DEFAULT '', amount bigint NOT NULL CHECK(amount > 0), msg {T} NOT NULL DEFAULT '',
  anon bigint NOT NULL DEFAULT 0, at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS lux_gifts_week ON lux_gifts(week, sid);
CREATE INDEX IF NOT EXISTS lux_gifts_kind ON lux_gifts(kind, at);
CREATE UNIQUE INDEX IF NOT EXISTS lux_gifts_slot ON lux_gifts(slot) WHERE slot <> '';
-- 🔨 Nhà đấu giá đồ độc bản (game/auction.py; SCHEMA_VERSION 29). One row per lot (system lots: the day's plan
-- '<yyyymmdd>-<slot>' or an operator's 'a<hex>'), locked FOR UPDATE by every bid and by the settlement; `seq` moves on
-- every change (compare-and-set). An item is in at most one open or sold lot (an unsold one goes back to the pool).
CREATE TABLE IF NOT EXISTS auction_lots (
  id {T} PRIMARY KEY, item {T} NOT NULL, kind {T} NOT NULL, tier bigint NOT NULL, name {T} NOT NULL, emoji {T} NOT NULL DEFAULT '',
  data {T} NOT NULL DEFAULT '{{}}', start bigint NOT NULL CHECK(start > 0), step bigint NOT NULL CHECK(step > 0),
  starts_at double precision NOT NULL, ends_at double precision NOT NULL, planned_end double precision NOT NULL,
  status {T} NOT NULL DEFAULT 'open', high bigint NOT NULL DEFAULT 0, high_sid {T} NOT NULL DEFAULT '',
  high_anon bigint NOT NULL DEFAULT 0, bids bigint NOT NULL DEFAULT 0, seq bigint NOT NULL DEFAULT 0,
  winner_sid {T} NOT NULL DEFAULT '', winner_name {T} NOT NULL DEFAULT '', price bigint NOT NULL DEFAULT 0,
  settled_at double precision, src {T} NOT NULL DEFAULT 'plan', created double precision NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS auction_lots_item ON auction_lots(item) WHERE status IN ('open', 'sold');
CREATE INDEX IF NOT EXISTS auction_lots_due ON auction_lots(status, ends_at);
CREATE INDEX IF NOT EXISTS auction_lots_settled ON auction_lots(settled_at);
-- One row per player per lot: the latest bid and the escrow the database knows (`held`, 0 once refunded or burned;
-- refunds travel through live_effects rows 'auc:<lot>:<pid>:b<n>', `refunds` = n).
CREATE TABLE IF NOT EXISTS auction_bids (
  lot {T} NOT NULL, sid {T} NOT NULL, amount bigint NOT NULL CHECK(amount > 0), held bigint NOT NULL DEFAULT 0 CHECK(held >= 0),
  anon bigint NOT NULL DEFAULT 0, n bigint NOT NULL DEFAULT 0, refunds bigint NOT NULL DEFAULT 0, at double precision NOT NULL,
  pushed_at double precision NOT NULL DEFAULT 0, PRIMARY KEY(lot, sid)
);
CREATE INDEX IF NOT EXISTS auction_bids_sid ON auction_bids(sid, lot);
-- 🎙️ Phòng hát mic trực tiếp (game/karaoke_mic.py, live/karaoke.py; SCHEMA_VERSION 30): an account's optional birth year,
-- asked the first time it turns the live mic on (under 16: listening only). Set once; deleted with the player's data.
-- Its own table (not a column of accounts, not a save key): a rollback never sees it.
CREATE TABLE IF NOT EXISTS account_birth (
  sid {T} PRIMARY KEY, year bigint NOT NULL, at double precision NOT NULL
);
-- 🎨 Cho trang trí (game/home_coop.py; SCHEMA_VERSION 31): a friend may move the owner's furniture in one home they own
-- (expires_at NULL: until revoked), and every change they make, with the spots before (`undo`) and after, for Hoàn tác.
-- Tables only, no save key: an older build or a rollback never sees them.
CREATE TABLE IF NOT EXISTS home_deco_grants (
  id {T} PRIMARY KEY, owner {T} NOT NULL, guest {T} NOT NULL,
  home_id {T} NOT NULL, home_kind {T} NOT NULL,
  status {T} NOT NULL CHECK (status IN ('active','revoked','left','expired','ended')),
  created_at double precision NOT NULL, expires_at double precision, ended_at double precision,
  CHECK (owner <> guest)
);
CREATE TABLE IF NOT EXISTS home_deco_log (
  id {ID} PRIMARY KEY, owner {T} NOT NULL, actor {T} NOT NULL,
  home_id {T} NOT NULL, home_kind {T} NOT NULL, text {T} NOT NULL,
  undo {T} NOT NULL, after {T} NOT NULL, at double precision NOT NULL, undone double precision
);
-- 💌 Thiệp mời cưới cả phố (game/wed_invite.py, live/wedinvite.py; SCHEMA_VERSION 32): one row per paid card (`rid` =
-- its marriage_effects debit, idempotent), and per viewer the last card shown (`upto`), today's count and the last card
-- cheered: written only when a card is shown, never in bulk. Tables only, no save key: an older build never sees them.
CREATE TABLE IF NOT EXISTS wed_invites (
  id {ID} PRIMARY KEY, rid {T} NOT NULL UNIQUE, sid {T} NOT NULL, partner {T} NOT NULL, pid {T} NOT NULL, ppid {T} NOT NULL,
  couple bigint NOT NULL, wedding bigint, name_a {T} NOT NULL, name_b {T} NOT NULL, text {T} NOT NULL, raw {T},
  at double precision NOT NULL, until double precision NOT NULL, status {T} NOT NULL DEFAULT 'live',
  cheers bigint NOT NULL DEFAULT 0, by_admin {T}, deleted_at double precision
);
CREATE TABLE IF NOT EXISTS wed_invite_seen (
  sid {T} PRIMARY KEY, upto bigint NOT NULL DEFAULT 0, day {T} NOT NULL, n bigint NOT NULL DEFAULT 0,
  cheer_upto bigint NOT NULL DEFAULT 0
);
-- 🚔 Trại tạm giữ (game/jail.py mark_commit; SCHEMA_VERSION 33): one row per jailed save, `until` its safety release,
-- written in the save's own transaction, so the live server knows "free" from a primary-key lookup (no save read).
-- Not in the save: an older build ignores it (a stale row is checked against the save and deleted).
CREATE TABLE IF NOT EXISTS jail_marks (sid {T} PRIMARY KEY, until double precision NOT NULL);
-- 👮 Công an phường Mây across players (owner spec 11/10; SCHEMA_VERSION 40). cand_roster: one row per save on the CAND
-- ladder, written in the save's own transaction (game/cand_roster.py command_commit): the seat caps (PGĐ 5, GĐ 1) and
-- the commanders' lists. cand_stops: a patrol's stop of a player at Chợ đen (game/cand_ops.py), status ask -> offer ->
-- done | gone, every move a guarded UPDATE from the status before. cand_acts: a commander's commendation or expulsion,
-- one per (by, target, kind, day). Not in the save: an older build never sees them.
CREATE TABLE IF NOT EXISTS cand_roster (
  sid {T} PRIMARY KEY, name {T} NOT NULL DEFAULT '', post {T} NOT NULL, grade {T} NOT NULL, seen double precision NOT NULL,
  sev double precision NOT NULL DEFAULT 0, sev_code {T} NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS cand_stops (
  id {T} PRIMARY KEY, officer {T} NOT NULL, target {T} NOT NULL, at double precision NOT NULL, status {T} NOT NULL DEFAULT 'ask',
  act {T} NOT NULL DEFAULT '', bribe bigint NOT NULL DEFAULT 0, outcome {T} NOT NULL DEFAULT '', done_at double precision,
  day {T} NOT NULL DEFAULT '', stake bigint NOT NULL DEFAULT 0
);
-- stake: the caught round's stake read from the target's save when the stop opened (the fine is 30% of it).
ALTER TABLE cand_stops ADD COLUMN IF NOT EXISTS stake bigint NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS cand_acts (
  id {T} PRIMARY KEY, by_sid {T} NOT NULL, target {T} NOT NULL, kind {T} NOT NULL, day {T} NOT NULL, at double precision NOT NULL,
  note {T} NOT NULL DEFAULT ''
);
-- 🐕 Kéo co chó sủa (game/dog_bark.py, live/dog_bark.py; SCHEMA_VERSION 34): one row per stake put in escrow (`id` the
-- ticket, the payout row is live_effects 'bark:<id>'). status wait -> play | dog -> done, or -> back (refunded); every
-- move is a guarded UPDATE from the status before, so a ticket is settled once. No save key: an older build never sees it.
CREATE TABLE IF NOT EXISTS bark_tickets (
  id {T} PRIMARY KEY, sid {T} NOT NULL, stake bigint NOT NULL CHECK(stake > 0), status {T} NOT NULL DEFAULT 'wait',
  created double precision NOT NULL, started double precision, ended double precision, match {T} NOT NULL DEFAULT '',
  opp {T} NOT NULL DEFAULT '', result {T} NOT NULL DEFAULT '', pay bigint NOT NULL DEFAULT 0, dog {T} NOT NULL DEFAULT '',
  competitive boolean NOT NULL DEFAULT false
);
-- Legacy live workers omit this field safely; old unverified history never qualifies.
ALTER TABLE bark_tickets ADD COLUMN IF NOT EXISTS competitive boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS bark_tickets_sid ON bark_tickets(sid, created);
CREATE INDEX IF NOT EXISTS bark_tickets_open ON bark_tickets(status, created) WHERE status IN ('wait', 'play', 'dog');
CREATE INDEX IF NOT EXISTS bark_tickets_week ON bark_tickets(ended) WHERE status = 'done';
-- Weekly fair cashflow, atomically updated with save commands; no historical backfill.
CREATE TABLE IF NOT EXISTS fair_loss_week (
  week bigint NOT NULL, sid {T} NOT NULL REFERENCES sessions(sid) ON DELETE CASCADE,
  net bigint NOT NULL, since double precision NOT NULL, PRIMARY KEY(week,sid)
);
CREATE INDEX IF NOT EXISTS fair_loss_week_rank ON fair_loss_week(week,net,since,sid) WHERE net<0;
CREATE INDEX IF NOT EXISTS fair_loss_week_win ON fair_loss_week(week,net DESC,since,sid) WHERE net>0;
-- 🌳 Cây ước nguyện (game/chua_wish.py; SCHEMA_VERSION 44, owner 15/10): one row per wish a player wrote and hung on a
-- tree, written in the save's own transaction (jr_chua_do 'nguyen' with a tree; `key` from the receipt: a replay never
-- hangs twice). status live -> hidden (reports) | removed (admin) | down (the author); never deleted but by the player's
-- own "Xóa dữ liệu". chua_wish_prayers: 🙏 cùng cầu, once per player and wish. Reports go to `reports` (kind 'wish').
-- No save key and no FK to sessions: an older build never sees them.
CREATE TABLE IF NOT EXISTS chua_wishes (
  id {ID} PRIMARY KEY, key {T} NOT NULL UNIQUE, sid {T} NOT NULL, tree {T} NOT NULL, color {T} NOT NULL,
  text {T} NOT NULL, raw {T}, name {T} NOT NULL DEFAULT '', at double precision NOT NULL, day {T} NOT NULL,
  life_day bigint NOT NULL DEFAULT 0, prayers bigint NOT NULL DEFAULT 0, reports bigint NOT NULL DEFAULT 0,
  status {T} NOT NULL DEFAULT 'live', reviewed_at double precision, by_admin {T}
);
CREATE INDEX IF NOT EXISTS chua_wishes_tree ON chua_wishes(tree, id DESC) WHERE status='live';
CREATE INDEX IF NOT EXISTS chua_wishes_sid ON chua_wishes(sid, day);
CREATE INDEX IF NOT EXISTS chua_wishes_mine ON chua_wishes(sid, id DESC);
CREATE INDEX IF NOT EXISTS chua_wishes_review ON chua_wishes(id DESC) WHERE reports>0 AND reviewed_at IS NULL;
CREATE TABLE IF NOT EXISTS chua_wish_prayers (
  wish bigint NOT NULL, sid {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (wish, sid)
);
CREATE INDEX IF NOT EXISTS chua_wish_prayers_sid ON chua_wish_prayers(sid);
-- 📜 Old shared lời chúc in the wish garden (game/chua_wish.py; SCHEMA_VERSION 45, owner 15/10 "đưa vào 1 cái đi, sử dụng
-- chung mà"): the cards their owners shared (chua_public_cards, schema 42, read where they are, never copied) hang on a
-- tree by their theme. chua_card_marks: one row per card someone prayed for, reported or an admin looked at, keyed by
-- the owner and the card (so un-sharing and sharing again keeps an admin's decision); status live | hidden (reports) |
-- removed (admin). chua_card_prayers: 🙏 cùng cầu, once per player and card. Reports go to `reports` (kind 'card').
-- New tables only, no FK, no backfill: 2.4.16 / 2.4.15 never see them (they keep showing the cards their own way).
CREATE TABLE IF NOT EXISTS chua_card_marks (
  sid {T} NOT NULL, card_id {T} NOT NULL, prayers bigint NOT NULL DEFAULT 0, reports bigint NOT NULL DEFAULT 0,
  status {T} NOT NULL DEFAULT 'live', reviewed_at double precision, by_admin {T}, PRIMARY KEY (sid, card_id)
);
CREATE TABLE IF NOT EXISTS chua_card_prayers (
  sid {T} NOT NULL, card_id {T} NOT NULL, by_sid {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (sid, card_id, by_sid)
);
CREATE INDEX IF NOT EXISTS chua_card_prayers_by ON chua_card_prayers(by_sid);
-- 💐 Thiệp 20/10 (game/event2010.py; SCHEMA_VERSION 46, owner 16/10): one row per card a player wrote on /2010, read by
-- anyone with its link (`id`: 12 random url-safe characters). status live -> hidden (reports) | removed (admin) | down (the
-- sender deleted it: its words are emptied, the row stays for today's count). ev2010_reports: once per reader (their save
-- or their address, hashed). ev2010_rewards: the 100.000 xu, once per account (uid) and per save (sid), with the system
-- gift it queued (system_gifts.id) and the reader's address hashed (clone rings). New tables only, no FK: older builds
-- never see them.
CREATE TABLE IF NOT EXISTS ev2010_cards (
  id {T} PRIMARY KEY, sid {T} NOT NULL, uid bigint, theme {T} NOT NULL, direction {T} NOT NULL, to_name {T} NOT NULL,
  from_name {T} NOT NULL, text {T} NOT NULL, raw {T}, stickers {T} NOT NULL DEFAULT '[]', at double precision NOT NULL,
  day {T} NOT NULL, hearts bigint NOT NULL DEFAULT 0, reports bigint NOT NULL DEFAULT 0, status {T} NOT NULL DEFAULT 'live',
  reviewed_at double precision, by_admin {T}
);
CREATE INDEX IF NOT EXISTS ev2010_cards_sid ON ev2010_cards(sid, day);
CREATE INDEX IF NOT EXISTS ev2010_cards_mine ON ev2010_cards(sid, at DESC);
CREATE INDEX IF NOT EXISTS ev2010_cards_at ON ev2010_cards(at DESC);
CREATE INDEX IF NOT EXISTS ev2010_cards_review ON ev2010_cards(at DESC) WHERE reports>0 AND reviewed_at IS NULL;
CREATE TABLE IF NOT EXISTS ev2010_reports (
  card {T} NOT NULL, reporter {T} NOT NULL, reason {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (card, reporter)
);
CREATE TABLE IF NOT EXISTS ev2010_rewards (
  uid bigint PRIMARY KEY, sid {T} UNIQUE NOT NULL, username {T}, card {T} NOT NULL, gift {T} NOT NULL,
  coins bigint NOT NULL, life_day bigint NOT NULL, ip {T} NOT NULL, at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS ev2010_rewards_ip ON ev2010_rewards(ip);
CREATE INDEX IF NOT EXISTS ev2010_rewards_at ON ev2010_rewards(at DESC);
-- 🛃 Hải quan across players (owner spec 14/10; SCHEMA_VERSION 48). hq_roster: one row per save on the customs ladder,
-- like cand_roster (game/cand_roster.py LADDERS: the seats of Chi cục trưởng 5, Cục trưởng 1, Tổng cục trưởng 1, and the
-- reviewers of a case). hq_cases: a warehouse inspection of a player's shop (game/hq_ops.py), status clear | found ->
-- review -> done | rejected | void (-> reversed after an appeal); every move a guarded UPDATE from the status before.
-- finding: the evidence read from the shop's save (JSON); proper: the Cục's rule for the proposed measure; wrong /
-- rwrong: counted against the officer / the approver. New tables only, no FK, no backfill: 2.4.26 and older never see them.
CREATE TABLE IF NOT EXISTS hq_roster (
  sid {T} PRIMARY KEY, name {T} NOT NULL DEFAULT '', post {T} NOT NULL, grade {T} NOT NULL, seen double precision NOT NULL,
  sev double precision NOT NULL DEFAULT 0, sev_code {T} NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS hq_cases (
  id {T} PRIMARY KEY, officer {T} NOT NULL, target {T} NOT NULL, at double precision NOT NULL, day {T} NOT NULL DEFAULT '',
  status {T} NOT NULL, measure {T} NOT NULL DEFAULT '', finding {T} NOT NULL DEFAULT '{{}}', proper bigint NOT NULL DEFAULT 0,
  opost {T} NOT NULL DEFAULT '', reviewer {T} NOT NULL DEFAULT '', review_at double precision, outcome {T} NOT NULL DEFAULT '',
  amount bigint NOT NULL DEFAULT 0, appeal bigint NOT NULL DEFAULT 0, appeal_at double precision,
  wrong bigint NOT NULL DEFAULT 0, rwrong bigint NOT NULL DEFAULT 0
);
-- 🎨 Thi làm sticker (game/sticker_event.py; SCHEMA_VERSION 49, owner 16/10): one row per sticker an account submitted
-- on /sticker (at most sticker_event.MAX_ENTRIES), the re-encoded 512x512 image (PNG or WebP, at most 400 KB) and a small
-- WebP thumbnail for the operators; status live | rejected (admin); rank 1..10 set by an admin from the Facebook votes
-- (kept for the chat stickers later). sticker_rewards: one row per account and kind (join: the participation gift,
-- prize: the rank's prize), the system_gifts id it queued, granted | revoked. New tables only, no FK, no save key:
-- older releases never read them; a 'revoked' system_gifts row is skipped by every release (on_load pays 'pending' only).
CREATE TABLE IF NOT EXISTS sticker_entries (
  id {ID} PRIMARY KEY, sid {T} NOT NULL, username {T} NOT NULL, display {T} NOT NULL DEFAULT '',
  mime {T} NOT NULL CHECK(mime IN ('image/png','image/webp')), width integer NOT NULL, height integer NOT NULL,
  byte_size integer NOT NULL CHECK(byte_size BETWEEN 1 AND 409600), data bytea NOT NULL, thumb bytea NOT NULL,
  sha {T} NOT NULL, created double precision NOT NULL, life_day bigint NOT NULL DEFAULT 0, ip_tag {T} NOT NULL DEFAULT '',
  status {T} NOT NULL DEFAULT 'live', rank smallint CHECK(rank BETWEEN 1 AND 10), reviewed_at double precision,
  by_admin {T}, note {T} NOT NULL DEFAULT '', CHECK(octet_length(data)=byte_size)
);
CREATE INDEX IF NOT EXISTS sticker_entries_sid ON sticker_entries(sid, id);
CREATE UNIQUE INDEX IF NOT EXISTS sticker_entries_rank ON sticker_entries(rank) WHERE rank IS NOT NULL;
CREATE TABLE IF NOT EXISTS sticker_rewards (
  gift_id {T} PRIMARY KEY, sid {T} NOT NULL, kind {T} NOT NULL CHECK(kind IN ('join','prize')), entry bigint, rank smallint,
  coins bigint NOT NULL, username {T} NOT NULL DEFAULT '', status {T} NOT NULL DEFAULT 'granted', created double precision NOT NULL,
  by_admin {T}, revoked_at double precision, life_day bigint, ip_tag {T}
);
CREATE UNIQUE INDEX IF NOT EXISTS sticker_rewards_once ON sticker_rewards(sid, kind);
-- 🎨 Sticker packs (game/sticker_event.py; SCHEMA_VERSION 50, owner 16/10 afternoon: a whole set of one character's
-- expressions, not single stickers). One pack per account (sid UNIQUE), replaced in place before the deadline (version
-- + 1, its images rewritten): kind sheet (one picture of the whole set, `count` as the author declares it) | set (one
-- 512x512 image per sticker, count = images); ai: the author says AI helped. status live | rejected (admin); rank
-- 1..10 from the Facebook votes; a prize row (sticker_rewards.kind='prize') names the pack in `entry`. sticker_entries
-- keeps the single stickers sent under the first rules (2.4.29), read only. New tables only, no FK.
CREATE TABLE IF NOT EXISTS sticker_packs (
  id {ID} PRIMARY KEY, sid {T} UNIQUE NOT NULL, username {T} NOT NULL, display {T} NOT NULL DEFAULT '',
  kind {T} NOT NULL CHECK(kind IN ('sheet','set')), count integer NOT NULL CHECK(count BETWEEN 1 AND 200), ai boolean NOT NULL,
  bytes integer NOT NULL, sha {T} NOT NULL, created double precision NOT NULL, updated double precision NOT NULL,
  version integer NOT NULL DEFAULT 1, life_day bigint NOT NULL DEFAULT 0, ip_tag {T} NOT NULL DEFAULT '',
  status {T} NOT NULL DEFAULT 'live', rank smallint CHECK(rank BETWEEN 1 AND 10), reviewed_at double precision,
  by_admin {T}, note {T} NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS sticker_packs_rank ON sticker_packs(rank) WHERE rank IS NOT NULL;
CREATE TABLE IF NOT EXISTS sticker_pack_images (
  pack bigint NOT NULL, idx smallint NOT NULL, mime {T} NOT NULL CHECK(mime IN ('image/png','image/webp')),
  width integer NOT NULL, height integer NOT NULL, byte_size integer NOT NULL CHECK(byte_size BETWEEN 1 AND 3145728),
  data bytea NOT NULL, thumb bytea NOT NULL, sha {T} NOT NULL, PRIMARY KEY (pack, idx), CHECK(octet_length(data)=byte_size)
);
-- 🏗️ Công trình của phố (game/town_projects.py; SCHEMA_VERSION 52, owner 16/10): town_projects, one row per project
-- of the catalogue once it opened (game/town_projects_content.py id), locked FOR UPDATE by every contribution: status
-- funding -> building (the goal reached: ready_at = funded_at + 48 h) -> done, each move guarded by its status;
-- openings and completions under pg_advisory_xact_lock(17852, 1). town_gifts, one row per contribution written in the
-- save's own transaction (id '<pid>:<n>', idempotent); a player who erases their data stays as anonymous (sid '').
-- New tables and indexes only, no FK, no backfill.
CREATE TABLE IF NOT EXISTS town_projects (
  id {T} PRIMARY KEY, seq bigint NOT NULL, goal bigint NOT NULL CHECK(goal > 0), raised bigint NOT NULL DEFAULT 0,
  status {T} NOT NULL DEFAULT 'funding' CHECK(status IN ('funding','building','done')), opened_at double precision NOT NULL,
  funded_at double precision, ready_at double precision, done_at double precision, CHECK(raised BETWEEN 0 AND goal)
);
CREATE TABLE IF NOT EXISTS town_gifts (
  id {T} PRIMARY KEY, sid {T} NOT NULL, project {T} NOT NULL, amount bigint NOT NULL CHECK(amount > 0),
  anon bigint NOT NULL DEFAULT 0, at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS town_gifts_project ON town_gifts(project, sid);
CREATE INDEX IF NOT EXISTS town_gifts_sid ON town_gifts(sid);
-- 🏝️ Đảo riêng (game/island_trips.py, live/island.py; SCHEMA_VERSION 54): a trip to a private island its owner
-- started (status open → ended: the owner, the time, a sale), the vehicle and its seats (the owner included), and who
-- was invited / is aboard. The seats are counted under the trip row's lock. New tables only, no FK, no backfill.
CREATE TABLE IF NOT EXISTS island_trips (
  id {T} PRIMARY KEY, owner {T} NOT NULL, island {T} NOT NULL, vehicle {T} NOT NULL DEFAULT '', kind {T} NOT NULL,
  seats integer NOT NULL CHECK (seats BETWEEN 1 AND 40), status {T} NOT NULL CHECK (status IN ('open','ended')),
  created double precision NOT NULL, ends double precision NOT NULL, ended double precision, why {T} NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS island_guests (
  trip {T} NOT NULL, guest {T} NOT NULL,
  status {T} NOT NULL CHECK (status IN ('invited','aboard','declined','left','removed')),
  invited double precision NOT NULL, answered double precision, PRIMARY KEY (trip, guest)
);
-- 🏗️ Xây trên đảo (game/island_build.py; SCHEMA_VERSION 56, owner 19/10): one row per owner, island and plot, a copy of
-- the save's journey.islb written in the save's own transaction (status 'up' | 'gone' after a phá dỡ or a sale: kept),
-- what visitors, the open-island list and the weekly 🏝️ Đảo đẹp board read. A level stands once ready_at is past.
-- 🌍 island_public: a trip its owner opened to everyone (open | closed); island_visitors: who visits it (in | left |
-- removed), counted under the trip row's lock (game/island_trips.py). New tables and indexes only, no FK, no backfill.
CREATE TABLE IF NOT EXISTS island_builds (
  owner {T} NOT NULL, island {T} NOT NULL, plot integer NOT NULL CHECK (plot BETWEEN 0 AND 63), kind {T} NOT NULL,
  lvl integer NOT NULL DEFAULT 0, next_lvl integer NOT NULL DEFAULT 0, ready_at double precision NOT NULL DEFAULT 0,
  paid bigint NOT NULL DEFAULT 0, status {T} NOT NULL CHECK (status IN ('up','gone')), at double precision NOT NULL,
  PRIMARY KEY (owner, island, plot)
);
CREATE TABLE IF NOT EXISTS island_public (
  trip {T} PRIMARY KEY, owner {T} NOT NULL, island {T} NOT NULL, status {T} NOT NULL CHECK (status IN ('open','closed')),
  opened double precision NOT NULL, closed double precision
);
CREATE TABLE IF NOT EXISTS island_visitors (
  trip {T} NOT NULL, guest {T} NOT NULL, status {T} NOT NULL CHECK (status IN ('in','left','removed')),
  at double precision NOT NULL, PRIMARY KEY (trip, guest)
);
-- 🧧 Lì xì (game/lixi.py, live/lixi.py; SCHEMA_VERSION 51, owner 16/10 "cho phép người ta phát lì xì và giật lì xì"):
-- one row per packet a player gave, written in the giver's own save transaction (jr_lixi_give: the debit and this row,
-- both or neither), locked FOR UPDATE by every grab and by the 24 h sweep (`seq` moves on every change). left_n/left_xu:
-- what is still in it; status open | done | expired | gone (the giver erased their data); `back` the xu returned to the
-- giver (live_effects 'lixi:<id>:back'); `raw` a custom line before the chat mask, for admins only. New tables only.
CREATE TABLE IF NOT EXISTS lixi_packets (
  id {T} PRIMARY KEY, sid {T} NOT NULL, pid {T} NOT NULL, name {T} NOT NULL DEFAULT '', total bigint NOT NULL CHECK(total > 0),
  n integer NOT NULL CHECK(n BETWEEN 1 AND 100), left_n integer NOT NULL CHECK(left_n >= 0), left_xu bigint NOT NULL CHECK(left_xu >= 0),
  wish {T} NOT NULL DEFAULT '', text {T} NOT NULL DEFAULT '', raw {T} NOT NULL DEFAULT '', status {T} NOT NULL DEFAULT 'open',
  day {T} NOT NULL, at double precision NOT NULL, expires double precision NOT NULL, done_at double precision,
  back bigint NOT NULL DEFAULT 0, seq bigint NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS lixi_packets_sid ON lixi_packets(sid, at);
CREATE INDEX IF NOT EXISTS lixi_packets_due ON lixi_packets(status, expires);
CREATE INDEX IF NOT EXISTS lixi_packets_at ON lixi_packets(at);
-- One row per envelope taken (one per player per packet), its amount drawn under the packet's lock and paid into the
-- grabber's save through the live_effects row 'lixi:<packet>:<pid>' (game/live_effects.py: once). `day` the Vietnam day
-- (the grabber's caps), `giver` the packet's sid (one giver's packets a day), `ip` a keyed hash (one per address).
CREATE TABLE IF NOT EXISTS lixi_grabs (
  packet {T} NOT NULL, sid {T} NOT NULL, pid {T} NOT NULL, name {T} NOT NULL DEFAULT '', giver {T} NOT NULL DEFAULT '',
  amount bigint NOT NULL CHECK(amount > 0), day {T} NOT NULL, ip {T} NOT NULL DEFAULT '', at double precision NOT NULL,
  PRIMARY KEY(packet, sid)
);
CREATE INDEX IF NOT EXISTS lixi_grabs_day ON lixi_grabs(sid, day);
CREATE INDEX IF NOT EXISTS lixi_grabs_ip ON lixi_grabs(packet, ip) WHERE ip <> '';
-- ⚔️ Bang (game/bang.py, live/bangs.py; SCHEMA_VERSION 57, owner 19/10): player guilds. New tables and indexes only, no
-- FK, no backfill, nothing in any save but the optional journey['bang'] counter of the two paid commands: older releases
-- never read these tables. Nothing is ever deleted: a member who leaves keeps a row with status 'out' (points and items
-- stay with that bang), a disbanded bang keeps its row (status 'disbanded', its fund burned into `burned`), the fund's
-- ledger only grows. Lock order everywhere: the save row (sessions, when a command pays), then bangs rows in id order,
-- then bang_members rows. `seq` moves on every change a cache must see (name tags, the page).
-- Rows a later Đảo bang reuses: anything keyed by `bang` (facilities have a free `place` for an island map).
CREATE TABLE IF NOT EXISTS bangs (
  id {T} PRIMARY KEY, name {T} NOT NULL, key {T} NOT NULL, emoji {T} NOT NULL, color {T} NOT NULL, motto {T} NOT NULL DEFAULT '',
  open bigint NOT NULL DEFAULT 1, leader {T} NOT NULL, status {T} NOT NULL DEFAULT 'active' CHECK(status IN ('active','disbanded')),
  hidden bigint NOT NULL DEFAULT 0, fund bigint NOT NULL DEFAULT 0 CHECK(fund >= 0), given bigint NOT NULL DEFAULT 0,
  spent bigint NOT NULL DEFAULT 0, burned bigint NOT NULL DEFAULT 0, channel {T} NOT NULL DEFAULT '',
  created double precision NOT NULL, created_by {T} NOT NULL, ended double precision, seq bigint NOT NULL DEFAULT 0,
  phao_at double precision NOT NULL DEFAULT 0, admin_note {T} NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS bangs_key ON bangs(key) WHERE status='active';
-- SCHEMA_VERSION 60 (owner 20/10): the join rules (JSON: mode closed | ask | auto, career, rank, any, days) (game/bang.py
-- rules_of; `open` stays in step: 1 for auto, 0 otherwise, as the code before 60 read it). An empty object: the mode from `open`.
ALTER TABLE bangs ADD COLUMN IF NOT EXISTS rules {T} NOT NULL DEFAULT '{{}}';
-- SCHEMA_VERSION 62 (owner 21/10 "đảo bang bắt phải mua nhé … sau mở rộng lên được"): the bang's island (game/bang.py
-- island_of; numbers in game/bang_content.py ISLE_*). isle: the level held (0: not bought; 1…5); while an upgrade is being
-- built, isle_to = isle + 1 until isle_ready (epoch s), started at isle_started; isle_paid: xu the fund paid for it in all;
-- isle_how: 'grant' (held from before this release: the default, so a bang written without these columns, by 2.4.64 or
-- older, counts as granted), 'buy' (bought), '' (founded since, not bought yet). Paid only from the fund (bang_fund kind
-- 'build', id 'i:<bang>:<level>'). Constant defaults: no table rewrite, no backfill.
ALTER TABLE bangs ADD COLUMN IF NOT EXISTS isle integer NOT NULL DEFAULT 1;
ALTER TABLE bangs ADD COLUMN IF NOT EXISTS isle_to integer;
ALTER TABLE bangs ADD COLUMN IF NOT EXISTS isle_started double precision;
ALTER TABLE bangs ADD COLUMN IF NOT EXISTS isle_ready double precision;
ALTER TABLE bangs ADD COLUMN IF NOT EXISTS isle_paid bigint NOT NULL DEFAULT 0;
ALTER TABLE bangs ADD COLUMN IF NOT EXISTS isle_how {T} NOT NULL DEFAULT 'grant';
-- One row per (bang, player) ever: status 'in' (one bang at a time: bangs_one) or 'out'. points: điểm cống hiến to spend;
-- earned: all ever earned here; given: xu given here; act_day/act_pts/work_n: today's activity points (the daily cap);
-- wear: bang items worn (1 uniform, 2 badge, 4 flag at home, 8 boat paint), uniform: its style.
CREATE TABLE IF NOT EXISTS bang_members (
  bang {T} NOT NULL, sid {T} NOT NULL, pid {T} NOT NULL, status {T} NOT NULL CHECK(status IN ('in','out')),
  role {T} NOT NULL DEFAULT 'tv', joined double precision NOT NULL, left_at double precision, why {T} NOT NULL DEFAULT '',
  points bigint NOT NULL DEFAULT 0 CHECK(points >= 0), earned bigint NOT NULL DEFAULT 0, given bigint NOT NULL DEFAULT 0,
  act_day {T} NOT NULL DEFAULT '', act_pts bigint NOT NULL DEFAULT 0, work_n bigint NOT NULL DEFAULT 0,
  checkin_day {T} NOT NULL DEFAULT '', wear bigint NOT NULL DEFAULT 0, uniform {T} NOT NULL DEFAULT 'polo',
  PRIMARY KEY (bang, sid)
);
CREATE UNIQUE INDEX IF NOT EXISTS bang_members_one ON bang_members(sid) WHERE status='in';
CREATE INDEX IF NOT EXISTS bang_members_pid ON bang_members(pid) WHERE status='in';
CREATE INDEX IF NOT EXISTS bang_members_in ON bang_members(bang) WHERE status='in';
-- Every membership's time span (the bang's Giờ vàng counts for a window that started while the player was in).
CREATE TABLE IF NOT EXISTS bang_stints (
  id {ID} PRIMARY KEY, bang {T} NOT NULL, sid {T} NOT NULL, joined double precision NOT NULL, left_at double precision,
  why {T} NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS bang_stints_sid ON bang_stints(sid, joined);
CREATE INDEX IF NOT EXISTS bang_stints_bang ON bang_stints(bang) WHERE left_at IS NULL;
-- A player asking to join (kind 'ask') or invited by an officer (kind 'invite'); answered rows stay.
CREATE TABLE IF NOT EXISTS bang_asks (
  bang {T} NOT NULL, sid {T} NOT NULL, kind {T} NOT NULL CHECK(kind IN ('ask','invite')), by_sid {T} NOT NULL,
  status {T} NOT NULL CHECK(status IN ('open','done','declined','cancelled')), at double precision NOT NULL,
  answered double precision, PRIMARY KEY (bang, sid, kind)
);
CREATE INDEX IF NOT EXISTS bang_asks_sid ON bang_asks(sid) WHERE status='open';
CREATE INDEX IF NOT EXISTS bang_asks_bang ON bang_asks(bang) WHERE status='open';
-- 💰 Quỹ bang's ledger: 'give' (+, a member's deposit written in their save's own transaction, id 'g:<pid>:<nonce>'),
-- 'build' (−, a facility), 'burn' (−, the fund of a disbanded bang). There is no other kind: no withdrawal exists.
CREATE TABLE IF NOT EXISTS bang_fund (
  id {T} PRIMARY KEY, bang {T} NOT NULL, sid {T} NOT NULL, kind {T} NOT NULL CHECK(kind IN ('give','build','burn')),
  amount bigint NOT NULL, balance bigint NOT NULL CHECK(balance >= 0), note {T} NOT NULL DEFAULT '', at double precision NOT NULL,
  CHECK((kind='give' AND amount > 0) OR (kind<>'give' AND amount <= 0))
);
CREATE INDEX IF NOT EXISTS bang_fund_bang ON bang_fund(bang, at);
-- ⭐ Điểm cống hiến's ledger (unique ids: idempotent). week: the Vietnam ISO week (Bang mạnh nhất tuần), day: its day.
CREATE TABLE IF NOT EXISTS bang_points (
  id {T} PRIMARY KEY, bang {T} NOT NULL, sid {T} NOT NULL, kind {T} NOT NULL, pts bigint NOT NULL, week {T} NOT NULL,
  day {T} NOT NULL, at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS bang_points_week ON bang_points(week, bang);
CREATE INDEX IF NOT EXISTS bang_points_sid ON bang_points(sid, bang);
-- 🏗️ Công trình bang: one row per (bang, facility) once built or building (target/ready_at while building).
CREATE TABLE IF NOT EXISTS bang_facilities (
  bang {T} NOT NULL, fac {T} NOT NULL, level integer NOT NULL DEFAULT 0, target integer, started double precision,
  ready_at double precision, paid bigint NOT NULL DEFAULT 0, place {T} NOT NULL DEFAULT '', PRIMARY KEY (bang, fac)
);
-- 🛍️ Bang items a member bought with points: kept after leaving, usable only while in that bang (n: fireworks held).
CREATE TABLE IF NOT EXISTS bang_items (
  bang {T} NOT NULL, sid {T} NOT NULL, item {T} NOT NULL, n integer NOT NULL DEFAULT 1 CHECK(n >= 0), at double precision NOT NULL,
  PRIMARY KEY (bang, sid, item)
);
CREATE INDEX IF NOT EXISTS bang_items_sid ON bang_items(sid);
-- ⏰ Giờ vàng của bang: windows the leader set ahead (never moved once started; cancelled ones stay).
CREATE TABLE IF NOT EXISTS bang_gh (
  id {ID} PRIMARY KEY, bang {T} NOT NULL, start double precision NOT NULL, ends double precision NOT NULL, by_sid {T} NOT NULL,
  status {T} NOT NULL CHECK(status IN ('set','cancelled')), at double precision NOT NULL, CHECK(ends > start)
);
CREATE INDEX IF NOT EXISTS bang_gh_bang ON bang_gh(bang, start);
CREATE INDEX IF NOT EXISTS bang_gh_ends ON bang_gh(ends) WHERE status='set';
-- 📜 What happened in a bang (joins, roles, builds, admin renames…), for its page and the operator.
CREATE TABLE IF NOT EXISTS bang_log (
  id {ID} PRIMARY KEY, bang {T} NOT NULL, sid {T} NOT NULL DEFAULT '', kind {T} NOT NULL, text {T} NOT NULL,
  at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS bang_log_bang ON bang_log(bang, id);
-- 👑 Bang mạnh nhất tuần: the week's winner, frozen once after the week ended (its members wear the title the next week).
CREATE TABLE IF NOT EXISTS bang_week_win (
  week {T} PRIMARY KEY, bang {T} NOT NULL, score bigint NOT NULL, at double precision NOT NULL
);
-- ⚔️ Đấu trường pet (game/pet_arena.py, game/pet_battle.py; SCHEMA_VERSION 58, owner 19/10 "thêm thi đua nữa nhé, kết hợp
-- với pet ra tranh đấu với bang nữa"). pet_arena: one row per player who set a lineup: the pets' battle snapshot (fighters,
-- refreshed by every jr_pet_* command in the save's own transaction), the Elo rating, `ip` a keyed hash of the last
-- address (never two players of one network in a ranked match), `npc` today's practice (thử thách) progress. Nothing of
-- this is in a save: a battle never touches a pet. New tables and indexes only, no FK, no backfill: older releases never
-- read them.
CREATE TABLE IF NOT EXISTS pet_arena (
  sid {T} PRIMARY KEY, pid {T} NOT NULL, name {T} NOT NULL DEFAULT '', lineup {T} NOT NULL DEFAULT '[]',
  snap {T} NOT NULL DEFAULT '[]', size integer NOT NULL DEFAULT 0, pw integer NOT NULL DEFAULT 0,
  rating integer NOT NULL DEFAULT 1000, best integer NOT NULL DEFAULT 1000, games integer NOT NULL DEFAULT 0,
  wins integer NOT NULL DEFAULT 0, ip {T} NOT NULL DEFAULT '', npc {T} NOT NULL DEFAULT '{{}}',
  at double precision NOT NULL, last double precision NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS pet_arena_rating ON pet_arena(rating);
CREATE INDEX IF NOT EXISTS pet_arena_pid ON pet_arena(pid);
-- The weekly season (Vietnam ISO week): each player's rating and record of ranked battles that week (`opp` distinct
-- opponents, `stars` practice wins): the ladder and its titles (game/lb_titles.py board 'arena').
CREATE TABLE IF NOT EXISTS pet_arena_season (
  week {T} NOT NULL, sid {T} NOT NULL, rating integer NOT NULL, w integer NOT NULL DEFAULT 0, l integer NOT NULL DEFAULT 0,
  d integer NOT NULL DEFAULT 0, opp integer NOT NULL DEFAULT 0, stars integer NOT NULL DEFAULT 0, at double precision NOT NULL,
  PRIMARY KEY (week, sid)
);
CREATE INDEX IF NOT EXISTS pet_arena_season_top ON pet_arena_season(week, rating);
-- One row per battle (kind rank | friend | npc | spar | cup): both lineups' snapshots and the engine version in `data`,
-- the seed is the id (a replay is the same fight), the rating moves (ra/rb before, da/db the change), `rd` a cup round.
CREATE TABLE IF NOT EXISTS pet_arena_matches (
  id {T} PRIMARY KEY, kind {T} NOT NULL, day {T} NOT NULL, week {T} NOT NULL, a {T} NOT NULL, b {T} NOT NULL DEFAULT '',
  a_name {T} NOT NULL DEFAULT '', b_name {T} NOT NULL DEFAULT '', win integer NOT NULL, ra integer NOT NULL DEFAULT 0,
  rb integer NOT NULL DEFAULT 0, da integer NOT NULL DEFAULT 0, db integer NOT NULL DEFAULT 0, rd integer NOT NULL DEFAULT 0,
  engine integer NOT NULL, data {T} NOT NULL, at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS pet_arena_matches_a ON pet_arena_matches(a, at);
CREATE INDEX IF NOT EXISTS pet_arena_matches_b ON pet_arena_matches(b, at) WHERE b <> '';
CREATE INDEX IF NOT EXISTS pet_arena_matches_day ON pet_arena_matches(a, day, kind);
CREATE INDEX IF NOT EXISTS pet_arena_matches_cup ON pet_arena_matches(week, kind, rd) WHERE kind = 'cup';
-- 🏟️ Giải đấu pet tuần (game/pet_cup.py): sign up during the week, a Swiss tournament on the lineups' snapshots at the
-- close; `score` ×2 (a win 2, a draw 1), `tb` Buchholz, `rank` the final place.
CREATE TABLE IF NOT EXISTS pet_cup (
  week {T} PRIMARY KEY, status {T} NOT NULL CHECK (status IN ('done','cancelled')), n integer NOT NULL DEFAULT 0,
  rounds integer NOT NULL DEFAULT 0, at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS pet_cup_entries (
  week {T} NOT NULL, sid {T} NOT NULL, name {T} NOT NULL DEFAULT '', rating integer NOT NULL DEFAULT 1000,
  snap {T} NOT NULL DEFAULT '[]', score integer NOT NULL DEFAULT 0, tb integer NOT NULL DEFAULT 0, rank integer NOT NULL DEFAULT 0,
  at double precision NOT NULL, PRIMARY KEY (week, sid)
);
CREATE INDEX IF NOT EXISTS pet_cup_entries_rank ON pet_cup_entries(week, rank);
-- 🛡️ Bang chiến pet (game/pet_war.py, owner 19/10 "mỗi bang đến giờ sẽ chọn các pet ra đánh với nhau, đánh 5v5 và ngẫu
-- nhiên … ai thắng nhiều thì vào vòng trong"): teams are (team_kind, team_id), a bang is kind 'bang' (its own tables
-- live elsewhere). pet_war: one row per weekly war once its lineups lock (the bracket in `data`); pet_war_picks: the one
-- pet each member fields; pet_war_matches: every team match (5 duels in `data`); pet_team_ladder: the week's standing
-- of each team; pet_team_rating: a team's rating across weeks.
CREATE TABLE IF NOT EXISTS pet_war (
  week {T} PRIMARY KEY, status {T} NOT NULL CHECK (status IN ('done','cancelled')), start double precision NOT NULL,
  n integer NOT NULL DEFAULT 0, rounds integer NOT NULL DEFAULT 0, champ_kind {T} NOT NULL DEFAULT '',
  champ_id {T} NOT NULL DEFAULT '', champ_name {T} NOT NULL DEFAULT '', data {T} NOT NULL DEFAULT '{{}}',
  at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS pet_war_picks (
  week {T} NOT NULL, sid {T} NOT NULL, team_kind {T} NOT NULL, team_id {T} NOT NULL, name {T} NOT NULL DEFAULT '',
  pet {T} NOT NULL, snap {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY (week, sid)
);
CREATE INDEX IF NOT EXISTS pet_war_picks_team ON pet_war_picks(week, team_kind, team_id, at);
CREATE TABLE IF NOT EXISTS pet_war_matches (
  week {T} NOT NULL, rd integer NOT NULL, slot integer NOT NULL, a_kind {T} NOT NULL, a_id {T} NOT NULL,
  a_name {T} NOT NULL DEFAULT '', b_kind {T} NOT NULL DEFAULT '', b_id {T} NOT NULL DEFAULT '', b_name {T} NOT NULL DEFAULT '',
  win integer NOT NULL, wa integer NOT NULL DEFAULT 0, wb integer NOT NULL DEFAULT 0, start double precision NOT NULL,
  data {T} NOT NULL DEFAULT '{{}}', PRIMARY KEY (week, rd, slot)
);
CREATE TABLE IF NOT EXISTS pet_team_ladder (
  week {T} NOT NULL, team_kind {T} NOT NULL, team_id {T} NOT NULL, name {T} NOT NULL DEFAULT '',
  rating integer NOT NULL DEFAULT 1000, w integer NOT NULL DEFAULT 0, l integer NOT NULL DEFAULT 0,
  best integer NOT NULL DEFAULT 0, pts integer NOT NULL DEFAULT 0, champ integer NOT NULL DEFAULT 0,
  at double precision NOT NULL, PRIMARY KEY (week, team_kind, team_id)
);
CREATE TABLE IF NOT EXISTS pet_team_rating (
  team_kind {T} NOT NULL, team_id {T} NOT NULL, name {T} NOT NULL DEFAULT '', rating integer NOT NULL DEFAULT 1000,
  wars integer NOT NULL DEFAULT 0, titles integer NOT NULL DEFAULT 0, at double precision NOT NULL,
  PRIMARY KEY (team_kind, team_id)
);
-- 🗄️ SCHEMA_VERSION 59 (review fixes 19/10): nothing is ever dropped. Rows past their keep move here as they were, with
-- `archived_at` (game/bang.py run_housekeeping, game/pet_arena.py archive_matches: small batches, off the peak hours,
-- one transaction a batch: copied then removed, so a row is always in exactly one of the two). Never read by a page but
-- a replay of an old match (pet_arena replay falls back to pet_arena_matches_old). Column order = the source's + archived_at.
CREATE TABLE IF NOT EXISTS bang_log_old (
  id bigint PRIMARY KEY, bang {T} NOT NULL, sid {T} NOT NULL DEFAULT '', kind {T} NOT NULL, text {T} NOT NULL,
  at double precision NOT NULL, archived_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS bang_points_old (
  id {T} PRIMARY KEY, bang {T} NOT NULL, sid {T} NOT NULL, kind {T} NOT NULL, pts bigint NOT NULL, week {T} NOT NULL,
  day {T} NOT NULL, at double precision NOT NULL, archived_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS bang_stints_old (
  id bigint PRIMARY KEY, bang {T} NOT NULL, sid {T} NOT NULL, joined double precision NOT NULL, left_at double precision,
  why {T} NOT NULL DEFAULT '', archived_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS pet_arena_matches_old (
  id {T} PRIMARY KEY, kind {T} NOT NULL, day {T} NOT NULL, week {T} NOT NULL, a {T} NOT NULL, b {T} NOT NULL DEFAULT '',
  a_name {T} NOT NULL DEFAULT '', b_name {T} NOT NULL DEFAULT '', win integer NOT NULL, ra integer NOT NULL DEFAULT 0,
  rb integer NOT NULL DEFAULT 0, da integer NOT NULL DEFAULT 0, db integer NOT NULL DEFAULT 0, rd integer NOT NULL DEFAULT 0,
  engine integer NOT NULL, data {T} NOT NULL, at double precision NOT NULL, archived_at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS bang_stints_bang_joined ON bang_stints(bang, joined);
CREATE INDEX IF NOT EXISTS bang_stints_left ON bang_stints(left_at) WHERE left_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS bang_log_at ON bang_log(at);
CREATE INDEX IF NOT EXISTS bang_points_at ON bang_points(at);
CREATE INDEX IF NOT EXISTS pet_arena_matches_at ON pet_arena_matches(at);
-- ⚔️ Thách đấu bang (game/bang_challenge.py; SCHEMA_VERSION 61, owner 21/10 "đấu trường pets chỉ mở cho các bang hội đánh
-- nhau thôi, thêm hoạt động đó vào cho các bang hội nhé"): bang against bang, 5 vs 5, any day. New tables and indexes only,
-- no FK, no backfill, no save key: 2.4.64 and older never read them. Nothing of a save: a match never touches a pet.
-- bang_chal_roster: the bang's standing roster, one pet a member (`pos`: the order its officers set; the first five ready
-- entries start), the pet's battle snapshot refreshed by every jr_pet_* command (`ok` 0: the pet is no longer at home or in
-- the kennel), `pw` its power. A leaver's row stays, unused (only members still in the bang count).
CREATE TABLE IF NOT EXISTS bang_chal_roster (
  bang {T} NOT NULL, sid {T} NOT NULL, pid {T} NOT NULL, name {T} NOT NULL DEFAULT '', pet {T} NOT NULL, snap {T} NOT NULL,
  pw integer NOT NULL DEFAULT 0, ok integer NOT NULL DEFAULT 1, pos integer NOT NULL DEFAULT 0, at double precision NOT NULL,
  PRIMARY KEY (bang, sid)
);
CREATE INDEX IF NOT EXISTS bang_chal_roster_sid ON bang_chal_roster(sid);
-- bang_chal_team: a bang's challenge Elo and record (separate from the weekly war's pet_team_rating: its seeding is
-- unchanged) and how it takes challenges (mode ask | auto | off).
CREATE TABLE IF NOT EXISTS bang_chal_team (
  bang {T} PRIMARY KEY, rating integer NOT NULL DEFAULT 1000, w integer NOT NULL DEFAULT 0, l integer NOT NULL DEFAULT 0,
  d integer NOT NULL DEFAULT 0, mode {T} NOT NULL DEFAULT 'ask', at double precision NOT NULL
);
-- bang_chal: one row per challenge (a challenges b, `rid` the sender's request id: a retry finds its row), open until
-- answered, cancelled or `expires`; a played one (status done, exactly once under its row lock) holds the five duels with
-- both snapshots in `data` (the seed is the id: a replay is the same fight), the Elo before (ra, rb) and its change
-- (da, db), the 🛡️ Bang chiến points of the week's ranking it gave each side (sa, sb), `week` / `done_day` of the match.
CREATE TABLE IF NOT EXISTS bang_chal (
  id {T} PRIMARY KEY, a {T} NOT NULL, b {T} NOT NULL, a_name {T} NOT NULL DEFAULT '', b_name {T} NOT NULL DEFAULT '',
  by_sid {T} NOT NULL DEFAULT '', rid {T} NOT NULL,
  status {T} NOT NULL CHECK (status IN ('open','done','declined','cancelled','expired')), day {T} NOT NULL,
  at double precision NOT NULL, expires double precision NOT NULL, answered double precision, ans_sid {T} NOT NULL DEFAULT '',
  auto integer NOT NULL DEFAULT 0, win integer NOT NULL DEFAULT -1, wa integer NOT NULL DEFAULT 0, wb integer NOT NULL DEFAULT 0,
  ra integer NOT NULL DEFAULT 0, rb integer NOT NULL DEFAULT 0, da integer NOT NULL DEFAULT 0, db integer NOT NULL DEFAULT 0,
  sa integer NOT NULL DEFAULT 0, sb integer NOT NULL DEFAULT 0, week {T} NOT NULL DEFAULT '', done_day {T} NOT NULL DEFAULT '',
  engine integer NOT NULL DEFAULT 0, data {T} NOT NULL DEFAULT '{{}}', CHECK (a <> b)
);
CREATE UNIQUE INDEX IF NOT EXISTS bang_chal_rid ON bang_chal(a, rid);
CREATE UNIQUE INDEX IF NOT EXISTS bang_chal_pair_open ON bang_chal(a, b) WHERE status='open';
CREATE INDEX IF NOT EXISTS bang_chal_a ON bang_chal(a, at);
CREATE INDEX IF NOT EXISTS bang_chal_b ON bang_chal(b, at);
CREATE INDEX IF NOT EXISTS bang_chal_open ON bang_chal(expires) WHERE status='open';
CREATE INDEX IF NOT EXISTS bang_chal_week ON bang_chal(week) WHERE status='done';
CREATE INDEX IF NOT EXISTS bang_chal_done ON bang_chal(answered) WHERE status='done';
-- 💪 pet_power (SCHEMA_VERSION 61, owner 21/10 "top bang thì bằng cách cống hiến và tính điểm chiến lực bằng pets"): each
-- player's strongest pet power (pet_tiers.power of the best pet at home or in the kennel), refreshed by every jr_pet_*
-- command in the save's own transaction and by an arena visit (game/pet_arena.py power_commit; written only when it
-- changes). The bang ranking's 🛡️ Bang chiến pillar counts the Chiến lực: it sums it over a bang's current members (game/bang.py standings): never a save
-- parsed per request. A player who erased their data: their row goes.
CREATE TABLE IF NOT EXISTS pet_power (
  sid {T} PRIMARY KEY, pw integer NOT NULL DEFAULT 0, at double precision NOT NULL
);
-- 🛎️ Phố dịch vụ (game/service_market.py; SCHEMA_VERSION 63, owner 21/10 "players serve players across careers"). A
-- provider's offer of one registered service (career, service): on/off, mode 'fixed' (unit price = NPC base × mult, 1–10)
-- or 'nego' (the buyer offers, the provider answers), `price` the last unit price shown (the directory's sort), `note`
-- one short line. No row: a legacy workplace order keeps ×3 at its place; a registered service is simply not offered.
CREATE TABLE IF NOT EXISTS svc_settings (
  provider {T} NOT NULL, pid {T} NOT NULL DEFAULT '', career {T} NOT NULL, service {T} NOT NULL, on_ integer NOT NULL DEFAULT 0,
  mode {T} NOT NULL DEFAULT 'fixed', mult integer NOT NULL DEFAULT 3, price bigint NOT NULL DEFAULT 0,
  note {T} NOT NULL DEFAULT '', updated_at double precision NOT NULL, PRIMARY KEY(provider, career, service)
);
CREATE INDEX IF NOT EXISTS svc_settings_on ON svc_settings(career, service) WHERE on_=1;
CREATE INDEX IF NOT EXISTS svc_settings_pid ON svc_settings(pid);
-- One talk or order between a buyer and a provider. kind 'svc': the escrow is held here (price, then fee + paid at
-- done); kind 'wo': a talk about a legacy workplace order, `link` the work_service_orders row made at agreement (its
-- own escrow). status: talk (no money) → held (paid, waiting for the provider) → working → delivered (buyer confirms,
-- or auto after 24 h) | ready (a career's proof) → done (provider paid, fee burned); refunded (money back in full);
-- declined / cancelled / expired (a talk, nothing paid); linked (a 'wo' talk agreed). ask/ask_by/rounds: the price on
-- the table while talking.
CREATE TABLE IF NOT EXISTS svc_orders (
  id {T} PRIMARY KEY, buyer {T} NOT NULL, provider {T} NOT NULL, career {T} NOT NULL, service {T} NOT NULL,
  kind {T} NOT NULL DEFAULT 'svc', status {T} NOT NULL, qty integer NOT NULL DEFAULT 1,
  price bigint NOT NULL DEFAULT 0 CHECK(price >= 0), ask bigint NOT NULL DEFAULT 0, ask_by {T} NOT NULL DEFAULT '',
  rounds integer NOT NULL DEFAULT 0, base bigint NOT NULL DEFAULT 0, mult integer NOT NULL DEFAULT 0,
  fee bigint NOT NULL DEFAULT 0, paid bigint NOT NULL DEFAULT 0, link {T} NOT NULL DEFAULT '',
  request_id {T} NOT NULL, fingerprint {T} NOT NULL, data {T} NOT NULL DEFAULT '{{}}',
  created_at double precision NOT NULL, updated_at double precision NOT NULL, due_at double precision,
  held_at double precision, delivered_at double precision, done_at double precision,
  UNIQUE(buyer, request_id)
);
CREATE INDEX IF NOT EXISTS svc_orders_provider ON svc_orders(provider, status, created_at);
CREATE INDEX IF NOT EXISTS svc_orders_buyer ON svc_orders(buyer, created_at);
CREATE INDEX IF NOT EXISTS svc_orders_due ON svc_orders(due_at) WHERE status IN ('talk','held','working','delivered','ready');
CREATE INDEX IF NOT EXISTS svc_orders_pair ON svc_orders(buyer, provider, created_at);
-- ⭐ One rating per completed order (svc_orders, or a legacy order: src 'wo', its own review stays in
-- work_service_reviews). `counted`: it moved the provider's reputation (one counted rating per buyer and provider a week).
CREATE TABLE IF NOT EXISTS svc_reviews (
  order_id {T} PRIMARY KEY, src {T} NOT NULL DEFAULT 'svc', provider {T} NOT NULL, buyer {T} NOT NULL,
  stars integer NOT NULL CHECK(stars BETWEEN 1 AND 5), comment {T} NOT NULL DEFAULT '', reply {T} NOT NULL DEFAULT '',
  counted integer NOT NULL DEFAULT 1, created_at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS svc_reviews_provider ON svc_reviews(provider, created_at);
CREATE INDEX IF NOT EXISTS svc_reviews_pair ON svc_reviews(provider, buyer, created_at);
-- A provider's reputation: counted ratings (n, stars), completed deals and their xu (both kinds of orders).
CREATE TABLE IF NOT EXISTS svc_rep (
  provider {T} PRIMARY KEY, n bigint NOT NULL DEFAULT 0, stars bigint NOT NULL DEFAULT 0,
  deals bigint NOT NULL DEFAULT 0, xu bigint NOT NULL DEFAULT 0, updated_at double precision NOT NULL
);
-- 🚩 A buyer's report on an order (within FLAG_HOURS of its delivery): the admin reads and closes it; nothing automatic.
CREATE TABLE IF NOT EXISTS svc_flags (
  order_id {T} PRIMARY KEY, src {T} NOT NULL DEFAULT 'svc', buyer {T} NOT NULL, provider {T} NOT NULL,
  text {T} NOT NULL, status {T} NOT NULL DEFAULT 'open', note {T} NOT NULL DEFAULT '', by_admin {T} NOT NULL DEFAULT '',
  created_at double precision NOT NULL, closed_at double precision
);
CREATE INDEX IF NOT EXISTS svc_flags_open ON svc_flags(status, created_at);
-- Keyed network tags (game/lixi.py ip_tag: a hash, never the address) of the market's users: buyer and provider of one
-- network never trade (spouses excepted).
CREATE TABLE IF NOT EXISTS svc_net (
  sid {T} NOT NULL, tag {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY(sid, tag)
);
-- The 5 % burned on a legacy workplace order paid through this build (0: paid in full by an older one).
ALTER TABLE work_service_orders ADD COLUMN IF NOT EXISTS fee bigint NOT NULL DEFAULT 0;
-- 🏥 Phòng sinh & nhận nuôi (game/birth.py; SCHEMA_VERSION 65, owner 21/10 "sinh con … phải mất tiền ra, đặt tiền tối thiểu"):
-- birth_rooms: the birth room a player offers (a homestay owner; one per save), its price (≥ the floor, checked in
-- game/birth.py), open or closed, and its ratings. birth_stays: one row per booking or adoption of a couple; the price
-- paid is held by the row (escrow) until the baby is born (a player room: 5 % burned, the rest to the provider as a
-- pending marriage_effects row) or refunded on a cancel before check-in. At most one open row per couple.
CREATE TABLE IF NOT EXISTS birth_rooms (
  id {ID} PRIMARY KEY, sid {T} NOT NULL UNIQUE, career {T} NOT NULL, name {T} NOT NULL, price bigint NOT NULL,
  open boolean NOT NULL DEFAULT true, stars bigint NOT NULL DEFAULT 0, rated bigint NOT NULL DEFAULT 0,
  born bigint NOT NULL DEFAULT 0, at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS birth_stays (
  id {ID} PRIMARY KEY, couple bigint NOT NULL, kind {T} NOT NULL, status {T} NOT NULL,
  from_sid {T} NOT NULL, to_sid {T} NOT NULL, payer {T} NOT NULL, name {T} NOT NULL,
  provider {T} NOT NULL, room bigint, provider_sid {T}, price bigint NOT NULL, burn bigint NOT NULL DEFAULT 0,
  nurse {T}, nurse_ok boolean NOT NULL DEFAULT true, starts double precision, ends double precision,
  data {T} NOT NULL DEFAULT '{{}}', rating integer, at double precision NOT NULL, done double precision
);
CREATE UNIQUE INDEX IF NOT EXISTS birth_stays_open ON birth_stays(couple) WHERE status IN ('proposed','booked','staying');
CREATE INDEX IF NOT EXISTS birth_stays_room ON birth_stays(room, status) WHERE status IN ('booked','staying');
CREATE INDEX IF NOT EXISTS birth_stays_to ON birth_stays(to_sid) WHERE status='proposed';
CREATE INDEX IF NOT EXISTS birth_stays_nurse ON birth_stays(nurse, status) WHERE nurse IS NOT NULL;
CREATE INDEX IF NOT EXISTS birth_stays_calls ON birth_stays(id) WHERE status IN ('booked','staying') AND nurse IS NULL AND nurse_ok;
CREATE INDEX IF NOT EXISTS birth_stays_couple ON birth_stays(couple, status);
CREATE INDEX IF NOT EXISTS birth_rooms_open ON birth_rooms(price, id) WHERE open;
-- 📸 Chụp ảnh cho người chơi (game/photo_studio.py; SCHEMA_VERSION 66, owner 21/10). New tables and indexes only, no FK, no
-- backfill: 2.4.66 and older never read them. photo_studios: a photographer's prices (JSON, package id to xu, kept between the
-- package's floor and cap), open flag, last network tag (a keyed hash, never the address) and record (done, stars).
CREATE TABLE IF NOT EXISTS photo_studios (
  sid {T} PRIMARY KEY, pid {T} NOT NULL, name {T} NOT NULL DEFAULT '', open integer NOT NULL DEFAULT 1, prices {T} NOT NULL DEFAULT '{{}}',
  ip {T} NOT NULL DEFAULT '', done bigint NOT NULL DEFAULT 0, stars bigint NOT NULL DEFAULT 0, at double precision NOT NULL
);
-- photo_orders: one row per order (`rid` the buyer's request id: a retry finds its row). open (the price held: the buyer's
-- save paid it in the same transaction) → shoot (accepted) → done (delivered: `pay` to the photographer, `burn` burned,
-- pay + burn = price), or declined / cancelled / expired (the price back: the buyer's own cancel into their save, the others
-- a live_effects row 'photo:<id>:back', `refund` 1). `snap`: the look snapshot taken at order time; `sess`: the shots.
CREATE TABLE IF NOT EXISTS photo_orders (
  id {T} PRIMARY KEY, rid {T} NOT NULL, buyer {T} NOT NULL, buyer_pid {T} NOT NULL, buyer_name {T} NOT NULL DEFAULT '',
  shooter {T} NOT NULL, shooter_pid {T} NOT NULL, shooter_name {T} NOT NULL DEFAULT '', pkg {T} NOT NULL,
  price bigint NOT NULL, list_price bigint NOT NULL DEFAULT 0, pay bigint NOT NULL DEFAULT 0, burn bigint NOT NULL DEFAULT 0,
  status {T} NOT NULL CHECK (status IN ('open','shoot','done','declined','cancelled','expired')),
  snap {T} NOT NULL, wish {T} NOT NULL DEFAULT '{{}}', sess {T} NOT NULL DEFAULT '{{}}', note {T} NOT NULL DEFAULT '',
  ip {T} NOT NULL DEFAULT '', day {T} NOT NULL, at double precision NOT NULL, until double precision NOT NULL,
  answered double precision, done_at double precision, photo {T} NOT NULL DEFAULT '', refund integer NOT NULL DEFAULT 0,
  via {T} NOT NULL DEFAULT 'direct', CHECK (buyer <> shooter)
);
CREATE UNIQUE INDEX IF NOT EXISTS photo_orders_rid ON photo_orders(buyer, rid);
CREATE INDEX IF NOT EXISTS photo_orders_shooter ON photo_orders(shooter, status, at);
CREATE INDEX IF NOT EXISTS photo_orders_buyer ON photo_orders(buyer, status, at);
CREATE INDEX IF NOT EXISTS photo_orders_day ON photo_orders(day, buyer, shooter);
CREATE INDEX IF NOT EXISTS photo_orders_due ON photo_orders(until) WHERE status IN ('open','shoot');
-- photos: a delivered photo. `data`: the game's own render data (look snapshot, the session's choices, the retouch;
-- ~1-2 KB, drawn by public/js/v4/portrait-art.js: no image bytes, nothing uploaded). The buyer's album: archived 0
-- (the newest 60), 1 the archive ("Xem cũ hơn"), never deleted; `folio` 1: in the photographer's public portfolio.
CREATE TABLE IF NOT EXISTS photos (
  id {T} PRIMARY KEY, order_id {T} NOT NULL DEFAULT '', buyer {T} NOT NULL, buyer_pid {T} NOT NULL, shooter {T} NOT NULL,
  shooter_pid {T} NOT NULL, shooter_name {T} NOT NULL DEFAULT '', pkg {T} NOT NULL, data {T} NOT NULL,
  stars integer NOT NULL DEFAULT 0, at double precision NOT NULL, archived integer NOT NULL DEFAULT 0, folio integer NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS photos_buyer ON photos(buyer, archived, at);
CREATE INDEX IF NOT EXISTS photos_shooter ON photos(shooter, at);
CREATE INDEX IF NOT EXISTS photos_folio ON photos(shooter_pid, at) WHERE folio=1;
-- photo_pfp: a player's profile photo (one of their album; photo '' when cleared), shown on the profile card.
CREATE TABLE IF NOT EXISTS photo_pfp (
  sid {T} PRIMARY KEY, pid {T} NOT NULL, photo {T} NOT NULL DEFAULT '', at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS photo_pfp_pid ON photo_pfp(pid);
-- 🏨 Phòng cho người chơi (game/hotel_stay.py; SCHEMA_VERSION 68, owner 21/10). New tables and indexes only, no FK, no
-- backfill: 2.4.66 and older never read them. The price, its escrow, the 95 % / 5 % and every refund are Phố dịch vụ's
-- (svc_orders, SCHEMA 63); hotel_stays is the stay of one such order (`order_id` = svc_orders.id): booked (the host took
-- it) → arrived → in (a room, `due_at` its end, `late` minutes granted) → out (checked out: `result` is what the market's
-- deliver hook keeps) | gone (refunded or ended by the market). `ev`: the stay's situations (JSON, ≤ ~12 short entries) and
-- the host's choices; `mood` the guest's satisfaction; `open_n` / `next_at` keep the badge one indexed query; `partner`:
-- the spouse of a couple's stay, `partner_rest` 0 none, 1 due, 2 applied (its own exactly-once step).
CREATE TABLE IF NOT EXISTS hotel_stays (
  order_id {T} PRIMARY KEY, host {T} NOT NULL, guest {T} NOT NULL, partner {T} NOT NULL DEFAULT '', career {T} NOT NULL,
  service {T} NOT NULL, qty integer NOT NULL DEFAULT 1, stage {T} NOT NULL CHECK (stage IN ('booked','arrived','in','out','gone')),
  room {T} NOT NULL DEFAULT '', wish {T} NOT NULL DEFAULT '', temper {T} NOT NULL DEFAULT '', booked_at double precision NOT NULL,
  arrived_at double precision, in_at double precision, due_at double precision, out_at double precision,
  mood integer NOT NULL DEFAULT 70, ev {T} NOT NULL DEFAULT '[]', asks integer NOT NULL DEFAULT 0, want_out integer NOT NULL DEFAULT 0,
  late integer NOT NULL DEFAULT 0, open_n integer NOT NULL DEFAULT 0, next_at double precision, partner_rest integer NOT NULL DEFAULT 0,
  result {T} NOT NULL DEFAULT '{{}}', updated_at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS hotel_stays_host ON hotel_stays(host, stage, updated_at);
CREATE INDEX IF NOT EXISTS hotel_stays_guest ON hotel_stays(guest, stage, updated_at);
CREATE INDEX IF NOT EXISTS hotel_stays_partner ON hotel_stays(partner) WHERE partner<>'';
CREATE INDEX IF NOT EXISTS hotel_stays_live ON hotel_stays(stage, updated_at) WHERE stage IN ('booked','arrived','in');
CREATE INDEX IF NOT EXISTS hotel_stays_rest ON hotel_stays(partner_rest) WHERE partner_rest=1;
-- A host's record: stays checked out, the sum of their guests' satisfaction, situations handled and missed.
CREATE TABLE IF NOT EXISTS hotel_hosts (
  sid {T} PRIMARY KEY, stays bigint NOT NULL DEFAULT 0, mood_sum bigint NOT NULL DEFAULT 0, handled bigint NOT NULL DEFAULT 0,
  missed bigint NOT NULL DEFAULT 0, updated_at double precision NOT NULL
);
-- One rest a Vietnam day per player (a second stay that day still completes, without the rest).
CREATE TABLE IF NOT EXISTS hotel_rest (
  sid {T} NOT NULL, day {T} NOT NULL, order_id {T} NOT NULL, at double precision NOT NULL, PRIMARY KEY(sid, day)
);
-- 💒 Dịch vụ cưới từ người chơi (game/wed_services.py; SCHEMA_VERSION 69, owner 21/10). A new table and indexes only, no FK,
-- no backfill: 2.4.66 and older never read it. wedsvc_jobs: one row per wedding order (svc_orders.id; the money, escrow and
-- the 5 % burn stay there): the couple's brief (JSON, the CURRENT one: an agreed last-minute change moves it), the seven work
-- steps rolled once from the order id (plan), the provider's answers, the score and stars, the couple it serves; status work
-- (steps left) → ready (all answered) → delivered (handed over through service_market.deliver, exactly once there).
CREATE TABLE IF NOT EXISTS wedsvc_jobs (
  order_id {T} PRIMARY KEY, svc {T} NOT NULL, career {T} NOT NULL, service {T} NOT NULL, provider {T} NOT NULL, buyer {T} NOT NULL,
  couple bigint, brief {T} NOT NULL DEFAULT '{{}}', plan {T} NOT NULL DEFAULT '[]', answers {T} NOT NULL DEFAULT '[]',
  status {T} NOT NULL DEFAULT 'work' CHECK (status IN ('work','ready','delivered')), score integer NOT NULL DEFAULT 0,
  stars integer NOT NULL DEFAULT 0, created_at double precision NOT NULL, updated_at double precision NOT NULL,
  delivered_at double precision
);
CREATE INDEX IF NOT EXISTS wedsvc_jobs_couple ON wedsvc_jobs(couple, status);
CREATE INDEX IF NOT EXISTS wedsvc_jobs_provider ON wedsvc_jobs(provider, status, updated_at);
-- 🔬 Đơn nghiên cứu (game/research_lab.py; SCHEMA_VERSION 71, owner 21/10). A new table and an index only, no FK, no
-- backfill: 2.4.66 and older never read it. One row per Phố dịch vụ order of the career 'research' (svc_orders.id): the
-- research step reached (`at`, of three), the wrong tries, work → done (moved forward once, under the row lock and the old
-- `at`), the quality and the result's name. Never deleted; bounded by the market's open-order caps.
CREATE TABLE IF NOT EXISTS research_jobs (
  order_id {T} PRIMARY KEY, provider {T} NOT NULL, buyer {T} NOT NULL, service {T} NOT NULL,
  at integer NOT NULL DEFAULT 0, wrong integer NOT NULL DEFAULT 0, quality integer NOT NULL DEFAULT 100,
  status {T} NOT NULL CHECK (status IN ('work','done')), name {T} NOT NULL DEFAULT '', data {T} NOT NULL DEFAULT '{{}}',
  created_at double precision NOT NULL, updated_at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS research_jobs_provider ON research_jobs(provider, status);
-- 📜 Nội quy bang (game/bang_code.py; SCHEMA_VERSION 73, owner 21/10 "bang thì thêm cái nội quy bang nữa nhé", "công bố
-- bên ngoài thì có nội quy bang riêng nữa, có text và giới hạn chữ"). bang_code: one row per bang and kind ('pub': 📢 the
-- public rules, shown outside the bang, what an applicant agrees to; 'in': 📜 the members-only rules). `ver` grows with
-- every change of what is shown (an edit, an admin hide or show): edits compare-and-set it, a join names the version read.
-- `hidden` 1: an admin hid it (the text stays, never deleted).
CREATE TABLE IF NOT EXISTS bang_code (
  bang {T} NOT NULL, kind {T} NOT NULL CHECK (kind IN ('pub','in')), text {T} NOT NULL DEFAULT '', ver bigint NOT NULL DEFAULT 0,
  by_sid {T} NOT NULL DEFAULT '', at double precision NOT NULL DEFAULT 0, hidden integer NOT NULL DEFAULT 0,
  hidden_by {T} NOT NULL DEFAULT '', hidden_at double precision, PRIMARY KEY (bang, kind)
);
-- bang_code_hist: every edit, hide and show (`what`), with the text of that version: append-only (the operator reads what
-- was there; the edits' rate limit counts it).
CREATE TABLE IF NOT EXISTS bang_code_hist (
  id {ID} PRIMARY KEY, bang {T} NOT NULL, kind {T} NOT NULL, ver bigint NOT NULL, what {T} NOT NULL CHECK (what IN ('edit','hide','show')),
  text {T} NOT NULL DEFAULT '', by_sid {T} NOT NULL DEFAULT '', at double precision NOT NULL
);
CREATE INDEX IF NOT EXISTS bang_code_hist_bang ON bang_code_hist(bang, at);
-- bang_code_seen: per player and bang, the versions read (`pub`, `inn`: the 📜 Nội quy mới badge until they are the
-- current ones) and the public version agreed to on a join or a request (`agreed`, `agreed_at`).
CREATE TABLE IF NOT EXISTS bang_code_seen (
  sid {T} NOT NULL, bang {T} NOT NULL, pub bigint NOT NULL DEFAULT 0, inn bigint NOT NULL DEFAULT 0, agreed bigint NOT NULL DEFAULT 0,
  agreed_at double precision, at double precision NOT NULL DEFAULT 0, PRIMARY KEY (sid, bang)
);
-- 🧰 Thợ phục chế (game/restore_service.py; SCHEMA_VERSION 72, owner 21/10). A new table and indexes only, no FK, no backfill:
-- 2.4.66 and older never read it. restore_tickets: the thing a buyer brings to a restorer (`ref` a vehicle id, 'home:part'
-- or a furniture uid of the buyer's save; `label` its name then), open → bound (`order_id`: the svc_orders order it is
-- worked for, `provider`, `steps` the bench progress) → done (`grade` 1–3, `done_at`) | dropped (the buyer withdrew it);
-- a bound ticket whose order ended without delivery opens again (status back to open, order_id NULL). Never deleted.
CREATE TABLE IF NOT EXISTS restore_tickets (
  id {T} PRIMARY KEY, buyer {T} NOT NULL, service {T} NOT NULL, ref {T} NOT NULL, label {T} NOT NULL DEFAULT '',
  style {T} NOT NULL DEFAULT 'giu', status {T} NOT NULL CHECK (status IN ('open','bound','done','dropped')),
  order_id {T}, provider {T}, steps {T} NOT NULL DEFAULT '{{}}', grade integer NOT NULL DEFAULT 0,
  at double precision NOT NULL, updated_at double precision NOT NULL, done_at double precision
);
CREATE UNIQUE INDEX IF NOT EXISTS restore_tickets_order ON restore_tickets(order_id) WHERE order_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS restore_tickets_item ON restore_tickets(buyer, service, ref) WHERE status IN ('open','bound');
CREATE INDEX IF NOT EXISTS restore_tickets_buyer ON restore_tickets(buyer, service, status, at);
CREATE INDEX IF NOT EXISTS restore_tickets_provider ON restore_tickets(provider, status) WHERE provider IS NOT NULL;
-- 📻 Đài phát thanh Sóng Mây for players (game/radio_station.py; SCHEMA_VERSION 70, owner 21/10). New table and indexes only,
-- no FK, no backfill: 2.4.66 and older never read it. radio_lines: one row per line a radio DJ aired for another player through
-- Phố dịch vụ (`order_id` the svc_orders row, unique: a retried delivery finds its line), `kind` quang_cao | tang_bai, `text` the
-- ticker line as shown (moderated), `note` the buyer's own words, `pick` the bed or the song, on the ticker from `start_at` to
-- `end_at`; `hidden` 1 when the buyer, the DJ or an admin took it down (`hidden_by`), never deleted. `day` the Vietnam date
-- (the buyer's and the DJ's daily caps).
CREATE TABLE IF NOT EXISTS radio_lines (
  id {T} PRIMARY KEY, order_id {T} NOT NULL, kind {T} NOT NULL CHECK (kind IN ('quang_cao','tang_bai')), buyer {T} NOT NULL,
  provider {T} NOT NULL, text {T} NOT NULL, note {T} NOT NULL DEFAULT '', pick {T} NOT NULL DEFAULT '', day {T} NOT NULL,
  start_at double precision NOT NULL, end_at double precision NOT NULL, hidden integer NOT NULL DEFAULT 0,
  hidden_by {T} NOT NULL DEFAULT '', hidden_at double precision, created_at double precision NOT NULL, CHECK (buyer <> provider)
);
CREATE UNIQUE INDEX IF NOT EXISTS radio_lines_order ON radio_lines(order_id);
CREATE INDEX IF NOT EXISTS radio_lines_live ON radio_lines(end_at) WHERE hidden=0;
CREATE INDEX IF NOT EXISTS radio_lines_buyer ON radio_lines(buyer, day);
CREATE INDEX IF NOT EXISTS radio_lines_dj ON radio_lines(provider, day);
CREATE INDEX IF NOT EXISTS radio_lines_at ON radio_lines(created_at);
-- 🎪 Hội chợ việc làm (game/town_fair.py; SCHEMA_VERSION 74, owner 21/10 "làm hết đi"). New tables and indexes only, no FK, no
-- backfill, no save key: 2.4.66 and older never read them. The money of every fair order stays in svc_orders /
-- work_service_orders (63): a booth only lowers its owner's own Phố dịch vụ price while the fair is on.
-- fair_events: one row per fair (id 'w<YYYYMMDD>' of the weekly Saturday, 'x<epoch>' of one an admin opened), open until
-- its settle time, then final with its leaderboard snapshot (`board`, JSON) kept for the archive. Never deleted.
CREATE TABLE IF NOT EXISTS fair_events (
  id {T} PRIMARY KEY, kind {T} NOT NULL DEFAULT 'week', starts double precision NOT NULL, ends double precision NOT NULL,
  status {T} NOT NULL DEFAULT 'open' CHECK (status IN ('open','final')), board {T} NOT NULL DEFAULT '{{}}',
  announced integer NOT NULL DEFAULT 0, created_at double precision NOT NULL, final_at double precision
);
CREATE INDEX IF NOT EXISTS fair_events_open ON fair_events(ends) WHERE status='open';
-- One booth per player and fair: its career, the discount (pct), open or closed, the mood (0–100) and its counters, the
-- show running (show_until) and the next one allowed (show_next), the next oái oăm moment (next_moment); data: the moment
-- waiting for an answer, the log of answers, the watchers of the current show.
CREATE TABLE IF NOT EXISTS fair_booths (
  event {T} NOT NULL, sid {T} NOT NULL, pid {T} NOT NULL DEFAULT '', career {T} NOT NULL, pct integer NOT NULL DEFAULT 15,
  open_ integer NOT NULL DEFAULT 1, mood integer NOT NULL DEFAULT 70, shows integer NOT NULL DEFAULT 0,
  watchers integer NOT NULL DEFAULT 0, moments integer NOT NULL DEFAULT 0, handled integer NOT NULL DEFAULT 0,
  missed integer NOT NULL DEFAULT 0, show_until double precision NOT NULL DEFAULT 0, show_next double precision NOT NULL DEFAULT 0,
  next_moment double precision NOT NULL DEFAULT 0, data {T} NOT NULL DEFAULT '{{}}', opened_at double precision NOT NULL,
  updated_at double precision NOT NULL, PRIMARY KEY(event, sid)
);
CREATE INDEX IF NOT EXISTS fair_booths_career ON fair_booths(event, career);
CREATE INDEX IF NOT EXISTS fair_booths_sid ON fair_booths(sid, event);
-- 🎟️ One stamp per visitor, fair and career: src 'order' (a completed order at that career's booth, ref = the order) or
-- 'show' (a show watched while it ran, ref = the show).
CREATE TABLE IF NOT EXISTS fair_stamps (
  event {T} NOT NULL, sid {T} NOT NULL, career {T} NOT NULL, src {T} NOT NULL, ref {T} NOT NULL DEFAULT '',
  booth {T} NOT NULL DEFAULT '', at double precision NOT NULL, PRIMARY KEY(event, sid, career)
);
-- One row per visitor, fair and stamp tier claimed (the reward's live_effects row is written in the same transaction).
CREATE TABLE IF NOT EXISTS fair_rewards (
  event {T} NOT NULL, sid {T} NOT NULL, tier integer NOT NULL, item {T} NOT NULL, at double precision NOT NULL,
  PRIMARY KEY(event, sid, tier)
);
-- The admin's switches: 'weekly' ('1' on, '0' off) and 'special' (JSON {{id, starts, ends}} of a one-off fair, or '').
CREATE TABLE IF NOT EXISTS fair_config (
  k {T} PRIMARY KEY, v {T} NOT NULL DEFAULT '', by_admin {T} NOT NULL DEFAULT '', updated_at double precision NOT NULL
);
-- 🛎️ SCHEMA_VERSION 75 (review fixes 22/10): indexes only, on this release's own tables (no FK, no backfill, nothing
-- dropped: svc_orders_due stays). svc_orders_due_all: every due timer and money step (settle_for's predicates, the
-- 'refund' status included); svc_orders_working: the 🏨 stays waiting for their row (game/hotel_stay.py sync);
-- svc_orders_buyer_alert: a buyer's talks and deliveries (service_market.alert_count, each /api/news poll);
-- birth_stays_pair: a player birth room in service_market.pair_usage (payer → provider).
CREATE INDEX IF NOT EXISTS svc_orders_due_all ON svc_orders(due_at) WHERE status IN ('talk','held','working','delivered','ready','refund');
CREATE INDEX IF NOT EXISTS svc_orders_working ON svc_orders(career, service, updated_at) WHERE status='working';
CREATE INDEX IF NOT EXISTS svc_orders_buyer_alert ON svc_orders(buyer) WHERE status IN ('talk','delivered');
CREATE INDEX IF NOT EXISTS birth_stays_pair ON birth_stays(payer, provider_sid, at) WHERE provider='room';

"""

INDEX_DDL = """
CREATE UNIQUE INDEX IF NOT EXISTS island_trip_open ON island_trips(owner) WHERE status='open';
CREATE INDEX IF NOT EXISTS island_trip_ends ON island_trips(ends) WHERE status='open';
CREATE INDEX IF NOT EXISTS island_guest_of ON island_guests(guest,status);
CREATE INDEX IF NOT EXISTS island_builds_up ON island_builds(status) WHERE status='up';
CREATE INDEX IF NOT EXISTS island_public_open ON island_public(opened) WHERE status='open';
CREATE INDEX IF NOT EXISTS island_visitor_of ON island_visitors(guest,status);
CREATE UNIQUE INDEX IF NOT EXISTS home_guest_active_pair ON home_guest_invites(owner,guest)
  WHERE status IN ('pending','accepted');
CREATE INDEX IF NOT EXISTS home_guest_recipient ON home_guest_invites(guest,status);
CREATE UNIQUE INDEX IF NOT EXISTS home_deco_active_pair ON home_deco_grants(owner,guest) WHERE status='active';
CREATE INDEX IF NOT EXISTS home_deco_guest ON home_deco_grants(guest,status);
CREATE INDEX IF NOT EXISTS home_deco_log_owner ON home_deco_log(owner,id);
CREATE INDEX IF NOT EXISTS home_deco_log_actor ON home_deco_log(actor);
CREATE INDEX IF NOT EXISTS wed_invites_live ON wed_invites(status, id);
CREATE INDEX IF NOT EXISTS wed_invites_sid ON wed_invites(sid, id);
CREATE UNIQUE INDEX IF NOT EXISTS wed_invites_party ON wed_invites(sid, wedding) WHERE wedding IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS family_pending_kind ON family_requests(couple,kind) WHERE status='pending';
CREATE INDEX IF NOT EXISTS family_request_recipient ON family_requests(to_sid,status);
CREATE INDEX IF NOT EXISTS family_custody_owner ON family_custody(sid);
CREATE INDEX IF NOT EXISTS logins_sid ON logins (sid);
CREATE INDEX IF NOT EXISTS tiktok_identity_sid ON tiktok_identities (sid);
CREATE INDEX IF NOT EXISTS tiktok_flow_source ON tiktok_flows (source_sid);
CREATE INDEX IF NOT EXISTS player_feedback_sid ON player_feedback (sid, id);
CREATE INDEX IF NOT EXISTS player_feedback_status ON player_feedback (status, id);
CREATE INDEX IF NOT EXISTS inbox_pid ON inbox (pid, id);
CREATE INDEX IF NOT EXISTS board_career ON board (career, id);
CREATE INDEX IF NOT EXISTS market_status ON market (status, career);
CREATE INDEX IF NOT EXISTS preview_to ON previews (to_pid, id);
CREATE INDEX IF NOT EXISTS gifts_to ON gifts (to_pid, claimed);
CREATE INDEX IF NOT EXISTS push_subs_sid ON push_subs (sid);
CREATE INDEX IF NOT EXISTS push_queue_sid ON push_queue (sid, id);
CREATE INDEX IF NOT EXISTS stat_sessions_seen ON sessions (updated_at, revision, sid);
CREATE INDEX IF NOT EXISTS stat_births_day ON stat_births (day);
CREATE INDEX IF NOT EXISTS stat_active_sid ON stat_active (sid);
CREATE INDEX IF NOT EXISTS stat_play_sid ON stat_play (sid);
CREATE INDEX IF NOT EXISTS stat_leaves_sid ON stat_leaves USING hash (sid);   -- equality only (delete with the save): ~4x smaller than a btree
CREATE INDEX IF NOT EXISTS stat_acquisition_day ON stat_acquisition (day);
CREATE INDEX IF NOT EXISTS stat_milestones_key ON stat_milestones (key, at);   -- "started a workplace" (start:<career>) in a period
CREATE INDEX IF NOT EXISTS hits_k ON hits (k, at);
CREATE INDEX IF NOT EXISTS stat_fb_created ON player_feedback (created_at);
CREATE INDEX IF NOT EXISTS stat_accounts_created ON accounts (created_at);
CREATE INDEX IF NOT EXISTS leaderboard_rank ON leaderboard (board, score DESC, k1 DESC, k2 DESC, since, sid);
CREATE INDEX IF NOT EXISTS lb_weekly_sid ON lb_weekly (sid, final);
CREATE INDEX IF NOT EXISTS lb_weekly_board ON lb_weekly (board, final, week);
CREATE INDEX IF NOT EXISTS marriage_rings_sid ON marriage_rings (sid, status);
CREATE INDEX IF NOT EXISTS proposals_to ON proposals (to_sid, status);
CREATE INDEX IF NOT EXISTS work_places_owner ON work_visit_places(owner,visibility);
CREATE INDEX IF NOT EXISTS work_places_public ON work_visit_places(visibility,updated_at);
CREATE INDEX IF NOT EXISTS work_orders_provider ON work_service_orders(provider,status,created_at);
CREATE INDEX IF NOT EXISTS work_orders_customer ON work_service_orders(customer,created_at);
CREATE INDEX IF NOT EXISTS work_reviews_place ON work_service_reviews(place,created_at);
CREATE INDEX IF NOT EXISTS work_reviews_provider ON work_service_reviews(provider,created_at);
CREATE INDEX IF NOT EXISTS proposals_from ON proposals (from_sid, at);
CREATE INDEX IF NOT EXISTS weddings_couple ON weddings (couple, status);
CREATE INDEX IF NOT EXISTS marriage_effects_sid ON marriage_effects (sid, status, due);
CREATE INDEX IF NOT EXISTS news_at ON news (at);
CREATE INDEX IF NOT EXISTS friend_requests_to ON friend_requests (to_sid, status);
CREATE INDEX IF NOT EXISTS friend_requests_from ON friend_requests (from_sid, at);
CREATE INDEX IF NOT EXISTS friend_searches_sid ON friend_searches (sid, at);
CREATE INDEX IF NOT EXISTS joint_ledger_couple ON joint_ledger (couple, id);
CREATE INDEX IF NOT EXISTS joint_ledger_held ON joint_ledger (sid, status);
CREATE INDEX IF NOT EXISTS couple_requests_couple ON couple_requests (couple, status);
CREATE INDEX IF NOT EXISTS couple_debts_people ON couple_debts (lender, borrower);
CREATE INDEX IF NOT EXISTS couple_moments_couple ON couple_moments (couple, id);
CREATE INDEX IF NOT EXISTS system_gifts_sid ON system_gifts (sid, status);
CREATE INDEX IF NOT EXISTS system_gifts_created ON system_gifts (created);
CREATE INDEX IF NOT EXISTS chat_members_pid ON chat_members (pid, channel);
CREATE INDEX IF NOT EXISTS chat_messages_channel ON chat_messages (channel, id);
CREATE INDEX IF NOT EXISTS chat_messages_pid ON chat_messages (pid, id);
CREATE INDEX IF NOT EXISTS chat_messages_reported ON chat_messages (id) WHERE reports > 0;
CREATE INDEX IF NOT EXISTS chat_reacts_pid ON chat_reacts (pid);
CREATE INDEX IF NOT EXISTS chat_hides_msg ON chat_hides (msg);
CREATE INDEX IF NOT EXISTS chat_clears_pid ON chat_clears (pid);
CREATE INDEX IF NOT EXISTS live_effects_sid ON live_effects (sid, status);
CREATE INDEX IF NOT EXISTS live_effects_day ON live_effects (sid, kind, at);
CREATE INDEX IF NOT EXISTS quay_jobs_owner ON quay_jobs (owner, status);
CREATE INDEX IF NOT EXISTS quay_jobs_worker ON quay_jobs (worker, status);
CREATE INDEX IF NOT EXISTS quay_jobs_open ON quay_jobs (status, until);
CREATE INDEX IF NOT EXISTS bank_xfers_receiver ON bank_xfers (receiver, status);
CREATE INDEX IF NOT EXISTS bank_xfers_sender ON bank_xfers (sender, at);
CREATE INDEX IF NOT EXISTS cand_roster_post ON cand_roster (post, seen);
CREATE INDEX IF NOT EXISTS cand_stops_target ON cand_stops (target, at);
CREATE INDEX IF NOT EXISTS cand_stops_officer ON cand_stops (officer, at);
CREATE INDEX IF NOT EXISTS cand_acts_target ON cand_acts (target, kind, day);
CREATE INDEX IF NOT EXISTS cand_acts_by ON cand_acts (by_sid, kind, day);
CREATE INDEX IF NOT EXISTS cand_acts_day ON cand_acts (kind, day);
CREATE INDEX IF NOT EXISTS cand_stops_open ON cand_stops (status, at) WHERE status IN ('ask', 'offer');
CREATE INDEX IF NOT EXISTS hq_roster_post ON hq_roster (post, seen);
CREATE INDEX IF NOT EXISTS hq_cases_officer ON hq_cases (officer, at);
CREATE INDEX IF NOT EXISTS hq_cases_target ON hq_cases (target, at);
CREATE INDEX IF NOT EXISTS hq_cases_reviewer ON hq_cases (reviewer, at);
CREATE INDEX IF NOT EXISTS hq_cases_review ON hq_cases (status, at) WHERE status='review';
CREATE INDEX IF NOT EXISTS bank_xfers_open ON bank_xfers (status, at);
CREATE INDEX IF NOT EXISTS live_dates_at ON live_dates (at);
CREATE INDEX IF NOT EXISTS date_bonds_b ON date_bonds (b);
CREATE INDEX IF NOT EXISTS wedding_parties_at ON wedding_parties (status, at);
CREATE INDEX IF NOT EXISTS wedding_guests_week ON wedding_guests (week, ok);
CREATE INDEX IF NOT EXISTS wedding_guests_sid ON wedding_guests (sid, day);
CREATE INDEX IF NOT EXISTS kara_tickets_sid ON kara_tickets (sid, kind, day);
CREATE INDEX IF NOT EXISTS kara_tickets_to ON kara_tickets (to_sid, kind, day) WHERE to_sid IS NOT NULL;
CREATE INDEX IF NOT EXISTS reports_kind_at ON reports (kind, at);
"""

# Store.delete, prune and prune_guests remove dependent rows before their save.
# Statistics triggers update the admin counters atomically with each write.
TRIGGER_DDL = f"""
CREATE OR REPLACE FUNCTION mnl_stat_session_born() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO stat_births (sid, day) VALUES (NEW.sid, {VN_DAY}) ON CONFLICT DO NOTHING;
  RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION mnl_stat_session_active() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO stat_active (day, sid) VALUES ({VN_DAY}, NEW.sid) ON CONFLICT DO NOTHING;
  RETURN NULL;
END $$;
-- A deleted save keeps its stat rows (owner, 02/10: statistics kept forever): the *_gone functions do nothing.
CREATE OR REPLACE FUNCTION mnl_stat_session_gone() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION mnl_stat_play_cmd() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  _at double precision := extract(epoch FROM statement_timestamp());
  _vn timestamp := (statement_timestamp() AT TIME ZONE 'UTC') + interval '7 hours';
BEGIN
  INSERT INTO stat_play AS p (day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens)
  VALUES (to_char(_vn, 'YYYY-MM-DD'), NEW.sid, {PLAY_IDLE_TAIL}, 1, 1, _at, _at, 1 << extract(hour FROM _vn)::int, _at, '')
  ON CONFLICT (day, sid) DO UPDATE SET
    secs = p.secs + CASE WHEN _at - p.last_at <= {PLAY_GAP} THEN GREATEST(round(_at - p.last_at), 0)::bigint ELSE {PLAY_IDLE_TAIL} END,
    sessions = p.sessions + CASE WHEN _at - p.last_at <= {PLAY_GAP} THEN 0 ELSE 1 END,
    cmds = p.cmds + 1,
    last_at = GREATEST(p.last_at, _at),
    hours = p.hours | EXCLUDED.hours,
    sess_at = CASE WHEN _at - p.last_at <= {PLAY_GAP} THEN p.sess_at ELSE _at END,
    lens = CASE WHEN _at - p.last_at <= {PLAY_GAP} THEN p.lens
                ELSE p.lens || (round(p.last_at - p.sess_at)::bigint + {PLAY_IDLE_TAIL})::text || ',' END;
  RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION mnl_stat_play_gone() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION mnl_stat_retention_gone() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION mnl_stat_fb_seen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO stat_fb_ack (id, at) VALUES (NEW.id, NEW.updated_at) ON CONFLICT DO NOTHING;
  RETURN NULL;
END $$;
CREATE OR REPLACE FUNCTION mnl_stat_fb_gone() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RETURN NULL;
END $$;
CREATE OR REPLACE TRIGGER stat_session_born AFTER INSERT ON sessions FOR EACH ROW EXECUTE FUNCTION mnl_stat_session_born();
CREATE OR REPLACE TRIGGER stat_session_active AFTER UPDATE OF updated_at ON sessions FOR EACH ROW EXECUTE FUNCTION mnl_stat_session_active();
CREATE OR REPLACE TRIGGER stat_session_gone AFTER DELETE ON sessions FOR EACH ROW EXECUTE FUNCTION mnl_stat_session_gone();
CREATE OR REPLACE TRIGGER stat_play_cmd AFTER INSERT ON receipts FOR EACH ROW EXECUTE FUNCTION mnl_stat_play_cmd();
CREATE OR REPLACE TRIGGER stat_play_gone AFTER DELETE ON sessions FOR EACH ROW EXECUTE FUNCTION mnl_stat_play_gone();
CREATE OR REPLACE TRIGGER stat_retention_gone AFTER DELETE ON sessions FOR EACH ROW EXECUTE FUNCTION mnl_stat_retention_gone();
CREATE OR REPLACE TRIGGER stat_fb_seen AFTER UPDATE OF status ON player_feedback FOR EACH ROW
  WHEN (OLD.status = 'new' AND NEW.status <> 'new') EXECUTE FUNCTION mnl_stat_fb_seen();
CREATE OR REPLACE TRIGGER stat_fb_gone AFTER DELETE ON player_feedback FOR EACH ROW EXECUTE FUNCTION mnl_stat_fb_gone();
"""

# Only changed when different (ALTER TABLE takes an exclusive lock on the table).
TUNING_DDL = """
DO $$
DECLARE want text;
BEGIN
  BEGIN
    IF (SELECT attcompression FROM pg_attribute WHERE attrelid = 'sessions'::regclass AND attname = 'state') IS DISTINCT FROM 'l' THEN
      ALTER TABLE sessions ALTER COLUMN state SET COMPRESSION lz4;
    END IF;
    IF (SELECT attcompression FROM pg_attribute WHERE attrelid = 'archive'::regclass AND attname = 'row') IS DISTINCT FROM 'l' THEN
      ALTER TABLE archive ALTER COLUMN row SET COMPRESSION lz4;
    END IF;
  EXCEPTION WHEN feature_not_supported OR invalid_parameter_value THEN
    RAISE NOTICE 'lz4 is not available on this server: TOAST keeps pglz';
  END;
  -- Every command rewrites a whole save (100 KB - 1.3 MB): vacuum the hot table and its TOAST early.
  want := 'autovacuum_vacuum_scale_factor=0.02';
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid = 'sessions'::regclass AND want = ANY (coalesce(reloptions, '{}'))) THEN
    ALTER TABLE sessions SET (autovacuum_vacuum_scale_factor = 0.02, autovacuum_analyze_scale_factor = 0.05,
                              toast.autovacuum_vacuum_scale_factor = 0.02);
  END IF;
END $$;
"""

STAGES = (("tables", TABLES_DDL), ("indexes", INDEX_DDL), ("triggers", TRIGGER_DDL), ("tuning", TUNING_DDL))

# (table, trigger) pairs installed by TRIGGER_DDL.
TRIGGERS = [('sessions', 'stat_session_born'), ('sessions', 'stat_session_active'), ('sessions', 'stat_session_gone'),
            ('player_feedback', 'stat_fb_seen'), ('player_feedback', 'stat_fb_gone'),
            ('receipts', 'stat_play_cmd'), ('sessions', 'stat_play_gone'), ('sessions', 'stat_retention_gone')]


# Runtime catalog: installed tables and their generated identity columns.
TABLES = [
    dict(name='family_children', identity=None),
    dict(name='family_custody', identity=None),
    dict(name='family_requests', identity='id'),
    dict(name='family_receipts', identity=None),
    dict(name='sessions', identity=None),
    dict(name='receipts', identity=None),
    dict(name='accounts', identity='uid'),
    dict(name='logins', identity=None),
    dict(name='tiktok_identities', identity=None),
    dict(name='tiktok_flows', identity=None),
    dict(name='town_treasure_waves', identity=None),
    dict(name='town_treasure_chests', identity=None),
    dict(name='town_treasure_presence', identity=None),
    dict(name='town_treasure_proofs', identity=None),
    dict(name='player_feedback', identity='id'),
    dict(name='player_feedback_images', identity=None),
    dict(name='archive', identity=None),
    dict(name='chua_public_cards', identity='position'),
    dict(name='profiles', identity=None),
    dict(name='work_visit_places', identity=None),
    dict(name='work_service_orders', identity=None),
    dict(name='work_service_reviews', identity=None),
    dict(name='visits', identity=None),
    dict(name='previews', identity='id'),
    dict(name='gifts', identity='id'),
    dict(name='market', identity='id'),
    dict(name='board', identity='id'),
    dict(name='comments', identity='id'),
    dict(name='reactions', identity=None),
    dict(name='follows', identity=None),
    dict(name='blocks', identity=None),
    dict(name='reports', identity=None),
    dict(name='inbox', identity='id'),
    dict(name='push_subs', identity=None),
    dict(name='push_queue', identity='id'),
    dict(name='push_daily', identity=None),
    dict(name='stat_births', identity=None),
    dict(name='stat_active', identity=None),
    dict(name='stat_play', identity=None),
    dict(name='stat_play_est', identity=None),
    dict(name='stat_play_daily', identity=None),
    dict(name='stat_milestones', identity=None),
    dict(name='stat_actions', identity=None),
    dict(name='stat_actions_daily', identity=None),
    dict(name='stat_rollups', identity=None),
    dict(name='stat_leaves', identity='id'),
    dict(name='stat_leave_last', identity=None),
    dict(name='stat_client_errors', identity=None),
    dict(name='stat_loads', identity=None),
    dict(name='stat_acquisition', identity=None),
    dict(name='stat_fb_ack', identity=None),
    dict(name='hits', identity=None),
    dict(name='leaderboard', identity=None),
    dict(name='leaderboard_players', identity=None),
    dict(name='leaderboard_meta', identity=None),
    dict(name='lb_weekly', identity=None),
    dict(name='marriage_people', identity=None),
    dict(name='marriage_rings', identity=None),
    dict(name='proposals', identity='id'),
    dict(name='couples', identity='id'),
    dict(name='marriage_bonds', identity=None),
    dict(name='weddings', identity='id'),
    dict(name='marriage_effects', identity=None),
    dict(name='marriage_blocks', identity=None),
    dict(name='news', identity='id'),
    dict(name='friend_prefs', identity=None),
    dict(name='friend_requests', identity='id'),
    dict(name='friends', identity=None),
    dict(name='home_guest_invites', identity=None),
    dict(name='friend_searches', identity=None),
    dict(name='joint_funds', identity=None),
    dict(name='joint_ledger', identity='id'),
    dict(name='couple_requests', identity='id'),
    dict(name='couple_debts', identity='id'),
    dict(name='couple_moments', identity='id'),
    dict(name='couple_stats', identity=None),
    dict(name='system_gifts', identity=None),
    dict(name='chat_channels', identity=None),
    dict(name='chat_members', identity=None),
    dict(name='chat_messages', identity='id'),
    dict(name='chat_mutes', identity=None),
    dict(name='chat_prefs', identity=None),
    dict(name='chat_reacts', identity=None),
    dict(name='chat_archive', identity=None),
    dict(name='chat_pins', identity=None),
    dict(name='chat_faces', identity=None),
    dict(name='chat_hides', identity=None),
    dict(name='chat_clears', identity=None),
    dict(name='chat_slow', identity=None),
    dict(name='donations', identity=None),
    dict(name='chat_style', identity=None),
    dict(name='live_effects', identity=None),
    dict(name='quay_jobs', identity=None),
    dict(name='quay_funding', identity=None),
    dict(name='rentals', identity=None),
    dict(name='rental_receipts', identity=None),
    dict(name='rental_closed_accounts', identity=None),
    dict(name='bank_xfers', identity=None),
    dict(name='bank_xfer_days', identity=None),
    dict(name='live_dates', identity=None),
    dict(name='date_bonds', identity=None),
    dict(name='wedding_dates', identity=None),
    dict(name='wedding_parties', identity=None),
    dict(name='wedding_guests', identity=None),
    dict(name='wedding_photos', identity=None),
    dict(name='wedding_race', identity=None),
    dict(name='player_closeness', identity=None),
    dict(name='kara_songs', identity=None),
    dict(name='kara_tickets', identity=None),
    dict(name='kara_reviews', identity=None),
    dict(name='pet_board', identity=None),
    dict(name='lux_gifts', identity=None),
    dict(name='auction_lots', identity=None),
    dict(name='auction_bids', identity=None),
    dict(name='account_birth', identity=None),
    dict(name='home_deco_grants', identity=None),
    dict(name='home_deco_log', identity='id'),
    dict(name='wed_invites', identity='id'),
    dict(name='wed_invite_seen', identity=None),
    dict(name='jail_marks', identity=None),
    dict(name='cand_roster', identity=None),
    dict(name='cand_stops', identity=None),
    dict(name='cand_acts', identity=None),
    dict(name='bark_tickets', identity=None),
    dict(name='fair_loss_week', identity=None),
    dict(name='chua_wishes', identity='id'),
    dict(name='chua_wish_prayers', identity=None),
    dict(name='chua_card_marks', identity=None),
    dict(name='chua_card_prayers', identity=None),
    dict(name='ev2010_cards', identity=None),
    dict(name='ev2010_reports', identity=None),
    dict(name='ev2010_rewards', identity=None),
    dict(name='hq_roster', identity=None),
    dict(name='hq_cases', identity=None),
    dict(name='sticker_entries', identity='id'),
    dict(name='sticker_rewards', identity=None),
    dict(name='sticker_packs', identity='id'),
    dict(name='sticker_pack_images', identity=None),
    dict(name='town_projects', identity=None),
    dict(name='town_gifts', identity=None),
    dict(name='island_trips', identity=None),
    dict(name='island_guests', identity=None),
    dict(name='island_builds', identity=None),
    dict(name='island_public', identity=None),
    dict(name='island_visitors', identity=None),
    dict(name='lixi_packets', identity=None),
    dict(name='lixi_grabs', identity=None),
    dict(name='bangs', identity=None),
    dict(name='bang_members', identity=None),
    dict(name='bang_stints', identity='id'),
    dict(name='bang_asks', identity=None),
    dict(name='bang_fund', identity=None),
    dict(name='bang_points', identity=None),
    dict(name='bang_facilities', identity=None),
    dict(name='bang_items', identity=None),
    dict(name='bang_gh', identity='id'),
    dict(name='bang_log', identity='id'),
    dict(name='bang_week_win', identity=None),
    dict(name='pet_arena', identity=None),
    dict(name='pet_arena_season', identity=None),
    dict(name='pet_arena_matches', identity=None),
    dict(name='pet_cup', identity=None),
    dict(name='pet_cup_entries', identity=None),
    dict(name='pet_war', identity=None),
    dict(name='pet_war_picks', identity=None),
    dict(name='pet_war_matches', identity=None),
    dict(name='pet_team_ladder', identity=None),
    dict(name='pet_team_rating', identity=None),
    dict(name='bang_log_old', identity=None),
    dict(name='bang_points_old', identity=None),
    dict(name='bang_stints_old', identity=None),
    dict(name='pet_arena_matches_old', identity=None),
    dict(name='bang_chal_roster', identity=None),
    dict(name='bang_chal_team', identity=None),
    dict(name='bang_chal', identity=None),
    dict(name='pet_power', identity=None),
    dict(name='svc_settings', identity=None),
    dict(name='svc_orders', identity=None),
    dict(name='svc_reviews', identity=None),
    dict(name='svc_rep', identity=None),
    dict(name='svc_flags', identity=None),
    dict(name='svc_net', identity=None),
    dict(name='birth_rooms', identity='id'),
    dict(name='birth_stays', identity='id'),
    dict(name='photo_studios', identity=None),
    dict(name='photo_orders', identity=None),
    dict(name='photos', identity=None),
    dict(name='photo_pfp', identity=None),
    dict(name='hotel_stays', identity=None),
    dict(name='hotel_hosts', identity=None),
    dict(name='hotel_rest', identity=None),
    dict(name='wedsvc_jobs', identity=None),
    dict(name='research_jobs', identity=None),
    dict(name='bang_code', identity=None),
    dict(name='bang_code_hist', identity='id'),
    dict(name='bang_code_seen', identity=None),
    dict(name='restore_tickets', identity=None),
    dict(name='radio_lines', identity=None),
    dict(name='fair_events', identity=None),
    dict(name='fair_booths', identity=None),
    dict(name='fair_stamps', identity=None),
    dict(name='fair_rewards', identity=None),
    dict(name='fair_config', identity=None),
    dict(name='mnl_meta', identity=None),
]

TABLE = {t['name']: t for t in TABLES}


def _run(conn, script: str) -> None:
    """Run a DDL script on a psycopg connection (or a game.db.PgConnection)."""
    raw = getattr(conn, 'raw', conn)
    raw.execute(script)


def installed_version(conn) -> int:
    raw = getattr(conn, 'raw', conn)
    if raw.execute("SELECT to_regclass('mnl_meta')").fetchone()[0] is None:
        return 0
    row = raw.execute("SELECT value FROM mnl_meta WHERE key = 'schema_version'").fetchone()
    return int(row[0]) if row else 0


def missing_tables(conn) -> list:
    """Tables of TABLES that do not exist in the current schema (one catalog query)."""
    raw = getattr(conn, 'raw', conn)
    names = [t['name'] for t in TABLES]
    have = {r[0] for r in raw.execute("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                      "WHERE n.nspname = current_schema() AND c.relkind IN ('r', 'p') AND c.relname = ANY(%s)", (names,))}
    return [n for n in names if n not in have]


def repair_character_names(conn) -> None:
    """One-time repair for settings renames made before schema 22.

    Lock sessions first, in sid order, then update accounts: the same lock order
    as a settings commit. A concurrent rename that finishes while this query
    waits supplies its current name through PostgreSQL's locked-row recheck,
    rather than being overwritten from an earlier snapshot of the save.
    """
    raw = getattr(conn, 'raw', conn)
    raw.execute(f"""
        WITH locked AS MATERIALIZED (
          SELECT s.sid, CASE WHEN jsonb_typeof(s.state::jsonb->'name')='string'
                 THEN btrim(s.state::jsonb->>'name', E' \\t\\n\\r') END AS name
          FROM sessions s JOIN accounts a ON a.sid=s.sid
          ORDER BY s.sid FOR UPDATE OF s
        ), renamed AS (
          UPDATE accounts a SET display=l.name, updated_at={NOW_TEXT}
          FROM locked l WHERE a.sid=l.sid AND length(l.name) BETWEEN 1 AND 24
            AND l.name <> 'Mây' AND a.display IS DISTINCT FROM l.name
          RETURNING a.sid
        )
        SELECT pg_notify('mnl_live', json_build_object('op','name','sid',sid)::text)
        FROM renamed
    """)


def _ddl_tries() -> list:
    """[(lock_timeout, pause before the next try)] of ensure(): MNL_DDL_LOCK_TIMEOUT (default 3s) for the first tries,
    MNL_DDL_LOCK_TRIES of them (default 6), then one last try at MNL_DDL_LOCK_LAST (default 30s)."""
    import os
    short = (os.environ.get('MNL_DDL_LOCK_TIMEOUT') or '3s').strip()
    last = (os.environ.get('MNL_DDL_LOCK_LAST') or '30s').strip()
    try:
        n = max(0, min(50, int(os.environ.get('MNL_DDL_LOCK_TRIES') or 6)))
    except ValueError:
        n = 6
    return [(short, min(30.0, 1.0 * 2 ** i)) for i in range(n)] + [(last, 0.0)]


def _ensure_once(raw, everything: bool, stages, force: bool, lock_timeout: str):
    """One try of ensure()'s DDL transaction. (None, previous version) when it ran, (False, _) when nothing was to do."""
    with raw.transaction():
        # Serialize startup upgrades in this schema, rechecking after the wait (not bound by lock_timeout: set after).
        raw.execute("SELECT pg_advisory_xact_lock(17822, hashtext(current_schema()))")
        previous_version = installed_version(raw)
        if everything and not force and previous_version >= SCHEMA_VERSION and not missing_tables(raw):
            return False, previous_version
        # one-off DDL (an index on a big table, a slow disk): not bound by the request timeout
        raw.execute("SELECT set_config('statement_timeout', '600s', true)")
        # never queue live requests behind a DDL lock for long: give up, roll back, try again (ensure)
        raw.execute("SELECT set_config('lock_timeout', %s, true)", (lock_timeout,))
        for name, ddl in STAGES:
            if everything or name in stages:
                raw.execute(ddl)
        if everything:
            # Schema 21 is usable if the following name repair is interrupted.
            # Never hold DDL relation locks while waiting on player session rows.
            version = 21 if previous_version < 22 else SCHEMA_VERSION
            raw.execute("INSERT INTO mnl_meta (key, value) VALUES ('schema_version', %s) "
                        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (str(version),))
    return None, previous_version


def ensure(conn, stages=None, force: bool = False) -> bool:
    """Create what is missing, idempotently, in the connection's current schema (search_path).
    `stages`: a subset of ("tables", "indexes", "triggers", "tuning").
    Without `force`, a database already at SCHEMA_VERSION is left alone (no DDL, no locks).
    Returns True when an upgrade ran. DDL and data repair commit separately
    so live player transactions can finish before repair takes their row locks.
    Requires an autocommit connection.

    🔒 Live servers keep serving during an upgrade: a DDL lock (ALTER TABLE … ADD COLUMN takes ACCESS EXCLUSIVE, CREATE
    INDEX a SHARE lock) waiting behind a long player transaction would queue every request on that table behind it.
    Each lock wait is bounded by lock_timeout (_ddl_tries); the whole upgrade then rolls back (every statement here is
    idempotent) and is tried again after a pause. The last try waits longer and raises when it still cannot get its
    locks: the start fails loudly with nothing half-applied, and the next start tries again."""
    import time
    import psycopg
    raw = getattr(conn, 'raw', conn)
    everything = stages is None
    previous_version = installed_version(raw)
    if everything and not force and previous_version >= SCHEMA_VERSION and not missing_tables(raw):
        return False
    tries = _ddl_tries()
    for attempt, (timeout, pause) in enumerate(tries):
        try:
            done, previous_version = _ensure_once(raw, everything, stages, force, timeout)
            break
        except psycopg.errors.LockNotAvailable:
            if attempt == len(tries) - 1:
                raise
            time.sleep(pause)
    if done is False:
        return False
    if everything and previous_version < 22:
        with raw.transaction():
            raw.execute("SELECT pg_advisory_xact_lock(17822, hashtext(current_schema()))")
            raw.execute("SELECT set_config('statement_timeout', '600s', true)")
            if installed_version(raw) < 22:
                repair_character_names(raw)
                raw.execute("UPDATE mnl_meta SET value=%s WHERE key='schema_version'", (str(SCHEMA_VERSION),))
    return True


def reset_sequences(conn, floors: dict | None = None) -> dict:
    """Advance identities past max(id) or supplied {table: sequence floor}.
    Returns {table: next id}. Safe to run again after a database restore."""
    raw = getattr(conn, 'raw', conn)
    floors = floors or {}
    out = {}
    for t in TABLES:
        col = t['identity']
        if not col:
            continue
        top = raw.execute(f'SELECT COALESCE(MAX({col}), 0) FROM {t["name"]}').fetchone()[0]
        top = max(int(top), int(floors.get(t['name']) or 0))
        seq = raw.execute('SELECT pg_get_serial_sequence(%s, %s)', (t['name'], col)).fetchone()[0]
        if top > 0:
            raw.execute('SELECT setval(%s, %s, true)', (seq, top))
        else:
            raw.execute('SELECT setval(%s, 1, false)', (seq,))
        out[t['name']] = top + 1
    return out
