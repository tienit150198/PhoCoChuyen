"""Higher grades for the teacher (feedback #304): lớp 2 to lớp 5.

A teacher starts with lớp 1A (the classic periods of game/extra_content.LESSONS).
Each grade unlocks at a career level (1 + xp // 90). When one unlocks, the
principal offers the class: the teacher takes it or stays. The choice lives in
c['ext']['data']['homeroom'] = {g, seen, day} (optional; older builds ignore it).

A period taught in grade 2+ keeps the v1 task exactly as generated (the
task-compat gate). Its v2 layer lives under t['grade_room'] instead of
t['room'] (an older build ignores that key, so a rollback still loads the save)
and carries two more fixed facts rolled from (grade, day, slot): the grade and
the day's awkward demand (a parent, the principal, the office). The lesson
itself is never saved: lesson(grade, day, slot) rebuilds it.

Content follows the Chương trình GDPT 2018 for primary school in spirit
(Toán, Tiếng Việt, Tự nhiên và Xã hội / Khoa học, Lịch sử và Địa lí). Every
answer key is checked in tests/test_teacher_grades.py.
"""
from __future__ import annotations

import copy
import random

GRADES = (1, 2, 3, 4, 5)
# Career level needed to be offered each grade.
UNLOCK = {1: 1, 2: 2, 3: 4, 4: 6, 5: 8}
PAY_STEP = 5   # a period pays +5 xu per grade above lớp 1


def label(g: int) -> str:
    return f'Lớp {g}A'


def name(g: int) -> str:
    return f'lớp {g}A'


def level(c: dict) -> int:
    return 1 + int(c.get('xp', 0) or 0) // 90


def unlocked(c: dict) -> int:
    lv = level(c)
    return max(g for g in GRADES if lv >= UNLOCK[g])


def record(c: dict) -> dict | None:
    hr = ((c.get('ext') or {}).get('data') or {}).get('homeroom')
    return hr if isinstance(hr, dict) else None


def homeroom(c: dict | None) -> int:
    """The grade new periods are taught in (1 until the teacher takes a higher class)."""
    hr = record(c) if c else None
    return hr['g'] if hr and hr.get('g') in GRADES else 1


def offer(c: dict) -> int | None:
    """A newly unlocked grade the principal has not offered yet."""
    hr = record(c) or {}
    top = unlocked(c)
    return top if top > max(hr.get('seen', 1), homeroom(c)) else None


def _L(title, topic, subject, prompt, answer, choices, fact, ask, keys, good, ok, poor):
    return dict(title=title, topic=topic, subject=subject, prompt=prompt, answer=answer, choices=choices, fact=fact,
                q=dict(text=ask, keys=keys, answers=(('good', good), ('ok', ok), ('poor', poor))))


LESSONS = {
    2: [
        _L('Cộng có nhớ: hạc giấy', 'Toán · Cộng có nhớ', 'math',
           'Lớp 2A gấp 38 con hạc, lớp 2B gấp 25 con. Cả hai lớp gấp bao nhiêu con?', 63, [53, 63, 513],
           '8 + 5 = 13, viết 3 nhớ 1; 3 + 2 = 5, thêm 1 là 6: được 63 con.',
           '{Title} ơi, 8 cộng 5 ra 13 sao chỉ viết 3 ạ?',
           ('nho 1', 'hang chuc', 'mot chuc', '1 chuc', 'viet 3', 'don vi'),
           '13 là 1 chục và 3 đơn vị. Con viết 3 ở hàng đơn vị, nhớ 1 chục sang hàng chục. Con bó 10 que tính lại xem.',
           'Quy tắc là vậy, con cứ nhớ 1.', '{Title} giảng rồi, con tự xem lại đi.'),
        _L('Trừ có nhớ: tủ truyện', 'Toán · Trừ có nhớ', 'math',
           'Tủ có 52 cuốn truyện, các bạn mượn 17 cuốn. Tủ còn mấy cuốn?', 35, [35, 45, 69],
           '2 không trừ được 7, lấy 12 − 7 = 5, viết 5 nhớ 1; 1 thêm 1 là 2, 5 − 2 = 3: còn 35 cuốn.',
           'Sao 1 phải thêm 1 thành 2 rồi mới trừ ạ?',
           ('muon', 'muon 1', 'tra lai', 'tra 1', 'nho 1', '12 tru'),
           'Lúc nãy mình mượn 1 chục để có 12. Mượn thì phải trả: 1 thêm 1 là 2, rồi 5 − 2 = 3. Con thử bằng que tính nhé.',
           'Cứ trừ vậy là ra con ạ.', 'Hỏi hoài, làm bài đi con.'),
        _L('Bảng nhân 2: đôi đũa', 'Toán · Phép nhân', 'math',
           'Mỗi đôi đũa có 2 chiếc. 6 đôi đũa có bao nhiêu chiếc?', 12, [8, 12, 26],
           '2 được lấy 6 lần: 2 × 6 = 12 chiếc đũa.',
           '2 nhân 6 với 6 nhân 2 có bằng nhau không ạ?',
           ('bang nhau', 'nhu nhau', 'doi cho', 'deu bang', 'deu la 12'),
           'Bằng nhau con ạ, đều là 12. Đổi chỗ hai thừa số thì tích không đổi. Con xếp 6 đôi đũa ra đếm thử nhé.',
           'Chắc là bằng con ạ.', 'Học thuộc bảng là được, hỏi chi.'),
        _L('Bảng chia 5: chia kẹo', 'Toán · Phép chia', 'math',
           'Có 20 cái kẹo chia đều cho 5 bạn. Mỗi bạn được mấy cái?', 4, [4, 5, 15],
           '20 : 5 = 4, vì 5 × 4 = 20.',
           'Sao biết 20 chia 5 bằng 4 mà không cần đếm ạ?',
           ('bang nhan', 'nhan 5', '5 nhan 4', '5 x 4', 'nhan nguoc', 'nguoc lai'),
           'Nhớ bảng nhân 5: 5 × 4 = 20, nên 20 chia 5 được 4. Phép chia là nhân ngược lại. Con xếp que tính thử nhé.',
           'Thì con đếm cũng được.', 'Học bảng chưa mà hỏi?'),
        _L('Xem đồng hồ', 'Toán · Thời gian', 'math',
           'Kim ngắn nằm giữa số 3 và số 4, kim dài chỉ số 6. Đồng hồ chỉ mấy giờ?', '3 giờ 30 phút',
           ['6 giờ 15 phút', '3 giờ 30 phút', '3 giờ 6 phút'],
           'Kim ngắn qua số 3: 3 giờ. Kim dài chỉ số 6: 30 phút. Đó là 3 giờ 30 phút, 3 giờ rưỡi.',
           'Kim dài chỉ số 6 sao lại là 30 phút ạ?',
           ('5 phut', 'nam phut', 'moi so', 'dem 5', '6 lan 5', 'sau lan'),
           'Kim dài đi từ số này sang số kế là 5 phút. Từ số 12 tới số 6 là 6 lần 5 phút: 30 phút. Con đếm 5, 10, 15… thử nhé.',
           'Đồng hồ quy định vậy con ạ.', 'Nhìn kỹ đồng hồ đi.'),
        _L('Từ chỉ hoạt động', 'Tiếng Việt · Từ ngữ', 'read',
           '“Bé quét nhà, mẹ nấu cơm.” Những từ nào chỉ hoạt động?', 'quét, nấu', ['bé, mẹ', 'quét, nấu', 'nhà, cơm'],
           '“Quét”, “nấu” là việc người ta làm: từ chỉ hoạt động. “Bé, mẹ, nhà, cơm” là từ chỉ sự vật.',
           '“Cơm” cũng là từ chỉ hoạt động phải không ạ?',
           ('su vat', 'do vat', 'viec lam', 'lam gi', 'cam duoc', 'nhin thay'),
           'Không con ạ. Cơm là thứ con nhìn thấy, cầm được: từ chỉ sự vật. Hoạt động là việc làm, như nấu, ăn, quét.',
           'Không phải đâu con.', 'Sai rồi, ngồi xuống.'),
        _L('Dấu chấm hỏi', 'Tiếng Việt · Dấu câu', 'read',
           '“Bạn đi học bằng gì…” Cuối câu này cần dấu gì?', 'Dấu chấm hỏi', ['Dấu chấm', 'Dấu chấm hỏi', 'Dấu phẩy'],
           'Câu có “gì” để hỏi bạn: cuối câu hỏi dùng dấu chấm hỏi (?).',
           'Sao biết đây là câu hỏi mà không phải câu kể ạ?',
           ('tu gi', 'chu gi', 'tra loi', 'can tra loi', 'hoi ban', 'len giong'),
           'Câu có chữ “gì” và cần bạn trả lời: đó là câu hỏi. Con đọc lên giọng ở cuối câu nghe thử nhé.',
           'Đọc là biết mà con.', 'Dễ vậy mà cũng hỏi.'),
        _L('Hít vào, thở ra', 'Tự nhiên và Xã hội', 'think',
           'Hít vào bằng mũi, không khí theo khí quản đi vào đâu?', 'Phổi', ['Dạ dày', 'Phổi', 'Tim'],
           'Mũi → khí quản → phế quản → phổi. Đó là cơ quan hô hấp.',
           'Sao phải thở bằng mũi mà không thở bằng miệng ạ?',
           ('long mui', 'loc bui', 'can bui', 'am hon', 'sach hon', 'giu bui'),
           'Trong mũi có lông và chất nhầy giữ bớt bụi, làm không khí ấm hơn. Con đặt tay trước mũi thở ra thử xem.',
           'Thở bằng mũi tốt hơn con ạ.', 'Thì cứ thở bằng mũi đi.'),
    ],
    3: [
        _L('Bảng nhân 6: hộp bánh', 'Toán · Bảng nhân', 'math',
           'Mỗi hộp có 6 cái bánh. 7 hộp có bao nhiêu cái bánh?', 42, [13, 42, 48],
           '6 × 7 = 42 cái bánh.',
           'Con quên 6 nhân 7 thì làm sao nhớ lại ạ?',
           ('them 6', 'cong them', 'cong 6', '6 x 6', '36', 'dem them'),
           'Hỏi hay đó! Con nhớ 6 × 6 = 36, rồi cộng thêm một lần 6 nữa: 36 + 6 = 42.',
           'Học thuộc lòng là nhớ con ạ.', 'Quên thì chép bảng nhân 10 lần.'),
        _L('Chia có dư: xếp bàn', 'Toán · Phép chia có dư', 'math',
           '25 bạn ngồi mỗi bàn 4 bạn. Được mấy bàn đủ 4 bạn, dư mấy bạn?', '6 bàn, dư 1 bạn',
           ['5 bàn, dư 5 bạn', '6 bàn, dư 1 bạn', '7 bàn, dư 3 bạn'],
           '25 : 4 = 6 (dư 1), vì 4 × 6 = 24 và 25 − 24 = 1. Số dư luôn bé hơn số chia.',
           'Sao không phải 5 bàn dư 5 bạn ạ?',
           ('be hon', 'nho hon', 'them mot ban', 'them 1 ban', 'du 4', 'so du', 'ngoi them'),
           'Hỏi hay đó! Dư 5 bạn thì vẫn đủ 4 bạn ngồi thêm một bàn. Số dư luôn phải bé hơn số chia, nên là 6 bàn dư 1 bạn.',
           'Vì 6 bàn mới đúng con ạ.', 'Sai thì sửa, đừng cãi.'),
        _L('Chu vi vườn rau', 'Toán · Hình học', 'math',
           'Vườn rau hình chữ nhật dài 8 m, rộng 5 m. Chu vi vườn là bao nhiêu mét?', 26, [13, 26, 40],
           '(8 + 5) × 2 = 26 m. Chu vi là đi trọn một vòng quanh vườn.',
           'Sao phải nhân 2 ạ?',
           ('hai canh', '2 canh', 'mot vong', 'di mot vong', 'bon canh', '4 canh'),
           'Hình chữ nhật có hai cạnh dài, hai cạnh rộng. Đi một vòng là qua mỗi loại hai lần, nên cộng dài với rộng rồi nhân 2.',
           'Công thức vậy con ạ.', 'Thuộc công thức chưa mà hỏi?'),
        _L('Diện tích tờ giấy', 'Toán · Diện tích', 'math',
           'Tờ giấy hình vuông cạnh 6 cm. Diện tích là bao nhiêu xăng-ti-mét vuông?', 36, [12, 24, 36],
           '6 × 6 = 36 cm². Còn chu vi mới là 6 × 4 = 24 cm.',
           'Diện tích với chu vi khác nhau chỗ nào ạ?',
           ('ben trong', 'phu kin', 'o vuong', 'duong vien', 'vong quanh', 'mat giay'),
           'Chu vi là đường viền đi quanh hình. Diện tích là phần mặt giấy bên trong, đếm bằng các ô vuông 1 cm². Con tô thử nhé.',
           'Hai cái khác nhau con ạ.', 'Đọc sách giáo khoa đi.'),
        _L('Một phần tư chiếc bánh', 'Toán · Một phần mấy', 'math',
           'Bánh chưng cắt 4 phần bằng nhau, Mai ăn 1 phần. Mai ăn mấy phần chiếc bánh?', 'Một phần tư',
           ['Một phần hai', 'Một phần tư', 'Một phần ba'],
           'Chia 4 phần bằng nhau, lấy 1 phần: một phần tư (1/4) chiếc bánh.',
           'Nếu cắt 4 miếng mà miếng to miếng nhỏ thì sao ạ?',
           ('bang nhau', 'deu nhau', 'nhu nhau', 'chua phai', 'khong phai'),
           'Thì chưa phải một phần tư con ạ. Một phần tư là chia 4 phần bằng nhau. Con gấp tờ giấy làm 4 phần bằng nhau thử nhé.',
           'Cứ coi như bằng nhau con ạ.', 'Ai lại cắt bánh như vậy.'),
        _L('Trăng tròn như cái đĩa', 'Tiếng Việt · So sánh', 'read',
           'Câu “Trăng tròn như cái đĩa” so sánh trăng với gì?', 'Cái đĩa', ['Bầu trời', 'Cái đĩa', 'Ngôi sao'],
           'Từ “như” nối hai sự vật giống nhau: trăng tròn giống cái đĩa.',
           'Sao biết câu này có so sánh ạ?',
           ('tu nhu', 'chu nhu', 'giong nhau', 'giong', 'tu so sanh', 'deu tron'),
           'Con tìm từ “như”. Trước “như” là trăng, sau “như” là cái đĩa: hai thứ đều tròn nên được so sánh.',
           'Đọc là thấy mà con.', 'Câu dễ vậy cũng hỏi.'),
        _L('Ôi, bông hoa đẹp quá!', 'Tiếng Việt · Kiểu câu', 'read',
           '“Ôi, bông hoa đẹp quá!” là kiểu câu gì?', 'Câu cảm', ['Câu hỏi', 'Câu khiến', 'Câu cảm'],
           '“Ôi… quá!” bộc lộ cảm xúc, cuối câu có dấu chấm than: câu cảm.',
           'Câu khiến cũng có dấu chấm than mà ạ?',
           ('nho lam', 'bao lam', 'yeu cau', 'cam xuc', 'hay dong', 'khen'),
           'Đúng rồi, nhưng câu khiến là nhờ hay bảo ai làm gì: “Con hãy đóng cửa!”. Câu này khen hoa đẹp, bộc lộ cảm xúc nên là câu cảm.',
           'Câu này là câu cảm con ạ.', 'Nhớ đáp án là được.'),
        _L('Cây cần ánh sáng', 'Tự nhiên và Xã hội', 'think',
           'Hai cây đậu cùng được tưới: một cây để chỗ nắng, một cây úp trong hộp tối. Sau một tuần, cây nào xanh tốt?', 'Cây chỗ nắng',
           ['Cây trong hộp tối', 'Cây chỗ nắng', 'Hai cây như nhau'],
           'Lá cây cần ánh sáng để tự làm thức ăn. Cây trong hộp tối vàng úa, yếu dần.',
           'Cây trong hộp vẫn được tưới mà sao vẫn yếu ạ?',
           ('anh sang', 'nang', 'thuc an', 'lam thuc an', 'ca hai', 'ca nuoc'),
           'Cây cần cả nước lẫn ánh sáng. Lá cần ánh sáng để làm thức ăn nuôi cây, thiếu sáng thì lá vàng. Mình làm thử ở lớp nhé.',
           'Thiếu nắng thì yếu con ạ.', 'Sách viết vậy, con chép vào.'),
    ],
    4: [
        _L('Trung bình cộng chiều cao', 'Toán · Trung bình cộng', 'math',
           'Ba bạn cao 130 cm, 134 cm và 135 cm. Trung bình mỗi bạn cao bao nhiêu xăng-ti-mét?', 133, [133, 134, 399],
           '(130 + 134 + 135) : 3 = 399 : 3 = 133 cm.',
           'Sao cộng xong lại chia cho 3 ạ?',
           ('ba ban', '3 ban', 'chia deu', 'san bang', 'bang nhau', 'moi ban'),
           'Hỏi hay đó! Vì có 3 bạn. Chia đều tổng cho 3 là “san bằng” chiều cao: xem mỗi bạn cao bao nhiêu nếu ai cũng cao bằng nhau.',
           'Công thức là vậy con ạ.', 'Cứ làm theo mẫu đi.'),
        _L('Tổng và hiệu: góp vở', 'Toán · Tổng và hiệu', 'math',
           'Hai lớp góp 90 quyển vở. Lớp 4A góp nhiều hơn lớp 4B 10 quyển. Lớp 4A góp bao nhiêu quyển?', 50, [40, 45, 50],
           'Số lớn = (tổng + hiệu) : 2 = (90 + 10) : 2 = 50. Lớp 4B góp 40 quyển.',
           'Sao lại cộng 10 vào 90 ạ?',
           ('bu them', 'them 10', 'bang nhau', 'so lon', 'doan thang', 'so do'),
           'Mình bù cho lớp 4B thêm 10 quyển để hai lớp bằng nhau: 100 quyển, chia đôi là 50. Con vẽ hai đoạn thẳng thử nhé.',
           'Công thức số lớn đó con.', 'Thuộc công thức thì khỏi hỏi.'),
        _L('Rút gọn phân số', 'Toán · Phân số', 'math',
           'Rút gọn phân số 6/8 được phân số tối giản nào?', '3/4', ['2/3', '3/4', '1/2'],
           'Chia cả tử số và mẫu số cho 2: 6/8 = 3/4. 3 và 4 không cùng chia hết cho số nào lớn hơn 1.',
           'Rút gọn rồi phân số có bé đi không ạ?',
           ('khong doi', 'van bang', 'bang nhau', 'cung chia', 'ca tu', 'gia tri'),
           'Hỏi hay đó! Không con ạ. Chia cả tử và mẫu cho cùng một số thì phân số vẫn bằng như cũ: 6/8 cái bánh bằng 3/4 cái bánh.',
           'Không bé đi đâu con.', 'Hỏi câu khác đi.'),
        _L('Cộng phân số cùng mẫu', 'Toán · Phân số', 'math',
           '1/5 + 2/5 bằng bao nhiêu?', '3/5', ['3/10', '3/5', '2/5'],
           'Cùng mẫu số: cộng hai tử số, giữ nguyên mẫu số: 1/5 + 2/5 = 3/5.',
           'Sao không cộng luôn mẫu số thành 10 ạ?',
           ('giu nguyen', 'cung mau', 'mau so', '5 phan', 'nam phan', 'cai banh'),
           'Hỏi hay đó! Mẫu số cho biết bánh cắt 5 phần. Lấy 1 phần rồi thêm 2 phần là 3 trong 5 phần, bánh vẫn cắt 5 phần thôi.',
           'Quy tắc là giữ mẫu con ạ.', 'Học quy tắc rồi mà.'),
        _L('Nóc nhà Đông Dương', 'Lịch sử và Địa lí', 'think',
           'Đỉnh Phan-xi-păng, “nóc nhà Đông Dương”, nằm trên dãy núi nào?', 'Hoàng Liên Sơn',
           ['Trường Sơn', 'Hoàng Liên Sơn', 'Bạch Mã'],
           'Phan-xi-păng cao hơn 3 100 m, trên dãy Hoàng Liên Sơn, vùng Trung du và miền núi Bắc Bộ.',
           'Sao gọi là nóc nhà Đông Dương ạ?',
           ('cao nhat', 'ba nuoc', 'lao', 'cam pu chia', 'ban do', 'dong duong'),
           'Vì đó là đỉnh cao nhất ba nước Đông Dương: Việt Nam, Lào, Cam-pu-chia. Con tìm trên bản đồ cùng {title} nhé.',
           'Vì nó cao lắm con ạ.', 'Học thuộc là được.'),
        _L('Mèo tròn sưởi nắng', 'Tiếng Việt · Từ loại', 'read',
           '“Chú mèo tròn xoe nằm sưởi nắng.” Từ nào là tính từ?', 'tròn xoe', ['mèo', 'nằm', 'tròn xoe'],
           '“Tròn xoe” tả đặc điểm của chú mèo: tính từ. “Mèo” là danh từ, “nằm” là động từ.',
           'Sao “nằm” không phải tính từ ạ?',
           ('hoat dong', 'viec lam', 'lam gi', 'the nao', 'dac diem', 'dong tu'),
           'Hỏi hay đó! “Nằm” là việc chú mèo làm, trả lời câu “làm gì?”: động từ. Tính từ trả lời câu “thế nào?”: tròn xoe.',
           '“Nằm” là động từ con ạ.', 'Sai rồi, học lại bài.'),
        _L('Chị gió hát ru', 'Tiếng Việt · Nhân hóa', 'read',
           'Câu nào dùng biện pháp nhân hóa?', 'Chị gió hát ru.', ['Gió thổi mạnh.', 'Chị gió hát ru.', 'Gió mát quá.'],
           'Gọi gió là “chị”, cho gió “hát ru” như người: đó là nhân hóa.',
           'Nhân hóa với so sánh khác nhau sao ạ?',
           ('nhu nguoi', 'giong nguoi', 'goi bang', 'xung ho', 'tu nhu', 'hanh dong'),
           'Hỏi hay đó! So sánh có từ “như” nối hai sự vật. Nhân hóa thì gọi, tả sự vật như con người: chị gió, gió hát ru.',
           'Hai cái khác nhau con ạ.', 'Đọc sách đi con.'),
        _L('Nước đá tan', 'Khoa học', 'think',
           'Cục nước đá để ngoài tủ lạnh một lúc thì sao?', 'Tan thành nước', ['Bay hơi ngay', 'Tan thành nước', 'Cứng hơn'],
           'Gặp chỗ ấm, nước đá (thể rắn) nóng chảy thành nước (thể lỏng).',
           'Nước sôi thì bay đi đâu ạ?',
           ('hoi nuoc', 'bay hoi', 'the khi', 'khong khi', 'nap noi', 'dong lai'),
           'Nước sôi thành hơi nước, ở thể khí, bay vào không khí. Gặp nắp nồi lạnh, hơi nước lại đọng thành giọt. Mình thử ở lớp nhé.',
           'Bay lên trời con ạ.', 'Câu đó không có trong bài.'),
    ],
    5: [
        _L('Cộng số thập phân', 'Toán · Số thập phân', 'math',
           'Anh nặng 32,5 kg, em nặng 18,75 kg. Hai anh em nặng tất cả bao nhiêu ki-lô-gam?', '51,25',
           ['51,25', '50,80', '5,125'],
           'Đặt thẳng dấu phẩy: 32,50 + 18,75 = 51,25 kg.',
           'Sao phải viết 32,5 thành 32,50 ạ?',
           ('them so 0', 'them 0', 'khong doi', 'dau phay', 'thang hang', 'thang cot'),
           'Hỏi hay đó! Thêm số 0 ở cuối phần thập phân thì số không đổi. Viết 32,50 để hai số thẳng hàng dấu phẩy, cộng khỏi lệch cột.',
           'Cho đẹp con ạ.', 'Làm theo mẫu đi con.'),
        _L('Phần trăm đi xe đạp', 'Toán · Tỉ số phần trăm', 'math',
           'Lớp 5A có 40 bạn, 10 bạn đi xe đạp. Số bạn đi xe đạp chiếm bao nhiêu phần trăm?', '25%', ['10%', '25%', '40%'],
           '10 : 40 = 0,25 = 25%.',
           'Phần trăm nghĩa là sao ạ?',
           ('tren 100', 'mot tram', '100 ban', 'cu 100', 'cu 4', '25 ban'),
           'Hỏi hay đó! 25% là cứ 100 bạn thì có 25 bạn. Lớp mình 40 bạn: cứ 4 bạn có 1 bạn đi xe đạp.',
           'Là một phần của số đó con ạ.', 'Câu này lớp 4 học rồi.'),
        _L('Lá cờ tam giác', 'Toán · Diện tích', 'math',
           'Lá cờ hình tam giác có đáy 6 dm, chiều cao 4 dm. Diện tích lá cờ là bao nhiêu?', '12 dm²',
           ['10 dm²', '12 dm²', '24 dm²'],
           'Diện tích tam giác = đáy × chiều cao : 2 = 6 × 4 : 2 = 12 dm².',
           'Sao phải chia 2 ạ?',
           ('mot nua', 'nua hinh', 'hinh chu nhat', 'cat doi', 'ghep hai', 'ghep lai'),
           'Hai tam giác như vậy ghép lại thành hình chữ nhật 6 × 4. Một tam giác là một nửa, nên chia 2. Con cắt giấy ghép thử nhé.',
           'Công thức có chia 2 con ạ.', 'Thuộc công thức là được.'),
        _L('Vận tốc xe đạp', 'Toán · Chuyển động', 'math',
           'Xe đạp đi 24 km trong 2 giờ. Vận tốc xe đạp là bao nhiêu?', '12 km/giờ', ['12 km/giờ', '26 km/giờ', '48 km/giờ'],
           'Vận tốc = quãng đường : thời gian = 24 : 2 = 12 km/giờ.',
           'Km/giờ nghĩa là sao ạ?',
           ('moi gio', 'mot gio', 'trong 1 gio', 'trong mot gio', 'di duoc', 'ki lo met'),
           'Hỏi hay đó! Đọc là ki-lô-mét trên giờ: mỗi giờ xe đi được 12 km. Đi 2 giờ thì được 24 km.',
           'Là đơn vị vận tốc con ạ.', 'Ghi đúng đơn vị là được.'),
        _L('Bể cá nhà Khoa', 'Toán · Thể tích', 'math',
           'Bể cá dài 5 dm, rộng 3 dm, cao 4 dm. Thể tích bể là bao nhiêu đề-xi-mét khối?', 60, [12, 60, 94],
           '5 × 3 × 4 = 60 dm³. 1 dm³ = 1 lít, bể chứa đầy được 60 lít nước.',
           'Đề-xi-mét khối với lít khác nhau không ạ?',
           ('1 lit', 'mot lit', 'bang nhau', 'nhu nhau', '60 lit', 'khoi lap phuong'),
           'Bằng nhau con ạ: 1 dm³ = 1 lít. Bể này chứa vừa 60 lít nước. Mình đổ thử chai 1 lít vào hộp 1 dm³ nhé.',
           'Gần giống nhau con ạ.', 'Không thi phần đó đâu.'),
        _L('Siêng năng, chăm chỉ', 'Tiếng Việt · Từ đồng nghĩa', 'read',
           'Từ nào đồng nghĩa với “siêng năng”?', 'Chăm chỉ', ['Lười biếng', 'Chăm chỉ', 'Thông minh'],
           '“Siêng năng” và “chăm chỉ” cùng nói về người chịu khó làm việc.',
           '“Thông minh” cũng là lời khen, sao không đồng nghĩa ạ?',
           ('nghia giong', 'giong nghia', 'cung nghia', 'khac nghia', 'chiu kho', 'thay vao'),
           'Hỏi hay đó! Cùng là lời khen nhưng nghĩa khác: thông minh là nhanh hiểu, siêng năng là chịu khó. Đồng nghĩa là nghĩa giống nhau, thay vào câu được.',
           'Vì khác nghĩa con ạ.', 'Hỏi lạc đề quá.'),
        _L('Trời mưa nên đường ngập', 'Tiếng Việt · Câu ghép', 'read',
           '“Trời mưa to … đường ngập nước.” Điền kết từ nào?', 'nên', ['nhưng', 'nên', 'hoặc'],
           'Mưa to là nguyên nhân, đường ngập là kết quả: dùng “nên”.',
           '“Vì” với “nên” dùng khi nào ạ?',
           ('nguyen nhan', 'ket qua', 'ly do', 'vi sao', 'tai sao', 'dan den'),
           '“Vì” đứng trước nguyên nhân, “nên” đứng trước kết quả: Vì trời mưa to nên đường ngập nước.',
           'Đọc thấy xuôi là được con.', 'Học thuộc cặp từ đi.'),
        _L('Lấy lại muối', 'Khoa học', 'think',
           'Hòa muối vào nước, khuấy tan hết. Muốn lấy lại muối thì làm sao?', 'Cho nước bay hơi',
           ['Lọc qua giấy', 'Cho nước bay hơi', 'Để lắng'],
           'Muối tan thành dung dịch, lọc hay để lắng đều không tách được. Nước bay hơi hết thì muối còn lại.',
           'Sao lọc qua giấy không được ạ?',
           ('tan het', 'hoa tan', 'dung dich', 'lot qua', 'ruong muoi', 'qua giay'),
           'Hỏi hay đó! Muối đã tan hết vào nước, nhỏ tới mức lọt qua giấy lọc. Phải để nước bay hơi, như ruộng muối ở biển.',
           'Không được đâu con.', 'Thử là biết, hỏi chi.'),
    ],
}
QUESTIONS = {x['title']: dict(x['q']) for rows in LESSONS.values() for x in rows}


def lesson(g: int, day: int, slot: int) -> dict:
    """The lesson a grade-g period (day, slot) teaches; never saved, always rebuilt."""
    rows = LESSONS[g]
    x = rows[((day - 1) * 3 + slot) % len(rows)]
    return dict({k: copy.deepcopy(v) for k, v in x.items() if k != 'q'}, grade=g)


# ------------------------------------------------------------------ the day's awkward demand
def _d(id, grades, emoji, who, text, good, bad1, bad2):
    """good/bad = (option id, label, outcome text[, complaint, note, severity])."""
    return dict(id=id, grades=grades, emoji=emoji, who=who, text=text, options=[
        dict(id=good[0], label=good[1], text=good[2], good=True),
        dict(id=bad1[0], label=bad1[1], text=bad1[2], good=False, slip=bad1[3], note=bad1[4], sev=bad1[5]),
        dict(id=bad2[0], label=bad2[1], text=bad2[2], good=False, slip=bad2[3], note=bad2[4], sev=bad2[5])])


DEMANDS = [
    _d('zalo', (2, 3, 4, 5), '📱', 'Mẹ Vy', '22 giờ nhắn Zalo: “{Title} ơi sao Vy chỉ “Hoàn thành”? Gửi em xem bài các bạn khác với!”',
       ('meet', 'Hẹn sáng mai, cho xem bài Vy và tiêu chí', 'Mẹ Vy xem bài, gật gù: “Vậy em hiểu rồi, để em kèm thêm.”'),
       ('send', 'Gửi ảnh bài các bạn khác', 'Ảnh bài của Linh lan khắp nhóm phụ huynh.',
        'Bài của con tôi bị gửi cho phụ huynh khác xem, ai cho phép vậy?', 'lộ bài học sinh khác', 2),
       ('raise', 'Sửa thành “Hoàn thành tốt” cho xong', 'Mẹ Vy thả tim. Sáng mai ba phụ huynh khác nhắn đòi y vậy.',
        'Con nhà người ta nhắn một câu là được nâng mức, con tôi thì không.', 'sửa đánh giá theo ý phụ huynh', 2)),
    _d('plan', (2, 3, 4, 5), '📑', 'Cô Hiệu trưởng', '“Phòng yêu cầu nộp lại kế hoạch bài dạy theo mẫu mới, trước 17 giờ hôm nay.”',
       ('redo', 'Chuyển bài này sang mẫu mới, nộp đúng giờ', 'Nộp lúc 16 giờ 52. Cô Hiệu trưởng thả một dấu ✓.'),
       ('copy', 'Chép giáo án năm ngoái, đổi ngày', 'Giáo án ghi “lớp 1A”. Tổ trưởng khoanh đỏ ngay trang đầu.',
        'Kế hoạch bài dạy chép của năm ngoái, còn ghi nhầm lớp.', 'nộp giáo án chép', 1),
       ('skip', 'Để mai tính', 'Tên {title} được đọc trong buổi họp chiều.',
        'Lớp mình nộp kế hoạch bài dạy trễ hạn, nhà trường nhắc tên.', 'nộp hồ sơ trễ hạn', 1)),
    _d('fund', (2, 3, 4, 5), '💰', 'Trưởng ban phụ huynh', '“{Title} thu giúp quỹ lớp 500 nghìn mỗi bé nhé, {title} cầm cho tiện!”',
       ('board', 'Không cầm tiền; ban phụ huynh tự thu, công khai sổ', 'Ban phụ huynh tự lập sổ quỹ, gửi ảnh từng khoản lên nhóm.'),
       ('take', 'Nhận thu giúp', 'Cuối tuần thiếu 200 nghìn, ai cũng hỏi {title}.',
        'Giáo viên đứng ra thu quỹ, giờ sổ quỹ lệch mà không ai rõ.', 'giáo viên cầm tiền quỹ', 2),
       ('cut', 'Thu 300 nghìn thôi cho nhẹ', 'Vẫn là {title} cầm tiền. Hai nhà không đóng, nhắn hỏi quỹ để làm gì.',
        'Quỹ lớp do giáo viên tự đặt mức rồi thu, không bàn với phụ huynh.', 'tự đặt mức thu quỹ', 1)),
    _d('seat', (2, 3), '🪑', 'Mẹ Bảo', '“Cho Bảo lên bàn đầu nhé {title}, nhà em đóng góp nhiều mà.”',
       ('rule', 'Xếp theo thị lực, chiều cao; một tuần xem lại', 'Mẹ Bảo hơi phụng phịu, nhưng thấy cả lớp xếp cùng một cách.'),
       ('swap', 'Đổi Bảo lên, chuyển Minh xuống cuối', 'Minh ngồi cuối, nheo mắt nhìn bảng cả buổi.',
        'Minh cận mà bị chuyển xuống cuối lớp để nhường chỗ cho bạn.', 'đổi chỗ theo ý phụ huynh', 2),
       ('snap', '“Đóng góp thì liên quan gì?”', 'Ảnh chụp tin nhắn được chuyển khắp nhóm phụ huynh.',
        'Nhắn hỏi chỗ ngồi cho con mà bị trả lời cộc lốc.', 'trả lời phụ huynh cộc lốc', 1)),
    _d('neat', (2, 3), '📒', 'Cô Hiệu phó', '“Thi vở sạch chữ đẹp: nộp 3 vở đẹp nhất của lớp trước thứ Sáu.”',
       ('real', 'Chọn vở thật, có cả bạn tiến bộ nhiều', 'Vở của Tú được chọn. Bố Tú chụp ảnh khoe cả xóm.'),
       ('redo', 'Cho Linh chép lại vở hộ bạn', 'Linh chép tới khuya, sáng ra mắt thâm quầng.',
        'Con tôi phải chép vở hộ bạn để nộp thi, thức tới khuya.', 'bắt học sinh chép vở hộ', 2),
       ('self', 'Tự viết lại vở mẫu cho đẹp', 'Ban giám khảo nhận ra nét chữ người lớn.',
        'Vở thi của lớp là chữ giáo viên viết, không phải chữ các con.', 'làm hộ vở thi', 1)),
    _d('tutor', (3, 4, 5), '🏠', 'Bố Tú', '“Tối {title} dạy thêm thằng Tú ở nhà, tôi trả 200 nghìn một buổi.”',
       ('free', 'Từ chối; kèm Tú ở lớp giờ ra chơi', 'Bố Tú nhắn cụt: “Rứa cũng được. Cảm ơn.”'),
       ('yes', 'Nhận dạy, tiền trao tay', 'Nhóm phụ huynh xì xào: học thêm thì được cô ưu ái.',
        'Giáo viên chủ nhiệm nhận dạy thêm có thu tiền học sinh lớp mình.', 'dạy thêm học sinh lớp mình', 2),
       ('refer', 'Gợi ý lớp học thêm của người quen', 'Tú đi học thêm, về kể bài y như trên lớp.',
        'Giáo viên giới thiệu lớp học thêm, con không đi thì sợ bị để ý.', 'giới thiệu lớp học thêm', 1)),
    _d('exam', (4, 5), '📝', 'Mẹ Linh', '“{Title} cho em xin trước đề kiểm tra cuối kì để con ôn cho chắc ạ.”',
       ('outline', 'Gửi đề cương ôn tập chung cho cả lớp', 'Cả lớp cùng có đề cương. Mẹ Linh in ra dán lên bàn học.'),
       ('leak', 'Gửi riêng vài câu cho Linh', 'Ba hôm sau, cả nhóm phụ huynh có “đề rò rỉ”.',
        'Có nhà được giáo viên gửi trước câu hỏi kiểm tra, vậy là không công bằng.', 'lộ đề kiểm tra', 3),
       ('block', 'Chặn số chị ấy', 'Mẹ Linh lên thẳng phòng Hiệu trưởng.',
        'Nhắn hỏi chuyện học của con thì bị giáo viên chặn số.', 'chặn liên lạc phụ huynh', 1)),
    _d('soft', (4, 5), '💻', 'Văn phòng', '“Hạn nhập nhận xét lên phần mềm là 16 giờ. Lớp mình còn thiếu!”',
       ('each', 'Nhập nhận xét riêng từng bạn, kịp giờ', 'Xong lúc 15 giờ 58. Mạng lag hai lần, nhưng kịp.'),
       ('same', 'Copy một câu cho cả lớp', 'Hai mươi bạn cùng một câu “Ngoan, cần cố gắng hơn”.',
        'Nhận xét của con y hệt cả lớp, chẳng biết con tiến bộ chỗ nào.', 'nhận xét rập khuôn', 1),
       ('kid', 'Nhờ học sinh nhập hộ', 'Khoa nhập giúp, đọc được nhận xét của cả lớp.',
        'Nghe nói học sinh được nhờ nhập nhận xét, xem được thông tin của các bạn.', 'để học sinh xem dữ liệu lớp', 2)),
    _d('hocba', (5,), '🎓', 'Bố An', '“{Title} nâng điểm học bạ giúp An, để xét vào lớp 6 chất lượng cao.”',
       ('no', 'Từ chối; chỉ ra phần An cần ôn, hẹn kèm', 'Bố An im một lúc, rồi xin lịch ôn cho An.'),
       ('fix', 'Sửa điểm cho An', 'Điểm học bạ lệch với bài kiểm tra. Tổ chuyên môn gọi lên hỏi.',
        'Điểm học bạ lớp này bị sửa, phụ huynh khác đòi xem lại bài thi.', 'sửa điểm học bạ', 3),
       ('maybe', 'Nhận quà, hứa “để xem”', 'Hộp quà để trên bàn giáo viên, cả lớp nhìn thấy.',
        'Giáo viên nhận quà của phụ huynh trước kì xét tuyển.', 'nhận quà phụ huynh', 2)),
    _d('party', (5,), '🎉', 'Ban phụ huynh', '“Tiệc chia tay lớp 5 ở nhà hàng, mỗi bé 400 nghìn. {Title} báo cả lớp giúp nhé!”',
       ('class', 'Đề nghị làm ở lớp, ai góp được thì góp', 'Tiệc ở lớp, bánh mì que và nước cam. Cả lớp cười tới chiều.'),
       ('read', 'Đọc thông báo thu tiền trước lớp', 'Mai cúi mặt: nhà Mai chưa có tiền.',
        'Giáo viên đọc thu tiền tiệc trước lớp, con tôi ngại không dám đi học.', 'thu tiền trước lớp', 2),
       ('list', 'Ghi tên bạn chưa nộp lên bảng', 'Tên Mai nằm trên bảng cả buổi.',
        'Tên con bị ghi lên bảng vì chưa nộp tiền tiệc.', 'bêu tên học sinh chưa nộp tiền', 3)),
]
DEMAND = {x['id']: x for x in DEMANDS}


def demand_roll(g: int, day: int, slot: int) -> dict | None:
    """Fixed by (grade, day, slot): about two periods in three bring an awkward demand."""
    r = random.Random(f'mnl-teacher-demand|{g}|{day}|{slot}')
    pool = [x['id'] for x in DEMANDS if g in x['grades']]
    if r.random() >= 0.7 or not pool:
        return None
    return dict(id=r.choice(pool), pick=None)


# ------------------------------------------------------------------ the homeroom moment
OFFER_WHO = 'Cô Hiệu trưởng'
OFFER = '“{Title} nhận {cls} nhé? Bài khó hơn, phụ huynh cũng… khó hơn.”'
TAKE = 'Nhận {cls} · Zalo phụ huynh: 31 tin chưa đọc 😅'
STAY = 'Ở lại {cls}. Muốn lên lớp thì báo cô Hiệu trưởng.'
SWITCH = 'Từ tiết sau dạy {cls}.'


def public(c: dict) -> dict:
    g, top = homeroom(c), unlocked(c)
    lv = level(c)
    nxt = next((x for x in GRADES if UNLOCK[x] > lv), None)
    o = offer(c)
    return dict(g=g, label=label(g), top=top, offer=dict(g=o, label=label(o), who=OFFER_WHO, text=OFFER.replace('{cls}', name(o))) if o else None, grades=[dict(g=x, label=label(x), open=x <= top, level=UNLOCK[x]) for x in GRADES],
                next=dict(g=nxt, label=label(nxt), level=UNLOCK[nxt]) if nxt else None)


def choose(c: dict, grade) -> str:
    from .engine import need
    need(type(grade) is int and grade in GRADES, 'Lớp không hợp lệ.')
    need(grade <= unlocked(c), f'{label(grade)} mở ở cấp {UNLOCK.get(grade, "?")}. Dạy thêm vài tiết nữa nhé.')
    hr = record(c)
    was = homeroom(c)
    pending = offer(c)
    if hr is None:
        hr = c['ext']['data']['homeroom'] = dict(g=1, seen=1, day=0)
    if pending is None and grade != was:
        need(hr['day'] != c['day'], 'Hôm nay đã đổi lớp rồi. Mai đổi tiếp nhé.')
    hr.update(g=grade, seen=max(hr['seen'], unlocked(c)), day=c['day'] if grade != was else hr['day'])
    if pending is not None:
        return (TAKE if grade != was else STAY).format(cls=name(grade))
    return SWITCH.format(cls=name(grade)) if grade != was else f'Vẫn dạy {name(grade)}.'


def validate(c: dict) -> None:
    from .engine import need, integer
    hr = ((c.get('ext') or {}).get('data') or {}).get('homeroom')
    if hr is None:
        return
    need(isinstance(hr, dict) and set(hr) == {'g', 'seen', 'day'}, 'Lớp chủ nhiệm không hợp lệ.')
    integer(hr['g'], 1, len(GRADES))
    integer(hr['seen'], 1, len(GRADES))
    integer(hr['day'], 0, 10 ** 9)
