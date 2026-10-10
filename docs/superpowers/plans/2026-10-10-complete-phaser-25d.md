# Hoàn thiện Phaser 2.5D trên source hiện tại

Ngày: 2026-10-10. Nền tích hợp: `09f630c4` (main sau pull). Phạm vi đã được người dùng chốt: cảnh 2D isometric nét mềm, nhân vật chibi, ưu tiên cảnh tĩnh, chuyển động chéo, HUD rõ trên điện thoại/tablet/desktop; giữ đầy đủ nghề, nhiệm vụ và dữ liệu mới.

## Bảo toàn và đối chiếu

- [x] Fetch và fast-forward main; lưu riêng sửa hội chợ cũ bằng stash trước khi pull.
- [x] So sánh lần tích hợp 1.9.0 (`74b4904f`) với lần gỡ giao diện 1.9.2 (`d483ec29`). Backend town/leisure vẫn còn; public runtime và artwork đã bị xóa.
- [x] Đã kiểm tra danh sách/archived Codex, tìm ChatGPT và các tab qua Chrome extension. Không tìm được đúng hai chat “Phố Có Chuyện 1”/“Phố Có Chuyện 2”; chưa đọc được lịch sử đó. Dùng ảnh trong cuộc trò chuyện này và các lỗi người dùng chỉ rõ.

## Thực hiện

1. Khôi phục các file runtime/art/style đã xóa từ bản tích hợp 1.9.0; giữ các file hiện tại đã có thay đổi mới. Khôi phục script/dependency build và build lại từ TypeScript hiện tại (có nghề mới zpop), không dùng bundle cũ.
2. Ghép các hook Phaser vào app/boot/index/journey/look hiện tại. Giữ polyfill Safari, asset recovery, menu, trang phục, economy/save và tất cả tính năng 1.9.43. Loại cảnh canvas nghề cũ khỏi đường tải chính và career warm.
3. Hoàn thiện tương thích: town-only live welcome; thứ tự đăng ký live listeners; không join town khi bị giam; không mở leisure trái jail gate; Chợ đen hiện rõ; loader chờ scene ready và có retry; chat/biểu tượng đồng bộ nét mềm. Chỉ sửa các phần được kiểm chứng thiếu.
4. Chạy bộ kiểm tra JS/TS, movement/town/leisure/map contract, asset loader/warm và các kiểm tra backend liên quan. Kiểm tra trình duyệt local với database riêng: đảo → di chuyển → nghề → quay về; hoạt động ngoài trời; chat; màn hình nhỏ/vừa/lớn; trạng thái lỗi tải có thể phục hồi.
5. Review độc lập theo yêu cầu rồi chất lượng; sửa lỗi phát hiện. Ghi lại thay đổi, kết quả thực đo và giới hạn. Không suy ra khả năng chịu 1.000 người từ FPS trình duyệt, không tự deploy production.

## Phân công và giới hạn

- Parent giữ việc phục hồi file đã xóa, asset/build, kiểm tra cảnh và đọc lịch sử; implementer chỉ sở hữu các hook file được giao rõ ràng. Không ghi đè thay đổi người khác.
- Không phục hồi toàn bộ app/backend cũ; không áp stash hội chợ cũ vào source mới một cách tự động.
- Không đưa `output/`, `.playwright-cli/` hay tài liệu reset mật khẩu không liên quan vào thay đổi bàn giao.

## Phạm vi bổ sung và kết quả

- Phaser tải bất đồng bộ, chờ scene ready và có retry; giữ các tính năng live mới, jail gate, Chợ đen, tủ đồ và nội dung nghề mới. Tách vocabulary khỏi module cảnh cũ để không kéo thêm engine cũ vào đường tải chính.
- Lái xe: cảnh phố minh họa, nhân vật theo trang phục đã lưu, camera chéo, nền và công trình cache; giữ phương án góc nhìn người lái. Sửa RAF bị khởi động hai lần khi thay kích thước. Nút/biển báo theo tông giấy ấm, cảnh có mở rộng toàn màn hình.
- Nông trại: mặc định Khu vườn, giữ góc thứ nhất/thứ ba; tám hướng theo màn hình, chạm luống thì đi đến đúng luống và dùng thao tác server cũ. Sáu luống, chuồng gà, kho, bó rơm và cây có thứ tự che khuất. Cache giữ đủ tối đa 20 chunk trong phạm vi vườn; giới hạn 24, tránh vẽ lại hàng loạt trên desktop. Tab hiện lại tiếp tục đường đi, đóng màn dọn listener.
- Máy bay: mặc định góc ngoài, chuyển được về buồng lái; cùng flight model, weather, nhiệm vụ và server. Camera nhìn được sân bay, thêm cây/taxiway và chọn đúng mặt/mái nhà theo camera. Sprite máy bay nén WebP 51.958 byte, chỉ tải khi vào bay, có hình dự phòng nếu tải lỗi.
- Bơi/chèo: thân ở trong nước, tay/chân theo nhịp; ngồi trong lòng thuyền, tay nối mái chèo và nước. Chỉ tải nền cần dùng, không tải sprite thuyền cũ không còn sử dụng. Bấm xuống hồ/lên thuyền giữ tiêu điểm bàn phím ở cảnh.
- Popup: bỏ transform trong animation, giữ chiều cao màn nghề ổn định. Màn bay giữ lớp fullscreen ngay cả khi nội dung nhiệm vụ không đổi; ẩn hướng dẫn công việc phía sau khi đang bay.

## Tham khảo hình ảnh và asset mới

- [art of rally — nhà phát hành](https://noodlecake.com/games/art-of-rally/): học cách nhìn rõ tuyến đường và đặt thông tin ở mép cảnh. Không sao chép asset.
- [Hay Day — Supercell](https://supercell.com/en/games/hayday/): tham khảo cách đọc luống/cây/công trình từ góc nhìn chéo.
- Hình máy bay tạo bằng **built-in image_gen**, alpha giữ nguyên, tối ưu kích thước/WebP bằng sharp.
  File dùng trong game: `public/icons/cozy-v3/aircraft-chase.webp` (768×512).
  Bản gốc giữ tại `C:/Users/ADMIN/.codex/generated_images/01a10ac1-359e-7992-8d83-466339b567f2/exec-ab303557-ecb2-42f7-9242-ca269d74ef8c.png`.
  Prompt/spec: một máy bay chở khách khu vực, minh họa cozy 2D nét mềm có chi tiết, thân màu kem ngà,
  xanh ngọc và sọc vàng đất, nhìn chéo cao từ sau, đối xứng, mũi hướng trên và đuôi hướng dưới;
  bánh thu vào, nền trong suốt, không nền cảnh/bóng rời/chữ/logo; dùng như sprite riêng trong game.

## Kiểm chứng 10 October

- `npm run check`: 1.034/1.034 JavaScript; Safari 15 parse/runtime probes 331/331.
- `npm run typecheck:isometric`: pass. `npm run test:isometric`: toàn chuỗi pass, bao gồm loader, current integration,
  guide lifecycle, wardrobe, town, delivery, leisure, water poses, pilot camera và farm cache/movement/lifecycle.
- Python farm/farm_plus/farm_thuc: 116 pass. Backend town/leisure/live/webassets trước đó: 51 chạy, 1 skip.
- Python pilot/variation/guidance/webassets/asset names: 89 chạy, 88 pass. Một lỗi ở `OldServer.test_flown_saves_cross_the_151_build`:
  bộ nghề của source hiện tại khác cây `_rel151` bên ngoài, bản cũ từ chối save. Các file engine/career backend và test đó
  không đổi trong lần tích hợp này. Không sửa hoặc bỏ qua gate rollback đó để báo xanh.
- Browser thật, dữ liệu local riêng: đăng ký nhân vật → đảo, vào nghề/ra đảo; mở chat; farm desktop và 390×844,
  chạm P1 rồi đến đúng luống và hiện năm thao tác; delivery nhận/kiểm/lấy hàng/gọi khách và lái làm giảm khoảng cách;
  pool xuống nước rồi bơi đến mốc 1/4 sau bản sửa focus; thuyền lên/ngồi/chèo chéo. Cảnh bay đổi góc nhìn,
  tăng ga 0→100, lăn bánh, hiển thị ở desktop/820×1180/390×844. Console không có lỗi runtime;
  một số màn công việc có warning text-budget cũ (giới hạn 25 từ).
- Dữ liệu test thuộc PostgreSQL local riêng ở 127.0.0.1:55439; không dùng save production. Fixture được lưu bản gốc
  và đã khôi phục sau kiểm tra. Preview HTTP 18891 / live 18892.
- Ảnh browser lưu riêng ở `output/phaser-completion-20261010/{farm,pilot,boat}-preview.jpg`, không đưa ảnh thử hoặc
  dữ liệu fixture vào gói source. Bundle cuối: 1.289.289 byte, gzip 361.166 byte.
- Không chạy lại benchmark 1.000 CCU trong lần chỉnh hình này. Cache/idle regression và kiểm tra browser không thay cho
  load test trên máy 9 core. Chưa deploy production.
