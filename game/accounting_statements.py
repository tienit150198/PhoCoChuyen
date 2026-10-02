"""TT99 form labels and reconciled views of the fictional company's actual book.

Templates retain every official row. Unused rows have zero; notes explain the
case scope. Monthly comparative figures are pedagogical, not annual filings.
"""
import json
from pathlib import Path

TEMPLATES=json.loads(Path(__file__).with_name('accounting_report_templates.json').read_text(encoding='utf-8'))


def snapshot(book):
    from . import accounting_company as c
    opening,old_debts=c._opening(book['period'])
    rows=c._transactions(book['period'])[:book['at']]
    balances,debts=dict(opening),dict(old_debts)
    c._post(balances,rows,debts)
    movements={}
    for t in rows:
        for line in t['_key']:
            for side in ('debit','credit'):
                a=line[side];movements.setdefault(a,dict(debit=0,credit=0))[side]+=line['amount']
    operating=c._post({},[t for t in rows if not t['closing']])
    return opening,balances,debts,movements,operating,rows


def trial_balance(book):
    from . import accounting_company as c
    opening,balances,_,movements,_,_=snapshot(book)
    return [dict(account=a,name=name,opening_debit=max(opening.get(a,0),0),opening_credit=max(-opening.get(a,0),0),
                 movement_debit=movements.get(a,{}).get('debit',0),movement_credit=movements.get(a,{}).get('credit',0),
                 debit=max(balances.get(a,0),0),credit=max(-balances.get(a,0),0)) for a,name in c.CHART.items()]


def details(book):
    from . import accounting_company as c
    opening,bal,debts,moves,_,rows=snapshot(book)
    posted={t['id'] for t in rows};period=book['period']
    f=lambda p:10+(p-1)%3
    assets=[dict(id='TS-SX-00',name='Máy sản xuất đầu năm',cost=50_000_000,life=100,
                 accumulated=12_500_000+500_000*(period-1+('production_dep' in posted))),
            dict(id='TS-QL-00',name='Thiết bị quản lý đầu năm',cost=30_000_000,life=100,
                 accumulated=7_500_000+300_000*(period-1+('admin_dep' in posted)))]
    for p in range(1,period+1):
        if p<period or 'machine' in posted:
            assets.append(dict(id=f'TS-SX-{p:02}',name=f'Máy sản xuất mua tháng{p}',cost=36_000_000*f(p)//10,life=120,
                               accumulated=300_000*f(p)//10*(period-p+('production_dep' in posted))))
    for a in assets:a['net']=a['cost']-a['accumulated']
    insurance=[];services=[];deposits=[];fx=[]
    for p in range(1,period+1):
        if p<period or 'insurance' in posted:
            cost=2_400_000*f(p)//10; monthly=cost//12;used=period-p+('allocation' in posted)
            insurance.append(dict(id=f'BH-{p:02}',start=p,periods=12,cost=cost,monthly=monthly,allocated=monthly*used,remaining=cost-monthly*used))
        if p<period or 'service_advance' in posted:
            total=6_000_000*f(p)//10; recognized=total//3*min(3,period-p+('service_revenue' in posted))
            services.append(dict(id=f'DV-{p:02}',start=p,periods=3,total=total,recognized=recognized,remaining=total-recognized))
        if p>=period-6 and (p<period or 'term_deposit' in posted) and not(p==period-6 and 'term_maturity' in posted):
            principal=10_000_000*f(p)//10;elapsed=min(6,period-p+('term_interest_accrual' in posted))
            deposits.append(dict(id=f'TG-{p:02}',start=p,maturity=p+6,principal=principal,accrued=principal//200*elapsed,
                                 balance=principal+principal//200*elapsed,rate='3%/6 tháng, trả lãi khi đáo hạn'))
        if p<period or 'fx_invoice' in posted:
            usd=100*f(p)//10;trade_rate=25_000+(p-1)*100
            rate=26_000+(period-1)*100 if 'fx_revalue' in posted else 26_000+(period-2)*100 if p<period else trade_rate
            fx.append(dict(id=f'FX-{p:02}',party='khach_fx',currency='USD',original=usd,trade_rate=trade_rate,rate=rate,vnd=usd*rate))
    parties=[dict(account=k.split('|')[0],party=k.split('|')[1],debit=max(v,0),credit=max(-v,0)) for k,v in sorted(debts.items())]
    return dict(assets=assets,insurance=insurance,services=services,deposits=deposits,foreign_currency=fx,parties=parties,
                production=dict(materials=moves.get('621',{}).get('debit',0),labor=moves.get('622',{}).get('debit',0),
                                overhead=moves.get('627',{}).get('debit',0),finished=moves.get('155',{}).get('debit',0),work_in_progress=bal.get('154',0)))


def numbers(book):
    from . import accounting_company as c
    op,bal,debts,_,p,rows=snapshot(book);v=c.reports(book)
    b=lambda a:bal.get(a,0)
    d=lambda a:sum(max(x,0) for k,x in debts.items() if k.startswith(a+'|'))
    cr=lambda a:sum(max(-x,0) for k,x in debts.items() if k.startswith(a+'|'))
    b1={r['code']:0 for r in TEMPLATES['B01']['rows']}
    b1.update({'111':b('111')+b('112'),'123':b('1281'),'131':d('131'),'132':d('331'),'136':b('2293'),
               '141':sum(b(a) for a in ('152','154','155','156','621','622','627')),'161':b('242'),
               '162':b('1331')+b('1332'),'222':b('211'),'223':b('214'),'272':b('243'),
               '311':cr('331'),'312':cr('131'),'313':-b('332'),'314':-b('3331')-b('3334'),
               '315':-b('334'),'319':-b('3387'),'320':-b('3383'),'321':-b('341'),'342':-b('347'),
               '411':-b('411'),'411a':-b('411'),'420b':v['profit']})
    # 420a/b follow report periods, not simply year-based 4211/4212 labels.
    # Each supplied resolution distributes previously closed earnings:
    # Jan from last year's4211, Feb onward from prior months'4212.
    b1['420a']=v['equity']-b1['411']-b1['420b']
    b1['420']=b1['420a']+b1['420b'];b1['400']=b1['411']+b1['420']
    b1['110']=b1['111'];b1['120']=b1['123'];b1['130']=sum(b1[k] for k in ('131','132','136'))
    b1['140']=b1['141'];b1['160']=b1['161']+b1['162']
    b1['100']=sum(b1[k] for k in ('110','120','130','140','150','160'))
    b1['221']=b1['222']+b1['223'];b1['220']=b1['221'];b1['270']=b1['272'];b1['200']=b1['220']+b1['270']
    b1['280']=b1['100']+b1['200']
    b1['310']=sum(b1[str(k)] for k in range(311,325));b1['330']=b1['342'];b1['300']=b1['310']+b1['330'];b1['440']=b1['300']+b1['400']
    b2={r['code']:0 for r in TEMPLATES['B02']['rows']}
    b2.update({'01':-p.get('511',0),'02':p.get('521',0),'10':v['revenue'],'11':v['cost'],
               '22':-p.get('515',0),'23':p.get('635',0),'24':p.get('635',0),'25':p.get('641',0),'26':p.get('642',0),
               '50':v['pretax'],'51':p.get('8211',0),'52':p.get('8212',0),'60':v['profit'],'70':None,'71':None})
    b2['20']=b2['10']-b2['11'];b2['30']=b2['20']+b2['21']+b2['22']-b2['23']-b2['25']-b2['26'];b2['40']=b2['31']-b2['32']
    b3={r['code']:0 for r in TEMPLATES['B03']['rows']}
    mapping={'old_receipt':'01','customer_advance':'01','goods_sale':'01','service_advance':'01',
             'supplier_pay':'02','supplier_advance':'02','goods':'02','insurance':'02','admin_cash':'07','selling':'02',
             'wage_pay':'03','interest':'04','charge_pay':'07','machine_pay':'21','term_deposit':'23',
             'capital':'31','loan':'33','loan_pay':'34','dividend_pay':'36'}
    for t in rows:
        cash=sum(l['amount']*((l['debit'] in ('111','112'))-(l['credit'] in ('111','112'))) for l in t['_key'])
        if t['id']=='term_maturity':
            principal=10_000_000*(10+(book['period']-7)%3)//10
            b3['24']+=principal;b3['27']+=cash-principal
        elif t['id'] in mapping:b3[mapping[t['id']]]+=cash
    b3['20']=sum(b3[f'{i:02}'] for i in range(1,8));b3['30']=sum(b3[str(i)] for i in range(21,28))
    b3['40']=sum(b3[str(i)] for i in range(31,37));b3['50']=b3['20']+b3['30']+b3['40'];b3['60']=v['cash_start'];b3['70']=v['cash_end']
    return {'B01':b1,'B02':b2,'B03':b3}


def note_values(book):
    from . import accounting_company as c
    _,bal,_,moves,p,rows=snapshot(book);v=c.reports(book);dt=details(book)
    n=c._n;b=lambda a:bal.get(a,0)
    element_materials=sum(l['amount'] for t in rows if t['id']=='issue' for l in t['_key'])
    element_staff=sum(l['amount'] for t in rows if t['id'] in ('production_wage','admin_wage','charges') for l in t['_key'])
    element_dep=sum(l['amount'] for t in rows if t['id'] in ('production_dep','admin_dep') for l in t['_key'])
    element_services=sum(l['amount'] for t in rows if t['id'] in ('overhead','allocation','selling') for l in t['_key'])
    element_other=sum(l['amount'] for t in rows if t['id']=='admin_cash' for l in t['_key'])
    reserve_change=sum(l['amount']*(1 if l['debit']=='642' else -1) for t in rows if t['id']=='allowance' for l in t['_key'])
    goods_cost=sum(l['amount'] for t in rows if t['id']=='goods_sale' for l in t['_key'] if l['debit']=='632')
    product_stock_change=p.get('155',0)
    notes={r['code']:'Không phát sinh trong bộ hồ sơ mô phỏng này.' for r in TEMPLATES['B09']['rows']}
    notes.update({
        'I':'Công ty CP Mây Tre Xanh; doanh nghiệp giả lập sản xuất và thương mại tại Việt Nam.',
        'I.1':'Công ty cổ phần chưa đại chúng, vốn góp bằng tiền; không có cổ phiếu ưu đãi.',
        'I.2':'Sản xuất, thương mại và dịch vụ.','I.3':'Sản phẩm mây tre; hàng hóa mua để bán; hợp đồng dịch vụ 3 tháng.',
        'I.4':'Chu kỳ sản xuất 1 tháng, dịch vụ 3 tháng.','I.5':'Tăng máy sản xuất và vốn góp mỗi kỳ theo hồ sơ được cung cấp.',
        'I.6':'Một pháp nhân, không có công ty con hoặc chi nhánh. Báo cáo riêng.','I.7':'10 người theo hồ sơ nhân sự giả lập.',
        'I.8':'So sánh tháng trước theo cùng chính sách; tháng 1 lấy số dư đầu năm, chưa có số kết quả năm 2025.',
        'I.9':'Quyền cổ tức phát sinh khi công ty không còn quyền từ chối thanh toán; chứng từ đã hoàn tất điều kiện.',
        'II':'Năm 2026; bài thực hành lập báo cáo từng tháng. Đây là số liệu học tập.','II.1':'01/01/2026–31/12/2026.',
        'II.2':'Đồng Việt Nam (VND); không thay đổi đồng tiền ghi sổ.',
        'III':'Áp dụng TT99/2025/TT-BTC và các nguyên tắc VAS có liên quan tới tình huống đã cung cấp.',
        'III.1':'TT99/2025/TT-BTC, có hiệu lực 01/01/2026; mẫu Phụ lụcIV.',
        'III.2':'Bộ hồ sơ phục vụ học ghi nhận, khóa sổ và trình bày; không là báo cáo thực tế đã kiểm toán hoặc đã nộp.',
        'IV':'Chính sách nhất quán, cơ sở dồn tích, hoạt động liên tục; bảng nghĩa vụ thuế do bộ phận thuế cung cấp.',
        'IV.1':'Ghi sổ VND, không chuyển đổi báo cáo từ đồng tiền khác.',
        'IV.2':'Hóa đơn USD: tỷ giá giao dịch thực tế 25.000+(tháng−1)×100VND/USD. Cuối kỳ dùng tỷ giá mua bán chuyển khoản trung bình 26.000+(tháng−1)×100; đánh giá cả hóa đơn cũ chưa thu.',
        'IV.3':'Tiền gửi trả cuối kỳ: lãi hợp đồng 3%/6 tháng, dự thu hàng tháng 0,5% gốc theo hồ sơ; không có khoản chiết khấu khác.',
        'IV.4':'Tiền gồm 111 và 112; tiền gửi 6 tháng ở 1281, không là tương đương tiền. Chuyển 111/112 không là dòng tiền hoạt động.',
        'IV.5':'Khoản 1281 theo dõi riêng gốc, lãi dự thu, ngày đáo hạn.','IV.6':'Theo từng khách, giữ USD; dự phòng 2293 ghi chênh lệch mức cần có cuối kỳ.',
        'IV.7':'Kê khai thường xuyên; giá xuất và giá thành theo bảng giá trị đã xác định trong hồ sơ, không tự suy ra đơn giá khi thiếu số lượng.',
        'IV.8':'Khấu hao đường thẳng: máy đầu năm 100 tháng, máy mới 120 tháng. Mua đầu tháng, đủ 1 tháng khấu hao theo giả định thời điểm đưa vào sử dụng.',
        'IV.11':'Mỗi hợp đồng bảo hiểm hưởng lợi 12 tháng, phân bổ đồng đều; tính cả hợp đồng mua các tháng trước.',
        'IV.12':'Tách từng người bán, ứng trước bên Nợ và nghĩa vụ bên Có; không bù giữa đối tượng.',
        'IV.13':'Cổ tức ghi 332 khi đã phát sinh nghĩa vụ, giảm 421; không là chi phí.',
        'IV.15':'Hợp đồng dịch vụ 3 tháng được nghiệm thu đều từng tháng;3387 chuyển 511 theo tiến độ toàn bộ hợp đồng còn hiệu lực.',
        'IV.17':'Thuế hoãn lại 347 theo bảng chênh lệch tạm thời chịu thuế đã soát xét; không tự dùng một thuế suất chung từ TT99.',
        'IV.18':'Các khoản vay đều đến hạn trong 12 tháng tới theo hợp đồng, trình bày ngắn hạn.',
        'IV.19':'Lãi vay phục vụ hoạt động, không có tài sản đủ điều kiện vốn hóa; ghi 635.',
        'IV.21':'Vốn tiền đã góp ghi 411; cổ tức theo nghị quyết; lợi nhuận kỳ hiện tại 4212 sau khóa sổ.',
        'IV.22':'Bán hàng khi điều kiện hồ sơ hoàn tất; dịch vụ theo phần nghiệm thu; lãi tiền gửi dự thu từng kỳ.',
        'IV.23':'Giảm giá có hồ sơ điều chỉnh doanh thu 521 và thuế; không giả định có hàng trả lại.',
        'IV.24':'632 theo giá trị xuất kho; sản xuất tập hợp 621/622/627→154→155 rồi 632 khi bán.',
        'IV.25':'635 gồm lãi vay; đánh giá ngoại tệ và lãi gửi phát sinh515 trong hồ sơ hiện tại.',
        'IV.26':'Bán hàng 641; quản lý 642 gồm lương, khấu hao, phân bổ và điều chỉnh dự phòng.',
        'IV.28':'8211/3334 thuế hiện hành và 8212/347 hoãn lại theo bảng nghĩa vụ. TT99 không quyết định nghĩa vụ thuế.',
        'IV.29':'Công nợ tách theo đối tượng; VAT đủ điều kiện được khấu trừ cuối kỳ bằng bút toán 3331/133 theo bảng. Lưu chứng từ, sổ chi tiết và dấu vết chỉ ghi một lần.',
        'V':'Xem sổ chi tiết và bảng dưới đây; mọi số đều lấy từ các bút toán đã được ghi.',
        'V.1':f'Tiền mặt{n(b("111"))}; tiền gửi không kỳ hạn{n(b("112"))}; tổng{n(b("111")+b("112"))}.',
        'V.2':f'Tiền gửi kỳ hạn, gồm lãi dự thu: {n(b("1281"))}; đối chiếu bảng từng hợp đồng.',
        'V.3':f'Phải thu khách{n(v["customer_debit"])}; khách trả trước{n(v["customer_advance"])}. Sổ USD gồm{sum(r["original"] for r in dt["foreign_currency"])}USD.',
        'V.6':f'Dự phòng phải thu khó đòi{n(-b("2293"))}; khoản nợ vẫn giữ trên 131, chưa xóa nợ.',
        'V.7':'; '.join(f'{c.CHART[a]}: {n(b(a))}' for a in ('152','154','155','156')),
        'V.9':f'Nguyên giá{n(b("211"))}; hao mòn{n(-b("214"))}; giá trị còn lại{n(b("211")+b("214"))}. Xem bảng từng TSCĐ.',
        'V.14':f'Chi phí bảo hiểm chờ phân bổ{n(b("242"))}; xem bảng từng hợp đồng 12 kỳ.',
        'V.16':f'Dư vay ngắn hạn{n(-b("341"))}; không bù với tiền gửi ngân hàng.',
        'V.17':f'Phải trả người bán{n(v["supplier_credit"])}; ứng trước{n(v["supplier_advance"])}; xem từng đối tượng.',
        'V.18':f'Cổ tức chưa trả{n(-b("332"))}.','V.19':f'GTGT đầu vào{n(b("1331")+b("1332"))}; GTGT đầu ra phải nộp{n(-b("3331"))}; TNDN hiện hành phải nộp{n(-b("3334"))}.',
        'V.21':f'Lương còn phải trả{n(-b("334"))}; bảo hiểm còn phải nộp{n(-b("3383"))}.',
        'V.22':f'Doanh thu chờ phân bổ{n(-b("3387"))}; xem hợp đồng dịch vụ 3 kỳ.',
        'V.26':f'Tài sản thuế hoãn lại{n(b("243"))}; nghĩa vụ hoãn lại{n(-b("347"))}.',
        'V.27':f'Vốn góp{n(-b("411"))}; lợi nhuận năm trước{n(-b("4211"))}, năm nay sau bút toán đã ghi{n(-b("4212"))}.',
        'V.29':'Lãi đánh giá lại phải thu ghi 515, không vào 413 trong bộ hồ sơ này.',
        'V.32':'Mọi giá trị thuế, lương và giá xuất kho đã cho có căn cứ riêng; người học thực hành kế toán bằng VND.',
        'VII':'Kết quả kỳ hiện tại tính từ phát sinh trước kết chuyển.',
        'VII.1':n(-p.get('511',0)),'VII.2':n(p.get('521',0)),'VII.3':n(p.get('632',0)),
        'VII.5':n(-p.get('515',0)),'VII.6':n(p.get('635',0)),
        'VII.9':f'Bán hàng{n(p.get("641",0))}; quản lý{n(p.get("642",0))}.',
        'VII.10':f'Yếu tố phát sinh phục vụ sản xuất, bán hàng và quản lý: nguyên liệu{n(element_materials)}; nhân công và khoản doanh nghiệp trích{n(element_staff)}; khấu hao{n(element_dep)}; dịch vụ mua ngoài (phân xưởng, bảo hiểm phân bổ, tiếp thị){n(element_services)}; chi quản lý khác bằng tiền{n(element_other)}. Điều chỉnh dự phòng không bằng tiền{n(reserve_change)}; giá vốn hàng hóa mua để bán{n(goods_cost)} trình bày thêm để đối chiếu chi phí. Sản phẩm tồn kho tăng/giảm{n(product_stock_change)}, giải thích phần chi sản xuất chưa thành giá vốn. Không cộng 632 trùng với 621/622/627.',
        'VII.11':f'Thuế hiện hành{n(p.get("8211",0))}; hoãn lại{n(p.get("8212",0))}.',
        'VIII':'Phương pháp trực tiếp; loại chuyển tiền nội bộ, khấu hao, phân bổ, đánh giá ngoại tệ, dự thu và kết chuyển.',
        'VIII.2':'Khấu hao, dự phòng, dự thu lãi, đánh giá ngoại tệ, chi phí thuế chưa trả và giao dịch mua chịu không có dòng tiền tại thời điểm ghi nhận.',
        'VIII.3':n(moves.get('341',{}).get('credit',0)),'VIII.4':n(moves.get('341',{}).get('debit',0)),
        'IX':'Giả định hồ sơ hoàn chỉnh, hoạt động liên tục; không có sự kiện điều chỉnh sau ngày kỳ báo cáo được cung cấp.',
        'IX.3':'Góp vốn và cổ tức với cổ đông theo hồ sơ nghị quyết, đã phản ánh 411/421/332.',
        'IX.5':'Số B01 so với cuối tháng trước; B02/B03 so với tháng trước, tháng 1 chưa có số 2025.',
        'IX.6':'Theo hồ sơ giả lập ban giám đốc xác nhận hoạt động liên tục; người học vẫn cần kiểm tra nếu tình huống thay đổi.',
        'IX.7':'Tuổi thọ tài sản, phần nghiệm thu, dự phòng và thuế hoãn lại theo bảng giả định đã soát xét trong hồ sơ.',
        'X':'Giữ nguyên mã và nhãn mẫu TT99; giao diện thêm cột tiến độ và so sánh tháng phục vụ học. Chỉ tiêu không phát sinh bằng 0; EPS không áp dụng với hồ sơ doanh nghiệp chưa đại chúng này.'})
    return notes


def public(book):
    from . import accounting_company as c
    current=numbers(book);previous=None
    if book['period']>1:previous=numbers(dict(period=book['period']-1,at=10**6))
    elif book['at']>=0:previous={'B01':numbers(dict(period=1,at=0))['B01']}
    result={}
    for fid in ('B01','B02','B03'):
        result[fid]=dict(title=TEMPLATES[fid]['title'],unit='VND',comparison='Cuối tháng trước / đầu năm' if fid=='B01' else 'Tháng trước',
                         rows=[dict(**r,value=current[fid][r['code']],previous=previous.get(fid,{}).get(r['code']) if previous else None) for r in TEMPLATES[fid]['rows']])
    notes=note_values(book)
    result['B09']=dict(title=TEMPLATES['B09']['title'],rows=[dict(**r,text=notes[r['code']]) for r in TEMPLATES['B09']['rows']])
    result['source_url']=TEMPLATES['source_url']
    result['status']='Đã khóa sổ' if book['at']>=len(c.tasks(book)) else 'Đang ghi sổ · chỉ gồm nghiệp vụ đã làm'
    return result
