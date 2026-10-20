"""🧭 Coach of a feature outside the workplaces (see game/coach/__init__.py): 💛 Thân thiết với NPC (game/goodwill.py).

Not a workplace walk: public/js/v4/closeness.js shows these steps as a small card on top of 👥 Người quen the first
time the sheet opens with the goodwill perks on (remembered as the note id NOTE in settings.notesSeen, like the coach's
own marks), "Tiếp" between steps and "Xong" at the end. Words only (x=True); the same text rules as the workplaces."""
from . import S

NOTE = 'gw1'

FEATURES: dict[str, list[dict]] = {
    'goodwill': [
        S('💛', 'Ai thân với bạn sẽ giúp bạn: khách ruột trả thêm, hàng xóm bớt giá, giúp mỗi tuần.', x=True),
        S('💬', 'Mỗi ngày hỏi thăm, tặng đúng món họ thích là thân thêm.', x=True),
        S('📝', 'Có người nhờ việc nhỏ thì giúp: thân nhanh hơn, lâu dần nghe chuyện riêng.', x=True),
        S('🔒', 'Dòng 🔒 ??? là điều bí mật: thân tới đó mới biết.', x=True),
        S('🍃', 'Lâu không gặp thì nhạt dần. Ghé thăm đều tay nhé!', x=True),
    ],
}

EN: dict[str, str] = {
    'Ai thân với bạn sẽ giúp bạn: khách ruột trả thêm, hàng xóm bớt giá, giúp mỗi tuần.':
        'People close to you help you: regulars pay a bit more, neighbours give discounts and weekly favours.',
    'Mỗi ngày hỏi thăm, tặng đúng món họ thích là thân thêm.': 'Say hello every day and give what they like to grow closer.',
    'Có người nhờ việc nhỏ thì giúp: thân nhanh hơn, lâu dần nghe chuyện riêng.':
        'Help with small requests: you grow closer faster, and in time you hear their secrets.',
    'Dòng 🔒 ??? là điều bí mật: thân tới đó mới biết.': 'A 🔒 ??? line is a secret: get that close to find out.',
    'Lâu không gặp thì nhạt dần. Ghé thăm đều tay nhé!': 'Friendships fade if you stay away too long. Visit often!',
    'Thân thiết với mọi người': 'Getting close to people',
}
