/** 🍱 Căn tin trường Tiểu học Phố Mây: the whole counter on one screen (counter_kit.js). Morning rush and recess before
 * the school bell (🥁 the beats left), the class teachers' lunch trays after 🧪 Lưu mẫu (game/careers/canteen.py). */
import {counterKit} from './counter_kit.js';

// The dock sits in the exported literal so the menu inventory (tests/isometric-feature-parity.mjs) can read it.
export default {...counterKit({
  id:'canteen',prefix:'ct_',icon:'🍱',place:'Căn tin trường Tiểu học Phố Mây',
  tray:'Khay',trayIcon:'🍽️',sample:true,
  serve:t=>t.phase==='trua'?'Giao cơm cho lớp':'Giao cho bé',
  deskWhere:'Chuyện ở căn tin',shelvesTitle:'🛒 Quầy căn tin',moreLabel:'Đón thêm',callNext:'Mời bạn tiếp theo',
  waitLine:'Học trò sắp chạy tới quầy. Xếp sẵn xôi, bánh mì, nước cho kịp trống.',
  closedLine:'Căn tin chưa mở cửa: bắt đầu ngày để đón học trò.',
  trayEmpty:'Chạm món trên kệ để bỏ vào khay cho bé.',
  notesTitle:'Sổ tay căn tin',
}),
  dock:[['inventory','box','Kho','Nhập đồ ăn, nước uống'],['car:notes','book','Sổ tay căn tin','Bảng giá, dị ứng, lưu mẫu, giờ trống'],['car:intro','question','Giới thiệu nghề','Kịp trống, đúng món, đúng giá']],
};
