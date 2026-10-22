/** Existing app routes shared by the compact HUD and searchable town guide.
 * Availability mirrors app.js navItems: no feature is invented by the map.
 */
import {choice as rideChoice,canRide,label as rideLabel,next as nextRide} from '../v4/ride.js';
import {fairOpen} from '../v4/town-fair-data.js';   // 🎪 Hội chợ việc làm: on now (game/town_fair.py)
import {hwShown} from '../v4/halloween-data.js';   // 🎃 Lễ hội Ma Phố: 26/10 → the end of 01/11 (game/halloween.py)
/** 🚗 The HUD's "đi xe / đi bộ" toggle (the same choice as the old interface's walks, remembered in this browser):
 * its words while the player owns something to ride, else ''. nextTownRide switches to the next one. */
export const townRideLabel=(state,content)=>canRide(state,content)?rideLabel(rideChoice(state,content)):'';
export const nextTownRide=(state,content)=>nextRide(state,content);
/** 📯 What is ridden now (for the horn button): {kind, bell} (a bicycle rings a bell), or null on foot. */
export function townRiding(state,content){
  try{const v=canRide(state,content)?rideChoice(state,content):null;return v?{kind:String(v.kind||''),bell:v.kind==='bicycle'}:null;}catch{return null;}
}
const JOURNEY_FEATURES={tileMatch:'tile',garage:'garage',gadgets:'gadgets',pets:'pets',petArena:'pets',spend:'spend',spendStyle:'spend',spendQuan:'spend',spendSpa:'spend',spendRap:'spend',spendChua:'spend',lux:'lux',luxFw:'lux',luxTrip:'lux',luxSuu:'lux',luxNha:'lux',luxBay:'lux',luxTiec:'lux',luxHoc:'lux',luxMtq:'lux',abroad:'abroad'};
const CONTENT_FEATURES={quay:'quay',auction:'auction',auctionLands:'auction',jrCerts:'certs',island:'island',lixi:'lixi'};
const LIVE_FEATURES={liveWalk:'street',liveDate:'dating',liveWed:'wedding',liveKara:'kara'};
const owns=(object,key)=>Object.prototype.hasOwnProperty.call(object,key);
/** 💐 Thiệp 20/10 (/2010, game/event2010.py WRITE_UNTIL; tests/test_event2010.py keeps the two equal): the entries
 * (Tiện ích, the journey home, the card that opens once: v4/ev2010.js) show until writing closes, 21/10/2026 23:59 VN. */
export const EV2010_UNTIL=1792515599e3;   // 20/10 23:59:59 VN: writing closed (owner 21/10), no card or entry after it
export const ev2010Open=(t=Date.now())=>t<=EV2010_UNTIL;

/** Known optional services use the app's gates; ordinary map actions stay available. */
export function townServiceAvailable(action,state={},content={},social={},actionData={}){
  const journey=state?.journey||{},story=Boolean(journey.story);
  if(owns(JOURNEY_FEATURES,action))return Boolean(story&&journey[JOURNEY_FEATURES[action]]);
  if(owns(CONTENT_FEATURES,action))return Boolean(story&&content?.journey?.[CONTENT_FEATURES[action]]);
  if(owns(LIVE_FEATURES,action))return Boolean(social?.welcomed&&social?.flags?.[LIVE_FEATURES[action]]);
  if(action==='house'||action==='jrInvest'||action==='townProjects'||action==='bang')return story;
  if(action==='rui')return Boolean(state?.rui);
  if(action==='bangIsland')return Boolean(content?.bang_island);   // ⚔️ Đảo bang: only while MNL_BANG_ISLAND=1 (game/bang_island.py)
  if(action==='ev2010')return ev2010Open();
  if(action==='halloween')return story&&hwShown();
  if(action==='townFair')return story&&fairOpen();   // 🎪 Saturday 14:00–17:00, or a fair an admin opened
  if(action==='fair'){
    if(!state?.fair?.show)return false;
    const feature={dg:'dog',dt:'knife',xs:'scratch',pb:'photo'}[actionData?.tab];
    return !feature||Boolean(state.fair[feature]);
  }
  if(action==='jrEnterHome')return Boolean(story&&journey.deco);
  if(action==='jrAccShop')return Boolean(journey.gender);   // 🛍️ Tiệm phụ kiện (v4/acc-shop.js): a character to dress
  if(action==='homeGuests')return story;
  if(action==='stView')return Boolean(story&&actionData?.view==='household'&&journey.household);
  if(action==='marriage'&&actionData?.tab==='family')return story;
  if(action==='wedInvite')return Boolean(story&&state?.marriage?.spouse);
  return true;
}

export function townUtilityGroups(state={},content={},social={}){
  const entries=rows=>rows.map(([action,icon,emoji,label,actionData,id])=>({id:id||action,action,icon,emoji,label,...(actionData?{actionData}:{})})).filter(item=>townServiceAvailable(item.action,state,content,social,item.actionData));
  return [
    {id:'services',icon:'home',label:'Tiền, nhà & phương tiện',items:entries([
      ['money','bag','💰','Tiền của bạn'],['bank','coin','🏦','Ngân hàng'],
      ['house','home','🏠','Nhà của bạn'],['garage','bike','🛵','Xe & phương tiện'],
      ['jrEnterHome','home','🎨','Vào nhà · trang trí & sửa chữa'],['homeGuests','people','🏡','Khách & người ở cùng'],
      ['garage','bike','🛵','Cửa hàng xe máy',{tab:'bike'},'garage-bike'],['garage','truck','🚗','Showroom ô tô',{tab:'car'},'garage-car'],
      ['garage','boat','🛥️','Du thuyền',{tab:'boat'},'garage-boat'],['garage','pilot','✈️','Máy bay riêng',{tab:'plane'},'garage-plane'],
      ['gadgets','phone','📱','Điện thoại & đồ công nghệ'],
      ['rui','shield','🛡️','Bảo hiểm'],['jrInvest','coin','📈','Đầu tư'],
      ['quay','store','🏪','Quầy của bạn'],
      ['lux','bag','🛍️','Mua sắm'],['island','boat','🏝️','Đảo riêng'],['island','home','🏗️','Xây trên đảo',{tab:'build'},'island-build'],['bangIsland','flag','⚔️','Đảo bang'],['auction','award','🔨','Nhà đấu giá'],
      ['auctionLands','map','🏞️','Đấu giá danh thắng'],
    ])},
    {id:'life',icon:'paw',label:'Đời sống & đi chơi',items:entries([
      ['pets','paw','🐾','Thú cưng'],['spend','coffee','☕','Đi chơi'],
      ['pets','paw','🐱','Nhận nuôi thú cưng',{tab:'adopt'},'pets-adopt'],['pets','paw','🐶','Tiệm thú cưng',{tab:'shop'},'pets-shop'],
      ['pets','award','🏆','Bé cưng của tuần',{tab:'board'},'pets-board'],
      
      ['stView','home','👶','Chăm con riêng & thú cưng',{view:'household'},'household'],
      ['spendQuan','coffee','☕','Cà phê & quán ăn'],['spendSpa','sparkle','🪷','Spa'],['spendRap','camera','🎬','Rạp phim'],['spendChua','home','🙏','Công đức'],
      ['spendStyle','sparkle','🎨','Phong cách'],['jrAccShop','bag','🎀','Tiệm phụ kiện'],['jrAccShop','gift','🤝','Phụ kiện đôi',{tab:'pair'},'acc-pairs'],['lixi','gift','🧧','Lì xì'],['luxFw','sparkle','🎆','Bắn pháo hoa'],['island','globe','🌍','Đảo mở cửa',{tab:'inv'},'island-open'],
      ['luxTrip','pilot','✈️','Du lịch'],['luxSuu','award','🏺','Sưu tầm'],['luxNha','home','🏰','Dinh thự'],['luxBay','pilot','🛩️','Bay riêng'],
      ['luxTiec','people','🎉','Mở tiệc'],['luxHoc','book','📚','Khóa học'],['luxMtq','heart','💝','Mạnh Thường Quân'],
    ])},
    {id:'fair',icon:'flag',label:'Hội chợ & Chợ đen',items:entries([
      ['townFair','flag','🎪','Hội chợ việc làm · gian hàng mọi nghề'],
      ['fair','flag','🏮','Cổng Chợ đen',{tab:'home'},'fair-home'],
      ['fair','flag','🎪','Hội chợ · ném vòng',{tab:'ring'},'fair-ring'],['fair','paw','🐕','Đường đua chó',{tab:'dg'},'fair-dg'],
      ['fair','people','🪨','Ô ăn quan',{tab:'oaq'},'fair-oaq'],['fair','award','🎲','Bầu cua',{tab:'bc'},'fair-bc'],
      ['fair','music','🎟️','Gánh lô tô',{tab:'lt'},'fair-lt'],['fair','coin','🥣','Xóc đĩa',{tab:'xd'},'fair-xd'],
      ['fair','award','🗡️','Phóng dao',{tab:'dt'},'fair-dt'],['fair','award','🎫','Vé số cào',{tab:'xs'},'fair-xs'],
      ['fair','camera','📸','Buồng chụp ảnh',{tab:'pb'},'fair-pb'],['fair','award','🏆','Bảng vàng Chợ đen',{tab:'board'},'fair-board'],
      ['fair','coffee','🍜','Quầy đồ ăn Chợ đen',{tab:'food'},'fair-food'],['fair','coin','💰','Vay & trả tại Chợ đen',{tab:'loan'},'fair-loan'],
    ])},
    {id:'learning',icon:'book',label:'Học tập & chứng chỉ',items:entries([
      ['jrCerts','clipboard','🎓','Thi chứng chỉ'],
      ['accountingSchool','calculator','📒','Học kế toán'],['historyCourse','book','📜','Học lịch sử'],
      ['abroad','globe','🌏','Du học & nước ngoài'],
    ])},
    {id:'community',icon:'people',label:'Bạn bè & khu phố',items:entries([
      ['friends','user','🤝','Bạn bè'],['marriage','heart','💒','Hôn nhân & gia đình'],
      ['marriage','home','👨‍👩‍👧','Nhà & gia đình chung',{tab:'family'},'family'],
      ['marriage','heart','👶','Chăm con chung',{tab:'family',section:'children'},'family-children'],
      ['nhom','chat','📌','Nhóm phố'],['social','globe','🛍️','Phố nghề'],['rank','award','🏆','Bảng xếp hạng'],
      ['townProjects','building','🏗️','Công trình của phố'],['bang','shield','⚔️','Bang'],
      ['liveWalk','map','🚶','Phố đi dạo'],['liveDate','heart','💕','Góc hẹn hò'],
      ['liveWed','heart','💍','Lịch cưới'],['liveKara','music','🎤','Phòng hát'],
      ['tileMatch','grid','🧩','Ghép ba Phố Mây'],
      ['wedInvite','mail','💌','Thiệp mời cưới'],['ev2010','heart','💐','Thiệp 20/10'],['halloween','sparkle','🎃','Lễ hội Ma Phố'],
    ])},
  ].filter(group=>group.items.length);
}
