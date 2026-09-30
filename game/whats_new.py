"""Có gì mới: the release notes players see in a centred card after an update
(public/js/v4/whatsnew.js), and again from Cài đặt → Cách chơi → "Có gì mới".

=====================================================================
EVERY RELEASE MUST ADD AN ENTRY AT THE TOP OF ENTRIES (newest first).
=====================================================================
- version: the release number ("0.9.2"), higher than the entry below it and at
  least game.__version__ (tests/test_whats_new.py fails otherwise);
- date: "YYYY-MM-DD", the day it goes live;
- items: 1 to MAX_ITEMS short bullets in plain player Vietnamese (no developer notes,
  no file names), each a dict(emoji=..., text=...). Whole Vietnamese literals:
  the English pack (scripts/i18n_extract.py) picks them up from this file.
  Optional go=dict(action=..., data={...}) adds a "Thử ngay" button that
  presses the game's own control with that data-action; it only shows when
  such a control exists on the page, so a route that is not built yet is
  simply left out.
Then run `python -m game.whats_new` to rewrite public/js/v4/whatsnew-data.js
(the copy the browser loads lazily, so the first load does not grow).

Players who already saw a version keep it in settings.whatsNewSeen (the save,
so it follows the account). It is a server-wide notice: a brand-new save starts at ""
too, so new players see the latest notes once they have named their character.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ENTRIES = (
    dict(version="0.9.4", date="2026-09-30", items=(
        dict(emoji="🛠️", text="Đã khắc phục sự cố giật, lag: game chạy mượt hơn nhiều."),
        dict(emoji="🏪", text="Chương 3 có thêm 3 nghề: Shop quần áo, Shop thú cưng (cá cảnh, thú nhỏ, góc nhận nuôi) và quán trà đá vỉa hè."),
        dict(emoji="💍", text="Kết hôn (cần tài khoản): mua nhẫn, cầu hôn bằng mã người chơi, đặt tiệc cưới, nhận tiền mừng. Cả phố cùng hay tin.", go=dict(action="marriage")),
        dict(emoji="💞", text="Vợ chồng có quỹ chung và thẻ chung: cùng góp tiền, cùng chi tiêu, ai gửi hay rút đều báo cho nhau."),
        dict(emoji="🏦", text="Ngân hàng Phố: gửi tiết kiệm, mở thẻ, vay tiền. Trả đúng hạn thì điểm tín dụng tăng.", go=dict(action="bank")),
        dict(emoji="👋", text="Kết bạn với người chơi khác. Người quen trong phố thân dần khi bạn hỏi han, tặng quà.", go=dict(action="friends")),
        dict(emoji="🎓", text="Trượt phỏng vấn? Thi chứng chỉ nhẹ nhàng (đúng 4/6 là đạt, có 💡 gợi ý) để dễ được nhận hơn, hoặc “Đi cửa sau”."),
        dict(emoji="🏆", text="Bảng xếp hạng: Top trải nghiệm (cả phố và từng nghề) và Top chứng chỉ.", go=dict(action="rank")),
        dict(emoji="🕰️", text="Đồng hồ trong ngày: trời sáng tối theo giờ, mỗi tiệm có giờ mở cửa và giờ đóng cửa riêng."),
        dict(emoji="💝", text="Làm tốt thì thỉnh thoảng được khách bo thêm, hên xui."),
        dict(emoji="💵", text="Khách có thể đưa thiếu tiền: đếm lại, nhắc khéo, cho nợ hay báo công an. Mỗi cách một kết cục khác nhau."),
        dict(emoji="⭐", text="Đánh giá đa dạng hơn: khách khen chê vị đồ uống, ống hút, nhà vệ sinh, thái độ nhân viên, cả cách ăn mặc."),
        dict(emoji="📘", text="Sách hướng dẫn đầy đủ: mua nhẫn, cầu hôn, đám cưới, thẻ chung, ngân hàng, chứng chỉ, từng nghề…", go=dict(action="help")),
        dict(emoji="🛒", text="Giờ cao điểm ở tạp hoá bán như quầy thường. Thối tiền sai ở đâu cũng bị khách phàn nàn."),
        dict(emoji="📱", text="Màn hình gọn hơn trên điện thoại, ít phải cuộn."),
        dict(emoji="💬", text="Thông báo hiện lâu hơn, đủ thời gian đọc."),
        dict(emoji="⚡", text="Vào game nhanh hơn, hàng nhập về nhanh hơn."),
    )),
)

MAX_ITEMS = 18
MAX_TEXT = 130
VERSION = re.compile(r"\d{1,3}(?:\.\d{1,3}){1,2}")
DATE = re.compile(r"20\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
ACTION = re.compile(r"[A-Za-z][A-Za-z0-9:_-]{0,31}")
DATA_JS = Path(__file__).resolve().parents[1] / "public" / "js" / "v4" / "whatsnew-data.js"


def parse(version: str) -> tuple[int, ...]:
    """"0.9.1" -> (0, 9, 1); "0.9" -> (0, 9, 0) so the two compare equal."""
    parts = tuple(int(x) for x in version.split("."))
    return parts + (0,) * (3 - len(parts))


def valid_seen(value) -> bool:
    """settings.whatsNewSeen: "" (nothing seen yet) or a release number. Only the shape is
    checked, not membership: a save must stay valid when a release is rolled back."""
    return isinstance(value, str) and (value == "" or bool(VERSION.fullmatch(value)))


def newer(a: str, b: str) -> str:
    """The later of two valid settings.whatsNewSeen values ("" is the earliest): a tab still
    running an older release can never lower what the player has already read."""
    if not a or not b:
        return a or b
    return b if parse(b) > parse(a) else a


def validate(entries=ENTRIES) -> None:
    """Raise ValueError when an entry is malformed or the list is not newest first."""
    if not entries:
        raise ValueError("whats_new: no entries")
    seen = set()
    for i, e in enumerate(entries):
        where = f"whats_new entry {i}"
        if not isinstance(e, dict) or set(e) != {"version", "date", "items"}:
            raise ValueError(f"{where}: needs exactly version, date, items")
        v, d, items = e["version"], e["date"], e["items"]
        if not isinstance(v, str) or not VERSION.fullmatch(v) or v in seen:
            raise ValueError(f"{where}: bad or repeated version {v!r}")
        seen.add(v)
        if not isinstance(d, str) or not DATE.fullmatch(d):
            raise ValueError(f"{where}: date must be YYYY-MM-DD")
        if i and not (parse(v) < parse(entries[i - 1]["version"]) and d <= entries[i - 1]["date"]):
            raise ValueError(f"{where}: entries must be newest first ({v} after {entries[i - 1]['version']})")
        if not isinstance(items, (list, tuple)) or not 1 <= len(items) <= MAX_ITEMS:
            raise ValueError(f"{where}: 1 to {MAX_ITEMS} items")
        for it in items:
            if not isinstance(it, dict) or not {"emoji", "text"} <= set(it) <= {"emoji", "text", "go"}:
                raise ValueError(f"{where}: an item needs emoji and text (go is optional)")
            if not isinstance(it["emoji"], str) or not 1 <= len(it["emoji"]) <= 8 or any(c.isalnum() for c in it["emoji"]):
                raise ValueError(f"{where}: emoji {it['emoji']!r}")
            t = it["text"]
            if not isinstance(t, str) or not 8 <= len(t) <= MAX_TEXT or t != t.strip() or "<" in t or "\n" in t:
                raise ValueError(f"{where}: text must be one plain line of 8-{MAX_TEXT} characters: {t!r}")
            if "go" in it:
                go = it["go"]
                if (not isinstance(go, dict) or not {"action"} <= set(go) <= {"action", "data"} or not ACTION.fullmatch(str(go["action"]))
                        or not isinstance(go.get("data", {}), dict)
                        or not all(isinstance(k, str) and re.fullmatch(r"[a-z][a-zA-Z0-9]{0,23}", k) and isinstance(x, str) for k, x in go.get("data", {}).items())):
                    raise ValueError(f"{where}: go must be dict(action=..., data={{str: str}})")


validate()
LATEST = ENTRIES[0]["version"]


def public() -> list[dict]:
    """JSON-ready copy for the browser."""
    return [dict(version=e["version"], date=e["date"], items=[dict(it) for it in e["items"]]) for e in ENTRIES]


def render_js() -> str:
    """public/js/v4/whatsnew-data.js: plain JSON after `export default`, one bullet per line."""
    dump = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    rows = []
    for e in public():
        items = ",\n".join("  " + dump(it) for it in e["items"])
        rows.append(f' {{"version":{dump(e["version"])},"date":{dump(e["date"])},"items":[\n{items}\n ]}}')
    body = "[\n" + ",\n".join(rows) + "\n]"
    return ("/* GENERATED by `python -m game.whats_new` from game/whats_new.py: edit that file, not this one.\n"
            " * Release notes for the \"Có gì mới\" card (whatsnew.js), newest first. Loaded only after the game is up. */\n"
            f"export default {body};\n")


if __name__ == "__main__":
    DATA_JS.write_text(render_js(), encoding="utf-8", newline="\n")
    print(f"wrote {DATA_JS.relative_to(DATA_JS.parents[3])} ({len(ENTRIES)} entries, latest {LATEST})")
