"""Teacher v0.4: "Kế hoạch lớp" — varied lessons, grading, parent meetings and a
school-year calendar of events (Trung thu, sinh nhật tháng, 20/11, hội khỏe,
Tết, dã ngoại, tổng kết).

Activities are step procedures (game/procedures.py). Answer keys live in this
module, never in the save; the save keeps only the activity id and progress.
Everything is fictional; school rules here are simplified game rules.
"""
from __future__ import annotations
import copy
from .jsoncopy import tree_copy
import random
import re

from . import procedures as P
from . import archive as ar

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
                S('fix', 'choice', 'Cân đối quỹ', 'Chi phí vượt quỹ thì chọn cách cân đối.', 'craft',
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
        d['history'] = ar.last(d['history'] + [dict(id=a['id'], day=c['day'], grade=grade, mistakes=mistakes)], 30, 'classroom.history', c)
        d['active'] = None
        label = dict(great='Tuyệt vời', ok='Khá ổn', rough='Còn vụng')[grade]
        return dict(message=f'{label}! {a["title"]} hoàn thành · +{reward} xu thưởng.', celebrate=grade == 'great',
                    outcome=dict(activity=a['id'], grade=grade, mistakes=mistakes, perspectives=copy.deepcopy(a['perspectives']), lesson=a['lesson']))
    if name == 'cl_quit':
        need(d['active'], 'Chưa chọn hoạt động nào.')
        d['active'] = None
        return dict(message='Đã tạm gác hoạt động. Có thể chọn lại nếu còn trong lịch.')
    if name in CARE_ACTIONS:
        return CARE_ACTIONS[name](s, c, p)
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
        active = dict(id=a['id'], kind=a['kind'], emoji=a['emoji'], tag=a['tag'], title=a['title'], intro=a['intro'], facts=tree_copy(a['facts']),
                      steps=steps, state=state, mistakes=d['active']['mistakes'], done=state['at'] >= len(steps))
    last = d['history'][-1] if d.get('history') else None
    recap = None
    if last and last['day'] == day:
        a = INDEX[last['id']]
        recap = dict(id=a['id'], title=a['title'], grade=last['grade'], perspectives=tree_copy(a['perspectives']), lesson=a['lesson'])
    from .teach_lesson import notebook
    return dict(month=MONTHS[month_index(day)], month_index=month_index(day), offers=offered, active=active, notebook=notebook(d), care=care_view(c),
                history=[dict(h, title=INDEX[h['id']]['title'], emoji=INDEX[h['id']]['emoji']) for h in d.get('history', [])[-10:]][::-1],
                recap=recap, calendar=[dict(month=MONTHS[i], events=[dict(emoji=a['emoji'], title=a['title']) for a in ACTIVITIES if i in a.get('months', ()) and a['kind'] == 'event']) for i in range(len(MONTHS))])


def validate(c: dict) -> None:
    from .engine import need, integer
    d = c['ext']['data'].get('class')
    if d is None:
        return
    need(isinstance(d, dict) and {'active', 'done', 'history'} <= set(d) <= {'active', 'done', 'history', 'kids', 'care'}, 'Dữ liệu kế hoạch lớp không hợp lệ.')
    from .teach_lesson import validate_kids
    validate_kids(d)
    if 'care' in d:
        validate_care(d['care'], c['day'])
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


# ------------------------------------------------------------ care loop (several days)
# Each pupil carries progress per subject, wellbeing and "voice" (how openly they speak
# up) from day to day. Homework given after class is handed in the next day and waits
# to be marked; each parent expects to hear from the teacher about once a week (a game
# day is a school week in the planner's calendar); the seat plan changes how pupils
# learn. Every effect is a rule on the save, seeded by kid and day. The AI only rewords
# lines (teach_lesson.voice, /api/ai/class). Old saves get the book on first use.
# Spec: docs/superpowers/specs/2026-09-29-teacher-care-ai-design.md
SUBJECTS = [dict(id='math', emoji='🧮', label='Toán'), dict(id='read', emoji='📖', label='Tiếng Việt'), dict(id='think', emoji='🔍', label='Tư duy')]
SUBJECT = {x['id']: x for x in SUBJECTS}
SUBJECT_IDS = [x['id'] for x in SUBJECTS]
TOPIC_SUBJECT = {'Toán vui': 'math', 'Đếm hình': 'math', 'Đo lường': 'math', 'Đọc hiểu': 'read', 'Đọc bảng': 'read',
                 'Quan sát': 'think', 'Phân loại': 'think'}
PUPILS = ('minh', 'an', 'vy', 'bao', 'khoa', 'linh', 'tu', 'mai')
# (math, read, think, wellbeing, voice) at the start of the year.
START = dict(minh=(50, 44, 60, 50, 0), an=(55, 50, 62, 65, 3), vy=(50, 66, 50, 65, 5), bao=(42, 46, 55, 60, 4),
             khoa=(66, 50, 64, 55, 3), linh=(60, 64, 56, 45, 2), tu=(52, 40, 55, 40, 1), mai=(55, 55, 50, 50, 3))
VOICE_LABEL = ('Im lặng', 'Nói nhỏ với bạn', 'Dám hỏi khi được mời', 'Hay giơ tay', 'Tự tin phát biểu', 'Dẫn lời cả lớp')
BEHIND, SLOW, STRONG = 40, 55, 75
SAD, LOW = 35, 45
DUE, OVERDUE, CONTACT_GOAL = 4, 6, 2
MAX_TRUST_PARENT = 10
LINES_PER_THREAD = 12
# Seat i: row i // 2 counted from the board, the window seat is the even one.
DEFAULT_SEATS = ['linh', 'khoa', 'bao', 'an', 'tu', 'mai', 'minh', 'vy']
PAIRS = {  # deskmates → {kid: (progress per period, wellbeing per period)}, note
    frozenset(('minh', 'vy')): (dict(minh=(0, 2)), 'Có Vy bên cạnh, Minh đỡ run.'),
    frozenset(('an', 'tu')): (dict(an=(0, 1), tu=(0, 2)), 'An với Tú cùng mê làm thử, Tú có bạn mới.'),
    frozenset(('khoa', 'minh')): (dict(khoa=(1, 0), minh=(1, 0)), 'Khoa với Minh cùng mê hình vẽ, vẽ cho nhau xem.'),
    frozenset(('bao', 'vy')): (dict(bao=(-2, 0), vy=(-2, 0)), 'Bảo với Vy nói chuyện riêng suốt giờ.'),
    frozenset(('bao', 'tu')): (dict(bao=(0, -2), tu=(0, -2)), 'Bảo với Tú hay cãi nhau.'),
    frozenset(('linh', 'vy')): (dict(linh=(0, -2), vy=(-1, 0)), 'Vy hay liếc vở Linh, Linh khó chịu.'),
}
HW_SIZES = dict(light=dict(label='Nhẹ · 3 câu', gain=1), full=dict(label='Vừa · 6 câu', gain=2))
HW_KINDS = dict(good=('Làm đủ, đúng hết, trình bày gọn.', 'praise'),
                some=('Làm đủ, sai hai câu cùng một chỗ.', 'fix'),
                missing=('Không nộp vở.', 'ask'),
                tired=('Làm được một câu, nét chữ xiêu vẹo; cuối trang người nhà ghi: “Con buồn ngủ quá.”', 'ask'))
HW_MARKS = [dict(id='praise', emoji='🌟', label='Khen cụ thể'), dict(id='fix', emoji='✏️', label='Chữa cùng con'),
            dict(id='ask', emoji='🤝', label='Hỏi riêng vì sao')]
HW_MARK_IDS = [m['id'] for m in HW_MARKS]
HW_WHY = dict(mai='Mai kể sáng nào cũng dậy từ sớm phụ mẹ bán phở, tối về là ngủ gục.', bao='Bảo để quên vở ở nhà bà ngoại.',
              tu='Tú chưa hiểu đề, bố đi làm ca tối nên không ai hỏi giúp.', minh='Minh làm rồi nhưng sợ sai nên không dám nộp.',
              linh='Linh làm đi làm lại vì sợ bẩn vở, tới khuya vẫn chưa xong.', vy='Vy mải kể chuyện với em, quên mất bài.',
              an='An mải làm mô hình bằng nắp chai, quên làm bài.', khoa='Bà nội không đọc được đề nên Khoa không biết hỏi ai.')
PARENTS = dict(
    minh=dict(name='Cô Lan', rel='mẹ của Minh', self='chị', temper='parent_kind', trust=6, region='miền Bắc', particles=['ạ', 'nhé'],
              style='hiền, hay lo vì con nhút nhát, rất mừng khi con dám nói; nhắn tin nhẹ nhàng'),
    an=dict(name='Bố An', rel='bố của An', self='anh', temper='parent_kind', trust=6, region='miền Nam', particles=['nha', 'hen'],
            style='kỹ sư, vui tính, nhắn ngắn gọn, thích con tự tay làm thử'),
    vy=dict(name='Mẹ Vy', rel='mẹ của Vy', self='chị', temper='parent_worried', trust=4, region='miền Nam', particles=['ạ', 'nha', 'á'],
            style='hay lo, nhắn liền mấy tin, hỏi dồn, cần được trấn an bằng việc cụ thể'),
    bao=dict(name='Mẹ Bảo', rel='mẹ của Bảo', self='chị', temper='parent_knowitall', trust=5, region='miền Bắc', particles=['đấy', 'nhé'],
             style='tự nhận rành giáo dục, hay góp ý cách dạy, thương con, dễ tự ái khi con bị chê'),
    khoa=dict(name='Bà nội Khoa', rel='bà nội của Khoa', self='bà', temper='parent_kind', trust=6, region='miền Bắc', particles=['nhé'],
              style='lớn tuổi, không rành nhắn tin, gõ chậm, câu ngắn, rất thương cháu', age='elder'),
    linh=dict(name='Mẹ Linh', rel='mẹ của Linh', self='chị', temper='parent_strict', trust=5, region='miền Bắc', particles=['ạ', 'nhé'],
              style='cầu toàn, muốn con giỏi, đang tập cho con bớt sợ sai'),
    tu=dict(name='Bố Tú', rel='bố của Tú', self='tôi', temper='parent_strict', trust=3, region='miền Trung (Quảng Ngãi)', particles=['hỉ', 'rứa'],
            style='thẳng tính, nhắn cụt, làm ca tối, thương con mới chuyển trường'),
    mai=dict(name='Mẹ Mai', rel='mẹ của Mai', self='chị', temper='parent_kind', trust=5, region='miền Nam', particles=['nha', 'ạ'],
             style='bán phở từ sáng sớm, nhắn tin vội lúc rảnh tay, rất thương con'),
)
TOPICS = dict(sad='con buồn, không muốn đi học', worry='con kêu khó một môn', hw='bài về nhà làm tới khuya',
              thanks='con về khoe tiến bộ', check='hỏi thăm việc học trong tuần', news='giáo viên báo tin vui',
              help='giáo viên nhờ nhà phối hợp', brief='giáo viên hỏi thăm ngắn')
OPEN = dict(sad='{Title} ơi, mấy hôm nay {child} không muốn đi học, hỏi gì con cũng im. Ở lớp có chuyện gì không ạ?',
            worry='{Title} ơi, dạo này {child} về nhà hay kêu khó môn {subject}. Ở lớp con có theo kịp không ạ?',
            hw='{Title} ơi, tối qua {child} làm bài về nhà muộn quá. Bài có nhiều không ạ?',
            thanks='{Title} ơi, hôm nay {child} về khoe học {subject} vui lắm. Cảm ơn {title} nhiều!',
            check='{Title} ơi, tuần này {child} học hành thế nào ạ? Nhà có cần kèm thêm gì không?')
OPEN_KID = dict(tu=dict(check='{Title}, tuần ni thằng Tú học răng? Có chi cần nhà lo thì nói tôi.',
                        worry='{Title}, thằng Tú về kêu môn {subject} khó quá. Ở lớp nó theo kịp không?'),
                khoa=dict(check='{Title} giáo ơi, bà hỏi chút. Tuần này thằng Khoa học có ngoan không?',
                          hw='{Title} giáo ơi, tối qua thằng Khoa làm bài khuya quá, bà không biết chỉ.'),
                vy=dict(worry='{Title} ơi! Vy về kêu môn {subject} khó. Con có theo kịp không ạ? Có cần cho con đi học thêm không ạ?'))
ANSWER = dict(good='{Self} cảm ơn {title}, nghe {title} nói cụ thể vậy {self} yên tâm hẳn. Tối nay nhà sẽ làm cùng con như {title} dặn.',
              ok='Dạ vâng, {self} cảm ơn {title}.',
              poor='{Self} hỏi về con mà {title} trả lời vậy thì {self} chưa yên tâm lắm.',
              privacy='Chuyện con nhà khác {title} đừng kể với {self} thì hơn ạ.')
ANSWER_KID = dict(tu=dict(good='Rứa thì tôi yên tâm. Cảm ơn {title}.', poor='Tôi hỏi thật mà {title} trả lời cho qua. Tôi không vui.'),
                  khoa=dict(good='Bà cảm ơn {title} giáo nhiều. Tối nay bà dặn cháu.'),
                  bao=dict(good='Được, cách đó chị thấy hợp lý đấy. Để chị kèm thêm ở nhà.', poor='Chị nghĩ {title} nên xem lại cách dạy đấy.'))
METHOD_WORD = dict(look='hình vẽ', hands='đồ vật cho con cầm thử', talk='ví dụ kể bằng lời', short='cách chia nhỏ từng bước')
HOME_TIP = dict(math='đếm đồ vật trong nhà', read='đọc to một đoạn ngắn', think='xếp đồ chơi theo nhóm')
REPLY = dict(sad='Cảm ơn {sp} đã báo. Ở lớp {child} dạo này hơi trầm. {Title} sẽ để ý, cho con ngồi cạnh bạn thân và hỏi chuyện riêng; ở nhà mình cứ nghe con kể nhé.',
             worry='Dạ, ở lớp {child} đang {weak_band} môn {subject}. Tuần này {title} kèm con thêm bằng {method}; ở nhà mình cho con {tip} nhé.',
             hw='Dạ, {title} cảm ơn nhà đã báo. {Title} sẽ giao bài nhẹ hơn cho con; con làm được tới đâu thì làm, không thức khuya.',
             thanks='Dạ, {child} dạo này tiến bộ rõ ở môn {subject}. Nhà mình cứ khen con đúng việc con làm nhé.',
             check='Dạ, tuần này {child} {best_band} môn {best}, còn môn {weak} thì {weak_band}. Mỗi tối nhà mình cho con {tip} nhé.')
VAGUE = 'Dạ {sp} yên tâm, con vẫn ổn ạ.'
BLAMING = 'Con ở nhà cũng phải chịu khó hơn chứ ạ, các bạn khác vẫn làm được.'
START_MSG = dict(news='{Title} báo tin vui: dạo này {child} làm môn {best} rất chắc tay. Nhà mình khen con giúp {title} nhé!',
                 help='{Title} nhắn để nhà mình cùng biết: {child} đang {weak_band} môn {weak}. {Title} sẽ kèm thêm ở lớp; mỗi tối nhà mình cho con {tip} nhé.',
                 brief='Dạ, {title} nhắn hỏi thăm nhà mình. Con ở lớp vẫn ổn ạ.')
START_LABEL = dict(news='Báo tin vui', help='Nhờ nhà phối hợp', brief='Hỏi thăm ngắn')
BLAME = ('luoi', 'hu', 'hoc kem', 'kem qua', 'yeu kem', 'dot', 'cham hieu', 'phai phat', 'tai nha', 'bo me phai', 'nha minh phai',
         'chiu kho hon', 'khong chiu hoc', 'ngoc')
COMPARE = ('so voi', 'ban khac', 'cac ban khac', 'hon ban', 'thua ban', 'dung thu', 'dung bet', 'xep hang', 'kem nhat')
STEP = ('tuan nay', 'toi nay', 'moi toi', 'moi ngay', 'se', 'kem them', 'cung con', 'o nha', 'hen', 'buoc', 'thu', 'goi y', 'de y')
WARM_P = ('cam on', 'yen tam', 'chia se', 'dong hanh', 'phoi hop', 'tien bo', 'khen', 'co gang', 'vui')
CARE_KEYS = {'v', 'day', 'pupils', 'seats', 'hw', 'books', 'parents', 'threads', 'taught', 'subject', 'seen', 'mailed', 'called', 'seq', 'log'}


def _clamp(v: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(v)))


def subject_of(lesson: dict) -> str:
    return TOPIC_SUBJECT.get((lesson or {}).get('topic'), 'math')


def band(n: int) -> str:
    return 'còn hổng' if n < BEHIND else 'cần kèm thêm' if n < SLOW else 'theo kịp' if n < STRONG else 'rất vững'


def mood(n: int) -> str:
    return 'buồn, thu mình' if n < SAD else 'cần động viên' if n < LOW else 'vui vẻ' if n >= 65 else 'bình thường'


def _new_care(c: dict, d: dict | None = None) -> dict:
    day = c['day']
    old = (d or {}).get('kids') or {}
    pupils = {}
    for kid in PUPILS:
        m, r, th, w, v = START[kid]
        bonus = min(10, 2 * int((old.get(kid) or {}).get('trust', 0)))  # an old save's class notebook still counts
        pupils[kid] = dict(prog=dict(math=m, read=r, think=th), well=_clamp(w + bonus), voice=v)
    parents = {kid: dict(trust=PARENTS[kid]['trust'], last=day - DUE + i // 2, sent=0) for i, kid in enumerate(PUPILS)}
    return dict(v=1, day=day, pupils=pupils, seats=list(DEFAULT_SEATS), hw=None, books=[], parents=parents,
                threads={kid: [] for kid in PUPILS}, taught=0, subject=None, seen=[], mailed=0, called=[], seq=0, log=[])


def care(c: dict) -> dict:
    """The class care book, brought up to today (lazy day rollover; old saves get one here)."""
    d = data(c)
    if d.get('care') is None:
        d['care'] = _new_care(c, d)
    _sync(d['care'], c['day'])
    return d['care']


def _log(cr: dict, text: str) -> None:
    cr['log'] = ar.last(cr['log'] + [dict(day=cr['day'], text=text[:200])], 12, 'classroom.log', None)


def _hw_result(cr: dict, kid: str, hw: dict) -> str:
    p, trust = cr['pupils'][kid], cr['parents'][kid]['trust']
    prog = p['prog'][hw['subject']]
    r = random.Random(f'mnl-teacher-hw|{kid}|{hw["day"]}|{hw["size"]}').random()
    miss = 0.04 + (0.12 if p['well'] < SAD else 0) + (0.10 if trust <= 2 else 0) - (0.03 if trust >= 8 else 0)
    tired = 0.0
    if hw['size'] == 'full':
        miss += 0.05
        tired = 0.08 + (0.40 if kid == 'mai' else 0) + (0.12 if kid == 'linh' else 0)
    good = max(0.15, min(0.85, (prog - 30) / 55))
    if r < miss:
        return 'missing'
    if r < miss + tired:
        return 'tired'
    return 'good' if r < miss + tired + (1 - miss - tired) * good else 'some'


def _sync(cr: dict, day: int) -> None:
    if cr['day'] >= day:
        return
    for dd in range(max(cr['day'] + 1, day - 6), day + 1):
        hw = cr['hw']
        if hw and hw['day'] < dd:
            for kid in hw['kids']:
                cr['seq'] += 1
                cr['books'].append(dict(id=f'hw{cr["seq"]}', day=hw['day'], kid=kid, subject=hw['subject'], size=hw['size'],
                                        kind=_hw_result(cr, kid, hw), mark=None))
            cr['hw'] = None
        keep = []
        for b in cr['books']:
            if b['mark'] is not None:
                continue
            if dd - b['day'] >= 3:  # never marked: the book goes home without a word
                cr['pupils'][b['kid']]['well'] = _clamp(cr['pupils'][b['kid']]['well'] - 1)
                continue
            keep.append(b)
        cr['books'] = ar.last(keep, 24, 'classroom.books', None)
        for p in cr['pupils'].values():
            p['well'] += max(-2, min(2, 55 - p['well']))
        for kid, par in cr['parents'].items():
            if dd - par['last'] > OVERDUE:
                par['trust'] = max(1, par['trust'] - 1)
            th = cr['threads'][kid]
            if th and th[-1]['who'] == 'parent' and th[-1].get('ask') and dd - th[-1]['day'] >= 2 and not th[-1].get('late'):
                th[-1]['late'] = True
                par['trust'] = max(0, par['trust'] - 1)
    cr['day'] = day
    cr['seen'] = []
    cr['called'] = []


def voices(c: dict) -> dict:
    return {k: p['voice'] for k, p in care(c)['pupils'].items()}


def pupil_change(c: dict, kid: str, subject: str | None = None, prog: int = 0, well: int = 0, voice: int = 0) -> None:
    if kid not in PUPILS:
        return
    p = care(c)['pupils'][kid]
    if subject and prog:
        p['prog'][subject] = _clamp(p['prog'][subject] + prog)
    p['well'] = _clamp(p['well'] + well)
    p['voice'] = _clamp(p['voice'] + voice, 0, len(VOICE_LABEL) - 1)


def on_trust(c: dict, kid: str, delta: int) -> None:
    """Trust moves in the notebook (incidents, roll call, help) also move how a kid feels."""
    pupil_change(c, kid, well=2 * delta, voice=1 if delta >= 2 else 0)


def seat_notes(seats: list[str]) -> dict:
    """{kid: [(progress, wellbeing, note)]} from where each kid sits and who sits next to them."""
    from .teach_lesson import KID
    out = {k: [] for k in seats}
    for i, kid in enumerate(seats):
        row, window, style = i // 2, i % 2 == 0, KID[kid]['style']
        if style == 'look' and row >= 2:
            out[kid].append((-2, 0, 'Ngồi xa bảng, khó xem hình mẫu.'))
        elif style == 'look' and row == 0:
            out[kid].append((1, 0, 'Ngồi gần bảng, nhìn rõ hình mẫu.'))
        if style == 'short' and window:
            out[kid].append((-2, 0, 'Ngồi cạnh cửa sổ, hay nhìn ra ngoài.'))
        elif style == 'short' and row == 0:
            out[kid].append((1, 0, 'Ngồi gần bàn giáo viên, dễ tập trung.'))
        if i % 2 == 0:
            mate = seats[i + 1]
            pair = PAIRS.get(frozenset((kid, mate)))
            if pair:
                fx, note = pair
                for k, (pg, wb) in fx.items():
                    out[k].append((pg, wb, note))
    return out


def after_period(s: dict, c: dict, t: dict, room: dict) -> str:
    """A period just closed: progress and wellbeing per pupil, seats, and (once a day) parents write."""
    from . import teach_lesson as TL
    cr = care(c)
    day, subj = c['day'], subject_of(t['lesson'])
    present = TL.present_ids(room)
    notes = seat_notes(cr['seats'])
    before = {k: band(cr['pupils'][k]['prog'][subj]) for k in PUPILS}
    for row in room['kids']:
        kid = row['id']
        if kid not in present:
            pupil_change(c, kid, subject=subj, prog=-1)
            continue
        tk, mark = room['tickets'].get(kid), room['marks'].get(kid)
        if tk is None:
            continue
        right = mark == TL.MARK_FOR[tk['kind']]
        prog = (4 if right else 2) if tk['kind'] in ('right', 'slip') else (1 if right else -1) if tk['kind'] == 'copy' else -2
        well = 1 if right else -2
        for pg, wb, _ in notes.get(kid, []):
            prog, well = prog + pg, well + wb
        pupil_change(c, kid, subject=subj, prog=prog, well=well)
        if kid not in cr['seen']:
            cr['seen'].append(kid)
    cr['taught'], cr['subject'] = day, subj
    order = ['còn hổng', 'cần kèm thêm', 'theo kịp', 'rất vững']
    after = {k: band(cr['pupils'][k]['prog'][subj]) for k in PUPILS}
    up = [k for k in present if order.index(after[k]) > order.index(before[k])]
    down = [k for k in present if after[k] == 'còn hổng' and before[k] != 'còn hổng']
    parts = []
    if up:
        parts.append(', '.join(TL.KID[k]['name'] for k in up) + f' tiến bộ môn {SUBJECT[subj]["label"]}')
    if down:
        parts.append(', '.join(TL.KID[k]['name'] for k in down) + f' đang hổng {SUBJECT[subj]["label"]}')
    if parts:
        _log(cr, '; '.join(parts) + '.')
    wrote = _mail(s, c, cr, set(up), subj, room) if cr['mailed'] != day else 0
    out = ('📒 ' + '; '.join(parts) + '.') if parts else ''
    if wrote:
        out += f' 💌 {wrote} phụ huynh vừa nhắn tin.'
    return out.strip()


def _words(state: dict, c: dict, cr: dict, kid: str) -> dict:
    """Facts about a pupil in words, for scripted lines and the AI context."""
    from . import teach_lesson as TL
    p = cr['pupils'][kid]
    best = max(SUBJECT_IDS, key=lambda x: (p['prog'][x], -SUBJECT_IDS.index(x)))
    weak = min(SUBJECT_IDS, key=lambda x: (p['prog'][x], SUBJECT_IDS.index(x)))
    known = ((data(c).get('kids') or {}).get(kid) or {}).get('known')
    return dict(child=TL.KID[kid]['name'], best=SUBJECT[best]['label'], weak=SUBJECT[weak]['label'],
                best_band=band(p['prog'][best]), weak_band=band(p['prog'][weak]), tip=HOME_TIP[weak],
                method=METHOD_WORD[TL.KID[kid]['style']] if known else 'cách con dễ hiểu nhất', sp=PARENTS[kid]['self'],
                best_id=best, weak_id=weak)


def _fill(text: str, w: dict) -> str:
    for k, v in w.items():
        text = text.replace('{' + k + '}', str(v))
    return text


def _mail(s: dict, c: dict, cr: dict, improved: set, subj: str, room: dict) -> int:
    """After class, up to two parents write about their child's real week."""
    day = c['day']
    arcs = {tag.split(':')[0] for tag in room.get('arcs', [])}
    cands = []
    for kid in PUPILS:
        th = cr['threads'][kid]
        if th and th[-1]['who'] == 'parent' and th[-1].get('ask'):
            continue
        p = cr['pupils'][kid]
        w = _words(s, c, cr, kid)
        if p['well'] < SAD:
            cands.append((0, kid, 'sad', None))
        elif p['prog'][w['weak_id']] < BEHIND:
            cands.append((1, kid, 'worry', w['weak_id']))
        elif any(b['kid'] == kid and b['day'] == day - 1 and b['kind'] in ('tired', 'missing') for b in cr['books']):
            cands.append((2, kid, 'hw', None))
        elif kid in improved or kid in arcs:
            cands.append((3, kid, 'thanks', subj))
        elif day - cr['parents'][kid]['last'] >= DUE:
            cands.append((4, kid, 'check', None))
    random.Random(f'mnl-teacher-mail|{day}').shuffle(cands)
    cands.sort(key=lambda x: x[0])
    for _, kid, topic, sid in cands[:2]:
        w = _words(s, c, cr, kid)
        text = OPEN_KID.get(kid, {}).get(topic) or OPEN[topic]
        text = _say(s, _fill(text, dict(w, subject=SUBJECT[sid]['label'] if sid else w['weak'])))
        line = dict(who='parent', text=text, mode='scripted', day=day, ask=True, topic=topic)
        if sid:
            line['subject'] = sid
        cr['threads'][kid] = ar.last(cr['threads'][kid] + [line], LINES_PER_THREAD, 'classroom.thread:' + kid, c)
    cr['mailed'] = day
    return len(cands[:2])


# ---- parent messages: options, rules, effects ---------------------------------
def _awaiting(cr: dict, kid: str) -> dict | None:
    th = cr['threads'][kid]
    return th[-1] if th and th[-1]['who'] == 'parent' and th[-1].get('ask') else None


def parent_options(s: dict | None, c: dict, cr: dict, kid: str) -> list[dict]:
    """Three scripted messages (reply to the waiting message, or start one), neutral ids."""
    w = _words(s or {}, c, cr, kid)
    p = cr['pupils'][kid]
    msg = _awaiting(cr, kid)
    if msg:
        topic = msg['topic']
        w['subject'] = SUBJECT[msg['subject']]['label'] if msg.get('subject') in SUBJECT else w['weak']
        rows = [('good', REPLY.get(topic, REPLY['check']), topic), ('ok', VAGUE, topic), ('poor', BLAMING, topic)]
    else:
        news_ok = max(p['prog'].values()) >= 60 or p['well'] >= 60
        help_ok = min(p['prog'].values()) < SLOW or p['well'] < LOW
        rows = [('good' if news_ok else 'ok', START_MSG['news'], 'news'), ('good' if help_ok else 'ok', START_MSG['help'], 'help'),
                ('ok', START_MSG['brief'], 'brief')]
    random.Random(f'mnl-teacher-popt|{kid}|{cr["day"]}|{len(cr["threads"][kid])}').shuffle(rows)
    out = []
    for i, (quality, text, topic) in enumerate(rows):
        label = _fill(text, w)
        out.append(dict(id='abc'[i], quality=quality, topic=topic, label=_say(s, label) if s is not None else label))
    return out


def _names_other(text: str, kid: str) -> bool:
    """Another pupil named in a message to this parent (privacy). Sentence starts are ignored."""
    from .teach_lesson import KID
    for other in PUPILS:
        if other == kid:
            continue
        for m in re.finditer(r'(?<!\w)' + re.escape(KID[other]['name']) + r'(?!\w)', text):
            before = text[:m.start()].rstrip()
            if before and before[-1] not in '.!?…:"“\n':
                return True
    return False


def judge_parent(text: str, kid: str, topic: str | None) -> tuple[str, str]:
    """Rule-based quality of a typed message to a parent → (quality, why)."""
    from . import ai
    from .teach_lesson import _fold, _has, KID
    folded = _fold(text)
    if ai.abusive(text):
        return 'poor', 'rude'
    if _names_other(text, kid):
        return 'privacy', 'privacy'
    if _has(folded, BLAME) or _has(folded, COMPARE):
        return 'poor', 'blame'
    if len(folded.strip()) < 8:
        return 'poor', 'short'
    score = 0
    if _has(folded, [_fold(KID[kid]['name']).strip()] + [_fold(x['label']).strip() for x in SUBJECTS]):
        score += 2
    if _has(folded, STEP):
        score += 1
    if _has(folded, WARM_P):
        score += 1
    if score >= 3:
        return 'good', 'rules'
    return ('ok', 'rules') if score >= 1 or len(folded.strip()) >= 20 else ('poor', 'short')


def parent_answer(s: dict, kid: str, quality: str) -> str:
    par = PARENTS[kid]
    text = ANSWER_KID.get(kid, {}).get(quality) or ANSWER[quality]
    text = text.replace('{Self}', par['self'].capitalize()).replace('{self}', par['self'])
    return _say(s, text)


def _cl_parent(s: dict, c: dict, p: dict) -> dict:
    from . import engine as e
    need = e.need
    cr = care(c)
    kid = p.get('kid')
    need(kid in PUPILS, 'Không có phụ huynh này trong lớp.')
    day = c['day']
    par, msg = cr['parents'][kid], _awaiting(cr, kid)
    if not msg:
        need(par['sent'] != day and kid not in cr['called'], 'Hôm nay đã nhắn phụ huynh này rồi. Để mai nhé.')
    opt, text = p.get('option'), p.get('text')
    need((opt is None) != (text is None), 'Chọn một tin soạn sẵn hoặc gõ tin của bạn.')
    if opt is not None:
        row = next((o for o in parent_options(s, c, cr, kid) if o['id'] == opt), None)
        need(row, 'Tin nhắn không hợp lệ.')
        quality, said, topic = row['quality'], row['label'], row['topic']
    else:
        from .teach_lesson import ANSWER_MAX
        said = e.clean_text(text, ANSWER_MAX, 2)
        quality, _ = judge_parent(said, kid, msg['topic'] if msg else None)
        topic = msg['topic'] if msg else 'brief'
    trust = dict(good=1, ok=0, poor=-1, privacy=-2)[quality]
    if quality == 'good' and msg and msg['day'] == day:
        trust += 1  # answered the same day
    par['trust'] = _clamp(par['trust'] + trust, 0, MAX_TRUST_PARENT)
    if quality == 'good':
        pupil_change(c, kid, well=4 if msg and msg['topic'] == 'sad' else 2)
    elif quality in ('poor', 'privacy'):
        pupil_change(c, kid, well=-1)
    th = cr['threads'][kid]
    if msg:
        msg['ask'] = False
    answer = parent_answer(s, kid, quality)
    th.append(dict(who='teacher', text=said, mode='scripted', day=day))
    th.append(dict(who='parent', text=answer, mode='scripted', day=day, topic=topic, q=quality))
    cr['threads'][kid] = ar.last(th, LINES_PER_THREAD, 'classroom.thread:' + kid, c)
    par['last'] = day
    if not msg:
        par['sent'] = day
    extra = ''
    if kid not in cr['called']:
        cr['called'].append(kid)
        if len(cr['called']) == CONTACT_GOAL:
            c['xp'] += 4
            extra = f' Đã giữ nhịp liên lạc tuần này ({CONTACT_GOAL} phụ huynh) · +4 XP.'
    e.metric(c, 'class_parent_messages')
    if quality in ('poor', 'privacy') and par['trust'] <= 1:
        from .teach_lesson import _post
        _post(s, c, kid, PARENTS[kid]['name'], answer, f'care-parent-{kid}-{day}')
    name = PARENTS[kid]['name']
    label = dict(good=f'{name} yên tâm hơn.', ok=f'{name} đã đọc tin.', poor=f'{name} chưa hài lòng.',
                 privacy=f'{name} thấy không nên kể chuyện con nhà khác.')[quality]
    return dict(message=label + extra, correct=quality in ('good', 'ok'), quality=quality, reply=answer)


# ---- seats and homework -------------------------------------------------------
def _cl_seat(s: dict, c: dict, p: dict) -> dict:
    from . import engine as e
    need = e.need
    cr = care(c)
    a, b = p.get('a'), p.get('b')
    need(a in PUPILS and b in PUPILS and a != b, 'Chọn hai bạn khác nhau để đổi chỗ.')
    busy = any(isinstance(t.get('room'), dict) and t['room'].get('stage') in ('teach', 'check') and t['status'] not in ('completed', 'referred', 'cancelled')
               for t in c['tasks'] if t.get('career') == 'teacher')
    need(not busy, 'Đang trong giờ dạy. Khép tiết rồi hãy đổi chỗ nhé.')
    seats = cr['seats']
    i, j = seats.index(a), seats.index(b)
    seats[i], seats[j] = b, a
    from .teach_lesson import KID
    notes = seat_notes(seats)
    said = [f'{KID[k]["name"]}: {n}' for k in (a, b) for _, _, n in notes[k]]
    return dict(message=f'Đã đổi chỗ {KID[a]["name"]} và {KID[b]["name"]}.' + (' ' + ' '.join(dict.fromkeys(said)) if said else ''))


def _cl_hw(s: dict, c: dict, p: dict) -> dict:
    from . import engine as e
    need = e.need
    cr = care(c)
    size = p.get('size')
    need(size in HW_SIZES, 'Chọn lượng bài về nhà.')
    day = c['day']
    need(cr['taught'] == day and cr['seen'], 'Dạy xong ít nhất một tiết hôm nay rồi mới giao bài về nhà.')
    need(not (cr['hw'] and cr['hw']['day'] == day), 'Hôm nay đã giao bài về nhà rồi.')
    cr['hw'] = dict(day=day, subject=cr['subject'], size=size, kids=list(cr['seen']))
    return dict(message=f'Đã giao bài {SUBJECT[cr["subject"]]["label"]} ({HW_SIZES[size]["label"].lower()}) cho {len(cr["seen"])} bạn. Mai các bạn nộp vở.')


def _cl_hw_mark(s: dict, c: dict, p: dict) -> dict:
    from . import engine as e
    from .teach_lesson import KID
    need = e.need
    cr = care(c)
    book = next((b for b in cr['books'] if b['id'] == p.get('book')), None)
    need(book, 'Không có vở này.')
    need(book['mark'] is None, 'Vở này đã chấm rồi.')
    mark = p.get('mark')
    need(mark in HW_MARK_IDS, 'Cách chấm không hợp lệ.')
    book['mark'] = mark
    kid, kind, gain = book['kid'], book['kind'], HW_SIZES[book['size']]['gain']
    name = KID[kid]['name']
    right = mark == HW_KINDS[kind][1]
    if right and kind == 'good':
        pupil_change(c, kid, subject=book['subject'], prog=gain, well=2)
        c['xp'] += 1
        msg = f'{name} cười tít khi đọc lời khen.'
    elif right and kind == 'some':
        pupil_change(c, kid, subject=book['subject'], prog=gain + 1, well=1)
        msg = f'{name} sửa lại hai câu sai, giờ hiểu chỗ nhầm rồi.'
    elif right:
        pupil_change(c, kid, well=1)
        msg = HW_WHY[kid] + (' Lần sau giao bài nhẹ hơn cho con, hoặc nhắn phụ huynh.' if kind == 'tired' else ' Có thể nhắn phụ huynh để cùng nhắc con.')
    elif kind in ('missing', 'tired'):
        pupil_change(c, kid, well=-3)
        cr['parents'][kid]['trust'] = max(0, cr['parents'][kid]['trust'] - 1)
        msg = f'{name} bị ghi thiếu bài mà không ai hỏi vì sao. Về nhà con buồn.'
    elif mark == 'praise':
        msg = f'{name} tưởng mình làm đúng hết, chỗ sai vẫn còn đó.'
    elif mark == 'fix':
        pupil_change(c, kid, well=-2)
        msg = f'Bài của {name} đúng hết mà bị bắt chữa lại. Con hơi buồn.'
    else:
        pupil_change(c, kid, well=-1)
        msg = f'{name} làm bài đầy đủ mà bị gọi hỏi riêng, con thấy như mình có lỗi.'
    e.metric(c, 'class_homework_marked')
    return dict(message=msg, correct=right)


CARE_ACTIONS = dict(cl_seat=_cl_seat, cl_hw=_cl_hw, cl_hw_mark=_cl_hw_mark, cl_parent=_cl_parent)


# ---- projection ---------------------------------------------------------------
def care_view(c: dict) -> dict:
    """What the planner shows. Works on a synced copy: reading never changes the save."""
    from .teach_lesson import KID
    d = c['ext']['data'].get('class') or {}
    cr = tree_copy(d['care']) if d.get('care') else _new_care(c, d)
    _sync(cr, c['day'])
    day = c['day']
    view_c = dict(c, ext=dict(c['ext'], data=dict(c['ext']['data'], **{'class': dict(d, care=cr)})))
    notes = seat_notes(cr['seats'])
    pupils = []
    for kid in PUPILS:
        p = cr['pupils'][kid]
        behind = [SUBJECT[x]['label'] for x in SUBJECT_IDS if p['prog'][x] < BEHIND]
        flags = (['behind'] if behind else []) + (['sad'] if p['well'] < SAD else ['low'] if p['well'] < LOW else []) + \
                (['opening'] if kid == 'minh' and p['voice'] >= 2 else [])
        pupils.append(dict(id=kid, name=KID[kid]['name'], emoji=KID[kid]['emoji'], prog=dict(p['prog']), well=p['well'], mood=mood(p['well']),
                           voice=p['voice'], voice_label=VOICE_LABEL[p['voice']], behind=behind, flags=flags, seat=cr['seats'].index(kid)))
    seats = []
    for i, kid in enumerate(cr['seats']):
        seats.append(dict(i=i, row=i // 2, window=i % 2 == 0, kid=kid, name=KID[kid]['name'], emoji=KID[kid]['emoji'],
                          notes=[dict(tone='good' if pg + wb > 0 else 'bad', text=n) for pg, wb, n in notes[kid]]))
    hw_today = cr['hw'] if cr['hw'] and cr['hw']['day'] == day else None
    books = [dict(id=b['id'], kid=b['kid'], name=KID[b['kid']]['name'], emoji=KID[b['kid']]['emoji'], subject=SUBJECT[b['subject']]['label'],
                  size=HW_SIZES[b['size']]['label'], clue=HW_KINDS[b['kind']][0], mark=b['mark'], day=b['day']) for b in cr['books']]
    parents = []
    for kid in PUPILS:
        par, th, msg = cr['parents'][kid], cr['threads'][kid], _awaiting(cr, kid)
        can = bool(msg) or (par['sent'] != day and kid not in cr['called'])
        parents.append(dict(kid=kid, child=KID[kid]['name'], emoji=KID[kid]['emoji'], name=PARENTS[kid]['name'], rel=PARENTS[kid]['rel'],
                            trust=par['trust'], waiting=bool(msg), late=bool(msg and msg.get('late')), due=day - par['last'] >= DUE,
                            overdue=day - par['last'] > OVERDUE, called=kid in cr['called'], can=can,
                            thread=[dict(who=x['who'], text=x['text'], mode=x['mode'], day=x['day'], **({'canonical': x['canonical']} if x.get('canonical') else {}))
                                    for x in th],
                            options=[dict(id=o['id'], label=o['label']) for o in parent_options(None, view_c, cr, kid)] if can else [],
                            start_labels=[START_LABEL[k] for k in ('news', 'help', 'brief')] if not msg else None))
    # A fixed order: the sheet keeps open threads by position across re-renders.
    return dict(day=day, subjects=SUBJECTS, pupils=pupils, seats=seats, busy=any(
        isinstance(t.get('room'), dict) and t['room'].get('stage') in ('teach', 'check') and t['status'] not in ('completed', 'referred', 'cancelled')
        for t in c['tasks'] if t.get('career') == 'teacher'),
        hw=dict(today=dict(subject=SUBJECT[hw_today['subject']]['label'], size=HW_SIZES[hw_today['size']]['label'], count=len(hw_today['kids'])) if hw_today else None,
                can=cr['taught'] == day and bool(cr['seen']) and not hw_today,
                subject=SUBJECT[cr['subject']]['label'] if cr['taught'] == day and cr['subject'] else None,
                sizes=[dict(id=k, label=v['label']) for k, v in HW_SIZES.items()]),
        books=books, marks=HW_MARKS, parents=parents, called=len(cr['called']), goal=CONTACT_GOAL,
        waiting=sum(1 for x in parents if x['waiting']), log=list(reversed(cr['log']))[:6],
        voices=list(VOICE_LABEL))


# ---- validation ---------------------------------------------------------------
def validate_care(cr: dict, day: int) -> None:
    from .engine import need, integer, clean_text
    need(isinstance(cr, dict) and set(cr) == CARE_KEYS and cr['v'] == 1, 'Sổ chăm lớp không hợp lệ.')
    integer(cr['day'], 1, 10 ** 9)
    need(cr['day'] <= day, 'Sổ chăm lớp đi trước ngày chơi.')
    integer(cr['taught'], 0, 10 ** 9)
    integer(cr['mailed'], 0, 10 ** 9)
    integer(cr['seq'], 0, 10 ** 9)
    need(cr['subject'] in (None, *SUBJECT_IDS), 'Môn học không hợp lệ.')
    need(isinstance(cr['pupils'], dict) and set(cr['pupils']) == set(PUPILS), 'Sổ học sinh không hợp lệ.')
    for p in cr['pupils'].values():
        need(isinstance(p, dict) and set(p) == {'prog', 'well', 'voice'}, 'Sổ học sinh không hợp lệ.')
        need(isinstance(p['prog'], dict) and set(p['prog']) == set(SUBJECT_IDS), 'Tiến bộ môn học không hợp lệ.')
        for v in p['prog'].values():
            integer(v, 0, 100)
        integer(p['well'], 0, 100)
        integer(p['voice'], 0, len(VOICE_LABEL) - 1)
    need(isinstance(cr['seats'], list) and sorted(cr['seats']) == sorted(PUPILS), 'Sơ đồ chỗ ngồi không hợp lệ.')
    for key in ('seen', 'called'):
        need(isinstance(cr[key], list) and len(set(cr[key])) == len(cr[key]) and all(k in PUPILS for k in cr[key]), 'Danh sách học sinh không hợp lệ.')
    hw = cr['hw']
    if hw is not None:
        need(isinstance(hw, dict) and set(hw) == {'day', 'subject', 'size', 'kids'}, 'Bài về nhà không hợp lệ.')
        integer(hw['day'], 1, day)
        need(hw['subject'] in SUBJECT_IDS and hw['size'] in HW_SIZES, 'Bài về nhà không hợp lệ.')
        need(isinstance(hw['kids'], list) and 0 < len(hw['kids']) == len(set(hw['kids'])) and all(k in PUPILS for k in hw['kids']), 'Bài về nhà không hợp lệ.')
    need(isinstance(cr['books'], list) and len(cr['books']) <= 24 and len({b.get('id') for b in cr['books'] if isinstance(b, dict)}) == len(cr['books']), 'Vở bài tập không hợp lệ.')
    for b in cr['books']:
        need(set(b) == {'id', 'day', 'kid', 'subject', 'size', 'kind', 'mark'} and isinstance(b['id'], str) and len(b['id']) <= 20, 'Vở bài tập không hợp lệ.')
        integer(b['day'], 1, day)
        need(b['kid'] in PUPILS and b['subject'] in SUBJECT_IDS and b['size'] in HW_SIZES and b['kind'] in HW_KINDS and b['mark'] in (None, *HW_MARK_IDS), 'Vở bài tập không hợp lệ.')
    need(isinstance(cr['parents'], dict) and set(cr['parents']) == set(PUPILS), 'Sổ liên lạc không hợp lệ.')
    for par in cr['parents'].values():
        need(isinstance(par, dict) and set(par) == {'trust', 'last', 'sent'}, 'Sổ liên lạc không hợp lệ.')
        integer(par['trust'], 0, MAX_TRUST_PARENT)
        integer(par['last'], -DUE, day)
        integer(par['sent'], 0, day)
    need(isinstance(cr['threads'], dict) and set(cr['threads']) == set(PUPILS), 'Tin nhắn phụ huynh không hợp lệ.')
    for th in cr['threads'].values():
        need(isinstance(th, list) and len(th) <= LINES_PER_THREAD, 'Tin nhắn phụ huynh không hợp lệ.')
        for x in th:
            need(isinstance(x, dict) and {'who', 'text', 'mode', 'day'} <= set(x) <= {'who', 'text', 'mode', 'day', 'canonical', 'ask', 'topic', 'late', 'q', 'subject'}, 'Tin nhắn phụ huynh không hợp lệ.')
            need(x.get('subject') in (None, *SUBJECT_IDS), 'Tin nhắn phụ huynh không hợp lệ.')
            need(x['who'] in ('parent', 'teacher') and x['mode'] in ('scripted', 'ai', 'guard'), 'Tin nhắn phụ huynh không hợp lệ.')
            clean_text(x['text'], 600)
            integer(x['day'], 1, day)
            if 'canonical' in x:
                clean_text(x['canonical'], 600)
            need(type(x.get('ask', False)) is bool and type(x.get('late', False)) is bool, 'Tin nhắn phụ huynh không hợp lệ.')
            need(x.get('topic') in (None, *TOPICS) and x.get('q') in (None, 'good', 'ok', 'poor', 'privacy'), 'Tin nhắn phụ huynh không hợp lệ.')
            need(not x.get('ask') or x['who'] == 'parent', 'Tin nhắn phụ huynh không hợp lệ.')
    need(isinstance(cr['log'], list) and len(cr['log']) <= 12, 'Nhật ký lớp không hợp lệ.')
    for row in cr['log']:
        need(isinstance(row, dict) and set(row) == {'day', 'text'}, 'Nhật ký lớp không hợp lệ.')
        integer(row['day'], 1, day)
        clean_text(row['text'], 200)


# ---- AI voice jobs (server route /api/ai/class) -------------------------------
DIRECTION = dict(
    ask='Bạn đang giơ tay hỏi {title} đúng câu hỏi trong canonical. Hỏi lại đúng ý đó bằng giọng của bạn, một hai câu; nhút nhát thì ngập ngừng.',
    good='Câu trả lời của {title} giúp bạn hiểu ra: vui, có thể nói lại điều mình vừa hiểu hoặc cảm ơn.',
    ok='Bạn nghe rồi nhưng vẫn còn hơi lăn tăn, chưa hiểu hẳn vì sao; nói lễ phép.',
    poor='Câu trả lời làm bạn ngại, buồn: bạn thu mình lại, nói rất ít, không cãi, không hỗn.',
    ignored='Bạn chờ mãi không được gọi nên hạ tay xuống, hơi buồn.',
    open='Bạn đang nhắn tin cho {title} chủ nhiệm của con về đúng chuyện trong canonical. Viết như tin nhắn Zalo thật, đúng tính cách; chỉ dùng thông tin trong task.',
    p_good='{Title} vừa trả lời cụ thể, có bước tiếp theo: bạn yên tâm hơn, cảm ơn, có thể hứa phối hợp ở nhà.',
    p_ok='{Title} trả lời chung chung: bạn lịch sự nhưng vẫn còn băn khoăn.',
    p_poor='{Title} trả lời đổ lỗi hoặc so con với bạn khác: bạn không vui, nói thẳng nhưng lịch sự, không xúc phạm.',
    p_privacy='{Title} vừa kể chuyện của một bạn khác: bạn thấy không nên, nhắc khéo giữ chuyện riêng của trẻ.',
)


def parent_card(state: dict, kid: str) -> dict:
    from . import ai
    from .personas import AGE_LABEL
    from .teach_lesson import titles, KID
    par = PARENTS[kid]
    age = par.get('age', 'adult')
    return dict(id='parent:' + kid, name=par['name'], role='Phụ huynh, ' + par['rel'], career='teacher', place='Lớp học Mầm Nắng',
                age=age, age_label=AGE_LABEL[age], temperament=par['temper'], temperament_label='Phụ huynh',
                style=ai.STYLE_GUIDE.get(par['temper'], '') + '; ' + par['style'], personality=par['style'],
                traits=[f'Con: {KID[kid]["name"]}, học lớp 2. {KID[kid]["trait"]}.'], address=dict(self=par['self'], player=titles(state)[1]),
                region=par['region'], particles=list(par['particles']), cares=['con tiến bộ thật, được báo tin cụ thể'], memory={})


def _facts(state: dict, c: dict, cr: dict, kid: str) -> dict:
    p = cr['pupils'][kid]
    return dict(progress={SUBJECT[x]['label']: f'{band(p["prog"][x])} ({p["prog"][x]}/100)' for x in SUBJECT_IDS},
                wellbeing=mood(p['well']), speaking_up=VOICE_LABEL[p['voice']])


def voice_job(state: dict, kind: str, kid: str, task: str | None, op: str) -> dict | None:
    """The scripted line /api/ai/class may reword, with what the model may know. None = nothing to voice."""
    from . import teach_lesson as TL
    c = (state.get('careers') or {}).get('teacher')
    if not c or kid not in PUPILS or op not in ('voice', 'reply'):
        return None
    d = (c.get('ext') or {}).get('data', {}).get('class') or {}
    cr = d.get('care')
    title = TL.titles(state)[1]
    if kind == 'pupil':
        t = next((x for x in c.get('tasks', []) if x.get('id') == task and isinstance(x.get('room'), dict)), None)
        ask = t['room'].get('ask') if t else None
        if not ask or ask['kid'] != kid:
            return None
        lines = ask['lines']
        # 'voice': the raised hand's question; once answered, the pupil's reaction (a reply sent with
        # later=true is voiced by a separate 'voice' call). 'reply': the reaction.
        if op == 'voice' and ask['state'] == 'up':
            idx = 0 if ask['result'] is None and lines and lines[0]['who'] == 'pupil' else None
            said, direction = '(giơ tay xin hỏi)', DIRECTION['ask']
        else:
            idx = len(lines) - 1 if ask['state'] == 'done' and len(lines) >= 3 and lines[-1]['who'] == 'pupil' else None
            said, direction = (lines[-2]['text'] if idx else ''), DIRECTION.get(ask['result'] or 'ok', '')
        if idx is None or lines[idx]['mode'] != 'scripted':
            return None
        facts = _facts(state, c, cr, kid) if cr else {}
        context = dict(lesson=t['lesson'].get('title'), lesson_goal=t['lesson'].get('prompt'), subject=SUBJECT[subject_of(t['lesson'])]['label'],
                       question=lines[0]['text'], answer_quality=TL.QUALITY_NOTE.get(ask['result']) if ask['result'] in TL.QUALITY else None, pupil=facts)
        who = {'npc': TL.CARRIER[kid]} if kid in TL.CARRIER else {'card': TL.pupil_card(state, kid, dict(pupil=facts))}
        return dict(who=who, said=said, context={k: v for k, v in context.items() if v}, canonical=lines[idx]['text'],
                    history=TL.history_rows(lines, idx), purpose='class_question', direction=direction.replace('{title}', title),
                    ref=dict(kind='pupil', kid=kid, task=task, index=idx))
    if kind != 'parent' or not cr:
        return None
    th = cr['threads'][kid]
    if not th or th[-1]['who'] != 'parent' or th[-1]['mode'] != 'scripted':
        return None
    idx, last = len(th) - 1, th[-1]
    if op == 'voice' and last.get('ask'):
        said, direction = '(mở tin nhắn gửi giáo viên)', DIRECTION['open']
    else:
        if last.get('ask') or len(th) < 2 or th[-2]['who'] != 'teacher':
            return None
        said, direction = th[-2]['text'], DIRECTION.get('p_' + (last.get('q') or 'ok'), '')
    context = dict(child=TL.KID[kid]['name'], relation=PARENTS[kid]['rel'], class_name='lớp 2, Lớp học Mầm Nắng', topic=TOPICS.get(last.get('topic'), ''),
                   child_facts=_facts(state, c, cr, kid), trust_in_teacher='cao' if cr['parents'][kid]['trust'] >= 7 else 'thấp' if cr['parents'][kid]['trust'] <= 3 else 'vừa',
                   teacher_reply_quality=last.get('q'))
    direction = direction.replace('{Title}', title.capitalize()).replace('{title}', title)
    return dict(who={'card': parent_card(state, kid)}, said=said, context={k: v for k, v in context.items() if v}, canonical=last['text'],
                history=TL.history_rows(th, idx), purpose='parent_message', direction=direction,
                ref=dict(kind='parent', kid=kid, task=None, index=idx))


def rewrite(raw: dict, ref: dict, canonical: str, text: str, mode: str) -> bool:
    """Reword one stored line in a raw save, only if it still holds the same scripted text."""
    c = ((raw.get('careers') or {}).get('teacher')) or {}
    if ref['kind'] == 'pupil':
        t = next((x for x in c.get('tasks', []) if x.get('id') == ref['task'] and isinstance(x.get('room'), dict)), None)
        ask = (t or {}).get('room', {}).get('ask')
        lines = ask['lines'] if ask and ask.get('kid') == ref['kid'] else []
    else:
        cr = ((c.get('ext') or {}).get('data', {}).get('class') or {}).get('care') or {}
        lines = (cr.get('threads') or {}).get(ref['kid']) or []
    i = ref['index']
    if not 0 <= i < len(lines):
        return False
    line = lines[i]
    if line.get('mode') != 'scripted' or line.get('text') != canonical:
        return False
    line.update(text=text[:600], mode=mode, canonical=canonical[:600])
    return True
