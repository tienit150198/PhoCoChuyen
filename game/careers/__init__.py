"""Plugin careers (v0.4).

Each module in this package describes one playable job: its content, task
factory, rules and public projection. The engine owns money, reviews, turns and
validation; a plugin can only change its own task/ext data through `kit`.
Modules listed in ORDER but not present on disk are skipped, so careers can be
added one at a time without touching the engine.
"""
from __future__ import annotations
import os
from importlib import import_module

ORDER = (
    'restaurant', 'cafe_bakery', 'florist', 'grocery', 'repair', 'farm', 'delivery',
    'homestay', 'pet_care', 'salon', 'corp_accounting', 'tax_payroll', 'group_accounting',
    'clothing', 'pet_shop', 'tra_da',
    'fruit', 'garbage', 'drain',   # street trades: fruit stall, rubbish round, drain cleaning
    'homemaker',                   # nội trợ: a home helper in a three-generation family
    'ice_cream',                   # bán kem: cô Hiền's ice-cream corner by the school gate
    'nail',                        # tiệm nail: chị Diệp's little nail shop on the street
    'pagoda',                      # thầy chùa: a young monk at chùa Gió Lành by the river landing
    'pho',                         # bán phở: bác Lâm's phở shop under the old banyan, the broth pot on all day
    'com',                         # bán cơm: dì Bảy's broken-rice stall at the mouth of the market
    'photobooth',                  # photobooth: chị Lam's Tiệm ảnh Tách Tách by the night market
    'giupviec',                    # giúp việc theo giờ: cô Mai's Nhà Thơm team, cleaning clients' flats by the hour
    'naucom',                      # nấu cơm gia đình: a hired home cook, one family's meal a day
    'babysitter',                  # bảo mẫu: a day minding one family's child for cô Tâm's sitting service
    'pilot', 'flight_attendant',
    'hr_admin', 'secretary', 'it_helpdesk',   # Công ty CP Cánh Diều: HR, the director's secretary, IT helpdesk
)
# Development filter: MNL_CAREERS=restaurant,florist loads only those plugins.
_ONLY = {x.strip() for x in os.environ.get('MNL_CAREERS', '').split(',') if x.strip()}
PLUGINS = {}
for _name in ORDER:
    if _ONLY and _name not in _ONLY:
        continue
    try:
        _module = import_module(f'.{_name}', __name__)
    except ModuleNotFoundError as error:
        if error.name == f'{__name__}.{_name}':
            continue
        raise
    PLUGINS[_module.SPEC['id']] = _module
IDS = tuple(PLUGINS)


def spec(career: str) -> dict:
    return PLUGINS[career].SPEC


def get(career: str):
    return PLUGINS.get(career)
