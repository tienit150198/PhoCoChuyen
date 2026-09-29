/** Guide content: short Vietnamese lines + real screenshots (public/icons/tutorial,
* served by nginx with the other icons). Marks are [x%, y%, n, badge side?] over the picture.
* Pictures: real 390×844 phone screenshots, cropped, WebP under 60 KB each. */
export const IMG='/icons/tutorial/';

/** "Cách chơi": three cards (what a new player touches first). `art` = an inline illustration, `pic` = a screenshot, points = [mark number (0 = none), words]. */
export const OVERVIEW=[
  {id:"street",emoji:"🏘️",title:"Khu phố & Hành trình",pic:{img:"ov-street.webp",w:720,h:554,marks:[[75.9, 29.3, 1]]},points:[[1, "Bấm để mở Hành trình"], [0, "Một đời, nhiều nghề"]]},
  {id:"day",emoji:"☀️",title:"Một ngày làm việc",art:"day",pic:{img:"ov-day.webp",w:720,h:384,marks:[[80.0, 37.0, 1], [30.3, 83.2, 2]]},points:[[1, "Làm tiếp việc trước mắt"], [2, "Tự tay làm"]]},
  {id:"money",emoji:"💰",title:"Ví và quỹ tiệm",pic:{img:"ov-money.webp",w:720,h:720,marks:[[50.0, 23.1, 1], [50.0, 90.5, 2]]},points:[[1, "Ví: tiền của bạn"], [2, "Quỹ tiệm: tiền của tiệm"], [0, "Tiền phòng trừ từ ví"]]},
];

/** "Cách làm": 4 steps for the places new players start in, one picture per step. */
export const CAREERS={
  milk_tea:{emoji:"🧋",name:"Trà sữa",steps:[
    {text:"👂 Nghe khách gọi món",img:"milk-tea-1.webp",w:720,h:351,marks:[[60.5, 56.3, 1]]},
    {text:"🥤 Lấy ly, rót trà",img:"milk-tea-2.webp",w:720,h:552,marks:[[26.7, 23.1, 1], [81.3, 58.2, 2]]},
    {text:"🧊 Topping, đá, đường",img:"milk-tea-3.webp",w:720,h:369,marks:[[38.5, 30.0, 1], [31.3, 67.0, 2]]},
    {text:"🔥 Ép nắp, giao ly",img:"milk-tea-4.webp",w:720,h:445,marks:[[28.2, 49.0, 1], [75.1, 81.3, 2]]},
  ]},
  grocery:{emoji:"🛒",name:"Tạp hoá",steps:[
    {text:"🛒 Mời khách lên quầy",img:"grocery-1.webp",w:720,h:375,marks:[[50.5, 82.8, 1]]},
    {text:"📷 Quét đủ từng món",img:"grocery-2.webp",w:720,h:369,marks:[[82.8, 37.0, 1], [82.8, 72.0, 2]]},
    {text:"🏷️ Áp khuyến mãi, chốt bill",img:"grocery-3.webp",w:720,h:535,marks:[[87.4, 47.2, 1], [61.3, 87.6, 2]]},
    {text:"💵 Đủ tiền mới giao",img:"grocery-4.webp",w:720,h:609,marks:[[36.2, 57.6, 1], [61.3, 86.1, 2]]},
  ]},
  delivery:{emoji:"🛵",name:"Giao hàng",steps:[
    {text:"✋ Nhận đơn trên app",img:"delivery-1.webp",w:720,h:441,marks:[[50.0, 70.3, 1]]},
    {text:"⚖️ Cân và kiểm hàng",img:"delivery-2.webp",w:720,h:495,marks:[[34.6, 73.5, 1]]},
    {text:"🗺️ Chọn điểm, chốt lộ trình",img:"delivery-3.webp",w:720,h:539,marks:[[26.4, 43.2, 1]]},
    {text:"💵 Thối đúng, giao tận tay",img:"delivery-4.webp",w:720,h:569,marks:[[22.6, 43.5, 1], [45.9, 88.3, 2]]},
  ]},
  cafe_bakery:{emoji:"🥐",name:"Bánh & cà phê",steps:[
    {text:"📝 Nhận order",img:"cafe-bakery-1.webp",w:720,h:460,marks:[[50.5, 78.7, 1]]},
    {text:"⚖️ Chọn hạt, xay, nén",img:"cafe-bakery-2.webp",w:720,h:462,marks:[[18.7, 28.8, 1], [79.5, 71.2, 2]]},
    {text:"⏹️ Vạch xanh: dừng chiết",img:"cafe-bakery-3.webp",w:720,h:443,marks:[[21.5, 67.5, 1]]},
    {text:"🛎️ Đủ ✓ thì Giao",img:"cafe-bakery-4.webp",w:720,h:609,marks:[[82.1, 87.0, 1]]},
  ]},
  florist:{emoji:"💐",name:"Tiệm hoa",steps:[
    {text:"📝 Nghe khách dặn",img:"florist-1.webp",w:720,h:463,marks:[[50.5, 85.7, 1]]},
    {text:"🌻 Chọn đúng hoa",img:"florist-2.webp",w:720,h:574,marks:[[26.4, 81.7, 1], [26.4, 18.3, 2]]},
    {text:"✂️ Cắt gốc, tuốt lá",img:"florist-3.webp",w:720,h:609,marks:[[26.9, 18.2, 1], [36.4, 64.2, 2]]},
    {text:"💐 Gói, viết thiệp, trao",img:"florist-4.webp",w:720,h:609,marks:[[82.1, 91.2, 1]]},
  ]},
};

/** The last tour bubble shows what the end of a day looks like. */
export const SUMMARY_PIC=IMG+'day-summary.webp';
