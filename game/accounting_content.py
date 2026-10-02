"""Original Vietnamese accounting teaching material (VND unless stated).

Content is server-side: question keys must go through procedures.public before
being sent to a player. Tax rates in scenarios are explicit teaching assumptions.
"""
import re
from .procedures import step

TT99_URL = 'https://congbao.chinhphu.vn/van-ban/thong-tu-so-99-2025-tt-btc-46529.htm'
SOURCES = [
    {'label': 'Thông tư 99/2025/TT-BTC – Công báo chính thức', 'url': TT99_URL,
     'locator': 'Ban hành 27/10/2025; hiệu lực 01/01/2026; Điều 1–31 và Phụ lục I–IV'},
    {'label': 'Luật Kế toán 88/2015/QH13 – Cổng thông tin Chính phủ',
     'url': 'https://vanban.chinhphu.vn/?pageid=27160&docid=183198',
     'locator': 'Quy định chung, chứng từ, tài khoản và sổ kế toán; đọc cùng văn bản sửa đổi hiện hành'},
]
VAS_SOURCES = [
    {'label': 'Quyết định149/2001/QĐ-BTC – VAS đợt1',
     'url': 'https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=22028',
     'locator': 'VAS02,03,04,14 – hàng tồn kho, TSCĐ và doanh thu'},
    {'label': 'Quyết định165/2002/QĐ-BTC – VAS đợt2',
     'url': 'https://chinhphu.vn/default.aspx?docid=11581&pageid=27160',
     'locator': 'VAS01,06,10,15,16,24 – nguyên tắc, thuê, ngoại tệ, xây dựng, đi vay, dòng tiền'},
    {'label': 'Quyết định234/2003/QĐ-BTC – VAS đợt3',
     'url': 'https://vbpl.vn/botaichinh/Pages/vbpq-toanvan.aspx?ItemID=17841',
     'locator': 'VAS05,07,08,21,25,26 – BĐSĐT, đầu tư, trình bày, hợp nhất, bên liên quan'},
    {'label': 'Quyết định12/2005/QĐ-BTC – VAS đợt4',
     'url': 'https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=18466',
     'locator': 'VAS17,22,23,27,28,29 – thuế thu nhập, sự kiện sau kỳ, chính sách và sai sót'},
    {'label': 'Quyết định100/2005/QĐ-BTC – VAS đợt5',
     'url': 'https://vbpl.vn/botaichinh/Pages/vbpq-toanvan.aspx?ItemID=16846',
     'locator': 'VAS11,18,19,30 – hợp nhất kinh doanh, dự phòng và thông tin liên quan'},
]
SOURCES.extend(VAS_SOURCES)
TAX_SOURCES = {
    'vat': {'label': 'Thuế GTGT – Văn bản hợp nhất114/VBHN-VPQH (20/05/2026)',
            'url': 'https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-114-vbhn-vpqh-469597.htm',
            'locator': 'Tra cứu nghĩa vụ và điều kiện thuế GTGT; kiểm tra kỳ áp dụng. Bản hợp nhất không tạo hiệu lực riêng; tỷ lệ bài tập là giả định'},
    'cit': {'label': 'Thuế TNDN – Văn bản hợp nhất113/VBHN-VPQH (20/05/2026)',
            'url': 'https://vanban.chinhphu.vn/?docid=218265&pageid=27160',
            'locator': 'Tra cứu thu nhập tính thuế, khoản điều chỉnh và điều kiện; kiểm tra kỳ áp dụng. Bản hợp nhất không tạo hiệu lực riêng; tỷ lệ bài tập là giả định'},
    'gmt': {'label': 'Nghị quyết107/2023/QH15 – Thuế TNDN bổ sung theo quy định chống xói mòn cơ sở thuế toàn cầu',
            'url': 'https://congbao.chinhphu.vn/van-ban/nghi-quyet-so-107-2023-qh15-40679.htm',
            'locator': 'Nguồn pháp luật riêng cho thuế tối thiểu toàn cầu; kiểm tra đối tượng, kỳ áp dụng và văn bản hướng dẫn, không suy ra nghĩa vụ từ ví dụ'},
    'pit': {'label': 'Thuế TNCN – Văn bản hợp nhất112/VBHN-VPQH (20/05/2026)',
            'url': 'https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-112-vbhn-vpqh-469595.htm',
            'locator': 'Tra cứu nghĩa vụ khấu trừ thuế TNCN; kiểm tra kỳ áp dụng. Bản hợp nhất không tạo hiệu lực riêng; khấu trừ bài tập là giả định'},
    'social': {'label': 'Bảo hiểm xã hội – Luật41/2024/QH15',
            'url': 'https://vanban.chinhphu.vn/?classid=1&docid=211199&pageid=27160',
            'locator': 'Hiệu lực01/07/2025; đọc cùng văn bản hướng dẫn và kỳ áp dụng. Tỷ lệ trích trong bài là giả định, không thay việc xác định đối tượng và mức đóng'},
}
SOURCES.extend(TAX_SOURCES.values())
SOURCES.extend([{'label': 'TT99 – Công báo chính thức, phần 1/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6Onm39-iviA6Iga3PvlYGZvG_pahsek4RkxvtJWTp1ii-B7RKLH09ur56dsZmH35HXig~~&file_name=2025_1563+%2b+1564_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 1; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 2/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6Onh7_USZxv5sYAwWEgac2MxmGucpxOva8W9nuOXdp8uMGs9-FQYJXv262RMV1tq2csg~~&file_name=2025_1565+%2b+1566_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 2; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 3/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6OntMj3yaKhgxVUbnnT3-Fv6tHidCppgcIf3r1yWQqwX3zIFXXImMkETjd6XyVzDjXlA~~&file_name=2025_1567+%2b+1568_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 3; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 4/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6Onp-E6h7mzizdIffZhnBVN13ARAvbvSlvwFjYMkjwed2DMPMVkgQn-ntBC83KGCgfuw~~&file_name=2025_1569+%2b+1570_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 4; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 5/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6Onp07Bv0h9Y-TXlTeIPZzgPfCIg_EZEClMyXH4F9unhXq3WKKphB4YyoFNYhy77qpkA~~&file_name=2025_1571+%2b+1572_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 5; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 6/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6Onqcz4jihJLUHA17j9OM20MS0IGiR15wlX-84G3XTqyaAqB1vLIR3v1H8pvnv1VOMxQ~~&file_name=2025_1573+%2b+1574_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 6; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 7/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6OnhhROYeSptv5dIqKPrHrHoQjoyVknrYVlAePIoiJESFnfUKM23bx1s2l8ibUSq9_zQ~~&file_name=2025_1575+%2b+1576_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 7; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 8/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6OnlJkTXaZoWcLROEfAy6ePDNINRvEvlH8CdRFQCUMPpGTbGLaDJyc2iJlHCVAF_0Y8g~~&file_name=2025_1577+%2b+1578_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 8; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 9/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6Onv6IC9hJAGEiOOm6wbywH4YYMya140uPMZT2_5LxhB6oHuE9U2xb5UeNuo4hQZErJA~~&file_name=2025_1579+%2b+1580_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 9; đối chiếu Điều và Phụ lục ghi trong bài'}, {'label': 'TT99 – Công báo chính thức, phần 10/10', 'url': 'https://g7.cdnchinhphu.vn/api/download/stream?Url=tm-8mq6BhNw0NbrKRhTDAQWsKg3tuqaY0aWypnY78U6M2BY68Ekp0Gvvr483flbRCg5Kr_2FOJOXWBKx_Y6OnnXF27KUm7xbY9mhoLAkN7K3NW0p7mTdwfd2_L7ntL6oED_ujnpjHybGBSx7H1u2ZA~~&file_name=2025_1581+%2b+1582_99-2025-TT-BTC.pdf', 'locator': 'PDF Công báo, phần 10; đối chiếu Điều và Phụ lục ghi trong bài'}])

# All 71 level-1 chart accounts and the level-2 codes actually used.
# Names changed by TT99 intentionally differ from older TT200 material.
ACCOUNT_CHART = [
    ('111', 'Tiền mặt'), ('112', 'Tiền gửi không kỳ hạn'), ('113', 'Tiền đang chuyển'),
    ('121', 'Chứng khoán kinh doanh'), ('128', 'Đầu tư nắm giữ đến ngày đáo hạn'),
    ('131', 'Phải thu của khách hàng'), ('133', 'Thuế GTGT được khấu trừ'),
    ('136', 'Phải thu nội bộ'), ('138', 'Phải thu khác'), ('141', 'Tạm ứng'),
    ('151', 'Hàng mua đang đi đường'), ('152', 'Nguyên liệu, vật liệu'),
    ('153', 'Công cụ, dụng cụ'), ('154', 'Chi phí sản xuất, kinh doanh dở dang'),
    ('155', 'Sản phẩm'), ('156', 'Hàng hóa'), ('157', 'Hàng gửi đi bán'),
    ('158', 'Nguyên liệu, vật tư tại kho bảo thuế'), ('171', 'Giao dịch mua, bán lại trái phiếu chính phủ'),
    ('211', 'Tài sản cố định hữu hình'), ('212', 'Tài sản cố định thuê tài chính'),
    ('213', 'Tài sản cố định vô hình'), ('214', 'Hao mòn tài sản cố định'),
    ('215', 'Tài sản sinh học'), ('217', 'Bất động sản đầu tư'),
    ('221', 'Đầu tư vào công ty con'), ('222', 'Đầu tư vào công ty liên doanh, liên kết'),
    ('228', 'Đầu tư khác'), ('229', 'Dự phòng tổn thất tài sản'),
    ('2293', 'Dự phòng phải thu khó đòi'), ('2294', 'Dự phòng giảm giá hàng tồn kho'),
    ('2291', 'Dự phòng giảm giá chứng khoán kinh doanh'),
    ('2292', 'Dự phòng tổn thất đầu tư vào đơn vị khác'),
    ('2295', 'Dự phòng tổn thất tài sản sinh học'), ('241', 'Xây dựng cơ bản dở dang'),
    ('2413', 'Sửa chữa, bảo dưỡng định kỳ TSCĐ'), ('2414', 'Nâng cấp, cải tạo TSCĐ'),
    ('242', 'Chi phí chờ phân bổ'), ('243', 'Tài sản thuế thu nhập hoãn lại'),
    ('244', 'Ký quỹ, ký cược'), ('331', 'Phải trả cho người bán'),
    ('332', 'Phải trả cổ tức, lợi nhuận'), ('333', 'Thuế và các khoản phải nộp Nhà nước'),
    ('3331', 'Thuế GTGT phải nộp'), ('3334', 'Thuế thu nhập doanh nghiệp'),
    ('3335', 'Thuế thu nhập cá nhân'), ('334', 'Phải trả người lao động'),
    ('335', 'Chi phí phải trả'), ('336', 'Phải trả nội bộ'), ('337', 'Thanh toán theo tiến độ hợp đồng xây dựng'),
    ('338', 'Phải trả, phải nộp khác'), ('3387', 'Doanh thu chờ phân bổ'),
    ('341', 'Vay và nợ thuê tài chính'), ('343', 'Trái phiếu phát hành'),
    ('344', 'Nhận ký quỹ, ký cược'), ('347', 'Thuế thu nhập hoãn lại phải trả'),
    ('352', 'Dự phòng phải trả'), ('353', 'Quỹ khen thưởng, phúc lợi'),
    ('356', 'Quỹ phát triển khoa học và công nghệ'), ('357', 'Quỹ bình ổn giá'),
    ('411', 'Vốn đầu tư của chủ sở hữu'), ('412', 'Chênh lệch đánh giá lại tài sản'),
    ('413', 'Chênh lệch tỷ giá hối đoái'), ('414', 'Quỹ đầu tư phát triển'),
    ('418', 'Các quỹ khác thuộc vốn chủ sở hữu'), ('419', 'Cổ phiếu mua lại của chính mình'),
    ('421', 'Lợi nhuận sau thuế chưa phân phối'), ('4211', 'Lợi nhuận sau thuế chưa phân phối lũy kế đến cuối năm trước'),
    ('4212', 'Lợi nhuận sau thuế chưa phân phối năm nay'),
    ('4118', 'Vốn khác'), ('2281', 'Đầu tư góp vốn vào đơn vị khác'),
    ('511', 'Doanh thu bán hàng và cung cấp dịch vụ'),
    ('515', 'Doanh thu hoạt động tài chính'), ('521', 'Các khoản giảm trừ doanh thu'),
    ('621', 'Chi phí nguyên liệu, vật liệu trực tiếp'), ('622', 'Chi phí nhân công trực tiếp'),
    ('623', 'Chi phí sử dụng máy thi công'), ('627', 'Chi phí sản xuất chung'),
    ('632', 'Giá vốn hàng bán'), ('635', 'Chi phí tài chính'), ('641', 'Chi phí bán hàng'),
    ('642', 'Chi phí quản lý doanh nghiệp'), ('711', 'Thu nhập khác'), ('811', 'Chi phí khác'),
    ('821', 'Chi phí thuế thu nhập doanh nghiệp'), ('8211', 'Chi phí thuế thu nhập doanh nghiệp hiện hành'),
    ('82111', 'Chi phí thuế thu nhập doanh nghiệp hiện hành theo quy định của Luật thuế thu nhập doanh nghiệp'),
    ('82112', 'Chi phí thuế thu nhập doanh nghiệp bổ sung theo quy định về thuế tối thiểu toàn cầu'),
    ('8212', 'Chi phí thuế thu nhập doanh nghiệp hoãn lại'), ('911', 'Xác định kết quả kinh doanh'),
]

def ref(locator, label='TT99/2025/TT-BTC'):
    return {'label': label, 'url': TT99_URL, 'locator': locator}

def choice(prompt, correct, *wrong, explain):
    # Rotate the correct option deterministically so the curriculum does not teach
    # that the first answer is always right. Option ids carry no answer semantics.
    labels = list(wrong)
    at = sum(ord(c) for c in prompt) % (len(labels) + 1)
    labels.insert(at, correct)
    return step('', 'choice', 'Chọn cách xử lý', prompt, f'o{at}',
                options=[{'id': f'o{i}', 'label': s} for i, s in enumerate(labels)], explain=explain)

def number(prompt, key, explain, unit='đ'):
    return step('', 'number', 'Tính giá trị' if unit != 'đ' else 'Tính số tiền', prompt, key, unit=unit, explain=explain)

def entry(prompt, rows, explain):
    return step('', 'entry', 'Lập bút toán', prompt, rows,
                accounts=[{'id': code, 'label': f'{code} — {name}'} for code, name in ACCOUNT_CHART],
                explain=explain)

def fields(prompt, values, explain):
    return step('', 'fields', 'Hoàn thành bảng', prompt, {k: v for k, _, v in values},
                fields=[{'id': k, 'label': label} for k, label, _ in values], explain=explain)

def order(prompt, labels, explain):
    return step('', 'order', 'Sắp xếp quy trình', prompt, [f's{i}' for i in range(len(labels))],
                items=[{'id': f's{i}', 'label': label} for i, label in enumerate(labels)], explain=explain)

def multi(prompt, correct, wrong, explain):
    labels = list(correct) + list(wrong)
    return step('', 'multi', 'Chọn các điều kiện', prompt, [f'm{i}' for i in range(len(correct))],
                options=[{'id': f'm{i}', 'label': label} for i, label in enumerate(labels)], explain=explain)

def match(prompt, pairs, explain):
    return step('', 'match', 'Ghép nội dung', prompt, {f'l{i}': f'r{i}' for i in range(len(pairs))},
                left=[{'id': f'l{i}', 'label': a} for i, (a, _) in enumerate(pairs)],
                right=[{'id': f'r{i}', 'label': b} for i, (_, b) in enumerate(pairs)], explain=explain)

def lesson(slug, title, objectives, body, example, questions, exam, locator):
    vas = set(re.findall(r'VAS(\d{2})', locator))
    references = [ref(locator)]
    for source in VAS_SOURCES:
        source_vas = set(re.findall(r'VAS(\d{2})', source['locator']))
        # The bibliography uses compressed lists (VAS02,03,04...); expand them.
        source_vas.update(re.findall(r'(?<!\d)(\d{2})(?=,|\s*–)', source['locator']))
        if vas & source_vas:
            references.append(dict(source, locator='Căn cứ chuẩn mực: ' + ', '.join('VAS'+v for v in sorted(vas & source_vas))))
    tax_refs = {'tax': ('vat', 'cit'), 'vat': ('vat',), 'currenttax': ('cit', 'gmt'),
                'deferredtax': ('cit',), 'payroll': ('pit', 'social')}
    references.extend(dict(TAX_SOURCES[k]) for k in tax_refs.get(slug, ()))
    return {'id': slug, 'title': title, 'objectives': objectives, 'body': body,
            'example': {'title': 'Ví dụ có lời giải', 'lines': example},
            'references': references, 'questions': questions, '_exam': exam}

def build_course(cid, name, description, chapters):
    result, bank = [], []
    for slug, title, lessons in chapters:
        chapter_id = f'{cid}_{slug}'
        for l in lessons:
            l['id'] = f'{cid}_{l["id"]}'
            for i, q in enumerate(l['questions']):
                q.update(id=f'{l["id"]}_practice_{i+1}', lesson_id=l['id'], chapter_id=chapter_id)
            q = l.pop('_exam')
            q.update(id=f'{l["id"]}_exam', lesson_id=l['id'], chapter_id=chapter_id)
            bank.append(q)
        result.append({'id': chapter_id, 'title': title, 'lessons': lessons})
    return {'id': cid, 'name': name, 'description': description, 'chapters': result}, bank

from .accounting_basic_content import build_basic
from .accounting_vn_content import build_vn

_basic, _basic_exam = build_basic()
_vn, _vn_exam = build_vn()
COURSES = [_basic, _vn]
LESSONS = {l['id']: l for c in COURSES for ch in c['chapters'] for l in ch['lessons']}
EXAM_BANK = {'basic': _basic_exam, 'vn_business': _vn_exam}
