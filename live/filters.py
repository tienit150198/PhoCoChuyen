"""Chat text: cleaning, masking and duplicate detection (pure functions, no I/O).

Masked with `•••` (the message still goes out, the rest of it intact):
* phone and bank numbers: 9+ digits, or a Vietnamese number (0…, +84…), whatever the separators;
  money written with dot thousands (100.000.000) is left alone;
* links (http…, www…, name.com/.vn/…), e-mails, @handles, and contact ids after "zalo / fb / insta / tele…"
  ("add zalo minh123" → "add zalo •••"; "ib zalo nha" stays);
* heavy, direct profanity only. The owner's tone rule (30/09): GenZ slang and rude banter stay as written
  ("vl", "vcl", "đm", "cút mẹ mày đi"); only the explicit sexual words and slurs below are masked.
"""
from __future__ import annotations

import re
import unicodedata

MASK = '•••'

# Heavy words only (owner, 30/09). With their diacritics: without them most are everyday words (lon = can,
# cac = các, buoi = buổi), so they are left alone. A repeated letter ("lồnnn") still matches.
HEAVY = ('địt', 'đjt', 'đ1t', 'đụ', 'lồn', 'l0n', 'cặc', 'c4c', 'buồi', 'đĩ', 'fuck', 'fucking', 'fucker', 'motherfucker',
         'cunt', 'pussy', 'nigger', 'nigga', 'faggot')
HEAVY_PHRASES = ('dit me', 'dit con me', 'djt me', 'du ma', 'du me')

TLDS = ('com|net|org|vn|io|me|xyz|link|co|info|app|gg|tk|ly|to|site|online|shop|store|club|top|biz|asia|cc|tv|live|pro|'
        'fun|vip|one|ai|dev|page|blog|click|space|website|icu|win|bet|cam')
_URL = re.compile(r'(?:https?://|www\.)\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:' + TLDS + r')\b(?:/\S*)?', re.I)
_EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
_HANDLE = re.compile(r'(?<![\w@])@[A-Za-z0-9_.]{3,}')
_CONTACT = re.compile(r'(?<!\w)(zalo|zl|fb|facebook|face|insta|instagram|ig|tiktok|tt|tele|telegram|messenger|mess|skype|discord|'
                      r'snap|snapchat|kakao|wechat|viber|line|sđt|sdt)(\s*[:=\-]?\s*)([A-Za-z0-9_.#\-]{3,})', re.I)
_DIGITS = re.compile(r'\+?\d[\d \t.\-()]{6,}\d')
_MONEY = re.compile(r'\d{1,3}(?:\.\d{3})+')
_WORDS = re.compile('|'.join(r'(?<!\w)' + ''.join(re.escape(ch) + '+' for ch in w) + r'(?!\w)' for w in HEAVY)
                    + '|' + '|'.join(r'(?<!\w)' + re.escape(p).replace(r'\ ', r'\s+') + r'(?!\w)' for p in HEAVY_PHRASES), re.I)
_SPACES = re.compile(r'[ \t  -​  　]+')
_ZW = re.compile('[​-‏ -‮⁠-⁯﻿]')


def clean(text, limit: int, lines: int = 4) -> str | None:
    """NFC, no control or invisible characters, one space between words, at most `lines` lines, trimmed.
    None when it is not text or is empty or longer than `limit` characters."""
    if not isinstance(text, str) or len(text) > limit * 4:
        return None
    text = unicodedata.normalize('NFC', text)
    text = _ZW.sub('', text)
    text = ''.join(ch for ch in text if ch == '\n' or unicodedata.category(ch)[0] != 'C')
    out, marks = [], 0   # at most two combining marks in a row (no "zalgo" walls)
    for ch in text:
        if unicodedata.combining(ch):
            marks += 1
            if marks > 2:
                continue
        else:
            marks = 0
        out.append(ch)
    text = ''.join(out)
    rows = [_SPACES.sub(' ', r).strip() for r in text.split('\n')]
    rows = [r for i, r in enumerate(rows) if r or (i and rows[i - 1])]   # no runs of empty lines
    if len(rows) > lines:
        rows = rows[:lines - 1] + [' '.join(rows[lines - 1:])]
    text = '\n'.join(rows).strip()
    if not text or len(text) > limit:
        return None
    return text


def _phone(m: re.Match) -> str:
    run = m.group(0)
    digits = re.sub(r'\D', '', run)
    if len(digits) < 9:
        return run
    s = run.strip()
    if not s.startswith(('0', '+84', '84')) and _MONEY.fullmatch(s):
        return run    # 100.000.000 xu: money, not a phone
    return MASK


def _contact(m: re.Match) -> str:
    key, sep, token = m.group(1), m.group(2), m.group(3)
    if key.lower() in ('tt', 'line', 'face', 'mess') and not re.search(r'\d', token):
        return m.group(0)   # "line dài", "mess up": a contact id after these needs digits
    if re.search(r'[0-9_.#]', token) or len(token) >= 6:
        return key + sep + MASK
    return m.group(0)


def _mention(known):
    """@Tên of a player the chat knows stays (chat C#20991: "muốn @tag"); any other @handle is masked."""
    def sub(m: re.Match) -> str:
        return m.group(0) if known and m.group(0)[1:].rstrip('.').casefold() in known else MASK
    return sub


# 🛟 Safety (moderation C#18077–18120: an adult arranged to meet a 15-year-old at Hồ Tây; handles posted on Cả phố).
# A message with one of these cues gets the SENDER a one-time, friendly notice (public/js/v4/chat.js); nothing is
# blocked or reported by it. Matched on the folded text (no tone marks, đ → d, lower case), whole words.
SAFETY_CUES = (
    r'hen gap', r'gap (nhau|mat|truc tiep|ngoai doi|rieng)', r'ngoai doi', r'di choi (rieng|ngoai)', r'hen ho ngoai',
    r'(cho|don|ruoc) (em|anh|chi|minh|tao|toi|tui|ban|cau|e|a|c|b|may|nhau) (di|ve|o)', r'qua nha', r've nha (em|anh|minh|tao|toi|ban)',
    r'nha (\w+ )?o (dau|quan|phuong|duong|ngo|hem|gan|ha noi|hn|sai gon|sg|hcm|tp|thanh pho|da nang)',
    r'(ban|em|anh|chi|cau|may|ong|ba|b|e|a|c) (o|song o|hoc o) (dau|quan nao|tinh nao|tp nao)', r'dia chi', r'so dien thoai', r'sdt', r'so dt',
    r'zalo', r'zl', r'facebook', r'fb', r'insta(gram)?', r'ig', r'tik ?tok', r'tele(gram)?', r'messenger', r'mess', r'snap(chat)?',
    r'(may|bao nhieu) tuoi', r'hoc (truong|lop) (nao|may)', r'ib (rieng|zalo|fb)', r'ket ban (zalo|fb|face)',
)
_SAFETY = re.compile(r'(?<!\w)(?:' + '|'.join(SAFETY_CUES) + r')(?!\w)')
_HANDLE_OR_PHONE = re.compile(r'(?<![\w@])@[A-Za-z0-9_.]{3,}|(?:\+?84|0)\d{8,10}\b')


def fold(text: str) -> str:
    """Lower case, no tone marks, đ → d, one space between words."""
    t = unicodedata.normalize('NFD', (text or '').lower()).replace('đ', 'd')
    t = ''.join(ch for ch in t if unicodedata.category(ch) != 'Mn')
    return re.sub(r'\s+', ' ', t).strip()


def safety_cue(text: str) -> bool:
    """True when a message talks about meeting up, where someone lives, or contact details (see SAFETY_CUES)."""
    if not isinstance(text, str) or not text:
        return False
    if _HANDLE_OR_PHONE.search(re.sub(r'[ .\-]', '', text) if re.search(r'\d[ .\-]\d', text) else text):
        return True
    return bool(_SAFETY.search(fold(text)))


def mention_keys(names) -> set:
    """What may follow @ for these display names: the whole name without spaces, and its first word (casefold)."""
    out = set()
    for n in names:
        if not isinstance(n, str) or not n.strip():
            continue
        words = n.casefold().split()
        out.add(''.join(words))
        if len(words[0]) >= 3:
            out.add(words[0])
    return out


def mask(text: str, known: set | None = None) -> str:
    text = _EMAIL.sub(MASK, text)
    text = _URL.sub(MASK, text)
    text = _HANDLE.sub(_mention(known), text)
    text = _CONTACT.sub(_contact, text)
    text = _DIGITS.sub(_phone, text)
    text = _WORDS.sub(MASK, text)
    return text


def fingerprint(text: str) -> str:
    """For "the same message again": case, spaces and punctuation do not count."""
    t = unicodedata.normalize('NFC', text).casefold()
    return re.sub(r'[\W_]+', '', t)
