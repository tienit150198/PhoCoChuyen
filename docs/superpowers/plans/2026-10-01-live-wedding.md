# Plan: live weddings, anniversaries and the weekly guest race (01/10/2026)

Design (owner-approved numbers): `docs/superpowers/specs/2026-10-01-live-wedding-design.md`. Branch `live-wedding`
(from main 1.0.0, merged with 1.0.5; ships as 1.1.0). Switch `LIVE_WEDDING` (live service). No version bump, no whats_new entry, no tutorial or guide.

## What players see

- **Booking** (Hôn nhân › Kế hoạch cưới): "Ngày cưới" and "Giờ" pickers (Vietnam time, 1 hour to 14 days ahead;
  tomorrow 20:00 by default) instead of "Sau N ngày sống", and one line "💍 Cả phố được mời dự tiệc lúc đó." The
  partner confirms as before (at least 15 minutes before the time). The engaged card then says "Cưới lúc 04/10/2026
  · 20:30 · Tiệc mở trước 10 phút ở Khu phố › Lịch cưới. Bạn bè được nhắc trước 30 phút." The in-game ceremony
  (deposits, NPC lì xì, the result card) runs at that time, as before otherwise.
- **The date for good**: both players' cards (Hôn nhân, and every friend card) say "💍 Cưới ngày 04/10/2026 · 20:30".
  Couples married before this feature show their wedding's time (else `married_at`).
- **Lịch cưới** (Khu phố hub): the upcoming parties ("Lan Anh & Minh Tú · 20:30 · T7 04/10"), "Mở sau 9:12",
  "Sắp bắt đầu · 6:40", "Đang diễn ra · còn 23:10" and a "Vào dự" button once the room is open; "🏆 Khách mời của tuần".
  Friends of the couple get an inbox line and a web push 30 minutes before.
- **The party** (the Đi dạo scene kit): a garden with the striped tent, the stage and its 囍, a red carpet with petals,
  flower stands, heart balloons and the flower gate; four dressed tables (sit to get topic cards). The couple stand
  on the stage under "💍 Cô dâu" / "💍 Chú rể"; guests walk in through the gate with their name tag. The header shows
  "💍 Lan Anh & Minh Tú", the guest count and the clock ("⏳ 6:12" to the start, "🎊 23:40" left). Guests cheer in
  bubbles (chat filters), send 👋 ❤️ 😂 😮 🙏, and anyone tap 📸: "3, 2, 1, Cười lên nào!", a flash, and the picture
  (a 3:2 frame around everyone, names under it) goes to the couple's Kỷ niệm (up to 3 per wedding). At the start:
  hearts and "🎊 Lễ cưới bắt đầu!". Every 5 minutes a guest sees "+15 xu" over their head. From the 61st guest:
  "Đông quá! Bạn đứng ngoài cổng xem, vẫn được tính là khách 🎉" (they watch, cannot move or talk, and count).
  A player without an account watches from the gate too ("Bạn đang xem từ ngoài cổng. [Tạo tài khoản] để vào dự."),
  and is never counted.
  At the end: "💍 Tiệc đã tàn · 25 khách ở lại chung vui 💛"; the couple get the private card "💍 Đám cưới của hai bạn
  · +1.100 xu". Guests never give lì xì; NPC neighbours still do in the in-game ceremony.
- **Anniversaries** (real calendar days since the date): on the first load from that day, each spouse gets the private
  card (💞 Trăm ngày bên nhau 200 xu · 🎂 Tròn một năm 500 · 💍 Năm trăm ngày thương 800 · 👑 Nghìn ngày son sắt 1.500),
  the title, 40-120 xu of lì xì from the neighbours, and the phố's news line "Hôm nay A và B tròn 100 ngày cưới 🎉"
  (if both allowed the wedding news).
- **Khách mời của tuần** (Xếp hạng, third tab "💍 Khách mời"): weddings attended ≥ 5 minutes this Vietnam week,
  the prizes, the days left, my count, last week's winners. Names follow Xếp hạng's privacy (accounts shown,
  guests once they opt in; your own always). Winners get the card, the xu and the title, and wear it on their name
  tag in every live scene the whole next week.

## Rules (constants in game/wedding_live.py)

| | |
|---|---|
| Booking | 1 h to 14 days ahead (`BOOK_MIN`, `BOOK_MAX`); confirmed ≥ 15 min before (`CONFIRM_MIN`) |
| Party | opens 10 min before (`OPEN_BEFORE`), lasts 30 min from the start (`PARTY_SECS`); room `wed:<wedding id>` |
| Visible | 60 avatars (`VISIBLE`); the couple always; more watch (≤ 300 per party) and count |
| Guest | +15 xu per 5 min present (`GUEST_XU`, `GUEST_STEP`), ≤ 4 per wedding, rewards from ≤ 2 weddings a day; +2 closeness with each spouse once per wedding |
| Couple, each | 30 xu per counted guest (≤ 50), +100 at 10, +250 and 🎉 Đám cưới đông vui at 20 (max 1.850) |
| Counted guest | accounts only (decided 1.1.0, with the anti-alt rule): one account once (tabs), named, ≥ 1 day old (born before today, else first seen 24 h ago), never the couple |
| No account | may watch from outside the gate ("Tạo tài khoản để vào dự"): no avatar slot, no bubbles (1.0.1: only accounts talk), no photo, never counted, no rewards. Booking needs an account, as marriage does |
| Anniversaries | 100 d 200 xu · 365 d 500 · 500 d 800 · 1000 d 1.500, + title; a divorce stops it; once per couple and milestone |
| Race | #1 300 xu + 🥇 Khách quý của phố; #2-#3 150 xu + 🎊 Ăn cưới chuyên nghiệp; ties to who reached the count first |

Interpretations (say so if the owner meant otherwise):
- "two accounts from one device": not cheap to tell (4G carriers share IPs), so ignored, as the design allows.
- "1 life day old": the live service never reads a save; it uses the same age as Cả phố (born before today).
- "the title is worn the whole next week": the title is also unlocked for good in the player's collection.
- The room counts presence from its opening (10 minutes before), so a guest can reach the 4 steps in time.

## How it is built

- **Game server** `game/wedding_live.py`: new tables only (SCHEMA_VERSION 8): `wedding_dates` (insert-only: the date
  for good, 'booked' or 'legacy'), `wedding_parties`, `wedding_guests`, `wedding_photos`, `wedding_race`,
  `player_closeness`. Booking hooks in `game/marriage.py` (`clean_plan` accepts `at`; `_plan` checks the window;
  `_confirm` sets `due_at = at`, no life-day targets, books the party; a divorce cancels it). Anniversaries on
  `/api/bootstrap`. Routes: `GET /api/wedding/race`, `GET /api/wedding/photos`, `POST /api/wedding/photo`; `POST
  /api/live/effects` also returns the gift cards now. Friend cards carry `wed` and `close`.
- **Rewards** `game/live_effects.py`: new kinds `title` (only the 7 wedding titles) and `closeness` (beside the save,
  `player_closeness`, under the row's pending → applied guard), a row's `data.popup` becomes the private card of
  game/system_gift.py (a gift row written as 'applied'), AMOUNT_MAX 2000 here and in live/effects.py. Bootstrap
  order: marriage → anniversaries → live effects → gift cards (so a card shows on the same load).
- **Live service** `live/wedding.py` (`WeddingFeature`, flag `wedding`): the schedule (every 30 s), the room on the
  street machinery (live/street.py runs `walk:` and `wed:` rooms: moves, bubbles, emotes, tables, blocks), the visible
  cap and watchers, attendance (one second per tick), the steps and the couple's settle (fixed keys), the photo slot,
  the reminder (guarded by `wedding_parties.reminded`), the weekly settle (`settle_week`, recorded in
  `wedding_race`) and the race titles on name tags. `scripts/wedding_week.py` settles a week by hand (idempotent).
- **Client** `public/js/v4/walk.js` (wedding mode: `walk.open(env,{wedding:id})`), `public/js/v4/wedding.js` (Lịch cưới,
  the Kỷ niệm photos), `public/js/scenes/stroll.js` (the wedding place), `public/js/v4/marriage.js` (date and time,
  labels), `public/js/v4/leaderboard.js` (the race tab), `public/js/app.js` (one nav line, the hub entry, the action,
  the album slot), CSS in walk.css, marriage.css, leaderboard.css.

## Tests

- `tests/test_wedding_live.py`: booking (stored for good, the ceremony waits for the time, the window, a late
  confirmation takes nothing, old clients keep life days, a divorce cancels the party), legacy dates, anniversaries
  (paid once with the card and title, a year later only the year, a divorce stops it, 1000 days = 1.500 xu), the new
  kinds (closeness, title, the card, paid once), the race view (ties, privacy), the week script (once), photos.
- `tests/test_live_wedding.py`: the schedule and window, the stage and titles, bubbles and emotes, no coffee from a
  wedding, the visible cap and watchers (counted, cannot talk), steps (2 tabs = 1 guest, at most 4), 2 weddings a day,
  new/unnamed saves and the couple never counted, host scaling 9/12/25/70 guests (cap 50, title at 20, once), the end
  of the party, the photo (gap, 3 at most), the reminder (once, inbox + push), the weekly settle (ties, once, worn
  on name tags).
- `scripts/browser_live_wedding.py`: five phones (the couple + 3 guests): planner, booking, Lịch cưới, the party,
  the watcher, bubble, heart, photo, start, steps, dark, end, the couple's card, Kỷ niệm, Xếp hạng.
- `scripts/live_load.py --weddings 3 --guests 60` (alone, and inside the 2,000-socket run).

## Production (the owner runs these)

1. Release as usual. The game server of this release creates the new tables at start-up (SCHEMA_VERSION 8; nothing
   existing changes). Bookings made before step 3 already store their date and time; their party simply has no live
   room until the switch is on (the in-game ceremony runs at that time either way).
2. Rolling release restarts `mnl-live` after the game (`deploy/rolling_release.sh`), so it loads `live/wedding.py`.
3. Turn it on: `LIVE_WEDDING=1` in `/etc/mot-ngay-lam-nghe/live.env`, `systemctl restart mnl-live`. Off again:
   `LIVE_WEDDING=0` and restart (Lịch cưới and the race tab disappear; bookings and anniversaries keep working:
   anniversaries are the game server's).
4. The weekly settle needs nothing more (the live service does it after Monday 00:00). To check or re-run a week:
   `sudo -u mnl env $(cat /etc/mot-ngay-lam-nghe/pg.env | xargs) python3 scripts/wedding_week.py --dry-run`.
5. Load test with weddings on the scratch database first:
   `PYTHONPATH=…/pyvendor python3 scripts/live_load.py --db-url postgresql://…/mnl_loadtest --conns 2000 --weddings 3 --guests 60`.
