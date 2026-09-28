# Workplace scenes: every career in its own place

Date: 2026-09-29 · Sub-project 1 of 4 (scenes → work screens → career stories → care mechanics)

## Problem

All 20 careers share one canvas storefront (`public/js/boba-world.js`): the same awning, counter, shelves, "KHO", "SỔ TIỆM" and "ĐANG MỞ". Only the palette and a few props change, so a classroom or an accounting office looks like a shop. The top bar also speaks shop: "đánh giá", "Ví của tiệm".

## Goal

Seven **scene kinds**. Every career belongs to one kind and adds its own dressing: sign, shelf labels, desk items and outfit. As a result no two careers look alike, and each place reads as what it is.

| Kind | Careers | Scene |
|---|---|---|
| `shop` | milk_tea, cafe_bakery, restaurant, grocery, florist, mother_baby, pharmacy | Today's storefront, kept and tidied |
| `service` | salon, pet_care, repair | Work chair / grooming table / repair bench, waiting bench, tool wall |
| `classroom` | teacher | Blackboard, rows of pupil desks, teacher's desk, reading corner, cubbies |
| `office` | accounting, corp_accounting, tax_payroll, group_accounting, customer_care | Desks with monitors, printer, filing cabinets, a glass-walled boss room, a meeting table. customer_care adds headsets and a ticket screen |
| `farm` | farm | Sky and hills, vegetable beds, chicken coop, well, a shed as "kho" |
| `street` | delivery, tour_guide | Pavement and street front. Delivery: post office with parcel shelves and a scooter. Tour guide: a meeting point with bus stop, route board and flag |
| `lodging` | homestay | Reception desk, key board, corridor of room doors, a garden corner |

## Design

### Scene module interface (`public/js/scenes/<kind>.js`)

```js
export default {
  id: 'office',
  plan: {land: PLAN, port: PLAN},  // same schema as today's PLAN in boba-world.js
  room(w, p),                      // walls/background/sign, before people (w = the world, p = palette)
  props(w, p) → [[depthY, draw]],  // floor furniture sorted with people by feet y
  words: {…},                      // hotspot labels and top-bar vocabulary, may be overridden per career
}
```

- `plan` keeps every hotspot key: `shelf`, `evidence`, `workbench`, `counter`, `warehouse`, `board`, `finance`, `property`, `security`, `door` and `pet`. Hotspot ids, and so every action they open, do not change.
- A kind may move a hotspot anywhere on its floor. Every approach spot must be walkable, and every hotspot must be reachable from `home` (tested).
- Portrait (≤620 px wide, 700×890 scene) and landscape (1200×790) plans are both required.
- Drawing helpers move to `public/js/scenes/kit.js`: `R`, `E`, `L`, `T`, `P`, `fit`, `heart`, `bloom`, `plantAt` and `mascot`. The world keeps the shared parts: people, cat, labels, marker, speech, particles, security props, decor and nav.
- `public/js/scenes/index.js` maps career → kind, plus per-career dressing (sign title/sub, shelf names, the `tinyItem` style). Unknown careers use `shop`.

### Top bar and labels by kind (`words`)

| | shop | service | classroom | office | farm | street | lodging |
|---|---|---|---|---|---|---|---|
| rating label | đánh giá | đánh giá | phụ huynh | phản hồi | đánh giá | đánh giá | đánh giá |
| door open / closed | Mở cửa tiệm / Khép một ngày | same | Vào lớp / Tan lớp | Vào ca / Tan làm | Ra vườn / Nghỉ tay | Bắt đầu chạy / Nghỉ | Mở quầy / Khép một ngày |
| warehouse | Kho sau tiệm | Kho vật tư | Tủ đồ dùng | Tủ hồ sơ | Nhà kho | Kho hàng | Kho buồng phòng |
| till aria | Ví của tiệm | Ví của tiệm | Quỹ lớp | Quỹ bộ phận | Quỹ nông trại | Quỹ | Ví của homestay |

### Rollout

1. **Core** (single author): extract the kit, move today's scene into `scenes/shop.js`, and make BobaWorld delegate to the kind. Shop careers stay pixel-equivalent. Add the `words` plumbing and a nav reachability test for every kind and orientation.
2. **Kinds in parallel** (one author per file): service, classroom, office, farm, street, lodging.
3. **Review**: screenshots of all 20 careers, portrait and landscape; fix overlaps; run a nav test and the full browser sweep.

## Not changing

Game rules, the server, hotspot ids and actions, the work sheets (sub-project 2), and the stories (sub-project 4).

## Testing

- `node scripts/check_js.mjs`.
- A nav check in the browser (`?navdebug=1` exposes the world): for each career and orientation, every approach spot is walkable and reachable from home.
- `scripts/browser_v04.py` (no console errors, no overflow).
- Phone and desktop screenshots of each career, reviewed by eye.
