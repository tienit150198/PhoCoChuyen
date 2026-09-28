> Tài liệu nền v0.2 được giữ để tra cứu. Phần bổ sung hiện hành ở V03_GUIDE.md, API_V03.md và README.md; số lượng nghề/schema trong lịch sử không mô tả v0.3.

# HTTP API thực thi v0.2.0

Dùng cùng origin với frontend. Không có CORS công khai. Ví dụ dưới là dữ liệu giả lập, không phải endpoint dịch vụ bên ngoài.

## Đọc

| Route | Nội dung |
|---|---|
| `GET /api/health` | Phiên bản và trạng thái local server |
| `GET /api/bootstrap` | Tạo/đọc cookie phiên; trả state công khai, revision, csrf, content và cờ cấu hình AI |
| `GET /api/state` | State công khai và revision; cần cookie phiên |
| `GET /api/save/export` | JSON backup đầy đủ của phiên, attachment filename |

Cookie `mnl_session` HttpOnly, SameSite=Strict, Path=/; giữ cookie từ bootstrap. Server local không dùng cookie Secure vì chạy HTTP loopback. Đừng đưa cấu hình này lên Internet rồi coi là production.

## Ghi

`POST /api/command`, `Content-Type: application/json`, header `X-Game-CSRF` lấy từ bootstrap:

```json
{
  "request_id": "mot-ma-duy-nhat-cho-y-dinh-nay",
  "expected_revision": 0,
  "career": "mother_baby",
  "action": "start_day",
  "payload": {}
}
```

Thành công trả `state`, `revision`, `result` và `replayed`. Retry cùng ý định phải dùng cùng request_id + payload + expected_revision. Cùng ID nhưng nội dung khác bị từ chối. Xung đột revision trả 409 kèm state hiện tại; lấy lại dữ liệu trước khi tạo một ý định mới. Không tự đổi ID và gửi lại lệnh đã thành công để tránh cộng thưởng hai lần.

Các nghề hợp lệ: `mother_baby`, `pharmacy`, `accounting`, `customer_care`.

| Nhóm | Action và payload điển hình |
|---|---|
| Nghề/ngày | `select_career {}` với career đích; `start_day {}`; `end_day {carry_event:true}`; `more_work {}`; `advance {}` |
| Công việc | `task_select {task}`; `ask {task}`; `defer {task}` |
| Tiệm | `shop_pick {task,item}`; `basket_remove {task,item}`; `shop_pack {task,paper,ribbon,card}`; `shop_check {task}`; `shop_deliver {task}` |
| Nhà thuốc | `ph_inspect {task,lot}`; `ph_pick {task,item:lotId}`; `ph_check {task,checks:["code","quantity","lot"]}`; `ph_deliver {task}`; `ph_refer {task}`; `ph_quarantine {lot}`; `ph_release {lot}` |
| Kho | `order_stock {item,qty}`; `receive_stock {shipment,count}`; `assistant_help {}` |
| Kế toán | `ac_inspect {task,doc}`; `ac_request_source {task}`; `ac_duplicate {task,doc}`; `ac_correct {task,doc}`; `ac_match {task,docs:[],transactions:[]}`; `ac_unmatch {task,index}`; `ac_complete {task,explanation:"source_report"}` |
| CSKH | `cs_identity {task}`; `cs_evidence {task,evidence}`; `cs_propose {task,solution}`; `cs_execute {task}`; `cs_confirm {task}`; `cs_close {task}`; `cs_handover {task}` |
| Sự kiện | `event_start {event:"MB-E07"}` là diễn tập; `event_read {evidence}`; `event_choose {choice:"a"}`; `event_confirm {}`; `event_step {}`; `event_dismiss {}` |
| Giao tiếp | `talk {npc,text}`; `chat_clear {npc}`; `feed_post {text}`; `feed_reply {post,text}`; `feed_like {post}`; `review_followup {post}` |
| Tiến triển | `buy_upgrade {item}`; `decor_move {item,spot}`; `theme {theme}`; `quest_claim {quest}`; `photo {image,title}` |
| Lưu/cài đặt | `settings {name,mode,sound,music,reduceMotion,largeText,aiConsent}`; `import_save {save:envelope}`; `reset_career {confirm:"BAT DAU LAI"}` |

`task`, `npc`, `evidence`, `shipment`, `quest` lấy từ bootstrap/state; đừng hardcode ID tác vụ theo số thứ tự UI. Hành động nghiệp vụ cần ca đang mở và đúng bước. Chỉ các setting gửi lên mới thay đổi; không cần gửi toàn bộ settings mỗi lần.

`POST /api/ai/rephrase` nhận `{career,npc}`, cùng cookie/CSRF. Trả `mode`, `text`, `canonical`, `reason`. Không có API key trong payload. Endpoint trả fallback bình thường khi AI chưa cấu hình/không đồng ý; không coi đó là lỗi game.

## Lỗi

400: dữ liệu, lệnh, điều kiện hoặc backup sai. 401: thiếu phiên. 403: Host/Origin/CSRF không được phép. 409: revision/request conflict. 413: body quá lớn. 415: cần JSON. 429: giới hạn thao tác. 500: lỗi nội bộ; UI không được báo thành công.

Host phải được cho phép. CSRF không thay thế tài khoản hay cơ chế anti-cheat; đây là phiên chơi local. Backup tối đa bị chặn ở tầng HTTP và được validate trước khi thay state.

Xem `game/engine.py` và `tests/` để biết đầy đủ các điều kiện. Schema trong `reference/data/` là tài liệu thiết kế baseline, không được dùng thay tài liệu API hiện hành này.

## Operations v0.2 — same `/api/command` transaction

All names below are prefixed `ops_`. `career` is required and stays isolated per career. For asset/cost mutations the payload MUST contain `confirm: true`. The browser confirmation dialog supplies this; a chat message cannot substitute for it. Revision and request ID follow the existing envelope. Fields shown without `confirm` do not require a cost confirmation.

| Action | Payload |
|---|---|
| `ops_hire` | `{candidate, confirm:true}` |
| `ops_assign` | `{employee, role}` |
| `ops_schedule` | `{employee, schedule:daily/odd/even/manual}` |
| `ops_shift` | `{employee, on:boolean}` |
| `ops_rest` | `{employee}` |
| `ops_train`, `ops_bonus`, `ops_warn`, `ops_dismiss` | `{employee, confirm:true}` |
| `ops_staff_talk` | `{employee, text}` |
| `ops_pay_bill` | `{bill, confirm:true}` |
| `ops_extend_bill` | `{bill}` |
| `ops_grant` | `{confirm:true}` |
| `ops_move_property` | `{tier:cozy/sunny/garden, confirm:true}`; only while closed |
| `ops_buy_security` | `{item:bell/camera/lock/light, confirm:true}` |
| `ops_insurance_toggle` | `{enabled:boolean, confirm:true}` |
| `ops_case_demo` | `{kind:misplaced/unpaid/theft/snatch}`; rehearsal only |
| `ops_case_read` | `{case?, evidence:inventory/witness/camera}` |
| `ops_case_conclude` | `{case?, finding:misplaced/forgot_payment/theft}` |
| `ops_report`, `ops_recover`, `ops_reward`, `ops_insurance_claim` | `{case?, confirm:true}` |
| `ops_case_close` | `{case?}` |
| `ops_incident_demo` | `{kind:accident/equipment/wrong_item/damage}`; rehearsal only |
| `ops_incident_read` | `{evidence:worklog/listen}` |
| `ops_incident_choose` | `{choice:coach/repair/reassign/warning, confirm:true}` |
| `ops_incident_finish`, `ops_incident_dismiss` | `{}` |

`settings` additionally accepts `{securityEvents:boolean}`. `start_day`/`end_day` hook the staff schedule and bill accrual; `advance` and actual work actions progress jobs, repair and police follow-up. Menus/ops chat do not create work ticks. No HTTP action exists to force a **live** theft or pick a successful police outcome; testing fixtures use import only in the test process.

`GET /api/bootstrap` now includes `content.operations`. Career public state includes `ops` with computed finance totals, active case and alerts. Private `_truth`, `_roll`, and evidence text that has not been opened are absent/hidden from public views. Save export is a user-owned full backup and therefore includes private simulation values. Import is not an anti-cheat certificate or competitive authorization.

Save schema is `2`; export format is `mot-ngay-lam-nghe/save-v2`. Import accepts `save-v1`/schema 1 with migration. Do not pass public presentation state back as a full save: it omits private values required to resume a case.

## Optional accounts (v0.5)

All are `POST` with the usual cookie + `X-Game-CSRF` + same-origin checks. Bodies are never logged.

| Route | Body | Result |
|---|---|---|
| `/api/account/register` | `{username, password, confirm, display}` | Attaches the **current** save to a new account; rotates the cookie to a device login token (same CSRF). Display name becomes the character/profile name if none was chosen. 409 `username_taken`. |
| `/api/account/login` | `{username, password, replace?}` | 409 `confirm_replace` (checked before the password) when this anonymous device has progress; resend with `replace:true`. On success the cookie points at the account's save (new token + CSRF for this device) and the old anonymous save is deleted. Wrong user or password: 401 "Sai tên đăng nhập hoặc mật khẩu." |
| `/api/account/logout` | `{}` | Removes this device's login; sets a fresh anonymous session cookie. |
| `/api/account/password` | `{current, password, confirm}` | Changes the password and signs out every other device. |
| `/api/account/delete` | `{confirm:"XOA"}` | Existing endpoint; now also deletes the account and all device logins. |

`GET /api/bootstrap` includes `account: {username, display} | null`. Storage: tables `accounts` (scrypt hash + salt) and `logins` (sha256 of each device token → save id, per-device CSRF). Several devices share one save; the revision guard (409 + latest state) settles concurrent writes. Account saves are not pruned for idleness; idle device logins expire after `SESSION_IDLE_DAYS`. The SQLite backup in DEPLOY.md copies the whole database, accounts included. Rate limits: register 5/10 min per IP; login 10/min per IP and 5/min (20/h) per username; password change 10/10 min per IP.
