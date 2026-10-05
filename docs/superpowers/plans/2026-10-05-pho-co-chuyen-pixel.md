# Phố Có Chuyện — chuyển toàn bộ sang pixel

> Phần mỹ thuật pixel của tài liệu này đã được thay thế theo phản hồi trực tiếp của người dùng: “Giữ đúng nét và độ chi tiết trong ảnh mẫu”. Xem `../specs/2026-10-05-reference-art-correction.md`. Các yêu cầu chức năng, di chuyển và tối ưu vẫn áp dụng.

Hướng mới người dùng đã chốt ngày 2026-10-05, thay thế phần mỹ thuật minh họa trong kế hoạch isometric trước. Giữ góc nhìn có chiều sâu, server và bản lưu hiện tại; không phát hành production trong công việc này.

## Điều kiện hoàn tất

1. Cảnh phố và 41 nghề dùng sprite pixel bản địa, không tải bộ WebP minh họa cũ. Nhân vật bốn hướng, bước chân khi đi, camera/collision và thứ tự trước–sau theo chân.
2. Điện thoại có cần tròn thật; tap điểm đến đi qua đường, tap cửa phải đi đến cửa rồi tương tác. Mọi kết thúc pointer, blur, modal, hidden, mode đổi đều dừng input.
3. Tất cả màn game, HUD, nhiệm vụ, đời sống, tài khoản, xã hội và mini game dùng hệ pixel đồng bộ. Chữ và đồ thị vẫn phải đọc được; không thay luật hay ID nghề.
4. Lái xe pixel, vẫn dùng vật lý, đường đi, giao thông, thao tác đến nơi và phần thưởng do server quyết định. Không còn lựa chọn mỹ thuật cũ trong UI.
5. Map chung có người thật qua liveTown, nhiệm vụ/ví/bản lưu riêng. Kiểm ít nhất hai người thật; phòng tối đa 30, không giả người online.
6. Câu cá, đi thuyền, hồ bơi có cảnh và thao tác chơi được, có đường vào từ phố. Kết quả riêng được lưu đúng qua server; hồ bơi riêng ở nhà giữ luật sở hữu hiện có.
7. Hình tĩnh cache, texture bản địa nhỏ, không frame loop vô ích khi đứng yên/ẩn/modal; giới hạn cache. Đo tải và vẽ trên browser, không dùng giả lập desktop để cam kết FPS điện thoại thật.
8. Review spec rồi quality; check/typecheck và kiểm thử tương tác, backend, browser desktop/mobile; ghi đúng phạm vi và mọi phần chưa được chứng minh. Không đánh dấu goal hoàn tất khi còn màn chưa áp dụng hoặc chưa kiểm tra.

## Trách nhiệm và việc đang làm

- Renderer worker: Phaser scene/model, đồ vật pixel, landmark ngoài phố, walking cycle, geometry và collision.
- Driving worker: cần tròn mobile, renderer lái xe pixel và vòng đời input.
- Live worker: authenticated presence, room/batch/speed/privacy, compatibility transport, thử socket.
- Controller: bộ pixel dùng chung, icon/avatar, giao diện toàn cục/legacy art bridge, câu cá/thuyền/bể bơi, app integration và đo nghiệm thu.

Các ảnh minh họa đã sinh được giữ làm tài liệu lịch sử trong docs; không đưa lại vào runtime pixel. Worktree đang có nhiều thay đổi từ trước: không reset, revert, stash hay commit chúng.
