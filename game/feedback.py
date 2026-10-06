"""Customer feedback with personalities and owner reply threads (v0.4).

Stars come from what actually happened in the task (criteria). Each reviewer
has a stable personality: sharp-tongued, know-it-all, warm and funny, picky,
Gen Z, terse; parents review teachers. When the owner answers, the reviewer
decides for themselves: revise up, keep, argue back with the facts, or revise
down after a rude reply. An optional AI writes the words and proposes the
decision; the engine clamps the star change to what the facts allow and falls
back to the scripted decision whenever AI is unavailable.

v0.5 wave 2: real review sites are not always polite. From day 3 some
reviewers show up on a bad day (know-it-all, rude, entitled, "bóc phốt"), and
some reviews are careless or fake (twists): off-topic 1★, wrong shop, never
visited, a rival's plant, stars tapped by mistake, demands, rumours. Twists are
rolled once from the task id, stored in the record and may move the stars away
from the facts; the true grade stays in `fair`. The owner can reply, ignore,
or report: every review can be reported (góp ý #196, 06/10). Fakes, wrong shops,
off-topic 1★, off-topic gripes and pile-ons leave the average (kept, marked); a real
experience stays, at no star cost and with no pile-on. A rude reply gets screenshotted:
more 1★ follow (a pile-on never starts another one).
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import re
import unicodedata
from . import archive as ar

PERSONAS = {
    'sour': dict(name='Chanh chua', emoji='🍋', style='Nói thẳng, hơi đá đểu, châm chọc nhưng công bằng nếu thấy người ta sửa thật.', group='customer', bias=-0.4),
    'bossy': dict(name='Bố đời', emoji='🧐', style='Thích dạy đời, hay kể “hồi xưa tôi…”, muốn được ghi nhận là mình đúng.', group='customer', bias=-0.2),
    'warm': dict(name='Ấm áp vui tính', emoji='🌻', style='Dễ thương, hay đùa, khen cụ thể, dễ bỏ qua khi người ta thành thật.', group='customer', bias=0.3),
    'picky': dict(name='Kỹ tính', emoji='🔍', style='Soi từng chi tiết, cần bằng chứng và cam kết cụ thể.', group='customer', bias=-0.3),
    'genz': dict(name='Gen Z', emoji='✨', style='Nói trẻ trung, dùng vài từ lóng và emoji vừa phải, thẳng mà vui.', group='customer', bias=0.0),
    'quiet': dict(name='Kiệm lời', emoji='🤐', style='Nói cực ngắn, ít cảm xúc, chỉ nói điều quan trọng.', group='customer', bias=0.0),
    'parent_worried': dict(name='Phụ huynh hay lo', emoji='😟', style='Lo con bị thiệt, hỏi nhiều, cần được trấn an bằng thông tin cụ thể.', group='parent', bias=-0.2),
    'parent_strict': dict(name='Phụ huynh khó tính', emoji='😤', style='Hay khiếu nại, đòi giải trình, dễ nói “tôi sẽ báo nhà trường”.', group='parent', bias=-0.5),
    'parent_kind': dict(name='Phụ huynh đồng hành', emoji='🤝', style='Hợp tác, cảm ơn, góp ý nhẹ nhàng và muốn cùng giúp con.', group='parent', bias=0.3),
    'knowitall': dict(name='Chuyên gia bố đời', emoji='🤓', style='Kẻ cả, tự xưng “anh làm nghề mười năm rồi em ạ”, dạy đời từng chi tiết, không bao giờ chịu mình sai.', group='customer', bias=-0.5),
    'rude': dict(name='Xấc xược', emoji='😒', style='Cộc lốc, mỉa mai, chê dịch vụ bằng câu ngắn khó nghe nhưng không chửi tục.', group='customer', bias=-0.6),
    'entitled': dict(name='Thượng đế', emoji='👑', style='Coi mình là khách VIP, đòi ưu tiên, đòi quà, không được chiều là chê.', group='customer', bias=-0.5),
    'drama': dict(name='Dọa bóc phốt', emoji='📢', style='Hay dọa đăng lên group bóc phốt, đòi đền bù, giữ ảnh “làm bằng chứng”.', group='customer', bias=-0.6),
    'troll': dict(name='Đánh giá ẩu', emoji='🙃', style='Chấm sao theo cảm hứng, lý do chẳng liên quan, lười sửa.', group='customer', bias=-0.4),
    'parent_knowitall': dict(name='Phụ huynh bố đời', emoji='🧑‍🏫', style='Tự nhận rành giáo dục, dạy giáo viên cách dạy, hay nói “tôi cũng từng đứng lớp”.', group='parent', bias=-0.5),
    'parent_rude': dict(name='Phụ huynh hỗn', emoji='😠', style='Nói trống không trong nhóm Zalo lớp, gắt gỏng, dọa chuyển lớp, không chửi tục.', group='parent', bias=-0.6),
}
CUSTOMER_PERSONAS = ('sour', 'bossy', 'warm', 'picky', 'genz', 'quiet')
PARENT_PERSONAS = ('parent_worried', 'parent_strict', 'parent_kind')
# People on a bad day: they replace the usual voice for one review.
MOOD_CUSTOMER = ('knowitall', 'rude', 'entitled', 'drama')
MOOD_PARENT = ('parent_knowitall', 'parent_rude')
HARSH = MOOD_CUSTOMER + MOOD_PARENT + ('troll',)

# Short scripted voices. {bad} / {good} are criterion labels, {note} a fact.
VOICE = {
    'sour': dict(
        thanks=['Ờ, trả lời cũng lễ phép đấy. Giữ phong độ nhé.'],
        open={5: ['Ờ, lần này thì phải công nhận là được.', 'Tưởng lại phải chê, ai ngờ ổn thật.'],
              4: ['Tạm được, chưa tới mức để khoe.', 'Được đó, nhưng đừng tưởng thế là hoàn hảo.'],
              3: ['Ba sao là vì tôi còn nể đấy.', 'Kiểu làm cho có thì đúng rồi.'],
              2: ['Nói thật chứ trải nghiệm hơi bị “đáng nhớ”.', 'Tiền mất tật mang, ai rảnh thì thử.'],
              1: ['Chắc quán tưởng khách không biết gì.', 'Thôi, lần đầu cũng là lần cuối.']},
        good=['{good} thì không chê được.', 'Được cái {good} ổn.'],
        bad=['{bad} thì… thôi khỏi nói: {note}.', 'Còn {bad}? {note}, quán tự hiểu.'],
        accept=['Thấy quán nhận lỗi đàng hoàng nên tôi sửa lại. Nhớ đấy nhé.', 'Ừ, chịu sửa thì tôi nâng sao. Lần sau đừng để tôi phải nhắc.'],
        keep=['Nói hay lắm, nhưng tôi giữ nguyên. Làm được rồi hãy nói.', 'Đọc rồi. Sao giữ nguyên nhé.'],
        argue=['Quán nói vậy chứ {note} là sự thật, tôi không bịa.', 'Đừng lấy lý do. {note}, rõ ràng thế còn gì.'],
        down=['Trả lời khách kiểu này thì tôi hạ sao cho xứng.', 'Thái độ vậy à? Hạ thêm một sao cho nhớ.'],
        sorry=['Ờ… hồ sơ ghi vậy thật. Tôi nhầm, sửa lại sao cho quán.', 'Được rồi, tôi xem lại phiếu thì đúng là tôi nhớ nhầm. Sửa sao.']),
    'bossy': dict(
        thanks=['Tốt, biết cảm ơn khách là biết làm ăn.'],
        open={5: ['Làm vậy mới đúng bài. Hồi xưa tôi mở quán cũng dạy nhân viên y như thế.', 'Chuẩn. Cứ giữ phong độ này.'],
              4: ['Khá, nhưng nghe tôi góp ý thêm chút.', 'Được, có điều còn non tay.'],
              3: ['Tôi nói cho mà biết, làm nghề phải kỹ hơn thế.', 'Trung bình. Hồi tôi còn trẻ mà làm thế là bị mắng.'],
              2: ['Cái này là thiếu kinh nghiệm rõ ràng.', 'Tôi đi nhiều nơi rồi, chỗ này cần học lại cơ bản.'],
              1: ['Làm ăn thế này thì không trụ được đâu, nghe tôi.', 'Sai từ gốc. Phải học lại từ đầu.']},
        good=['{good} làm đúng như tôi vẫn hay nói.', '{good} được, giữ đó.'],
        bad=['{bad} thì chưa đạt: {note}. Tôi khuyên nên sửa quy trình.', 'Về {bad}, {note} — cái này người làm nghề phải biết.'],
        accept=['Biết nghe góp ý là tốt. Tôi nâng sao để khích lệ.', 'Được, chịu học là có tương lai. Tôi sửa lại đánh giá.'],
        keep=['Cảm ơn, nhưng làm được rồi tôi mới đổi đánh giá.', 'Tôi ghi nhận, cứ làm cho tốt đã.'],
        argue=['Cậu/cô giải thích thì giải thích, nhưng {note} là thật. Người làm nghề phải nhận.', 'Không phải cãi. Tôi đã thấy {note}.'],
        down=['Nói chuyện với khách lớn tuổi như thế là không được. Hạ sao.', 'Thái độ này thì tôi phải hạ đánh giá thôi.'],
        sorry=['À, phiếu ghi rõ thế thì tôi nhớ nhầm. Người lớn cũng phải biết nhận sai. Sửa lại sao.', 'Ừ, tôi xem lại rồi, quán đúng. Tôi sửa đánh giá.']),
    'warm': dict(
        thanks=['Hihi quán dễ thương quá, hẹn gặp lại nha! 💛'],
        open={5: ['Tuyệt vời luôn, ghé một lần là nhớ quán! 🥰', 'Xịn quá, mình cho 5 sao kèm một nụ cười nè.'],
              4: ['Ưng lắm, có chút xíu cần chỉnh thôi nha!', 'Vui ghê, lần sau mình lại ghé.'],
              3: ['Ổn nha, mình tin lần sau quán sẽ làm tốt hơn.', 'Hơi lấn cấn chút nhưng mọi người dễ thương lắm.'],
              2: ['Hôm nay chắc quán bận, mình hơi buồn xíu.', 'Không như mình mong, nhưng mình vẫn cho quán cơ hội nha.'],
              1: ['Buồn thiệt chứ, chắc mình ghé nhầm ngày.', 'Hôm nay không vui lắm, mong quán xem lại nha.']},
        good=['{good} đỉnh luôn!', 'Thích nhất là {good} nè.'],
        bad=['Chỉ có {bad} hơi tiếc: {note}.', '{bad} thì chưa ổn lắm ({note}), nhưng không sao đâu.'],
        accept=['Quán dễ thương ghê, mình nâng sao liền nè! 💛', 'Nghe quán nói vậy mình vui rồi, sửa lại đánh giá nha!'],
        keep=['Cảm ơn quán đã trả lời nha, mình giữ đánh giá để quán có động lực!', 'Mình đọc rồi nè, hẹn lần sau ghé tiếp.'],
        argue=['Mình không có ý bắt lỗi đâu, nhưng {note} thiệt đó quán ơi.', 'Mình kể đúng những gì mình thấy thôi: {note}.'],
        down=['Ơ, quán trả lời hơi gắt á… mình buồn nên hạ sao nha.', 'Mình góp ý thật lòng mà quán nói vậy, hơi hụt hẫng.'],
        sorry=['Ôi mình nhớ nhầm thật, xin lỗi quán nha! Sửa lại sao liền.', 'Hóa ra phiếu ghi vậy, mình quê quá 😅 Sửa lại cho quán.']),
    'picky': dict(
        thanks=['Đã đọc. Duy trì chất lượng như lần này.'],
        open={5: ['Đã kiểm từng chi tiết: đạt.', 'Không tìm ra điểm trừ. Hiếm đấy.'],
              4: ['Đạt phần lớn tiêu chí, còn một điểm cần cải thiện.', 'Tốt, trừ một chi tiết nhỏ.'],
              3: ['Nhiều chi tiết chưa đúng chuẩn.', 'Đạt mức trung bình theo tiêu chí của tôi.'],
              2: ['Sai lệch rõ so với yêu cầu ban đầu.', 'Tôi đã ghi lại từng lỗi dưới đây.'],
              1: ['Không đạt tiêu chí nào quan trọng.', 'Sai yêu cầu, không chấp nhận được.']},
        good=['{good}: đạt.', '{good} đúng yêu cầu.'],
        bad=['{bad}: KHÔNG đạt ({note}).', 'Lưu ý {bad} — {note}.'],
        accept=['Quán đưa ra biện pháp cụ thể, tôi điều chỉnh đánh giá.', 'Có cam kết rõ ràng. Tôi sửa lại số sao.'],
        keep=['Lời xin lỗi chung chung chưa đủ. Cần biện pháp cụ thể.', 'Tôi giữ nguyên cho tới khi thấy thay đổi thực tế.'],
        argue=['Tôi có ghi nhận cụ thể: {note}. Quán kiểm tra lại quy trình.', 'Dữ kiện là {note}. Tôi không đánh giá theo cảm tính.'],
        down=['Phản hồi thiếu chuyên nghiệp. Trừ thêm một sao.', 'Không chấp nhận cách trả lời này.'],
        sorry=['Đã đối chiếu với phiếu: tôi nhầm. Điều chỉnh lại đánh giá.', 'Dữ kiện quán đưa ra chính xác. Sửa lại số sao.']),
    'genz': dict(
        thanks=['Quán rep cute xỉu, lần sau ghé tiếp nha ✨'],
        open={5: ['Đỉnh nóc kịch trần luôn á ✨', 'Mê xỉu, 10 điểm không có nhưng 😭'],
              4: ['Oke áp, chấm 4 sao cho quán nha 👍', 'Khá là ưng, chỉ hơi “hmm” một xíu.'],
              3: ['Ừm cũng được, không có gì để flex lắm.', 'Mid thôi quán ơi 🥲'],
              2: ['Hơi toang nha quán ơi 😮‍💨', 'Kỳ vọng bao nhiêu thất vọng bấy nhiêu.'],
              1: ['Red flag luôn á 🚩', 'Thôi xin phép né quán này 🙃']},
        good=['{good} là chân ái ✨', '{good} ổn áp nha.'],
        bad=['{bad} thì hơi “sai sai” á: {note} 😵', '{bad} chưa ổn nha quán ({note}).'],
        accept=['Quán xin lỗi xịn quá, up sao liền nè 🫶', 'Okela, thấy quán có tâm nên sửa lại nha ✨'],
        keep=['Thanks quán đã rep nha, sao để nguyên đó 😌', 'Seen rồi nha, lần sau làm xịn hơn là được.'],
        argue=['Ủa nhưng mà {note} thật mà quán 🤨', 'Quán đừng gaslight tui nha, {note} đó.'],
        down=['Rep kiểu này là tụt mood thật sự, hạ sao 🙄', 'Thái độ gì vậy trời, trừ sao nha.'],
        sorry=['Ối tui nhớ nhầm thật, sorry quán nha 😅 sửa sao liền.', 'Check lại bill thì đúng là tui sai, xin lỗi quán 🙏']),
    'quiet': dict(
        thanks=['👍'],
        open={5: ['Tốt.', 'Được. Sẽ quay lại.'], 4: ['Ổn.', 'Được, gần đủ.'], 3: ['Bình thường.', 'Tạm.'],
              2: ['Không ổn.', 'Chưa đạt.'], 1: ['Tệ.', 'Không quay lại.']},
        good=['{good} ổn.'], bad=['{bad}: {note}.'],
        accept=['Được. Sửa sao.'], keep=['Đã đọc. Giữ nguyên.'], argue=['{note}. Vậy thôi.'],
        down=['Trả lời kém. Trừ sao.'], sorry=['Tôi nhầm. Sửa lại.']),
    'parent_worried': dict(
        thanks=['Cảm ơn cô/thầy đã phản hồi, gia đình yên tâm ạ.'],
        open={5: ['Cảm ơn cô/thầy nhiều, con về kể vui lắm ạ.', 'Gia đình rất yên tâm khi con học lớp mình.'],
              4: ['Con tiến bộ, gia đình cảm ơn. Chỉ có một điều muốn hỏi thêm ạ.', 'Nhìn chung ổn, nhưng tôi vẫn hơi lo một chút.'],
              3: ['Tôi hơi lo, mong cô/thầy để ý con hơn.', 'Con về kể vài chuyện làm tôi băn khoăn.'],
              2: ['Tôi thật sự lo lắng về buổi học hôm nay.', 'Con về buồn, gia đình muốn được giải thích.'],
              1: ['Tôi rất lo, mong nhà trường xem lại.', 'Gia đình không yên tâm chút nào.']},
        good=['{good} làm gia đình yên tâm.'], bad=['Về {bad}: {note}, tôi hơi lo cho cháu.'],
        accept=['Nghe cô/thầy giải thích tôi yên tâm hơn rồi, cảm ơn ạ.', 'Vậy là tôi hiểu rồi, gia đình sẽ phối hợp cùng lớp.'],
        keep=['Tôi đã đọc, nhưng vẫn mong được theo dõi thêm vài buổi.'],
        argue=['Nhưng con tôi về kể là {note}, tôi vẫn lo lắm.', 'Tôi hiểu, có điều {note} thì gia đình vẫn băn khoăn.'],
        down=['Cô/thầy trả lời vậy làm tôi càng lo hơn.'],
        sorry=['À hóa ra hồ sơ lớp ghi vậy, chắc cháu kể nhầm. Tôi xin lỗi cô/thầy.']),
    'parent_strict': dict(
        thanks=['Ghi nhận. Tiếp tục như vậy.'],
        open={5: ['Tạm ổn. Tôi sẽ tiếp tục theo dõi.', 'Được, giữ như vậy.'],
              4: ['Có một điểm tôi cần giáo viên giải trình.', 'Chưa hoàn toàn hài lòng.'],
              3: ['Tôi yêu cầu giáo viên giải thích rõ.', 'Tôi không đồng ý với cách làm hôm nay.'],
              2: ['Tôi sẽ phản ánh với ban giám hiệu nếu không có giải trình.', 'Như vậy là thiếu trách nhiệm.'],
              1: ['Tôi đề nghị nhà trường xem xét lại giáo viên.', 'Không chấp nhận được.']},
        good=['{good} thì đạt.'], bad=['{bad}: {note}. Tôi cần câu trả lời.', 'Về {bad} — {note}, giáo viên giải thích đi.'],
        accept=['Giải trình có căn cứ. Tôi rút lại phản ánh.', 'Được, có hồ sơ rõ ràng thì tôi chấp nhận.'],
        keep=['Tôi ghi nhận nhưng chưa đồng ý hoàn toàn.'],
        argue=['Tôi không cần lời hứa. {note} là sự thật.', 'Giáo viên đừng né tránh: {note}.'],
        down=['Thái độ như vậy tôi sẽ báo nhà trường.'],
        sorry=['Hồ sơ lớp ghi rõ như vậy thì tôi hiểu nhầm. Tôi rút lại khiếu nại.']),
    'parent_kind': dict(
        thanks=['Cảm ơn cô/thầy nhiều ạ!'],
        open={5: ['Cảm ơn cô/thầy, con thích đến lớp lắm!', 'Buổi học thật ý nghĩa, gia đình cảm ơn ạ.'],
              4: ['Con vui lắm, có một góp ý nhỏ thôi ạ.', 'Cảm ơn cô/thầy, gia đình rất trân trọng.'],
              3: ['Gia đình mong cô/thầy để ý thêm chút ạ.', 'Có vài điều mình cùng trao đổi nhé.'],
              2: ['Hôm nay có chuyện làm con buồn, mình cùng tìm cách nhé.', 'Gia đình hơi tiếc về buổi hôm nay.'],
              1: ['Gia đình mong được gặp để cùng trao đổi.']},
        good=['{good} rất tốt ạ.'], bad=['Có điều {bad}: {note}, mong cô/thầy lưu ý ạ.'],
        accept=['Cảm ơn cô/thầy đã phản hồi tận tình!', 'Vậy là rõ rồi, gia đình sẽ cùng nhắc con ạ.'],
        keep=['Cảm ơn cô/thầy, gia đình sẽ theo dõi thêm ạ.'],
        argue=['Gia đình hiểu, nhưng {note} nên vẫn mong cô/thầy xem lại ạ.'],
        down=['Gia đình hơi buồn vì cách trả lời này ạ.'],
        sorry=['Ôi gia đình nhầm, cảm ơn cô/thầy đã giải thích ạ.']),
    'knowitall': dict(
        thanks=['Ừ, biết điều đấy. Cứ nghe anh là lên.', 'Được. Nhớ lời anh dặn là được.'],
        open={5: ['Tạm được. Anh lăn lộn trong nghề mười năm rồi em ạ, anh khen thế là quý lắm đấy.', 'Cũng biết làm đấy. Nhưng còn phải học anh nhiều.', 'Ừ, được. Anh làm F&B mười năm rồi, ít chỗ qua được mắt anh.'],
              4: ['Được, nhưng anh nói thật: thiếu tinh tế. Anh đi nhiều rồi, nhìn là biết.', 'Bốn sao, còn một sao để em phấn đấu. Anh chấm ít ai được năm lắm.', 'Anh làm dịch vụ mười năm rồi em ạ, cái này mới đạt mức khá.'],
              3: ['Em còn non lắm. Để anh chỉ cho: khách vào là phải đọc được ý khách.', 'Trung bình. Ngày xưa anh mà làm thế này là bị đuổi.', 'Anh không chê, anh góp ý: làm lại quy trình từ đầu đi em.'],
              2: ['Sai cơ bản. Anh làm nghề mười năm chưa thấy ai làm thế.', 'Anh nói thẳng vì anh thương: chỗ này quản lý yếu.', 'Em ơi, cái này anh dạy thực tập sinh ngày đầu tiên đấy.'],
              1: ['Anh không muốn nói nhiều. Đóng cửa đi học lại đi em.', 'Làm ăn kiểu này thì anh cho ba tháng là dẹp.', 'Anh mở ba quán rồi em ạ, chưa thấy chỗ nào như chỗ này.']},
        good=['{good} thì tạm, chắc có người chỉ.', '{good} được, đúng kiểu anh hay dạy nhân viên.'],
        bad=['{bad}: {note}. Cái này sinh viên năm nhất cũng biết em ạ.', 'Về {bad} ({note}), anh chỉ cho: phải có checklist, hiểu chưa?', '{bad} thì hỏng rồi, {note}. Nghe anh, sửa ngay.'],
        accept=['Thấy chưa, nghe anh là đúng. Anh nâng sao cho có động lực.', 'Ừ, biết nhận là tốt. Anh sửa đánh giá, nhớ lời anh đấy.'],
        keep=['Trả lời thì hay, làm thì chưa. Anh giữ nguyên.', 'Anh đọc rồi. Làm được như anh nói đã rồi tính.', 'Em viết dài thế, anh đọc lướt thôi. Sao giữ nguyên.'],
        argue=['Em đừng cãi. {note}, anh nhìn là biết, anh làm nghề mười năm rồi.', 'Em còn trẻ, nghe người đi trước: {note} là sự thật.'],
        down=['Trẻ người non dạ mà dám cãi khách à? Hạ sao. Anh kể cho hội bạn anh biết.', 'Thái độ này thì anh chịu. Hạ sao, khỏi bàn.'],
        sorry=['À… phiếu ghi thế thì chắc hôm đó anh mệt. Thôi anh sửa, nhưng em vẫn phải học thêm.', 'Ừ thì anh nhớ nhầm. Nhưng góp ý của anh vẫn đúng đấy.']),
    'rude': dict(
        thanks=['Ừ.', 'Biết rồi, khỏi cảm ơn.'],
        open={5: ['Ok. Lần này không có gì để chê.', 'Được. Đừng tưởng bở.'],
              4: ['Tạm. Nhân viên mặt như đưa đám.', 'Được, trừ cái kiểu phục vụ uể oải.', 'Bốn sao vì hôm nay tôi vui.'],
              3: ['Làm cho có. Tiền nào của nấy.', 'Bình thường, không hiểu sao nhiều người khen.', 'Phục vụ như ban ơn.'],
              2: ['Chán. Nhân viên như robot hết pin.', 'Làm ăn kiểu gì vậy trời. Phí tiền.', 'Tưởng thế nào. Hóa ra thế.'],
              1: ['Tệ. Đừng ai tới.', 'Mất thời gian. Dẹp cho rồi.', 'Không có sao nào thấp hơn à?']},
        good=['{good} thì được, còn lại thì thôi.', 'Được mỗi {good}.'],
        bad=['{bad}: {note}. Khỏi nói thêm.', '{bad} dở ẹc, {note}.', '{bad}? {note}. Chịu.'],
        accept=['Ờ, xin lỗi vậy thì nghe được. Lên một sao.', 'Thôi được, sửa sao. Đừng để lần sau.'],
        keep=['Nói hay thế. Giữ nguyên.', 'Trả lời dài thế ai đọc. Sao giữ nguyên.', 'Ờ. Thế thôi.'],
        argue=['Cãi à? {note}, rõ như ban ngày.', 'Đổ lỗi cho khách là giỏi. {note} đấy.'],
        down=['Cãi khách à? Chụp màn hình rồi nhé. Hạ sao.', 'Láo. Hạ sao, để xem ai còn dám tới.'],
        sorry=['Ờ thì tôi nhầm. Sửa rồi đấy.', 'Tôi nhầm. Được chưa.']),
    'entitled': dict(
        thanks=['Khách là thượng đế, nhớ nhé.', 'Được. Lần sau nhớ mặt tôi mà ưu tiên.'],
        open={5: ['Được, nhưng lần sau nhớ tặng thêm gì đó cho khách quen.', 'Tốt. Khách như tôi thì phải được đối xử vậy.'],
              4: ['Tôi là khách VIP mà không được ưu tiên, trừ một sao.', 'Ổn, nhưng không ai mời tôi chỗ ngồi đẹp nhất.', 'Tôi xin thêm chút ưu đãi mà không cho, keo quá.'],
              3: ['Tôi đòi đổi chỗ ba lần mà nhân viên cứ lưỡng lự.', 'Khách trả tiền thì muốn gì phải được nấy chứ.'],
              2: ['Tôi yêu cầu gặp quản lý mà không ai ra. Thất vọng.', 'Không giảm giá cho khách quen, tôi không vui.'],
              1: ['Phục vụ không đúng ý tôi thì là dở, đơn giản vậy thôi.', 'Tôi đã nói rõ là phải nhanh gấp đôi. Không đạt.']},
        good=['{good} thì tạm chấp nhận.'],
        bad=['{bad}: {note}. Với khách như tôi thì không được phép.', '{bad} chưa xứng tầm ({note}).'],
        accept=['Vậy mới đúng. Có quà cho khách thì tôi nâng sao.', 'Được, biết chiều khách thì tôi sửa đánh giá.'],
        keep=['Xin lỗi suông thì ai chẳng nói. Tôi cần thấy thành ý.', 'Chưa đủ. Khách quen phải có ưu đãi chứ.'],
        argue=['Tôi là khách, tôi nói {note} thì là vậy.', 'Đừng giải thích, khách không cần biết. {note}.'],
        down=['Dám nói vậy với khách à? Hạ sao, khỏi quay lại.', 'Hỗn. Tôi sẽ kể cho cả công ty biết.'],
        sorry=['Ừ thì phiếu ghi vậy. Nhưng lần sau vẫn phải chiều khách hơn.', 'Được rồi, tôi sửa. Nhưng nhớ ưu tiên tôi.']),
    'drama': dict(
        thanks=['Ok, lần này tha nha.', 'Thấy thành ý rồi, mình không đăng nữa.'],
        open={5: ['Lần này ổn, chưa có gì để bóc 😏', 'Được á, tạm thời không lên group.'],
              4: ['Ổn nhưng có một điểm mình note lại, lần sau là lên group đó.', 'Tạm được, mình đang theo dõi nha.'],
              3: ['Có vài chỗ mình chụp lại rồi, tự xem đi.', 'Chưa ổn, mình giữ ảnh làm bằng chứng.'],
              2: ['Mình đang cân nhắc đăng lên group Review cả khu. Tự hiểu nha.', 'Nếu không có lời giải thích, mình sẽ bóc phốt đó.'],
              1: ['Đã chụp màn hình, tối nay lên group bóc phốt. Muốn yên thì hoàn tiền.', 'Đền bù đi, không thì cả phố biết.', 'Bài bóc phốt mình viết sẵn rồi, chỉ chờ bấm đăng.']},
        good=['{good} thì công nhận.'],
        bad=['{bad}: {note}. Có ảnh làm bằng chứng nhé.', '{bad} thế này ({note}) lên group là bão đó.'],
        accept=['Ok, thấy có thành ý nên mình gỡ bài nháp. Sửa sao.', 'Được, đền bù rồi thì mình không đăng nữa.'],
        keep=['Nói suông thôi hả? Mình vẫn giữ ảnh đó.', 'Chưa thấy thành ý, mình giữ nguyên.'],
        argue=['Chối à? {note}, ảnh còn đây.', 'Đừng lươn lẹo nha, {note}.'],
        down=['Ok, chụp màn hình câu này rồi. Lên group liền.', 'Trả lời vậy hả? Chờ bài bóc phốt tối nay nhé.'],
        sorry=['Ờ… xem lại thì đúng là mình nhầm. Mình không đăng nữa.', 'Thôi, mình rút lại, nói đúng rồi.']),
    'troll': dict(
        thanks=['Ok 👍', 'Ừ ừ.'],
        open={5: ['5 sao cho vui 😂', 'Chấm bừa 5 sao, chưa đọc kỹ.'],
              4: ['4 sao, lý do thì quên rồi.', 'Cũng được, chắc vậy.'],
              3: ['3 sao cho an toàn.', 'Tạm tạm.'],
              2: ['Không thích lắm, không nhớ vì sao.', 'Hai sao, cảm tính thôi.'],
              1: ['1 sao, hết.', 'Thích thì chấm thôi 🤷']},
        good=['{good} chắc ổn.'],
        bad=['{bad} thì hình như không ổn.'],
        accept=['Ờ thôi, lên thêm một sao cho vui.', 'Ok, trả lời nhiệt tình vậy thì thêm sao 😅'],
        keep=['Ờ kệ, sao để vậy.', 'Trả lời làm gì, mình chấm cho vui mà 😂', 'Lười sửa lắm, để vậy đi.'],
        argue=['Mình thấy vậy thì mình chấm vậy thôi.', 'Tranh luận chi mệt, {note} đó.'],
        down=['Ơ cay à? Hạ luôn cho đủ bộ 😂', 'Nóng tính ghê, hạ luôn.'],
        sorry=['Ờ nhầm, sửa rồi đó.', 'Thôi nhầm thật, sửa lại.']),
    'parent_knowitall': dict(
        thanks=['Được. Cô/thầy cứ theo hướng tôi góp ý là ổn.'],
        open={5: ['Tạm ổn. Tôi cũng từng đứng lớp, nhìn là biết cô/thầy có cố.', 'Được, đúng phương pháp tôi vẫn đọc trên mạng.'],
              4: ['Khá, nhưng tôi thấy nên dạy theo kiểu Nhật, con tự lập hơn.', 'Tôi làm giáo dục lâu rồi, góp ý cô/thầy vài điểm.'],
              3: ['Phương pháp cũ quá. Bây giờ người ta dạy khác rồi cô/thầy ạ.', 'Tôi đọc nhiều sách giáo dục, cách này chưa ổn.'],
              2: ['Dạy vậy là sai phương pháp. Tôi đề nghị đổi cách ngay.', 'Tôi dạy con ở nhà còn hiệu quả hơn.'],
              1: ['Tôi nghĩ cô/thầy nên đi học lại nghiệp vụ sư phạm.', 'Tôi sẽ đề xuất nhà trường cho tôi dự giờ.']},
        good=['{good} là nhờ gia đình kèm thêm ở nhà.'],
        bad=['{bad}: {note}. Tôi mà dạy thì không có chuyện đó.', 'Về {bad} ({note}), cô/thầy nên tham khảo cách dạy của tôi.'],
        accept=['Thấy chưa, nghe phụ huynh góp ý là tiến bộ. Tôi sửa đánh giá.', 'Được, cô/thầy chịu tiếp thu là tốt.'],
        keep=['Tôi ghi nhận, nhưng tôi vẫn giữ quan điểm.', 'Cảm ơn, nhưng làm được rồi hãy nói.'],
        argue=['Cô/thầy đừng giải thích, {note} là tôi thấy rõ.', 'Tôi có kinh nghiệm hơn, {note} là thật.'],
        down=['Cô/thầy trả lời phụ huynh như vậy à? Tôi sẽ nêu trong họp phụ huynh.', 'Thái độ này tôi phản ánh lên nhà trường.'],
        sorry=['À, sổ lớp ghi vậy thì tôi nhầm. Nhưng góp ý của tôi vẫn có giá trị.', 'Ừ thì tôi hiểu sai. Tôi sửa lại.']),
    'parent_rude': dict(
        thanks=['Ừ.', 'Được.'],
        open={5: ['Được. Cứ thế mà làm.', 'Tạm. Không có gì phải nói.'],
              4: ['Nhắn nhóm Zalo cả tối mới thấy trả lời. Bốn sao.', 'Được, nhưng đừng để tôi phải nhắc.'],
              3: ['Cô/thầy dạy kiểu gì mà con về chẳng nói được gì?', 'Học phí thì thu đủ, còn dạy thì thế này.'],
              2: ['Nói thật, lớp này chán. Tôi đang tính chuyển lớp cho con.', 'Tôi đóng tiền không phải để con ngồi chơi.'],
              1: ['Dạy dở thì nghỉ đi cho người khác dạy.', 'Tôi nói luôn trong nhóm lớp: không chấp nhận được.']},
        good=['{good} thì được.'],
        bad=['{bad}: {note}. Trả lời đi.', '{bad} thế ({note}) mà cũng gọi là dạy.'],
        accept=['Ờ, trả lời vậy thì nghe được.', 'Được rồi, tôi sửa. Đừng để lặp lại.'],
        keep=['Nói nhiều làm gì, làm đi.', 'Đọc rồi. Chưa ưng.'],
        argue=['Đừng có cãi phụ huynh. {note}.', 'Tôi nói rồi: {note}.'],
        down=['Cô/thầy dám nói phụ huynh vậy à? Tôi đưa lên nhóm lớp cho mọi người xem.', 'Láo. Mai tôi lên gặp hiệu trưởng.'],
        sorry=['Thôi, tôi nhầm. Được chưa.', 'Ờ, sổ ghi vậy thì tôi sai.']),
}

# ------------------------------------------------------------ twists
# Careless or fake reviews. `stranger`: the author is not the person served.
# `reportable`: the platform (or the class board) removes it when reported.
TWISTS = {
    'offtopic': dict(group='customer', persona='troll', stranger=True, reportable=True, clues=['Không nói gì về dịch vụ đã dùng']),
    'no_visit': dict(group='customer', persona='troll', stranger=True, reportable=True, clues=['Tự nhận chưa dùng dịch vụ']),
    'wrong_shop': dict(group='customer', persona='troll', stranger=True, reportable=True, clues=['Có vẻ đánh giá nhầm quán']),
    'competitor': dict(group='customer', persona='rude', stranger=True, reportable=True, clues=['Tài khoản mới, đây là đánh giá đầu tiên', 'Nhắc tới một tiệm khác']),
    'flip_low': dict(group='any', persona=None, stranger=False, reportable=False, clues=['Lời khen mà chấm 1★']),
    'flip_high': dict(group='customer', persona=None, stranger=False, reportable=False, clues=['Lời chê mà chấm 5★']),
    'bocphot': dict(group='customer', persona='drama', stranger=False, reportable=False, clues=['Dọa bóc phốt, đòi đền']),
    'demand': dict(group='customer', persona='entitled', stranger=False, reportable=False, clues=['Đòi hỏi ngoài dịch vụ']),
    'offtopic_p': dict(group='parent', persona='parent_rude', stranger=False, reportable=True, clues=['Không nói gì về buổi học']),
    'wrong_class': dict(group='parent', persona='parent_worried', stranger=True, reportable=True, clues=['Có vẻ nhắn nhầm lớp']),
    'rumor': dict(group='parent', persona='parent_knowitall', stranger=False, reportable=False, clues=['Nghe kể lại, không trực tiếp']),
    'pile_on': dict(group='any', persona=None, stranger=True, reportable=True, clues=['Kéo tới từ câu trả lời gắt của bạn']),
}
# Góp ý #196/#168 (06/10): every review can be reported. These kinds are removed from the average when reported
# (the record stays, marked `report: 'accepted'`), whatever an older save stored in twist['reportable'].
REMOVABLE = ('offtopic', 'offtopic_p', 'pile_on', 'no_visit', 'wrong_shop', 'competitor', 'wrong_class')
# Chat C#23729 / F#188: "nhầm quán" reviews were too frequent (weight 2 → 1).
TWIST_WEIGHTS = {'customer': (('offtopic', 3), ('no_visit', 2), ('wrong_shop', 1),('competitor', 2), ('flip_low', 2), ('flip_high', 2), ('bocphot', 2), ('demand', 2)),
                 'parent': (('offtopic_p', 3), ('wrong_class', 2), ('flip_low', 2), ('rumor', 2))}
TWIST_TEXT = {
    'offtopic': ['Không có chỗ đậu ô tô, phải gửi xe tận đầu hẻm. 1 sao.', 'Đường vào đang đào, bụi mù mịt. Một sao cho nhớ.',
                 'Trời mưa to quá, ướt hết cả người. Chán.', 'Wifi yếu, lướt video cứ đứng hình. 1 sao.', 'Nhạc mở không hợp gu tôi.',
                 'Bảo vệ tòa nhà bên cạnh nói chuyện cộc lốc.', 'Bản đồ chỉ đường sai, đi lạc cả buổi. Bực.',
                 'Hôm nay tôi bị sếp mắng nên chấm 1 sao.', 'Giá gửi xe đầu hẻm đắt quá trời.', 'Ghế chờ hơi thấp, ngồi đau lưng. 1 sao.'],
    'no_visit': ['Chưa ăn nhưng nhìn ảnh là thấy không ngon rồi.', 'Đi ngang thấy đông quá nên thôi, cho 1 sao.', 'Nghe đứa bạn kể là dở, tin bạn tôi.',
                 'Chưa ghé bao giờ nhưng tên nghe không sang.', 'Xem trên mạng thấy người ta chê nên tôi cũng chê.', 'Chưa thử, nhưng nhìn bảng hiệu là biết không ổn.'],
    'competitor': ['Dở, đắt, phục vụ chậm. Mọi người qua tiệm đầu hẻm đi, ngon gấp đôi mà rẻ.', 'Tôi thử rồi, thua xa tiệm ở ngã tư. Đừng phí tiền.',
                   'Nhân viên thái độ, không sạch sẽ. Mọi người chọn chỗ uy tín hơn, ví dụ tiệm bên kia đường.', '1 sao. Tiệm mới mở bên cạnh mới đúng là chuẩn.',
                   'Thất vọng toàn tập. Ai cần thì inbox, tôi chỉ chỗ khác tốt hơn.'],
    'demand': ['Tôi xin thêm chút ưu đãi mà không cho. Khách quen mà keo thế.', 'Tôi muốn được làm trước vì tôi đang vội, vậy mà vẫn phải xếp hàng.',
               'Tôi đòi gặp chủ để xin giảm giá, nhân viên bảo không có. Thất vọng.', 'Khách VIP như tôi mà không được tặng gì. Kỳ.',
               'Tôi yêu cầu làm theo cách của tôi, nhân viên cứ giải thích quy trình. Mệt.'],
    'bocphot': ['Đã chụp màn hình, tối nay lên group bóc phốt. Muốn yên thì hoàn tiền. Soi kỹ thì {label} chưa ổn đâu.',
                'Đền bù đi, không thì cả phố biết. {Label} như vậy mà cũng dám nhận tiền.',
                'Bài bóc phốt mình viết sẵn rồi, chỉ chờ bấm đăng. Mình giữ ảnh {label} làm bằng chứng.',
                'Mình là admin group Review cả khu nha. {Label} thế này thì hoàn tiền, không thì lên sóng.'],
    'offtopic_p': ['Trường không có chỗ đỗ ô tô cho phụ huynh, sáng nào cũng tắc.', 'Căng tin bán đồ ăn vặt đắt quá.', 'Đồng phục năm nay màu xấu, tôi không thích.',
                   'Cổng trường mở muộn năm phút, tôi trễ giờ làm.', 'Nhóm Zalo lớp nhiều tin quá, tôi tắt thông báo rồi.'],
    'wrong_class': ['Cô ơi lớp Chồi 3 mai có học bơi không ạ? Sao chưa thấy thông báo, tôi bực lắm.', 'Bài tập toán lớp Năm khó quá, con tôi khóc cả tối. Một sao.',
                    'Sao lớp Lá 2 hôm nay không cho bé ngủ trưa? Tôi rất không hài lòng.', 'Thầy chủ nhiệm lớp 9A trả sổ liên lạc chậm quá.'],
    'rumor': ['Nghe nhóm phụ huynh nói lớp mình học chậm hơn lớp bên, tôi rất thất vọng.', 'Tôi nghe kể hôm nay lớp ồn lắm, giáo viên không quản được.',
              'Có phụ huynh bảo cô/thầy hay để các cháu tự chơi. Tôi chưa hỏi con nhưng thấy lo.'],
}
# Other trades' reviews, for the wrong-shop twist; never the player's own trade.
WRONG_SHOP = (('food', 'Phở tái nguội ngắt, nước dùng nhạt như nước lã. 1 sao.'), ('food', 'Bún chả ít thịt, nước chấm ngọt lịm. Không quay lại.'),
              ('drink', 'Trà sữa ngọt khé, trân châu cứng như sỏi.'), ('drink', 'Cà phê muối mà chẳng thấy vị muối đâu, phí tiền.'),
              ('repair', 'Vá cái săm xe mà mất cả tiếng, còn nói giá trên trời.'), ('salon', 'Uốn tóc xong xù như tổ quạ, về nhà khóc cả tối.'),
              ('pet', 'Tắm cho con mèo mà về nó vẫn hôi, lại còn cắt móng lệch.'), ('stay', 'Phòng “view săn mây” mà mở cửa ra toàn tường nhà bên.'),
              ('flower', 'Đặt bó hồng đỏ mà giao hồng phấn, héo cả cánh.'), ('shop', 'Mua bỉm size L mà giao size M, gọi không ai nghe máy.'),
              ('pharmacy', 'Hỏi mua vitamin C cũng không có, nhà thuốc gì kỳ vậy.'), ('delivery', 'Shipper giao muộn cả buổi, hộp bánh móp méo.'),
              ('farm', 'Rau mua về héo rũ, trứng vỡ hai quả.'), ('office', 'Làm hồ sơ vay mà hẹn tới hẹn lui, nhân viên ngân hàng thiếu nhiệt tình.'),
              ('car', 'Rửa xe ô tô mà mâm còn nguyên vết bùn.'), ('gym', 'Phòng gym đông nghẹt, máy chạy bộ hỏng hai cái.'))
DOMAIN = {'milk_tea': 'drink', 'cafe_bakery': 'drink', 'restaurant': 'food', 'mother_baby': 'shop', 'grocery': 'shop', 'pharmacy': 'pharmacy',
          'accounting': 'office', 'corp_accounting': 'office', 'tax_payroll': 'office', 'group_accounting': 'office', 'customer_care': 'office',
          'tour_guide': 'stay', 'homestay': 'stay', 'florist': 'flower', 'repair': 'repair', 'farm': 'farm', 'delivery': 'delivery',
          'pet_care': 'pet', 'salon': 'salon', 'clothing': 'shop', 'tra_da': 'drink', 'pet_shop': 'pet',
          'fruit': 'shop', 'garbage': 'delivery', 'drain': 'repair', 'homemaker': 'stay', 'ice_cream': 'food', 'pho': 'food', 'com': 'food', 'nail': 'salon', 'pagoda': 'pagoda', 'photobooth': 'shop', 'giupviec': 'stay', 'naucom': 'stay', 'babysitter': 'stay', 'library': 'office',
          'hr_admin': 'office', 'secretary': 'office', 'it_helpdesk': 'office', 'nurse': 'pharmacy', 'lifeguard': 'gym'}
# How twist reviewers answer a polite reply.
TWIST_REPLY = {
    'flip_fix': ['Ơ, mình bấm nhầm sao thật! Sửa lại liền, xin lỗi nha 🙏', 'Trời, tay nhanh hơn não, mình chấm nhầm. Sửa rồi nè.', 'Ủa sao lại 1 sao, mình đâu định vậy. Sửa ngay!'],
    'flip_fix_parent': ['Ôi tôi bấm nhầm sao, xin lỗi cô/thầy. Tôi sửa lại rồi ạ.', 'Nhờ cô/thầy nhắc, tôi mới thấy mình chấm nhầm. Sửa rồi ạ.'],
    'flip_keep': ['Ừ thì góp ý vậy thôi, sao cứ để nguyên.', 'Mình chấm 5 sao vì quý, còn góp ý là thật đó nha.'],
    'wrong_shop': ['Ơ… hình như tôi nhầm chỗ thật. Mà thôi, lười sửa lắm.', 'Ủa đây không phải chỗ hôm qua hả? Kệ, chắc cũng vậy.', 'Nhầm hay không thì tôi vẫn chấm vậy.'],
    'wrong_class': ['Ơ chết, tôi nhắn nhầm nhóm lớp. Mà thôi để đó, lát tôi xóa.', 'Ủa đây không phải lớp của con tôi à? Kệ, để mai tính.'],
    'no_visit': ['Để hôm nào rảnh ghé thử, giờ cứ để vậy.', 'Chưa thử nhưng nhìn là biết, khỏi mời.'],
    'competitor': ['Nói gì thì nói, tiệm bên kia vẫn hơn.', 'Tôi chỉ nói thật thôi, ai tin thì tin.'],
    'offtopic': ['Biết là không phải lỗi bên bạn, nhưng tôi vẫn bực.', 'Giải thích làm gì, tôi chấm theo cảm xúc.'],
    'offtopic_soft': ['Thôi thấy trả lời lễ phép, thêm một sao.', 'Ừ, không phải lỗi bên bạn thật. Thêm sao nè.'],
    'pile_on': ['Nói chuyện với khách thế thì tôi vẫn giữ ý kiến.', 'Đọc rồi. Mong lần sau bình tĩnh hơn.'],
    'pile_on_soft': ['Ờ, biết xin lỗi thì còn đỡ. Nâng lên chút.', 'Thấy chịu nhận sai nên tôi bớt giận.'],
}
PILE_ON = {
    'customer': ['Đọc câu trả lời khách mà sốc. Một sao, khỏi ghé.', 'Thái độ với khách thế này thì tốt mấy cũng thôi.',
                 'Ai đưa bài này lên group vậy? Xin phép né 🙃', 'Khách góp ý mà trả lời vậy à? Bỏ theo dõi.',
                 'Từng ghé một lần, giờ đọc cách trả lời khách thì chắc không quay lại.'],
    'parent': ['Đọc tin nhắn cô/thầy trả lời phụ huynh trong nhóm lớp mà tôi sốc.', 'Phụ huynh góp ý mà nhận câu trả lời vậy, tôi cũng lo cho con mình.',
               'Tôi ủng hộ phụ huynh kia. Giáo viên không nên nói vậy.'],
    'report': ['Chủ quán đi báo cáo đánh giá thật của khách à? Một sao ủng hộ bạn kia.', 'Góp ý thật mà bị báo cáo, vậy thì tôi cũng một sao.'],
    'report_parent': ['Phụ huynh góp ý thật mà bị báo cáo, tôi thấy không ổn.', 'Tôi đứng về phía phụ huynh kia. Góp ý thì phải nghe chứ.'],
    'phot': ['Thấy bài bóc phốt trên group rồi, thôi né.', 'Group review đang bàn tán chỗ này, một sao đồng cảm với bạn kia.',
             'Bạn kia bóc phốt mà không ai lên tiếng giải thích à? Một sao.'],
}
PILE_NOTE = {'rude': 'trả lời gắt trên mạng', 'phot': 'im lặng trước lời tố', 'report': 'báo cáo đánh giá thật'}
PILE_CLUE = {'rude': 'Kéo tới từ câu trả lời gắt của bạn', 'phot': 'Kéo tới từ bài bóc phốt', 'report': 'Kéo tới vì bạn báo cáo nhầm'}
REPORT_ANGRY = {
    'customer': ['Báo cáo tôi à? Tôi trải nghiệm thật mà. Hạ thêm sao.', 'Còn đi báo cáo khách? Hay lắm, hạ sao cho đủ.', 'Nền tảng giữ bài tôi rồi nhé. Báo cáo bừa là hạ sao.'],
    'parent': ['Cô/thầy báo cáo tin nhắn của phụ huynh à? Tôi sẽ nói chuyện với nhà trường.', 'Tôi góp ý thật mà bị báo cáo, tôi rất buồn và hạ đánh giá.'],
}

APOLOGY = ('xin loi', 'sorry', 'loi cua', 'rut kinh nghiem', 'that xin', 'mong thong cam', 'thanh that', 'ghi nhan', 'cam on gop y', 'cam on phan hoi', 'tiep thu')
FIX = ('lan sau', 'se sua', 'da sua', 'lam lai', 'doi mon', 'hoan', 'tang', 'giam', 'bu', 'voucher', 'khac phuc', 'cai thien', 'dieu chinh', 'kiem lai', 'nhac nhan vien', 'quy trinh', 'se chu y')
FACTS = ('theo phieu', 'phieu ghi', 'hoa don', 'camera', 'ghi nhan', 'ho so', 'bien ban', 'don ghi', 'order', 'da xac nhan', 'so lop', 'diem danh', 'phieu cuoi tiet', 'chung tu', 'lich trinh')
BLAME = ('khong phai loi', 'tai anh', 'tai chi', 'tai ban', 'khach sai', 'bia', 'vo ly', 'kho tinh', 'dung co', 'ai bao', 'tu chiu')
# Insults are matched as whole words WITH their tone marks ("ngu" is not "ngủ"
# or "người", "chó" is not "cho"); rude phrases without marks are matched on
# the normalised text as whole words.
RUDE_WORDS = ('ngu', 'cút', 'điên', 'im đi', 'vô học', 'rác', 'chó', 'đồ điên', 'mất dạy', 'xéo', 'láo', 'khùng', 'hãm', 'đm', 'vcl', 'vl', 'óc chó', 'ngu ngốc', 'dở hơi')
RUDE = ('di cho khac', 'khoi ghe', 'khong tiep', 'khong thich thi', 'loai khach', 'lam nhu dung roi', 'biet gi ma', 'lo chuyen cua', 'chuyen lop khac',
        'kem hieu biet', 'nha que', 'ke ban', 'thich thi di', 'khong can khach', 'hang dau buoi')
# A report the platform does not accept (góp ý #196): the reviewer noticed, but keeps the same stars.
REPORT_KEEP = {
    'customer': ['Báo cáo tôi à? Tôi kể đúng trải nghiệm thật mà. Thôi, để nguyên vậy.', 'Nền tảng giữ bài tôi rồi nhé. Lần sau đọc kỹ rồi hẵng báo cáo.',
                 'Ủa, góp ý thật mà cũng bị báo cáo? Hơi buồn đó nha.'],
    'parent': ['Cô/thầy báo cáo tin nhắn của phụ huynh à? Tôi góp ý thật lòng mà.', 'Tôi góp ý thật mà bị báo cáo, tôi hơi buồn.'],
    'pagoda': ['Tôi kể thật lòng mà bị báo cáo, hơi buồn.', 'Cảm nhận thật mà bị báo cáo. Thôi, tôi để đó.'],
}
OFFERS = {'none': 0, 'gift': 10, 'refund': 20}
REPORTS_PER_DAY = 3


def _plain_review(post: dict) -> bool:
    """A review a shift event wrote straight on the feed (no thread): reportable, never removed."""
    return post.get('kind') == 'review' and bool(post.get('stars')) and not post.get('feedback') and post.get('npc') != 'player'


def reports_today(c: dict) -> int:
    return sum(1 for f in c['feed'] if (f.get('feedback') or {}).get('report_day') == c['day'] or f.get('reported') == c['day'])


def removable(post: dict) -> bool:
    """Would the platform take this review out of the average when reported? Fakes, wrong shops, off-topic 1★
    and pile-ons always (whatever an older save stored), and a gripe that took a star for something off-topic."""
    fb = post.get('feedback') or {}
    if _kind(fb) in REMOVABLE or (fb.get('twist') or {}).get('reportable'):
        return True
    g = fb.get('gripe')
    return bool(isinstance(g, dict) and not g.get('positive') and g.get('dropped') and (fb.get('unfair') or {}).get('gripe'))


def _has(text: str, words) -> bool:
    return any(re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text) for w in words)


def normalize(text: str) -> str:
    t = unicodedata.normalize('NFD', (text or '').lower()).replace('đ', 'd')
    return ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn')


def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def persona_for(career: str, npc: str) -> str:
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    if mod:
        for i, row in enumerate(mod.SPEC.get('people', [])):
            if f'{career}_npc_{i + 1:02d}' == npc and len(row) > 3 and row[3] in PERSONAS:
                return row[3]
    pool = PARENT_PERSONAS if career == 'teacher' else CUSTOMER_PERSONAS
    return pool[_hash(npc) % len(pool)]


def _criteria_default(c: dict, t: dict) -> list[dict]:
    """Criteria for the seven v0.1–v0.3 careers, derived from recorded facts."""
    m = t.get('mistakes', 0)
    patience = t.get('patience', 100)
    wait = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    acc = 5 if m == 0 else 4 if m <= 2 else 3
    cid = t['career']
    rows = []
    if cid == 'mother_baby':
        rows = [('accuracy', 'Đúng món', acc, 'đổi món trước khi chốt' if m else 'đúng món, đúng số lượng'),
                ('presentation', 'Gói quà', 5 if (t.get('pack') or not (t.get('needs') or {}).get('gift')) else 3, 'gói đúng màu đã chọn' if t.get('pack') else 'không cần gói'),
                ('speed', 'Thời gian chờ', wait, f'kiên nhẫn còn {patience}%')]
    elif cid == 'pharmacy':
        rows = [('accuracy', 'Đúng mã, đúng lô', acc, 'có lấy nhầm rồi đổi lại' if m else 'kiểm đủ mã, lượng, lô'),
                ('care', 'Cẩn thận', 5 if t.get('checked') or t.get('status') == 'referred' else 3, 'đã kiểm ba bước'),
                ('speed', 'Thời gian chờ', wait, f'kiên nhẫn còn {patience}%')]
    elif cid == 'accounting':
        rows = [('accuracy', 'Chính xác', acc, 'có ghép sai rồi sửa' if m else 'mọi nhóm khớp nguồn'),
                ('clarity', 'Giải thích rõ', 5, 'có bảng đối chiếu kèm nguồn'), ('speed', 'Đúng hẹn', wait, f'nhịp chờ còn {patience}%')]
    elif cid == 'customer_care':
        rows = [('resolution', 'Giải quyết tới nơi', 5 if t.get('confirmed') else 4, 'đã có kết quả xác nhận'),
                ('accuracy', 'Hiểu đúng vấn đề', acc, 'có chọn phương án chưa hợp' if m else 'xem đủ chứng cứ'),
                ('speed', 'Tốc độ', wait, f'kiên nhẫn còn {patience}%')]
    elif cid == 'teacher' and t.get('room'):
        # The class-period mode keeps its facts in t['room'].
        room = t['room']
        marked = len(room.get('marks') or {}) >= len(room.get('tickets') or {})
        rows = [('care', 'Quan tâm từng bạn', acc, 'có bạn phải đổi cách giảng' if m else 'mỗi bạn được giúp đúng cách'),
                ('feedback', 'Nhận xét riêng', 5 if marked else 3, 'mỗi phiếu có phản hồi riêng' if marked else 'còn phiếu chưa được nhận xét'),
                ('order', 'Nề nếp lớp', 5 if len(room.get('roll') or {}) >= len(room.get('kids') or []) else 3, 'điểm danh đầy đủ')]
    elif cid == 'tour_guide' and t.get('trip'):
        trip = t['trip']
        over = trip.get('clock', 0) > trip.get('limit', 10**6)
        rows = [('safety', 'An toàn đoàn', acc, 'có lúc để khách lẻ loi' if m else 'kiểm đủ người mỗi điểm'),
                ('story', 'Câu chuyện', acc, 'có đoạn đoàn chưa hứng thú' if m else 'kể chuyện hợp ý đoàn'),
                ('pace', 'Nhịp đi', 3 if over else wait, 'về trễ giờ hẹn' if over else f'nhịp đoàn còn {patience}%')]
    elif cid == 'teacher':
        rows = [('care', 'Quan tâm từng bạn', acc, 'có bạn phải đổi cách giảng' if m else 'mỗi bạn được giúp đúng cách'),
                ('feedback', 'Nhận xét riêng', 5 if t.get('feedback') else 3, 'mỗi phiếu có phản hồi riêng'),
                ('order', 'Nề nếp lớp', 5 if len(t.get('attendance', {})) == len(t.get('students', [])) else 3, 'điểm danh đầy đủ')]
    elif cid == 'tour_guide':
        rows = [('safety', 'An toàn đoàn', 5, 'kiểm đủ người mỗi điểm'), ('story', 'Câu chuyện', acc, 'có kể nhầm rồi sửa' if m else 'kể chuyện đúng và hay'),
                ('pace', 'Nhịp đi', wait, f'nhịp đoàn còn {patience}%')]
    elif cid == 'milk_tea':
        rows = [('accuracy', 'Đúng vị đã gọi', acc, 'phải làm lại ly' if m else 'đúng trà, topping, đường đá'),
                ('speed', 'Thời gian chờ', wait, f'kiên nhẫn còn {patience}%'), ('attitude', 'Hỏi kỹ trước khi pha', 5 if t.get('known') else 3, 'đã hỏi rõ món')]
    else:
        rows = [('accuracy', 'Chính xác', acc, 'có sai rồi sửa' if m else 'làm đúng yêu cầu'), ('speed', 'Thời gian chờ', wait, f'kiên nhẫn còn {patience}%')]
    return [dict(key=k, label=l, score=max(1, min(5, int(sc))), note=n) for k, l, sc, n in rows]


def evaluate(c: dict, t: dict, status: str) -> dict:
    from .careers import PLUGINS
    mod = PLUGINS.get(t['career'])
    if t.get('desk'):
        from . import desk as mod  # paperwork desks grade their own stamps
    if mod and hasattr(mod, 'feedback'):
        raw = mod.feedback(c, t) or {}
        criteria = [dict(key=x['key'], label=x['label'], score=max(1, min(5, int(x['score']))), note=str(x.get('note', ''))[:200]) for x in raw.get('criteria', [])]
        cap = raw.get('cap', 5)
        base = raw.get('stars')
    else:
        criteria = _criteria_default(c, t)
        cap = 5
        base = None
    if not criteria:
        criteria = [dict(key='overall', label='Tổng thể', score=5 if t.get('mistakes', 0) == 0 else 4, note='đã hoàn tất')]
    from . import consequences as _cq  # recorded order mistakes pull stars down by severity
    criteria, cap = _cq.adjust(t, criteria, cap)
    if base is None:
        low = min(x['score'] for x in criteria)
        avg = sum(x['score'] for x in criteria) / len(criteria)
        base = round(min(avg, low + 1.5))
    return dict(criteria=criteria, stars=max(1, min(5, cap, int(base))), cap=max(1, min(5, int(cap))))


def legacy_stars(t: dict) -> int:
    return 5 if t['mistakes'] == 0 else 4 if t['mistakes'] <= 2 else 3


def compose(persona: str, stars: int, criteria: list[dict], seed: int, unfair: dict | None = None) -> str:
    v = VOICE[persona]
    pick = lambda rows, k=0: rows[(seed + k) % len(rows)]
    parts = [pick(v['open'][max(1, min(5, stars))])]
    best = max(criteria, key=lambda x: x['score'])
    worst = min(criteria, key=lambda x: x['score'])
    if unfair:
        parts.append(pick(v['bad'], 1).format(bad=unfair['label'], note=unfair['claim']))
    elif worst['score'] <= 3:
        parts.append(pick(v['bad'], 1).format(bad=worst['label'], note=worst['note']))
    if best['score'] >= 4 and (not unfair or best['key'] != unfair['key']):
        parts.append(pick(v['good'], 2).format(good=best['label']))
    return ' '.join(parts)[:600]


UNFAIR_CLAIMS = {
    'speed': 'đợi lâu muốn xỉu', 'accuracy': 'không giống cái tôi dặn', 'attitude': 'nhân viên không cười với tôi',
    'presentation': 'trình bày nhìn không sang', 'care': 'con tôi bảo không được để ý', 'feedback': 'bài con tôi không được nhận xét gì',
    'order': 'lớp ồn ào quá', 'taste': 'vị không giống lần trước', 'quality': 'chất lượng không như quảng cáo',
}


def teacher_title(s: dict, text: str) -> str:
    """Parents write "cô/thầy"; use the player's own title once it is known."""
    gender = (s.get('journey') or {}).get('gender') if isinstance(s.get('journey'), dict) else None
    if gender not in ('male', 'female'):
        return text
    small = 'thầy' if gender == 'male' else 'cô'
    return text.replace('cô/thầy', small).replace('Cô/thầy', small.capitalize())


def twist_rate(day: int) -> float:
    """Share of finished jobs whose review is careless or fake. None early on."""
    return 0.0 if day < 3 else 0.07 if day < 6 else 0.12 if day < 10 else 0.16


def mood_rate(day: int) -> float:
    """Share of the remaining reviews written by someone on a bad day."""
    return 0.0 if day < 3 else 0.08 if day < 6 else 0.12 if day < 10 else 0.15


def _roll(*parts) -> float:
    return _hash('roll', *parts) % 10000 / 10000


def pick_twist(career: str, group: str, fair: int, seed: int) -> str:
    rows = [(k, w) for k, w in TWIST_WEIGHTS[group]
            if not (k == 'flip_low' and fair < 4) and not (k == 'rumor' and fair < 4) and not (k == 'flip_high' and fair > 3)]
    total = sum(w for _, w in rows)
    x = seed % total
    for k, w in rows:
        if x < w:
            return k
        x -= w
    return rows[-1][0]


def _stranger(career: str, served: str, seed: int) -> str:
    """Another customer of the same trade (chat C#23729: names from other trades made reviews look like they were
    about another shop); only a trade with nobody else falls back to the whole street."""
    from .content import NPCS
    pool = [n['id'] for n in NPCS if n['id'].startswith(career + '_npc_') and n['id'] != served]
    if not pool:
        pool = [n['id'] for n in NPCS if n['id'] != served]
    return pool[seed % len(pool)] if pool else served


def twist_review(career: str, kind: str, persona: str, fair: int, criteria: list[dict], seed: int) -> tuple[int, str]:
    """(stars, text) for a careless or fake review."""
    pick = lambda rows, k=0: rows[(seed // 7 + k) % len(rows)]
    worst = min(criteria, key=lambda x: x['score'])
    if kind == 'wrong_shop':
        own = DOMAIN.get(career)
        return 1 + seed % 2, pick([txt for dom, txt in WRONG_SHOP if dom != own])
    if kind == 'flip_low':
        return 1, compose(persona, fair, criteria, seed)
    if kind == 'flip_high':
        return 5, compose(persona, fair, criteria, seed)
    if kind == 'bocphot':
        return 1, pick(TWIST_TEXT['bocphot']).format(label=worst['label'].lower(), Label=worst['label'])
    if kind == 'demand':
        return max(1, min(3, fair - 1)), pick(TWIST_TEXT['demand'])
    if kind == 'no_visit':
        return 1 + seed % 2, pick(TWIST_TEXT['no_visit'])
    if kind in ('offtopic_p', 'rumor'):
        return 2, pick(TWIST_TEXT[kind])
    return 1, pick(TWIST_TEXT[kind])


def make_review(s: dict, c: dict, t: dict, status: str) -> dict:
    """Return dict(text, stars, feedback[, npc, author]) for engine.task_done.

    Every roll is seeded from the task id and day, and the result is stored,
    so a reload never rerolls it."""
    ev = evaluate(c, t, status)
    career = t['career']
    reviewer = t['npc']
    persona = persona_for(career, reviewer)
    group = PERSONAS[persona]['group']
    seed = _hash(t['id'], c['day'])
    stars = legacy_stars(t) if career in ('mother_baby', 'pharmacy', 'accounting', 'customer_care') and not t.get('desk') else ev['stars']
    stars = min(stars, ev['cap'])
    fair = stars
    own = _own_voice(career)
    if own:
        return _own_review(t, persona, stars, ev, own(c, t, persona, stars, ev['criteria'], seed))
    if _pv.on(career):
        # The pagoda's visitors write about calm and kindness, not service (pagoda_voice.py).
        return _pv.make_review(s, c, t, status, ev, persona, stars, seed)
    unfair = twist = None
    clues = []
    out = {}
    text = None
    if status == 'completed' and not t.get('slips') and _roll('twist', t['id'], c['day']) < twist_rate(c['day']):
        kind = pick_twist(career, group, fair, _hash('kind', t['id'], c['day']))
        spec = TWISTS[kind]
        persona = spec['persona'] or persona
        if kind == 'flip_low' and PERSONAS[persona]['bias'] < 0:
            # Praise tapped as 1★ reads best in a friendly voice.
            persona = 'parent_kind' if group == 'parent' else ('warm', 'genz', 'quiet')[seed % 3]
        stars, text = twist_review(career, kind, persona, fair, ev['criteria'], seed)
        twist = dict(kind=kind, reportable=spec['reportable'])
        clues = list(spec['clues'])
        if spec['stranger']:
            npc = _stranger(career, reviewer, seed)
            from .content import NPC_INDEX
            out = dict(npc=npc, author=NPC_INDEX[npc]['display_name'])
    elif stars >= 5 and status == 'completed' and c['day'] >= 2 and seed % 6 == 0:
        # About one perfect job in six meets a customer who remembers it differently.
        crit = ev['criteria'][seed % len(ev['criteria'])]
        unfair = dict(key=crit['key'], label=crit['label'], claim=UNFAIR_CLAIMS.get(crit['key'], 'không như tôi nghĩ'), truth=crit['note'])
        stars = 3 if PERSONAS[persona]['bias'] < 0 else 4
    elif status == 'completed' and _roll('mood', t['id'], c['day']) < mood_rate(c['day']):
        pool = MOOD_PARENT if group == 'parent' else MOOD_CUSTOMER
        persona = pool[_hash('mood', t['id']) % len(pool)]
        # "Năm sao là cho chỗ hoàn hảo": a bad day shaves the top star.
        if stars >= 5 and persona != 'drama':
            stars = 4
        # A red herring: harsh, new account, but a real visit.
        if persona in ('rude', 'parent_rude') and seed % 3 == 0:
            clues = ['Tài khoản mới, đây là đánh giá đầu tiên']
    item = _fv.topic(t)
    gripe = None
    if text is None and status == 'completed' and not (unfair or t.get('slips')):
        # Off-topic gripes ("con mèo nằm trên quầy") and trivial five-star reasons (review_gripes.py).
        g = _rg.roll(s, c, t, persona, group, fair, stars, ev['criteria'], seed, item)
        if g:
            gripe, stars, text, unfair = g['gripe'], g['stars'], g['text'], g['unfair']
            if g['clue']:
                clues.append(g['clue'])
    asp = None
    asp_unfair = False
    if text is None and status == 'completed' and not unfair and gripe is None:
        # Concrete angles: the taste, the straw, the restroom, the teacher's patience, office dress… (review_aspects.py).
        asp = _ra.plan(s, c, t, persona, group, stars, fair, ev['criteria'])
        if asp and asp['drop']:
            # A rare ungrounded complaint that costs a star: answerable with facts like any unfair claim.
            asp_unfair, stars, unfair = True, max(1, fair - 1), _ra.unfair_for(asp)
    style = None
    if text is None and status == 'completed' and not (unfair or t.get('slips') or persona in HARSH):
        # Mixed signals and odd voices: "ok", emoji only, long rants, 5★ for the owner's smile…
        styled = _fv.style_review(s, c, t, persona, group, fair, ev['criteria'], seed, item)
        if styled:
            style, stars, text = styled
    aspect_rows = []
    if text is None:
        # The concrete mistake is woven in below, so the order criterion is not repeated here.
        shown = [x for x in ev['criteria'] if not (t.get('slips') and x['key'] in ('accuracy', 'order'))] or ev['criteria']
        text = compose(persona, stars, shown, seed, None if asp_unfair else unfair)
        if t.get('slips'):
            from . import mistake_lines
            text = mistake_lines.weave(text, t, seed)
        if not unfair or asp_unfair:
            text = _fv.decorate(s, c, t, persona, group, stars, text, seed, item)
        if asp and asp['picks']:
            text, aspect_rows = _ra.weave(text, asp, s, t, persona, group, None, item, seed)
    elif style in _ra.STYLES_OK and asp and asp['picks']:
        text, aspect_rows = _ra.weave(text, asp, s, t, persona, group, style, item, seed)
    if asp_unfair:
        if aspect_rows:
            clues.append(_ra.CLUE)
        else:                                   # nothing was said after all: no star lost for it
            asp_unfair, stars, unfair = False, fair, None
    if asp and (aspect_rows or asp['slipped']):
        _ra.commit(c, aspect_rows)
        aspect_rows = [dict(r, text=teacher_title(s, r['text'])) if r.get('text') else r for r in aspect_rows + asp['slipped']][:_ra.MAX_ON_REVIEW]
    text = teacher_title(s, text)
    fb = dict(persona=persona, criteria=ev['criteria'], cap=ev['cap'], fair=fair, stars_original=stars, unfair=unfair,
              thread=[], status='open', rounds=0, pending=None, voice='scripted', task=t['id'], title=t.get('title', ''),
              value=int(t.get('_value', 0) or 0), item=item[:80])
    if style:
        fb['style'] = style
    if gripe:
        fb['gripe'] = gripe
    if twist:
        fb['twist'] = twist
    if clues:
        fb['clues'] = clues
    if out:
        fb['stranger'] = True
    if aspect_rows:
        fb['aspects'] = aspect_rows
    said = any(r.get('said', True) and not r.get('pos') for r in aspect_rows)   # a complaint was voiced
    # Happy asides ("Trà ngon, mai ghé tiếp!") only fit a plain, friendly review.
    return dict(text=text, stars=stars, feedback=fb,
                aside=not (twist or unfair or style or gripe or said or persona in HARSH or t.get('slips')), **out)


def _own_voice(career: str):
    """A career that writes its own reviews (careers/<id>.py `review_text`), e.g. the air crew: passengers of a
    flight and the captain's debrief, never the shop voices. Every other career keeps the shared path unchanged."""
    from .careers import PLUGINS
    return getattr(PLUGINS.get(career), 'review_text', None)


def _own_review(t: dict, persona: str, stars: int, ev: dict, text: str) -> dict:
    """The career's own words, closed at once: nobody at the airline answers a passenger note on the app, so no
    twists, shop gripes, reply thread, report or AI rewrite ever reach it (fb['own'])."""
    fb = dict(persona=persona, criteria=ev['criteria'], cap=ev['cap'], fair=stars, stars_original=stars, unfair=None,
              thread=[], status='closed', rounds=0, pending=None, voice='scripted', task=t['id'], title=t.get('title', ''),
              value=int(t.get('_value', 0) or 0), item='chuyến bay', own=True)
    return dict(text=str(text)[:600], stars=stars, feedback=fb, aside=False)


def _kind(fb: dict):
    return (fb.get('twist') or {}).get('kind')


def _bounds(fb: dict, current: int) -> tuple[int, int]:
    offered = any(x.get('offer', 'none') != 'none' for x in fb['thread'] if x['role'] == 'owner')
    orig, fair, kind = fb['stars_original'], fb['fair'], _kind(fb)
    if kind in ('flip_low', 'rumor'):
        high = max(orig, fair)                  # a mistake, fixable up to the truth
    elif kind == 'flip_high':
        high = orig
    elif kind in ('bocphot', 'demand'):
        high = max(orig, fair if offered else min(fair, orig + 1))
    elif kind:                                  # strangers and pile-ons
        high = min(5, orig + 1)
    elif fb.get('unfair'):
        high = fair
    else:
        high = min(5, orig + (2 if offered else 1), fb['cap'] + (1 if offered else 0))
    low = max(1, orig - 1)
    return low, max(low, high)


def classify(text: str) -> dict:
    n = normalize(text)
    marked = unicodedata.normalize('NFC', (text or '').lower())
    return dict(apology=_has(n, APOLOGY), fix=_has(n, FIX), facts=_has(n, FACTS),
                blame=_has(n, BLAME), rude=_has(marked, RUDE_WORDS) or _has(n, RUDE), short=len(text.strip()) < 12)


def scripted_decision(persona: str, fb: dict, stars: int, reply: str, offer: str) -> dict:
    sig = classify(reply)
    low, high = _bounds(fb, stars)
    worst = min(fb['criteria'], key=lambda x: x['score'])
    note = fb['unfair']['claim'] if fb.get('unfair') else worst['note']
    seed = _hash(reply, fb['task'], len(fb['thread']))
    v = VOICE[persona]
    pick = lambda rows: rows[seed % len(rows)].format(note=note)
    if sig['rude']:
        return dict(decision='revise_down', stars=max(low, stars - 1), text=pick(v['down']))
    kind = _kind(fb)
    parent = PERSONAS[persona]['group'] == 'parent'
    polite = not sig['blame'] or sig['apology']
    if kind in ('flip_low', 'rumor'):
        if not polite:
            return dict(decision='argue', stars=stars, text=pick(v['argue']))
        if kind == 'flip_low':
            return dict(decision='revise_up', stars=high, text=pick(TWIST_REPLY['flip_fix_parent' if parent else 'flip_fix']))
        if sig['facts'] or sig['apology'] or sig['fix']:
            return dict(decision='revise_up', stars=high, text=pick(v['sorry'] if sig['facts'] else v['accept']))
        return dict(decision='keep', stars=stars, text=pick(v['keep']))
    if kind == 'flip_high':
        return dict(decision='keep', stars=stars, text=pick(TWIST_REPLY['flip_keep']))
    if kind in ('wrong_shop', 'wrong_class', 'competitor', 'no_visit'):
        return dict(decision='keep', stars=stars, text=pick(TWIST_REPLY[kind]))
    if kind in ('offtopic', 'offtopic_p', 'pile_on'):
        soft = 'offtopic_soft' if kind != 'pile_on' else 'pile_on_soft'
        if sig['apology'] and polite and seed % 2 == 0:
            return dict(decision='revise_up', stars=min(high, stars + 1), text=pick(TWIST_REPLY[soft]))
        return dict(decision='keep', stars=stars, text=pick(TWIST_REPLY['pile_on' if kind == 'pile_on' else 'offtopic']))
    if kind in ('bocphot', 'demand') or persona in ('entitled', 'drama'):
        # They want something in hand, not words.
        given = [x.get('offer', 'none') for x in fb['thread'] if x['role'] == 'owner' and x.get('offer', 'none') != 'none']
        offer = given[-1] if given else offer
        if offer == 'refund' or (offer == 'gift' and (kind == 'demand' or persona == 'entitled')):
            return dict(decision='revise_up', stars=high, text=pick(v['accept']))
        if offer == 'gift' and sig['apology']:
            return dict(decision='revise_up', stars=min(high, stars + 1), text=pick(v['accept']))
        if sig['facts'] or sig['blame']:
            return dict(decision='argue', stars=stars, text=pick(v['argue']))
        return dict(decision='keep', stars=stars, text=pick(v['keep']))
    if persona in ('rude', 'parent_rude') and not fb.get('unfair') and not (sig['apology'] and (sig['fix'] or offer != 'none')):
        # Short fuse: words alone do not move them.
        if sig['facts'] and not sig['apology']:
            return dict(decision='argue', stars=stars, text=pick(v['argue']))
        return dict(decision='keep', stars=stars, text=pick(v['keep']))
    if fb.get('unfair'):
        if fb['unfair'].get('gripe') or fb['unfair'].get('aspect'):
            # An off-topic gripe or an unrecorded aspect ("nhà vệ sinh bí"): a kind or factual reply lets most people drop it.
            soft = 'aspect_soft' if fb['unfair'].get('aspect') else 'gripe_soft'
            if sig['facts'] or (sig['apology'] and persona not in HARSH):
                return dict(decision='revise_up', stars=high, text=pick(TWIST_REPLY[soft + '_parent' if parent else soft]))
        elif sig['facts'] or (sig['apology'] and persona in ('warm', 'genz', 'parent_kind', 'quiet')):
            return dict(decision='revise_up', stars=high, text=pick(v['sorry']))
        if sig['blame']:
            return dict(decision='argue', stars=stars, text=pick(v['argue']))
        return dict(decision='keep', stars=stars, text=pick(v['keep']))
    if sig['blame'] and not sig['apology']:
        return dict(decision='argue', stars=stars, text=pick(v['argue']))
    generous = persona in ('warm', 'genz', 'parent_kind', 'quiet')
    strict = persona in ('sour', 'picky', 'parent_strict')
    good_reply = sig['apology'] and (sig['fix'] or offer != 'none')
    if stars >= 5 and not fb.get('unfair'):
        return dict(decision='keep', stars=stars, text=pick(v['thanks']))
    if stars >= high:
        return dict(decision='keep', stars=stars, text=pick(v['keep']))
    # Know-it-alls melt as soon as someone admits they were right.
    flattered = persona in ('bossy', 'knowitall', 'parent_knowitall', 'troll') and sig['apology']
    if good_reply or (generous and sig['apology']) or flattered or (persona == 'parent_worried' and (sig['facts'] or sig['fix'])):
        if strict and offer == 'none' and not sig['fix']:
            return dict(decision='keep', stars=stars, text=pick(v['keep']))
        return dict(decision='revise_up', stars=min(high, stars + (2 if offer != 'none' and generous else 1)), text=pick(v['accept']))
    if sig['facts'] and not sig['apology'] and worst['score'] <= 3:
        return dict(decision='argue', stars=stars, text=pick(v['argue']))
    return dict(decision='keep', stars=stars, text=pick(v['keep']))


# Making amends (chat 03/10: "hoàn tiền 20 xu rồi xin lỗi mà nó vẫn giữ nguyên đánh giá"): a sincere apology with
# something real in hand gives a reviewer who would have kept the stars one more, seeded chance to edit the review
# up. Chance in percent by what was given (an apology; a polite reply without one gets half); never above
# AMENDS_CAP stars, never past what the facts allow (_bounds), rolled once per review from its id: one offer per
# review, so the roll cannot be bought twice.
AMENDS_CHANCE = {'refund': 80, 'gift': 65, 'drink': 50}
AMENDS_HARSH = 20                              # bad-day reviewers are harder to win back
AMENDS_CAP = 4
AMENDS_NEVER = ('wrong_shop', 'wrong_class', 'competitor', 'no_visit', 'flip_high', 'fan')  # never a real visit, or nothing to fix
AMENDS_UP = {'customer': ['Được xin lỗi đàng hoàng lại còn được bù, mình sửa lại sao nhé.',
                          'Thấy quán nhận lỗi thật lòng và bù cho mình, mình nâng sao. Lần sau cẩn thận hơn nha.',
                          'Quán xử lý vậy là có tâm. Mình sửa lại đánh giá rồi đó.'],
             'parent': ['Cảm ơn cô/thầy đã nhận thiếu sót và bù cho con. Tôi sửa lại đánh giá ạ.',
                        'Thấy cô/thầy nhận lỗi thật lòng, tôi yên tâm hơn và sửa lại đánh giá.']}
AMENDS_KEEP = {'customer': ['Cảm ơn lời xin lỗi và phần bù. Mình nhận, nhưng lần này vẫn giữ đánh giá để quán nhớ nha.',
                            'Mình ghi nhận quán đã bù rồi. Lần sau làm tốt thì mình sửa sao sau nhé.'],
               'parent': ['Tôi ghi nhận lời xin lỗi và phần bù, nhưng xin giữ nhận xét để lớp lưu ý ạ.',
                          'Cảm ơn cô/thầy đã bù cho con. Tôi giữ nhận xét, mong buổi sau tốt hơn ạ.']}


# Chat C#15809 (Yuika): "hoàn 20 xu rồi mà 1★ vẫn y nguyên". For these reviews no offer can ever move the stars, so
# the game says so before any xu leaves the wallet (fb_reply refuses the offer; the thread view shows the note).
OFFER_USELESS = {'wrong_shop': 'khách đánh giá nhầm chỗ', 'wrong_class': 'phụ huynh nhắn nhầm lớp', 'no_visit': 'khách chưa từng dùng dịch vụ',
                 'competitor': 'đây có vẻ là tài khoản cài cắm', 'flip_high': 'khách đã chấm 5★ rồi', 'fan': 'khách đã hài lòng sẵn rồi'}


def offer_note(fb: dict) -> str | None:
    """Why bù đắp cannot change this review (None: it may help)."""
    why = OFFER_USELESS.get(_kind(fb))
    if not why:
        return None
    tail = ' Báo cáo đánh giá để nền tảng gỡ thì hơn.' if _kind(fb) in REMOVABLE else ''
    return f'Bù xu không đổi được đánh giá này: {why}. Trả lời không kèm bù là đủ.{tail}'


def amends(post: dict, decision: dict, tone: str, reply: str) -> dict:
    """The reviewer's answer once something real was given (this round or before): a fair, seeded chance to
    edit the stars up when they would have kept them; otherwise they say they saw it."""
    fb, stars = post['feedback'], post.get('stars')
    given = [x.get('offer', 'none') for x in fb['thread'] if x['role'] == 'owner' and x.get('offer', 'none') != 'none']
    if not given or not stars or decision.get('decision') not in ('keep', 'argue') or _kind(fb) in AMENDS_NEVER:
        return decision
    sig = classify(reply)
    if tone in ('harsh', 'sassy') or sig['rude'] or (sig['blame'] and not sig['apology']):
        return decision
    chance = AMENDS_CHANCE.get(given[-1], 0)
    if not (tone == 'sorry' or sig['apology']):
        chance //= 2
    if fb['persona'] in HARSH:
        chance -= AMENDS_HARSH
    _, high = _bounds(fb, stars)
    new = min(high, AMENDS_CAP, stars + (2 if given[-1] == 'refund' else 1))
    group = 'parent' if PERSONAS[fb['persona']]['group'] == 'parent' else 'customer'
    seed = _hash('amends', post['id'])
    if new > stars and seed % 100 < chance:
        return dict(decision, decision='revise_up', stars=new, text=AMENDS_UP[group][seed % len(AMENDS_UP[group])], amends=True)
    if decision['decision'] == 'keep':
        return dict(decision, text=AMENDS_KEEP[group][seed % len(AMENDS_KEEP[group])], amends=True)
    return decision


def attach(post: dict, review: dict) -> None:
    post['feedback'] = review['feedback']
    if review.get('npc'):
        post['npc'] = review['npc']
        post['author'] = review['author']


def _pile_on(s: dict, c: dict, career: str, post: dict, count: int, why: str) -> int:
    """Strangers pile on with 1★ after a rude reply or an ignored threat. A pile-on never starts another one, and a
    report never starts one (góp ý #196: "báo cáo xong còn bị kéo bầy")."""
    from . import engine as e
    fb = post['feedback']
    if why == 'report' or _kind(fb) == 'pile_on':
        return 0
    parent = PERSONAS[fb['persona']]['group'] == 'parent'
    pool = [k for k in e.NPC_INDEX if k.startswith(career + '_npc_') and k != post['npc']] or [k for k in e.NPC_INDEX if k != post['npc']]
    texts = PILE_ON['phot' if why == 'phot' else ('report_parent' if parent else 'report') if why == 'report' else 'parent' if parent else 'customer']
    personas = MOOD_PARENT if parent else ('rude', 'genz', 'sour', 'troll')
    label = 'Cách trả lời phụ huynh' if parent else 'Thái độ khi trả lời khách'
    if _pv.on(career):
        texts, label = _pv.PILE_ON['phot' if why == 'phot' else 'report' if why == 'report' else 'customer'], _pv.PILE_LABEL
    made = 0
    for i in range(count):
        h = _hash('pile', post['id'], why, i)
        npc = pool[(h + i) % len(pool)]
        p = e.add_feed(s, c, npc, teacher_title(s, texts[(h // 3 + i) % len(texts)]), post['id'], 1, 'review')
        p['feedback'] = dict(persona=personas[h % len(personas)],
                             criteria=[dict(key='attitude', label=label, score=1, note=PILE_NOTE[why])],
                             cap=5, fair=1, stars_original=1, unfair=None, thread=[], status='open', rounds=0, pending=None, voice='scripted',
                             task=fb.get('task', ''), title=fb.get('title', ''), value=0, stranger=True,
                             twist=dict(kind='pile_on', reportable=True),
                             clues=[PILE_CLUE[why]])
        e.metric(c, 'reviews_viral')
        made += 1
    return made


def _post(c: dict, pid) -> dict:
    from .engine import need
    post = next((f for f in c['feed'] if f['id'] == pid), None)
    need(post and post.get('feedback'), 'Không thấy phản hồi này.')
    return post


def can_police(post: dict) -> bool:
    """Only the explicit money-for-silence scenario offers a simulated report."""
    fb = post.get('feedback') or {}
    text = normalize(post.get('text', ''))
    threat = _kind(fb) == 'bocphot' or (fb.get('persona') == 'drama'
             and any(line in text for line in ('muon yen thi hoan tien', 'den bu di, khong thi')))
    return bool(post.get('stars') and threat and not fb.get('police'))


def action(s: dict, c: dict, career: str, name: str, p: dict, internal: bool = False) -> dict:
    from . import engine as e
    need = e.need
    if name == 'fb_police':
        post = _post(c, p.get('post'))
        fb = post['feedback']
        need(can_police(post), 'Chỉ trình báo được lời đe dọa đòi tiền chưa có hồ sơ.')
        need(p.get('confirm') is True, 'Xác nhận lưu bằng chứng và trình báo trong game.')
        fb['police'] = dict(day=c['day'], text=post['text'], stars=post['stars'], thread=deepcopy(fb['thread']))
        fb['status'] = 'closed'
        fb['pending'] = None
        e.metric(c, 'reviews_police')
        e.log(s, c, 'feedback', f'Lưu bằng chứng và trình báo lời đe dọa đòi tiền của {post["author"]}.', post['npc'], post['id'])
        return dict(message='Đã lưu đánh giá và cuộc trao đổi vào hồ sơ trình báo trong game. Khép trao đổi trực tiếp; điểm đánh giá vẫn giữ nguyên.', police='filed')
    if name == 'fb_reply':
        post = _post(c, p.get('post'))
        fb = post['feedback']
        need(fb['status'] != 'closed', 'Cuộc trao đổi này đã khép.')
        need(fb['status'] != 'awaiting', 'Khách đang đọc phản hồi trước của bạn.')
        need(fb['rounds'] < 3, 'Đã trao đổi đủ ba lượt cho review này.')
        reply = e.clean_text(p.get('text'), 600, 4)
        offer = p.get('offer', 'none')
        need(offer in OFFERS, 'Hình thức bù đắp không hợp lệ.')
        tone = p.get('tone', 'free')
        need(_fv.tone_text_ok(tone), 'Giọng trả lời không hợp lệ.')
        if tone != 'free' and tone != 'harsh' and classify(reply)['rude']:
            tone = 'harsh'                      # the words win over the label
        if offer != 'none':
            note = offer_note(fb)
            need(not note, (note or '') + ' Chưa trừ xu nào.', 'offer_useless')
            need(not any(x.get('offer', 'none') != 'none' for x in fb['thread'] if x['role'] == 'owner'), 'Mỗi review chỉ bù đắp một lần.')
            e.money(s, c, -OFFERS[offer], (_pv.OFFER_LEDGER if _pv.on(career) else 'Bù đắp cho khách: ') + (post['author'] or 'khách'), post['id'], category='compensation')
        row = dict(role='owner', text=reply, day=c['day'], offer=offer)
        if tone != 'free':
            row['tone'] = tone
        fb['thread'].append(row)
        if tone != 'free':
            given = [x.get('offer', 'none') for x in fb['thread'] if x['role'] == 'owner' and x.get('offer', 'none') != 'none']
            decision = _fv.tone_decision(s, c, post, tone, given[-1] if given else 'none')
        else:
            decision = scripted_decision(fb['persona'], fb, post['stars'], reply, offer)
        if not _pv.on(career):
            decision = amends(post, decision, tone, reply)
        if _pv.on(career):
            decision = _pv.react(s, post, decision, _hash('pagoda-react', post['id'], fb['rounds'], tone))
        fb['rounds'] += 1
        fb['status'] = 'awaiting'
        fb['pending'] = dict(decision, turn=c['turn'])
        e.metric(c, 'replies')
        e.metric(c, 'review_replies')
        out = dict(message=('Đã gửi lời hồi đáp. ' if _pv.on(career) else 'Đã gửi phản hồi. ') + (post['author'] or 'Khách') + ' đang đọc…', awaiting=post['id'])
        if (tone == 'harsh' or classify(reply)['rude']) and not fb.get('viral') and _kind(fb) != 'pile_on':
            # Screenshots travel fast: once per review, strangers pile on.
            fb['viral'] = True
            n = 1 + (1 if fb['persona'] in ('drama', 'rude', 'parent_rude', 'knowitall') else 0) + _hash('viral', post['id']) % 2
            n = _pile_on(s, c, career, post, n, 'rude')
            out['message'] = (_pv.fill(_pv.VIRAL, n=n) if _pv.on(career)
                              else f'Câu trả lời gắt bị chụp màn hình lan đi: thêm {n} đánh giá 1★.')
            out['viral'] = n
        return out
    if name == 'fb_ignore':
        post = _post(c, p.get('post'))
        fb = post['feedback']
        need(fb['status'] == 'open', 'Đánh giá này không còn chờ bạn.')
        fb['status'] = 'closed'
        fb['ignored'] = True
        if (_kind(fb) == 'bocphot' or fb['persona'] == 'drama') and post.get('stars') and post['stars'] <= 2 and not fb.get('viral'):
            # Silence is an answer too: the threat gets posted.
            fb['viral'] = True
            n = _pile_on(s, c, career, post, 2, 'phot')
            pg = _pv.on(career)
            fb['thread'].append(dict(role='customer', text=_pv.PHOT_LINE if pg else 'Im lặng thì mình đăng nhé. Mọi người tự đánh giá.', day=c['day'], decision='keep', stars=post['stars'], mode='scripted'))
            fb['thread'] = ar.last(fb['thread'], 8, 'review.thread', c)
            return dict(message=_pv.fill(_pv.PHOT_MSG, author=post['author'], n=n) if pg else f'{post["author"]} đăng bài bóc phốt: thêm {n} đánh giá 1★.', viral=n)
        return dict(message=_pv.IGNORED if _pv.on(career) else 'Đã bỏ qua. Đánh giá vẫn giữ nguyên.')
    if name == 'fb_report':
        post = next((f for f in c['feed'] if f['id'] == p.get('post')), None)
        need(post and (post.get('feedback') or _plain_review(post)), 'Không thấy phản hồi này.')
        need(reports_today(c) < REPORTS_PER_DAY, f'Hôm nay bạn đã báo cáo {REPORTS_PER_DAY} lần. Để mai nhé.')
        if not post.get('feedback'):
            # A review written by a shift event (no thread): it is tied to something that really happened, so the
            # platform keeps it. Nothing else changes: no star, no angry reviewer.
            need(post.get('stars') and not post.get('reported'), 'Đánh giá này đã được báo cáo.')
            post['reported'] = c['day']             # the day of the (kept) report; `report` is consequences.py's flag
            e.metric(c, 'reviews_reported')
            return dict(message='Nền tảng giữ đánh giá này: nó gắn với chuyện có thật trong ca. Sao giữ nguyên, không ai phật ý.',
                        report='rejected')
        fb = post['feedback']
        need(not fb.get('police'), 'Đã lưu đánh giá này trong hồ sơ trình báo.')
        need(post.get('stars') and not fb.get('report'), 'Đánh giá này đã được báo cáo.')
        need(fb['status'] != 'awaiting', 'Chờ khách trả lời trước.')
        parent = PERSONAS[fb['persona']]['group'] == 'parent'
        fb['report_day'] = c['day']
        e.metric(c, 'reviews_reported')
        if removable(post):
            # Removed from the average, never deleted: the review stays in the list, struck through (`removed_stars`).
            fb['report'] = 'accepted'
            fb['removed_stars'] = post['stars']
            post['stars'] = None
            fb['status'] = 'closed'
            fb['pending'] = None
            e.metric(c, 'reviews_removed')
            return dict(message='Ban đại diện lớp đã gỡ tin nhắn này khỏi nhóm.' if parent else _pv.REPORT_OK if _pv.on(career)
                        else 'Nền tảng đã gỡ đánh giá này. Điểm trung bình không còn tính nó.', report='accepted')
        # A real experience: the platform keeps it. Góp ý #196: no star is lost and nobody piles on; the reviewer
        # only says they noticed, and the conversation closes.
        fb['report'] = 'rejected'
        seed = _hash('report', post['id'])
        pg = _pv.on(career)
        rows = REPORT_KEEP['pagoda' if pg else 'parent' if parent else 'customer']
        fb['thread'].append(dict(role='customer', text=teacher_title(s, rows[seed % len(rows)]), day=c['day'],
                                 decision='keep', stars=post['stars'], mode='scripted'))
        fb['thread'] = ar.last(fb['thread'], 8, 'review.thread', c)
        fb['status'] = 'closed'
        if post['npc'] in e.NPC_INDEX and not fb.get('stranger'):
            c['relationships'][post['npc']] = max(0, c['relationships'].get(post['npc'], 0) - 3)
        who = post['author'] or ('Phụ huynh' if parent else 'Khách')
        if parent:
            msg = f'Nhà trường không gỡ: đó là góp ý thật. Đánh giá giữ nguyên, {who} hơi phật ý.'
        elif pg:
            msg = f'Không gỡ được: khách có lên chùa thật. Cảm nhận giữ nguyên, {who} hơi buồn.'
        else:
            msg = f'Báo cáo không được duyệt: đây là trải nghiệm thật. Sao giữ nguyên, {who} hơi phật ý.'
        return dict(message=msg, report='rejected')
    if name == 'fb_resolve':
        need(internal, 'Thao tác chỉ dành cho máy chủ.', 'forbidden')
        post = _post(c, p.get('post'))
        return resolve(s, c, post, p.get('decision'), p.get('stars'), p.get('text'), p.get('mode', 'scripted'))
    if name == 'fb_voice':
        need(internal, 'Thao tác chỉ dành cho máy chủ.', 'forbidden')
        post = _post(c, p.get('post'))
        fb = post['feedback']
        need(not fb.get('police'), 'Đã lưu nội dung trong hồ sơ trình báo.')
        need(fb['voice'] == 'scripted' and not fb['thread'], 'Review đã được viết lại.')
        text = e.clean_text(p.get('text'), 700, 8)
        post['text'] = text
        fb['voice'] = 'ai'
        return dict(message='')
    if name == 'fb_close':
        post = _post(c, p.get('post'))
        need(post['feedback']['status'] != 'awaiting', 'Chờ khách trả lời trước.')
        post['feedback']['status'] = 'closed'
        return dict(message='Đã khép cuộc trao đổi.')
    raise e.GameError('Thao tác phản hồi chưa được hỗ trợ.')


def resolve(s: dict, c: dict, post: dict, decision, stars, text, mode: str) -> dict:
    from . import engine as e
    need = e.need
    fb = post['feedback']
    need(fb['status'] == 'awaiting', 'Không có phản hồi nào đang chờ khách.')
    pending = fb['pending'] or {}
    current = post['stars']
    low, high = _bounds(fb, current)
    if mode == 'ai' and pending.get('decision') and decision != pending['decision']:
        mode = 'scripted'   # the words are the model's, the outcome is the game's: a model that disagrees is not used
    if mode != 'ai' or type(stars) is not int or not isinstance(text, str) or not text.strip():
        decision, stars, text, mode = pending.get('decision', 'keep'), pending.get('stars', current), pending.get('text', ''), 'scripted'
    elif type(pending.get('stars')) is int:
        stars = pending['stars']   # same decision: the same stars as without AI (seeded, server-side)
    stars = max(low, min(high, int(stars)))
    # Keep the decision label honest about what happened to the stars.
    if stars > current:
        decision = 'revise_up'
    elif stars < current:
        decision = 'revise_down'
    elif decision not in ('argue', 'keep'):
        decision = 'keep'
    text = teacher_title(s, e.clean_text(text, 600, 1))
    fb['thread'].append(dict(role='customer', text=text, day=c['day'], decision=decision, stars=stars, mode=mode))
    post['stars'] = stars
    fb['pending'] = None
    fb['status'] = 'open' if decision == 'argue' and fb['rounds'] < 3 else 'closed'
    npc = post['npc']
    pg = _pv.on(_fv._career_of(s, c))
    if npc in e.NPC_INDEX and not fb.get('stranger'):
        if decision == 'revise_up':
            e.remember(s, c, npc, _pv.REMEMBER if pg else 'Đã sửa đánh giá sau khi đọc phản hồi của chủ quán.', post['id'])
            e.metric(c, 'reviews_improved')
        elif decision == 'revise_down':
            c['relationships'][npc] = max(0, c['relationships'].get(npc, 0) - 6)
    label = (_pv.RESOLVED if pg else {'revise_up': 'đã nâng đánh giá', 'revise_down': 'đã hạ đánh giá', 'argue': 'muốn đối chất lại', 'keep': 'giữ nguyên đánh giá'})[decision]
    extra = _fv.after_resolve(s, c, post, pending, decision)  # friends, sass fallout, bystanders
    fb['thread'] = ar.last(fb['thread'], 8, 'review.thread', c)
    message = f'{post["author"]} {label}: “{text}”'
    if stars != current and not pg:
        # Chat 03/10: the change is the news, said first ("Khách đã sửa đánh giá: ★1 → ★3").
        message = f'{post["author"]} đã sửa đánh giá: ★{current} → ★{stars}. “{text}”'
    if extra:
        message += ' ' + ' '.join(extra)
    return dict(message=message, decision=decision, stars=stars)


def tick(s: dict, c: dict) -> list[str]:
    """Reviewers answer by themselves after two work turns if no AI reply came."""
    notes = []
    for post in list(c['feed']):                # resolving may add new reviews
        fb = post.get('feedback')
        if fb and fb['status'] == 'awaiting' and fb.get('pending') and c['turn'] >= fb['pending']['turn'] + 2:
            r = resolve(s, c, post, None, None, None, 'scripted')
            notes.append(r['message'])
    return notes


def validate_post(post: dict) -> None:
    from .engine import need, integer, clean_text
    if 'reported' in post:                      # a kept report of a plain event review (fb_report)
        integer(post['reported'], 1, 100000)
    fb = post.get('feedback')
    if fb is None:
        return
    need(isinstance(fb, dict) and fb.get('persona') in PERSONAS, 'Phản hồi khách không hợp lệ.')
    need(fb.get('status') in ('open', 'awaiting', 'closed') and fb.get('voice') in ('scripted', 'ai'), 'Trạng thái phản hồi sai.')
    integer(fb.get('rounds'), 0, 3)
    for k in ('cap', 'fair', 'stars_original'):
        integer(fb.get(k), 1, 5)
    need(isinstance(fb.get('criteria'), list) and 1 <= len(fb['criteria']) <= 8, 'Tiêu chí phản hồi sai.')
    for x in fb['criteria']:
        need(isinstance(x, dict), 'Tiêu chí sai.')
        integer(x.get('score'), 1, 5)
        clean_text(x.get('label'), 80)
    need(isinstance(fb.get('thread'), list) and len(fb['thread']) <= 8, 'Cuộc trao đổi quá dài.')
    for row in fb['thread']:
        need(isinstance(row, dict) and row.get('role') in ('owner', 'customer', 'guest'), 'Lượt trao đổi sai.')
        clean_text(row.get('text'), 700)
        if row['role'] == 'owner':
            need(row.get('offer', 'none') in OFFERS, 'Bù đắp sai.')
    need(fb.get('pending') is None or isinstance(fb['pending'], dict), 'Phản hồi chờ sai.')
    if fb['status'] == 'awaiting':
        need(fb.get('pending'), 'Thiếu quyết định dự phòng.')
    tw = fb.get('twist')
    need(tw is None or (isinstance(tw, dict) and tw.get('kind') in TWISTS and type(tw.get('reportable')) is bool), 'Loại đánh giá sai.')
    clues = fb.get('clues', [])
    need(isinstance(clues, list) and len(clues) <= 4, 'Dấu hiệu đánh giá sai.')
    for x in clues:
        clean_text(x, 80)
    need(fb.get('report') in (None, 'accepted', 'rejected'), 'Trạng thái báo cáo sai.')
    if fb.get('report'):
        integer(fb.get('report_day'), 1, 100000)
    if fb.get('report') == 'accepted':
        need(post.get('stars') is None and fb['status'] == 'closed', 'Đánh giá đã gỡ vẫn còn sao.')
        integer(fb.get('removed_stars'), 1, 5)
    police = fb.get('police')
    if police is not None:
        need(isinstance(police, dict) and set(police) == {'day', 'text', 'stars', 'thread'}, 'Hồ sơ trình báo sai.')
        integer(police['day'], 1, 100000)
        integer(police['stars'], 1, 5)
        clean_text(police['text'], 700)
        need(police['thread'] == fb['thread'] and fb['status'] == 'closed' and fb.get('pending') is None,
             'Cuộc trao đổi đã trình báo không hợp lệ.')
    for k in ('stranger', 'viral', 'ignored', 'own'):
        need(type(fb.get(k, False)) is bool, 'Cờ đánh giá sai.')
    _fv.validate_extra(fb)
    _rg.validate(fb)
    _ra.validate(fb)


def public_post(post: dict, career: str | None = None) -> dict:
    fb = post.get('feedback')
    if not fb:
        if _plain_review(post):
            # Every review can be reported (góp ý #196); a plain event review is kept, at no cost.
            return dict(post, can_report=not post.get('reported'))
        return post
    v = dict(post)
    f = dict(fb)
    f.pop('pending', None)
    per = PERSONAS[fb['persona']]
    f['persona_name'] = per['name']
    f['persona_emoji'] = per['emoji']
    if fb.get('unfair'):
        f['unfair'] = dict(label=fb['unfair']['label'], claim=fb['unfair']['claim'], truth=fb['unfair']['truth'])
    # What kind of twist it was stays hidden: the player reads the clues and decides.
    tw = f.pop('twist', None)
    if tw and not fb.get('report'):
        f.pop('fair', None)
    f.pop('report_day', None)
    f['clues'] = list(fb.get('clues') or [])
    f['removed'] = fb.get('report') == 'accepted'
    f['can_report'] = bool(post.get('stars')) and not fb.get('report') and fb['status'] != 'awaiting' and not fb.get('own') and not fb.get('police')
    f['can_police'] = can_police(post)
    note = offer_note(fb)
    if note and fb['status'] == 'open':
        f['offer_note'] = note                  # bù xu would change nothing here: said before any xu is taken
    f['can_ignore'] = fb['status'] == 'open' and not fb['thread']
    f.pop('style', None)
    f.pop('aspects', None)
    if fb['status'] == 'open' and fb['rounds'] < 3 and post.get('stars'):
        f['tones'] = _fv.tone_choices(post, career)
    if fb.get('report') and tw:
        f['kind_label'] = TWIST_LABEL.get(tw['kind'], '')
    v['feedback'] = f
    return v


def stats(c: dict) -> dict:
    rows = [p for p in c['feed'] if p.get('feedback') and p.get('stars')]
    by = {}
    for p in rows:
        for x in p['feedback']['criteria']:
            b = by.setdefault(x['label'], [0, 0])
            b[0] += x['score']
            b[1] += 1
    return dict(count=len(rows), open=sum(p['feedback']['status'] != 'closed' for p in rows),
                improved=sum(p['stars'] > p['feedback']['stars_original'] for p in rows),
                removed=sum(1 for p in c['feed'] if (p.get('feedback') or {}).get('report') == 'accepted'),
                flagged=sum(1 for p in rows if p['feedback'].get('clues') and not p['feedback'].get('report')),
                criteria=[dict(label=k, avg=round(v[0] / v[1], 1), count=v[1]) for k, v in by.items()])


def ai_context(c: dict, post: dict, lang: str = 'vi', career: str | None = None) -> dict:
    fb = post['feedback']
    per = PERSONAS[fb['persona']]
    low, high = _bounds(fb, post['stars'])
    return dict(language='English' if lang == 'en' else 'tiếng Việt', persona=dict(name=per['name'], style=per['style'], reviewer=post['author']),
                role=_pv.AI_ROLE if _pv.on(career) else 'phụ huynh học sinh phản hồi giáo viên' if per['group'] == 'parent' else 'khách hàng phản hồi cửa hàng/dịch vụ',
                facts=dict(task=fb.get('title'), criteria=fb['criteria'], unfair_claim=fb.get('unfair'), situation=TWIST_AI.get(_kind(fb)) or _rg.situation(fb) or _ra.situation(fb),
                           aspects=_ra.ai_facts(fb)),
                review=dict(stars_now=post['stars'], stars_original=fb['stars_original'], text=post['text']),
                thread=fb['thread'][-6:], allowed_stars=[low, high], offers=[x.get('offer') for x in fb['thread'] if x['role'] == 'owner'],
                reply_tone=next((_fv.TONES[x['tone']]['label'] for x in reversed(fb['thread']) if x['role'] == 'owner' and x.get('tone') in _fv.TONES), None),
                suggested=dict(decision=(fb.get('pending') or {}).get('decision'), stars=(fb.get('pending') or {}).get('stars')))


TWIST_LABEL = {'offtopic': 'Lý do không liên quan', 'no_visit': 'Chưa dùng dịch vụ', 'wrong_shop': 'Đánh giá nhầm quán',
               'competitor': 'Tài khoản cài cắm', 'flip_low': 'Bấm nhầm sao', 'flip_high': 'Bấm nhầm sao', 'bocphot': 'Dọa bóc phốt',
               'demand': 'Đòi hỏi quá đà', 'offtopic_p': 'Lý do không liên quan', 'wrong_class': 'Nhắn nhầm lớp', 'rumor': 'Nghe kể lại',
               'pile_on': 'Hùa theo trên mạng'}
# Hidden situation for the optional AI voice (server side only).
TWIST_AI = {
    'offtopic': 'Bạn chấm 1 sao vì lý do không liên quan tới dịch vụ; bạn lười sửa, chỉ nhượng bộ chút nếu được trả lời rất lễ phép.',
    'no_visit': 'Bạn chưa hề dùng dịch vụ mà vẫn chấm thấp; bạn không muốn thừa nhận.',
    'wrong_shop': 'Bạn đánh giá nhầm sang chỗ khác; nếu được nhắc, bạn ngượng nhưng lười sửa.',
    'competitor': 'Bạn là người của tiệm đối thủ viết review xấu; không bao giờ thừa nhận, không nâng sao.',
    'flip_low': 'Bạn rất hài lòng nhưng bấm nhầm 1 sao; khi được hỏi lịch sự, bạn nhận ra và sửa lại.',
    'flip_high': 'Bạn chấm 5 sao nhưng nội dung là lời chê thật; bạn giữ nguyên.',
    'bocphot': 'Bạn dọa đăng bài bóc phốt để đòi hoàn tiền; chỉ nguôi khi được đền bù thật.',
    'demand': 'Bạn đòi ưu đãi ngoài dịch vụ; chỉ nguôi khi được tặng quà hoặc bù đắp.',
    'offtopic_p': 'Bạn là phụ huynh phàn nàn chuyện không liên quan tới buổi học.',
    'wrong_class': 'Bạn là phụ huynh nhắn nhầm nhóm lớp; ngượng nhưng lười sửa.',
    'rumor': 'Bạn chỉ nghe phụ huynh khác kể lại; nếu giáo viên đưa sự thật, bạn nhận là hiểu nhầm.',
    'pile_on': 'Bạn vào hùa sau khi thấy câu trả lời gắt trên mạng.',
}


def day_summary(c: dict, day: int) -> dict:
    rows = [p for p in c['feed'] if p.get('stars') and p['day'] == day and p['kind'] == 'review']
    crit = {}
    for p in rows:
        for x in (p.get('feedback') or {}).get('criteria', []):
            b = crit.setdefault(x['label'], [0, 0])
            b[0] += x['score']
            b[1] += 1
    weakest = min(crit.items(), key=lambda kv: kv[1][0] / kv[1][1])[0] if crit else None
    return dict(count=len(rows), average=round(sum(p['stars'] for p in rows) / len(rows), 1) if rows else None,
                weakest=weakest, open=sum(1 for p in rows if (p.get('feedback') or {}).get('status') == 'open'))


# Chùa Gió Lành's own words in the whole thread (pagoda_voice.py).
from . import pagoda_voice as _pv  # noqa: E402
# Livelier threads: extra voices, reply tones, third parties (feedback_voices.py).
from . import feedback_voices as _fv  # noqa: E402
_fv.install(globals())
# Off-topic gripes and trivial five-star reasons (review_gripes.py).
from . import review_gripes as _rg  # noqa: E402
_rg.install(globals())
# Many more angles: taste, straw, restroom, attitude, dress, teaching method… (review_aspects.py).
from . import review_aspects as _ra  # noqa: E402
_ra.install(globals())
