# Nhóm Cư Dân Phố (neighbourhood group board): design

Status: implemented in `game/board.py` (rules, state, AI prompt and guard),
`game/board_content.py` (cast and every authored line), `game/board_ai.py`
(HTTP glue), `public/js/v4/board.js`, `public/css/board.css`,
`tests/test_board.py` and `tests/test_board_http.py`.

## Why

The owner asked: "People should post on the group board now and then and
interact with each other, and let AI interact too. They ask or answer things;
when the user asks, they talk back. Warm people, cold people, tsundere… many
kinds of people." And: "Some talk a lot, some little; someone who judges
society; 'camera chạy bằng cơm' who see you come home late and hint that you
work the 'phố đêm'. Now and then people spread rumours, then someone comforts
you and gives advice."

## Cast

There are 22 residents (`C.CAST`; with the player the group has 23 members). Each has a temperament (`C.TEMPERS`, 21
kinds) and a verbosity (`terse` ≈ one short line, `normal` 1–3 sentences,
`talker` 4–6). Examples: Bà Tám (warm, talker), Cô Lụa (tổ trưởng), Chú Tư
(tsundere), Anh Khoa (biết tuốt, talker), Bé Tí (Gen Z), Quân (cold, terse),
Bác Liêm (judges society), Ông Bảy (grumpy), Chị Diệp (drama), Thư (shy,
terse), Anh Tâm (suspicious) and Chị Mai (optimist).

The street's gossips are the same three people the life layer names
(`life_content.GOSSIPS`), with the same ids, names and emoji:

- **Cô Hai Loa**: the camera, a talker;
- **Thím Bảy**: the camera, terse;
- **Chị Tư Zalo**: the gossip and the group's admin.

Older boards that still use the ids `co_huong`, `ba_mao` or `chi_tham` are
rewritten by `migrate`. Each temperament maps to a voice in `game/voices.py`
(`VOICE_OF`), whose `prompt_block` goes into the AI prompt.

## State: `s['journey']['board']`

- `posts`: at most 120 are kept. Each post keeps at most 16 comments.
- `queue`: at most 90 items. These are authored posts and comments waiting for
  their *beat*. A beat is one career action, so the board fills up while the
  player plays.
- The rest: `day`, `beat`, `clock`, `seq`, `seen` (read marker), `marks` (what
  the board has already reacted to, including `life`, the last life log row
  handled), `ai` (AI exchanges used today) and `stats`.

`validate` checks every field; `validate_state` runs it.

Everything is deterministic from (journey seed, life day, save). With story
mode off, the board stays on its first day and never reacts.

## Volume per life day

- **Daily threads**: 3–7 authored threads (about 5 on average) from 51
  threads in a seeded, cycle-shuffled stream. Each thread has NPC-to-NPC
  comments (about 3–6), plus 0–2 "floater" neighbours who drift in with their
  own line.
- **Context posts**: once each, about the save: chapter done, new workplace,
  level-up, office job, festival day, scam offer or collapse, debt.
- **Life threads**: see below, about one every 3–4 life days.
- **Rumours**: the board's own rumours come only from a real fact about the
  day (late, multi, money, van, debt), at least 3 days apart, with a 40%
  chance. They back off after a life-layer rumour. In play this comes to
  roughly one rumour every 8–12 life days.

## The player

- **Posts** are limited to 20 a day and 500 characters. They are moderated
  (`ai.abusive`) and redacted (`ai.redact`). The text is classified into an
  intent (sad, lost, complain, help, sell, happy, thanks, ask, food, greet).
  2–3 residents whose temperament suits that intent reply in character, and
  anyone @mentioned answers first.
- **Replies** go to the post's author or to the @mentioned residents.
- **Reactions**: ❤️😂😮😢😡.
- **Rumour threads** add quick tones: Giải thích, Cười trừ, Hỏi thẳng @gossip,
  Kệ thôi. After a tone, the gossip backs down or apologises, and the others
  respond in character.

## AI

`POST /api/ai/board` has two operations:

- **`{op: post|reply}`** runs `bd_post` or `bd_reply`, so the authored replies
  are stored first. Then, if AI is allowed (consent, a provider, and one unit
  of the per-player chat budget per line: `AI_CHAT_PER_MINUTE` and
  `AI_CHAT_PER_DAY`), up to 3 of those replies are reworded in character. The
  new wording is stored through the internal `bd_voice` command, and only if
  the line is still the same scripted line.
- **`{op: open}`**: when the player opens the board, the server may add one AI
  NPC-to-NPC comment (`bd_npc`) under today's daily, context or life threads.
  There are at most `AI_PER_DAY = 2` of these a life day.

Every AI line passes `board.guard`: `ai.clean_reply` checks safety, claims,
numbers and links, then the resident's own length limit is applied. The
player's name never leaves the server.

Without AI, everything still works, because the authored in-character lines
are already stored. The response carries `mode` (`ai` or `scripted`) and
`reason` (`no_consent`, `not_configured`, `rate_limit`, `superseded`, …).

## Life layer → board (`board.on_life_log`)

`life._log` calls `life._tell_board` for every row appended to
`journey.life.log`. It passes the finished card, the last choice id and the
react-stage choice. The call is guarded: on any exception the board is
restored and the life action goes on. Each row is handled once
(`marks.life`). The post and its first comment arrive at once; the rest
arrive over the next beats.

| Life row | Board |
|---|---|
| `cat lua` / `kind scam` | Anh Tâm's warning (the trick, no names). Then Cô Lụa's collection thread, which lists each contributor and amount from the card's góp rows and their total, with each contributor's line underneath; or the xóm's gift. If the player declined, Cô Lụa says the money went back. |
| `cat dat_dieu` | The rumour thread, opened by the row's gossip for its fact (late → "phố đêm", spend, draw, seen, breakup, stock). Someone piles on (Chị Tư Zalo or Bác Liêm), someone defends (Bà Tám, Chú Tư or Bé Tí; Anh Khoa too when he is the one named). The neighbour who comforted you on the life card gives short advice ("kệ người ta, sống thật là được"). The player can reply with a tone. If the life choice was to answer on the group (`post`, `invoice`), your words are already there and the gossip backs down. |
| `cat that_tinh` | Bà Tám's discreet post (nobody says what happened), with friends inviting you out: bia hơi, cà phê sống ảo, karaoke, game, a walk by the lake. |
| `kind ask` | The call for help for that neighbour (roof, theft, hospital, school, job, phone scam, Trung thu, flood). The poster thanks you for what you gave or did, and the neighbour in trouble thanks everyone. |
| `kind joy` | Congratulations or small happy posts for each joy (kittens, Bé Tí's drawing, a thank-you message, mum's parcel, …). |
| `kind sick` | Bà Tám's cháo, with neighbours offering help. |
| `cat an_hiep` | Cô Lụa's reminder not to suffer in silence (no names). |

Rumours are innuendo only. A test keeps explicit words out of every opener.

## Client

- **Entry points**: a chat-head button over the scene (`#bdFab`, with the
  unread count; on phone it is a 44px circle under the journey chip); the
  "Nhóm phố" rail and menu item with a badge; and a card on the journey home
  that shows the latest line, or "👀 Có người nhắc bạn" while a rumour is
  open.
- **The sheet**: a cover (members, rules), the composer (with the @ picker and
  the posts left today), and the feed. Comments show the last 2, with "Xem
  thêm". Each post has an inline reply field. New lines slide in, and a typing
  indicator shows while replies come. Posts can be read in pages ("Xem bài cũ
  hơn").
- **Layout**: mobile first (390px), with no horizontal overflow.
