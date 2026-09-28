/** Which workplace scene each career stands in, and the words that go with
 * it (hotspot labels, top-bar labels). Scene kinds live in
 * public/js/scenes/<kind>.js and load on demand; until one has loaded (or
 * for an unknown career) the storefront `shop` scene is used. */
import shop from './shop.js';

export const KIND_OF={
  milk_tea:'shop',cafe_bakery:'shop',restaurant:'shop',grocery:'shop',florist:'shop',mother_baby:'shop',pharmacy:'shop',
  salon:'service',pet_care:'service',repair:'service',
  teacher:'classroom',
  accounting:'office',corp_accounting:'office',tax_payroll:'office',group_accounting:'office',customer_care:'office',
  farm:'farm',
  delivery:'street',tour_guide:'street',
  homestay:'lodging',
};
export const kindOf=career=>KIND_OF[career]||'shop';

const BASE={
  rating:'đánh giá',till:'Ví của tiệm',door_open:'Khép một ngày',door_closed:'Mở cửa tiệm',open_sign:'ĐANG MỞ',closed_sign:'HẸN GẶP LẠI',
  shelf:'Kệ hàng xinh',evidence:'Đối chiếu yêu cầu',counter:'Kiểm & bàn giao',warehouse:'Kho sau tiệm',
  board:'Chuyện phố',cat_line:'Mrrr… hôm nay tiệm có thêm bạn mới không?',finance:'Sổ thu chi',property:'Mặt bằng của tiệm',security:'An ninh khu phố',pet:'Chơi với Mướp',ledger:'SỔ TIỆM',store:'KHO',
};
const KIND_WORDS={
  shop:{},
  service:{cat_line:'Mrrr… hôm nay có ai ghé làm đẹp không?',store:'VẬT TƯ',ledger:'SỔ THU CHI',open_sign:'ĐANG NHẬN KHÁCH',warehouse:'Kho vật tư',shelf:'Tủ dụng cụ',evidence:'Sổ hẹn & phiếu',counter:'Quầy thanh toán'},
  classroom:{cat_line:'Mrrr… hôm nay lớp mình học gì thế?',rating:'phụ huynh',till:'Quỹ lớp',door_open:'Tan lớp',door_closed:'Vào lớp',open_sign:'ĐANG HỌC',closed_sign:'ĐÃ TAN LỚP',
    shelf:'Góc học liệu',evidence:'Sổ liên lạc',counter:'Bàn giáo viên',warehouse:'Tủ đồ dùng',finance:'Sổ quỹ lớp',property:'Phòng học',ledger:'SỔ LỚP',store:'TỦ ĐỒ'},
  office:{cat_line:'Mrrr… bàn phím ấm quá, cho mèo nằm nhờ nhé.',rating:'phản hồi',till:'Quỹ bộ phận',door_open:'Tan làm',door_closed:'Vào ca',open_sign:'ĐANG LÀM VIỆC',closed_sign:'ĐÃ TAN LÀM',
    shelf:'Kệ hồ sơ',evidence:'Bản gốc & chứng cứ',counter:'Phòng trưởng phòng',warehouse:'Tủ hồ sơ',finance:'Sổ chi phí',property:'Văn phòng',ledger:'SỔ CÔNG VIỆC',store:'HỒ SƠ'},
  farm:{cat_line:'Mrrr… nắng đẹp thế này, rau lớn nhanh lắm.',till:'Quỹ nông trại',door_open:'Nghỉ tay',door_closed:'Ra vườn',open_sign:'ĐANG LÀM VƯỜN',closed_sign:'NGHỈ TAY',
    shelf:'Kệ hạt giống',evidence:'Nhật ký canh tác',board:'Chuyện xóm',security:'Canh vườn',counter:'Bàn đóng hàng',warehouse:'Nhà kho',property:'Đất trại',ledger:'SỔ TRẠI',store:'NHÀ KHO'},
  street:{cat_line:'Mrrr… đi đường cẩn thận nhé.',till:'Quỹ',door_open:'Nghỉ',door_closed:'Bắt đầu chạy',open_sign:'ĐANG CHẠY',closed_sign:'ĐÃ NGHỈ',
    shelf:'Kệ hàng',evidence:'Bảng lộ trình',counter:'Quầy nhận',warehouse:'Kho hàng',property:'Điểm tập kết',ledger:'SỔ CHUYẾN',store:'KHO'},
  lodging:{cat_line:'Mrrr… lò sưởi ấm quá, khách có lạnh không?',till:'Ví của homestay',door_closed:'Mở quầy',shelf:'Bảng chìa khóa',evidence:'Lịch phòng',counter:'Quầy trả phòng',warehouse:'Kho buồng phòng',pet:'Chơi với Mướp bên lò sưởi',door_open:'Khép quầy',open_sign:'ĐANG ĐÓN KHÁCH',closed_sign:'HẸN BẠN LẦN SAU',security:'An ninh nhà nghỉ',property:'Nhà & vườn',ledger:'SỔ KHÁCH',store:'KHO'},
};
const CAREER_WORDS={
  milk_tea:{warehouse:'Kho nguyên liệu'},
  delivery:{shelf:'Kệ bưu kiện',counter:'Quầy bưu cục',evidence:'Bản đồ tuyến giao',warehouse:'Lồng hàng chờ giao',finance:'Sổ tiền thu hộ',property:'Bưu cục Mây Chiều',open_sign:'ĐANG NHẬN ĐƠN',closed_sign:'TẠM NGHỈ GIAO'},
  tour_guide:{shelf:'Bưu thiếp & bản đồ',counter:'Điểm hẹn đoàn',evidence:'Bảng lộ trình',warehouse:'Hành trang',door_open:'Kết thúc chuyến',door_closed:'Xuất phát',finance:'Sổ quỹ đoàn',property:'Điểm hẹn Mây Lang Thang',open_sign:'ĐANG ĐÓN ĐOÀN',closed_sign:'HẸN CHUYẾN SAU',ledger:'SỔ ĐOÀN'},
  customer_care:{counter:'Trưởng ca',evidence:'Chứng cứ · phối hợp'},
  pet_care:{shelf:'Kệ đồ thú cưng',evidence:'Phiếu nhận thú cưng',counter:'Quầy nhận bé',cat_line:'Mrrr… hôm nay có bạn bốn chân nào ghé không?'},repair:{shelf:'Tường dụng cụ',counter:'Quầy nhận máy',evidence:'Phiếu nhận máy',cat_line:'Mrrr… cái quạt kia kêu to quá.'},salon:{shelf:'Kệ thuốc nhuộm'},
};
export const wordsFor=career=>({...BASE,...KIND_WORDS[kindOf(career)],...CAREER_WORDS[career]});

const loaded={shop},waiting={};
/** The scene module for a career, or `shop` while its kind is still loading.
 * `onReady` runs once the real one arrives (to redraw). */
export function sceneFor(career,onReady){
  const kind=kindOf(career);
  if(loaded[kind])return loaded[kind];
  if(!waiting[kind])waiting[kind]=import(`./${kind}.js`).then(m=>{loaded[kind]=m.default;return m.default;}).catch(error=>{console.warn('Chưa có cảnh',kind,error);loaded[kind]=shop;return shop;});
  waiting[kind].then(()=>onReady?.());
  return shop;
}
