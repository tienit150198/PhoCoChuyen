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
    dict(version="0.9.8", date="2026-09-30", items=(
        dict(emoji="🏰", text="Mua nhà: thêm biệt thự và 4 loại căn hộ (studio, 1 phòng ngủ, 2 phòng ngủ, penthouse).", go=dict(action="house")),
        dict(emoji="💰", text="Bấm vào tiền trên cùng để xem hết: ví, quỹ từng nơi làm, ngân hàng, nhà.", go=dict(action="money")),
        dict(emoji="📈", text="Giá nhà tăng 20%. Nhà đã mua giữ nguyên giá đã trả và khoản vay đang trả góp."),
        dict(emoji="🏦", text="Penthouse và biệt thự cần điểm tín dụng cao hơn mới vay được."),
        dict(emoji="🗂️", text="Nhà đang rao chia theo Phòng thuê, Căn hộ, Nhà phố, Biệt thự: ghi rõ góp mỗi tháng và còn thiếu bao nhiêu."),
        dict(emoji="💞", text="Vợ chồng bấm cùng lúc không còn báo “tab khác”; quỹ chung hiện đúng dấu tiền rút."),
    )),
    dict(version="0.9.7", date="2026-09-30", items=(
        dict(emoji="🛠️", text="Đã sửa lỗi “Dữ kiện gốc của nhiệm vụ không hợp lệ”: rút tiền, mở ngày mới và làm việc lại bình thường."),
        dict(emoji="👕", text="Đơn shop quần áo làm dở từ trước vẫn giữ nguyên, bạn làm tiếp được."),
        dict(emoji="🙏", text="Xin lỗi vì sự bất tiện. Cảm ơn mọi người đã báo lỗi!"),
    )),
    dict(version="0.9.6", date="2026-09-30", items=(
        dict(emoji="🧋", text="Trà sữa: phiếu order ghim trên đầu, làm xong phần nào tích phần đó, chỉ một nút bước tiếp."),
        dict(emoji="👕", text="Shop quần áo, sửa đồ, thú cưng: thẻ “Khách cần” ghim sẵn, món khách cần xếp lên trước."),
        dict(emoji="⚡", text="Game phản hồi nhanh hơn, nhất là giờ đông người."),
        dict(emoji="📚", text="Nhật ký, sổ tiền, bảng tin cũ vẫn còn đủ: bấm “Xem cũ hơn” để xem lại."),
    )),
    dict(version="0.9.5", date="2026-09-30", items=(
        dict(emoji="🏠", text="Mua nhà: trả trước 30%, còn lại vay trả góp. Có nhà là hết tiền phòng.", go=dict(action="house")),
        dict(emoji="💞", text="Vợ chồng góp quỹ chung mua nhà, rồi về ở chung."),
        dict(emoji="🐷", text="Tiết kiệm có kỳ hạn tới 3 năm, lãi theo năm, tới hạn tự gửi tiếp.", go=dict(action="bank")),
        dict(emoji="👗", text="Tủ đồ: đổi tóc, áo quần, giày, phụ kiện. Làm ở Tiệm Áo Chỉ Mây được giảm 20%.", go=dict(action="jrWardrobe")),
        dict(emoji="😊", text="Khách kiên nhẫn hơn một chút."),
        dict(emoji="🪙", text="Tiền đền nhẹ hơn."),
        dict(emoji="💰", text="Nhập hàng, mua sắm, gửi rút tiền: Ví và Quỹ tiệm luôn hiện ở góc trên, thiếu bao nhiêu ghi rõ."),
        dict(emoji="📉", text="Hàng giao thiếu: bấm “Khiếu nại phần thiếu” ngay trong Kho để được hoàn tiền."),
        dict(emoji="🔧", text="Sửa đồ, pet care, shop quần áo: lời dặn và đồ khách đưa kèm hiện ngay chỗ chọn."),
        dict(emoji="🗣️", text="Người trong phố có chính kiến hơn: khen có gai, chê có lý."),
        dict(emoji="🧾", text="Màn hình yên hơn: thông báo từng dòng, Đánh giá, Tổng kết ngày và Sổ tiệm gọn gàng."),
        dict(emoji="⚡", text="Máy chủ cập nhật không làm mất thao tác, nhẹ hơn khi đông người chơi."),
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
