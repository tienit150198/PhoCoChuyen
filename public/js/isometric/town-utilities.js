/** Existing app routes shared by the compact HUD and searchable town guide.
 * Availability mirrors app.js navItems: no feature is invented by the map.
 */
const JOURNEY_FEATURES={garage:'garage',gadgets:'gadgets',pets:'pets',spend:'spend',spendStyle:'spend',spendQuan:'spend',spendSpa:'spend',spendRap:'spend',spendChua:'spend',lux:'lux',luxFw:'lux',luxTrip:'lux',luxSuu:'lux',luxNha:'lux',luxBay:'lux',luxTiec:'lux',luxHoc:'lux',luxMtq:'lux',abroad:'abroad'};
const CONTENT_FEATURES={quay:'quay',auction:'auction',auctionLands:'auction',jrCerts:'certs'};
const LIVE_FEATURES={liveWalk:'street',liveDate:'dating',liveWed:'wedding',liveKara:'kara',liveBark:'bark'};
const owns=(object,key)=>Object.prototype.hasOwnProperty.call(object,key);

/** Known optional services use the app's gates; ordinary map actions stay available. */
export function townServiceAvailable(action,state={},content={},social={},actionData={}){
  const journey=state?.journey||{},story=Boolean(journey.story);
  if(owns(JOURNEY_FEATURES,action))return Boolean(story&&journey[JOURNEY_FEATURES[action]]);
  if(owns(CONTENT_FEATURES,action))return Boolean(story&&content?.journey?.[CONTENT_FEATURES[action]]);
  if(owns(LIVE_FEATURES,action))return Boolean(social?.welcomed&&social?.flags?.[LIVE_FEATURES[action]]&&(action!=='liveBark'||story));
  if(action==='house'||action==='jrInvest')return story;
  if(action==='rui')return Boolean(state?.rui);
  if(action==='fair'){
    if(!state?.fair?.show)return false;
    const feature={dg:'dog',dt:'knife',xs:'scratch',pb:'photo'}[actionData?.tab];
    return !feature||Boolean(state.fair[feature]);
  }
  if(action==='jrEnterHome')return Boolean(story&&journey.deco);
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
      ['lux','bag','🛍️','Mua sắm'],['auction','award','🔨','Nhà đấu giá'],
      ['auctionLands','map','🏞️','Đấu giá danh thắng'],
    ])},
    {id:'life',icon:'paw',label:'Đời sống & đi chơi',items:entries([
      ['pets','paw','🐾','Thú cưng'],['spend','coffee','☕','Đi chơi'],
      ['pets','paw','🐱','Nhận nuôi thú cưng',{tab:'adopt'},'pets-adopt'],['pets','paw','🐶','Tiệm thú cưng',{tab:'shop'},'pets-shop'],
      ['pets','award','🏆','Bé cưng của tuần',{tab:'board'},'pets-board'],
      ['stView','home','👶','Chăm con riêng & thú cưng',{view:'household'},'household'],
      ['spendQuan','coffee','☕','Cà phê & quán ăn'],['spendSpa','sparkle','🪷','Spa'],['spendRap','camera','🎬','Rạp phim'],['spendChua','home','🙏','Công đức'],
      ['spendStyle','sparkle','🎨','Phong cách'],['luxFw','sparkle','🎆','Bắn pháo hoa'],
      ['luxTrip','pilot','✈️','Du lịch'],['luxSuu','award','🏺','Sưu tầm'],['luxNha','home','🏰','Dinh thự'],['luxBay','pilot','🛩️','Bay riêng'],
      ['luxTiec','people','🎉','Mở tiệc'],['luxHoc','book','📚','Khóa học'],['luxMtq','heart','💝','Mạnh Thường Quân'],
    ])},
    {id:'fair',icon:'flag',label:'Hội chợ & Chợ đen',items:entries([
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
      ['liveWalk','map','🚶','Phố đi dạo'],['liveDate','heart','💕','Góc hẹn hò'],
      ['liveWed','heart','💍','Lịch cưới'],['liveKara','music','🎤','Phòng hát'],
      ['liveBark','paw','🐕','Kéo co chó sủa'],
      ['wedInvite','mail','💌','Thiệp mời cưới'],
    ])},
  ].filter(group=>group.items.length);
}
