"""Paid career equipment. Ownership is authoritative; tiers replace, never stack."""
import contextvars
from .work_gear import NAMES

_BONUS=contextvars.ContextVar('income_equipment_bonus',default=None)

ONLINE_CAREERS = ('tra_da','fruit','ice_cream','cafe_bakery','milk_tea','florist','grocery','clothing')
RATES = {'demand': (0,15,30,50), 'quality': (0,10,20,30), 'online': (0,25,50,100)}
PRICES = {'demand': (0,120,280,600), 'quality': (0,100,260,560), 'online': (0,140,320,680)}
GROUPS = {'demand': 'Đón thêm khách', 'quality': 'Kiếm thêm từ mỗi việc', 'online': 'Thêm đơn online'}
EQUIPMENT = {
    'demand': ('Bảng giới thiệu dịch vụ','Bộ bảng hiệu và đèn đón khách','Bộ đặt lịch và chăm khách quen'),
    'quality': ('Bộ dụng cụ tinh chỉnh','Bàn kiểm chất lượng','Bộ thiết bị hoàn thiện cao cấp'),
    'online': ('Đèn chụp và phông sản phẩm','Máy nhận đơn và in phiếu','Bộ chụp sản phẩm và quản lý gian hàng'),
}


def item_id(career, group, tier):
    return f'incomegear_{career}_{group}_{tier}'


def catalogue():
    out=[]
    for career in NAMES:
        for group,rates in RATES.items():
            if group=='online' and career not in ONLINE_CAREERS:continue
            for tier in range(1,4):
                percent=rates[tier]
                description={
                    'demand': f'Tăng tối đa {percent}% nhịp đơn riêng của nhân viên và khách tại quầy tự mở cùng nghề, trong giới hạn tốc độ phục vụ. Cần có nhân viên đang làm và đủ hàng cho đơn tự động.',
                    'quality': f'Thưởng {percent}% tiền hoàn thành đơn hoặc hồ sơ; tăng {percent}% lãi dương đơn nhân viên và quầy tự mở. Thưởng ở nghề làm tròn lên xu nguyên; quầy tự mở giữ phần xu lẻ sang đơn sau. Lương cố định, bài học và giao dịch người chơi không áp dụng.',
                    'online': f'Tăng {percent}% nhịp đơn online ở quầy tự mở cùng nghề khi bật bán online, cả lúc tự đứng quầy và có nhân viên. Vẫn cần hàng và trả phí giao hàng.',
                }[group]+' Bậc cao thay bậc thấp, không cộng dồn trong cùng nhóm.'
                out.append(dict(id=item_id(career,group,tier),name=EQUIPMENT[group][tier-1]+f' · Bậc {tier}',
                    icon='tool',kind='equipment',min_level=1,careers=[career],price=PRICES[group][tier],
                    gear_group=group,group_name=GROUPS[group],gear_tier=tier,effect_percent=percent,
                    effect_label={'demand':'nhịp khách','quality':'thu nhập từ việc','online':'nhịp đơn online'}[group],
                    description=description,requires=item_id(career,group,tier-1) if tier>1 else None))
    return out


ITEMS={u['id']:u for u in catalogue()}


def effects(c):
    result={group:0 for group in RATES}
    for key in c.get('upgrades',[]):
        item=ITEMS.get(key)
        if item:result[item['gear_group']]=max(result[item['gear_group']],item['effect_percent'])
    return result


def demand_factor(c):
    return 1+effects(c)['demand']/100


def improved_revenue(c, revenue, costs):
    return revenue+(max(0,revenue-costs)*effects(c)['quality']+99)//100


def completion_bonus(s,c,pay,title,ref):
    """Called only by guarded terminal work actions, never by generic money credits."""
    from .engine import money
    bonus=(max(0,pay)*effects(c)['quality']+99)//100
    if bonus:
        before=c['money']
        money(s,c,bonus,'Thiết bị chất lượng · '+title,ref,category='other_income')
        bonus=c['money']-before
        if _BONUS.get() is not None:_BONUS.set(_BONUS.get()+bonus)
    return bonus


def collect(run):
    """Explain the extra receipt without changing the customer's original bill."""
    token=_BONUS.set(0)
    try:
        state,result=run()
        bonus=_BONUS.get()
        if bonus:
            result=dict(result,income_gear_bonus=bonus,
                        message=result.get('message','Đã hoàn thành.')+f' +{bonus} xu nhờ thiết bị chất lượng.')
        return state,result
    finally:
        _BONUS.reset(token)


def cached(st, group):
    return st.get('business',{}).get('income_gear',{}).get(group,0)


def profit_percent(st, base):
    # Scale the owner's positive margin including its existing profit bonus.
    return base+(100+base)*cached(st,'quality')//100


def online_rate(st):
    return 100+cached(st,'online') if st.get('online') else 100


def channel(st, seq):
    if not st.get('online'):return 'counter'
    rate=online_rate(st);total=200+rate
    return 'online' if (seq+1)*rate//total>seq*rate//total else 'counter'
