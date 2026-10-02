/** The inside of the city airport for the air crew (pilot, flight_attendant): the areas of scenes/airfield.js
 * (see scenes/areas.js for the mechanism, scenes/interior.js for the kit). The apron stays the main area.
 *   crew      Phòng tổ bay: weather screen with the day's forecast, today's departures, lockers, a couch where
 *             Mướp naps, the briefing table (the pilot's brief and fuel sheet), the sign-in desk.
 *   terminal  Sảnh ga: the glass wall onto the apron, the departures board, check-in desks with a moving belt,
 *             the security line (X-ray belt and arch), passengers with luggage walking by, announcements.
 *   gate      Cổng ra tàu: the waiting seats, the gate desk with today's flight, the queue (the task people),
 *             the aircraft outside the window.
 *   cockpit   Buồng lái: the windshield (apron, clouds or the runway, by the flight's step), the instrument
 *             panel whose checklist switches, fuel gauge and weather screen follow the pilot's task.
 *   cabin     Khoang khách: windows, overhead bins, rows of passengers, the service cart; the special meals
 *             served, the seat-belt sign when turbulence comes (flight attendant's task).
 * Everything reads the career's public view (tasks, data.mod, data.turb); nothing is decided here. */
import {R,E,L,T,P,fit,heart} from './kit.js';
import {geo,both,box,spotAt,shell,doorway,windowPane,skyAt,weatherOf,hash,beat,bubble,suitcase,sitter,passer,plate} from './interior.js';

const NAVY='#2f5d8a',NAVY_D='#1b3550',TEAL='#1f7a78',GREY='#b9c1c8',GREY_D='#8d979f',WHITE='#f8fafc',GLASS='#bcd9ea',YEL='#f2c14e',RED='#d9534f',DARK='#26303b',GREEN='#8fe0a0';
const ended=t=>['completed','cancelled','referred'].includes(t.status);
const upper=s=>String(s||'').toLocaleUpperCase('vi-VN');
const fa=w=>w.career==='flight_attendant';
/** The task in hand, or null. */
const task=w=>{const c=w.c;return c?.tasks?.find(t=>t.id===c.active_task&&!ended(t))||null;};
/** Today's flights (both careers keep a leg on every task), in slot order; a few sample ones before the roster. */
function legs(w){
  const c=w.c||{},list=(c.tasks||[]).filter(t=>t.leg&&t.day===c.day).sort((a,b)=>Number(a.id.slice(-2))-Number(b.id.slice(-2)));
  if(list.length)return list.map(t=>({...t.leg,t}));
  return [{code:'CC 102',to:'Côn Đảo',dep:'07:40',gate:'2'},{code:'CC 114',to:'Cà Mau',dep:'09:10',gate:'1'},{code:'CC 120',to:'Rạch Giá',dep:'11:30',gate:'3'}];
}
/** A flight's line on the boards. */
function status(w,l){
  const t=l.t;if(!t)return ['ĐÚNG GIỜ',GREEN];
  if(t.status==='completed')return ['ĐÃ CẤT CÁNH','#9fb3c8'];
  if(ended(t))return ['ĐÃ HỦY',RED];
  if(t.id===w.c?.active_task){const st=t.stage;if(st==='cruise'||st==='approach')return ['ĐANG BAY',YEL];return ['ĐANG LÊN TÀU',YEL];}
  return (t.delay||0)>0?['TRỄ '+t.delay+'′','#f39c6b']:['ĐÚNG GIỜ',GREEN];
}
/** In the air right now (the flight in hand is cruising, approaching, or the cabin is in service)? */
function flying(w){
  const t=task(w);if(!t||!w.c?.open)return false;
  if(fa(w))return ['service','calm','medical'].includes(t.kind)||w.c?.data?.turb?.stage==='coming';
  return t.stage==='cruise'||t.stage==='approach';
}

/* ------------------------------------------------------------ shared pieces */
/** A departures board (split-flap look): rows of time · flight · to · gate · status; the active row blinks. */
function departures(c,w,g,x,y,wd,ht,{rows=4,title='KHỞI HÀNH'}={}){
  const k=g.k,list=legs(w).slice(0,rows),rh=(ht-34*k)/rows,size=Math.max(g.port?13:10,Math.min(rh*.5,15*k));
  R(c,x-6,y-6,wd+12,ht+12,'#3a434e',8);R(c,x,y,wd,ht,'#1d242c',6);
  T(c,`✈ ${title}`,x+12*k,y+16*k,g.port?14:12,YEL,800,'left');
  const flip=beat(w,4,3),narrow=wd<300,cols=narrow?[.02,.22,.45,0,.68]:[.02,.19,.39,.72,.8];
  list.forEach((l,i)=>{const ry=y+30*k+i*rh,[st,col]=status(w,l),now=l.t&&l.t.id===w.c?.active_task;
    R(c,x+4,ry+2,wd-8,rh-4,i%2?'#232c36':'#283340',3);
    if(flip.on&&i===flip.n%Math.max(1,list.length)&&flip.k<.08){R(c,x+4,ry+rh/2-1,wd-8,2,'#0b0f13',0);}
    const cell=(u,s,color,max)=>T(c,s,x+wd*u+4,ry+rh/2,fit(c,s,max,size),color,700,'left');
    cell(cols[0],l.dep||'',WHITE,wd*.18);cell(cols[1],l.code||'',YEL,wd*.2);cell(cols[2],upper(l.to),WHITE,narrow?wd*.22:wd*.32);if(!narrow)cell(cols[3],l.gate||'',WHITE,wd*.07);
    const blink=now&&!w.reduced&&Math.sin(w.time*4)<-.6;if(!blink)cell(cols[4],st,col,narrow?wd*.3:wd*.19);});
}
/** The white turboprop seen through a window, nose to the right; s scales it, (x,y) = wheels. */
function planeSide(c,x,y,s,{door=false,tail=NAVY}={}){
  c.save();c.translate(x,y);c.scale(s,s);
  E(c,0,4,170,8,'#00000018');
  P(c,[[-180,-40],[-150,-50],[150,-52],[180,-44],[195,-34],[180,-24],[-150,-22],[-176,-28]],WHITE);
  P(c,[[-178,-42],[-196,-92],[-170,-92],[-140,-50]],tail);heart(c,-176,-74,.28,WHITE);
  R(c,-150,-40,300,5,NAVY,2);for(let i=0;i<9;i++)R(c,-110+i*26,-46,10,8,GLASS,3);
  P(c,[[150,-48],[176,-44],[172,-36],[150,-38]],'#7fa7c4');
  R(c,-24,-62,110,8,'#e3e8ec',3);R(c,10,-62,34,14,'#e3e8ec',6,GREY_D,1);
  if(door)R(c,120,-48,14,22,'#3c3732',2);
  L(c,-60,-22,-60,-6,GREY_D,3);E(c,-60,-3,6,6,'#3b3f45');L(c,140,-24,140,-6,GREY_D,3);E(c,140,-3,5,5,'#3b3f45');
  c.restore();
}
/** The apron through a window: tarmac, a yellow line, sometimes the plane and the tower. */
function apronView(w,{plane=true,cart=true}={}){return (c,x,y,wd,ht)=>{
  const ground=y+ht*.68;R(c,x,ground,wd,ht,'#c3c9ce',0);L(c,x,ground+ht*.12,x+wd,ground+ht*.1,YEL,3);E(c,x+wd*.1,ground,wd*.2,8,'#9fb48f');
  R(c,x+wd*.82,ground-ht*.42,10,ht*.42,'#e3e8ec');P(c,[[x+wd*.82-12,ground-ht*.42],[x+wd*.82+22,ground-ht*.42],[x+wd*.82+16,ground-ht*.5],[x+wd*.82-6,ground-ht*.5]],'#9fc4d8');
  if(plane)planeSide(c,x+wd*.45,ground+ht*.06,Math.min(1,wd/520)*.95,{door:true});
  if(cart){const b=beat(w,14,5),px=x-60+(wd+120)*b.k;R(c,px,ground+ht*.15,46,14,'#e9eef2',3,GREY_D,1);R(c,px+34,ground+ht*.15-10,14,10,NAVY,2);E(c,px+8,ground+ht*.15+15,4,4,'#3b3f45');E(c,px+38,ground+ht*.15+15,4,4,'#3b3f45');suitcase(c,px+14,ground+ht*.15,.45,'#d07a5c');}
};}
/** A ceiling strip of lights. */
function ceiling(c,g,col='#f4f7fa'){const f=g.f;R(c,f.x,f.y,f.w,g.H(.06)-f.y,'#d7dde2',0);for(let i=0;i<6;i++)R(c,g.X(.08+i*.16),g.H(.02),g.f.w*.1,6,col,3);}
/** A rolling announcement over the hall: today's flights, the gate, a little life. */
function announce(w,g,x,y,{gate=false}={}){
  const c=w.ctx,list=legs(w),b=beat(w,7,1),i=b.n%Math.max(1,list.length),l=list[i]||{};
  const lines=[`Chuyến ${l.code} đi ${l.to} mời quý khách ra cửa ${l.gate}.`,'Quý khách vui lòng trông giữ hành lý cẩn thận.',
    gate?'Ưu tiên lên tàu: người già, trẻ nhỏ và mẹ bế em bé.':'Xin mời quý khách làm thủ tục tại quầy 1 đến 3.'];
  const late=list.find(x=>x.t&&(x.t.delay||0)>0&&!ended(x.t));
  if(late)lines.push(`Chuyến ${late.code} đi ${late.to} lùi giờ ${late.t.delay} phút. Mong quý khách thông cảm.`);
  if(!b.on||b.k<.72)bubble(c,g,x,y,lines[(b.n>>2)%lines.length]);
}

/* ------------------------------------------------------------ Phòng tổ bay */
const CREW=both(g=>({
  home:[g.X(.5),g.Y(.82)],
  blocks:[box(g,.36,.36,.64,.52),box(g,.78,.46,.95,.6),box(g,.15,0,.33,.08),box(g,.69,0,.8,.07),box(g,.82,0,.97,.07)],
  customers:[[g.X(.29),g.Y(.44)],[g.X(.71),g.Y(.38)],[g.X(.36),g.Y(.8)],[g.X(.64),g.Y(.8)]],
  cat:[g.X(.24),g.Y(.0)-g.k*26],
  labels:{workbench:'Bàn bản tin',evidence:'Màn hình thời tiết',warehouse:'Bảng giờ bay','look:coffee':'Máy pha cà phê',pet:'Chơi với Mướp trên ghế sofa'},
  spots:{workbench:spotAt(g,[g.X(.5),g.Y(.36)-30*g.k],70,[.5,.66],[.31,.62]),evidence:spotAt(g,[g.X(.49),g.H(.42)],80,[.49,.22]),
    warehouse:spotAt(g,[g.X(.71),g.H(.36)],55,[.6,.22]),door:spotAt(g,[g.X(.865),g.Y(.46)-34*g.k],55,[.865,.76]),
    pet:spotAt(g,[g.X(.24),g.Y(0)-40*g.k],45,[.24,.22]),'look:coffee':spotAt(g,[g.X(.745),g.Y(0)-50*g.k],40,[.745,.22]),
    'go:terminal':spotAt(g,[g.X(.07),g.H(.62)],50,[.07,.2])},
}));
function crewRoom(w,p){shell(w,{wall:'#e8eef4',wallLow:'#d5dee8',floor:'#c4cfd9',floor2:'#bac6d1',tile:70,rim:'#8fa3b5',trim:NAVY},(c,g)=>{
  const k=g.k;ceiling(c,g);
  doorway(c,g,.07,{color:'#5e7891',glass:GLASS});
  windowPane(c,w,g.X(.15),g.H(.2),g.f.w*.18,g.H(.66)-g.H(.2),{frame:'#dfe6ec',view:apronView(w,{cart:false})});
  // The couch under the window (Mướp naps on it).
  R(c,g.X(.15),g.base-62*k,g.f.w*.18,46*k,'#5e8fb5',14*k);R(c,g.X(.155),g.base-40*k,g.f.w*.17,24*k,'#79a8cc',10*k);
  R(c,g.X(.15),g.base-16*k,8,16*k,'#4a5d70',3);R(c,g.X(.33)-8,g.base-16*k,8,16*k,'#4a5d70',3);
  // The weather screen: a map of the routes with today's weather, a radar sweep.
  const sx=g.X(.38),sy=g.H(.14),sw=g.f.w*.22,sh=g.H(.66)-g.H(.14),m=w.c?.data?.mod||{};
  R(c,sx-8,sy-8,sw+16,sh+16,'#3a434e',10);R(c,sx,sy,sw,sh,'#cfe8f4',6);
  c.save();c.beginPath();c.roundRect(sx,sy,sw,sh,6);c.clip();
  R(c,sx,sy,sw,sh,'#7fb8d8',0);P(c,[[sx+sw*.1,sy+sh*.2],[sx+sw*.5,sy+sh*.1],[sx+sw*.62,sy+sh*.42],[sx+sw*.42,sy+sh*.62],[sx+sw*.3,sy+sh*.9],[sx+sw*.12,sy+sh*.62]],'#a7cf97');
  E(c,sx+sw*.8,sy+sh*.68,sw*.06,sh*.04,'#a7cf97');E(c,sx+sw*.72,sy+sh*.85,sw*.04,sh*.03,'#a7cf97');
  const sw0=w.reduced?0:w.time*1.2;c.globalAlpha=.25;P(c,[[sx+sw*.4,sy+sh*.5],[sx+sw*.4+Math.cos(sw0)*sw,sy+sh*.5+Math.sin(sw0)*sw],[sx+sw*.4+Math.cos(sw0+.35)*sw,sy+sh*.5+Math.sin(sw0+.35)*sw]],'#ffffff');c.globalAlpha=1;
  const icons={storms:'⛈️',fog:'🌫️',wind:'🌬️',rough:'🌬️',early:'🌫️'};
  legs(w).slice(0,3).forEach((l,i)=>{const px=sx+sw*[.3,.78,.66][i],py=sy+sh*[.3,.66,.86][i],wx=l.t?.needs?.wx?.emoji||icons[m.id]||'☀️';E(c,px,py,14*k,14*k,'#ffffffcc');T(c,wx,px,py+1,g.port?16:14);T(c,upper(l.to),px,py+22*k,g.port?12:10,DARK,800);});
  c.restore();
  R(c,sx,sy+sh-24*k,sw,24*k,'#1d242cdd',0);T(c,`${m.emoji||'🌤️'} ${m.label||'Trời đẹp, gió nhẹ'}`,sx+sw/2,sy+sh-12*k,fit(c,`${m.emoji||'🌤️'} ${m.label||'Trời đẹp, gió nhẹ'}`,sw-16,g.port?14:12),WHITE,700);
  departures(c,w,g,g.X(.62),g.H(.16),g.f.w*.18,g.H(.56)-g.H(.16),{rows:3});
  // Coffee machine with a wisp of steam, the lockers with caps on top.
  const cx=g.X(.745);R(c,cx-30*k,g.base-96*k,60*k,90*k,'#59626c',8*k);R(c,cx-22*k,g.base-86*k,44*k,26*k,'#2b3138',4);T(c,'☕',cx,g.base-73*k,16*k);R(c,cx-12*k,g.base-34*k,24*k,22*k,WHITE,3);
  if(!w.reduced){const s=(w.time*.8)%1;c.globalAlpha=.5*(1-s);E(c,cx+Math.sin(w.time*2)*4,g.base-46*k-s*40*k,6*k,10*k,'#ffffff');c.globalAlpha=1;}
  for(let i=0;i<3;i++){const lx=g.X(.825)+i*g.f.w*.05;R(c,lx,g.H(.3),g.f.w*.047,g.base-g.H(.3),['#8fb2cf','#9fc0d8','#8fb2cf'][i],4,'#6d8aa5',1.5);
    for(let j=0;j<3;j++)L(c,lx+8,g.H(.36)+j*6,lx+g.f.w*.047-8,g.H(.36)+j*6,'#6d8aa5',1.5);E(c,lx+g.f.w*.04,g.H(.62),2.5,2.5,'#f2d48c');
    T(c,['VÂN','THU','BẠN'][i],lx+g.f.w*.0235,g.H(.48),g.port?11:10,NAVY_D,800);}
  R(c,g.X(.84),g.H(.24),26*k,9*k,NAVY,4);R(c,g.X(.835),g.H(.27),36*k,5*k,NAVY_D,2);
  plate(c,g,g.X(.5),g.H(.08),'PHÒNG TỔ BAY · CÁNH CÒ',{bg:NAVY});
});}
function crewProps(w,p){const c=w.ctx,g=geo(w.isPortrait()),k=g.k,t=task(w),out=[];
  // The briefing table: fuel sheet, weather print-out, the flight bag; it glows while the brief is the step.
  out.push([g.Y(.52),()=>{const x0=g.X(.36),x1=g.X(.64),y0=g.Y(.36),y1=g.Y(.52),glow=w.c?.open&&t&&!fa(w)&&t.stage==='brief';
    E(c,(x0+x1)/2,y1+4,(x1-x0)/2+10,9,'#00000020');if(glow)E(c,(x0+x1)/2,(y0+y1)/2,(x1-x0)/2+22,(y1-y0)/2+16,'#f2c14e44');
    R(c,x0,y0-30*k,x1-x0,26*k,'#e9dcc7',8,'#c4ad8e',2);R(c,x0+14,y0-6*k,10,y1-y0,'#b39b7d',3);R(c,x1-24,y0-6*k,10,y1-y0,'#b39b7d',3);
    R(c,x0+30*k,y0-40*k,54*k,30*k,WHITE,3,'#c4ccd3',1);T(c,'PHIẾU DẦU',x0+57*k,y0-31*k,g.port?10:9,NAVY,800);
    const fuel=t&&!fa(w)&&t.fuel!=null;L(c,x0+36*k,y0-20*k,x0+(fuel?78:52)*k,y0-20*k,fuel?TEAL:'#c4ccd3',3);
    R(c,(x0+x1)/2-24*k,y0-42*k,48*k,32*k,'#f4f8fb',3,'#9fb8c8',1);T(c,t?.needs?.wx?.emoji||w.c?.data?.mod?.emoji||'🌤️',(x0+x1)/2,y0-27*k,16*k);
    R(c,x1-84*k,y0-44*k,46*k,34*k,NAVY,6);L(c,x1-70*k,y0-44*k,x1-70*k,y0-52*k,GREY_D,3);L(c,x1-52*k,y0-44*k,x1-52*k,y0-52*k,GREY_D,3);
    R(c,x1-30*k,y0-36*k,14*k,16*k,'#f4ece0',3);}]);
  // The sign-in desk.
  out.push([g.Y(.6),()=>{const x0=g.X(.78),x1=g.X(.95),y0=g.Y(.46),y1=g.Y(.6),open=w.c?.open;E(c,(x0+x1)/2,y1+3,(x1-x0)/2+6,7,'#00000020');
    R(c,x0,y0-46*k,x1-x0,y1-y0+46*k,'#eef2f5',8,GREY_D,2);R(c,x0,y0-46*k,x1-x0,12*k,fa(w)?TEAL:NAVY,6);
    const s=open?'ĐÃ BÁO DANH':'BÁO DANH';T(c,s,(x0+x1)/2,y0-14*k,fit(c,s,x1-x0-16,g.port?14:12),open?TEAL:NAVY_D,800);
    R(c,(x0+x1)/2-20*k,y0-80*k,40*k,30*k,DARK,4);T(c,open?'✓':'🪪',(x0+x1)/2,y0-65*k,15*k,open?GREEN:WHITE,800);}]);
  return out;}

/* ------------------------------------------------------------ Sảnh ga */
const HALL=both(g=>({
  home:[g.X(.5),g.Y(.78)],
  blocks:[box(g,.08,0,.44,.13),box(g,.6,.3,.77,.44),box(g,.81,.3,.89,.42)],
  labels:{warehouse:'Bảng giờ bay','look:checkin':'Quầy làm thủ tục','look:security':'Soi chiếu an ninh'},
  spots:{warehouse:spotAt(g,[g.X(.63),g.H(.3)],75,[.62,.2]),'look:checkin':spotAt(g,[g.X(.26),g.Y(0)-40*g.k],70,[.26,.3]),
    'look:security':spotAt(g,[g.X(.69),g.Y(.3)-40*g.k],55,[.69,.58]),
    'go:crew':spotAt(g,[g.X(.05),g.H(.62)],50,[.05,.22]),'go:gate':spotAt(g,[g.X(.94),g.H(.62)],50,[.94,.2])},
}));
const HALL_LOOKS={
  checkin:w=>{const l=legs(w)[0]||{};return `Khách đi ${l.to||'đảo'} xếp hàng từ sớm. Có bà còn ôm theo cả thùng xoài.`;},
  security:()=>'Soi chiếu: tháo thắt lưng, bỏ chai nước ra ngoài, máy tính để riêng một khay.',
};
function hall(w,p){shell(w,{wall:'#eef2f5',wallLow:'#dfe6ec',floor:'#e9e4da',floor2:'#ded7ca',tile:90,rim:'#9fb0bf',trim:'#c4ccd3'},(c,g)=>{
  const k=g.k;ceiling(c,g);
  // The glass wall onto the apron, between the two doors.
  windowPane(c,w,g.X(.11),g.H(.12),g.f.w*.78,g.H(.8)-g.H(.12),{frame:'#cfd8df',bars:5,r:6,sill:false,view:apronView(w)});
  doorway(c,g,.05,{color:'#6d8aa5'});
  doorway(c,g,.94,{color:NAVY,glass:GLASS});
  departures(c,w,g,g.X(.5),g.H(.14),g.f.w*.27,g.H(.5)-g.H(.14),{rows:4});
  L(c,g.X(.56),g.f.y,g.X(.56),g.H(.14),GREY_D,2);L(c,g.X(.72),g.f.y,g.X(.72),g.H(.14),GREY_D,2);
  // Check-in: three desks with numbers and a belt carrying bags behind them.
  R(c,g.X(.08),g.base-70*k,g.f.w*.36,22*k,'#59626c',4);
  const belt=w.reduced?0:(w.time*30)%(g.f.w*.36);for(let i=0;i<4;i++){const bx=g.X(.08)+(belt+i*g.f.w*.09)%(g.f.w*.36);suitcase(c,bx,g.base-66*k,.6*k,['#d07a5c','#5b8fb9','#e3b04b','#8fbf8a'][i]);}
  for(let i=0;i<3;i++)plate(c,g,g.X(.14+i*.12),g.base-92*k,`QUẦY ${i+1}`,{bg:TEAL,size:g.port?12:10,pad:8});
  // Security: queue tape on the floor.
  c.setLineDash([8,6]);L(c,g.X(.56),g.Y(.52),g.X(.92),g.Y(.52),'#c96f5a',3);c.setLineDash([]);
  T(c,'AN NINH',g.X(.74),g.Y(.58),g.port?14:12,'#c96f5a',800);
});
  announce(w,geo(w.isPortrait()),geo(w.isPortrait()).X(.3),geo(w.isPortrait()).H(.62));
}
function hallProps(w,p){const c=w.ctx,g=geo(w.isPortrait()),k=g.k,out=[];
  out.push([g.Y(.13),()=>{for(let i=0;i<3;i++){const x=g.X(.08+i*.12),wd=g.f.w*.1;R(c,x+4,g.Y(0)-46*k,wd,g.Y(.13)-g.Y(0)+46*k,'#eef2f5',6,GREY_D,1.5);R(c,x+4,g.Y(0)-46*k,wd,10*k,TEAL,4);
    R(c,x+wd*.55,g.Y(0)-74*k,26*k,22*k,DARK,3);T(c,'✈',x+wd*.55+13*k,g.Y(0)-63*k,12*k,YEL);
    sitter(c,x+wd*.3,g.Y(0)-40*k,.75*k,40+i);}}]);
  // The X-ray belt with trays sliding through, and the arch with its green light.
  out.push([g.Y(.44),()=>{const x0=g.X(.6),x1=g.X(.77),y0=g.Y(.3),y1=g.Y(.44);E(c,(x0+x1)/2,y1+3,(x1-x0)/2+6,7,'#00000020');
    R(c,x0,y0-20*k,x1-x0,26*k,'#59626c',4);R(c,x0+(x1-x0)*.35,y0-62*k,(x1-x0)*.32,60*k,'#cfd8df',8,GREY_D,2);R(c,x0+(x1-x0)*.4,y0-44*k,(x1-x0)*.22,26*k,'#1d242c',4);
    const sl=w.reduced?0:(w.time*24)%(x1-x0);for(let i=0;i<3;i++){const tx=x0+(sl+i*(x1-x0)/3)%(x1-x0-30*k);R(c,tx,y0-30*k,30*k,10*k,'#9aa6b1',3);}
    L(c,x0+8,y0+4,x0+8,y1,'#59626c',4);L(c,x1-8,y0+4,x1-8,y1,'#59626c',4);}]);
  out.push([g.Y(.42),()=>{const x0=g.X(.81),x1=g.X(.89),top=g.Y(.3)-118*k;R(c,x0,top,x1-x0,16*k,'#cfd8df',4,GREY_D,1.5);R(c,x0,top,14*k,g.Y(.42)-top,'#cfd8df',3,GREY_D,1.5);R(c,x1-14*k,top,14*k,g.Y(.42)-top,'#cfd8df',3,GREY_D,1.5);
    const red=beat(w,6,9);E(c,(x0+x1)/2,top+8*k,5*k,5*k,red.on&&red.k>.85?RED:GREEN);}]);
  // Passers-by with luggage crossing the hall.
  for(let i=0;i<(g.port?2:3);i++){const v=[.62,.86,.74][i],per=[22,30,26][i],b=w.reduced?{k:[.3,.7,.5][i]}:{k:((w.time+i*9)%per)/per},dir=i%2?-1:1,u=dir>0?.04+b.k*.92:.96-b.k*.92;
    out.push([g.Y(v),()=>passer(c,g.X(u),g.Y(v),1.15*k,70+i,dir,w.reduced?0:w.time+i)]);}
  out.push([g.Y(.44)+1,()=>passer(c,g.X(.92),g.Y(.46),1.1*k,99,-1,0,{bag:false})]);
  return out;}

/* ------------------------------------------------------------ Cổng ra tàu */
const GATE=both(g=>({
  home:[g.X(.36),g.Y(.61)],
  blocks:[box(g,.62,.08,.8,.22),box(g,.08,.4,.48,.5),box(g,.08,.72,.48,.82)],
  customers:[[g.X(.58),g.Y(.36)],[g.X(.68),g.Y(.5)],[g.X(.8),g.Y(.4)],[g.X(.7),g.Y(.72)]],
  labels:{counter:'Quầy cửa ra tàu','look:window':'Cửa kính nhìn ra sân đỗ'},
  spots:{counter:spotAt(g,[g.X(.71),g.Y(.08)-44*g.k],60,[.71,.32],[.55,.2]),'look:window':spotAt(g,[g.X(.3),g.H(.55)],70,[.3,.22]),
    'go:terminal':spotAt(g,[g.X(.05),g.H(.62)],50,[.05,.22]),'go:apron':spotAt(g,[g.X(.92),g.H(.62)],50,[.91,.2])},
}));
const GATE_LOOKS={window:w=>flying(w)?'Sân đỗ vắng: chuyến của mình đang trên trời.':'Cò Trắng đậu ngay ngoài kia, xe hành lý chạy tới chạy lui.'};
function gateRoom(w,p){shell(w,{wall:'#eef2f5',wallLow:'#dfe6ec',floor:'#7d97ad',floor2:'#7590a6',tile:64,rim:'#8fa3b5',trim:'#c4ccd3'},(c,g)=>{
  const k=g.k;ceiling(c,g);
  windowPane(c,w,g.X(.11),g.H(.12),g.f.w*.74,g.H(.82)-g.H(.12),{frame:'#cfd8df',bars:4,r:6,sill:false,view:apronView(w,{plane:!flying(w)})});
  doorway(c,g,.05,{color:'#6d8aa5'});
  doorway(c,g,.92,{color:NAVY,glass:GLASS,open:!!w.c?.open});
  // The gate sign: number, flight, destination, time.
  const t=task(w),l=t?.leg||legs(w)[0]||{},x=g.X(.71),y=g.H(.2);
  R(c,x-g.f.w*.12,y-26*k,g.f.w*.24,58*k,'#1d242c',8);T(c,`CỬA ${l.gate||'1'}`,x-g.f.w*.08,y+3*k,g.port?18:16,YEL,800);
  T(c,`${l.code||''} · ${upper(l.to)}`,x+g.f.w*.04,y-8*k,fit(c,`${l.code||''} · ${upper(l.to)}`,g.f.w*.13,g.port?13:11),WHITE,700);T(c,l.dep||'',x+g.f.w*.04,y+14*k,g.port?13:11,GREEN,700);
  // Stanchions and the queue tape.
  for(let i=0;i<4;i++){const sx=g.X(.52+i*.03);L(c,sx,g.Y(.3),sx,g.Y(.3)-30*k,GREY_D,3);E(c,sx,g.Y(.3),5*k,2*k,GREY_D);}L(c,g.X(.52),g.Y(.3)-26*k,g.X(.61),g.Y(.3)-26*k,'#c96f5a',3);
});
  announce(w,geo(w.isPortrait()),geo(w.isPortrait()).X(.36),geo(w.isPortrait()).H(.6),{gate:true});
}
function gateProps(w,p){const c=w.ctx,g=geo(w.isPortrait()),k=g.k,out=[],t=task(w);
  out.push([g.Y(.22),()=>{const x0=g.X(.62),x1=g.X(.8),y0=g.Y(.08),y1=g.Y(.22),board=fa(w)&&t?.kind==='board';E(c,(x0+x1)/2,y1+3,(x1-x0)/2+8,7,'#00000020');
    if(board)E(c,(x0+x1)/2,(y0+y1)/2,(x1-x0)/2+20,(y1-y0)/2+14,'#f2c14e44');
    R(c,x0,y0-44*k,x1-x0,y1-y0+44*k,'#eef2f5',8,GREY_D,2);R(c,x0,y0-44*k,x1-x0,12*k,fa(w)?TEAL:NAVY,6);
    const s=board?'ĐANG LÊN TÀU':w.c?.open?'ĐÚNG GIỜ':'CHƯA MỞ';T(c,s,(x0+x1)/2,y0-12*k,fit(c,s,x1-x0-14,g.port?14:12),board?'#c47f12':NAVY_D,800);
    R(c,x1-48*k,y0-80*k,40*k,30*k,DARK,4);T(c,'▤',x1-28*k,y0-65*k,14*k,GREEN);}]);
  // Two rows of seats with people waiting (a sleeper, a reader, a kid, bags under the seats).
  for(const [row,v0,v1] of [[0,.4,.5],[1,.72,.82]])out.push([g.Y(v1),()=>{const x0=g.X(.08),x1=g.X(.48),n=5,sw=(x1-x0)/n;
    E(c,(x0+x1)/2,g.Y(v1)+3,(x1-x0)/2+6,7,'#00000020');
    for(let i=0;i<n;i++){const sx=x0+i*sw,seed=row*7+i,h=hash(seed+(w.c?.day||0));
      R(c,sx+3,g.Y(v0)-46*k,sw-6,50*k,'#2f5d8a',8*k);
      if(h>.28)sitter(c,sx+sw/2,g.Y(v0)-6*k,.95*k,seed+(w.c?.day||0)*13,h>.9?'sleep':h>.75?'read':h>.6?'phone':h<.36?'kid':'');
      else suitcase(c,sx+sw/2,g.Y(v0)+2*k,.85*k,['#d07a5c','#5b8fb9','#e3b04b'][i%3]);
      R(c,sx+2,g.Y(v0)-6*k,sw-4,16*k,'#3e6f9c',5*k);}
    L(c,x0+10,g.Y(v0)+10*k,x0+10,g.Y(v1),GREY_D,4);L(c,x1-10,g.Y(v0)+10*k,x1-10,g.Y(v1),GREY_D,4);}]);
  // A small moment: a child runs to the window with a balloon.
  const b=beat(w,18,4);if(b.on&&b.k<.5){const u=.5-b.k*.8;out.push([g.Y(.62),()=>{passer(c,g.X(u),g.Y(.62),.85*k,4,-1,w.time,{bag:false});L(c,g.X(u)-4,g.Y(.62)-50*k,g.X(u)-8,g.Y(.62)-110*k,'#9aa6b1',1);E(c,g.X(u)-8,g.Y(.62)-122*k,13*k,15*k,'#f08aa8');}]);}
  return out;}

/* ------------------------------------------------------------ Buồng lái */
const COCKPIT=both(g=>({
  home:[g.X(.5),g.Y(.8)],
  blocks:[box(g,.17,.22,.35,.42),box(g,.55,.22,.73,.42),box(g,.4,.18,.5,.38)],
  labels:{workbench:'Bảng điều khiển',evidence:'Màn hình thời tiết','look:captain':'Cơ trưởng Vân'},
  spots:{workbench:spotAt(g,[g.X(.62),g.H(.74)],75,[.64,.56],[.52,.5]),evidence:spotAt(g,[g.X(.79),g.H(.72)],55,[.8,.3]),
    'look:captain':spotAt(g,[g.X(.26),g.Y(.42)-120*g.k],55,[.26,.58]),'go:cabin':spotAt(g,[g.X(.93),g.H(.62)],50,[.93,.26])},
}));
const COCKPIT_LOOKS={captain:w=>{const t=task(w),st=t?.stage;
  if(fa(w))return 'Chị Vân cười: “Khoang khách ổn chứ em? Có gì báo chị liền nhé.”';
  if(!w.c?.open)return 'Ghế cơ trưởng còn trống. Chị Vân đang uống cà phê ở phòng tổ bay.';
  return st==='start'?'“Đọc từng dòng nhé, không vội. Checklist là bạn của mình.”':st==='cruise'?'“Mắt trên đồng hồ, tai nghe đài. Giữ độ cao này.”':st==='approach'?'“Ổn định ở cổng đầu chưa? Chưa ổn thì bay lại, không xấu hổ gì cả.”':'“Bản tin xong thì mình ra vòng quanh tàu nhé.”';}};
/** Out of the windshield: the apron on the ground, clouds streaming in cruise, the runway lights on approach. */
function windshieldView(w){const t=task(w),st=fa(w)?null:t?.stage,air=flying(w),final=st==='approach';
  return (c,x,y,wd,ht)=>{
    if(final){const gy=y+ht*.62;R(c,x,gy,wd,ht,'#7c8f6c',0);const zoom=w.reduced?.5:(w.time*.15)%1;
      P(c,[[x+wd*.47,gy],[x+wd*.53,gy],[x+wd*(.62+zoom*.1),y+ht],[x+wd*(.38-zoom*.1),y+ht]],'#4b525a');
      for(let i=0;i<5;i++){const v=((i/5+zoom)%1),yy=gy+v*v*(ht*.38);R(c,x+wd*.5-2-v*4,yy,4+v*8,3+v*6,WHITE,1);}
      for(let i=0;i<4;i++)E(c,x+wd*(.4+i*.065),gy-3,3,3,i<2?RED:WHITE);}
    else if(air){const drift=w.reduced?0:w.time*40;R(c,x,y+ht*.78,wd,ht,'#b9d4e6',0);
      for(let i=0;i<5;i++){const cx=x+((i*173-drift)%(wd+160)+wd+160)%(wd+160)-80,cy=y+ht*(.35+(i%3)*.16),s=.7+(i%2)*.4;E(c,cx,cy,44*s,14*s,'#ffffffdd');E(c,cx-28*s,cy+4,26*s,10*s,'#ffffffdd');E(c,cx+30*s,cy+3,30*s,11*s,'#ffffffdd');}}
    else{const gy=y+ht*.6;R(c,x,gy,wd,ht,'#c3c9ce',0);L(c,x+wd*.5,gy,x+wd*.5,y+ht,YEL,4);L(c,x,gy+ht*.2,x+wd,gy+ht*.18,YEL,2);
      R(c,x+wd*.08,gy-ht*.24,wd*.22,ht*.24,'#eef2f5',3,GREY_D,1);for(let i=0;i<4;i++)R(c,x+wd*(.1+i*.05),gy-ht*.18,wd*.035,ht*.14,GLASS,2);
      planeSide(c,x+wd*.78,gy+ht*.1,Math.min(.6,wd/900),{tail:TEAL});}
  };}
function cockpitRoom(w,p){shell(w,{wall:'#3a434e',floor:'#4b545e',floor2:'#47505a',tile:40,rim:'#2b3138',trim:'#2b3138'},(c,g)=>{
  const k=g.k,f=g.f,t=task(w),pilot=!fa(w),wx=t?.needs?.wx;
  // Windshield: four panes under the roof, then the glare shield.
  const wy=g.H(.04),wh=g.H(.44)-wy;
  windowPane(c,w,g.X(.06),wy,g.X(.9)-g.X(.06),wh,{frame:'#2b3138',bars:3,barW:12*k,r:16,sill:false,view:windshieldView(w)});
  R(c,g.X(.04),g.H(.44),g.f.w*.86,g.H(.52)-g.H(.44),'#1f252b',10);
  // The overhead row: the before-start checklist as five switches, lit in the task's order.
  const done=pilot&&t?(t.switches||[]).length:0,next=pilot&&t?.stage==='start'?done:-1;
  for(let i=0;i<5;i++){const sx=g.X(.33+i*.06),sy=g.H(.48);R(c,sx-14*k,sy-8*k,28*k,22*k,'#2b3138',4);
    const on=i<done,blink=i===next&&!w.reduced&&Math.sin(w.time*5)>0;L(c,sx,sy+8*k,sx,sy+(on?-6:14)*k,'#d7dde2',4*k);E(c,sx+10*k,sy-2*k,3.5*k,3.5*k,on?GREEN:blink?YEL:'#5a636d');}
  // The main panel: two flight displays per side, the engine and fuel page in the middle.
  R(c,g.X(.04),g.H(.52),g.f.w*.86,g.base-g.H(.52),'#2b3138',8);
  const scr=(u,wd,draw)=>{const x=g.X(u),y=g.H(.58),hh=g.base-g.H(.58)-14*k,ww=f.w*wd;R(c,x-4,y-4,ww+8,hh+8,'#14191e',6);R(c,x,y,ww,hh,'#0f2a3a',4);c.save();c.beginPath();c.rect(x,y,ww,hh);c.clip();draw(x,y,ww,hh);c.restore();};
  const attitude=(x,y,ww,hh)=>{const tilt=w.reduced||!flying(w)?0:Math.sin(w.time*.6)*.06;c.save();c.translate(x+ww/2,y+hh/2);c.rotate(tilt);R(c,-ww,-hh,ww*2,hh,'#4c8cc4',0);R(c,-ww,0,ww*2,hh,'#9a6b45',0);L(c,-ww,0,ww,0,WHITE,2);c.restore();L(c,x+ww*.3,y+hh/2,x+ww*.45,y+hh/2,YEL,3);L(c,x+ww*.55,y+hh/2,x+ww*.7,y+hh/2,YEL,3);};
  const nav=(x,y,ww,hh)=>{c.strokeStyle='#8fe0a066';c.lineWidth=1.5;c.beginPath();c.arc(x+ww/2,y+hh*.9,hh*.7,Math.PI*1.15,Math.PI*1.85);c.stroke();P(c,[[x+ww/2,y+hh*.72],[x+ww/2-6,y+hh*.86],[x+ww/2+6,y+hh*.86]],WHITE);E(c,x+ww*.6,y+hh*.35,3,3,'#e07be0');L(c,x+ww/2,y+hh*.72,x+ww*.6,y+hh*.35,'#e07be0',1.5);};
  scr(.07,.11,attitude);scr(.19,.11,nav);
  scr(.32,.24,(x,y,ww,hh)=>{// engines and fuel: the needle shows the fuel loaded against full tanks
    for(let i=0;i<2;i++){const cx=x+ww*(.2+i*.22),cy=y+hh*.45,r=hh*.26;c.strokeStyle='#5a636d';c.lineWidth=3;c.beginPath();c.arc(cx,cy,r,Math.PI*.8,Math.PI*2.2);c.stroke();
      const a=Math.PI*.8+Math.PI*1.4*(w.c?.open&&(flying(w)||t?.stage==='start')?.72:.05);L(c,cx,cy,cx+Math.cos(a)*r,cy+Math.sin(a)*r,GREEN,2.5);T(c,i?'ĐC 2':'ĐC 1',cx,cy+r+10*k,g.port?10:9,'#9fb3c8',700);}
    const fuel=pilot&&t?.fuel!=null?t.fuel:null,need=pilot&&t?.needs?.fuel?(t.needs.fuel.trip||0)+(t.needs.fuel.alt||0)+(t.needs.fuel.reserve||0):null,max=Math.max(1,...(t?.needs?.fuel?.options||[fuel||1]));
    const fx=x+ww*.66,fy=y+hh*.18,fw=ww*.24,fh=hh*.62;R(c,fx,fy,fw,fh,'#14191e',3);
    if(fuel!=null)R(c,fx+3,fy+fh-fh*Math.min(1,fuel/max),fw-6,fh*Math.min(1,fuel/max),fuel>=(need||0)?TEAL:'#d98b3a',2);
    if(need)L(c,fx-4,fy+fh-fh*Math.min(1,need/max),fx+fw+4,fy+fh-fh*Math.min(1,need/max),YEL,2);
    const label=fuel!=null?`${Number(fuel).toLocaleString('vi-VN')} kg`:'DẦU';T(c,label,fx+fw/2,fy+fh+10*k,fit(c,label,ww*.34,g.port?10:9),fuel!=null?WHITE:'#9fb3c8',700);});
  scr(.58,.11,attitude);
  scr(.71,.12,(x,y,ww,hh)=>{// the weather radar: today's weather at the destination
    c.strokeStyle='#8fe0a055';c.lineWidth=1;for(let r=1;r<4;r++){c.beginPath();c.arc(x+ww/2,y+hh,hh*r/3.4,Math.PI,0);c.stroke();}
    const id=wx?.id||'',storm=/storm/.test(id)||w.c?.data?.mod?.id==='storms';
    if(storm){E(c,x+ww*.62,y+hh*.42,ww*.16,hh*.14,'#e0b84a99');E(c,x+ww*.62,y+hh*.42,ww*.08,hh*.07,'#e0605099');}else if(id){E(c,x+ww*.35,y+hh*.5,ww*.12,hh*.08,'#7fd08a66');}
    if(!w.reduced){const a=Math.PI+((w.time*.9)%1)*Math.PI;L(c,x+ww/2,y+hh,x+ww/2+Math.cos(a)*hh*.9,y+hh+Math.sin(a)*hh*.9,'#8fe0a0aa',1.5);}
    T(c,wx?.emoji||w.c?.data?.mod?.emoji||'🌤️',x+ww*.82,y+hh*.2,g.port?15:13);});
  // A caution light: amber when something on the way needs a decision.
  const caution=pilot&&t?.needs?.event&&t.stage==='cruise',blink=caution&&(w.reduced||Math.sin(w.time*4)>0);
  R(c,g.X(.5)-18*k,g.H(.53),36*k,14*k,blink?'#f2a33a':'#4a4f55',4);T(c,'CAUTION',g.X(.5),g.H(.53)+7*k,7*k,blink?DARK:'#6d747c',800);
  // Landing gear: three green after the wheels are down.
  for(let i=0;i<3;i++)E(c,g.X(.86)+i*12*k,g.H(.6),4*k,4*k,!flying(w)||t?.stage==='approach'?GREEN:'#5a636d');
  doorway(c,g,.94,{color:'#59626c',frame:'#2b3138'});
});}
function cockpitProps(w,p){const c=w.ctx,g=geo(w.isPortrait()),k=g.k,out=[];
  const seat=(u0,u1,who)=>{const x0=g.X(u0),x1=g.X(u1),y=g.Y(.42),cx=(x0+x1)/2,wd=x1-x0;E(c,cx,y+3,wd/2+6,7,'#00000030');
    if(who){E(c,cx,y-128*k,26*k,26*k,'#3a2f2a');E(c,cx-20*k,y-120*k,7*k,10*k,'#3a2f2a');R(c,cx-28*k,y-152*k,56*k,14*k,NAVY_D,6);R(c,cx-20*k,y-163*k,40*k,15*k,NAVY,6);T(c,'★',cx,y-155*k,9*k,YEL);
      R(c,cx-30*k,y-120*k,6*k,22*k,'#2b3138',3);L(c,cx-27*k,y-140*k,cx+27*k,y-140*k,'#2b3138',3);}
    R(c,x0+wd*.12,y-118*k,wd*.76,100*k,'#3e4954',22*k,'#232a31',2);R(c,x0+wd*.24,y-110*k,wd*.52,28*k,'#55616d',12*k);
    R(c,x0,y-40*k,wd,22*k,'#3e4954',10*k);R(c,cx-6,y-20*k,12,20*k,'#232a31',3);};
  out.push([g.Y(.42),()=>seat(.17,.35,!!w.c?.open)]);
  out.push([g.Y(.42)+1,()=>seat(.55,.73,false)]);
  out.push([g.Y(.38),()=>{const x0=g.X(.4),x1=g.X(.5),y=g.Y(.38);R(c,x0,y-70*k,x1-x0,70*k,'#2b3138',8);for(let i=0;i<2;i++){const lx=x0+(x1-x0)*(.33+i*.34),up=flying(w)?14:30;L(c,lx,y-46*k,lx,y-(46+up)*k,'#9aa6b1',5*k);R(c,lx-7*k,y-(52+up)*k,14*k,10*k,'#d7dde2',3);}}]);
  return out;}

/* ------------------------------------------------------------ Khoang khách */
const CABIN=both(g=>({
  home:[g.X(.8),g.Y(.6)],
  blocks:[box(g,.19,0,.86,.17),box(g,.19,.78,.86,1.05),box(g,.07,0,.16,.14),box(g,.47,.36,.53,.47)],
  customers:[[g.X(.3),g.Y(.45)],[g.X(.68),g.Y(.42)],[g.X(.38),g.Y(.62)],[g.X(.6),g.Y(.62)]],
  labels:{workbench:'Xe đẩy suất ăn',shelf:'Bếp tàu','look:bell':'Đèn gọi tiếp viên'},
  spots:{workbench:spotAt(g,[g.X(.5),g.Y(.36)-40*g.k],55,[.5,.58],[.42,.3]),shelf:spotAt(g,[g.X(.115),g.H(.66)],55,[.12,.28]),
    'look:bell':spotAt(g,[g.X(.55),g.H(.22)],45,[.56,.27]),
    'go:apron':spotAt(g,[g.X(.04),g.H(.6)],45,[.045,.3]),'go:cockpit':spotAt(g,[g.X(.93),g.H(.6)],50,[.93,.3])},
}));
const CABIN_LOOKS={bell:w=>fa(w)?'Đèn gọi sáng ở hàng 5: có người xin thêm chăn.':'Khách gọi tiếp viên. Chị Thu đi tới liền.'};
/** Rows shown along the cabin and what the service task says about them. */
function cabinRows(w){
  const t=task(w),rows=fa(w)&&t?.kind==='service'?t.needs?.rows:null;
  return Array.from({length:8},(_,i)=>{const r=rows?.[i%rows.length],seat=r?.seats?.[0];
    return {no:r?.row||i+1,served:!!(rows&&i<rows.length&&(i<(t.row||0)||seat?.given?.length)),kind:seat?.kind||'',known:!!r?.seats};});
}
function cabinRoom(w,p){shell(w,{wall:'#f1ede6',wallLow:'#e1dbd0',floor:'#5e7d9a',floor2:'#56748f',tile:46,rim:'#9fb0bf',trim:'#d5cec2'},(c,g)=>{
  const k=g.k,air=flying(w),turb=w.c?.data?.turb?.stage==='coming',t=task(w);
  // Curved ceiling and the overhead bins with row numbers and the seat-belt signs.
  R(c,g.f.x,g.f.y,g.f.w,g.H(.06)-g.f.y,'#e4dfd6',0);
  const rows=cabinRows(w),x0=g.X(.19),span=g.X(.86)-x0,cw=span/rows.length;
  R(c,x0-6,g.H(.08),span+12,g.H(.3)-g.H(.08),'#e9e4da',12,'#cfc7b9',2);
  const belt=turb||!air||(t&&['board','demo'].includes(t.kind)),blink=turb&&!w.reduced&&Math.sin(w.time*6)<0;
  rows.forEach((r,i)=>{const bx=x0+i*cw;L(c,bx+cw,g.H(.09),bx+cw,g.H(.29),'#cfc7b9',1.5);T(c,String(r.no),bx+cw/2,g.H(.27),g.port?11:10,'#8d8579',800);
    if(i%2===0){R(c,bx+cw/2-14*k,g.H(.31),28*k,12*k,'#2f3d4a',3);T(c,'⛓',bx+cw/2,g.H(.31)+6*k,8*k,belt&&!blink?YEL:'#59626c');}});
  // The windows: ground or sky, by where the flight is.
  rows.forEach((r,i)=>{const bx=x0+i*cw+cw*.28,wy=g.H(.42),ww=cw*.44,wh=g.H(.64)-wy;
    windowPane(c,w,bx,wy,ww,wh,{frame:'#e1dbd0',bars:0,r:ww/2,sill:false,view:(cc,x,y,wd,ht)=>{
      if(air){const d=w.reduced?0:(w.time*30+i*40)%(wd+60);E(cc,x+wd-d+20,y+ht*.55,22,8,'#ffffffcc');R(cc,x,y+ht*.85,wd,ht,'#b9d4e6',0);}
      else{R(cc,x,y+ht*.62,wd,ht,'#c3c9ce',0);L(cc,x,y+ht*.75,x+wd,y+ht*.72,YEL,2);}}});});
  // Rear door (to the airstairs) and the galley with its drawers; the cockpit door at the front.
  doorway(c,g,.04,{color:'#8d979f',frame:'#d5cec2',open:!air&&!!w.c?.open});
  R(c,g.X(.07),g.H(.36),g.f.w*.09,g.base-g.H(.36),'#d9d4cb',6,'#bfb7a9',1.5);for(let j=0;j<4;j++)R(c,g.X(.075),g.H(.42)+j*(g.base-g.H(.42))/4.4,g.f.w*.08,(g.base-g.H(.42))/5,'#c9c2b6',3);
  T(c,'BẾP TÀU',g.X(.115),g.H(.39),g.port?11:10,'#7b7366',800);
  doorway(c,g,.93,{color:'#59626c',frame:'#d5cec2'});
  if(turb){const s='〰️ Thắt dây an toàn!';bubble(c,g,g.X(.5),g.H(.4),s,{color:'#fff2d6'});}
  else{const b=beat(w,9,2);if(b.on&&b.k>.6&&w.c?.open){const i=b.n%rows.length;T(c,'🔔',x0+i*cw+cw/2,g.H(.36),g.port?18:15);}}
});}
function cabinProps(w,p){const c=w.ctx,g=geo(w.isPortrait()),k=g.k,out=[],t=task(w),rows=cabinRows(w),x0=g.X(.19),cw=(g.X(.86)-x0)/rows.length;
  const turb=w.c?.data?.turb?.stage==='coming',shake=turb&&!w.reduced?Math.sin(w.time*23)*2:0,passengers=!!w.c?.open;
  // Back row: seats against the wall, people facing the aisle; a cup above those already served.
  out.push([g.Y(.17),()=>rows.forEach((r,i)=>{const cx=x0+i*cw+cw/2,y=g.Y(.14);
    R(c,cx-cw*.4,y-70*k,cw*.8,74*k,NAVY,10*k);R(c,cx-cw*.3,y-66*k,cw*.6,14*k,WHITE,5*k);heart(c,cx,y-56*k,.18*k,TEAL);
    const seed=i*11+(w.c?.day||0)*7,h=hash(seed);
    if(passengers&&(h>.12||r.known))sitter(c,cx,y-8*k+shake,.9*k,seed,r.kind==='sleep'?'sleep':r.kind==='kid'?'kid':h>.85?'read':'');
    R(c,cx-cw*.42,y-12*k,cw*.84,18*k,'#3e6f9c',6*k);
    if(r.served)T(c,'🥤',cx+cw*.28,y-60*k,g.port?15:12);})]);
  // The service cart in the aisle (drinks, snacks, the special-meal list clipped on).
  out.push([g.Y(.47),()=>{const x0c=g.X(.47),x1=g.X(.53),y=g.Y(.47),service=fa(w)&&t?.kind==='service',demo=fa(w)&&t?.kind==='demo';E(c,(x0c+x1)/2,y+3,(x1-x0c)/2+6,6,'#00000025');
    if(service)E(c,(x0c+x1)/2,y-20*k,(x1-x0c)/2+24,30*k,'#f2c14e33');
    R(c,x0c,y-66*k,x1-x0c,62*k,'#dfe5ea',5,GREY_D,1.5);R(c,x0c+3,y-60*k,x1-x0c-6,8*k,TEAL,2);E(c,x0c+6,y-2,4,4,'#3b3f45');E(c,x1-6,y-2,4,4,'#3b3f45');
    if(demo){P(c,[[x0c+4,y-104*k],[x1-4,y-104*k],[x1,y-70*k],[x0c,y-70*k]],'#f5c542');R(c,(x0c+x1)/2-4,y-80*k,8,7*k,RED,2);}
    else{for(let i=0;i<3;i++)R(c,x0c+6+i*((x1-x0c-12)/3),y-82*k,(x1-x0c-16)/3,16*k,['#f6a9b8','#d8b08a','#9fd6a8'][i],3);R(c,x1-12,y-50*k,14,18*k,WHITE,2,'#c4ccd3',1);}}]);
  // Front row: the backs of the seats nearest to us, with heads peeking over.
  out.push([g.Y(1.2),()=>rows.forEach((r,i)=>{const cx=x0+i*cw+cw/2,y=g.Y(.96),seed=i*5+3+(w.c?.day||0),h=hash(seed);
    if(passengers&&h>.3){E(c,cx,y-118*k+shake,18*k,16*k,['#4a3a33','#6e4f3c','#2f2a28','#8a6a50'][Math.floor(h*4)]);}
    R(c,cx-cw*.42,y-110*k,cw*.84,120*k,NAVY,14*k);R(c,cx-cw*.3,y-104*k,cw*.6,18*k,WHITE,6*k);heart(c,cx,y-90*k,.2*k,TEAL);R(c,cx-cw*.26,y-70*k,cw*.52,30*k,'#3e6f9c',5*k);})]);
  return out;}

/* ------------------------------------------------------------ the area list and where the work is */
export const AREAS=[
  {id:'crew',name:'Phòng tổ bay',icon:'☕',plan:CREW,room:crewRoom,props:crewProps,people:true,looks:{coffee:()=>'Cà phê phin pha sẵn. Một ngụm rồi đọc bản tin.'}},
  {id:'terminal',name:'Sảnh ga',icon:'🧳',plan:HALL,room:hall,props:hallProps,looks:HALL_LOOKS},
  {id:'gate',name:'Cổng ra tàu',icon:'🚪',plan:GATE,room:gateRoom,props:gateProps,people:true,looks:GATE_LOOKS},
  {id:'apron',name:'Sân đỗ',icon:'🛫',main:true},
  {id:'cabin',name:'Khoang khách',icon:'💺',plan:CABIN,room:cabinRoom,props:cabinProps,people:true,looks:CABIN_LOOKS},
  {id:'cockpit',name:'Buồng lái',icon:'🕹️',plan:COCKPIT,room:cockpitRoom,props:cockpitProps,looks:COCKPIT_LOOKS},
];
/** Where the work in hand happens: the crew room before and after the shift; the pilot's brief in the crew
 * room, the walk-around on the apron, the checklist, the flight and the approach in the cockpit; the flight
 * attendant's boarding at the gate, everything else in the cabin (always the cabin when turbulence comes). */
export function areaFor(w){
  const c=w.c;if(!c)return null;
  if(!c.open)return {key:'off:'+c.day,area:'crew'};
  const t=task(w);if(!t)return {key:'free'};
  if(!fa(w)){const st=t.stage,area=st==='brief'?'crew':st==='walk'?'apron':['start','cruise','approach'].includes(st)?'cockpit':'apron';
    return {key:t.id+':'+area,area,spot:area==='crew'||area==='cockpit'?'workbench':null};}
  const area=c.data?.turb?.stage==='coming'?'cabin':t.kind==='board'?'gate':'cabin';
  return {key:t.id+':'+area,area,spot:area==='gate'?'counter':'workbench'};
}
