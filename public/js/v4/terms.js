/** Each career's own words for the screens every career shares (game/career_voice.py, sent in the catalogue as
 * `catalogue[i].terms`): "Sổ chùa" instead of "Sổ tiệm", "Xác nhận việc trực ban", "Ban công quả"… A shop keeps
 * today's words. SHOP is the fallback while the catalogue is not in (or an older catalogue without `terms`); it must
 * equal career_voice.SHOP (tests/test_career_words.py). */
export const SHOP={"commerce":true,"place":"tiệm","self":"tiệm","people":"khách","who":"bạn","owner":"chủ tiệm","served":"khách đã phục vụ","record":"phiếu","review":"đánh giá","reply":"trả lời","books":"Sổ tiệm","rail_in":"Trong tiệm","confirm":"Xác nhận việc của tiệm","end_title":"Khép ca hôm nay?","end_text":"Lương, điện nước và tiền thuê ghi vào sổ tiệm để bạn trả sau.","team":"Đội của tiệm","hire_board":"Bảng tìm người phụ tiệm","hire":"Mời về tiệm","calm":"Hiên tiệm đang yên.","security":"Chăm chút an ninh của tiệm","revenue":"Doanh thu nghề","income":"doanh thu","tip":"Khách quen boa thêm","fund":"Quỹ tiệm","daily":"Quán đang chờ bạn mở cửa, khách quen đang chờ. Mở ca hôm nay nhé!","host":"Chủ tiệm","by_owner":"Chủ tiệm phục vụ","by_staff":"Nhân viên phục vụ","rate":"Chấm quán","invite_label":"Mời quay lại","sorry_label":"Xin lỗi + bù đắp","offer_field":"Bù đắp","placeholder":"Cảm ơn, xin lỗi nếu cần, và nói rõ tiệm sẽ làm gì…","offers":{"drink":"Quà nhỏ · 6 xu","gift":"Voucher · 10 xu","refund":"Hoàn 20 xu"}};

let source=()=>null;
/** app.js hands over where the catalogue lives (api.content.catalogue), once at boot. */
export const termsSource=fn=>{source=typeof fn==='function'?fn:()=>null;};

/** The career's row of words (SHOP for an unknown career or before the catalogue is in). */
export function terms(career){
  let list=null;
  try{list=source();}catch{list=null;}
  const row=Array.isArray(list)?list.find(c=>c&&c.id===career):null;
  return row&&row.terms&&typeof row.terms==='object'?row.terms:SHOP;
}
/** One word: T('pagoda','books') → "Sổ chùa". A missing key gives the shop word. */
export const T=(career,key)=>{const v=terms(career)[key];return v==null?SHOP[key]:v;};
/** A shop (true) or a job whose shared screens must not say tiệm / quán / phục vụ (false). */
export const isShop=career=>terms(career).commerce!==false;
/** The bù đắp a career can give: [[id,label]…] (police: none). */
export const offersOf=career=>Object.entries(terms(career).offers||SHOP.offers).filter(([,l])=>l);
