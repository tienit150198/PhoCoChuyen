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
