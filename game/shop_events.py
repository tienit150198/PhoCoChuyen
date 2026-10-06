"""Recurring owner decisions. No unattended debits, backlog, or client outcomes.

Optional sidecars keep legacy cases and schema 4 saves readable. Progress is
actual work, not reads or wall-clock polling. Only resolving a pending decision
books a bounded local expense, exactly once; resolving starts a fresh interval.
"""
from __future__ import annotations

import copy
import random
from . import wealth_pricing

GAP = 12
RECENT = 8
FOOD = frozenset({'milk_tea', 'restaurant', 'cafe_bakery', 'tra_da', 'fruit', 'ice_cream', 'pho', 'com'})
RETAIL = FOOD | frozenset({'mother_baby', 'pharmacy', 'florist', 'grocery', 'clothing', 'pet_shop', 'repair', 'salon', 'pet_care', 'nail', 'photobooth', 'homestay'})


def _choice(id, label, cost, rep, text, loss=False):
    return dict(id=id, label=label, cost=cost, rep=rep, text=text, loss=loss)


def _event(title, text, *choices):
    return dict(title=title, text=text, choices=choices)


CATALOGUE = {
    'equipment_repair': _event('Thiết bị cần bảo dưỡng', 'Thiết bị làm việc phát tiếng lạ. Chủ tiệm chọn cách bảo dưỡng trước ca tiếp theo.',
        _choice('repair', 'Thuê thợ bảo dưỡng thiết bị', 240, 2, 'Thiết bị được kiểm tra, khách yên tâm với chất lượng phục vụ.'),
        _choice('defer', 'Tạm cất thiết bị, dùng phương án thủ công', 0, -2, 'Bạn dùng dụng cụ dự phòng; khách phải chờ lâu hơn.')),
    'stock_spoil': _event('Nguyên liệu cần thay mới', 'Một mẻ nguyên liệu mẫu không còn đạt chất lượng. Bạn loại bỏ mẻ đó và cân nhắc bổ sung cho buổi bán.',
        _choice('replace', 'Bổ sung mẻ nguyên liệu tươi', 160, 1, 'Tiệm có nguyên liệu tươi để giữ chất lượng; khoản bổ sung được ghi chi phí.'),
        _choice('discard', 'Bỏ mẻ lỗi và thu gọn thực đơn', 0, -1, 'Bạn chỉ phục vụ món còn nguyên liệu đạt chuẩn; khách có ít lựa chọn hơn.')),
    'staff_training': _event('Buổi hướng dẫn phục vụ', 'Có buổi thực hành kiểm hàng và phục vụ khách dành cho đội ngũ cửa tiệm.',
        _choice('train', 'Chi cho buổi hướng dẫn thực hành', 200, 3, 'Đội ngũ luyện cách kiểm hàng và giao tiếp; chất lượng phục vụ giúp tăng uy tín.'),
        _choice('internal', 'Tự ôn lại quy trình trong tiệm', 0, 0, 'Bạn cùng mọi người ôn quy trình hiện có, không phát sinh chi phí.')),
    'local_promotion': _event('Quảng bá tiệm trong khu phố', 'Nhóm sinh hoạt khu phố mời tiệm giới thiệu dịch vụ trong bảng tin chung.',
        _choice('promote', 'In tờ giới thiệu và mẫu trưng bày', 180, 2, 'Người trong khu biết rõ dịch vụ của tiệm; khoản quảng bá được ghi sổ.'),
        _choice('decline', 'Tiếp tục giới thiệu trực tiếp tại tiệm', 0, 0, 'Bạn giữ ngân sách và tiếp tục giới thiệu với khách ghé tiệm.')),
    'theft': _event('Khách lén lấy đồ', 'Bạn thấy một người giấu món hàng rồi đi qua quầy thanh toán. Giữ khoảng cách an toàn; không đuổi theo ngoài đường.',
        _choice('report', 'Nhờ hỗ trợ, giữ chứng cứ và báo sự việc', 4, 1, 'Bạn giữ an toàn, bàn giao chứng cứ. Ghi nhận phần hao hụt nhỏ chưa thu hồi.', True),
        _choice('record', 'Ghi nhận hao hụt và siết việc kiểm hàng', 12, -1, 'Bạn kiểm lại quầy và ghi nhận thiệt hại thực tế, không quy lỗi cho người khác.', True)),
    'dine_dash': _event('Khách ăn xong định bỏ đi', 'Một bàn đã dùng món nhưng rời đi khi hóa đơn còn chưa thanh toán.',
        _choice('remind', 'Nhắc hóa đơn bình tĩnh, nhờ đồng nghiệp hỗ trợ', 0, 1, 'Khách quay lại thanh toán. Bạn giữ được không khí bình tĩnh.'),
        _choice('record', 'Không đuổi theo; ghi khoản thất thoát', 10, -1, 'Bạn ghi phần thất thoát và nhắc nhân viên kiểm hóa đơn trước khi khách rời bàn.', True)),
    'influencer': _event('Người nổi tiếng xin đồ miễn phí', 'Một người làm nội dung đề nghị nhận hàng miễn phí để đổi lấy một bài đăng, chưa có thỏa thuận cụ thể.',
        _choice('sample', 'Tặng một mẫu nhỏ, ghi rõ đây là quà tài trợ', 8, 2, 'Bạn tặng mẫu theo ngân sách quảng bá, không hứa mua đánh giá tốt.'),
        _choice('decline', 'Lịch sự giữ chính sách giá chung', 0, 0, 'Bạn giải thích chính sách; mọi khách đều được phục vụ với cùng mức giá.')),
    'lost_child': _event('Em nhỏ bị lạc trước cửa', 'Một em nhỏ đứng khóc và không thấy người đi cùng. Em vẫn ở ngay trước cửa tiệm.',
        _choice('help', 'Ở cạnh em, nhờ bảo vệ tìm người thân', 0, 2, 'Bạn ở nơi dễ quan sát, cùng bảo vệ xác minh người thân trước khi bàn giao em.'),
        _choice('support', 'Chuẩn bị nước và nhờ nhân viên hỗ trợ', 3, 3, 'Em được trấn an; nhân viên và bảo vệ xác minh, đưa em về với người thân.')),
    'traffic_inspection': _event('Kiểm tra chỗ đặt xe bán hàng', 'Cán bộ nhắc xe và bảng menu đang lấn lối đi. Biên bản cho phép khắc phục ngay hoặc nộp khoản phạt mô phỏng.',
        _choice('rectify', 'Thu gọn xe, dọn lối đi ngay', 0, -1, 'Bạn thu gọn xe đúng vị trí, khắc phục trong thời hạn nhắc nhở; một vài khách phải chờ.'),
        _choice('fine', 'Nhận biên bản và nộp phạt qua kênh chính thức', 15, 0, 'Khoản phạt được ghi sổ; bạn cũng thu gọn xe để tiếp tục bán đúng vị trí.')),
    'shop_inspection': _event('Đoàn kiểm tra cửa tiệm', 'Đợt kiểm tra phát hiện nhãn lô hàng chưa đầy đủ. Bạn được yêu cầu khắc phục và lưu phiếu đối chiếu.',
        _choice('rectify', 'Mua bộ nhãn, đối chiếu và bổ sung ngay', 6, 2, 'Nhãn lô và phiếu được bổ sung; đoàn kiểm tra ghi nhận đã khắc phục.'),
        _choice('hold', 'Tự đối chiếu, tạm ngừng nhận khách mới', 0, -2, 'Bạn tạm dừng để tự hoàn thiện nhãn và phiếu. Khách chờ lâu hơn nhưng hàng được kiểm đủ.')),
    'fake_transfer': _event('Ảnh chuyển khoản chưa khớp', 'Khách đưa ảnh báo chuyển tiền nhưng sổ giao dịch chưa có khoản tương ứng.',
        _choice('verify', 'Đối chiếu giao dịch rồi mới giao hàng', 0, 1, 'Khách dùng phương thức thanh toán khác sau khi cùng kiểm tra.'),
        _choice('trust', 'Tin ảnh và giao hàng ngay', 10, -2, 'Khoản chuyển không tới; bạn ghi khoản mất để đối chiếu, không ghi doanh thu khống.', True)),
    'supplier_short': _event('Kiện hàng giao thiếu phụ kiện', 'Nhà cung cấp báo thiếu phụ kiện trong kiện mới; phần thiếu chưa được nhập vào kho.',
        _choice('claim', 'Giữ phiếu và yêu cầu giao bổ sung', 0, 1, 'Bạn đối chiếu với nhà cung cấp, chỉ nhập phần thực nhận.'),
        _choice('express', 'Trả phí giao nhanh phần bổ sung', 5, 2, 'Nhà cung cấp giao bổ sung phụ kiện; phí chuyển phát được ghi chi phí.')),
    'rain': _event('Mưa tạt vào cửa tiệm', 'Mưa bất chợt khiến khách tụ lại và lối ra vào ướt trơn.',
        _choice('tidy', 'Lau khô, xếp lại lối ra vào', 0, 1, 'Bạn ưu tiên lối đi an toàn và nhắc khách cẩn thận.'),
        _choice('cover', 'Mua tấm che và thảm chống trượt', 7, 2, 'Lối vào khô hơn, khách trú mưa thoải mái; chi phí được ghi sổ.')),
    'wrong_change': _event('Khách nói bị thối thiếu tiền', 'Khách quay lại với hóa đơn và đề nghị đối chiếu tiền thừa.',
        _choice('count', 'Cùng kiểm hóa đơn và kiểm quỹ', 0, 1, 'Hai bên đối chiếu rõ ràng và giải quyết nhầm lẫn.'),
        _choice('refund', 'Bù khoản nhỏ để khách khỏi chờ', 4, 2, 'Bạn ghi rõ khoản hỗ trợ khách, không sửa doanh thu của hóa đơn trước.')),
    'queue_dispute': _event('Hai khách tranh lượt', 'Hai khách cùng cho rằng mình tới trước, những người phía sau bắt đầu sốt ruột.',
        _choice('order', 'Nhắc thứ tự và phát số lượt', 0, 1, 'Bạn xác nhận thứ tự và mời từng khách, hàng chờ yên trở lại.'),
        _choice('gesture', 'Xin lỗi và tặng món hỗ trợ nhỏ', 5, 2, 'Khách nhận lời xin lỗi và tiếp tục chờ theo thứ tự.')),
    'power_cut': _event('Điện chập chờn', 'Đèn quầy nhấp nháy. Bạn cần kiểm nguồn trước khi tiếp tục dùng thiết bị.',
        _choice('pause', 'Ngắt thiết bị, tự kiểm ổ cắm an toàn', 0, -1, 'Bạn ngừng thiết bị, xác nhận nguồn an toàn rồi mới tiếp tục; khách phải đợi thêm.'),
        _choice('repair', 'Nhờ thợ kiểm tra nguồn điện', 9, 2, 'Thợ kiểm tra và khắc phục đầu nối, bạn lưu khoản sửa chữa.')),
}


def career_eligible(career):
    return career in RETAIL


def eligible_kinds(career, place):
    return [kind for kind in CATALOGUE if (kind not in ('dine_dash','stock_spoil') or career in FOOD)
            and (kind != 'traffic_inspection' or place == 'xe')]


def theft_probability(items, protection='none'):
    # Camera is excluded from the base security reduction: its factor is exact.
    base = .20 * (.8 if 'ket' in items or 'lock' in items else 1)
    if 'alarm' in items:base *= .75
    base *= {'none':1, 'basic':.8, 'premium':.6}.get(protection,1)
    return base / 2 if 'camera' in items else base


def select_kind(career, place, items, seed, seq, protection='none'):
    rng = random.Random(f'shop-events|{seed}|{career}|{place}|{seq}')
    if rng.random() < theft_probability(items,protection):
        return 'theft'
    return rng.choice([kind for kind in eligible_kinds(career, place) if kind != 'theft'])


def make_event(kind, seq, owner, camera):
    return dict(id=f'shop-{owner}-{seq}', kind=kind, camera_at_event=camera)


def _state(container, progress):
    if 'shop_events' not in container:
        container['shop_events'] = dict(v=1, seq=0, next=progress + GAP, pending=None, recent=[], reputation=0, spent=0)
        return True
    return False


def _tick(s, container, career, owner, progress, items, place=None, busy=False):
    fresh = _state(container, progress)
    state = container['shop_events']
    if fresh or state['pending'] or progress < state['next'] or busy:
        return fresh
    if not s.get('settings', {}).get('securityEvents', True):
        state['next'] = progress + GAP
        return True
    state['seq'] += 1
    seed = str(s.get('journey', {}).get('seed', 0)) + '|' + owner
    protection=container.get('business',{}).get('protection',{}).get('level','none')
    kind = select_kind(career, place, items, seed, state['seq'],protection)
    state['pending'] = make_event(kind, state['seq'], owner, 'camera' in items)
    quote = (container.get('business',{}).get('protection_quote') if place else container.get('insurance_quote'))
    # Use the same saved day/shift basis online and offline. Polling frequency
    # must not change the loss just because a batch contains more sales.
    if wealth_pricing.ENABLED:
        state['pending']['wealth'] = quote['wealth'] if quote else wealth_pricing.total(s)
        if kind == 'theft':
            state['pending'].update(wealth_pricing.event_quote(s, state['pending']['id'], state['pending']['wealth']))
    return True


def _career_progress(c):
    return c['ops']['work_ticks'] + c['ops'].get('business', {}).get('served', 0)


def tick_career(s, c, career):
    if not career_eligible(career) or not c.get('started'):
        return False
    o = c['ops']
    busy = any(x['status'] != 'closed' for x in o['security']['cases']) or bool(o['incident'] and o['incident']['status'] != 'resolved')
    busy = busy or bool(c.get('event') and c['event']['stage'] != 'resolved')
    return _tick(s, o, career, career, _career_progress(c), o['security']['items'], busy=busy)


def tick_quay(s, st):
    if 'business' not in st:
        return False
    run = st.get('run') or {}
    busy = bool(st.get('case')) or len(run.get('eo', [])) < len(run.get('ev', []))
    return _tick(s, st, st['trade'], st['id'], st['business']['sold'], st['items'], st['place'], busy)


def _cash(c, quay):
    return c['fund'] + c['till'] if quay else c['money']


def demand_factor(c, quay=False):
    rep = c['rep'] - 100 if quay else c.get('ops', {}).get('shop_events', {}).get('reputation', 0)
    return (100 + max(-10, min(10, rep))) / 100


def _maximum(choice, wealth=0, percent=None):
    if percent is not None:
        loss = wealth_pricing.event_cost(dict(wealth=wealth, percent=percent))
        return (loss + 2) // 3 if choice['id'] == 'report' else loss
    return wealth_pricing.cost(choice['cost'], wealth)


def _cost(choice, cash, kind=None, items=(), wealth=0, percent=None):
    # Unavoidable losses cannot empty a till even if the owner moved funds since
    # the event appeared. Optional spending requires the full published price.
    cost=_maximum(choice, wealth, percent)
    if (kind=='power_cut' and 'surge' in items) or (kind=='shop_inspection' and 'hygiene' in items):
        cost=(cost+1)//2
    # A counter's két sắt: a theft never takes more than half of the cash there.
    cap = cash // 2 if kind == 'theft' and 'ket' in items else cash
    return min(cost, max(0, cap if percent is not None else cash // 10)) if choice['loss'] else cost


def public(c, quay=False):
    container = c if quay else c['ops']
    state = container.get('shop_events')
    if not state:
        return None
    items = c['items'] if quay else c['ops']['security']['items']
    out = dict(pending=None, recent=copy.deepcopy(state['recent']), camera='camera' in items,
               theft_probability=theft_probability(items,container.get('business',{}).get('protection',{}).get('level','none')), gap=GAP, reputation=state['reputation'], spent=state['spent'])
    out.update(demand_factor=demand_factor(c,quay), reputation_effect='Uy tín ảnh hưởng lượng khách của nhân viên, tối đa ±10%.')
    pending = state['pending']
    if pending:
        spec = CATALOGUE[pending['kind']]
        out['pending'] = dict(pending, title=spec['title'], text=spec['text'], choices=[])
        for x in spec['choices']:
            cost = _cost(x, _cash(c, quay),pending['kind'],items,pending.get('wealth',0),pending.get('percent'))
            effect = x['text'] + (f" Uy tín {'+' if x['rep'] >= 0 else ''}{x['rep']}." if x['rep'] else '')
            if x['loss']:effect += ((' Hao hụt tính theo tài sản lúc phát sinh, ' + ('két sắt giữ lại ít nhất nửa quỹ hiện có.' if pending['kind'] == 'theft' and 'ket' in items else 'không vượt quỹ hiện có.'))
                                    if 'percent' in pending else ' Hao hụt tối đa 10% quỹ hiện có.')
            out['pending']['choices'].append(dict(id=x['id'], label=x['label'], cost=cost, max_cost=_maximum(x,pending.get('wealth',0),pending.get('percent')),
                rep=x['rep'], effect=effect, affordable=_cash(c, quay) >= cost))
    return out


def _choose(s, c, owner, p, quay):
    from . import engine
    need = engine.need
    need(isinstance(p, dict) and set(p) <= ({'stall', 'event', 'choice', 'confirm'} if quay else {'event', 'choice', 'confirm'}), 'Thông tin xử lý tình huống không hợp lệ.')
    need(p.get('confirm') is True, 'Xác nhận cách xử lý tình huống.')
    container = c if quay else c['ops']
    state = container.get('shop_events')
    pending = state and state['pending']
    need(pending and pending['id'] == p.get('event'), 'Tình huống đã được xử lý hoặc không còn chờ.', 'no_event')
    spec = CATALOGUE[pending['kind']]
    choice = next((x for x in spec['choices'] if x['id'] == p.get('choice')), None)
    need(choice, 'Cách xử lý không hợp lệ.')
    items=c['items'] if quay else c['ops']['security']['items']
    cost = _cost(choice, _cash(c, quay),pending['kind'],items,pending.get('wealth',0),pending.get('percent'))
    need(_cash(c, quay) >= cost, 'Quỹ không đủ; chọn phương án không tốn xu.', 'no_money')
    if quay:
        from . import quay as qy, quay_business as qb
        qy._from_till_fund(c, cost)
        c['business']['expenses']['loss'] += cost
        qb._profit_state(c)['costs'] += cost
        c['business']['income_tax']['loss'] += cost
        c['rep'] = max(90, min(110, c['rep'] + choice['rep']))
        qy._log(c, s['journey']['life_day'], spec['title'] + ': ' + choice['label'], -cost)
        progress = c['business']['sold']
    else:
        # Explicit ledger write: service-order suppression must never suppress
        # this independent owner expense while a visitor task is open.
        from . import operations
        c['money'] -= cost
        c['costs'] += cost
        if cost:operations.record_money(c, -cost, spec['title'], pending['id'], 'other_cost')
        engine.log(s, c, 'shop_event', choice['text'], ref=pending['id'])
        progress = _career_progress(c)
    state['reputation'] = max(-10, min(10, state['reputation'] + choice['rep']))
    state['spent'] += cost
    row = dict(id=pending['id'], kind=pending['kind'], title=spec['title'], choice=choice['id'],
               text=choice['text'], cost=cost, rep=choice['rep'])
    if 'wealth' in pending:row['wealth']=pending['wealth']
    if 'percent' in pending:row['percent']=pending['percent']
    state['recent'] = (state['recent'] + [row])[-RECENT:]
    state['pending'] = None
    state['next'] = progress + GAP
    return dict(message=choice['text'] + (f' Đã ghi chi phí {cost} xu.' if cost else ''), shop_event=row)


def choose_career(s, c, career, p):
    from .engine import need
    need(career_eligible(career), 'Nghề này không có sự kiện chủ tiệm.')
    return _choose(s, c, career, p, False)


def choose_quay(s, st, p):
    return _choose(s, st, st['id'], p, True)


def validate(container, owner, career, place=None):
    from .engine import need
    state = container.get('shop_events')
    if state is None:return
    def check(ok):need(ok, 'Dữ liệu tình huống chủ tiệm không hợp lệ.', 'invalid_save')
    def integer(v, lo=0, hi=10**16):return type(v) is int and lo <= v <= hi
    check(isinstance(state, dict) and set(state) == {'v','seq','next','pending','recent','reputation','spent'})
    check(type(state['v']) is int and state['v'] == 1)
    check(all(integer(state[k]) for k in ('seq','next','spent')) and integer(state['reputation'], -10, 10))
    kinds = eligible_kinds(career, place)
    prefix = 'shop-' + owner + '-'
    def valid_id(ref):
        return isinstance(ref,str) and ref.startswith(prefix) and ref[len(prefix):].isdigit() and 0 < int(ref[len(prefix):]) <= state['seq']
    pending = state['pending']
    if pending is not None:
        check(isinstance(pending,dict) and {'id','kind','camera_at_event'} <= set(pending) <= {'id','kind','camera_at_event','wealth','percent'})
        if 'wealth' in pending:check(wealth_pricing.valid_wealth(pending['wealth']))
        if 'percent' in pending:check(pending['kind']=='theft' and wealth_pricing.valid_event_quote(pending))
        check(pending['kind'] in kinds and pending['id'] == prefix + str(state['seq']) and type(pending['camera_at_event']) is bool)
    check(isinstance(state['recent'],list) and len(state['recent']) <= RECENT)
    ids=set()
    for row in state['recent']:
        check(isinstance(row,dict) and {'id','kind','title','choice','text','cost','rep'} <= set(row) <= {'id','kind','title','choice','text','cost','rep','wealth','percent'})
        if 'wealth' in row:check(wealth_pricing.valid_wealth(row['wealth']))
        if 'percent' in row:check(row['kind']=='theft' and wealth_pricing.valid_event_quote(row))
        check(valid_id(row['id']) and row['id'] not in ids and row['kind'] in kinds)
        ids.add(row['id'])
        spec=CATALOGUE[row['kind']];choice=next((x for x in spec['choices'] if x['id']==row['choice']),None)
        check(choice is not None)
        check(row['title']==spec['title'] and row['text']==choice['text'] and row['rep']==choice['rep'])
        # History keeps the cost paid then, even after protection equipment changes.
        maximum=_maximum(choice,row.get('wealth',0),row.get('percent'))
        costs={maximum}
        if row['kind'] in ('power_cut','shop_inspection'):costs.add((maximum+1)//2)
        check(integer(row['cost'], 0, maximum) and (choice['loss'] or row['cost'] in costs))
    check(pending is None or pending['id'] not in ids)
    check(sum(row['cost'] for row in state['recent']) <= state['spent'])
