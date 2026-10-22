/** ✏️ Tiệm văn phòng phẩm Bút Mây: the whole shop on one screen (counter_kit.js). Notebooks, pens, school tools and
 * bags on the shelves, covering, labels and photocopies as services that use their material
 * (game/careers/stationery.py). */
import {counterKit} from './counter_kit.js';

// The dock sits in the exported literal so the menu inventory (tests/isometric-feature-parity.mjs) can read it.
export default {...counterKit({
  id:'stationery',prefix:'vp_',icon:'✏️',place:'Tiệm văn phòng phẩm Bút Mây',
  tray:'Giỏ',trayIcon:'🧺',sample:false,
  serve:'Giao cho khách',
  deskWhere:'Chuyện ở tiệm',shelvesTitle:'🛒 Kệ hàng',moreLabel:'Đón khách',callNext:'Mời khách vào tiệm',
  waitLine:'Tiệm đang vắng. Sắp lại kệ vở, châm giấy cho máy photo.',
  closedLine:'Tiệm chưa mở cửa: bắt đầu ngày để đón khách.',
  trayEmpty:'Chạm món trên kệ để bỏ vào giỏ cho khách.',
  notesTitle:'Sổ tay tiệm Bút Mây',
}),
  dock:[['inventory','box','Kho','Nhập vở, bút, giấy'],['car:notes','book','Sổ tay tiệm Bút Mây','Bảng giá, vở theo lớp, bọc vở, photo'],['car:intro','question','Giới thiệu nghề','Đủ món, đúng loại vở']],
};
