"""🏗️ Công trình của phố: the catalogue (game/town_projects.py). Ids are never renamed: rows, saves and titles keep them.

Owner 16/10: "bổ sung công trình của phố góp tiền và có bảng tài trợ, có mục tiêu nhé. Thời gian xây dựng là 2 ngày".
The richest players hold 13–48 million xu (top 1 ≈ 48 M, top 10 ≥ 13 M): the goals sit where that money is, so the
first one is within reach of a few of them together and the last one needs the whole top of the street.

Built in this order, one raising money at a time; each opens when the one before it is finished. `lot`: its plot on both
town maps (game/town_layout.json lot `tp_<id>`, the old town's place list public/js/v4/town-projects.js). `title`: the
top sponsor's own title (game/spend_content.py TOWN_TITLES).
"""
from __future__ import annotations

PROJECTS = (
    dict(id='cong_vien', emoji='🌳', name='Công viên ven sông', goal=20_000_000, title='t_ct_cong_vien',
         blurb='Bãi cỏ, lối đi bộ và ghế đá dọc bờ sông cho cả phố hóng mát.'),
    dict(id='rap_phim', emoji='🎬', name='Rạp chiếu phim', goal=30_000_000, title='t_ct_rap_phim',
         blurb='Ba phòng chiếu, ghế đôi và quầy bắp rang ngay giữa phố.'),
    dict(id='thu_vien', emoji='📚', name='Thư viện lớn', goal=30_000_000, title='t_ct_thu_vien',
         blurb='Hai tầng sách, góc đọc cho trẻ con và phòng tự học mở tới khuya.'),
    dict(id='san_van_dong', emoji='🏟️', name='Sân vận động', goal=50_000_000, title='t_ct_san_vd',
         blurb='Sân cỏ, đường chạy và khán đài cho các trận bóng của phố.'),
    dict(id='cau_ra_dao', emoji='🌉', name='Cầu ra đảo', goal=80_000_000, title='t_ct_cau_dao',
         blurb='Cây cầu dây văng nối phố với đảo, đèn sáng suốt đêm.'),
    dict(id='benh_vien', emoji='🏥', name='Bệnh viện phường', goal=100_000_000, title='t_ct_benh_vien',
         blurb='Phòng khám, phòng cấp cứu và khu nội trú ngay trong phường.'),
)
BUILD_SECS = 48 * 3600           # owner: "2 ngày" of real time from the day the goal is reached
MIN_GIFT = 1_000                 # xu, the smallest contribution
MAX_GIFT = 10_000_000            # xu, the largest at once: a wallet history row of every build stays within ±10,000,000
                                 # (journey.validate), so a whale gives in a few taps
PRESETS = (10_000, 100_000, 1_000_000, 10_000_000)
NEWS_FROM = 1_000_000            # a contribution from this amount gets a line on the street's ticker
TOP_TITLES = 3                   # 2nd–3rd: t_ct_vang (the 1st has the project's own title and this one too)
TOP_SILVER = 10                  # 4th–10th: t_ct_bac
GOLD, SILVER, BRICK = 't_ct_vang', 't_ct_bac', 't_ct_gach'   # every sponsor of a finished project: t_ct_gach
