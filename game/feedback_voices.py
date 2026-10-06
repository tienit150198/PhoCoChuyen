"""Livelier review threads (v0.5 wave 2b).

* More reviewer voices: extra openers and reactions per persona, lines that
  mention the actual job ({item}), day-aware closers, and review "styles"
  with mixed signals (ultra short, emoji only, teencode, long rants, life
  stories, regulars, "5★ because the owner is cute", sarcastic praise).
* Ten owner reply tones with ready-made texts. What a tone does depends on
  the reviewer's persona and the kind of review (a server-side table), and
  on whether the facts back the owner up. Sass is a gamble.
* Third parties: fans who defend the shop, trolls who pile on, friends who
  come in after a moved reviewer spreads the word. Deterministic, capped.

Everything is seeded from ids and rounds; nothing rerolls on reload. The
module holds data and helpers; feedback.py calls in through `install`,
`decorate`, `style_review`, `tone_decision`, `tone_choices`, `after_resolve`.
"""
from __future__ import annotations

import re

from .memo import Memo, size_of

# ------------------------------------------------------------ extra voices
# Merged into feedback.VOICE. Lists that feedback.py formats with .format(note=)
# (accept/keep/argue/down/sorry/thanks) only use {note}; `good`/`bad` only use
# {good}/{bad}/{note}; openers have no placeholders. The new keys (moved,
# laugh, jab, seen, fans, item_pos, item_neg) may also use {owner} and {item}.
MORE_VOICE = {
    'sour': dict(
        open={5: ['Chê mãi cũng mỏi miệng, hôm nay cho năm sao cho lạ.', 'Công nhận, lần này tôi hết chỗ bắt bẻ.'],
              4: ['Được, nhưng khen nhiều lại sinh hư.', 'Ổn, trừ một sao để còn có cái mà cố.'],
              3: ['Không dở, nhưng cũng chẳng có gì để nhớ.', 'Làm vừa đủ để khách không chửi, thế thôi.'],
              2: ['Tưởng quán tử tế, hóa ra cũng thường.', 'Đẹp ở cái bảng hiệu là chính.'],
              1: ['Tiền tôi cũng là tiền chứ bộ.', 'Muốn góp ý mà chẳng biết bắt đầu từ đâu.']},
        thanks=['Ừ, được cái biết điều.', 'Thôi được, lần này tôi không bắt bẻ nữa.'],
        accept=['Nói phải thì củ cải cũng nghe. Tôi nâng sao.', 'Ừ, nhận lỗi thẳng thắn thế thì tôi cũng không làm khó.'],
        keep=['Lời hay ý đẹp đấy, nhưng sao thì để nguyên.', 'Ghi nhận. Chờ xem lần sau.'],
        argue=['Nói khéo mấy thì {note} vẫn là {note}.', 'Tôi không mù đâu: {note}.'],
        down=['Chủ quán nói kiểu này thì nhân viên học ai?', 'Hạ sao. Đáng ra phải hạ từ đầu.'],
        sorry=['Ờ thì tôi nhớ nhầm. Nhưng đừng có đắc ý đấy.', 'Được rồi, tôi sai. Sửa sao. Vừa lòng chưa?'],
        moved=['Ờ… nói vậy thì tôi cũng mềm lòng. Nâng sao, lần sau đừng để tôi chê.', 'Chịu, trả lời có tâm thế này ai nỡ giữ sao thấp.'],
        laugh=['Được, trả lời cũng có duyên. Thêm sao vì cái duyên đó.', 'Tôi định cà khịa lại mà đọc xong phì cười. Thôi, thêm sao.'],
        jab=['Đùa hay đấy, nhưng {note} thì không có gì buồn cười.', 'Quán thích đùa thế thì làm cho đàng hoàng rồi hẵng đùa.', 'Tự trào hay lắm, giờ tự sửa đi.'],
        seen=['Ờ.', 'Đọc rồi. Thế thôi à?'],
        fans=['Thôi được, tôi nâng sao, còn rủ mấy đứa bạn ra thử. Đừng làm tôi mất mặt.', 'Nâng sao. Tôi kể cho mấy đứa ở cơ quan, liệu mà làm.'],
        item_pos=['Riêng {item} thì phải công nhận.', '{item} hôm nay được, không cãi.'],
        item_neg=['Còn {item} thì đừng hỏi.', '{item} mà cũng dám bán giá đó.']),
    'bossy': dict(
        open={5: ['Tốt. Có ai chỉ cho hay tự học mà được vậy?', 'Đúng chuẩn, tôi đi nhiều nơi rồi mới dám nói.'],
              4: ['Được, nhưng còn thiếu cái tinh tế người làm lâu mới có.', 'Khá. Tôi mà là chủ thì còn chỉnh vài chỗ.'],
              3: ['Chưa ra đâu vào đâu, nghe tôi nói đây.', 'Làm thế thì khách sang người ta không quay lại đâu.'],
              2: ['Phải có quy trình, cái này làm theo cảm hứng.', 'Người mới nên đi học việc thêm vài tháng.'],
              1: ['Tôi nói thẳng vì muốn tốt cho quán thôi.', 'Làm ăn phải có tâm, cái này thì không.']},
        thanks=['Được. Biết lắng nghe là quý.', 'Ừ, cứ thế mà làm.'],
        accept=['Người trẻ biết nghe là hiếm đấy. Tôi nâng sao.', 'Ừ, sửa được thì tôi ghi nhận ngay.'],
        keep=['Tôi nói rồi, làm được mới tính.', 'Đọc rồi. Để tôi quay lại kiểm tra.'],
        argue=['Không phải giải thích với tôi. {note}, tôi thấy tận mắt.', 'Nói với người từng trải thì đừng vòng vo: {note}.'],
        down=['Nói chuyện với người đi trước vậy à? Hạ sao.', 'Tôi góp ý thiện chí mà nhận câu đó. Hạ.'],
        sorry=['Thôi được, tôi cũng có lúc nhầm. Nhưng hiếm đấy.', 'Phiếu ghi rõ thì tôi sửa. Người lớn phải biết nhận.'],
        moved=['Được, trả lời thế là có học. Tôi nâng sao, cứ theo đó mà làm.', 'Đấy, biết điều thế thì tôi nâng sao liền.'],
        laugh=['Ha, cũng có khiếu ăn nói. Nâng sao cho có động lực.', 'Đùa được đấy. Tôi thêm sao, nhưng nhớ lời tôi.'],
        jab=['Đùa gì mà đùa, người làm nghề phải nghiêm túc.', 'Hồi tôi bằng tuổi cậu/cô, nói với khách vậy là bị mắng đấy.', 'Chuyện nghiêm túc mà trả lời đùa cợt, tôi không thích.'],
        seen=['Ừ, đọc rồi.', 'Ngắn thế. Thôi được.'],
        fans=['Tốt, tôi nâng sao và sẽ giới thiệu cho mấy ông bạn già.', 'Nâng sao. Hội bạn tôi mai ra đây uống, phục vụ cho đàng hoàng.'],
        item_pos=['{item} làm đúng bài bản.', '{item} được, có nghề đấy.'],
        item_neg=['{item} phải làm lại từ khâu đầu.', '{item} là thiếu kinh nghiệm thấy rõ.']),
    'warm': dict(
        open={5: ['Thương quán ghê, ghé một lần mà muốn ghé hoài.', 'Hôm nay vui ơi là vui, cảm ơn quán nhiều nha!'],
              4: ['Dễ thương lắm, chỉ có một xíu xiu thôi nè.', 'Mình ưng nè, lần sau quán làm kỹ chút là mười điểm.'],
              3: ['Không sao đâu, ai cũng có ngày bận mà.', 'Mình tin quán sẽ tốt hơn, cố lên nha!'],
              2: ['Hơi tiếc chút xíu, nhưng mình không giận đâu.', 'Hôm nay chưa suôn sẻ lắm, mình góp ý nhẹ thôi nha.'],
              1: ['Mình hơi buồn, nhưng mong quán đọc được góp ý này.', 'Chắc hôm nay xui, mình vẫn mong lần sau khác hơn.']},
        thanks=['Quán rep nhanh quá trời, thương ghê 💛', 'Hihi cảm ơn quán nha, mai mình ghé tiếp!'],
        accept=['Đọc xong mình vui hẳn luôn, nâng sao nha 🥰', 'Quán thật lòng quá, mình sửa sao liền nè.'],
        keep=['Mình đọc rồi nè, cảm ơn quán nha! Sao để lần sau mình tăng.', 'Không sao đâu, mình vẫn thương quán mà.'],
        argue=['Mình nói thiệt lòng nha quán: {note}. Không phải mình khó đâu.', 'Mình cũng ngại nói, nhưng {note} thật mà.'],
        down=['Quán nói vậy làm mình hơi tủi thân… hạ sao nha.', 'Mình tưởng quán dễ thương mà trả lời vậy, buồn ghê.'],
        sorry=['Trời ơi mình nhầm, quê xỉu. Sửa sao liền nha quán!', 'Xin lỗi quán nha, mình nhớ lộn ngày. Sửa lại liền.'],
        moved=['Đọc mà rưng rưng luôn á, nâng sao liền nè {owner} ơi 💛', 'Trời ơi dễ thương dữ vậy, mình sửa sao lên liền nha!', 'Quán trả lời có tâm quá, mình cảm động thiệt sự 🥹'],
        laugh=['Haha quán lầy quá, mình cười muốn xỉu. Thêm sao nè 😂', 'Đọc rep mà cười cả buổi, thôi nâng sao cho quán nha 🤭'],
        jab=['Hihi quán vui tính ghê, mà {note} là thiệt nha 😅', 'Quán đùa dễ thương á, nhưng lần sau sửa giúp mình nha.'],
        seen=['Dạ mình đọc rồi nè 🙂', 'Cảm ơn quán nha.'],
        fans=['Thương quán quá, mình nâng sao và rủ cả nhóm bạn ghé ủng hộ nè! 💛', 'Nâng sao liền, cuối tuần mình dắt cả nhà qua luôn 🥰'],
        item_pos=['{item} ngon xỉu, nhớ hoài luôn.', '{item} đúng ý mình ghê.', 'Mình mê {item} hôm nay lắm nha.'],
        item_neg=['{item} hôm nay chưa được như mình mong thôi.', '{item} hơi tiếc xíu, lần sau chắc ổn hơn.']),
    'picky': dict(
        open={5: ['Tiêu chí nào cũng đạt. Ghi nhận.', 'Đúng chuẩn, không có điểm trừ.'],
              4: ['Đạt, có một chi tiết cần xem lại.', 'Ổn định, trừ một điểm nhỏ.'],
              3: ['Chất lượng không đồng đều.', 'Có ba điểm tôi thấy cần sửa, ghi dưới đây.'],
              2: ['Không đúng như mô tả.', 'Nhiều chi tiết lệch chuẩn.'],
              1: ['Không đạt yêu cầu tối thiểu.', 'Tôi đã ghi chú đầy đủ, quán tự đối chiếu.']},
        thanks=['Ghi nhận phản hồi đúng hạn.', 'Cảm ơn. Duy trì chuẩn này.'],
        accept=['Có biện pháp cụ thể. Tôi cộng lại một sao.', 'Cam kết rõ ràng. Điều chỉnh đánh giá.'],
        keep=['Chưa có số liệu hay biện pháp cụ thể. Giữ nguyên.', 'Tôi sẽ kiểm lại ở lần sau.'],
        argue=['Tôi ghi rõ: {note}. Đề nghị kiểm tra lại.', 'Dữ kiện không đổi: {note}.'],
        down=['Phản hồi không đúng mực. Trừ một sao.', 'Thiếu chuyên nghiệp. Điều chỉnh giảm.'],
        sorry=['Đối chiếu xong: tôi nhầm. Đã sửa.', 'Dữ liệu quán đưa ra khớp. Tôi điều chỉnh.'],
        moved=['Phản hồi đầy đủ, đúng trọng tâm. Tôi điều chỉnh lên mức tương xứng.', 'Có quy trình, có cam kết. Đủ cơ sở để tôi sửa đánh giá.'],
        laugh=['Hài hước không thay được giải pháp. Nhưng tôi ghi nhận thái độ, cộng một sao.'],
        jab=['Tôi cần biện pháp, không cần câu đùa.', 'Đùa không sửa được {note}.', 'Vui tính là một chuyện, chuẩn là chuyện khác.'],
        seen=['Đã xem. Chưa đủ thông tin.', 'Không có nội dung cụ thể.'],
        fans=['Phản hồi mẫu mực. Tôi điều chỉnh lên và sẽ giới thiệu cho đồng nghiệp.'],
        item_pos=['{item}: đạt chuẩn.', '{item} đúng mô tả.'],
        item_neg=['{item}: chưa đạt chuẩn.', '{item} lệch so với mô tả.']),
    'genz': dict(
        open={5: ['Slay quá quán ơi, 5 sao không bàn cãi 💅', 'Vibe xịn, người xinh, đồ ngon, hết nước chấm ✨'],
              4: ['Ổn áp nha, chỉ thiếu chút “wow” thôi.', 'Recommend nha mọi người, trừ một sao cho có động lực.'],
              3: ['Cũng ok, chưa đủ để lên story.', 'Bình thường thôi à, không “u mê” lắm.'],
              2: ['Hơi “căng” nha quán ơi 😬', 'Tâm trạng tụt dốc không phanh 📉'],
              1: ['Né gấp, né ngay 🏃', 'Tui buồn, tui 1 sao, tui đi về 🥲']},
        thanks=['Ui quán rep cưng xỉu 🫶', 'Thanks quán nha, hẹn gặp lại 😚'],
        accept=['Okela, quán rep có tâm quá nên up sao nè 🫡', 'Thấy thật lòng nên tui sửa sao nha ✨'],
        keep=['Oke seen, để lần sau tính nha 🙂‍↔️', 'Rep xinh nhưng sao vẫn để vậy nha 😌'],
        argue=['Ủa {note} mà quán, tui có ảnh nha 📸', 'Không phải tui khó, {note} thật á 🤨'],
        down=['Ủa alo? Rep vậy là toang rồi, hạ sao 🙄', 'Tụt mood thật sự, trừ sao nha 😤'],
        sorry=['Ối tui lộn, sorry quán nha 🙏 sửa liền!', 'Check lại thì tui sai thật, quê gì đâu 😭 sửa sao nè.'],
        moved=['Rep có tâm vậy ai chịu nổi, up full sao nè 🥹✨', 'Trời ơi quán iu quá, sửa sao liền tay 🫶'],
        laugh=['Rep mặn xỉu 😂 thôi up sao cho quán nha', 'Quán lầy dữ, tui cười ẻ, thêm sao 🤣'],
        jab=['Quán cà khịa tui hả 😏 được lắm, {note} vẫn là thật nha', 'Ủa rep vậy là sao, tui không cười nổi á 🙃'],
        seen=['Seen 👀', 'Ok 👍'],
        fans=['Rep vậy là tui up sao + share cho hội bạn liền 🫶✨', 'Quán iu quá, tui kéo cả team qua ủng hộ nha 🙌'],
        item_pos=['{item} là chân ái luôn ✨', '{item} ngon muốn xỉu 😋', '{item} xứng đáng lên story.'],
        item_neg=['{item} hơi “sai sai” nha 😵', '{item} chưa tới nha quán.']),
    'quiet': dict(
        open={5: ['Ngon. Sạch. Nhanh.', 'Đáng tiền.'], 4: ['Được.', 'Khá.'], 3: ['Tạm được.', 'Thường.'],
              2: ['Chưa ổn.', 'Không như mong đợi.'], 1: ['Không.', 'Thất vọng.']},
        thanks=['Ok.', '🙏'], accept=['Được. Nâng.', 'Ổn. Sửa sao.'], keep=['Ừ.', 'Giữ.'],
        argue=['Vẫn là {note}.'], down=['Kém. Hạ.'], sorry=['Nhầm. Sửa.'],
        moved=['Cảm ơn. Nâng sao.', 'Tử tế. Sửa lại.'], laugh=['Haha. Thêm sao.'], jab=['Không vui.', 'Sửa đi rồi đùa.'],
        seen=['.', 'Đã xem.'], fans=['Tốt. Sẽ giới thiệu bạn bè.'],
        item_pos=['{item} ổn.'], item_neg=['{item} chưa đạt.']),
    'parent_worried': dict(
        open={5: ['Con về vui lắm, gia đình yên tâm hẳn ạ.', 'Cảm ơn cô/thầy, tối qua con kể chuyện lớp say sưa.'],
              4: ['Cháu tiến bộ ạ, chỉ có điều tôi vẫn hơi băn khoăn.', 'Ổn ạ, mong cô/thầy để ý thêm giúp cháu.'],
              3: ['Cháu về hơi buồn, tôi muốn hỏi thêm ạ.', 'Tôi lo cháu theo không kịp các bạn.'],
              2: ['Tối qua cháu khóc, tôi lo quá.', 'Tôi cần cô/thầy giải thích giúp ạ.'],
              1: ['Cả nhà mất ngủ vì chuyện hôm nay.', 'Tôi thật sự rất lo cho cháu.']},
        thanks=['Dạ cảm ơn cô/thầy, tôi yên tâm rồi ạ.'],
        accept=['Nghe cô/thầy nói vậy tôi nhẹ lòng hẳn. Cảm ơn ạ.', 'Vậy là tôi yên tâm rồi, tôi sửa lại đánh giá ạ.'],
        keep=['Cảm ơn cô/thầy, nhưng tôi vẫn muốn theo dõi thêm ạ.', 'Tôi đọc rồi ạ, mong buổi sau cháu vui hơn.'],
        argue=['Nhưng cháu về kể {note}, tôi vẫn chưa hết lo ạ.', 'Tôi không trách, chỉ là {note} làm tôi lo.'],
        down=['Cô/thầy trả lời vậy tôi càng lo hơn ạ.', 'Tôi hỏi vì lo cho con, không ngờ nhận câu trả lời thế này.'],
        sorry=['Ôi vậy là cháu kể nhầm, tôi xin lỗi cô/thầy ạ.', 'Hóa ra sổ lớp ghi vậy, tôi lo hão rồi. Xin lỗi cô/thầy.'],
        moved=['Đọc tin nhắn của cô/thầy mà tôi nhẹ cả người. Cảm ơn nhiều lắm ạ.', 'Cô/thầy chu đáo quá, cả nhà yên tâm rồi ạ.'],
        laugh=['Cô/thầy vui tính quá, tôi đỡ lo hẳn ạ 😊'],
        jab=['Tôi đang lo thật mà cô/thầy lại đùa…', 'Chuyện của con, tôi mong cô/thầy trả lời nghiêm túc hơn ạ.'],
        seen=['Vâng ạ… nhưng tôi vẫn muốn biết thêm.', 'Chỉ vậy thôi ạ? Tôi vẫn lo.'],
        fans=['Cảm ơn cô/thầy, tôi sẽ kể cho các phụ huynh khác biết lớp mình tốt thế nào ạ.'],
        item_pos=['Bài {item} cháu về kể lại vanh vách.'], item_neg=['Bài {item} cháu về bảo chưa hiểu lắm.']),
    'parent_strict': dict(
        open={5: ['Đạt yêu cầu. Tôi ghi nhận.', 'Buổi học có tổ chức. Tốt.'],
              4: ['Nhìn chung được, còn một điểm cần làm rõ.', 'Tạm được, tôi sẽ hỏi thêm.'],
              3: ['Chưa đạt kỳ vọng của gia đình.', 'Tôi cần kế hoạch cụ thể cho con.'],
              2: ['Tôi đề nghị giáo viên trả lời bằng văn bản.', 'Không thể chấp nhận thêm lần nào nữa.'],
              1: ['Tôi đã soạn đơn gửi ban giám hiệu.', 'Rất không hài lòng.']},
        thanks=['Ghi nhận.'],
        accept=['Có kế hoạch rõ ràng. Tôi đồng ý.', 'Giải trình hợp lý. Điều chỉnh đánh giá.'],
        keep=['Tôi cần thấy kết quả, không cần lời hứa.', 'Chưa đủ. Tôi sẽ theo dõi.'],
        argue=['Giáo viên chưa trả lời vào vấn đề: {note}.', 'Tôi hỏi lại: {note}, xử lý thế nào?'],
        down=['Câu trả lời này sẽ được tôi chuyển lên nhà trường.', 'Thái độ như vậy tôi không chấp nhận.'],
        sorry=['Sổ lớp ghi rõ, tôi nhầm. Tôi rút lại ý kiến.'],
        moved=['Giải trình đầy đủ, có kế hoạch. Tôi rút lại phản ánh và nâng đánh giá.'],
        laugh=['Tôi không thấy chuyện này đáng đùa, nhưng tôi ghi nhận thiện chí.'],
        jab=['Đây là chuyện học của con, không phải chuyện đùa.', 'Giáo viên trả lời phụ huynh kiểu đùa cợt là không nên.'],
        seen=['Chỉ vậy thôi sao? Tôi cần giải trình.', 'Câu trả lời quá sơ sài.'],
        fans=['Cách làm việc chuyên nghiệp. Tôi sẽ nói với ban đại diện phụ huynh.'],
        item_pos=['Bài {item} được chuẩn bị kỹ.'], item_neg=['Bài {item} tổ chức chưa chặt.']),
    'parent_kind': dict(
        open={5: ['Cả nhà cảm ơn cô/thầy nhiều lắm ạ 💐', 'Con về khoe mãi, cảm ơn cô/thầy ạ.'],
              4: ['Con thích lắm ạ, có một góp ý nhỏ thôi.', 'Buổi học vui, cảm ơn cô/thầy.'],
              3: ['Mình cùng để ý thêm cho con nhé ạ.', 'Con hơi mệt, chắc tại hôm nay trời nóng.'],
              2: ['Hôm nay con hơi buồn, mình trao đổi thêm nhé ạ.'],
              1: ['Gia đình muốn gặp cô/thầy để cùng tìm cách ạ.']},
        thanks=['Dạ cảm ơn cô/thầy ạ 🙏'],
        accept=['Cảm ơn cô/thầy đã phản hồi, gia đình yên tâm ạ.', 'Vâng ạ, nhà mình sẽ cùng nhắc con.'],
        keep=['Dạ cảm ơn cô/thầy, mình cùng theo dõi thêm ạ.'],
        argue=['Dạ gia đình hiểu, chỉ là {note} nên nhờ cô/thầy để ý giúp ạ.'],
        down=['Gia đình hơi buồn vì câu trả lời này ạ.'],
        sorry=['Ôi gia đình nhầm rồi, xin lỗi cô/thầy ạ.'],
        moved=['Cô/thầy tận tâm quá, gia đình cảm động lắm ạ 💐', 'Cảm ơn cô/thầy, đọc xong cả nhà ai cũng vui ạ.'],
        laugh=['Cô/thầy vui tính quá, con về chắc lại kể cho cả nhà nghe ạ 😄'],
        jab=['Dạ cô/thầy đùa vui ạ, nhưng nhờ cô/thầy để ý giúp con chuyện {note} nhé.'],
        seen=['Dạ vâng ạ.'],
        fans=['Cảm ơn cô/thầy, gia đình sẽ giới thiệu lớp cho các phụ huynh khác ạ.'],
        item_pos=['Bài {item} con thích lắm ạ.'], item_neg=['Bài {item} con bảo hơi khó ạ.']),
    'knowitall': dict(
        open={5: ['Được. Anh gật đầu là hiếm lắm đấy nhé.', 'Anh ăn khắp phố rồi, chỗ này tạm lọt top.'],
              4: ['Anh chấm bốn, năm sao anh để dành cho chỗ anh mở.', 'Khá, cần thêm vài năm kinh nghiệm.'],
              3: ['Em làm theo sách, còn anh làm theo nghề.', 'Không tệ, nhưng thiếu tầm nhìn.'],
              2: ['Anh chỉ nói một lần thôi: sai hết từ khâu chuẩn bị.', 'Em đọc kỹ góp ý của anh, miễn phí đấy.'],
              1: ['Anh tư vấn cho nhiều quán lắm, chỗ này cứu không nổi.', 'Anh không chấm không sao là vì hệ thống không cho.']},
        thanks=['Ừ. Biết nghe lời anh là khôn.', 'Được, cứ thế mà lên.'],
        accept=['Đấy, anh nói có sai đâu. Anh cho thêm sao.', 'Chịu tiếp thu là có tương lai. Anh sửa đánh giá.'],
        keep=['Em cứ làm đi, anh sẽ quay lại soi.', 'Viết thì hay, anh cần thấy hành động.'],
        argue=['Em giải thích là em chưa hiểu vấn đề: {note}.', 'Anh nói lại lần cuối: {note}.'],
        down=['Em có biết anh là ai không? Hạ sao.', 'Anh góp ý mà em trả treo. Hạ sao, cho em nhớ.'],
        sorry=['Ừ thì hôm đó anh nhìn nhầm. Nhưng tổng thể anh vẫn đúng.', 'Thôi anh sửa, coi như anh nhường em lần này.'],
        moved=['Được, em biết cư xử. Anh nâng sao, nhớ giữ phong độ.', 'Anh ít khi đổi ý đâu, nhưng lần này em xứng đáng.'],
        laugh=['Cũng biết đùa đấy. Anh thêm sao, nhưng nghề thì phải học anh.'],
        jab=['Em đùa với anh à? Anh làm nghề mười năm, anh không đùa.', 'Cà khịa anh là em sai người rồi.', 'Nói dí dỏm không làm {note} biến mất đâu em.'],
        seen=['Ngắn thế thôi à em? Anh còn chờ nghe em giải thích.', 'Ừ.'],
        fans=['Anh nâng sao, còn giới thiệu cho hội anh em trong nghề. Đừng làm anh mất mặt.'],
        item_pos=['{item} tạm, đúng kiểu anh hay dạy.', '{item} được, chắc có người chỉ.'],
        item_neg=['{item} làm sai kỹ thuật cơ bản.', '{item} mà đưa anh làm thì khác hẳn.']),
    'rude': dict(
        open={5: ['Được. Vậy thôi.', 'Hết chê.'], 4: ['Tạm. Đừng hỏi thêm.', 'Được, trừ cái mặt nhân viên.'],
              3: ['Thường. Rất thường.', 'Không đáng nhắc.'], 2: ['Dở. Đi về.', 'Thua cả hàng rong đầu ngõ.'],
              1: ['Không ai tới là vừa.', 'Chán không buồn nói.']},
        thanks=['Ờ.'], accept=['Ờ, còn biết điều. Thêm sao.', 'Được. Lần này thôi.'],
        keep=['Rồi sao?', 'Nói nhiều thế.'], argue=['Chối gì nữa, {note}.', '{note}. Hết.'],
        down=['Láo. Hạ.', 'Cãi hay nhỉ. Hạ luôn.'], sorry=['Ờ nhầm. Sửa.'],
        moved=['Ờ… cũng được. Nâng sao, đừng làm tôi hối hận.'], laugh=['Hừ. Buồn cười. Thêm sao.'],
        jab=['Đùa với ai?', 'Buồn cười lắm à? {note} đấy.', 'Cà khịa khách à? Hay.'],
        seen=['…', 'Đọc rồi.'], fans=['Được. Tôi bảo mấy thằng bạn ra thử.'],
        item_pos=['{item} được.'], item_neg=['{item} dở.', '{item}? Thôi.']),
    'entitled': dict(
        open={5: ['Tốt. Nhớ mặt tôi, lần sau ưu tiên.', 'Được. Khách VIP thì phải thế.'],
              4: ['Ổn, nhưng không ai ra chào tôi.', 'Được, thiếu mỗi món quà tri ân khách quen.'],
              3: ['Tôi phải tự nhắc mới được phục vụ.', 'Khách sộp mà phải đợi như ai.'],
              2: ['Tôi đã nói tôi đang vội.', 'Không có chế độ khách quen à?'],
              1: ['Tôi sẽ không giới thiệu ai tới đây.', 'Phục vụ không xứng với tiền tôi bỏ ra.']},
        thanks=['Được. Nhớ ưu đãi lần sau.'],
        accept=['Có thành ý thế này thì tôi sửa.', 'Tốt, quà nhận rồi, sao tôi sửa.'],
        keep=['Lời xin lỗi không làm tôi no.', 'Tôi cần thấy ưu đãi, không cần lời văn.'],
        argue=['Khách nói {note} là {note}.', 'Giải thích làm gì, tôi trả tiền mà.'],
        down=['Dám dạy khách à? Hạ sao.', 'Tôi không quay lại, hạ sao.'],
        sorry=['Thôi được, nhầm thì sửa. Nhưng nhớ ưu tiên tôi.'],
        moved=['Biết chiều khách thế này tôi nâng sao, lần sau nhớ chỗ ngồi đẹp.'],
        laugh=['Cũng dí dỏm. Nhưng quà đâu?'],
        jab=['Cà khịa khách à? Tôi là khách đấy.', 'Đùa với khách VIP là không được đâu.'],
        seen=['Vậy thôi? Không có ưu đãi gì à?', 'Tôi chờ thành ý.'],
        fans=['Được, tôi nâng sao và sẽ giới thiệu cho bạn bè cỡ tôi.'],
        item_pos=['{item} tạm xứng tầm.'], item_neg=['{item} không xứng tầm khách như tôi.']),
    'drama': dict(
        open={5: ['Tốt, group Review sẽ biết chỗ này ổn.', 'Không có gì để bóc, lạ thật đấy.'],
              4: ['Có một chi tiết mình đã chụp lại, cẩn thận nha.', 'Tạm tha lần này.'],
              3: ['Ảnh đã lưu vào máy, chưa đăng thôi.', 'Mình đang viết nháp, tùy quán.'],
              2: ['Chờ phản hồi, không thì lên bài.', 'Group hai chục nghìn thành viên đang chờ.'],
              1: ['Bài đăng đã sẵn, quán chọn đi.', 'Hoàn tiền hoặc lên sóng, không có lựa chọn thứ ba.']},
        thanks=['Ok, mình ghi nhận thành ý.'],
        accept=['Được, mình xóa bài nháp. Sửa sao.', 'Có đền bù thì mình không đăng nữa.'],
        keep=['Nói thì ai chẳng nói.', 'Mình vẫn giữ bài nháp nha.'],
        argue=['Mình có bằng chứng: {note}.', 'Cãi là mình đăng đó, {note}.'],
        down=['Rep kiểu này lên group là nổ nha.', 'Chụp rồi, đăng rồi.'],
        sorry=['Ờ… xem lại ảnh thì mình nhầm. Mình không đăng.'],
        moved=['Ok, thấy thành ý thật rồi. Mình gỡ nháp và nâng sao.'],
        laugh=['Rep lầy vậy ai nỡ bóc 😂 thôi nâng sao.'],
        jab=['Cà khịa hả? Để xem group nói gì.', 'Đùa hay ha, mai lên sóng nhé.'],
        seen=['Im lặng là đồng ý đăng đó nha.', 'Chỉ vậy thôi hả? Ok.'],
        fans=['Mình nâng sao và đăng bài khen quán lên group luôn nè!'],
        item_pos=['{item} thì ok, không có gì để bóc.'], item_neg=['{item} mình chụp lại rồi nha.']),
    'troll': dict(
        open={5: ['Năm sao vì hôm nay trời đẹp.', 'Chấm năm sao, lý do bí mật.'], 4: ['Bốn sao vì mình thích số bốn.', 'Ok ok.'],
              3: ['Ba sao cho cân bằng vũ trụ.', 'Tạm tạm được.'], 2: ['Hai sao, tâm trạng thôi.', 'Hmm.'],
              1: ['Một sao vì mèo nhà mình bảo vậy.', 'Không thích, không lý do.']},
        thanks=['Ờ hay.'], accept=['Thôi thêm sao cho vui.', 'Ok nâng.'], keep=['Kệ đi.', 'Để vậy cho vui.'],
        argue=['Mình thích vậy đó, {note}.'], down=['Nóng dữ, hạ.', 'Ơ cay à 😂 hạ.'], sorry=['Nhầm, sửa.'],
        moved=['Ờ trả lời dễ thương, sửa sao cho vui.'], laugh=['😂😂 quán lầy hơn cả mình, thêm sao', 'Haha được, thua quán, thêm sao.'],
        jab=['Cà khịa lại nè: 🙃', 'Quán vui ghê, mình cũng vui, sao để vậy.'],
        seen=['👀', 'Ờ.'], fans=['Ờ vui, nâng sao, rủ tụi bạn vào quậy… à không, vào ủng hộ 😆'],
        item_pos=['{item} chắc ổn.'], item_neg=['{item} chắc không ổn.']),
    'parent_knowitall': dict(
        open={5: ['Được, đúng hướng tôi hay khuyên.', 'Tạm ổn, cô/thầy có tiến bộ.'],
              4: ['Khá, nhưng tôi có mấy tài liệu cô/thầy nên đọc.', 'Được, cần thêm phương pháp mới.'],
              3: ['Phương pháp chưa phù hợp với con tôi.', 'Tôi đề xuất đổi cách chia nhóm.'],
              2: ['Tôi dạy con ở nhà còn tốt hơn.', 'Cần xem lại toàn bộ giáo án.'],
              1: ['Tôi sẽ gửi ban giám hiệu góp ý chi tiết.', 'Không đạt chuẩn sư phạm.']},
        thanks=['Được, cô/thầy cứ theo góp ý của tôi.'],
        accept=['Thấy chưa, nghe phụ huynh là đúng. Tôi sửa đánh giá.'],
        keep=['Tôi vẫn giữ quan điểm.', 'Cảm ơn, làm được rồi hãy nói.'],
        argue=['Tôi cũng từng đứng lớp: {note}.', 'Cô/thầy chưa hiểu ý tôi: {note}.'],
        down=['Tôi sẽ nêu chuyện này ở họp phụ huynh.', 'Trả lời thế là thiếu tôn trọng phụ huynh.'],
        sorry=['Ừ thì tôi hiểu nhầm. Nhưng phương pháp của tôi vẫn đáng tham khảo.'],
        moved=['Cô/thầy biết lắng nghe, tôi đánh giá cao. Nâng sao.'],
        laugh=['Cô/thầy dí dỏm đấy. Nhưng phương pháp vẫn cần xem lại.'],
        jab=['Tôi góp ý chuyên môn, cô/thầy lại đùa?', 'Cà khịa phụ huynh là không chuyên nghiệp.'],
        seen=['Chỉ vậy thôi sao?', 'Tôi chờ câu trả lời chuyên môn.'],
        fans=['Tôi nâng sao và sẽ nói tốt với ban đại diện phụ huynh.'],
        item_pos=['Bài {item} làm đúng phương pháp.'], item_neg=['Bài {item} nên dạy theo cách khác.']),
    'parent_rude': dict(
        open={5: ['Được.', 'Ổn. Giữ vậy.'], 4: ['Tạm.', 'Được, đừng để tôi nhắc.'],
              3: ['Dạy vậy à?', 'Học phí đâu có rẻ.'], 2: ['Chán.', 'Tôi tính chuyển lớp.'],
              1: ['Không chấp nhận.', 'Tôi lên gặp hiệu trưởng.']},
        thanks=['Ừ.'], accept=['Được rồi.', 'Nghe được.'], keep=['Làm đi rồi nói.', 'Đọc rồi.'],
        argue=['{note}. Trả lời đi.'], down=['Nói vậy với phụ huynh à?', 'Tôi đưa lên nhóm lớp.'],
        sorry=['Ờ, tôi nhầm.'],
        moved=['Ờ, trả lời vậy thì được. Tôi sửa.'], laugh=['Đùa hay đấy. Thôi được.'],
        jab=['Đùa với phụ huynh à?', 'Cà khịa tôi à? Được lắm.'],
        seen=['Vậy thôi à?', 'Ừ.'], fans=['Được, tôi nói tốt trong nhóm lớp.'],
        item_pos=['Bài {item} được.'], item_neg=['Bài {item} dạy chán.']),
}

# Closers by the day's stage and the shop's mood. {owner} is how people call the player.
CLOSE = {
    'customer': dict(
        early_pos=['Quán mới mở mà chỉn chu vậy là có tương lai.', 'Mới khai trương mà đã ra dáng lắm rồi.', 'Ủng hộ quán mới mở nha!'],
        early_neg=['Quán mới mở, chắc còn bỡ ngỡ.', 'Mới mở nên mình thông cảm, lần sau cố hơn nha.'],
        late_pos=['Ghé từ hồi quán mới mở, giờ vẫn giữ phong độ.', 'Khách quen xác nhận: chất lượng đều tay.', 'Càng ngày càng lên tay đó {owner}.'],
        late_neg=['Hồi mới mở làm kỹ hơn cơ.', 'Đông khách rồi thì đừng làm ẩu nha.'],
        festival_pos=['Ngày hội đông nghẹt mà vẫn làm kỹ, nể.', 'Phố đang hội mà quán vẫn chu đáo.'],
        festival_neg=['Biết là ngày hội đông, nhưng vẫn phải kỹ chứ.', 'Hội phố đông quá nên quán rối hết.'],
        calm_pos=['Hôm nay vắng nên được phục vụ kỹ ghê.', 'Chiều nay yên ả, ngồi thích lắm.'],
        calm_neg=['Vắng khách vậy mà còn chậm.', 'Hôm nay vắng hoe mà vẫn làm sai.']),
    'parent': dict(
        early_pos=['Lớp mới bắt đầu mà các con đã vào nề nếp.', 'Mới những buổi đầu mà con đã thích đi học.'],
        early_neg=['Biết là mới những buổi đầu, nhưng mong cô/thầy để ý hơn.'],
        late_pos=['Cả năm theo dõi, tôi thấy lớp tiến bộ rõ.', 'Con học với cô/thầy lâu rồi, càng ngày càng ưng.'],
        late_neg=['Mấy tuần gần đây lớp có vẻ lơi hơn trước.'],
        festival_pos=['Ngày hội ở trường mà vẫn giữ lớp ngăn nắp.'], festival_neg=['Ngày hội ồn ào nên buổi học hơi loãng.'],
        calm_pos=['Buổi học nhẹ nhàng, con về vui.'], calm_neg=['Buổi học nhẹ mà con vẫn chưa theo kịp.']),
}

# ------------------------------------------------------------------ styles
STYLES = ('short', 'emoji', 'teencode', 'rant', 'lifestory', 'regular', 'handsome', 'sarcastic', 'p_short', 'p_story', 'p_long', 'p_emoji')
DOMAIN_EMOJI = {'drink': '🧋', 'food': '🍜', 'stay': '🏡', 'flower': '💐', 'repair': '🔧', 'farm': '🥬', 'delivery': '🛵', 'pet': '🐶',
                'salon': '💇', 'shop': '🛍️', 'pharmacy': '💊', 'office': '📑', 'pagoda': '🪷'}
NOUN = {'milk_tea': 'ly trà', 'restaurant': 'tô mì', 'cafe_bakery': 'ly cà phê', 'florist': 'bó hoa', 'grocery': 'đơn hàng', 'repair': 'món đồ sửa',
        'farm': 'mẻ rau', 'delivery': 'đơn giao', 'homestay': 'phòng', 'pet_care': 'bé cưng', 'salon': 'mái tóc', 'teacher': 'buổi học',
        'tour_guide': 'chuyến đi', 'mother_baby': 'món quà', 'pharmacy': 'đơn thuốc', 'clothing': 'bộ đồ', 'tra_da': 'cốc trà đá', 'pet_shop': 'món hàng',
        'fruit': 'ký trái cây', 'garbage': 'chuyến thu gom', 'drain': 'đường ống', 'homemaker': 'việc nhà', 'ice_cream': 'ly kem', 'pho': 'tô phở', 'com': 'dĩa cơm',
        'nail': 'bộ móng', 'pagoda': 'việc chùa', 'photobooth': 'dải ảnh', 'giupviec': 'lượt dọn nhà', 'naucom': 'bữa cơm', 'library': 'lượt mượn sách', 'babysitter': 'buổi trông bé',
        'railway': 'ca gác chắn', 'nurse': 'ca chăm sóc', 'lighthouse': 'ca trực đèn'}
BASE_NAME = {'milk': 'trà sữa', 'black': 'hồng trà', 'matcha': 'matcha', 'green': 'lục trà', 'oolong': 'olong', 'thai': 'trà Thái'}
SHORT = {'pos': ['ok', 'Ổn.', 'Được nha.', 'Ngon.', '10 điểm.', 'Ok áp 👌', 'Sẽ quay lại.', 'Không chê.', 'Đỉnh.', 'Ưng.', 'Good.', 'Được đấy.']}
EMOJI = {'pos': ['{e}👍✨', '😍{e}😍', '🔥🔥🔥', '💯{e}', '🥰{e}🥰', '👏👏👏', '{e}{e}{e}', '🤤{e}', '⭐⭐⭐⭐⭐', '😋👌']}
TEEN = {
    'pos': ['{item} ngon xỉu lun á, 10đ ko có nhưng 😭', 'Oki quán ơi, lần sau ghé típ nhe 🫶', 'dth quá trời, mn nên thử nha', 'z là đc r, ưng ghia 😚',
            'iu quán nhìu nhìu, {item} okela 🥰', 'hông có j để chê lun á mn ơi ✨'],
    'mid': ['cx đc, ko có j đặc biệt 🤷', 'tạm ổn nha, chưa tới mức wow', 'bth thui, ko biết nói j 🙂‍↔️', '{item} cx dc, nma {note} 😶'],
    'neg': ['hơi xu cà na nha quán, {note} 🥲', 'ko ưng lắm á, {note}, buồn j đâu 😮‍💨', 'thiệt sự là hơi toang, {note} 🙃', 'j z trời, {note} 😵‍💫',
            'ủa alo, {note} là sao z quán 🤨']}
RANT = {
    'intro': ['Chuyện là thế này, hôm nay tôi tan làm muộn, vừa đói vừa mệt, định ghé cho nhanh rồi về.',
              'Tôi kể hơi dài mọi người thông cảm. Sáng nay dắt xe ra thì xe xẹp lốp, đi bộ ra đầu hẻm mới thấy tiệm.',
              'Hôm nay là ngày nghỉ phép hiếm hoi của tôi, nên muốn tự thưởng một chút.',
              'Mẹ tôi dặn đi đâu cũng phải đánh giá cho công bằng, nên tôi viết kỹ.',
              'Tôi vốn ít viết đánh giá, nhưng hôm nay nhiều chuyện quá nên phải kể.'],
    'pos': ['Phải nói là {label} ổn thật: {note}.', 'Được cái {label} làm tốt, {note}.'],
    'neg': ['Vậy mà {label} thì… {note}.', 'Đến đoạn {label} thì tôi hơi hụt hẫng: {note}.'],
    'tangent': ['Trong lúc chờ tôi còn kịp nghe hết chuyện nhà bàn bên cạnh.', 'Xong đi về thì trời đổ mưa, nhưng cái đó không phải lỗi tiệm.',
                'Tiện nói luôn là con mèo nhà bên cứ nhìn tôi suốt, dễ thương.', 'À, bãi gửi xe đầu hẻm cũng chật, nhưng thôi.',
                'Nhân tiện, bài nhạc tiệm mở làm tôi nhớ thời sinh viên ghê.'],
    'end_pos': ['Tóm lại là ổn, tôi sẽ quay lại, có khi rủ cả cơ quan.', 'Tóm lại: đáng tiền. Cảm ơn ai đã đọc tới đây.'],
    'end_neg': ['Tóm lại là tôi hơi buồn, nhưng vẫn cho thêm một cơ hội.', 'Tóm lại là chưa ổn. Ai đọc tới đây thì cảm ơn nhé.',
                'Tôi viết dài vì tôi quý tiệm, chứ ghét thì tôi đi luôn rồi.']}
P_RANT = {
    'intro': ['Tôi xin phép nói dài một chút. Tối qua con ăn cơm xong cứ ngồi kể chuyện lớp mãi.',
              'Tôi đi làm cả ngày, tối mới có thời gian hỏi con, nên nhắn muộn cô/thầy thông cảm.',
              'Nhà tôi ba đời làm nông, giờ con được đi học đàng hoàng nên tôi để ý lắm.'],
    'pos': ['Con kể {label} rất tốt: {note}.'], 'neg': ['Có điều về {label}: {note}.'],
    'tangent': ['Nhân tiện, tuần sau con có sinh nhật, cháu cứ đòi mang bánh lên lớp.', 'Bà nội cháu cũng gửi lời hỏi thăm cô/thầy.',
                'Hôm qua cháu còn đòi mua cặp mới giống bạn cùng bàn.'],
    'end_pos': ['Gia đình cảm ơn cô/thầy nhiều.'], 'end_neg': ['Mong cô/thầy để ý giúp gia đình ạ.', 'Tôi nói vậy thôi, mong cô/thầy thông cảm.']}
LIFESTORY = [
    'Hôm nay là ngày đầu tôi đi làm lại sau một thời gian dài ốm. Ghé đây được đối xử nhẹ nhàng, thấy đời dễ thương hẳn. Cảm ơn {owner} nhiều.',
    'Bà tôi hồi còn sống hay dắt tôi đi quanh khu này. Hôm nay ghé tiệm, được hỏi han tử tế, tự nhiên nhớ bà. Cảm ơn tiệm.',
    'Mới chuyển lên thành phố, chưa quen ai. Được {owner} hỏi han vài câu mà thấy bớt cô đơn hẳn.',
    'Hôm nay tôi vừa nhận tin đậu phỏng vấn, ghé tự thưởng. Được {item} đúng ý, coi như may mắn nhân đôi 🥹',
    'Hai vợ chồng giận nhau cả tuần, ghé đây ngồi một lúc tự nhiên làm lành. Cảm ơn tiệm đã có mặt đúng lúc.',
    'Con tôi nằm viện mấy hôm, hôm nay được về. Tôi ghé lấy {item} mang về cho cả nhà, được làm kỹ lắm. Cảm ơn nhiều.',
    'Ba tôi mất năm ngoái, ông hay đi ngang con phố này. Hôm nay ghé, được chào hỏi ấm áp, tự nhiên thấy lòng nhẹ hơn.']
P_STORY = [
    'Con tôi vốn nhút nhát, hôm nay về khoe được cô/thầy khen trước lớp. Cả nhà vui cả tối. Cảm ơn cô/thầy nhiều lắm.',
    'Bố cháu đi công tác xa, cháu hay buồn. Hôm nay cháu về cười suốt, kể chuyện lớp không ngừng. Cảm ơn cô/thầy.',
    'Tôi học không nhiều nên không kèm con được. Thấy cô/thầy kiên nhẫn với cháu, tôi biết ơn lắm.',
    'Cháu nói lớn lên muốn làm giáo viên giống cô/thầy. Tôi nghe mà rưng rưng.']
REGULAR = {
    'pos': ['Khách quen đây! Ghé lần thứ {n} rồi mà {owner} vẫn nhớ mình thích gì. Mãi iu.', 'Lần thứ {n} ghé, chất lượng vẫn giữ. Khách quen chứng nhận ✅',
            'Tuần nào cũng ghé, hôm nay {item} vẫn chuẩn như mọi lần.', 'Lần thứ {n} rồi đó nha {owner}, lần sau nhớ giảm giá khách quen 😆'],
    'neg': ['Khách quen lần thứ {n} nên nói thật: hôm nay {note}. Không giống mọi lần nha.', 'Ghé {n} lần rồi, lần này hơi hụt: {note}. Mình vẫn quý quán nên mới nói.']}
HANDSOME = {
    'male': ['5 sao vì anh chủ đẹp trai, còn {item} thì… để lần sau mình tính 😆', 'Anh chủ đẹp trai quá nên quên mất mình gọi gì. 5 sao!',
             'Nói thật đồ thì tạm, nhưng anh chủ cười cái là 5 sao liền 😳'],
    'female': ['5 sao vì chị chủ xinh, còn {item} thì… để lần sau mình tính 😆', 'Chị chủ xinh quá nên quên mất mình gọi gì. 5 sao!',
               'Nói thật đồ thì tạm, nhưng chị chủ cười cái là 5 sao liền 😳'],
    None: ['5 sao vì chủ quán dễ thương, còn {item} thì… để lần sau tính 😆', 'Chủ quán nói chuyện duyên quá nên 5 sao, còn món thì bình thường thôi.']}
SARCASTIC = {
    'speed': ['Tuyệt vời, chờ lâu tới mức tôi kịp lên kế hoạch cho cả tuần 👏 ({note})', 'Phục vụ nhanh như gió… gió mùa năm sau 🙂 ({note})'],
    'accuracy': ['Gọi một đằng ra một nẻo, đúng là có năng khiếu gây bất ngờ 👏 ({note})', 'Rất sáng tạo, tôi dặn gì thì làm khác đi, đỉnh 🙂 ({note})'],
    'attitude': ['Thân thiện lắm, thân thiện tới mức không thèm hỏi khách một câu 🙂 ({note})'],
    '': ['Trải nghiệm “đáng nhớ” thật, nhớ để lần sau né 👏 ({note})', 'Mười điểm cho sự tự tin, còn {label} thì để hôm khác 🙂 ({note})',
         'Hay lắm, {label} kiểu này chắc định lập kỷ lục 👏 ({note})']}
P_SHORT = {'pos': ['Vâng, cảm ơn ạ.', 'Ok cô/thầy.', 'Đã xem ạ.', 'Tốt ạ.', 'Cảm ơn.', '👍'], 'neg': ['Con về kể {note}. Cô/thầy xem giúp.', '{note}?']}
P_EMOJI = ['🙏🙏', '👍❤️', '🥰📚', '👏👏👏', '💐🙏']
# How styled reviewers answer: outcome group -> lines (no {note} for emoji/short).
STYLE_REACT = {
    'emoji': dict(up=['🥹🙏', '😍⭐', '🫶'], keep=['👍', '👌', '🙂'], down=['😤👎', '🙄'], argue=['🤨❓', '😑']),
    'short': dict(up=['Ok, sửa.', 'Được. Nâng.'], keep=['Ok.', 'Ừ.'], down=['Thôi.', 'Hạ.'], argue=['Không.', 'Vẫn vậy.']),
    'p_short': dict(up=['Vâng ạ.'], keep=['Vâng.'], down=['Thôi.'], argue=['Vẫn vậy ạ.']),
    'p_emoji': dict(up=['🙏🥰'], keep=['👍'], down=['😞'], argue=['🤔']),
    'handsome': dict(up=['Chủ quán rep cũng duyên nữa, mê 😍'], keep=['Hihi chủ quán rep kìa, sao để nguyên 5 nha 😳', 'Rep dễ thương vậy ai nỡ sửa 🫣'],
                     down=['Ơ, đẹp mà nói chuyện gắt ghê… thôi hạ sao 😶'], argue=['Chủ quán đẹp nhưng {note} là thật nha 😅']),
    'lifestory': dict(up=['Đọc mà rưng rưng, cảm ơn {owner} nhiều lắm 🥹'], keep=['Cảm ơn {owner} đã đọc chuyện của mình 🥹', 'Mình sẽ còn ghé hoài, cảm ơn nha.'],
                      down=['Mình kể chuyện buồn mà nhận câu này… thôi.'], argue=['Mình chỉ muốn kể chuyện thôi mà.']),
    'regular': dict(up=['Khách quen mà, giận gì lâu, sửa sao nha {owner} 😆'], keep=['Khách quen đọc rồi nha, mai ghé tiếp.'],
                    down=['Khách quen mà rep vậy, buồn thật sự.'], argue=['Khách quen nói thật nên mới góp ý: {note}.']),
}

# -------------------------------------------------------------- reply tones
TONE_ORDER = ('warm', 'funny', 'sassy', 'facts', 'sorry', 'invite', 'process', 'genz', 'silent', 'harsh')
TONES = {
    'warm': dict(label='Ấm áp', emoji='💛', risk='safe', customer=[
        'Cảm ơn {who} nhiều lắm vì đã ghé và dành thời gian viết mấy dòng này. Đọc xong cả tiệm thấy ấm lòng ạ 💛',
        'Dạ tiệm cảm ơn {who} thật lòng. Góp ý về {label} tiệm ghi lại rồi, mong được gặp lại {who} sớm ạ.',
        'Cảm ơn {who} đã chọn tiệm giữa bao nhiêu chỗ khác. Lời {who} viết là động lực cho cả ca hôm nay ạ.',
        'Tiệm đọc đi đọc lại review của {who} luôn á. Cảm ơn {who} nhiều, chúc {who} một ngày thật vui ạ!'],
        parent=['Cảm ơn phụ huynh đã dành thời gian nhắn cho lớp. Tôi đọc kỹ từng dòng và rất trân trọng ạ.',
                'Dạ cảm ơn anh chị nhiều. Góp ý về {label} tôi ghi lại rồi, mình cùng đồng hành với con nhé.',
                'Được phụ huynh quan tâm như vậy là niềm vui của lớp ạ. Cảm ơn anh chị thật lòng.']),
    'funny': dict(label='Hài hước tự trào', emoji='😂', risk='safe', customer=[
        'Đọc review xong tiệm đứng hình mất năm giây 😅 Hứa lần sau {label} sẽ xịn tới mức {who} phải sửa review ạ!',
        'Tiệm xin nhận một vé “ăn hành” cho {label} ạ 🧅 Lần sau quay lại, tiệm đền bằng nụ cười rộng gấp đôi!',
        'Dạ tiệm đã dán review này lên tường để tự nhắc mỗi sáng 😂 Cảm ơn {who} đã “khai sáng” ạ.',
        'Tiệm đọc xong mà muốn tự trừ lương mình luôn á 🥲 Hẹn {who} lần sau, tụi mình chuộc lỗi ạ!'],
        parent=['Dạ tôi xin nhận điểm “cần cố gắng” ở mục {label} ạ 😅 Buổi sau lớp sẽ “nâng cấp” ngay!',
                'Đọc tin nhắn xong tôi tự giao bài tập về nhà cho mình luôn ạ 😄 Cảm ơn phụ huynh đã “chấm bài” giúp.',
                'Dạ tôi ghi vào sổ “bài học hôm nay” rồi ạ, lần này học trò là tôi 😄']),
    'sassy': dict(label='Cà khịa nhẹ', emoji='😏', risk='risky', customer=[
        'Dạ theo sổ thì {fact} đó ạ. Chắc hôm đó {who} kỳ vọng vào tiệm cao quá, tiệm cảm động ghê 😌',
        'Tiệm ghi nhận hết ạ, riêng vụ {label} thì {fact}, chắc tại trời nóng nên cảm giác hơi khác thôi {who} ơi 🙂',
        'Cảm ơn {who} đã chấm điểm kỹ như giám khảo ẩm thực ạ 😄 Lần sau tiệm xin được thi lại vòng {label}!',
        'Dạ tiệm nhận góp ý, còn buồn thì để mai, nay khách đông quá chưa kịp buồn ạ 😌'],
        parent=['Dạ theo sổ lớp thì {fact} ạ. Chắc các con về kể hơi “sáng tạo”, lớp mình học văn tốt quá 😌',
                'Tôi ghi nhận ạ. Riêng chuyện {label} thì {fact}, phụ huynh ghé lớp một buổi là thấy ngay ạ 🙂',
                'Dạ cảm ơn phụ huynh chấm kỹ như đoàn kiểm tra ạ 😄 Mời anh chị dự giờ cho khách quan luôn nhé.']),
    'facts': dict(label='Nêu sự thật', emoji='📋', risk='safe', customer=[
        'Dạ, theo phiếu ghi hôm đó: {fact}. Bên mình gửi lại để cùng đối chiếu ạ.',
        'Tiệm đã xem lại hóa đơn và ghi chép ca đó: {fact}. Nếu {who} còn thấy chỗ nào khác, tiệm sẵn sàng kiểm tra thêm ạ.',
        'Dạ bên mình có ghi nhận cụ thể: {fact}. Tiệm gửi {who} để mình cùng nhìn lại cho công bằng ạ.'],
        parent=['Dạ, theo sổ lớp hôm đó: {fact}. Mong phụ huynh xem lại giúp ạ.',
                'Tôi đã xem lại sổ điểm danh và phiếu cuối tiết: {fact}. Phụ huynh cần thêm thông tin gì, tôi gửi ngay ạ.',
                'Dạ hồ sơ lớp ghi rõ: {fact}. Tôi gửi để mình cùng nắm tình hình của con ạ.']),
    'sorry': dict(label='Xin lỗi + bù đắp', emoji='🙏', risk='safe', customer=[
        'Thành thật xin lỗi {who} vì {label} chưa tốt. Tiệm đã sửa lại quy trình, lần sau {who} ghé tiệm xin bù cho chu đáo ạ.',
        'Tiệm xin lỗi {who} ạ. Chuyện {fact} là lỗi của tụi mình, tiệm đã nhắc lại cả ca để không lặp lại.',
        'Dạ tiệm nhận lỗi hoàn toàn. Mong {who} cho tiệm một cơ hội sửa sai, tiệm xin gửi chút bù đắp ạ.'],
        parent=['Cảm ơn phụ huynh đã góp ý. Tôi xin lỗi và sẽ điều chỉnh cách làm trong lớp ạ.',
                'Dạ tôi xin lỗi vì {label} chưa chu đáo. Từ buổi sau tôi sẽ để ý con kỹ hơn ạ.',
                'Tôi nhận thiếu sót ạ. Tôi xin kèm con thêm để bù lại, mong phụ huynh thông cảm.']),
    'invite': dict(label='Mời quay lại', label_parent='Mời trao đổi', emoji='🚪', risk='safe', customer=[
        'Cảm ơn {who} đã ghé và góp ý. Mời {who} quay lại, bên mình sẽ phục vụ chu đáo hơn ạ.',
        'Lần sau {who} ghé cứ gọi tiệm một tiếng, tụi mình làm {item} thật kỹ cho {who} ạ.',
        'Tiệm mong được gặp lại {who} một ngày đẹp trời, để làm lại từ đầu cho đúng ý ạ ☀️'],
        parent=['Mời phụ huynh ghé lớp trao đổi trực tiếp, mình cùng giúp con nhé.',
                'Dạ phụ huynh rảnh buổi nào, mời anh chị ghé lớp ngồi dự một tiết cùng con ạ.',
                'Tôi mong được gặp phụ huynh sau giờ học, mình nói chuyện kỹ hơn về con nhé.']),
    'process': dict(label='Giải thích quy trình', emoji='⚙️', risk='safe', customer=[
        'Dạ tiệm xin kể quy trình: việc nào cũng được kiểm lại trước khi giao. Hôm đó {fact}, tiệm đang xem bước nào cần chặt hơn ạ.',
        'Bên mình làm theo thứ tự: nhận yêu cầu, chuẩn bị, kiểm tra rồi mới giao. Góp ý về {label} tiệm đưa vào bước kiểm tra ạ.',
        'Dạ giờ cao điểm tiệm làm lần lượt theo phiếu nên có lúc phải chờ. Tiệm đang sắp xếp lại để {label} tốt hơn ạ.'],
        parent=['Dạ lớp làm theo trình tự: điểm danh, giảng, cho con tự làm rồi nhận xét từng phiếu. Hôm đó {fact} ạ.',
                'Tôi xin chia sẻ cách lớp vận hành: con nào cũng có phiếu cuối tiết và nhận xét riêng. Góp ý về {label} tôi đưa vào kế hoạch tuần ạ.',
                'Dạ các con học theo nhóm nhỏ, tôi xoay vòng hỗ trợ từng nhóm. Tôi sẽ để ý thêm phần {label} ạ.']),
    'genz': dict(label='Kiểu Gen Z', emoji='✨', risk='safe', customer=[
        'Ui tiệm đọc mà “chấm hỏi” luôn á 🥲 Hứa lần sau {label} sẽ xịn xò, ghé lại cho tụi mình “gỡ” nha ✨',
        'Real quá {who} ơi, tụi mình nhận hết 🫶 Lần sau ghé là “10 điểm không có nhưng” luôn nha!',
        'Okela tiệm “note” lại liền 📝 {who} ghé lại tụi mình “bù đắp tinh thần” nha 😆'],
        parent=['Dạ tôi “note” lại liền ạ 📝 Tuần sau lớp mình sẽ “lên level” phần {label} nha phụ huynh ✨',
                'Real ạ, tôi nhận hết 🫶 Phụ huynh cứ góp ý thoải mái nha!']),
    'silent': dict(label='Im lặng lịch sự', emoji='🤐', risk='safe', customer=['Dạ, tiệm cảm ơn {who} ạ.', 'Tiệm đã đọc, cảm ơn {who} 🙏', 'Dạ, bên mình ghi nhận ạ.'],
                   parent=['Dạ, tôi đã nhận được ạ.', 'Cảm ơn phụ huynh ạ.']),
    'harsh': dict(label='Đáp trả gắt', emoji='💢', risk='bad', customer=[
        'Không thích thì đi chỗ khác, bên mình không tiếp loại khách như bạn.',
        'Khó tính vậy thì khỏi ghé, ở nhà tự làm cho vừa ý.',
        'Bạn biết gì mà chê, lo chuyện của bạn đi.',
        'Khách gì mà khó chiều, tiệm không cần khách như bạn.'],
        parent=['Phụ huynh không hài lòng thì chuyển lớp khác đi.',
                'Phụ huynh biết gì mà dạy tôi cách dạy, lo chuyện của mình đi ạ.',
                'Không thích thì cho con chuyển lớp khác, tôi không cần phụ huynh như vậy.']),
}
# Replies to a happy review (nothing to apologise for): same tones, other words.
TONES_POS = {
    'warm': dict(customer=['Đọc review của {who} mà cả tiệm vui cả buổi. Cảm ơn {who} nhiều lắm ạ 💛', 'Cảm ơn {who} đã thương tiệm. Hẹn {who} ghé lại sớm nha!'],
                 parent=['Cảm ơn phụ huynh nhiều ạ. Được gia đình tin tưởng là niềm vui lớn của lớp.', 'Dạ cảm ơn anh chị, con ngoan và chăm lắm ạ.']),
    'funny': dict(customer=['Tiệm đọc xong cười tới mang tai 😆 Lần sau làm {item} ngon gấp đôi cho xứng với lời khen này ạ!',
                            'Review này tiệm in ra đóng khung treo giữa quán luôn á 🖼️ Cảm ơn {who} nha!'],
                  parent=['Tin nhắn này tôi xin lưu vào “sổ vàng” của lớp ạ 😄 Cảm ơn phụ huynh!']),
    'sassy': dict(customer=['Dạ tiệm biết mà, nhưng được {who} công nhận vẫn vui ạ 😌', 'Tiệm quen được khen rồi, nhưng {who} khen thì tiệm vẫn đỏ mặt nha 😏'],
                  parent=['Dạ tôi cũng thấy con giỏi thật, chắc giống phụ huynh ạ 😌']),
    'facts': dict(customer=['Dạ theo phiếu hôm đó: {fact}. Cảm ơn {who} đã để ý kỹ vậy ạ.'],
                  parent=['Dạ sổ lớp ghi: {fact}. Cảm ơn phụ huynh đã theo sát con ạ.']),
    'sorry': dict(customer=['Tiệm vẫn thấy mình còn chậm một chút, xin lỗi và cảm ơn {who} đã thông cảm ạ. Lần sau tiệm gửi chút quà nhỏ nha.'],
                  parent=['Dạ nếu có gì chưa chu đáo, tôi xin lỗi và cảm ơn phụ huynh đã thông cảm ạ.']),
    'invite': dict(customer=['Cảm ơn {who} nhiều! Lần sau ghé nhớ gọi tên tiệm, tụi mình để dành chỗ đẹp cho {who} ạ.'],
                   parent=['Cảm ơn phụ huynh, buổi họp lớp tới mời anh chị ghé chơi với các con nhé.']),
    'process': dict(customer=['Dạ bí quyết của tiệm là làm từng bước, bước nào cũng kiểm lại. Cảm ơn {who} đã nhận ra ạ.'],
                    parent=['Dạ lớp làm từng bước nhỏ và nhận xét từng phiếu, may mà con theo kịp. Cảm ơn phụ huynh ạ.']),
    'genz': dict(customer=['Ui được khen xỉu luôn á 🫶 Ghé lại tụi mình tiếp nha {who} ơi ✨', 'Review xịn quá, tụi mình “u mê” luôn 😚'],
                 parent=['Dạ được phụ huynh khen là tôi “vui xỉu” luôn ạ 🫶']),
    'silent': dict(customer=['Dạ, cảm ơn {who} ạ.', 'Cảm ơn {who} 🙏'], parent=['Dạ, cảm ơn phụ huynh ạ.']),
    'harsh': dict(customer=['Khen thì khen, bạn biết gì mà chấm với chả điểm.', 'Không cần bạn khen, lo chuyện của bạn đi.'],
                  parent=['Phụ huynh biết gì mà khen, lo chuyện của mình đi ạ.']),
}
# Persona × tone outcome table, one letter per tone in TONE_ORDER:
#   W moved, full stars (to what the facts allow)   U up one      L laughs, up one
#   F moved + tells friends (new reviews)            K keeps       S keeps, "seen"
#   A argues back (thread reopens)                   J jabs back (argues)
#   D revises down                                   R a gamble (sass)
#   $ only moves if something real was given (an offer)
TABLE = {
    'sour': 'KJRUUKKJSD', 'bossy': 'UKRAWKAJKD', 'warm': 'WLRUWFULKD', 'picky': 'KKRWUKWJSD',
    'genz': 'ULRUUUKFSD', 'quiet': 'UKRUUUKKKD', 'parent_worried': 'UKRWUWWAAD', 'parent_strict': 'KARWKUWAAD',
    'parent_kind': 'WLRUWFULKD', 'knowitall': 'KJRAUKJJKD', 'rude': 'KJRAUKKJSD', 'entitled': 'KKRA$$AKKD',
    'drama': 'KJRA$KAJKD', 'troll': 'ULRKUKSLSD', 'parent_knowitall': 'KARAUUAAKD', 'parent_rude': 'KARAUKKASD',
}
# How often sass wins someone over (it backfires otherwise).
RISK_WIN = {'genz': .7, 'warm': .6, 'troll': .65, 'quiet': .4, 'sour': .45, 'bossy': .25, 'picky': .3, 'parent_kind': .45,
            'parent_worried': .15, 'parent_strict': .1, 'knowitall': .15, 'rude': .2, 'entitled': .1, 'drama': .1,
            'parent_knowitall': .15, 'parent_rude': .1}
SOFT = ('warm', 'genz', 'quiet', 'parent_kind', 'troll')
HARSHP = ('knowitall', 'rude', 'entitled', 'drama', 'parent_knowitall', 'parent_rude')
FAKES = ('wrong_shop', 'wrong_class', 'competitor', 'no_visit')
KEY = {'W': 'moved', 'U': 'accept', 'L': 'laugh', 'F': 'fans', 'K': 'keep', 'S': 'seen', 'A': 'argue', 'J': 'jab', 'D': 'down'}

# ------------------------------------------------------------ third parties
GUEST_NAMES = {
    'customer': [('Hàng xóm Tư', '🧓'), ('Minh Thư', '🌸'), ('Anh Khoa', '🧢'), ('Chú Sáu xe ôm', '🛵'), ('Lan Anh', '💄'),
                 ('Tuấn Béo', '🍔'), ('Cô Út bán rau', '🧺'), ('Bé Na', '🎀'), ('Hiếu Gym', '💪'), ('Chị Hạnh tạp hóa', '🛒')],
    'parent': [('Mẹ bé Na', '👩'), ('Bố bé Bin', '👨'), ('Bà nội bé Cốm', '👵'), ('Mẹ bé Sữa', '🤱'), ('Bố bé Tí', '🧔')]}
GUEST_TEXT = {
    'customer': dict(
        defend=['Tôi ghé đây hoài, chủ quán trả lời vậy là lịch sự lắm rồi á.', 'Công bằng mà nói, quán nói có lý đó bạn ơi.',
                'Mình ở gần đây, quán làm có tâm lắm, chắc hôm đó xui thôi.', 'Bình tĩnh nha bạn, quán giải thích rõ ràng vậy rồi mà 😅',
                'Hôm đó tôi cũng có mặt, quán làm đúng mà.'],
        cheer=['Chủ quán rep có tâm ghê, follow liền 👏', 'Đọc rep mà thương quán, mai mình ghé ủng hộ.', 'Rep mặn mà duyên, 10 điểm 😂',
               'Quán dễ thương vậy ai nỡ chê 🥹'],
        troll=['Hóng drama 🍿', 'Ủa rồi ai đúng ai sai, kể tiếp đi 👀', 'Lót dép ngồi hóng 🩴', 'Bình luận để xem tiếp phần hai 😆'],
        agree=['Mình cũng từng gặp y chang, không phải mỗi bạn đâu.', 'Chủ quán trả lời vậy là không được rồi.', 'Khách góp ý thì nghe thôi, gắt chi vậy quán.'],
        fake=['Ủa bạn ơi, tiệm này đâu có làm món đó 😅', 'Tài khoản này mới lập mà ta 🤔', 'Hình như bạn đánh giá nhầm chỗ rồi á.',
              'Mình ghé tuần rồi thấy khác hẳn nha, bạn xem lại thử.']),
    'parent': dict(
        defend=['Tôi thấy cô/thầy giải thích vậy là rõ rồi ạ.', 'Con tôi học lớp này cũng tiến bộ lắm, phụ huynh bình tĩnh nhé.',
                'Mình cứ trao đổi nhẹ nhàng thôi, cô/thầy tận tâm lắm.'],
        cheer=['Cảm ơn cô/thầy, đọc mà thấy yên tâm cho cả lớp.', 'Cô/thầy trả lời chu đáo quá ạ 👏'],
        troll=['Nhóm lớp hôm nay sôi nổi ghê 😅', 'Tôi chỉ vào xem bài tập về nhà thôi mà 🙈'],
        agree=['Tôi cũng lo chuyện này giống phụ huynh kia.', 'Giáo viên trả lời phụ huynh vậy là không nên ạ.'],
        fake=['Chị ơi hình như chị nhắn nhầm nhóm lớp rồi ạ.', 'Lớp mình đâu có chuyện đó ạ, chắc nghe nhầm.'])}
GUEST_SIDE = {'defend': 'fan', 'cheer': 'fan', 'fake': 'fan', 'troll': 'troll', 'agree': 'other'}
FAN_TEXT = {
    'customer': ['Được {author} rủ ghé thử, {item} ổn thật nha 👍', 'Nghe {author} khen quá trời nên ghé, không thất vọng.',
                 'Bạn thân {author} dắt tới, giờ thành khách quen luôn 😆', 'Thấy {author} khoe trên mạng nên ghé, xịn thật ✨'],
    'parent': ['Nghe {author} kể trong nhóm lớp, tôi cũng muốn cảm ơn cô/thầy.', 'Tôi đọc tin nhắn của {author}, đúng là cô/thầy rất tận tâm ạ.']}
GUEST_RATE = 0.35
GUESTS_PER_POST = 2
GUESTS_PER_DAY = 4
FANS_PER_DAY = 3


# ------------------------------------------------------------------ helpers
class _Blank(dict):
    def __missing__(self, key):
        return ''


def fill(text: str, **kw) -> str:
    return re.sub(r'\s{2,}', ' ', text.format_map(_Blank(kw))).strip()


def owner_call(s: dict, parent: bool = False) -> str:
    """How a reviewer calls the player: "anh chủ"/"chị chủ" or neutral."""
    g = ((s or {}).get('journey') or {}).get('gender') if isinstance((s or {}).get('journey'), dict) else None
    if parent:
        return {'male': 'thầy', 'female': 'cô'}.get(g, 'cô/thầy')
    return {'male': 'anh chủ', 'female': 'chị chủ'}.get(g, 'chủ quán')


def gender(s: dict):
    j = (s or {}).get('journey')
    g = j.get('gender') if isinstance(j, dict) else None
    return g if g in ('male', 'female') else None


def topic(t: dict) -> str:
    """A short name for what was served, taken from the job itself."""
    career = t.get('career', '')
    needs = t.get('needs') if isinstance(t.get('needs'), dict) else {}
    if career == 'milk_tea' and needs.get('base') in BASE_NAME:
        return 'ly ' + BASE_NAME[needs['base']]
    title = re.sub(r'^[^\w“"]+', '', str(t.get('title') or '')).strip()
    if '·' in title:
        title = title.split('·')[0].strip()
    if not title or ':' in title or '→' in title or len(title) > 48:
        return NOUN.get(career, 'dịch vụ')
    return '“' + title + '”'


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text and text[0] != '“' else text


def _lower(label: str) -> str:
    return label[:1].lower() + label[1:] if label else label


def _pick(rows, seed, k=0):
    return rows[(seed + k * 7919) % len(rows)]


def install(ns: dict) -> None:
    """Merge the extra voices and small tables into feedback.py's globals."""
    voice = ns['VOICE']
    for persona, extra in MORE_VOICE.items():
        v = voice[persona]
        for key, rows in extra.items():
            if key == 'open':
                for star, lines in rows.items():
                    v['open'][star] = v['open'][star] + [x for x in lines if x not in v['open'][star]]
            else:
                v[key] = list(v.get(key, [])) + [x for x in rows if x not in v.get(key, [])]
    ns['OFFERS'].setdefault('drink', 6)
    ns['TWISTS'].setdefault('fan', dict(group='any', persona=None, stranger=True, reportable=False, clues=[]))
    ns['TWIST_LABEL'].setdefault('fan', 'Bạn bè rủ tới')
    ns['TWIST_AI'].setdefault('fan', 'Bạn ghé vì một người bạn rủ, bạn thấy hài lòng và dễ tính.')
    ns['PILE_NOTE'].setdefault('sass', 'cà khịa khách trên mạng')
    ns['PILE_CLUE'].setdefault('sass', 'Kéo tới từ câu cà khịa của bạn')


# ------------------------------------------------------------ first review
def decorate(s: dict, c: dict, t: dict, persona: str, group: str, stars: int, text: str, seed: int, item: str) -> str:
    """Add an item line and a day-aware closer to a plain scripted review."""
    from .feedback import VOICE, _roll
    v = VOICE[persona]
    parts = [text]
    pos = stars >= 4
    rows = v.get('item_pos' if pos else 'item_neg') or []
    if rows and _roll('item', t['id'], c['day']) < .55:
        parts.append(_cap(fill(_pick(rows, seed, 3), item=item)))
    if _roll('close', t['id'], c['day']) < .4:
        mode = ((c.get('life') or {}).get('mode')) if isinstance(c.get('life'), dict) else None
        day = c.get('day', 1)
        stage = mode if mode in ('festival', 'calm') and seed % 2 else 'early' if day <= 3 else 'late' if day >= 8 else None
        if stage:
            lines = CLOSE['parent' if group == 'parent' else 'customer'][stage + ('_pos' if pos else '_neg')]
            parts.append(fill(_pick(lines, seed, 5), owner=owner_call(s, group == 'parent')))
    return ' '.join(parts)[:600]


def style_rate(day: int) -> float:
    return 0.0 if day <= 1 else 0.25 if day == 2 else 0.32


def style_review(s: dict, c: dict, t: dict, persona: str, group: str, fair: int, criteria: list, seed: int, item: str):
    """Maybe give a plain review a style. Returns (style, stars, text) or None."""
    from .feedback import _roll, _hash, DOMAIN, HARSH
    if _roll('style', t['id'], c['day']) >= style_rate(c.get('day', 1)):
        return None
    worst = min(criteria, key=lambda x: x['score'])
    ok = worst['score'] >= 4 and fair >= 4
    served = int((c.get('metrics') or {}).get('served:' + str(t.get('npc')), 0))
    harsh = persona in HARSH
    if group == 'parent':
        opts = [('p_short', 2), ('p_emoji', 1), ('p_story', 3), ('p_long', 1)] if ok else [('p_long', 3), ('p_short', 1)]
    elif ok:
        opts = [('short', 3), ('emoji', 2), ('teencode', 4 if persona in ('genz', 'troll') else 1), ('rant', 1)]
        if not harsh:
            opts += [('lifestory', 2)] + ([('handsome', 1)] if c.get('day', 1) >= 2 else [])
        if served >= 3:
            opts.append(('regular', 3))
    else:
        opts = [('teencode', 3 if persona in ('genz', 'troll') else 1), ('rant', 2)] + ([('sarcastic', 2)] if fair <= 3 else [])
        if served >= 3 and not harsh:
            opts.append(('regular', 2))
    total = sum(w for _, w in opts)
    x = _hash('style-kind', t['id'], c['day']) % total
    style = opts[-1][0]
    for k, w in opts:
        if x < w:
            style = k
            break
        x -= w
    label, note = _lower(worst['label']), worst['note']
    best = max(criteria, key=lambda x: x['score'])
    owner = owner_call(s, group == 'parent')
    emo = DOMAIN_EMOJI.get(DOMAIN.get(t.get('career'), ''), '✨')
    stars = fair
    if style == 'short':
        text = _pick(SHORT['pos'], seed)
    elif style == 'emoji':
        text = fill(_pick(EMOJI['pos'], seed), e=emo)
    elif style == 'teencode':
        text = fill(_pick(TEEN['pos' if ok else 'mid' if fair >= 3 and seed % 2 else 'neg'], seed), item=item, note=note)
    elif style in ('rant', 'p_long'):
        R = P_RANT if style == 'p_long' else RANT
        body = fill(_pick(R['pos'], seed, 1), label=_lower(best['label']), note=best['note']) if ok else fill(_pick(R['neg'], seed, 1), label=label, note=note)
        text = ' '.join([_pick(R['intro'], seed), body, _pick(R['tangent'], seed, 2), _pick(R['end_pos' if ok else 'end_neg'], seed, 3)])
    elif style == 'lifestory':
        stars = 5
        text = fill(_pick(LIFESTORY, seed), owner=owner, item=item)
    elif style == 'p_story':
        stars = 5
        text = _pick(P_STORY, seed)
    elif style == 'regular':
        text = fill(_pick(REGULAR['pos' if ok else 'neg'], seed), n=served + 1, owner=owner, item=item, note=note)
    elif style == 'handsome':
        stars = 5
        text = fill(_pick(HANDSOME[gender(s)], seed), item=item)
    elif style == 'sarcastic':
        rows = SARCASTIC.get(worst['key']) or SARCASTIC['']
        text = fill(_pick(rows, seed), note=note, label=label)
    elif style == 'p_short':
        text = fill(_pick(P_SHORT['pos' if ok else 'neg'], seed), note=note)
    else:  # p_emoji
        text = _pick(P_EMOJI, seed)
    return style, stars, text[:600]


# -------------------------------------------------------------- reply tones
def _facts_ok(fb: dict, kind) -> bool:
    worst = min(fb['criteria'], key=lambda x: x['score'])
    return bool(fb.get('unfair')) or kind in ('flip_low', 'rumor', 'offtopic', 'offtopic_p') or kind in FAKES or worst['score'] >= 4


def outcome_code(fb: dict, persona: str, tone: str, stars: int, offer: str, seed: int) -> tuple[str, str | None]:
    """(code, text key override) for this tone, persona and kind of review."""
    from .feedback import _kind, PERSONAS
    kind = _kind(fb)
    style = fb.get('style')
    if tone == 'harsh':
        return 'D', None
    if kind == 'fan':
        return 'K', 'thanks'
    if kind == 'flip_low':
        return ('K', 'keep') if tone == 'silent' else ('W', 'flip_fix')
    if kind == 'flip_high' or style == 'handsome':
        return 'K', ('flip_keep' if kind == 'flip_high' else None)
    if kind in FAKES:
        return 'K', kind
    if kind in ('offtopic', 'offtopic_p', 'pile_on'):
        soft = 'pile_on_soft' if kind == 'pile_on' else 'offtopic_soft'
        if tone in ('warm', 'sorry', 'funny', 'invite') and seed % 2 == 0:
            return 'U', soft
        return 'K', 'pile_on' if kind == 'pile_on' else 'offtopic'
    offered = offer != 'none'
    if kind in ('bocphot', 'demand') or persona in ('entitled', 'drama'):
        if offered and (offer in ('gift', 'refund') or tone in ('sorry', 'warm')):
            return 'W', 'accept'
        if tone in ('facts', 'process'):
            return 'A', None
        if tone == 'sassy':
            return 'R', None
        return ('S' if tone == 'silent' else 'K'), None
    code = TABLE[persona][TONE_ORDER.index(tone)]
    fact_ok = _facts_ok(fb, kind)
    if fb.get('unfair') or kind == 'rumor':
        # An off-topic gripe ("con mèo nằm trên quầy") is dropped, not "misremembered".
        # An unrecorded aspect ("nhà vệ sinh bí") settles the same way, with its own words.
        aspect = bool((fb.get('unfair') or {}).get('aspect'))
        gripe = bool((fb.get('unfair') or {}).get('gripe')) or aspect
        root = 'aspect_soft' if aspect else 'gripe_soft'
        soft = (root + '_parent' if PERSONAS[persona]['group'] == 'parent' else root) if gripe else 'sorry'
        if tone in ('facts', 'process'):
            return 'W', soft
        if tone in ('warm', 'sorry', 'invite', 'genz', 'funny') and (persona in SOFT + ('parent_worried',) or (gripe and persona not in HARSHP)):
            return 'W', soft
    elif tone in ('facts', 'process') and not fact_ok:
        # The records show a real fault: "facts" read as denial.
        code = 'D' if persona in HARSHP else ('K' if persona in SOFT and tone == 'process' else 'A')
    if code == '$':
        code = 'W' if offered else 'K'
    elif tone == 'sorry' and offered and code in ('U', 'K'):
        code = 'W' if code == 'U' else 'U'
    return code, None


def tone_decision(s: dict, c: dict, post: dict, tone: str, offer: str) -> dict:
    from .feedback import VOICE, TWIST_REPLY, PERSONAS, _bounds, _hash
    fb = post['feedback']
    persona = fb['persona']
    stars = post['stars']
    low, high = _bounds(fb, stars)
    seed = _hash('tone', post['id'], fb['rounds'], tone)
    code, key = outcome_code(fb, persona, tone, stars, offer, seed)
    extra = {}
    if code == 'R':
        win = _hash('risk', post['id'], fb['rounds']) % 1000 / 1000 < RISK_WIN.get(persona, .3)
        code = 'F' if win else 'D'
        extra['sass'] = 'won' if win else 'lost'
    worst = min(fb['criteria'], key=lambda x: x['score'])
    note = fb['unfair']['claim'] if fb.get('unfair') else worst['note']
    parent = PERSONAS[persona]['group'] == 'parent'
    if code in ('W', 'F'):
        new, decision = high, 'revise_up'
    elif code in ('U', 'L'):
        new, decision = min(high, stars + 1), 'revise_up'
    elif code == 'D':
        new, decision = max(low, stars - 1), 'revise_down'
    elif code in ('A', 'J'):
        new, decision = stars, 'argue'
    else:
        new, decision = stars, 'keep'
    if decision == 'revise_up' and new <= stars:
        new, decision, key, code = stars, 'keep', 'thanks', 'K'
    if decision == 'revise_down' and new >= stars:
        new, decision = stars, 'keep'
    v = VOICE[persona]
    group = {'revise_up': 'up', 'revise_down': 'down', 'argue': 'argue', 'keep': 'keep'}[decision]
    style_rows = (STYLE_REACT.get(fb.get('style')) or {}).get(group)
    if key == 'flip_fix':
        rows = TWIST_REPLY['flip_fix_parent' if parent else 'flip_fix']
    elif key in TWIST_REPLY:
        rows = TWIST_REPLY[key]
    elif style_rows and not key:
        rows = style_rows
    elif key:
        rows = v.get(key) or v['keep']
    else:
        rows = v.get(KEY[code]) or v['keep']
    if code == 'D' and tone != 'harsh' and extra.get('sass') == 'lost':
        rows = v.get('jab') or v['down']
    text = fill(_pick(rows, seed), note=note, owner=owner_call(s, parent), item=fb.get('item') or 'lần này')
    out = dict(decision=decision, stars=new, text=text, tone=tone)
    if code == 'F' and decision == 'revise_up':
        out['fans'] = True
    out.update(extra)
    return out


def tone_choices(post: dict, career: str | None = None) -> list[dict]:
    """Ready-made replies for the open round: one text per tone, varied per review and round.
    The pagoda answers in its own words (pagoda_voice.py): same tones, other labels and texts."""
    from .feedback import PERSONAS, _hash
    from . import pagoda_voice as pv
    fb = post['feedback']
    parent = PERSONAS[fb['persona']]['group'] == 'parent'
    pagoda = pv.on(career)
    worst = min(fb['criteria'], key=lambda x: x['score'])
    fact = fb['unfair']['truth'] if fb.get('unfair') else worst['note']
    who = pv.address(post, fb['persona']) if pagoda else 'phụ huynh' if parent else 'bạn'
    item = fb.get('item') or '“' + str(fb.get('title') or 'lần này') + '”'
    happy = (post.get('stars') or 0) >= 4 and worst['score'] >= 4 and not fb.get('unfair')
    label = pv.topic(fb['unfair'] if fb.get('unfair') else worst) if pagoda else worst['label']
    # Every public view of an open review builds these: the same inputs give the same replies.
    key = (post['id'], fb['rounds'], parent, happy, label, fact, item, who, pagoda)
    if type(fb['rounds']) is not int or not all(type(x) is str for x in (post['id'], label, fact, item)):
        key = None  # only plain inputs (1 == True == 1.0 would share a memo row, not a text)
    texts = _TONES_MEMO.get(key) if key is not None else None
    if texts is None:
        texts = (pv.tone_texts(post['id'], fb['rounds'], happy, who, label, fact, _hash) if pagoda
                 else _tone_texts(post['id'], fb['rounds'], parent, happy, who, label, fact, item, _hash))
        if key is not None:
            _TONES_MEMO.put(key, texts, size_of(key) + size_of(texts))
    return [dict(id=tid, label=pv.LABEL[tid] if pagoda else spec.get('label_parent', spec['label']) if parent else spec['label'],
                 emoji=spec['emoji'], risk=spec['risk'], text=text) for tid, text in zip(TONE_ORDER, texts) for spec in (TONES[tid],)]


_TONES_MEMO = Memo(entries=4096, budget=8 << 20)  # per worker: the reply texts of at most 4096 open reviews, about 8 MB


def _tone_texts(post_id, rounds, parent, happy, who, label, fact, item, _hash) -> tuple:
    """One reply text per tone (TONE_ORDER)."""
    out = []
    for tid in TONE_ORDER:
        rows = (TONES_POS[tid] if happy else TONES[tid])['parent' if parent else 'customer']
        out.append(_cap(fill(_pick(rows, _hash('tpl', post_id, rounds, tid)), who=who, label=_lower(label), fact=fact, item=item)))
    return tuple(out)


def tone_text_ok(tone) -> bool:
    return tone == 'free' or tone in TONES


# ------------------------------------------------------------ after resolve
def _career_of(s: dict, c: dict) -> str:
    return next((k for k, v in (s.get('careers') or {}).items() if v is c), '')


def _guests_today(c: dict) -> int:
    return sum(1 for p in c['feed'] for x in ((p.get('feedback') or {}).get('thread') or []) if x.get('role') == 'guest' and x.get('day') == c['day'])


def _fans_today(c: dict) -> int:
    return sum(1 for p in c['feed'] if ((p.get('feedback') or {}).get('twist') or {}).get('kind') == 'fan' and p.get('day') == c['day'])


def add_guest(s: dict, c: dict, post: dict, situation: str, seed: int, career: str | None = None) -> dict | None:
    from .feedback import PERSONAS, teacher_title
    from . import pagoda_voice as pv
    fb = post['feedback']
    thread = fb['thread']
    if len(thread) >= 8 or sum(1 for x in thread if x.get('role') == 'guest') >= GUESTS_PER_POST or _guests_today(c) >= GUESTS_PER_DAY:
        return None
    grp = 'parent' if PERSONAS[fb['persona']]['group'] == 'parent' else 'customer'
    names, lines = (pv.GUEST_NAMES, pv.GUEST_TEXT) if pv.on(career) else (GUEST_NAMES[grp], GUEST_TEXT[grp])
    name, emoji = _pick(names, seed)
    text = teacher_title(s, _pick(lines[situation], seed // 3))
    row = dict(role='guest', name=name, emoji=emoji, side=GUEST_SIDE[situation], text=text, day=c['day'])
    # Bystanders comment on the owner's reply while the reviewer is still reading,
    # so the reviewer's own answer stays the last word of the round.
    at = len(thread) - 1 if thread and thread[-1].get('role') == 'customer' else len(thread)
    thread.insert(at, row)
    return row


def _fans(s: dict, c: dict, career: str, post: dict, n: int) -> int:
    from . import engine as e
    from .feedback import PERSONAS, teacher_title, _hash
    fb = post['feedback']
    parent = PERSONAS[fb['persona']]['group'] == 'parent'
    pool = [k for k in e.NPC_INDEX if k.startswith(career + '_npc_') and k != post['npc']] or [k for k in e.NPC_INDEX if k != post['npc']]
    from . import pagoda_voice as pv
    rows = pv.FAN_TEXT if pv.on(career) else FAN_TEXT['parent' if parent else 'customer']
    made = 0
    for i in range(max(0, min(n, FANS_PER_DAY - _fans_today(c)))):
        h = _hash('fan', post['id'], i)
        npc = pool[(h + i) % len(pool)]
        stars = 5 if h % 3 else 4
        text = teacher_title(s, fill(_pick(rows, h // 5), author=post.get('author') or 'bạn tôi', item=fb.get('item') or 'đồ ở đây'))
        p = e.add_feed(s, c, npc, text, post['id'], stars, 'review')
        persona = 'parent_kind' if parent else ('warm', 'genz', 'quiet')[h % 3]
        p['feedback'] = dict(persona=persona, criteria=[dict(key='overall', label='Tổng thể', score=stars, note='ghé theo lời bạn rủ')],
                             cap=5, fair=stars, stars_original=stars, unfair=None, thread=[], status='open', rounds=0, pending=None,
                             voice='scripted', task=fb.get('task', ''), title=fb.get('title', ''), value=0, stranger=True,
                             twist=dict(kind='fan', reportable=False), item=fb.get('item') or '')
        e.metric(c, 'reviews_fans')
        made += 1
    return made


def after_resolve(s: dict, c: dict, post: dict, pending: dict, decision: str) -> list[str]:
    """Friends, sass fallout and bystanders once the reviewer has answered."""
    from .feedback import _hash, _pile_on, _kind
    from . import pagoda_voice as pv
    fb = post['feedback']
    notes = []
    career = _career_of(s, c)
    if pending.get('fans') and decision == 'revise_up' and not fb.get('fans') and career:
        n = _fans(s, c, career, post, 1 + _hash('fans', post['id']) % 2)
        if n:
            fb['fans'] = True
            notes.append(pv.fill(pv.FANS_NOTE, author=post['author'], n=n) if pv.on(career)
                         else f'{post["author"]} rủ bạn bè ghé ủng hộ: thêm {n} đánh giá tốt.')
    if pending.get('sass') == 'lost' and decision != 'revise_up' and not fb.get('viral') and career:
        fb['viral'] = True
        n = _pile_on(s, c, career, post, 1, 'sass')
        notes.append(pv.fill(pv.SASS_LOST, n=n) if pv.on(career) else f'Câu cà khịa bị chụp màn hình: thêm {n} đánh giá 1★.')
    # Bystanders chime in now and then.
    if c.get('day', 1) >= 2:
        roll = _hash('guest', post['id'], fb['rounds']) % 1000 / 1000
        forced = pending.get('sass') is not None
        if forced or roll < GUEST_RATE:
            tone = pending.get('tone')
            if tone == 'harsh':
                situation = ('agree', 'troll')[_hash('gside', post['id']) % 2]
            elif _kind(fb) in FAKES:
                situation = 'fake'
            elif decision == 'revise_up' or pending.get('sass') == 'won':
                situation = 'cheer'
            elif decision in ('argue', 'revise_down'):
                situation = 'defend' if pending.get('sass') != 'lost' else ('agree', 'troll')[_hash('gside', post['id']) % 2]
            else:
                situation = 'cheer' if (post.get('stars') or 0) >= 4 and seed_side(post) else 'troll'
            add_guest(s, c, post, situation, _hash('gname', post['id'], fb['rounds']), career)
    return notes


def seed_side(post: dict) -> bool:
    from .feedback import _hash
    return _hash('cheer', post['id']) % 3 != 0


def validate_extra(fb: dict) -> None:
    from .engine import need, clean_text
    need(fb.get('style') is None or fb['style'] in STYLES, 'Kiểu đánh giá sai.')
    need(fb.get('item') is None or (isinstance(fb['item'], str) and len(fb['item']) <= 80), 'Tên món sai.')
    need(type(fb.get('fans', False)) is bool, 'Cờ đánh giá sai.')
    for row in fb.get('thread') or []:
        if row.get('role') == 'guest':
            clean_text(row.get('name'), 40)
            need(isinstance(row.get('emoji'), str) and len(row['emoji']) <= 8, 'Biểu tượng khách sai.')
            need(row.get('side') in ('fan', 'troll', 'other'), 'Người bình luận sai.')
        if row.get('role') == 'owner':
            need(row.get('tone', 'free') == 'free' or row.get('tone') in TONES, 'Giọng trả lời sai.')
