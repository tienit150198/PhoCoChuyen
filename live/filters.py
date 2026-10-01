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


def mask(text: str) -> str:
    text = _EMAIL.sub(MASK, text)
    text = _URL.sub(MASK, text)
    text = _HANDLE.sub(MASK, text)
    text = _CONTACT.sub(_contact, text)
    text = _DIGITS.sub(_phone, text)
    text = _WORDS.sub(MASK, text)
    return text


def fingerprint(text: str) -> str:
    """For "the same message again": case, spaces and punctuation do not count."""
    t = unicodedata.normalize('NFC', text).casefold()
    return re.sub(r'[\W_]+', '', t)
