/** 🎱 Gánh lô tô (public/js/v4/fair.js): what cô Bảy Lô Tô says and what the troupe does. Every verse here was
 * written for the game (no lyrics of any song): a short folk-style câu rao that ends on a word rhyming with the
 * number, then the number. The verses are grouped by the rhyme of the number's last word (một/mốt, hai, ba, bốn, tư,
 * năm/lăm, sáu, bảy, tám, chín, mười/mươi); a round picks them so the same verse does not come twice in one round,
 * and everyone in the same minute hears the same ones. Nothing here decides anything: the server checks every Kinh. */

const UNITS=['','một','hai','ba','bốn','năm','sáu','bảy','tám','chín'];
/** The number in words, as the caller says it (21 hai mươi mốt, 24 hai mươi tư, 15 mười lăm). Up to 99 (lật ngược). */
export function words(n){
  if(n<10)return UNITS[n]||'không';
  const t=Math.floor(n/10),u=n%10,head=t===1?'mười':UNITS[t]+' mươi';
  if(!u)return head;
  const tail=u===1&&t>1?'mốt':u===4&&t>1?'tư':u===5?'lăm':UNITS[u];
  return head+' '+tail;
}
const RHYME_OF={một:'ot',mốt:'ot',hai:'ai',ba:'a',bốn:'on',tư:'u',năm:'am5',lăm:'am5',sáu:'au',bảy:'ay',tám:'am',chín:'in',mười:'uoi',mươi:'uoi'};

/* Each line ends on the rhyme; the number follows it (TAILS). */
export const VERSES={
  ot:['Bột mì nhồi kỹ, bánh nở thơm lừng mùi bột','Bánh mì vừa nướng, còn thơm còn nóng sốt','Ai đàn tích tịch tình tang, nghe vui từng nốt',
    'Nhà ai mới dựng, chôn xong cái cột','Vườn nhà trồng cải, nhổ được củ cà rốt','Gạo mới xay xong, trắng tinh từng hột',
    'Đi coi hội về, nhớ cài cửa cài chốt','Đêm rằm trung thu, lồng đèn ai đốt','Gió đồng thổi mát, lúa trổ bông tốt',
    'Học bài chăm chỉ, cô khen trò ngoan trò tốt'],
  ai:['Hôm nay vui vẻ, hẹn nhau ngày mai','Tóc ai dài óng, thả ngang bờ vai','Chợ chiều bán khoai, củ to củ dài',
    'Con thỏ nhảy nhót, vểnh đôi tai','Bé học chăm ngoan, thuộc làu từng bài','Mùa này trái chín, ngọt lịm trái xoài',
    'Đứng đây ngó quanh, đố bà con là ai','Tiểu phẩm xem xong, cười té ghế vì hài','Áo mới cúc vàng, cô Bảy khéo cài',
    'Dò cho thiệt kỹ, kẻo lỡ dò sai'],
  a:['Hội chợ đông vui, khách tới gần xa','Cơm trắng canh chua, thêm chén dưa cà','Sáng sớm tinh mơ, gáy vang con gà',
    'Chiều chiều ông nội, pha ấm nước trà','Hội chợ tan rồi, ai cũng có quà','Vườn xuân rực rỡ, muôn sắc muôn hoa',
    'Cả xóm quây quần, cùng hát cùng ca','Đò ơi đợi chút, cho em sang qua','Cây đa đầu làng, gió mát la đà',
    'Trăng lên đầu ngõ, sáng cả sân nhà'],
  on:['Mưa rơi trên mái, lách tách mái tôn','Đường về xóm nhỏ, đầu làng cuối thôn','Lục bình trôi nổi, ghé vào bãi cồn',
    'Nghe tiếng trống chầu, ai nấy bồn chồn','Học ăn học nói, mai mốt nên khôn','Hoa tươi trong chậu, nước tưới đầy bồn',
    'Gió đưa tiếng hát, rộn ràng tâm hồn'],
  u:['Nhớ ai mà viết lá thư','Ngồi dò cho kỹ, chớ có chần chừ','Nồi cơm má nấu, ăn no còn dư',
    'Bé ngoan vâng lời, chẳng có chút hư','Tay dò số giỏi, thiệt là quá cừ','Rủ đi coi hội, bạn gật đầu: ừ',
    'Mưa dầm sụt sùi, trời đất lừ đừ','Nói hay chưa bằng làm, cứ thong thả từ từ'],
  am5:['Ai đi xa nhớ ghé về thăm','Đêm nay trăng sáng tròn như rằm','Trưa hè gió mát, đong đưa võng nằm',
    'Ruộng ai cày cấy, sớm tối siêng chăm','Cơm ngon nhờ có chén nước mắm','Bánh tét bánh chưng, má gói cả trăm',
    'Cô Bảy hát hay, khán giả mê lắm','Thuyền ai về bến, sóng nước êm đằm','Cơm nắm muối mè, ăn xong một nắm'],
  au:['Hai đứa mình đi hội cùng nhau','Miếng trầu têm với quả cau','Vườn nhà má trồng mấy luống rau',
    'Mua tờ dò lẹ, chạy nhanh cho mau','Cầu vồng sau mưa, rực rỡ bảy màu','Sân ga tấp nập, xình xịch đoàn tàu',
    'Bà ngồi đầu hiên, kể chuyện cho cháu','Bờ đê lộng gió, trắng xóa bông lau','Ca dao ông bà, là của quý báu',
    'Mới lạ hôm trước, quen thân hôm sau'],
  ay:['Hội chợ vui quá, vỗ tay vỗ tay','Cánh diều no gió tung bay','Ớt xanh ớt đỏ, trái nào cũng cay',
    'Trâu ra ruộng sớm, cùng bác đi cày','Thóc vàng mới gặt, chở về nhà xay','Tiếng hò câu hát, nghe sao mà hay',
    'Chúc bà con mình, ai cũng gặp may','Con đường làng nhỏ, bé tung tăng chạy','Cô giáo hiền hậu, chữ đẹp cô dạy',
    'Bốn mùa xuân hạ, thu đông đổi thay'],
  am:['Ai ăn quýt ngọt, ai ăn cam','Áo ai phơi nắng màu lam','Ngày mai đi hội, hôm nay lo làm',
    'Thuyền xuôi về bắc, chim bay về nam','Mây chiều kéo tới, trời ngả màu xám','Rừng tràm xanh mát, thơm ngát hoa tràm',
    'Gà con lích chích, mổ thóc mổ cám','Bé ngoan không khóc, khi bác sĩ khám','Đọc sách đọc truyện, bé mê bé ham'],
  in:['Đứng đây mà ngó mà nhìn','Lời thương nhắn gửi ai tin','Bánh bông lan nướng, xốp mềm mà mịn',
    'Qua cầu khỉ nhỏ, nhớ tay vịn','Bé đang khóc nhè, cho kẹo là nín','Tờ dò cô Bảy, mới tinh mới in',
    'Cả xóm vô xem, đông tới cả nghìn','Áo cô Bảy mặc, kim tuyến hàng xịn','Lúa vàng trĩu hạt, trái cây đã chín',
    'Muốn mượn đồ chơi, lễ phép thưa xin'],
  uoi:['Cô hàng nước miệng cười tươi','Cả phố đi hội đông người','Vô sở thú ngó chú đười ươi',
    'Bà ngoại cho quà, một trái bưởi','Thuyền về bến cá, đầy ắp khoang lưới','Vườn rau xanh mướt, sáng chiều siêng tưới',
    'Rộn ràng hội chợ, xóm trên xóm dưới','Trời lạnh căm căm, quây quần bếp sưởi','Ăn rồi làm việc, chẳng có ai lười',
    'Hàng xóm sang chơi, tiếng nói tiếng cười'],
};
const TAILS=['là con số {w}!','ra con số {w}!','con số {w} đây!','số {w} nè bà con!'];
/** Lines for one number, said instead of a verse every other round. */
export const SPECIAL={
  1:'Mở hàng con số đầu dàn: số một!',7:'Số ruột của cô Bảy nè bà con: số bảy!',8:'Tròn trịa như hai bánh xe đạp: số tám!',
  10:'Mười ngón tay xinh, đếm hoài không hết: số mười!',11:'Hai chiếc đũa đứng song song: mười một!',12:'Mười hai con giáp đủ mặt cả làng: mười hai!',
  22:'Hai con vịt nhỏ bơi tung tăng: hai mươi hai!',33:'Ba với ba, cặp đôi dễ thương: ba mươi ba!',45:'Đứng giữa dàn số, chẳng lớn chẳng nhỏ: bốn mươi lăm!',
  55:'Năm với năm, đập tay cái bốp: năm mươi lăm!',66:'Hai con nòng nọc ngoắt đuôi bơi: sáu mươi sáu!',70:'Số ruột thứ hai của cô Bảy: bảy mươi!',
  77:'Bảy với bảy, cô Bảy mừng gấp đôi: bảy mươi bảy!',80:'Tám mươi chưa già, ông còn chạy bộ: tám mươi!',90:'Lớn nhất cả dàn: chín mươi!',
};
const EN=['Number {n}!','Next up: {n}!','Here comes {n}!','It is {n}, folks!'];
/** How many verses (for the record: tests and the release notes count them). */
export const verseCount=()=>Object.values(VERSES).reduce((a,v)=>a+v.length,0)+Object.keys(SPECIAL).length;

const hash=s=>{let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}return h>>>0;};
/** The caller's line for the call at `i` of a round (seq: the round's calls; slot: its minute; shown: the number
 * as the board shows it, reversed in a lật ngược vòng). Verses rotate inside a rhyme group from a start drawn from
 * the minute, so a number's verse does not come twice in a round. */
export function callLine(seq,i,slot,en=false,shown=null){
  const n=seq[i],say=shown??n;
  if(en)return EN[hash(`${slot}|${i}`)%EN.length].replace('{n}',String(say));
  if(shown==null&&SPECIAL[n]&&(slot+n)%2===0)return SPECIAL[n];
  const w=words(say),key=RHYME_OF[w.split(' ').pop()]||'uoi',list=VERSES[key];
  let k=0;for(let j=0;j<i;j++){const m=seq[j];if(RHYME_OF[words(m).split(' ').pop()]===key)k++;}   // earlier calls of this rhyme
  const verse=list[(hash(`${slot}|${key}`)+k)%list.length],tail=TAILS[hash(`${slot}|t${i}`)%TAILS.length];
  return `${verse}, ${tail.replace('{w}',w)}`;
}

/* ---- cô Bảy between calls ---- */
export const MC={name:'Cô Bảy Lô Tô',
  hello:['Xin chào bà con cô bác! Gánh lô tô cô Bảy về tới rồi đây!','Mua tờ dò đi bà con ơi, vui thôi mà, xu nhỏ cũng chơi!','Nhạc lên đèn sáng, ai mua tờ dò thì ngồi xuống nha!','Áo kim tuyến cô Bảy mặc rồi, chỉ còn chờ bà con mua vé!'],
  ready:'Chuẩn bị nha bà con… số đầu tiên ra liền!',
  near:['Có người chờ một số rồi đó nha, dò cho kỹ!','Ai chờ thì ngồi im, đừng có nhấp nhổm nha!','Nóng rồi nóng rồi, sắp có người kinh!'],
  hut:['Ủa ủa, kinh gì kỳ vậy nè? Hàng còn trống kìa!','Kinh hụt rồi! Hát một câu chuộc lỗi đi nha!','Ha ha, kinh sớm quá! Dò lại cho kỹ nha cưng!','Khán giả cười quá trời kìa, dò lại đi nha!'],
  win:['Kinh rồi! Kinh rồi! Chúc mừng người thắng, vỗ tay lên nào!','Trời ơi hên quá xá! Lên nhận thưởng nè!','Kinh ngọt xớt! Cả gánh chúc mừng nha!'],
  lose:['{who} kinh rồi! Ván sau tới lượt mình nha.','{who} hô “Kinh!” trước mất rồi, ván sau gỡ nha!','Ván này về tay {who}, mình chơi tiếp ván sau nha!'],
};
/** The troupe between rounds: one act at a time (the client cycles them; `say` is the act's line). */
export const ACTS=[
  {k:'dance',who:'💃🕺',name:'Đôi múa quạt',say:['Một, hai, ba, xoay! Bà con vỗ tay theo nhịp nha!','Quạt hồng quạt tím, múa cho cả xóm coi!']},
  {k:'drum',who:'🥁',name:'Bé Tí đánh trống',say:['Tùng tùng cắc, tùng tùng cắc! Trống lên là có số!','Bé Tí đánh trống chầu, ván sau ai kinh trước đây?']},
  {k:'juggle',who:'🤹',name:'Chú Sáu tung banh',say:['Một banh, hai banh, ba banh… ủa, banh thứ tư đâu rồi?','Tung cao tung thấp, chụp không rớt trái nào!']},
  {k:'skit',who:'🎭',name:'Tiểu phẩm',say:[
    'Anh Tèo: “Cô Bảy ơi, sao số 7 ra hoài vậy?” — Cô Bảy: “Tại nó nhớ chị nó đó!”',
    'Bé Bi: “Con dò số giỏi lắm!” — Bà Năm: “Giỏi sao tờ dò của con cầm ngược?”',
    'Chú Sáu: “Tui kinh!” — Cô Bảy: “Chú ơi, chưa mua tờ dò mà kinh cái gì?”',
    'Cô Ba: “Sao cô Bảy hô số hay vậy?” — Cô Bảy: “Tập hát từ hồi còn bú bình đó!”',
    'Bác Tư: “Đeo kính vô rồi mà sao số nhảy lung tung?” — Chị Mận: “Bác đeo kính râm đó bác!”',
    'Anh Tèo: “Em mua ba tờ cho chắc ăn!” — Cô Bảy: “Ba tờ mà dò một tờ thì cũng như một tờ thôi nha!”']},
  {k:'sing',who:'🎤',name:'Cô Bảy chào khán giả',say:['Cảm ơn bà con đã ghé gánh lô tô cô Bảy! Vui là chính, hên là mười!','Gánh nhỏ mà vui, chơi xu nhỏ mà cười to!']},
];
export const CROWD=['👏','😂','🎉','❤️','😮','🙌','🥳','✨'];
/** Stickers for a Kinh: the vòng's own, then a cute one picked from the round. */
export const STICKERS=[['🐣','Gà con may mắn'],['🐯','Hổ con dò số'],['🐼','Gấu trúc hên xui'],['🦊','Cáo nhỏ lanh lợi'],['🐸','Ếch xanh nhảy số'],['🐰','Thỏ ngọc kinh nhanh']];
export const MODE_STICKER={doi:['🎎','Kinh đôi rộn ràng'],nguoc:['🙃','Đọc ngược như xuôi'],dem:['🏺','Ôm hũ đêm hội']};
