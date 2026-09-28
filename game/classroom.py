"""Teacher v0.4: "Kế hoạch lớp" — varied lessons, grading, parent meetings and a
school-year calendar of events (Trung thu, sinh nhật tháng, 20/11, hội khỏe,
Tết, dã ngoại, tổng kết).

Activities are step procedures (game/procedures.py). Answer keys live in this
module, never in the save; the save keeps only the activity id and progress.
Everything is fictional; school rules here are simplified game rules.
"""
from __future__ import annotations
import copy

from . import procedures as P

S = P.step
MONTHS = ('Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5')
DAYS_PER_MONTH = 4
YEAR = DAYS_PER_MONTH * len(MONTHS)
NPC = dict(ha='teacher_npc_01', minh='teacher_npc_02', an='teacher_npc_03', vy='teacher_npc_04', bao='teacher_npc_05', lan='teacher_npc_06')
KIND_LABEL = dict(lesson='Tiết học', grading='Chấm bài', meeting='Phụ huynh', event='Sự kiện', duty='Dạy thay')


def o(id, label):
    return dict(id=id, label=label)


def V(who, emoji, text):
    return dict(who=who, emoji=emoji, text=text)


ACTIVITIES = [
    # ------------------------------------------------------------ lessons
    dict(id='les_math_market', kind='lesson', emoji='🧮', tag='Toán', title='Tiết Toán “Đi chợ tí hon”', reward=20, xp=20, npcs=['minh', 'an', 'vy', 'bao'],
         intro='Lớp học phép trừ có nhớ trong phạm vi 100 qua trò chơi đi chợ bằng tiền giấy đồ chơi.',
         facts=[dict(title='Bốn bạn trong nhóm', text='Minh cần nhìn hình mẫu trước. An thích cầm đồ vật để thử. Vy hiểu nhanh khi được nói thành lời. Bảo tập trung được khoảng 5 phút, cần bài chia nhỏ.'),
                dict(title='Đồ dùng có sẵn', text='Tiền giấy đồ chơi, thẻ giá, rổ nhựa, bảng phụ, phiếu bài tập. Không có máy tính cầm tay.')],
         steps=[S('goal', 'choice', 'Mục tiêu tiết học', 'Chọn mục tiêu rõ và đo được cho tiết này.', 'sub',
                  options=[o('fun', 'Cả lớp chơi vui là được'), o('sub', 'Mỗi bạn tự tính được tiền thối trong phạm vi 100 và giải thích cách làm'), o('fast', 'Bạn nào tính nhanh nhất được thưởng')],
                  hints=['Mục tiêu tốt nói rõ học sinh làm được gì sau tiết học.'], explain='Mục tiêu nói rõ “làm được gì” giúp bạn biết cuối tiết cần kiểm tra điều gì.'),
                S('flow', 'order', 'Nhịp tiết học', 'Sắp xếp các hoạt động theo trình tự hợp lý.', ['warm', 'model', 'group', 'share', 'check'],
                  items=[o('group', 'Chơi đi chợ theo nhóm 4'), o('check', 'Phiếu 3 câu cuối tiết'), o('warm', 'Khởi động: đếm tiền nhanh'), o('share', 'Các nhóm kể cách tính'), o('model', '{Title} làm mẫu một lượt mua bán')],
                  hints=['Làm mẫu trước khi để các nhóm tự chơi.', 'Kiểm tra cá nhân nên nằm cuối cùng.'], explain='Khởi động → làm mẫu → thực hành → chia sẻ → kiểm tra.'),
                S('diff', 'match', 'Giao việc theo từng bạn', 'Mỗi bạn nhận một vai phù hợp với cách học.', dict(minh='card', an='money', vy='say', bao='small'),
                  left=[o('minh', 'Minh'), o('an', 'An'), o('vy', 'Vy'), o('bao', 'Bảo')],
                  right=[o('card', 'Xem thẻ hình mẫu rồi làm theo'), o('money', 'Cầm tiền giấy đếm thử'), o('say', 'Nói to cách tính cho nhóm'), o('small', 'Làm từng lượt mua 1 món, có dấu tích')],
                  hints=['Đọc lại mục “Bốn bạn trong nhóm”.'], explain='Cùng một mục tiêu, mỗi bạn đi bằng con đường hợp với mình.'),
                S('calc', 'number', 'Câu hỏi của Bảo', 'Bảo mua một hộp bút giá 35 nghìn và đưa tờ 50 nghìn. Cô bán hàng phải thối lại bao nhiêu nghìn?', 15,
                  hints=['50 − 35 = ?'], explain='50 − 35 = 15. Bảo đếm thêm từ 35 lên 50 bằng tờ 5 và tờ 10.'),
                S('mistake', 'choice', 'Khi An tính sai', 'An đưa thối 25 nghìn. Bạn phản hồi thế nào?', 'ask',
                  options=[o('wrong', '“Sai rồi, làm lại đi.”'), o('ask', '“Con đếm lại từ 35 lên 50 cho {title} nghe nhé, thử bằng tiền giấy.”'), o('other', 'Gọi bạn khác trả lời thay')],
                  hints=['Phản hồi tốt giúp học sinh tự tìm ra chỗ sai.'], explain='Hỏi lại quá trình giúp An tự phát hiện, không mất tự tin.')],
         perspectives=[V('An', '🧒', 'Con thích nhất lúc được làm cô bán hàng, đếm tiền thật đã tay!'), V('Cô Hạ', '👩‍🏫', 'Giao việc theo từng bạn tốn công chuẩn bị nhưng cả lớp đều được làm, không ai ngồi chờ.'), V('Mẹ của Bảo', '👩', 'Tối qua Bảo đòi đi chợ để tự tính tiền thối. Lần đầu con chủ động với Toán.')],
         lesson='Một mục tiêu rõ + nhiều con đường cho từng bạn = không ai bị bỏ lại.'),
    dict(id='les_story_roleplay', kind='lesson', emoji='📖', tag='Tiếng Việt', title='Tiết Tiếng Việt: kể chuyện bằng đóng vai', reward=20, xp=20, npcs=['vy', 'minh'],
         intro='Truyện “Chú thỏ và cái ô”. Mục tiêu: kể lại được câu chuyện theo thứ tự, dùng 2 từ nối.',
         facts=[dict(title='Truyện', text='Trời mưa, thỏ có một cái ô. Thỏ thấy nhím ướt nên rủ nhím đi chung. Sau đó ô bị gió thổi bay, cả hai cùng chạy vào gốc cây. Cuối cùng cầu vồng hiện ra.'),
                dict(title='Lưu ý lớp', text='Minh ngại nói trước lớp nhưng vẽ rất giỏi. Vy nói nhiều, hay kể lấn lượt bạn.')],
         steps=[S('seq', 'order', 'Trình tự câu chuyện', 'Xếp các tranh theo đúng diễn biến.', ['rain', 'share', 'wind', 'rainbow'],
                  items=[o('wind', 'Gió thổi bay ô'), o('rainbow', 'Cầu vồng hiện ra'), o('rain', 'Trời mưa, thỏ có ô'), o('share', 'Thỏ rủ nhím đi chung')],
                  hints=['Câu chuyện bắt đầu bằng trời mưa.'], explain='Thứ tự rõ giúp các bạn dùng từ nối: đầu tiên, sau đó, cuối cùng.'),
                S('link', 'multi', 'Từ nối nên dạy', 'Chọn các từ nối chỉ thứ tự thời gian.', ['first', 'then', 'finally'],
                  options=[o('first', 'Đầu tiên'), o('because', 'Vì vậy'), o('then', 'Sau đó'), o('finally', 'Cuối cùng'), o('but', 'Nhưng')],
                  hints=['Tìm những từ trả lời câu hỏi “lúc nào?”.'], explain='“Đầu tiên – sau đó – cuối cùng” là bộ từ nối trình tự.'),
                S('roles', 'match', 'Phân vai cho nhóm', 'Chọn vai giúp cả Minh và Vy cùng tham gia thoải mái.', dict(minh='draw', vy='narrator'),
                  left=[o('minh', 'Minh'), o('vy', 'Vy')],
                  right=[o('draw', 'Vẽ tranh bối cảnh rồi giơ tranh khi đến đoạn của mình'), o('narrator', 'Người dẫn chuyện, mỗi lượt nói 1 câu rồi chuyền mic')],
                  hints=['Minh mạnh về vẽ; Vy cần học cách nhường lượt.'], explain='Vai vẽ tranh cho Minh một cách tham gia không áp lực; mic chuyền giúp Vy nhường lượt.'),
                S('praise', 'choice', 'Nhận xét cuối tiết', 'Chọn lời nhận xét giúp các bạn tiến bộ.', 'specific',
                  options=[o('generic', '“Cả lớp giỏi lắm!”'), o('specific', '“Nhóm Minh dùng đúng “sau đó” khi chuyển tranh, lần sau thử thêm một câu tả cầu vồng nhé.”'), o('compare', '“Nhóm Vy hay hơn nhóm Minh.”')],
                  hints=['Nhận xét cụ thể: khen điều đã làm được + một bước tiếp theo.'], explain='Khen cụ thể và gợi ý một bước tiếp theo, không so sánh nhóm.')],
         perspectives=[V('Minh', '🧒', 'Con được giơ tranh cầu vồng con vẽ. Con nói được một câu luôn!'), V('Vy', '👧', 'Chuyền mic hơi khó vì con muốn nói nữa… nhưng nghe bạn kể cũng vui.'), V('Cô Hạ', '👩‍🏫', 'Đóng vai giúp các bạn ngại nói có chỗ đứng. Tiết sau mình mượn ý tưởng nhé.')],
         lesson='Mỗi học sinh cần một “cửa vào” khác nhau để dám nói.'),
    dict(id='les_science_float', kind='lesson', emoji='🔬', tag='Khoa học', title='Thí nghiệm: vật nổi, vật chìm', reward=20, xp=22, npcs=['an', 'bao'],
         intro='Tiết Tự nhiên & Xã hội: các nhóm dự đoán rồi thử thả đồ vật vào chậu nước.',
         facts=[dict(title='Đồ vật', text='Nắp chai nhựa, viên bi sắt, lá cây khô, đồng xu, miếng xốp, chìa khóa.'),
                dict(title='An toàn', text='Lớp dùng chậu nhựa. Sàn dễ trơn khi đổ nước. Nhóm 3 có một bạn hay chạy nhảy.')],
         steps=[S('safe', 'multi', 'Chuẩn bị an toàn', 'Chọn các việc cần làm trước khi phát nước.', ['towel', 'tray', 'rules'],
                  options=[o('towel', 'Để sẵn khăn lau và thảm chống trơn'), o('glass', 'Dùng cốc thủy tinh cho dễ nhìn'), o('tray', 'Đặt chậu trong khay, không bê đi lại'), o('rules', 'Thống nhất 3 quy tắc: không chạy, không té nước, giơ tay khi cần')],
                  hints=['Thủy tinh dễ vỡ khi học sinh nhỏ thao tác.'], explain='An toàn trước, thí nghiệm sau.'),
                S('order', 'order', 'Quy trình khoa học', 'Sắp xếp các bước của một thí nghiệm nhỏ.', ['guess', 'test', 'record', 'explain'],
                  items=[o('record', 'Ghi kết quả vào bảng'), o('explain', 'Cùng giải thích vì sao'), o('guess', 'Dự đoán nổi hay chìm'), o('test', 'Thả thử từng vật')],
                  hints=['Dự đoán phải có trước khi thử.'], explain='Dự đoán → thử → ghi lại → giải thích.'),
                S('sort', 'match', 'Kết quả', 'Ghép mỗi đồ vật với kết quả khi thả vào nước.', dict(cap='float', ball='sink', leaf='float', coin='sink', foam='float', key='sink'),
                  left=[o('cap', 'Nắp chai nhựa'), o('ball', 'Bi sắt'), o('leaf', 'Lá khô'), o('coin', 'Đồng xu'), o('foam', 'Miếng xốp'), o('key', 'Chìa khóa')],
                  right=[o('float', 'Nổi'), o('sink', 'Chìm')], hints=['Đồ kim loại nhỏ thường chìm; đồ nhẹ, xốp thường nổi.'], explain='Kết quả khớp với quan sát của các nhóm.'),
                S('wrong', 'choice', 'Khi dự đoán sai', 'Bảo đoán chìa khóa nổi nhưng nó chìm. Bạn nói gì?', 'scientist',
                  options=[o('laugh', 'Cười vui: “Sai rồi nha!”'), o('scientist', '“Nhà khoa học cũng đoán sai. Con thấy điều gì làm con bất ngờ?”'), o('skip', 'Bỏ qua, sang vật tiếp theo')],
                  hints=['Dự đoán sai là một phần của khoa học.'], explain='Biến dự đoán sai thành câu hỏi giúp Bảo thích khoa học hơn.')],
         perspectives=[V('Bảo', '🧒', 'Con đoán sai 3 lần mà {title} bảo con giống nhà khoa học. Mai con mang đồ ở nhà đến thử!'), V('Bác bảo vệ', '👴', 'Không có vũng nước nào ngoài hành lang. Lớp này dặn kỹ ghê.'), V('An', '🧒', 'Miếng xốp to mà nổi, đồng xu nhỏ mà chìm. Lạ ghê!')],
         lesson='Chuẩn bị an toàn kỹ thì trẻ mới được thử thật.'),
    dict(id='les_pe_heat', kind='lesson', emoji='🏃', tag='Thể dục', title='Tiết Thể dục ngày nắng nóng', reward=18, xp=18, npcs=['bao', 'vy'],
         intro='Sân trường 34°C lúc 9 giờ. Bài học: trò chơi chuyền bóng theo nhóm.',
         facts=[dict(title='Sức khỏe lớp', text='Vy có hen suyễn nhẹ, mang theo bình xịt trong cặp. Bảo quên mũ.'),
                dict(title='Sân', text='Nửa sân có bóng cây phượng, nửa kia nắng gắt.')],
         steps=[S('prep', 'multi', 'Trước khi ra sân', 'Chọn việc cần làm vì trời nóng.', ['water', 'shade', 'inhaler'],
                  options=[o('water', 'Nhắc cả lớp mang nước, nghỉ uống sau mỗi hiệp'), o('shade', 'Chơi ở nửa sân có bóng cây'), o('inhaler', 'Để bình xịt của Vy ở ghế giáo viên gần sân'), o('longer', 'Kéo dài tiết cho đủ vận động'), o('skip', 'Cho Vy ngồi lớp một mình')],
                  hints=['Trẻ có hen vẫn có thể tham gia, cần chuẩn bị đúng.'], explain='Nước, bóng râm và thuốc sẵn sàng giúp mọi bạn an toàn.'),
                S('flow', 'order', 'Nhịp bài học', 'Xếp nhịp vận động an toàn.', ['warm', 'game', 'water', 'cool'],
                  items=[o('cool', 'Thả lỏng, hít thở'), o('game', 'Trò chơi chuyền bóng'), o('warm', 'Khởi động khớp'), o('water', 'Nghỉ uống nước')],
                  hints=['Khởi động trước, thả lỏng sau cùng.'], explain='Khởi động → chơi → nghỉ nước → thả lỏng.'),
                S('hat', 'choice', 'Bảo quên mũ', 'Bạn xử lý thế nào?', 'role',
                  options=[o('sun', 'Cho Bảo đứng nắng để nhớ lần sau'), o('role', 'Cho Bảo làm trọng tài ở chỗ bóng râm lượt đầu, mượn mũ dự phòng của lớp'), o('home', 'Gọi phụ huynh mang mũ tới')],
                  hints=['Không dùng thời tiết để phạt.'], explain='Có mũ dự phòng và vai trò phù hợp, Bảo vẫn được tham gia.')],
         perspectives=[V('Vy', '👧', 'Con chơi được hết hiệp mà không mệt, biết bình xịt ở gần nên con yên tâm.'), V('Mẹ của Vy', '👩', '{Title} chủ động hỏi về bình xịt, tôi thấy an tâm gửi con.'), V('Bảo', '🧒', 'Làm trọng tài được thổi còi, vui hơn cả chơi!')],
         lesson='Hòa nhập nghĩa là chuẩn bị để mọi bạn cùng chơi, không loại ai ra.'),
    dict(id='les_english_song', kind='lesson', emoji='🎵', tag='Tiếng Anh', title='Tiếng Anh qua bài hát “Colors”', reward=18, xp=18, npcs=['vy', 'an'],
         intro='Học 5 từ màu sắc qua bài hát và trò chơi “chạm màu”.',
         facts=[dict(title='Từ mới', text='red, blue, yellow, green, pink'), dict(title='Thiết bị', text='Loa lớp hơi rè. Có thẻ màu và đồ vật trong lớp.')],
         steps=[S('match', 'match', 'Ghép từ với màu', 'Ghép từ tiếng Anh với màu đúng.', dict(red='do', blue='xanh_duong', yellow='vang', green='xanh_la', pink='hong'),
                  left=[o('red', 'red'), o('blue', 'blue'), o('yellow', 'yellow'), o('green', 'green'), o('pink', 'pink')],
                  right=[o('do', 'Đỏ'), o('xanh_duong', 'Xanh dương'), o('vang', 'Vàng'), o('xanh_la', 'Xanh lá'), o('hong', 'Hồng')], hints=['Yellow là màu của nắng.'], explain='Đúng hết 5 màu.'),
                S('game', 'choice', 'Trò chơi luyện tập', 'Chọn cách luyện tập giúp cả lớp nói được từ mới.', 'touch',
                  options=[o('copy', 'Chép mỗi từ 10 lần'), o('touch', '“Touch something blue!” – cả lớp chạm đồ vật màu đó và nói to'), o('test', 'Kiểm tra miệng từng bạn trước lớp')],
                  hints=['Trẻ nhỏ nhớ từ tốt hơn khi vận động và nói.'], explain='Vận động + nói giúp nhớ từ lâu hơn.'),
                S('speaker', 'choice', 'Loa bị rè', 'Loa rè giữa bài hát. Làm gì?', 'sing',
                  options=[o('stop', 'Dừng tiết để sửa loa'), o('sing', '{Title} hát chậm, cả lớp vỗ tay theo nhịp'), o('skip', 'Bỏ phần hát')],
                  hints=['Giữ mạch bài học quan trọng hơn thiết bị hoàn hảo.'], explain='Linh hoạt giữ được không khí tiết học.')],
         perspectives=[V('An', '🧒', '“Touch something green!” con chạm vào cây của lớp, bạn chạm vào áo {title}!'), V('Cô Hạ', '👩‍🏫', '{Title} hát chậm mà lớp theo tốt hơn cả loa. Tiết sau tôi báo sửa loa giúp.')],
         lesson='Thiết bị hỏng không làm hỏng tiết học nếu người dạy linh hoạt.'),
    dict(id='les_art_lantern', kind='lesson', emoji='🎨', tag='Mỹ thuật', title='Mỹ thuật: vẽ và cắt đèn lồng giấy', reward=18, xp=18, npcs=['minh', 'an'],
         intro='Chuẩn bị cho Trung thu: mỗi bạn làm một đèn lồng giấy nhỏ.',
         facts=[dict(title='Dụng cụ', text='Giấy màu, keo sữa, kéo đầu tròn, bút màu. Có một bộ kéo nhọn của giáo viên.'), dict(title='Lớp', text='Minh vẽ đẹp nhưng chê tranh mình xấu. An cắt còn vụng.')],
         steps=[S('tools', 'multi', 'Dụng cụ phát cho học sinh', 'Chọn dụng cụ an toàn để phát.', ['paper', 'glue', 'round', 'crayon'],
                  options=[o('paper', 'Giấy màu'), o('glue', 'Keo sữa'), o('round', 'Kéo đầu tròn'), o('sharp', 'Kéo nhọn'), o('crayon', 'Bút màu')],
                  hints=['Kéo nhọn chỉ để giáo viên dùng.'], explain='Dụng cụ an toàn cho lớp nhỏ.'),
                S('steps', 'order', 'Các bước làm đèn', 'Sắp xếp các bước.', ['fold', 'cut', 'draw', 'glue', 'handle'],
                  items=[o('glue', 'Dán mép thành ống'), o('draw', 'Vẽ trang trí'), o('fold', 'Gấp đôi tờ giấy'), o('handle', 'Gắn quai'), o('cut', 'Cắt các đường song song')],
                  hints=['Trang trí trước khi dán thành ống thì dễ hơn.'], explain='Gấp → cắt → vẽ → dán → gắn quai.'),
                S('praise', 'choice', 'Minh nói “tranh con xấu”', 'Bạn phản hồi thế nào?', 'process',
                  options=[o('best', '“Tranh con đẹp nhất lớp!”'), o('process', '“{Title} thấy con phối màu cam với xanh rất nổi. Con muốn thêm chi tiết gì nữa không?”'), o('ignore', 'Không nói gì để Minh tự vượt qua')],
                  hints=['Khen quá trình và chi tiết cụ thể, không xếp hạng.'], explain='Nhận xét cụ thể giúp Minh tự tin mà không cần so sánh.')],
         perspectives=[V('Minh', '🧒', '{Title} bảo màu cam xanh của con nổi. Con sẽ vẽ thêm ông trăng.'), V('An', '🧒', 'Con cắt lệch một đường nhưng đèn vẫn đứng được!')],
         lesson='Khen quá trình, không khen “giỏi nhất”.'),
    # ------------------------------------------------------------ grading
    dict(id='grade_math_quiz', kind='grading', emoji='✍️', tag='Chấm bài', title='Chấm bài kiểm tra 15 phút môn Toán', reward=16, xp=18, npcs=['bao', 'vy'],
         intro='Bài có 5 câu, mỗi câu 2 điểm. Chấm theo đáp án, không trừ điểm vì chữ xấu.',
         facts=[dict(title='Đáp án', text='C1: 47 · C2: 25 · C3: 60 · C4: 18 · C5: 9'),
                dict(title='Bài của Bảo', text='47 · 25 · 50 · 18 · 9 (chữ hơi nguệch ngoạc)'),
                dict(title='Bài của Vy', text='47 · 52 · 60 · 18 · 6'),
                dict(title='Bài của An', text='47 · 25 · 60 · 18 · 9')],
         steps=[S('scores', 'fields', 'Điểm từng bạn', 'Nhập điểm (thang 10) cho từng bài.', dict(bao=8, vy=6, an=10),
                  fields=[dict(id='bao', label='Bảo'), dict(id='vy', label='Vy'), dict(id='an', label='An')],
                  hints=['Đếm số câu đúng rồi nhân 2.', 'Chữ xấu không bị trừ điểm.'], explain='Bảo 8, Vy 6, An 10.'),
                S('comment', 'choice', 'Lời phê cho Vy', 'Vy viết 52 thay vì 25 ở câu 2 và sai câu 5.', 'specific',
                  options=[o('careless', '“Cẩu thả!”'), o('specific', '“Câu 2 con làm đúng cách nhưng viết ngược số; câu 5 thử vẽ sơ đồ nhé.”'), o('none', 'Chỉ ghi điểm, không phê')],
                  hints=['Lời phê tốt chỉ ra chỗ cần sửa và cách sửa.'], explain='Chỉ đúng lỗi và cách sửa giúp Vy tiến bộ lần sau.'),
                S('privacy', 'choice', 'Trả bài', 'Cách trả bài phù hợp?', 'private',
                  options=[o('rank', 'Đọc điểm từ cao xuống thấp trước lớp'), o('private', 'Trả bài riêng từng bạn, chữa chung các lỗi hay gặp'), o('board', 'Dán bảng điểm lên tường')],
                  hints=['Điểm số là thông tin riêng của từng học sinh.'], explain='Không công khai xếp hạng; chữa lỗi chung để cả lớp học.')],
         perspectives=[V('Bảo', '🧒', 'Chữ con xấu mà {title} không trừ điểm, con được 8!'), V('Vy', '👧', 'Con viết ngược số thật. Lần sau con đọc lại trước khi nộp.'), V('Cô Lan (phụ huynh)', '👩', 'Lời phê cụ thể, tôi biết kèm con chỗ nào.')],
         lesson='Chấm công bằng: đúng đáp án, không chấm theo nét chữ hay cảm tình.'),
    dict(id='grade_essay', kind='grading', emoji='📝', tag='Chấm bài', title='Chấm bài văn “Tả con vật em yêu”', reward=16, xp=18, npcs=['minh', 'an'],
         intro='Chấm theo 3 tiêu chí: Ý (có mở, thân, kết), Câu (câu đủ ý), Chính tả (≤2 lỗi là tốt).',
         facts=[dict(title='Bài của Minh', text='Có đủ mở bài – thân bài – kết bài. Nhiều câu dài hay. 5 lỗi chính tả.'),
                dict(title='Bài của An', text='Chỉ tả hình dáng, không có kết bài. Câu ngắn đủ ý. 1 lỗi chính tả.')],
         steps=[S('rubric', 'fields', 'Đánh giá theo tiêu chí', 'Chọn mức cho từng tiêu chí.', dict(minh_y='good', minh_ct='work', an_y='work', an_ct='good'),
                  fields=[dict(id='minh_y', label='Minh · Ý', options=[o('good', 'Tốt'), o('work', 'Cần cố gắng')]), dict(id='minh_ct', label='Minh · Chính tả', options=[o('good', 'Tốt'), o('work', 'Cần cố gắng')]),
                          dict(id='an_y', label='An · Ý', options=[o('good', 'Tốt'), o('work', 'Cần cố gắng')]), dict(id='an_ct', label='An · Chính tả', options=[o('good', 'Tốt'), o('work', 'Cần cố gắng')])],
                  hints=['So từng bài với đúng tiêu chí, không theo ấn tượng chung.'], explain='Mỗi bạn có điểm mạnh riêng: Minh về ý, An về chính tả.'),
                S('next', 'match', 'Bước tiếp theo cho từng bạn', 'Ghép mỗi bạn với gợi ý phù hợp.', dict(minh='spell', an='end'),
                  left=[o('minh', 'Minh'), o('an', 'An')], right=[o('spell', 'Lập sổ tay 5 từ hay viết sai'), o('end', 'Thêm 2 câu kết: em yêu con vật thế nào')],
                  hints=['Gợi ý nhắm vào tiêu chí còn yếu.'], explain='Mỗi gợi ý nhắm đúng một điểm cần cải thiện.')],
         perspectives=[V('Minh', '🧒', 'Con viết hay mà sai chính tả nhiều. Con làm sổ tay rồi!'), V('An', '🧒', 'Con chưa biết kết bài là gì, giờ biết rồi.')],
         lesson='Tiêu chí rõ giúp chấm công bằng và lời phê có ích.'),
    # ------------------------------------------------------------ meetings
    dict(id='meet_bao_parent', kind='meeting', emoji='🤝', tag='Phụ huynh', title='Gặp riêng mẹ của Bảo', reward=16, xp=20, npcs=['bao', 'lan'],
         intro='Bảo hay quên làm bài về nhà. Mẹ Bảo làm ca đêm, lo lắng và hơi phòng thủ.',
         facts=[dict(title='Quan sát 2 tuần', text='Bảo quên bài 5/10 buổi. Trên lớp Bảo hăng hái, giúp bạn dọn lớp, tính nhẩm nhanh.'),
                dict(title='Hoàn cảnh', text='Mẹ đi làm ca đêm, bà ngoại trông Bảo buổi tối, bà không biết chữ nhiều.')],
         steps=[S('agenda', 'order', 'Trình tự cuộc gặp', 'Sắp xếp để cuộc gặp tích cực và hiệu quả.', ['strength', 'fact', 'listen', 'plan', 'follow'],
                  items=[o('plan', 'Cùng đề xuất kế hoạch nhỏ'), o('listen', 'Hỏi và lắng nghe hoàn cảnh ở nhà'), o('strength', 'Kể điểm mạnh của Bảo'), o('follow', 'Hẹn trao đổi lại sau 2 tuần'), o('fact', 'Nêu sự việc cụ thể: quên bài 5/10 buổi')],
                  hints=['Mở đầu bằng điều tích cực; lắng nghe trước khi đề xuất.'], explain='Điểm mạnh → sự việc → lắng nghe → kế hoạch → hẹn lại.'),
                S('plan', 'choice', 'Kế hoạch phù hợp', 'Chọn giải pháp khả thi với hoàn cảnh nhà Bảo.', 'checklist',
                  options=[o('more', 'Giao thêm bài để Bảo quen'), o('checklist', 'Sổ tay hình ảnh 3 việc buổi tối, bà chỉ cần đánh dấu; {title} nhắc cuối giờ'), o('punish', 'Phạt đứng khi quên bài')],
                  hints=['Giải pháp phải làm được với bà ngoại buổi tối.'], explain='Sổ tay hình ảnh vừa sức với bà, Bảo tự chịu trách nhiệm.'),
                S('private', 'choice', 'Mẹ Bảo hỏi', '“Con Vy bàn bên học có giỏi không {title}?”', 'decline',
                  options=[o('tell', 'Kể điểm của Vy để mẹ Bảo tham khảo'), o('decline', '“{Title} chỉ trao đổi về Bảo thôi ạ, mỗi bạn có hành trình riêng.”')],
                  hints=['Thông tin học sinh khác là riêng tư.'], explain='Giữ riêng tư cho học sinh khác và không so sánh.')],
         perspectives=[V('Mẹ của Bảo', '👩', 'Tôi tưởng bị gọi lên để trách. Hóa ra {title} kể Bảo giúp bạn dọn lớp… tôi suýt khóc.'), V('Bà ngoại Bảo', '👵', 'Sổ có hình, bà nhìn là hiểu, tối nào bà cũng đánh dấu với cháu.'), V('Bảo', '🧒', 'Con được tự tích sổ, đủ 5 ngày {title} cho dán sao.')],
         lesson='Hợp tác với gia đình bắt đầu từ lắng nghe hoàn cảnh thật.'),
    dict(id='meet_parents_all', kind='meeting', emoji='🏫', tag='Phụ huynh', title='Họp phụ huynh đầu kỳ', reward=22, xp=24, npcs=['lan', 'ha'], months=[0, 4, 8],
         intro='30 phụ huynh, 60 phút. Có đề xuất lập quỹ lớp và câu hỏi về điểm số.',
         facts=[dict(title='Đề xuất quỹ lớp', text='Ban đại diện đề xuất mỗi nhà góp 200 nghìn/năm cho hoạt động lớp.'),
                dict(title='Quy định của trường', text='Quỹ lớp là tự nguyện, phải công khai thu – chi, giáo viên không trực tiếp giữ tiền.')],
         steps=[S('agenda', 'order', 'Chương trình họp', 'Sắp xếp chương trình.', ['welcome', 'report', 'plan', 'fund', 'qa'],
                  items=[o('qa', 'Hỏi đáp'), o('plan', 'Kế hoạch học kỳ'), o('welcome', 'Chào mừng, giới thiệu'), o('fund', 'Bàn về quỹ lớp'), o('report', 'Tình hình chung của lớp')],
                  hints=['Hỏi đáp nên ở cuối.'], explain='Một chương trình rõ giúp buổi họp đúng giờ.'),
                S('fund', 'multi', 'Nguyên tắc quỹ lớp', 'Chọn các nguyên tắc đúng.', ['volunteer', 'public', 'rep'],
                  options=[o('volunteer', 'Tự nguyện, không ghi tên nhà chưa góp'), o('public', 'Công khai sổ thu – chi mỗi tháng'), o('rep', 'Ban đại diện giữ quỹ, giáo viên không giữ tiền'), o('must', 'Bắt buộc mọi nhà góp bằng nhau'), o('gift', 'Dùng quỹ mua quà cho giáo viên')],
                  hints=['Đọc mục “Quy định”.'], explain='Tự nguyện, minh bạch, giáo viên không giữ tiền.'),
                S('scores', 'choice', 'Phụ huynh xin bảng điểm cả lớp', 'Một phụ huynh muốn xem điểm của tất cả học sinh.', 'own',
                  options=[o('share', 'Gửi bảng điểm cả lớp vào nhóm chat'), o('own', 'Mỗi phụ huynh nhận điểm của con mình qua sổ liên lạc'), o('top', 'Chỉ công bố top 5')],
                  hints=['Quyền riêng tư của học sinh.'], explain='Mỗi gia đình nhận thông tin của con mình.')],
         perspectives=[V('Cô Lan (phụ huynh)', '👩', 'Cuộc họp đúng giờ, quỹ rõ ràng. Nhà tôi tự nguyện góp mà vui.'), V('Một phụ huynh khó khăn', '👨', 'Không ai ghi tên nhà chưa góp, tôi không thấy ngại khi đi họp.'), V('Cô Hạ', '👩‍🏫', 'Không giữ tiền quỹ là cách tự bảo vệ mình, {title} làm đúng đấy.')],
         lesson='Minh bạch và tự nguyện giữ được niềm tin giữa trường và nhà.'),
    # ------------------------------------------------------------ events
    dict(id='ev_trung_thu', kind='event', emoji='🏮', tag='Trung thu', title='Tổ chức Trung thu cho lớp', reward=30, xp=35, npcs=['minh', 'an', 'vy', 'bao', 'lan'], months=[0, 1],
         intro='Đêm hội trăng rằm của lớp: rước đèn, phá cỗ, văn nghệ. Quỹ hoạt động: 300 nghìn.',
         facts=[dict(title='Báo giá', text='Đèn lồng LED: 8 nghìn/cái. Bánh trung thu mini: 6 nghìn/cái. Trái cây mâm cỗ: 60 nghìn. Lớp có 20 bạn.'),
                dict(title='Sức khỏe', text='An dị ứng đậu phộng. Bánh thập cẩm có đậu phộng; bánh đậu xanh thì không.'),
                dict(title='Hoàn cảnh', text='Hai bạn trong lớp chưa có đèn và gia đình không muốn góp thêm.')],
         steps=[S('budget', 'number', 'Tính chi phí', '20 đèn LED + 20 bánh mini + 1 mâm trái cây hết bao nhiêu nghìn?', 340,
                  hints=['20×8 + 20×6 + 60'], explain='160 + 120 + 60 = 340 nghìn, vượt quỹ 40 nghìn.'),
                S('fix', 'choice', 'Vượt quỹ 40 nghìn', 'Chọn cách cân đối.', 'craft',
                  options=[o('ask', 'Thu thêm mỗi nhà 2 nghìn'), o('craft', 'Chỉ mua 15 đèn; 5 đèn còn lại cả lớp tự làm từ tiết Mỹ thuật'), o('cheap', 'Mua đèn nến rẻ hơn')],
                  hints=['Có tiết Mỹ thuật làm đèn giấy; nến dễ gây cháy.'], explain='Tự làm đèn vừa tiết kiệm vừa ý nghĩa.'),
                S('safe', 'multi', 'An toàn đêm hội', 'Chọn các việc cần làm.', ['led', 'peanut', 'adults', 'count'],
                  options=[o('led', 'Chỉ dùng đèn LED, không dùng nến'), o('peanut', 'Mua bánh đậu xanh cho An, dán tên'), o('adults', 'Mỗi nhóm 5 bạn có một người lớn đi kèm khi rước đèn'), o('count', 'Điểm danh trước và sau khi rước đèn'), o('fire', 'Đốt pháo hoa nhỏ cho vui')],
                  hints=['Đọc lại mục Sức khỏe.', 'Pháo không an toàn cho trẻ nhỏ.'], explain='Đèn LED, bánh an toàn, người lớn đi kèm và điểm danh.'),
                S('flow', 'order', 'Chương trình', 'Sắp xếp chương trình đêm hội.', ['gather', 'parade', 'feast', 'show', 'clean'],
                  items=[o('show', 'Văn nghệ'), o('clean', 'Cùng dọn dẹp'), o('parade', 'Rước đèn quanh sân'), o('gather', 'Tập trung, điểm danh'), o('feast', 'Phá cỗ')],
                  hints=['Bắt đầu bằng điểm danh, kết thúc bằng dọn dẹp.'], explain='Điểm danh → rước đèn → phá cỗ → văn nghệ → dọn dẹp.'),
                S('include', 'choice', 'Hai bạn chưa có đèn', 'Làm sao để hai bạn không bị lạc lõng?', 'quiet',
                  options=[o('announce', 'Thông báo trước lớp để các bạn góp tặng'), o('quiet', 'Đèn tự làm của lớp được phát cho mọi bạn cùng lúc, không nêu tên ai'), o('skip', 'Để hai bạn cầm cờ thay đèn')],
                  hints=['Giữ thể diện cho học sinh.'], explain='Phát chung cho mọi người, không ai bị chú ý riêng.')],
         perspectives=[V('An', '🧒', 'Bánh của con có dán tên, con yên tâm ăn cùng các bạn!'), V('Một bạn nhận đèn tự làm', '🧒', 'Đèn con cầm là đèn cả lớp làm, đẹp nhất!'), V('Cô Lan (phụ huynh)', '👩', 'Không có nến, có người lớn đi kèm, tôi đi theo mà không phải lo.'), V('Bác bảo vệ', '👴', 'Năm nay dọn dẹp xong trước 8 giờ, lớp này chu đáo.')],
         lesson='Một đêm hội vui là đêm hội mọi bạn đều được an toàn và được tham gia.'),
    dict(id='ev_birthday_month', kind='event', emoji='🎂', tag='Sinh nhật', title='Sinh nhật chung các bạn trong tháng', reward=18, xp=22, npcs=['minh', 'vy'], monthly=True,
         intro='Tháng này có 3 bạn sinh nhật, trong đó có Minh (rất ngại đứng trước đám đông).',
         facts=[dict(title='Quy định của lớp', text='Không khuyến khích quà đắt tiền; lớp tổ chức sinh nhật chung mỗi tháng.'),
                dict(title='Minh', text='Minh thích vẽ và mèo, rất ngại bị hát chúc mừng một mình.')],
         steps=[S('format', 'choice', 'Hình thức', 'Chọn hình thức tổ chức.', 'group',
                  options=[o('each', 'Mỗi bạn một tiệc riêng, bố mẹ mang bánh kem'), o('group', 'Sinh nhật chung 15 phút cuối giờ: cả lớp làm thiệp tặng 3 bạn'), o('gift', 'Mỗi bạn góp tiền mua quà')],
                  hints=['Đọc quy định lớp.'], explain='Sinh nhật chung vừa ấm áp vừa công bằng.'),
                S('minh', 'choice', 'Cho Minh thoải mái', 'Làm sao để Minh vui mà không ngại?', 'choice',
                  options=[o('stage', 'Mời Minh lên bục để cả lớp hát'), o('choice', 'Hỏi riêng Minh trước: con muốn đứng cùng 2 bạn hay ngồi tại chỗ nhận thiệp?'), o('skip', 'Bỏ qua Minh cho khỏi ngại')],
                  hints=['Tôn trọng lựa chọn của học sinh.'], explain='Hỏi trước giúp Minh được chúc mừng theo cách mình thoải mái.'),
                S('cards', 'order', 'Hoạt động làm thiệp', 'Sắp xếp các bước.', ['idea', 'make', 'write', 'give'],
                  items=[o('give', 'Trao thiệp'), o('write', 'Viết một lời chúc cụ thể'), o('idea', 'Nghĩ điều mình quý ở bạn'), o('make', 'Gấp và trang trí thiệp')],
                  hints=['Nghĩ ý trước khi làm và viết.'], explain='Ý tưởng → làm thiệp → viết lời chúc → trao.')],
         perspectives=[V('Minh', '🧒', 'Con được ngồi tại chỗ mà nhận 20 cái thiệp, có cái vẽ mèo!'), V('Mẹ của Minh', '👩', 'Con về kể mãi, không phải lo mua bánh kem cho cả lớp.'), V('Vy', '👧', 'Con viết “Minh vẽ mèo đẹp nhất trái đất”.')],
         lesson='Chúc mừng đúng cách là chúc mừng theo cách người được chúc thấy thoải mái.'),
    dict(id='ev_teachers_day', kind='event', emoji='💐', tag='20/11', title='Ngày Nhà giáo Việt Nam 20/11', reward=22, xp=26, npcs=['ha', 'lan'], months=[2],
         intro='Lớp chuẩn bị văn nghệ; một số phụ huynh muốn tặng quà {title} giáo.',
         facts=[dict(title='Tin nhắn phụ huynh', text='Một phụ huynh muốn tặng phong bì “cảm ơn {title}”. Nhóm khác đề xuất cả lớp làm báo tường.'),
                dict(title='Quy định của trường', text='Giáo viên không nhận tiền, quà giá trị từ phụ huynh.')],
         steps=[S('gift', 'choice', 'Phong bì từ phụ huynh', 'Bạn trả lời thế nào?', 'decline',
                  options=[o('accept', 'Nhận vì là tấm lòng'), o('decline', 'Cảm ơn và từ chối nhẹ nhàng, gợi ý con viết một tấm thiệp'), o('fund', 'Nhận rồi đưa vào quỹ lớp')],
                  hints=['Đọc quy định.'], explain='Từ chối khéo giữ được sự công bằng với mọi học sinh.'),
                S('program', 'order', 'Chương trình chào mừng', 'Sắp xếp.', ['open', 'poem', 'song', 'paper', 'thanks'],
                  items=[o('song', 'Hát tập thể'), o('thanks', '{Title} cảm ơn và chụp ảnh chung'), o('paper', 'Giới thiệu báo tường'), o('open', 'Lớp trưởng mở màn'), o('poem', 'Đọc thơ')],
                  hints=['Mở màn trước, cảm ơn sau cùng.'], explain='Mở màn → thơ → hát → báo tường → cảm ơn.'),
                S('photo', 'choice', 'Đăng ảnh lên mạng', 'Phụ huynh xin đăng ảnh cả lớp lên trang cá nhân.', 'consent',
                  options=[o('ok', 'Cứ đăng'), o('consent', 'Chỉ đăng ảnh các bạn có phụ huynh đồng ý, không ghi tên trường – lớp'), o('never', 'Cấm chụp ảnh')],
                  hints=['Ảnh trẻ em cần sự đồng ý của gia đình.'], explain='Đồng ý của gia đình và hạn chế thông tin nhận diện.')],
         perspectives=[V('Phụ huynh định tặng phong bì', '👨', '{Title} từ chối khéo quá, tôi không thấy ngượng. Con tôi làm thiệp cả tối.'), V('Cô Hạ', '👩‍🏫', 'Giữ được nguyên tắc mà vẫn ấm áp — đó là điều khó nhất nghề mình.'), V('Học sinh', '🧒', 'Báo tường có tranh của cả lớp, {title} cười suốt.')],
         lesson='Tấm lòng quý nhất là tấm lòng mọi gia đình đều có thể trao.'),
    dict(id='ev_sports_day', kind='event', emoji='🏅', tag='Hội khỏe', title='Hội khỏe Phù Đổng của lớp', reward=22, xp=26, npcs=['bao', 'vy', 'an'], months=[3],
         intro='Chia 20 bạn thành các đội thi kéo co và chạy tiếp sức.',
         facts=[dict(title='Lớp', text='20 bạn, có 1 bạn đang bó bột tay (Nam). Vy có hen suyễn nhẹ.'), dict(title='Luật', text='Mỗi đội cần số người bằng nhau.')],
         steps=[S('teams', 'number', 'Chia đội', 'Nam làm trọng tài nên còn 19 bạn thi. {Title} tham gia cùng cho đủ 20 người, chia đội 5 người. Có mấy đội?', 4,
                  hints=['20 ÷ 5'], explain='20 ÷ 5 = 4 đội, đội nào cũng đủ người.'),
                S('fair', 'choice', 'Cách chia công bằng', 'Chọn cách chia đội.', 'mix',
                  options=[o('captain', 'Hai bạn khỏe nhất tự chọn đội'), o('mix', '{Title} chia trộn theo danh sách, đổi thứ tự bốc thăm'), o('friends', 'Bạn thân vào cùng đội')],
                  hints=['Tránh để bạn nào bị chọn cuối cùng.'], explain='Chia trộn tránh cảm giác bị chọn sau cùng.'),
                S('roles', 'match', 'Vai trò đặc biệt', 'Ghép bạn với vai phù hợp.', dict(nam='referee', vy='relay_short'),
                  left=[o('nam', 'Nam (bó bột tay)'), o('vy', 'Vy (hen nhẹ)')], right=[o('referee', 'Trọng tài bấm giờ'), o('relay_short', 'Chạy chặng ngắn nhất, có nghỉ uống nước')],
                  hints=['Ai cũng có một vai.'], explain='Mọi bạn đều có mặt trong hội khỏe.')],
         perspectives=[V('Nam', '🧒', 'Con được bấm giờ bằng đồng hồ thật của {title}!'), V('Vy', '👧', 'Chặng ngắn thôi nhưng con về đích trước bạn!'), V('Bảo', '🧒', 'Đội con thua kéo co mà vẫn vui vì {title} bốc thăm, không ai bị chọn cuối.')],
         lesson='Công bằng trong thể thao bắt đầu từ cách chia đội.'),
    dict(id='ev_tet', kind='event', emoji='🧧', tag='Tết', title='Góc Tết của lớp: gói bánh chưng mini', reward=26, xp=30, npcs=['ha', 'an', 'minh'], months=[4, 5],
         intro='Lớp làm “Góc Tết”: gói bánh chưng mini, viết lời chúc, kể phong tục mỗi nhà.',
         facts=[dict(title='Nguyên liệu', text='Lá dong đã rửa, gạo nếp ngâm, đậu xanh, thịt (có bạn ăn chay), lạt buộc. Luộc bánh do nhà bếp trường phụ trách.'),
                dict(title='Lớp', text='Một bạn nhà theo đạo, không đón Tết theo kiểu thờ cúng; một bạn ăn chay.')],
         steps=[S('safe', 'multi', 'Phân công an toàn', 'Chọn các phân công đúng.', ['wash', 'kitchen', 'veg', 'knife'],
                  options=[o('wash', 'Cả lớp rửa tay, đeo tạp dề'), o('kitchen', 'Nhà bếp trường luộc bánh, học sinh không đến gần nồi'), o('veg', 'Chuẩn bị nhân không thịt cho bạn ăn chay'), o('knife', 'Chỉ người lớn dùng dao cắt lạt'), o('fire', 'Cho các bạn tự nhóm bếp than')],
                  hints=['Trẻ không thao tác lửa, dao và nồi nóng.'], explain='An toàn và tôn trọng khẩu phần của từng bạn.'),
                S('steps', 'order', 'Các bước gói bánh', 'Sắp xếp.', ['leaf', 'rice1', 'bean', 'rice2', 'tie'],
                  items=[o('tie', 'Buộc lạt'), o('bean', 'Thêm đậu (và thịt nếu có)'), o('leaf', 'Xếp lá vào khuôn'), o('rice2', 'Phủ lớp gạo trên'), o('rice1', 'Rải lớp gạo dưới')],
                  hints=['Gạo – đậu – gạo.'], explain='Lá → gạo → đậu → gạo → buộc lạt.'),
                S('customs', 'choice', 'Phần kể phong tục', 'Tổ chức phần “Tết nhà em” thế nào?', 'share',
                  options=[o('one', 'Chỉ giới thiệu một kiểu Tết “chuẩn”'), o('share', 'Mỗi bạn kể một điều nhà mình làm dịp năm mới, ai muốn thì kể'), o('skip', 'Bỏ phần kể cho nhanh')],
                  hints=['Lớp có nhiều gia đình khác nhau.'], explain='Tôn trọng mỗi gia đình một cách đón năm mới.'),
                S('lixi', 'choice', 'Lì xì', 'Phụ huynh hỏi có nên lì xì các con trên lớp.', 'wish',
                  options=[o('money', 'Mỗi bạn một phong bao tiền'), o('wish', 'Phong bao lời chúc do các bạn tự viết tặng nhau'), o('top', 'Lì xì cho bạn học giỏi')],
                  hints=['Không mang tiền vào lớp.'], explain='Phong bao lời chúc giữ niềm vui mà không so bì.')],
         perspectives=[V('Bạn ăn chay', '🧒', 'Bánh của con nhân đậu, {title} dán hình lá xanh cho dễ nhận!'), V('Bạn nhà theo đạo', '👧', 'Con kể nhà con đi lễ đầu năm, các bạn nghe chăm chú lắm.'), V('Cô Hạ', '👩‍🏫', 'Bánh méo một chút nhưng lớp hiểu thêm về nhau, vậy là đủ.')],
         lesson='Mùa lễ hội là dịp để hiểu và tôn trọng những gia đình khác mình.'),
    dict(id='ev_field_trip', kind='event', emoji='🚌', tag='Dã ngoại', title='Dã ngoại nông trại rau sạch', reward=30, xp=35, npcs=['an', 'bao', 'lan'], months=[6, 7],
         intro='Đi xe 30 phút, 32 học sinh, thăm vườn rau và trại gà.',
         facts=[dict(title='Quy định của trường', text='Mỗi người lớn phụ trách tối đa 8 học sinh. Bắt buộc có giấy đồng ý của phụ huynh.'),
                dict(title='Sức khỏe', text='An dị ứng ong đốt (có bút tiêm dự phòng). Bảo hay say xe.'),
                dict(title='Giấy đồng ý', text='Đã nhận 30/32 giấy. Hai bạn chưa nộp.')],
         steps=[S('adults', 'number', 'Số người lớn', 'Cần tối thiểu bao nhiêu người lớn đi kèm?', 4, hints=['32 ÷ 8'], explain='32 ÷ 8 = 4 người lớn.'),
                S('consent', 'choice', 'Hai bạn chưa nộp giấy', 'Xử lý thế nào?', 'call',
                  options=[o('go', 'Cứ cho đi, về rồi tính'), o('call', 'Gọi phụ huynh xác nhận trước ngày đi; chưa có giấy thì bạn ở lại lớp bên cạnh học cùng'), o('ban', 'Mắng hai bạn trước lớp')],
                  hints=['Giấy đồng ý là bắt buộc.'], explain='Liên hệ gia đình sớm, có phương án an toàn cho bạn chưa có giấy.'),
                S('kit', 'multi', 'Túi chuẩn bị', 'Chọn những thứ cần mang.', ['firstaid', 'epipen', 'bag', 'list', 'water'],
                  options=[o('firstaid', 'Túi sơ cứu'), o('epipen', 'Bút tiêm dự phòng của An, người lớn nhóm An biết cách dùng'), o('bag', 'Túi nôn và ghế đầu xe cho Bảo'), o('list', 'Danh sách học sinh + số điện thoại phụ huynh'), o('water', 'Nước uống'), o('candy', 'Kẹo cho cả lớp ăn trên xe')],
                  hints=['Đọc mục Sức khỏe.'], explain='Chuẩn bị theo nhu cầu thật của từng bạn.'),
                S('count', 'order', 'Điểm danh', 'Sắp xếp các thời điểm điểm danh bắt buộc.', ['bus_go', 'arrive', 'lunch', 'bus_back', 'school'],
                  items=[o('lunch', 'Trước bữa trưa'), o('school', 'Về đến trường, bàn giao phụ huynh'), o('bus_go', 'Lên xe đi'), o('bus_back', 'Lên xe về'), o('arrive', 'Xuống xe tại nông trại')],
                  hints=['Mỗi lần chuyển địa điểm đều điểm danh.'], explain='Điểm danh ở mỗi lần di chuyển.')],
         perspectives=[V('An', '🧒', 'Có ong bay qua, cô Lan nhóm con bình tĩnh dẫn con ra xa. Con không sợ nữa.'), V('Bảo', '🧒', 'Ngồi ghế đầu con không say xe, còn được xem tài xế lái.'), V('Chủ nông trại', '👨‍🌾', 'Đoàn 32 bạn mà đi đâu cũng đếm đủ, tôi yên tâm cho các cháu vào chuồng gà.')],
         lesson='Chuyến đi vui nhất là chuyến đi được chuẩn bị kỹ nhất.'),
    dict(id='ev_year_end', kind='event', emoji='🎓', tag='Tổng kết', title='Lễ tổng kết năm học', reward=30, xp=40, npcs=['minh', 'an', 'vy', 'bao', 'lan', 'ha'], months=[8],
         intro='Mỗi học sinh nhận một giấy khen riêng về điểm mạnh của mình, không chỉ học sinh giỏi.',
         facts=[dict(title='Ghi chép cả năm', text='Minh: tiến bộ khi nói trước lớp, vẽ đẹp. An: thí nghiệm hăng say. Vy: đọc to rõ ràng, biết nhường lượt hơn. Bảo: chăm chỉ tích sổ tay, hay giúp bạn.')],
         steps=[S('awards', 'match', 'Giấy khen riêng', 'Ghép mỗi bạn với giấy khen xứng đáng.', dict(minh='brave', an='scientist', vy='reader', bao='helper'),
                  left=[o('minh', 'Minh'), o('an', 'An'), o('vy', 'Vy'), o('bao', 'Bảo')],
                  right=[o('brave', 'Giấy khen “Dám nói – dám vẽ”'), o('scientist', 'Giấy khen “Nhà khoa học nhí”'), o('reader', 'Giấy khen “Giọng đọc truyền cảm”'), o('helper', 'Giấy khen “Người bạn tốt bụng”')],
                  hints=['Đọc ghi chép cả năm.'], explain='Mỗi bạn được ghi nhận điều thật sự của mình.'),
                S('letter', 'choice', 'Thư gửi phụ huynh', 'Nội dung chính của thư cuối năm?', 'growth',
                  options=[o('rank', 'Bảng xếp hạng cả lớp'), o('growth', 'Tiến bộ riêng của con + gợi ý hoạt động hè'), o('fees', 'Nhắc nộp phí năm sau')],
                  hints=['Tập trung vào từng em.'], explain='Thư cá nhân hóa giúp gia đình tiếp tục đồng hành.')],
         perspectives=[V('Bảo', '🧒', 'Lần đầu con được giấy khen! “Người bạn tốt bụng” — con treo ở đầu giường.'), V('Mẹ của Minh', '👩', 'Minh cầm giấy khen “Dám nói” lên đọc cảm ơn {title}, cả nhà bất ngờ.'), V('Cô Hạ', '👩‍🏫', 'Một năm nhìn lại, mình nhớ từng đứa bằng điều riêng của nó. Nghề này đáng lắm.')],
         lesson='Mỗi đứa trẻ đều có một điều đáng được khen, việc của giáo viên là nhìn thấy nó.'),
]
# ------------------------------------------------------------ v0.5 additions
ACTIVITIES += [
    dict(id='meet_inbox', kind='meeting', emoji='💬', tag='Nhóm lớp', title='Nhóm chat phụ huynh “nổ” lúc tối', reward=18, xp=22, npcs=['lan', 'vy', 'bao'],
         intro='21 giờ, nhóm chat của lớp có 40 tin nhắn mới. Ba chuyện cùng lúc, mỗi phụ huynh một tính.',
         facts=[dict(title='Tin 1 · Mẹ Vy (lo lắng, nhắn liền năm tin)', text='Đăng ảnh cánh tay Vy bị xước, kèm dòng: “Bạn Tú lớp mình cào con tôi. Phụ huynh bạn Tú đâu?”'),
                dict(title='Tin 2 · Bố Tú (thẳng tính, nhắn cụt)', text='“Con tôi bảo không làm. {Title} xem lại đi.”'),
                dict(title='Tin 3 · Một phụ huynh bán hàng', text='Đăng quảng cáo váy trẻ em, xin mọi người ủng hộ.'),
                dict(title='Bà nội Khoa', text='Không rành nhắn tin, vừa gửi một tin thoại dài 3 phút nghe không rõ.')],
         steps=[S('first', 'choice', 'Việc đầu tiên', 'Tin nào cần xử lý trước?', 'photo',
                  options=[o('ads', 'Xóa quảng cáo cho gọn nhóm'), o('photo', 'Tin có ảnh và tên một bạn nhỏ bị gọi đích danh'), o('voice', 'Nghe tin thoại của bà nội Khoa')],
                  hints=['Việc nào đang làm tổn thương một đứa trẻ ngay trước mặt 40 gia đình?'], explain='Một bạn nhỏ bị nêu tên công khai là việc cần dừng lại trước tiên.'),
                S('reply', 'choice', 'Trả lời trong nhóm', 'Viết gì vào nhóm chung?', 'private',
                  options=[o('judge', '“Tú đúng là hay nghịch, {title} sẽ phạt.”'), o('private', '“{Title} đã nhận tin. Chuyện của hai bạn nhỏ, {title} xin phép gọi riêng từng gia đình tối nay.”'), o('silent', 'Không trả lời, chờ sáng mai')],
                  hints=['Chưa rõ đúng sai; chuyện riêng của trẻ không bàn giữa nhóm đông người.'], explain='Ghi nhận, không phán xét, chuyển sang trao đổi riêng.'),
                S('tone', 'match', 'Mỗi phụ huynh một cách nói', 'Ghép phụ huynh với cách liên lạc hợp nhất.', dict(vy='warm', tu='facts', khoa='call'),
                  left=[o('vy', 'Mẹ Vy (lo lắng)'), o('tu', 'Bố Tú (thẳng tính)'), o('khoa', 'Bà nội Khoa (không rành nhắn tin)')],
                  right=[o('warm', 'Hỏi thăm vết xước trước, hẹn kể lại sau khi hỏi hai bạn'), o('facts', 'Nói ngắn gọn điều đã biết, điều sẽ làm và giờ báo lại'), o('call', 'Gọi điện nghe trực tiếp, nói chậm và rõ')],
                  hints=['Người lo cần được trấn an, người thẳng tính cần thông tin rõ.'], explain='Cùng một sự thật, mỗi người cần một cách nói để nghe được.'),
                S('rules', 'multi', 'Nội quy ghim đầu nhóm', 'Chọn các quy tắc nên ghim.', ['nophoto', 'noads', 'private', 'hours'],
                  options=[o('nophoto', 'Không đăng ảnh, tên con người khác khi có chuyện'), o('noads', 'Không quảng cáo buôn bán'), o('private', 'Chuyện riêng của từng bạn trao đổi riêng với giáo viên'), o('hours', 'Giáo viên trả lời trong giờ 7h–20h, trừ việc khẩn'), o('scores', 'Mỗi tuần đăng bảng điểm cả lớp')],
                  hints=['Điểm số cũng là thông tin riêng.'], explain='Nội quy rõ giúp nhóm lớp là nơi báo tin, không phải nơi xử án.')],
         perspectives=[V('Mẹ của Vy', '👩', '{Title} gọi cho tôi, hỏi vết xước trước rồi mới kể. Hóa ra hai đứa giành bút, cả hai cùng sai.'), V('Bố của Tú', '👨', '{Title} nói rõ ràng, không bênh ai. Tôi xin gỡ tin nhắn nóng nảy.'), V('Bà nội Khoa', '👵', 'Bà hỏi giờ đón cháu thôi mà {title} gọi lại tận nơi.')],
         lesson='Nhóm chat chung là để báo tin; chuyện của từng đứa trẻ cần một cuộc gọi riêng.'),
    dict(id='grade_comments', kind='grading', emoji='🖋️', tag='Lời phê', title='Viết nhận xét giữa kỳ', reward=16, xp=20, npcs=['lan', 'ha'],
         intro='Mỗi bạn một dòng nhận xét vào sổ liên lạc: nêu điều làm tốt và một bước tiếp theo.',
         facts=[dict(title='Ghi chép của {title}', text='Khoa hiểu nhanh bài đo lường nhưng hay nói leo. Linh trình bày rất đẹp, sợ sai nên né bài khó. Tú mới chuyển trường, kể chuyện quê rất hay, viết sai chính tả d/gi. Mai chuyên cần, buổi sáng hay buồn ngủ.'),
                dict(title='Tin nhắn của Mẹ Linh', text='“{Title} ghi giúp con chữ xuất sắc nhé, con mà thấy chữ khác là buồn cả tuần.”')],
         steps=[S('match', 'match', 'Nhận xét cho từng bạn', 'Ghép mỗi bạn với dòng nhận xét đúng và hữu ích.', dict(khoa='k', linh='l', tu='t', mai='m'),
                  left=[o('khoa', 'Khoa'), o('linh', 'Linh'), o('tu', 'Tú'), o('mai', 'Mai')],
                  right=[o('k', 'Hiểu nhanh bài đo lường. Tập giơ tay chờ lượt để bạn khác cùng nói.'), o('l', 'Trình bày cẩn thận, đẹp. Thử chọn một bài khó mỗi tuần, sai cũng không sao.'),
                         o('t', 'Kể chuyện rất cuốn hút. Luyện thêm cặp chữ d/gi qua trò chơi đố từ.'), o('m', 'Đi học rất đều. Nhà giúp con ngủ sớm hơn một chút để buổi sáng tỉnh táo.')],
                  hints=['Mỗi dòng nói một điều làm tốt và một bước tiếp theo, đúng với ghi chép.'], explain='Nhận xét cụ thể giúp cả con và nhà biết bước tiếp theo.'),
                S('avoid', 'multi', 'Những lời nên tránh', 'Chọn các lời phê KHÔNG nên viết vào sổ.', ['lazy', 'rank', 'compare'],
                  options=[o('lazy', '“Lười, không chịu học.”'), o('rank', '“Đứng thứ 30/32 của lớp.”'), o('compare', '“Học kém hơn anh trai.”'), o('next', '“Tuần tới thử đọc to một đoạn trước nhóm.”'), o('good', '“Chữ viết tiến bộ rõ.”')],
                  hints=['Tránh dán nhãn, xếp hạng và so sánh.'], explain='Lời phê là để giúp tiến bộ, không để dán nhãn.'),
                S('parent', 'choice', 'Mẹ Linh xin chữ “xuất sắc”', 'Bạn trả lời thế nào?', 'honest',
                  options=[o('yes', 'Ghi “xuất sắc” cho mẹ vui'), o('honest', 'Giữ nhận xét thật, gọi điện kể điểm mạnh của Linh và cách nhà cùng giúp con bớt sợ sai'), o('ignore', 'Không trả lời tin nhắn')],
                  hints=['Lời khen không đúng làm con khó biết mình cần gì.'], explain='Trung thực, cụ thể và đồng hành với gia đình.')],
         perspectives=[V('Mẹ của Linh', '👩', 'Nghe {title} giải thích, tôi hiểu “sai cũng không sao” mới là điều con cần.'), V('Cô Hạ', '👩‍🏫', 'Nhận xét ngắn mà trúng, cho mình mượn mẫu nhé.'), V('Tú', '🧒', 'Con thích trò đố từ d/gi, giờ con toàn thắng!')],
         lesson='Một dòng nhận xét tốt vừa thật, vừa chỉ ra bước tiếp theo.'),
    dict(id='duty_cover', kind='duty', emoji='🧑‍🏫', tag='Dạy thay', title='Dạy thay lớp 3B của Cô Hạ', reward=20, xp=24, npcs=['ha'],
         intro='Cô Hạ bị sốt, nhờ bạn dạy thay tiết 2. Cô để lại một tờ giấy nhắn trên bàn.',
         facts=[dict(title='Giấy nhắn của Cô Hạ', text='Toán bài “Bảng nhân 6”, sách trang 45. Lớp trưởng: Hằng. Quân mắt kém, cần ngồi bàn đầu. Nhi có giấy xin về sớm lúc 10 giờ 30, mẹ đón. Không cho bạn nào về với người không có tên trong giấy.'),
                dict(title='10 giờ 25', text='Một người tự nhận là “chú của Nhi” đến cửa lớp xin đón Nhi về sớm.')],
         steps=[S('page', 'number', 'Mở sách', 'Cả lớp mở sách trang mấy?', 45, hints=['Đọc giấy nhắn.'], explain='Trang 45, bài “Bảng nhân 6”.'),
                S('seat', 'choice', 'Quân xin xuống bàn cuối', '“Cô Hạ cho con ngồi cuối với bạn mà!”', 'front',
                  options=[o('back', 'Cho Quân xuống cuối cho vui'), o('front', 'Nhẹ nhàng giữ Quân ở bàn đầu, cho bạn thân ngồi cạnh nếu được'), o('scold', 'Quát: “Không được nói dối!”')],
                  hints=['Giấy nhắn nói gì về mắt của Quân?'], explain='Giữ điều kiện học tốt cho Quân mà không mắng.'),
                S('pickup', 'choice', 'Người xin đón Nhi', 'Người này không có tên trong giấy xin phép.', 'verify',
                  options=[o('let', 'Cho Nhi về, trông chú hiền lành'), o('verify', 'Giữ Nhi trong lớp, nhờ văn phòng gọi mẹ Nhi xác nhận trước'), o('ask', 'Hỏi Nhi: “Con có biết chú không?” rồi cho về')],
                  hints=['Giấy nhắn: không giao học sinh cho người không có tên.'], explain='An toàn trước: chỉ giao trẻ khi gia đình xác nhận.'),
                S('handover', 'multi', 'Ghi lại cho Cô Hạ', 'Chọn các ý cần ghi vào sổ bàn giao.', ['done', 'pickup', 'hw'],
                  options=[o('done', 'Đã dạy xong phần bảng nhân 6, còn bài 3 để tiết sau'), o('pickup', 'Chuyện người xin đón Nhi và kết quả văn phòng gọi mẹ'), o('hw', 'Bài về nhà đã giao'), o('noisy', '“Lớp chị quậy quá, lần sau em không dạy thay nữa.”')],
                  hints=['Ghi sự việc, không than phiền.'], explain='Sổ bàn giao ghi đủ việc đã làm và chuyện cần theo dõi.')],
         perspectives=[V('Cô Hạ', '👩‍🏫', 'Đọc sổ bàn giao mà yên tâm hẳn. Mẹ Nhi bảo người đó là hàng xóm, không phải chú ruột. May quá.'), V('Quân', '🧒', 'Ngồi bàn đầu nhìn bảng rõ, con làm hết bài luôn.'), V('Hằng (lớp trưởng)', '👧', 'Lớp 3B ngoan hơn mọi khi vì {title} dạy vui!')],
         lesson='Dạy thay là giữ đúng những điều người nhờ đã dặn, nhất là chuyện an toàn.'),
    dict(id='ev_observed', kind='event', emoji='👀', tag='Thao giảng', title='Tiết thao giảng có tổ dự giờ', reward=28, xp=35, npcs=['ha', 'minh', 'vy'], months=[1, 5],
         intro='Năm thầy cô trong tổ ngồi cuối lớp dự tiết Tiếng Việt của bạn.',
         facts=[dict(title='Góp ý trước giờ', text='Một đồng nghiệp gợi ý: “Tập trước câu hỏi với mấy đứa giỏi, cho tiết trôi chảy.”'),
                dict(title='Trong tiết', text='Minh giơ tay lần đầu và trả lời sai. Mấy bạn khúc khích.')],
         steps=[S('rehearse', 'choice', 'Có tập trước không?', 'Bạn chuẩn bị thế nào?', 'real',
                  options=[o('script', 'Tập sẵn câu hỏi và đáp án với năm bạn giỏi'), o('real', 'Chuẩn bị kỹ giáo án và đồ dùng, dạy như một tiết thật'), o('swap', 'Đổi sang tiết trò chơi cho vui mắt')],
                  hints=['Người dự giờ muốn thấy lớp học thật.'], explain='Một tiết thật cho góp ý thật.'),
                S('wrong', 'choice', 'Minh trả lời sai', 'Cả tổ đang nhìn. Bạn làm gì?', 'value',
                  options=[o('skip', 'Gọi ngay bạn giỏi trả lời lại cho nhanh'), o('value', '“Cảm ơn Minh đã dám giơ tay. Ai giúp Minh đi tiếp một bước?”'), o('correct', 'Nói ngay đáp án đúng')],
                  hints=['Lần đầu giơ tay của Minh quan trọng hơn một tiết trôi chảy.'], explain='Trân trọng sự dũng cảm, biến câu sai thành bậc thang.'),
                S('feedback', 'multi', 'Nhận góp ý', 'Tổ góp ý: “Phần luyện tập hơi dài, cuối tiết chưa kịp kiểm tra.” Bạn làm gì?', ['thanks', 'plan'],
                  options=[o('thanks', 'Cảm ơn và ghi lại góp ý'), o('plan', 'Hẹn tiết sau cắt bớt luyện tập, dành 5 phút phiếu cuối tiết'), o('defend', 'Giải thích rằng lớp này chậm nên phải lâu'), o('upset', 'Im lặng, về nhà buồn cả tối')],
                  hints=['Góp ý là quà, kèm một thay đổi cụ thể.'], explain='Nhận góp ý và biến nó thành một thay đổi đo được.')],
         perspectives=[V('Cô Hạ', '👩‍🏫', 'Cả tổ nhớ nhất lúc Minh giơ tay. Tiết thật mới có khoảnh khắc thật.'), V('Minh', '🧒', 'Con trả lời sai mà {title} vẫn cảm ơn con. Lần sau con lại giơ tay.'), V('Tổ trưởng', '👩', 'Góp ý hôm trước, tiết sau đã thấy thay đổi. Rất đáng học.')],
         lesson='Thao giảng không phải để diễn, mà để cùng nhau dạy tốt hơn.'),
    dict(id='ev_fire_drill', kind='event', emoji='🚒', tag='An toàn', title='Diễn tập phòng cháy', reward=26, xp=32, npcs=['minh', 'bao', 'ha'], months=[6],
         intro='Chuông báo cháy diễn tập reo lúc 9 giờ 10. Lớp ở tầng 2.',
         facts=[dict(title='Sĩ số', text='Lớp 32 bạn, hôm nay 2 bạn nghỉ ốm. Lúc chuông reo, Bảo đang ở nhà vệ sinh và được thầy trực hành lang dẫn xuống cùng.'),
                dict(title='Lưu ý', text='Minh rất sợ tiếng động lớn. Lối cầu thang bên trái là lối thoát hiểm.')],
         steps=[S('order', 'order', 'Các bước thoát hiểm', 'Sắp xếp đúng thứ tự.', ['stop', 'line', 'book', 'exit', 'count'],
                  items=[o('count', 'Điểm danh ở sân tập trung, báo cáo ban chỉ huy'), o('book', 'Cầm sổ điểm danh'), o('stop', 'Dừng mọi việc, không lấy cặp'), o('exit', 'Đi theo lối cầu thang bên trái, không chạy, không chen'), o('line', 'Xếp hàng một ở cửa lớp')],
                  hints=['Dừng lại trước, đếm người sau cùng.'], explain='Dừng → xếp hàng → cầm sổ → đi đúng lối → điểm danh.'),
                S('count', 'number', 'Đếm ở sân', 'Ở sân tập trung, lớp phải có đủ bao nhiêu bạn?', 30, hints=['32 bạn, 2 bạn nghỉ ốm. Bảo có đi xuống không?'], explain='32 − 2 = 30, gồm cả Bảo đi cùng thầy trực.'),
                S('minh', 'choice', 'Minh bịt tai khóc', 'Minh đứng khựng ở cửa lớp.', 'hold',
                  options=[o('hold', 'Nắm tay Minh đi cùng, nói nhỏ: “Chỉ là diễn tập, {title} ở ngay đây.”'), o('leave', 'Để Minh ở lại lớp cho bớt sợ'), o('rush', 'Kéo mạnh tay Minh cho nhanh')],
                  hints=['Không ai ở lại phía sau, kể cả khi sợ.'], explain='Đi cùng và trấn an: an toàn và bình tĩnh.')],
         perspectives=[V('Minh', '🧒', '{Title} nắm tay con suốt cầu thang. Lần sau con không khóc nữa.'), V('Bảo', '🧒', 'Con đang đi vệ sinh thì chuông kêu, thầy trực dẫn con xuống, lớp đếm đủ 30!'), V('Cô Hạ', '👩‍🏫', 'Lớp mình xuống sân đầu tiên mà không ai chạy. Giỏi thật.')],
         lesson='Diễn tập nghiêm túc hôm nay là để không ai hoảng loạn khi có chuyện thật.'),
    dict(id='ev_book_day', kind='event', emoji='📚', tag='Ngày đọc sách', title='Ngày hội đọc sách của lớp', reward=26, xp=30, npcs=['minh', 'vy', 'bao', 'an'], months=[7],
         intro='Lớp dựng góc đọc sách, đổi sách cũ lấy sách mới và mời các em lớp 1 sang nghe đọc truyện.',
         facts=[dict(title='Quỹ mua sách', text='500 nghìn, mỗi cuốn khoảng 25 nghìn.'),
                dict(title='Đổi sách', text='Mỗi bạn mang một cuốn sách cũ để đổi. Tú mới chuyển trường, nhà chưa có sách.'),
                dict(title='Các bạn', text='Minh thích vẽ. Vy đọc to rất hay. Bảo mau chán khi ngồi lâu. An thích làm đồ thủ công.')],
         steps=[S('budget', 'number', 'Mua được mấy cuốn?', 'Với 500 nghìn, mua được bao nhiêu cuốn giá 25 nghìn?', 20, hints=['500 ÷ 25'], explain='500 ÷ 25 = 20 cuốn.'),
                S('swap', 'choice', 'Tú chưa có sách để đổi', 'Bạn làm gì?', 'draw',
                  options=[o('skip', 'Tú đứng xem các bạn đổi'), o('draw', 'Tú đổi bằng một bức tranh tự vẽ, hoặc chọn từ tủ sách lớp'), o('buy', 'Bảo Tú về xin tiền bố mua sách')],
                  hints=['Không để bạn nào đứng ngoài vì hoàn cảnh.'], explain='Có nhiều cách góp, ai cũng được tham gia.'),
                S('roles', 'match', 'Mỗi bạn một góc', 'Ghép mỗi bạn với hoạt động hợp nhất.', dict(minh='illustrate', vy='read', bao='hunt', an='bookmark'),
                  left=[o('minh', 'Minh'), o('vy', 'Vy'), o('bao', 'Bảo'), o('an', 'An')],
                  right=[o('illustrate', 'Vẽ lại cảnh yêu thích trong truyện'), o('read', 'Đọc to truyện cho các em lớp 1'), o('hunt', 'Trò truy tìm chữ trong 5 phút'), o('bookmark', 'Làm bookmark bằng giấy màu')],
                  hints=['Đọc mục “Các bạn”.'], explain='Mỗi bạn đến với sách bằng một cửa riêng.')],
         perspectives=[V('Tú', '🧒', 'Bức tranh của con được dán ở bìa sau một cuốn truyện của lớp!'), V('Vy', '👧', 'Các em lớp 1 ngồi im nghe con đọc. Con thấy mình như {title} giáo.'), V('Bảo', '🧒', 'Truy tìm chữ vui ghê, con tìm được 12 chữ “mèo”.')],
         lesson='Ngày đọc sách vui khi ai cũng có một cách chạm vào sách.'),
]
INDEX = {a['id']: a for a in ACTIVITIES}
REGULAR = [a['id'] for a in ACTIVITIES if a['kind'] in ('lesson', 'grading', 'duty') or (a['kind'] == 'meeting' and not a.get('months'))]


def month_index(day: int) -> int:
    return ((day - 1) // DAYS_PER_MONTH) % len(MONTHS)


def year_start(day: int) -> int:
    return day - (day - 1) % YEAR


def month_start(day: int) -> int:
    return day - (day - 1) % DAYS_PER_MONTH


def data(c: dict) -> dict:
    d = c['ext']['data'].setdefault('class', dict(active=None, done={}, history=[]))
    return d


def offers(c: dict) -> list[str]:
    """Deterministic list for the current game day."""
    day = c['day']
    m = month_index(day)
    done = (c['ext']['data'].get('class') or {}).get('done', {})
    out = []
    for a in ACTIVITIES:
        if a['kind'] == 'event' and not a.get('monthly') and m in a.get('months', ()) and done.get(a['id'], 0) < year_start(day):
            out.append(a['id'])
        if a.get('monthly') and done.get(a['id'], 0) < month_start(day):
            out.append(a['id'])
        if a['kind'] == 'meeting' and a.get('months') and m in a['months'] and done.get(a['id'], 0) < month_start(day):
            out.append(a['id'])
    n = len(REGULAR)
    for k in range(3):
        aid = REGULAR[(day * 2 + k) % n]
        if aid not in out and done.get(aid, 0) != day:
            out.append(aid)
    return out


def _task(a: dict, active: dict) -> dict:
    return dict(proc=a['steps'], proc_state=active['state'], mistakes=active['mistakes'])


def _say(s: dict, v):
    from .teach_lesson import say
    if isinstance(v, str):
        return say(s, v)
    if isinstance(v, list):
        return [_say(s, x) for x in v]
    if isinstance(v, dict):
        return {k: _say(s, x) for k, x in v.items()}
    return v


def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    return _say(s, _action(s, c, career, name, p))


def _action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    need(career == 'teacher', 'Kế hoạch lớp chỉ dành cho nghề giáo viên.')
    d = data(c)
    if name == 'cl_start':
        aid = p.get('activity')
        need(aid in INDEX, 'Hoạt động không tồn tại.')
        need(d['active'] is None, 'Hoàn thành hoạt động đang làm trước nhé.')
        need(aid in offers(c), 'Hoạt động này không có trong lịch hôm nay.')
        d['active'] = dict(id=aid, day=c['day'], state=P.initial_state(), mistakes=0)
        a = INDEX[aid]
        return dict(message=f'Bắt đầu: {a["title"]}. Đọc kỹ thông tin trước khi làm nhé.')
    if name == 'cl_submit':
        need(d['active'], 'Chưa chọn hoạt động nào.')
        a = INDEX[d['active']['id']]
        t = _task(a, d['active'])
        ok, msg = P.submit(t, p.get('step'), p.get('answer'))
        d['active']['mistakes'] = t['mistakes']
        return dict(message=('✓ ' if ok else '') + msg, correct=ok, done=P.done(t))
    if name == 'cl_finish':
        need(d['active'], 'Chưa chọn hoạt động nào.')
        a = INDEX[d['active']['id']]
        need(P.done(_task(a, d['active'])), 'Còn bước chưa hoàn thành.')
        mistakes = d['active']['mistakes']
        grade = 'great' if mistakes == 0 else 'ok' if mistakes <= 2 else 'rough'
        factor = dict(great=1.0, ok=0.7, rough=0.4)[grade]
        reward = int(round(a['reward'] * factor))
        if reward:
            e.money(s, c, reward, 'Thưởng hoạt động lớp: ' + a['title'], a['id'], category='bonus')
        c['xp'] += int(round(a['xp'] * factor))
        for key in a['npcs']:
            npc = NPC[key]
            if grade != 'rough':
                e.remember(s, c, npc, f'Cùng lớp {a["title"].lower()} ngày {c["day"]}.', a['id'])
        e.metric(c, 'class_activities')
        e.metric(c, 'class_' + a['kind'])
        voice = a['perspectives'][c['day'] % len(a['perspectives'])]
        e.add_feed(s, c, NPC['lan'] if a['kind'] in ('meeting', 'event') else NPC['ha'], _say(s, f'{voice["who"]}: “{voice["text"]}”'), 'classroom')
        d['done'][a['id']] = c['day']
        d['history'] = (d['history'] + [dict(id=a['id'], day=c['day'], grade=grade, mistakes=mistakes)])[-30:]
        d['active'] = None
        label = dict(great='Tuyệt vời', ok='Khá ổn', rough='Còn vụng')[grade]
        return dict(message=f'{label}! {a["title"]} hoàn thành · +{reward} xu thưởng.', celebrate=grade == 'great',
                    outcome=dict(activity=a['id'], grade=grade, mistakes=mistakes, perspectives=copy.deepcopy(a['perspectives']), lesson=a['lesson']))
    if name == 'cl_quit':
        need(d['active'], 'Chưa chọn hoạt động nào.')
        d['active'] = None
        return dict(message='Đã tạm gác hoạt động. Có thể chọn lại nếu còn trong lịch.')
    raise e.GameError('Thao tác kế hoạch lớp không hợp lệ.')


def public(c: dict) -> dict:
    d = c['ext']['data'].get('class') or dict(active=None, done={}, history=[])
    day = c['day']
    offered = []
    for aid in offers(c):
        a = INDEX[aid]
        offered.append(dict(id=aid, kind=a['kind'], kind_label=KIND_LABEL[a['kind']], emoji=a['emoji'], tag=a['tag'], title=a['title'], intro=a['intro'], reward=a['reward'], steps=len(a['steps'])))
    active = None
    if d.get('active'):
        a = INDEX[d['active']['id']]
        steps, state = P.public(_task(a, d['active']))
        active = dict(id=a['id'], kind=a['kind'], emoji=a['emoji'], tag=a['tag'], title=a['title'], intro=a['intro'], facts=copy.deepcopy(a['facts']),
                      steps=steps, state=state, mistakes=d['active']['mistakes'], done=state['at'] >= len(steps))
    last = d['history'][-1] if d.get('history') else None
    recap = None
    if last and last['day'] == day:
        a = INDEX[last['id']]
        recap = dict(id=a['id'], title=a['title'], grade=last['grade'], perspectives=copy.deepcopy(a['perspectives']), lesson=a['lesson'])
    from .teach_lesson import notebook
    return dict(month=MONTHS[month_index(day)], month_index=month_index(day), offers=offered, active=active, notebook=notebook(d),
                history=[dict(h, title=INDEX[h['id']]['title'], emoji=INDEX[h['id']]['emoji']) for h in d.get('history', [])[-10:]][::-1],
                recap=recap, calendar=[dict(month=MONTHS[i], events=[dict(emoji=a['emoji'], title=a['title']) for a in ACTIVITIES if i in a.get('months', ()) and a['kind'] == 'event']) for i in range(len(MONTHS))])


def validate(c: dict) -> None:
    from .engine import need, integer
    d = c['ext']['data'].get('class')
    if d is None:
        return
    need(isinstance(d, dict) and {'active', 'done', 'history'} <= set(d) <= {'active', 'done', 'history', 'kids'}, 'Dữ liệu kế hoạch lớp không hợp lệ.')
    from .teach_lesson import validate_kids
    validate_kids(d)
    need(isinstance(d['done'], dict) and all(k in INDEX for k in d['done']), 'Hoạt động lớp không hợp lệ.')
    for v in d['done'].values():
        integer(v, 1, 10 ** 9)
    need(isinstance(d['history'], list) and len(d['history']) <= 30, 'Lịch sử hoạt động không hợp lệ.')
    for h in d['history']:
        need(isinstance(h, dict) and h.get('id') in INDEX and h.get('grade') in ('great', 'ok', 'rough'), 'Lịch sử hoạt động không hợp lệ.')
        integer(h.get('day'), 1, 10 ** 9)
        integer(h.get('mistakes'), 0, 10 ** 6)
    if d['active'] is not None:
        act = d['active']
        need(isinstance(act, dict) and act.get('id') in INDEX, 'Hoạt động đang làm không hợp lệ.')
        integer(act.get('day'), 1, 10 ** 9)
        integer(act.get('mistakes'), 0, 10 ** 6)
        a = INDEX[act['id']]
        t = _task(a, act)
        P.validate(t, dict(proc=a['steps']))


def content() -> dict:
    return dict(months=list(MONTHS), kinds=KIND_LABEL, count=len(ACTIVITIES))
