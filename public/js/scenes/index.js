/** Which workplace scene each career stands in, and the words that go with
 * it (hotspot labels, top-bar labels). Scene kinds live in
 * public/js/scenes/<kind>.js and load on demand; until one has loaded (or
 * for an unknown career) the storefront `shop` scene is used. */
import shop from './shop.js';

export const KIND_OF={
  // Each storefront career has its own scene (falls back to the shared 'shop' storefront until it loads).
  milk_tea:'teabar',cafe_bakery:'cafe',restaurant:'kitchen',grocery:'minimart',florist:'flowershop',mother_baby:'babyshop',pharmacy:'drugstore',
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
  // Stage task card (app.js taskCards): closed-for-the-day line, open-but-idle card, next-task button.
  idle_line:'Khách sắp ghé rồi.',open_hint:'Chuẩn bị một chút rồi mở cửa nhé.',free_eyebrow:'Quầy đang rảnh',free_title:'Hết khách rồi!',
  free_more:'Đón thêm khách hoặc khép ca hôm nay.',more_btn:'Đón thêm một khách',none_waiting:'Chưa có khách nào đang chờ',next_btn:'Đón khách tiếp theo',
  people_sub:'Những người bạn gặp quanh tiệm.',feed_sub:'Lời nhắn và đánh giá quanh tiệm.',
};
const KIND_WORDS={
  shop:{},
  teabar:{shelf:'Hũ topping',evidence:'Màn hình đơn',counter:'Quầy nhận ly',cat_line:'Mrrr… cho Mướp một viên trân châu được không?'},
  cafe:{shelf:'Tủ bánh',evidence:'Phiếu order',counter:'Quầy tính tiền',warehouse:'Kho bột',store:'KHO BỘT',cat_line:'Mrrr… thơm mùi bánh mới ra lò quá!'},
  kitchen:{shelf:'Kệ gia vị & topping',evidence:'Dây phiếu gọi món',counter:'Quầy ra món',warehouse:'Kho lạnh',cat_line:'Mrrr… nồi nước dùng thơm quá đi.'},
  minimart:{shelf:'Kệ hàng tạp hóa',evidence:'Sổ ghi nợ',counter:'Cân & tính tiền',cat_line:'Mrrr… cô Ba ơi cho con xin miếng khô mực.'},
  flowershop:{shelf:'Kệ xô hoa',evidence:'Sổ đặt hoa',counter:'Quầy tính tiền',warehouse:'Tủ mát hoa',cat_line:'Mrrr… hoa hồng thơm nhưng gai quá.'},
  babyshop:{shelf:'Kệ thú bông',evidence:'Bỉm & sữa theo cỡ',counter:'Quầy thanh toán',cat_line:'Mrrr… thú bông này mềm ghê.'},
  drugstore:{shelf:'Kệ hộp theo mã',evidence:'Khay & phiếu',counter:'Quầy tư vấn',warehouse:'Kho thuốc',cat_line:'Mrrr… nằm trên tủ lạnh mát ghê.'},
  service:{cat_line:'Mrrr… hôm nay có ai ghé làm đẹp không?',store:'VẬT TƯ',ledger:'SỔ THU CHI',open_sign:'ĐANG NHẬN KHÁCH',idle_line:'Khách hẹn sắp tới.',warehouse:'Kho vật tư',shelf:'Tủ dụng cụ',evidence:'Sổ hẹn & phiếu',counter:'Quầy thanh toán'},
  classroom:{cat_line:'Mrrr… hôm nay lớp mình học gì thế?',rating:'phụ huynh',till:'Quỹ lớp',door_open:'Tan lớp',door_closed:'Vào lớp',open_sign:'ĐANG HỌC',closed_sign:'ĐÃ TAN LỚP',
    shelf:'Góc học liệu',evidence:'Sổ liên lạc',counter:'Bàn giáo viên',warehouse:'Tủ đồ dùng',finance:'Sổ quỹ lớp',property:'Phòng học',ledger:'SỔ LỚP',store:'TỦ ĐỒ',
    idle_line:'Học sinh sắp vào lớp.',open_hint:'Chuẩn bị một chút rồi vào lớp nhé.',free_eyebrow:'Lớp đang nghỉ giữa giờ',free_title:'Hết tiết rồi!',
    free_more:'Nhận thêm một tiết hoặc tan lớp hôm nay.',people_sub:'Những người bạn gặp ở trường.',feed_sub:'Lời nhắn và phản hồi quanh lớp học.',more_btn:'Nhận thêm một tiết',none_waiting:'Chưa có tiết nào đang chờ',next_btn:'Vào tiết tiếp theo'},
  office:{cat_line:'Mrrr… bàn phím ấm quá, cho mèo nằm nhờ nhé.',security:'An ninh tòa nhà',rating:'phản hồi',till:'Quỹ bộ phận',door_open:'Tan làm',door_closed:'Vào ca',open_sign:'ĐANG LÀM VIỆC',closed_sign:'ĐÃ TAN LÀM',
    shelf:'Kệ hồ sơ',evidence:'Bản gốc & chứng cứ',counter:'Phòng trưởng phòng',warehouse:'Tủ hồ sơ',finance:'Sổ chi phí',property:'Văn phòng',ledger:'SỔ CÔNG VIỆC',store:'HỒ SƠ',
    idle_line:'Hồ sơ mới đang chờ trên bàn.',open_hint:'Chuẩn bị một chút rồi vào ca nhé.',free_eyebrow:'Bàn làm việc đang trống',
    people_sub:'Những người bạn gặp ở nơi làm việc.',feed_sub:'Lời nhắn và phản hồi quanh văn phòng.'},
  farm:{cat_line:'Mrrr… nắng đẹp thế này, rau lớn nhanh lắm.',till:'Quỹ nông trại',door_open:'Nghỉ tay',door_closed:'Ra vườn',open_sign:'ĐANG LÀM VƯỜN',closed_sign:'NGHỈ TAY',
    shelf:'Kệ hạt giống',evidence:'Nhật ký canh tác',board:'Chuyện xóm',security:'Canh vườn',counter:'Bàn đóng hàng',warehouse:'Nhà kho',property:'Đất trại',ledger:'SỔ TRẠI',store:'NHÀ KHO',
    idle_line:'Vườn đang chờ bạn.',open_hint:'Chuẩn bị một chút rồi ra vườn nhé.',free_eyebrow:'Vườn đang yên',free_title:'Hết đơn rồi!',
    free_more:'Nhận thêm đơn hoặc nghỉ tay hôm nay.',people_sub:'Những người bạn gặp quanh trại.',feed_sub:'Lời nhắn và đánh giá quanh trại.',more_btn:'Nhận thêm một đơn',none_waiting:'Chưa có đơn nào đang chờ',next_btn:'Nhận đơn tiếp theo'},
  street:{cat_line:'Mrrr… đi đường cẩn thận nhé.',till:'Quỹ',door_open:'Nghỉ',door_closed:'Bắt đầu chạy',open_sign:'ĐANG CHẠY',closed_sign:'ĐÃ NGHỈ',
    shelf:'Kệ hàng',evidence:'Bảng lộ trình',counter:'Quầy nhận',warehouse:'Kho hàng',property:'Điểm tập kết',ledger:'SỔ CHUYẾN',store:'KHO',
    idle_line:'Đơn mới sắp tới.',open_hint:'Chuẩn bị một chút rồi lên đường nhé.',free_eyebrow:'Chưa có đơn mới',free_title:'Hết đơn rồi!',
    free_more:'Nhận thêm đơn hoặc nghỉ hôm nay.',people_sub:'Những người bạn gặp trên đường.',feed_sub:'Lời nhắn và đánh giá trên đường.',more_btn:'Nhận thêm một đơn',none_waiting:'Chưa có đơn nào đang chờ',next_btn:'Nhận đơn tiếp theo'},
  lodging:{cat_line:'Mrrr… lò sưởi ấm quá, khách có lạnh không?',till:'Ví của homestay',door_closed:'Mở quầy',shelf:'Bảng chìa khóa',evidence:'Lịch phòng',counter:'Quầy trả phòng',warehouse:'Kho buồng phòng',pet:'Chơi với Mướp bên lò sưởi',door_open:'Khép quầy',open_sign:'ĐANG ĐÓN KHÁCH',closed_sign:'HẸN BẠN LẦN SAU',security:'An ninh nhà nghỉ',property:'Nhà & vườn',ledger:'SỔ KHÁCH',store:'KHO',
    idle_line:'Khách sắp tới nhận phòng.',open_hint:'Chuẩn bị một chút rồi mở quầy nhé.',free_eyebrow:'Quầy lễ tân đang rảnh',people_sub:'Những người bạn gặp quanh homestay.',feed_sub:'Lời nhắn và đánh giá quanh homestay.'},
};
const CAREER_WORDS={
  milk_tea:{warehouse:'Kho nguyên liệu'},
  delivery:{shelf:'Kệ bưu kiện',counter:'Quầy bưu cục',evidence:'Bản đồ tuyến giao',warehouse:'Lồng hàng chờ giao',finance:'Sổ tiền thu hộ',property:'Bưu cục Mây Chiều',open_sign:'ĐANG NHẬN ĐƠN',closed_sign:'TẠM NGHỈ GIAO'},
  tour_guide:{shelf:'Bưu thiếp & bản đồ',counter:'Điểm hẹn đoàn',evidence:'Bảng lộ trình',warehouse:'Hành trang',door_open:'Kết thúc chuyến',door_closed:'Xuất phát',finance:'Sổ quỹ đoàn',property:'Điểm hẹn Mây Lang Thang',open_sign:'ĐANG ĐÓN ĐOÀN',closed_sign:'HẸN CHUYẾN SAU',ledger:'SỔ ĐOÀN',
    idle_line:'Đoàn khách sắp tới điểm hẹn.',open_hint:'Chuẩn bị một chút rồi xuất phát nhé.',free_eyebrow:'Điểm hẹn đang rảnh',free_title:'Hết đoàn rồi!',
    free_more:'Đón thêm đoàn hoặc kết thúc chuyến hôm nay.',more_btn:'Đón thêm một đoàn',none_waiting:'Chưa có đoàn nào đang chờ',next_btn:'Đón đoàn tiếp theo'},
  customer_care:{counter:'Trưởng ca',evidence:'Chứng cứ · phối hợp',idle_line:'Khách sắp gọi tới rồi.'},
  pet_care:{shelf:'Kệ đồ thú cưng',evidence:'Phiếu nhận thú cưng',counter:'Quầy nhận bé',cat_line:'Mrrr… hôm nay có bạn bốn chân nào ghé không?'},repair:{shelf:'Tường dụng cụ',counter:'Quầy nhận máy',evidence:'Phiếu nhận máy',cat_line:'Mrrr… cái quạt kia kêu to quá.'},salon:{shelf:'Kệ thuốc nhuộm'},
};
export const wordsFor=career=>({...BASE,...KIND_WORDS[kindOf(career)],...CAREER_WORDS[career]});

const loaded={shop},waiting={},listener={};
function load(kind){
  return waiting[kind]??=import(`./${kind}.js`).then(m=>{loaded[kind]=m.default;return m.default;})
    .catch(error=>{console.warn('Chưa có cảnh',kind,error);loaded[kind]=shop;return shop;})
    .then(scene=>{listener[kind]?.();delete listener[kind];return scene;});
}
/** The scene module for a career, or `shop` while its kind is still loading.
 * `onReady` runs once when the real one arrives (the latest caller wins; the
 * draw loop asks every frame, so nothing piles up). */
export function sceneFor(career,onReady){
  const kind=kindOf(career);
  if(loaded[kind])return loaded[kind];
  if(onReady)listener[kind]=onReady;
  load(kind);
  return shop;
}
/** Load every scene kind now (startup, tools) so no career flashes the shop. */
export const loadAllScenes=()=>Promise.all([...new Set(Object.values(KIND_OF))].filter(k=>!loaded[k]).map(load));
