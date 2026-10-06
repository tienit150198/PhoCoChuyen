"""Profession-specific equipment. Effects are server-derived from paid ownership."""
NAMES = {
 'mother_baby':'Bộ chia khay và máy in nhãn', 'pharmacy':'Máy quét lô và khay kiểm phiếu',
 'accounting':'Bộ máy quét chứng từ', 'customer_care':'Bàn phím và bộ tra cứu hồ sơ',
 'teacher':'Bộ học liệu và máy in bài', 'tour_guide':'Bộ đàm và bộ soạn tuyến',
 'milk_tea':'Bộ định lượng và linh kiện quầy pha', 'restaurant':'Bộ bếp và giỏ trụng cải tiến',
 'cafe_bakery':'Bộ bơm máy pha và quạt lò', 'florist':'Bộ kéo và giá xử lý hoa',
 'grocery':'Máy quét hàng và bộ chia kệ', 'repair':'Bộ dụng cụ và máy chẩn đoán',
 'farm':'Bộ tưới và dụng cụ thu hoạch', 'delivery':'Bộ truyền động và dẫn đường',
 'homestay':'Xe dụng cụ và bộ dọn phòng', 'pet_care':'Bộ vòi tắm và máy sấy',
 'salon':'Bộ kéo và máy hấp tóc', 'corp_accounting':'Máy quét hóa đơn và bộ xử lý sổ',
 'tax_payroll':'Bộ xử lý bảng lương', 'group_accounting':'Bộ đối soát và máy trạm',
 'clothing':'Động cơ máy may và bàn cắt', 'pet_shop':'Bộ chia thức ăn và xe hàng',
 'tra_da':'Bình ủ và bộ định lượng', 'fruit':'Bộ dao và máy ép cải tiến',
 'garbage':'Xe dụng cụ và bộ gắp rác', 'drain':'Máy hút và bộ đầu thông',
 'homemaker':'Bộ đồ dùng và xe dọn nhà', 'ice_cream':'Bộ giữ lạnh và muỗng định lượng',
 'nail':'Bộ máy và khay dụng cụ nail', 'pagoda':'Xe dụng cụ và bộ chuẩn bị lễ',
 'pho':'Bếp giữ nhiệt và bộ trụng phở', 'com':'Nồi cơm và bếp nướng cải tiến',
 'photobooth':'Bộ đèn và linh kiện máy ảnh', 'giupviec':'Máy hút bụi và bộ lau nhà',
 'naucom':'Bộ nồi và bếp gia đình', 'babysitter':'Bộ chuẩn bị bữa và đồ chăm bé',
 'pilot':'Bộ thiết bị hỗ trợ mặt đất', 'flight_attendant':'Xe phục vụ và bộ chia suất',
 'hr_admin':'Máy quét và bộ xử lý hồ sơ', 'secretary':'Bộ máy trạm và thiết bị văn phòng',
 'it_helpdesk':'Bộ chẩn đoán và linh kiện dự phòng',
 'railway':'Bộ cờ đèn và tay quay cần chắn',
}
RATES=(100,115,135,160)
PRICES=(0,90,220,480)

def item_id(career,tier):
    return f'workgear_{career}_{tier}'

def catalogue():
    out=[]
    for career,name in NAMES.items():
        for tier in range(1,4):
            description=f'Nhân viên xử lý công việc nhanh hơn {RATES[tier]-100}%. Các bậc không cộng dồn.'
            if career=='delivery': description+=' Giảm thời gian chạy tuyến và tăng tốc xe khi tự lái.'
            if career=='cafe_bakery': description+=' Tăng nhịp chiết cà phê, đánh sữa và lò nướng cho lượt bắt đầu mới.'
            out.append(dict(id=item_id(career,tier),name=f'{name} · Bậc {tier}',icon='tool',
                            price=PRICES[tier],kind='equipment',min_level=1,careers=[career],
                            description=description,gear_tier=tier,gear_rate=RATES[tier],
                            requires=item_id(career,tier-1) if tier>1 else None))
    return out

ITEMS={x['id']:x for x in catalogue()}

def factor(c):
    return max((ITEMS[k]['gear_rate'] for k in c.get('upgrades',[]) if k in ITEMS),default=100)/100

def public(c):
    f=factor(c)
    return dict(factor=f,percent=round((f-1)*100),tier=RATES.index(round(f*100)))
