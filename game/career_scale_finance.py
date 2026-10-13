"""Exact capital/management cash, excluded from legacy daily multipliers."""


def move(s, c, amount, label, ref, category='scale_capital'):
    from . import engine, operations
    engine.need(type(amount) is int and type(c.get('money')) is int,
                'Số tiền phải là số nguyên xu.')
    engine.need(c['money'] + amount >= 0, 'Quỹ nghề chưa đủ xu. Góp vốn vào nghề trước nhé.')
    engine.need(type(category) is str and category.startswith('scale_'), 'Loại giao dịch không hợp lệ.')
    engine.need(type(label) is str and len(label) <= 300 and type(ref) is str and len(ref) <= 150,
                'Biên nhận không hợp lệ.')
    c['money'] += amount
    operations.record_money(c, amount, label, ref, category)
    engine.log(s, c, 'money', f'{amount:+d} xu · {label}', ref=ref)
    if category == 'scale_capital' and 'scale' in c:
        rows = c['scale']['capital_history']
        rows.append(dict(amount=amount, label=label, ref=ref))
        del rows[:-80]
