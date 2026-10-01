# Live weddings, anniversaries and the weekly guest race (design, 01/10/2026)

This design records what the owner asked for on 01/10 and the reward numbers proposed to them. It extends the
in-game marriage in game/marriage.py (rings, proposals, couples, weddings, effects) and the live service
(`live/`; see `2026-09-30-live-chat-street-design.md` and the plan `docs/superpowers/plans/2026-10-01-live-chat-v1.md`).
It reuses the strolling scene kit (avatars, name tags, rooms) from the `live-stroll` branch. It ships in **1.0.0**,
together with chat, and appears in the release notes.

## 1. Booking a wedding: a real date and time, kept for good

- When the couple books the wedding ("đặt bàn" in today's wedding planning flow), they pick a **real date and time**,
  for example 20:30 on Saturday 04/10/2026, at least 1 hour and at most 14 days ahead.
- The chosen date and time is **stored on the couple for good** and shown on both players' cards as
  "💍 Cưới ngày 04/10/2026 · 20:30".
- **Couples married before this feature** take their existing stored wedding date and time as their date (migration
  only adds; nothing is rewritten). If none is stored, use the couple's `married_at`.
- Existing wedding rules (deposits, NPC lì xì, the in-game ceremony) keep working. The live party is an addition.

## 2. The live wedding party

- The whole phố sees the schedule (a "Lịch cưới" list in the Khu phố hub). The couple's friends get a reminder 30
  minutes before, through web push and the inbox.
- **Anyone online can attend** (real players). The party room opens 10 minutes before the start and lasts **30 minutes**.
  - The scene has a flower gate, a wedding tent and tables.
  - Everyone's avatar is present, with the **name shown above it**.
  - Guests can emote, cheer with speech bubbles (the chat filters apply) and take a group photo, a canvas snapshot
    the couple keeps in Kỷ niệm.
- **Guests do not give lì xì.** **NPC neighbours give lì xì**, as today.
- The room capacity is large, e.g. 60 visible. If more come, extra guests see a "đông quá" overflow view and are still
  counted.

## 3. Rewards (owner-approved numbers; adjustable constants)

| Who | Reward | Limits |
|---|---|---|
| Guest | **+15 xu every 5 minutes present**, plus closeness with the couple | at most 4 per wedding (60 xu), and rewards from at most 2 weddings a day |
| Couple, each | **+30 xu for every guest who stayed ≥ 5 minutes**; +100 xu at 10 guests; +250 xu and the title "Đám cưới đông vui 🎉" at 20 guests | counted up to 50 guests |

- **Anti-abuse:**
  - one account counts once, however many tabs;
  - a counted guest is a named save at least 1 life day old (old enough to rule out fresh alts);
  - the couple never count as their own guests;
  - two accounts from one device are counted once if that can be told cheaply, otherwise ignore this.
- **Payment:** through `live/effects.py` `grant()` rows, applied by the game server on load through the game's own
  command path (`game/live_effects.py`, modelled on game/system_gift.py). Idempotent, paid once, a wallet history row,
  and a private popup for the couple's total.

## 4. Anniversaries (real calendar days since the stored wedding date)

| Milestone | Gift for each spouse | Title |
|---|---|---|
| 100 days | 200 xu | 💞 Trăm ngày bên nhau |
| 1 year (365 days) | 500 xu | 🎂 Tròn một năm |
| 500 days | 800 xu | 💍 Năm trăm ngày thương |
| 1000 days | 1500 xu | 👑 Nghìn ngày son sắt |

- On the day, both spouses get a **private congratulation popup** (the system gift mechanism) with the coins, and the
  title is unlocked.
- The phố sees a small news line ("Hôm nay A và B tròn 100 ngày cưới 🎉"), and NPC neighbours add lì xì.
- **A divorce stops the count;** a new marriage starts again from its own date. Paid once per couple and milestone.

## 5. Weekly guest race ("Khách mời của tuần")

- Count, per player and per Vietnam week (Monday to Sunday), the weddings attended for at least 5 minutes, with the
  same anti-abuse rules.
- A live leaderboard "Khách mời của tuần" in Xếp hạng.
- **At the end of each week:**
  - #1 gets 🥇 **Khách quý của phố** and 300 xu;
  - #2 and #3 get 🎊 **Ăn cưới chuyên nghiệp** and 150 xu.
  - The title is worn the whole next week.
  - Ties go to whoever reached the count first.
  - Paid through the same effect path, once per week.

## 6. Constraints

- No tutorial, guide pages or coach marks; the UI explains itself. Phone first, little text, light and dark.
- Never alter existing player data beyond the intended rewards. Migrations only add. Tasks the live code generated
  must still validate (`scripts/check_task_compat.py`).
- All in-memory state is bounded. Rewards are deterministic and idempotent.
- Tests:
  - booking with a date and time;
  - legacy couples' dates;
  - the party room (attendance timing, the 5-minute drops, the caps, the anti-abuse rules, the host scaling);
  - anniversaries paid once;
  - the weekly race (ties, payout once);
  - a multi-browser wedding (couple + 3 guests);
  - load: 3 concurrent weddings with 60 guests each.

## 7. Rework after the first party (owner, 01/10/2026 15:00; supersedes §2 and §3 where they differ)

The first live party (#14, 14:15) had 14 guests talking but only 4 recorded: attendance was counted after 5 minutes
in memory, and the 1.1.2 deploy restarted the live service at 14:20 in the middle of it. The owner then asked:

- **Every guest who walks in is recorded** at once (`wedding_guests`, also the watchers at the gate; players without
  an account are recorded with ok=0 and never counted). The 1-day account age rule is dropped.
- **One party of 10 minutes** (the room opens 5 minutes before for guests to gather). **Every minute, everyone
  present during that minute gets 20 xu** (10 minutes = 200 xu; the couple too). A guest is paid at most at 2
  weddings a day (anti-farming); beyond that they are still counted. Payments are keyed per minute, so a restart of
  the live service loses nothing but the seconds before the sockets walk back in.
- **The couple: 15 xu for every counted guest** (each spouse), no cap but the room's (360); the title
  "Đám cưới đông vui" at 20 guests stays. Rewards above 2,000 xu are paid in several rows.
- **Every wedding can hold its party and invite guests for free:** "Tổ chức tiệc cưới" in Hôn nhân lets any couple
  with a wedding (married, or engaged with a confirmed plan) pick a date and time 10 minutes to 14 days ahead,
  free, once. For couples married without a date and time, that time becomes their wedding date (cards,
  anniversaries). "Mời khách" (free, once) tells both spouses' friends (inbox + push) and the phố (news line).
  Thiệp cưới in the plan is free.
- **The show** (public/js/v4/wedfeast.js, on the party clock, the same for every guest): the MC's programme, the
  neighbours at the tables, kids and teens with folk rhymes and Gen Z sayings, two lion dances, twinkling lights, the
  feast on the tables, the cake and the tower of glasses, and synthesised music (Wagner's Bridal Chorus, public
  domain, then a tune written for the game, drums under the lion dance), with a mute button.
- Deploying restarts the live service: never deploy while a party is open or within 15 minutes of one.
- **Red envelopes** (feedback #56): a guest at an open party (recorded, with an account, not the couple) picks
  10/20/50/100/200 xu and a ready-made wish. `POST /api/marriage/envelope {wedding, amount, wish, rid}`
  (game/wedding_live.py `envelope`) debits the wallet (a `marriage_effects` row `wenv:<wedding>:<rid>`, applied) and
  writes one `live_effects` row per spouse with half (`wedenv:<wedding>:<a|b>:<rid>`). At most 500 xu a guest a
  wedding; a repeated rid moves nothing. The client then sends `wed_env {rid}`: the live service reads the debit row
  back (this player's, this wedding's) and tells the room once (`wed_env {pid, name, n, text}`); the couple's
  private card at the end adds their envelope total.
- **The wishes board** ("Lời chúc"): what was said at the party and the envelopes stay on a board above the input
  (the last 3 lines; "Xem hết" shows the last 40), since bubbles fade and the phone keyboard hides them.
- **2 minutes to count** (owner, 01/10, 1.1.4): a guest counts as "đi ăn cưới" (the couple's 15 xu, the guest number
  on the end card, Khách mời của tuần) after at least `GUEST_MIN_MINUTES` = 2 paid minute marks present
  (`wedding_guests.steps >= 2`); the row is still written on entry and the minute money is unchanged.

## 8. A livelier party (1.3.0, owner 02/10/2026; extends §7)

Everything visual stays on the party clock (wedding id + seconds since `at`), so every guest sees the same show; the
live service only sends frames for real actions (eating, drinking, the bouquet, emotes).

- **The couple's name tags** (walk.js `tag(…, wed)`): a bigger gold-to-rose pill, bold 14px dark-maroon text (readable
  on light and dark), 👰/🤵 (💍 when unknown), "Cô dâu"/"Chú rể" below. When the two pills would overlap, they are
  pushed apart and kept on screen (`coupleTags`). Nothing else marks the couple.
- **The lion dance** (stroll.js `paintLion(c, x, y, t, rtl, o)`, canvas 2D, no images; the street happening uses the
  same lion): a big head (mane, horn with a pompom, ears, mirror, white brows, blinking eyes, cheeks, a jaw that opens
  with teeth and tongue, beard), a red cloth body with gold scales and fringe, two dancers' legs stepping, a tail.
  `o = {rear, hop, mouth, env, beat}`: it nods on the beat, shakes its head, rears and bites the lì xì hanging on a
  pole, then carries it. Three windows (`wedfeast.LION`): 40–110 s, 280–350 s, 450–505 s, with the drum cart.
- **Speakers and stage lights** (wedfeast.js `ground`/`over`): four speakers in the corners pulse on the beat; a disco
  ball, six beams sweeping from the stage and dance-floor tiles change colour on the beat (at most ~2 changes a
  second, only over the stage). Reduced motion (the system setting or the game's): the lights stand still and only the
  colours change slowly; no confetti, no spinning.
- **Music**: recorded, royalty-free tracks (CC0/public domain only, credits in public/music/CREDITS.md):
  `wedding-march.mp3` (Wagner, Bridal Chorus, Musopen recording, CC0) for the entrance (0–38 s, once),
  `wedding-house.mp3` (128 BPM) to 280 s, `wedding-disco.mp3` (110 BPM) after it and before the start,
  `wedding-lion.mp3` (drums and gongs) during the lion windows. Mono 64 kbps, ~2.3 MB together, served from /music/
  (versioned like the other static files). The playing position is the party second modulo the track length (plus
  the section offset), so everyone hears the same bar; `beat(s)` gives the shared beat for the lights. The engine
  (wedfeast.js `music`) decodes at most two tracks, prefetches the next section 12 s ahead, crossfades, and re-syncs
  when it drifts more than 0.35 s. The game's own music ducks while the party plays (audio.js `duck`); the existing
  unlock (`wantAudio`) and the mute button are unchanged.
- **The feast** (live/wedding.py `wed_eat`, 8 a 10 s): tapping a table opens its tray (mâm cỗ: 8 dishes, 🍺 beer,
  🥤 soft drink) and sits down if a seat is free. A dish gives +1 tinh thần, at most 3 a party (`EAT_SPIRIT`,
  `EAT_MAX`); a beer −1, at most 2 (`BEER_SPIRIT`, `BEER_MAX`), and the room sees two glasses clink "Dzô! 🍻"; a soft
  drink does nothing. Only someone inside the room, while the party is open and not ending. Each payment is a
  `live_effects` row with a fixed id `weat:<wedding>:<sid24>:<n>` / `wbeer:<wedding>:<sid24>:<n>` (n = 1…cap), so a
  restart never pays twice: the used slots are read back by primary key (`id IN (…)`), never by a scan.
  `live_effects` accepts a small negative amount for `spirit` only (down to −10). Others see an emote (🥢 + the dish,
  🍻, 🥤).
- **The bouquet** (`TOSS_AT` = 525 s): the MC calls it; the couple get "💐 Tung hoa" for `TOSS_WAIT` = 60 s, then it is
  thrown for them. The live service picks a random guest present with an account (not the couple), weighted towards
  the stage (1 / (1 + (d/140)²)), and pays `TOSS_XU` = 20 xu once a party (`wtoss:<wedding>`, checked by primary key
  after a restart). Everyone sees the bouquet fly, who caught it, and a toast.
- **Dancing**: whoever stands on the stage (`wedfeast.STAGE`) sways on the beat; "💃 Nhảy" (emote `dance`, weddings
  only) spins them for the room. Confetti when the couple walk in (0–7 s), fireworks in the last 25 s.
- No DDL, no change to player data; the new constants live in game/wedding_live.py.
