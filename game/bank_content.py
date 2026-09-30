"""🏦 Ngân hàng Phố: the words of the neighbourhood bank (game/bank.py holds the rules).

Every line is a whole Vietnamese sentence. Collector calls stay polite: a little tense,
never threatening, never shaming, never mentioning family or neighbours."""
from __future__ import annotations

BANK_NAME = 'Ngân hàng Phố'
BANK_SHORT = 'NH Phố'

# Credit score bands (300–850).
BANDS = (
    (800, 'Rất tốt', 'great'),
    (740, 'Tốt', 'good'),
    (670, 'Khá', 'fair'),
    (580, 'Trung bình', 'mid'),
    (300, 'Cần cải thiện', 'poor'),
)

SCORE_TIPS = [
    'Trả thẻ đúng hạn, tốt nhất là trả hết dư nợ sao kê: điểm lên đều mỗi kỳ.',
    'Giữ dư nợ thẻ dưới 30% hạn mức khi chốt sao kê.',
    'Có thu nhập đều đặn (lương, tiền lời rút về ví) giúp điểm tăng mỗi tuần.',
    'Tài khoản càng lâu năm, điểm càng vững.',
    'Đừng nộp nhiều hồ sơ vay, mở thẻ dồn dập: mỗi lần ngân hàng tra cứu là điểm giảm một chút.',
    'Trễ hạn một kỳ là mất nhiều điểm. Bật tự động trả tối thiểu nếu hay quên.',
]

SCORE_WHY = {
    'open': 'Mở tài khoản: hồ sơ tín dụng mới',
    'inquiry': 'Ngân hàng tra cứu hồ sơ tín dụng',
    'inquiry_many': 'Nhiều hồ sơ tín dụng trong thời gian ngắn',
    'card_full': 'Trả hết dư nợ sao kê đúng hạn',
    'card_min': 'Trả tối thiểu thẻ đúng hạn',
    'card_late': 'Trễ hạn thanh toán thẻ',
    'loan_ok': 'Trả góp khoản vay đúng hạn',
    'loan_late': 'Trễ hạn trả góp khoản vay',
    'loan_done': 'Tất toán khoản vay',
    'income': 'Thu nhập đều đặn trong tuần',
    'age': 'Tài khoản thêm một tuần tuổi',
    'util_low': 'Dư nợ thẻ thấp so với hạn mức',
    'util_mid': 'Dư nợ thẻ chiếm hơn 30% hạn mức',
    'util_high': 'Dư nợ thẻ chiếm hơn 70% hạn mức',
    'bad': 'Bị ghi nhận nợ xấu',
    'home_ok': 'Trả góp nhà đúng hạn',
    'home_late': 'Trễ hạn trả góp nhà',
    'home_done': 'Trả xong khoản vay mua nhà',
}

# Term (life days) -> name. 1 tháng = 5 ngày sống, 1 năm = 60 ngày sống (bank.MONTH_DAYS / YEAR_DAYS).
# 14 ngày is only for sổ opened before 0.9.5.
TERMS = {
    0: 'Không kỳ hạn',
    7: 'Kỳ hạn 7 ngày',
    14: 'Kỳ hạn 14 ngày',
    15: 'Kỳ hạn 3 tháng',
    30: 'Kỳ hạn 6 tháng',
    60: 'Kỳ hạn 12 tháng',
    120: 'Kỳ hạn 2 năm',
    180: 'Kỳ hạn 3 năm',
}

LOANS = {
    'personal': dict(name='Vay tiêu dùng tín chấp', emoji='💸',
                     desc='Không cần tài sản bảo đảm. Hạn mức theo thu nhập và điểm tín dụng. Tiền giải ngân vào tài khoản của bạn.'),
    'shop': dict(name='Vay mở rộng tiệm', emoji='🏪',
                 desc='Giải ngân thẳng vào quỹ một tiệm bạn làm chủ, như một khoản góp vốn. Lãi thấp hơn vay tiêu dùng.'),
}

ATM = {
    'own': 'Cây ATM Ngân hàng Phố',
    'other': 'Cây ATM khác ngân hàng',
}

AUTOPAY = {
    'off': 'Tự trả tay',
    'min': 'Tự động trả tối thiểu',
    'full': 'Tự động trả toàn bộ sao kê',
}

PAY_PREF = {
    'auto': 'Tự động: ví đủ thì trả tiền mặt, thiếu thì quẹt thẻ',
    'cash': 'Luôn trả tiền mặt',
    'card': 'Ưu tiên quẹt thẻ tín dụng',
    'joint': 'Ưu tiên thẻ chung vợ chồng (quỹ chung)',
}

# Reminder calls and messages. {name} = the player, {amount} = the sum due, {what} = the product, {days} = days overdue.
REMIND_SMS = [
    '{bank}: Khoản {what} đến hạn hôm nay chưa được thanh toán ({amount} xu). Quý khách vui lòng thanh toán sớm để tránh phát sinh phí.',
    '{bank}: Quý khách đang trễ hạn {what}, số tiền cần thanh toán {amount} xu. Vui lòng nộp tiền vào tài khoản để hệ thống tự trích.',
]
COLLECTOR_CALLS = [
    'Nhân viên thu hồi nợ gọi: “Chào {name}, em bên {bank}. Khoản {what} của mình đã trễ {days} ngày, còn {amount} xu. Mình sắp xếp thanh toán giúp em trong mấy ngày tới được không ạ?”',
    'Nhân viên thu hồi nợ gọi: “Dạ em gọi nhắc lại khoản {what} đang quá hạn {days} ngày, số tiền {amount} xu. Nếu đang khó khăn, mình trả trước một phần cũng được ạ.”',
    'Nhân viên thu hồi nợ gọi, giọng hơi gấp: “Khoản {what} đã quá hạn {days} ngày rồi ạ. Để lâu hơn là hồ sơ bị ghi nợ xấu, sau này vay rất khó. Mình cố gắng thanh toán sớm giúp em nha.”',
    'Nhân viên thu hồi nợ gọi: “Em chào {name}. Bên em chưa nhận được {amount} xu cho khoản {what}, quá hạn {days} ngày. Mình nộp vào tài khoản là hệ thống tự trích ngay ạ.”',
]
BAD_DEBT_SMS = ('{bank}: Hồ sơ của quý khách đã bị ghi nhận nợ xấu do trễ hạn nhiều lần. '
                'Các sản phẩm tín dụng mới tạm khóa tới Ngày {until}. Thẻ tín dụng tạm ngưng giao dịch.')
BAD_CLEAR_SMS = '{bank}: Hồ sơ tín dụng của quý khách đã hết ghi nhận nợ xấu. Cảm ơn quý khách đã thanh toán đầy đủ.'
STATEMENT_SMS = '{bank}: Sao kê thẻ •••• {no} kỳ này {amount} xu, tối thiểu {min} xu, hạn thanh toán Ngày {due}.'
MATURED_SMS = '{bank}: Sổ tiết kiệm {term} {amount} xu đã đáo hạn, tiền gốc và lãi {total} xu đã về tài khoản thanh toán.'
RENEWED_SMS = '{bank}: Sổ tiết kiệm {term} đã tái tục: nhập lãi {gain} xu vào gốc, sổ mới {total} xu, đáo hạn Ngày {due}.'
INSTALLMENT_SMS = '{bank}: Đã trích {amount} xu trả kỳ {k}/{n} khoản {what}. Cảm ơn quý khách.'

DECLINE = {
    'bad': 'Hồ sơ đang ghi nhận nợ xấu tới {until} nên ngân hàng chưa thể xét duyệt. Trả hết khoản quá hạn và chờ hết thời gian ghi nhận nhé.',
    'overdue': 'Bạn đang có khoản quá hạn. Thanh toán khoản đó trước rồi hãy nộp hồ sơ mới nhé.',
    'score': 'Điểm tín dụng chưa đủ để ngân hàng duyệt ({score}, cần từ {need}).',
    'income': 'Ngân hàng cần thấy thu nhập đều: ít nhất {days} ngày có lương hoặc tiền lời rút về ví trong {window} ngày gần nhất.',
    'many': 'Bạn đã nộp nhiều hồ sơ tín dụng trong {window} ngày gần đây. Nộp lại được {when}.',
    'dti': 'Tiền trả góp mỗi tuần sẽ vượt {pct}% thu nhập của bạn. Chọn số tiền nhỏ hơn hoặc kỳ hạn dài hơn nhé.',
}
