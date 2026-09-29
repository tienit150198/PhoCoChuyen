# Tiệm Hoa Nắng — care mechanics (sub-project 3)

Date: 2026-09-29 · Career `florist` · Files: `game/careers/florist.py`,
`public/js/careers/florist.js`, `public/css/careers/florist.css`,
`tests/test_career_florist.py`.

## Goal

Turn single orders into a loop that spans days. Flowers in the cooler open and
age from one day to the next, and a daily water change slows that down. Event
orders are booked days ahead, so the shop has to plan when to buy stock.
A regular gets a small arrangement every few days, and the shop keeps a card of
what each regular likes. Everything is decided on the server. Randomness comes
from `kit.rng` seeded by the career and the day (or by the delivery round).
`make_task` does not change, so every existing (day, slot) still makes the same
order.

## 1. The cooler — "Tủ mát"

* **Stages.** Each flower lot in the shared inventory has a stage that comes
  from its age and the days it has left.
  * *nụ* (bud): roses and lilies on the day they arrive.
  * *nở đẹp* (bloom): open and fresh.
  * *sắp héo* (wilting): its last day.

  The cooler strip and the cooler tab show the count at each stage. Regular
  orders are scored as before (days left). The stage matters for pre-orders
  and the subscription (below).
* **Water change** `fl_water` (once a day, one turn): change the water and
  recut the stems in the cooler. At day close every flower lot that is still
  there skips one night of ageing (`expires + 1`), and each lot can gain at
  most two nights (`data.kept[lot id]`). A hired prep helper who has nothing
  to prep does it on their own.
* **Neglect.** If the water was last changed two or more days ago (so two
  closes in a row without a change), the water goes cloudy and every flower
  lot loses a day at that close. Missing one day costs nothing. The chore is
  always shown and cheap to do, and it stops hurting the day it is done.
* Old saves and new games start with `water = day − 1`, which is one free day.

## 2. Pre-orders — "Đơn đặt trước"

* From day 2 a customer may call to book an event piece a few days ahead.
  The chance is 55% a day, or 80% in the wedding season, capped at 3 open
  bookings. The kinds are:

  | kind | who | lead | price | deposit | what is needed |
  |---|---|---|---|---|---|
  | 💒 bó hoa cô dâu | Linh | 3 days | 240 | 80 | 9 hồng trắng, 4 hồng phấn, 4 baby, giấy lụa trắng, ruy băng |
  | 🎉 giỏ khai trương | Anh Đạt | 2 days | 260 | 80 | 8 hướng dương, 5 hồng vàng, 4 bạch đàn, giỏ, mút |
  | 🕊️ kệ viếng | Cô Lụa | 1 day | 300 | 100 | 16 cúc trắng, 4 ly, 3 bạch đàn, chân kệ, 2 mút, băng rôn |
  | 💞 kỷ niệm cưới | Chú Phúc | 2 days | 200 | 60 | 11 hồng đỏ, 3 baby, 2 bạch đàn, giấy hồng, ruy băng |

* `fl_pre {id, do: accept|decline|make}`. Accepting takes the deposit.
  Declining is free. An offer nobody answers lapses at close with no penalty.
* **On the due day** (only then), `make` builds the piece from stock. It uses
  open stems first, then buds, then wilting stems. It takes one turn, and
  waiting customers lose a little patience. Stars start at 5: −1 if any stem
  is still a bud (bought today), −1 if any stem is wilting. The customer pays
  the balance, minus 10 xu for each star below 5. The customer then posts a
  review, and the shop gets 6 xp.
* Missing stock is refused, and the message names what is short. The booking
  card shows, for each flower, how many stems will be open on the due day
  (not bought on the day, still fresh), so the player can plan: buy the day
  before, not three days before, or keep the water fresh.
* Not made by the close of the due day: the deposit is refunded and the
  customer leaves a 1★ review.

## 3. Subscription — "Gói hoa định kỳ" (Bà Tám)

* From day 3 Bà Tám asks for a small vase of flowers every 3 days at 60 xu.
  The player can accept, decline, or stop later with `fl_sub {do: stop}`.
  She asks again 5 days after a "no".
* On a delivery day there are three templates (seeded by the round), and at
  least one of them avoids everything she dislikes. `fl_sub {do: make, pick}`
  uses the stems (same stage rules as pre-orders) plus kraft paper and a
  ribbon.
* **Her card.** At the start she says one thing: "chỉ lấy hoa nở đẹp". The
  rest the shop learns from what she says after a delivery:
  * lilies make her sneeze: −2, and "dị ứng phấn hoa ly" goes on the card;
  * white chrysanthemums are for the altar: −2, and that goes on the card;
  * a vase with no pink: −1, and "thích hồng phấn, cẩm chướng" goes on the card;
  * a bud or a wilting stem: −1 each.

  She always pays and posts a review. A missed delivery day gets a 2★
  review. Two misses in a row and she cancels.

## 4. Regulars' card — "Sổ khách quen"

* `data.book[npc] = {visits, notes}`. Each regular has two notes, and Bà Tám
  has four. The first note is learned after the first finished order, the
  second after the third. Examples: Chị Hạnh "mẹ nuôi 3 bé mèo: không ly,
  tránh baby/bạch đàn", Linh "dị ứng phấn hoa ly", Bà Tám "cúc trắng chỉ để
  bàn thờ".
* Unlearned notes never leave the server. The ticket shows a folded card for a
  known customer, and the idle panel lists the whole book.

## Readability

* The order on the ticket is a `reqList`. It has format, number of stems,
  focal count, palette (or "chưa hỏi"), card, banner, delivery time, and, only
  for a home with cats, a danger row "Nhà có mèo: không hoa ly (độc với mèo)".
  Each row updates live ✓/✗/○ from the bench.
* The price shows once, in the ticket header. It is no longer repeated on the
  order line or on each piece of a set. The value meter says "% ngân sách
  hoa" instead of printing the budget a second time.
* The side list ("Các bước làm") now holds only the making steps: fresh
  stems, cut, strip, soak, foam, arrange, wrap, ribbon. It is folded on a
  phone. Both lists use `reqList`.
* Too few stems while still picking shows ○ (not yet). It turns ✗ only when
  there are too many stems, or when the piece is arranged and still short.
* In the job view the care board is folded ("📋 Chăm tiệm hôm nay · N việc
  chờ"). A line in the day's banner says what must be delivered today. The
  idle panel shows the full board, the cooler strip with stage counts, and the
  folded regulars' book.
* The cat flags on flower tiles appear only when the recipient has cats. They
  are written in words ("độc với mèo", "mèo nên tránh") at 12 px and sit
  inside the tile instead of on top of it.

## Saves and validation

* New data keys `water`, `kept`, `book`, `pre`, `sub` are added by
  `setdefault` in `_migrate()`, which runs on every action, at start and close,
  and in `validate_data`. `public_data` reads them with defaults and never
  writes.
* `validate_data` range-checks every new field:
  * kept: at most 300 entries, values 1–2;
  * book: known npc, visits, notes, and no more notes than the visits allow;
  * pre: at most 12 bookings, known kinds, npc, price and deposit match the
    catalogue, known statuses;
  * sub: status, days, round, misses 0–1, known notes, last stars.
* All existing commands keep their payloads. The new commands are
  `fl_water`, `fl_pre` and `fl_sub`.
