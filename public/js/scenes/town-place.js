/** 🗺️ Bản đồ phố: the small town the player strolls on the home screen (v4/town-walk.js), every workplace a
 * storefront along a street. Six rows, top to bottom, each a row of buildings facing the street under it:
 *   0  🛕 Chùa · 🌾 Ngoại ô · ✈️ Sân bay       (pagoda; farm, homestay, school; tour desk, pilot, flight crew)
 *   1  🏢 Khu văn phòng                        (Ngân hàng, the accounting and office jobs)
 *   2  💇 Phố dịch vụ                          (salon, nail, photos, pets, repair, pharmacy, clothes; Gara)
 *   3  🛒 Phố chợ                              (the seven first-chapter shops, phở, cơm tấm, album ZPOP): a new player starts here
 *   4  🧺 Phố hàng rong                        (carts: trà đá, trái cây, kem, rác, cống; Cổng hội chợ, Nhóm phố, Đi dạo, 🎤 Phòng hát)
 *   5  🏠 Hẻm nhà · 🏗️ Công trình phố          (Nhà mình, the home careers, Quầy của bạn, Quảng trường; the six town
 *                                              projects, each painted for its stage: v4/town-projects-data.js)
 * Lanes between every few buildings (and a road round both ends) join one street to the next. A career this file
 * does not know yet joins the row of its kind, so a new career always has a door.
 * Walking: the walkable floor is a handful of rectangles (the streets, the lanes); a path goes from rectangle to
 * rectangle through the strips where they overlap (Dijkstra over ~60 points), so every leg is a straight line
 * inside one rectangle and never crosses a building.
 *   plan(ids) → {W, H, rows, items, rects, …}   items: {key, id|lm, kind, x0, x1, cx, F, G, h, row, stand, hit}
 * Pure (no DOM, no server). back() paints everything that does not move (the caller caches it as one bitmap);
 * marks() the few things that do (the glow round a lit shop, the arrow, the player's door). Text goes through the
 * i18n layer (kit.js T). */
import {R,E,L,T,P,fit} from './kit.js';
import {t as tr} from '../v4/i18n.js';

/* ------------------------------------------------------------ the town */
export const ROWS=[
  [{id:'chua',name:'Chùa',emoji:'🛕',items:['pagoda','lm:congduc']},{id:'ngoai_o',name:'Ngoại ô',emoji:'🌾',items:['farm','homestay','teacher','railway','lighthouse','lm:danhthang']},{id:'san_bay',name:'Sân bay',emoji:'✈️',items:['tour_guide','pilot','flight_attendant','oil','lm:travel','lm:duhoc']}],
  [{id:'van_phong',name:'Khu văn phòng',emoji:'🏢',items:['lm:bank','lm:daugia','library','accounting','customer_care','corp_accounting','tax_payroll','group_accounting','hr_admin','secretary','it_helpdesk','lawyer','research','radio']}],
  [{id:'dich_vu',name:'Phố dịch vụ',emoji:'💇',items:['art_studio','laundry','salon','nail','photobooth','pet_care','repair','restore','pharmacy','nurse','police','rescue','clothing','pet_shop','customs','hotel','reception','lm:pets','lm:garage','lm:gadgets','lm:spa','lm:style','lm:hanghieu']}],
  [{id:'pho_cho',name:'Phố chợ',emoji:'🛒',items:['post_office','florist','cafe_bakery','grocery','milk_tea','mother_baby','restaurant','banquet','teller','delivery','pho','com','zpop','lm:quan']}],
  [{id:'hang_rong',name:'Phố hàng rong',emoji:'🧺',items:['lm:fair','tra_da','fruit','ice_cream','lm:board','garbage','drain','lm:walk','lm:rap','lm:karaoke','lm:ghepba','lm:mtq','lifeguard']}],
  [{id:'hem',name:'Hẻm nhà',emoji:'🏠',items:['lm:house','homemaker','giupviec','naucom','babysitter','lm:quay','lm:square','lm:dinhthu']},
    {id:'cong_trinh',name:'Công trình phố',emoji:'🏗️',items:['lm:tp_cong_vien','lm:tp_rap_phim','lm:tp_thu_vien','lm:tp_san_van_dong','lm:tp_cau_ra_dao','lm:tp_benh_vien']}],
];
/** Landmarks: what they open (an existing data-action) and their sign. */
export const LANDMARKS={
  bank:{emoji:'🏦',name:'Ngân hàng',action:'bank'},garage:{emoji:'🚗',name:'Gara',action:'garage'},gadgets:{emoji:'📱',name:'Điện thoại',action:'gadgets'},pets:{emoji:'🐾',name:'Nuôi thú cưng',action:'pets'},
  fair:{emoji:'🕶️',name:'Cổng chợ đen',action:'fair'},board:{emoji:'📋',name:'Nhóm phố',action:'nhom'},
  walk:{emoji:'🚶',name:'Đi dạo',action:'liveWalk'},house:{emoji:'🏠',name:'Nhà mình',action:'house'},
  quay:{emoji:'🏪',name:'Quầy của bạn',action:'quay'},square:{emoji:'🎏',name:'Quảng trường',action:'town'},
  // ☕ chỗ tiêu xu (v4/spend.js, game/spend.py): each door opens its tab
  quan:{emoji:'☕',name:'Đi quán',action:'spendQuan'},spa:{emoji:'💆',name:'Spa Sen',action:'spendSpa'},rap:{emoji:'🎬',name:'Rạp Mây',action:'spendRap'},
  congduc:{emoji:'🙏',name:'Công đức',action:'spendChua'},style:{emoji:'🎨',name:'Phong cách',action:'spendStyle'},
  karaoke:{emoji:'🎤',name:'Phòng hát Mây',action:'liveKara'},   // 🎤 v4/karaoke.js: only while the live service has it on (else not built)
  ghepba:{emoji:'🧩',name:'Ghép ba Phố Mây',action:'tileMatch'},   // 🧩 v4/tile-match.js (game/tile_match.py)
  // 🛍️ Mua sắm (v4/lux.js, game/lux.py): each door opens its tab
  travel:{emoji:'✈️',name:'Đại lý vé',action:'luxTrip'},hanghieu:{emoji:'💎',name:'Hàng hiệu',action:'luxSuu'},
  duhoc:{emoji:'🎓',name:'Du học & việc làm',action:'abroad'},   // ✈️🌏 v4/abroad.js, game/abroad.py
  mtq:{emoji:'🎆',name:'Mạnh Thường Quân',action:'luxMtq'},dinhthu:{emoji:'🏰',name:'Dinh thự',action:'luxNha'},
  // 🔨 Nhà đấu giá đồ độc bản (v4/auction.js, game/auction.py); 🏞️ the plaques of the landmarks named at auction
  daugia:{emoji:'🔨',name:'Nhà đấu giá',action:'auction'},danhthang:{emoji:'🏞️',name:'Danh thắng',action:'auctionLands'},
  // 🏗️ Công trình của phố (v4/town-projects.js, game/town_projects.py): each lot opens the panel on its project
  tp_cong_vien:{emoji:'🌳',name:'Công viên ven sông',action:'townProjects',data:{id:'cong_vien'}},tp_rap_phim:{emoji:'🎬',name:'Rạp chiếu phim',action:'townProjects',data:{id:'rap_phim'}},
  tp_thu_vien:{emoji:'📚',name:'Thư viện lớn',action:'townProjects',data:{id:'thu_vien'}},tp_san_van_dong:{emoji:'🏟️',name:'Sân vận động',action:'townProjects',data:{id:'san_van_dong'}},
  tp_cau_ra_dao:{emoji:'🌉',name:'Cầu ra đảo',action:'townProjects',data:{id:'cau_ra_dao'}},tp_benh_vien:{emoji:'🏥',name:'Bệnh viện phường',action:'townProjects',data:{id:'benh_vien'}},
};
/** The sign over each door: an emoji and a short name (the card says the full place name). */
export const SIGNS={
  art_studio:['🎨','Xưởng vẽ'],lawyer:['⚖️','Văn phòng luật'],laundry:['🧺','Giặt ủi'],post_office:['📮','Bưu điện'],customs:['🛃','Hải quan'],hotel:['🛎️','Khách sạn'],banquet:['💒','Nhà hàng tiệc'],reception:['🔑','Lễ tân'],teller:['🏦','Ngân hàng'],restore:['🧰','Phục chế'],research:['🔬','Viện nghiên cứu'],radio:['📻','Đài phát thanh'],
  milk_tea:['🧋','Trà sữa'],grocery:['🛒','Tạp hóa'],delivery:['🛵','Giao hàng'],cafe_bakery:['🥐','Bánh & cà phê'],florist:['💐','Tiệm hoa'],
  mother_baby:['🎁','Mẹ & bé'],restaurant:['🌶️','Mì cay'],pho:['🍜','Phở'],com:['🍚','Cơm tấm'],clothing:['👕','Quần áo'],pet_shop:['🐠','Shop thú cưng'],
  salon:['💇','Salon tóc'],nail:['💅','Làm móng'],photobooth:['📸','Chụp ảnh'],pet_care:['🐾','Chăm thú cưng'],repair:['🔧','Sửa đồ'],pharmacy:['💊','Nhà thuốc'],
  tra_da:['🧊','Trà đá'],fruit:['🍉','Trái cây'],ice_cream:['🍨','Kem'],garbage:['♻️','Thu gom rác'],drain:['🚧','Thông cống'],
  homemaker:['🧺','Nội trợ'],giupviec:['🧹','Giúp việc'],naucom:['🍲','Nấu cơm'],babysitter:['👶','Bảo mẫu'],
  accounting:['📒','Kế toán'],customer_care:['🎧','Chăm sóc khách'],corp_accounting:['🧮','Kế toán DN'],tax_payroll:['🧾','Thuế & lương'],group_accounting:['🏢','Tập đoàn'],
  library:['📚','Thư viện'],hr_admin:['🗂️','Nhân sự'],secretary:['📅','Thư ký'],it_helpdesk:['🖥️','IT hỗ trợ'],
  pagoda:['🛕','Chùa'],farm:['🌾','Nông trại'],homestay:['🏡','Homestay'],teacher:['🍎','Lớp học'],tour_guide:['🧭','Du lịch'],pilot:['✈️','Phi công'],flight_attendant:['💺','Tiếp viên'],oil:['🛢️','Dầu khí'],railway:['🚦','Gác chắn'],
  nurse:['🏥','Bệnh viện'],lighthouse:['🗼','Hải đăng'],rescue:['📞','Tổng đài cứu hộ'],lifeguard:['🛟','Hồ bơi'],
  police:['👮','Công an phường'],zpop:['💿','Album ZPOP'],
};
const KIND={art_studio:'shop',lawyer:'office',laundry:'shop',post_office:'office',customs:'office',hotel:'lodge',banquet:'lodge',reception:'lodge',teller:'office',radio:'office',research:'office',restore:'shop',pagoda:'pagoda',farm:'farm',homestay:'lodge',teacher:'school',library:'school',tour_guide:'kiosk',pilot:'air',flight_attendant:'air',oil:'air',railway:'kiosk',lighthouse:'kiosk',
  tra_da:'cart',fruit:'cart',ice_cream:'cart',garbage:'cart',drain:'cart',homemaker:'house',giupviec:'house',naucom:'house',babysitter:'house',
  accounting:'office',customer_care:'office',corp_accounting:'office',tax_payroll:'office',group_accounting:'office',hr_admin:'office',secretary:'office',it_helpdesk:'office',nurse:'office',rescue:'office',lifeguard:'pool',police:'office',
  'lm:bank':'bank','lm:garage':'garage','lm:fair':'gate','lm:board':'board','lm:walk':'park','lm:house':'home','lm:quay':'quay','lm:square':'plaza','lm:congduc':'kiosk','lm:rap':'office','lm:travel':'kiosk','lm:duhoc':'kiosk','lm:mtq':'board','lm:dinhthu':'home','lm:daugia':'bank','lm:danhthang':'board',
  'lm:tp_cong_vien':'project','lm:tp_rap_phim':'project','lm:tp_thu_vien':'project','lm:tp_san_van_dong':'project','lm:tp_cau_ra_dao':'project','lm:tp_benh_vien':'project'};
const WIDE={pool:150,shop:128,office:128,cart:112,house:124,pagoda:208,farm:196,lodge:142,school:150,kiosk:120,air:156,bank:142,garage:132,gate:152,board:104,park:124,home:132,quay:118,plaza:134,project:150};
const HIGH={pool:150,shop:150,office:176,cart:122,house:136,pagoda:178,farm:140,lodge:150,school:160,kiosk:124,air:172,bank:160,garage:136,gate:168,board:112,park:118,home:144,quay:126,plaza:118,project:170};
export const kindOf=key=>KIND[key]||'shop';

/** Sizes in town pixels. A row: the band its buildings stand in (FH), then its street (SH). */
const FH=186,SH=112,PITCH=FH+SH,TOP=124,EDGE=78,GAP=60,PAD=14;
export const DIM={FH,SH,PITCH,TOP,EDGE,GAP};

const CACHE=new Map();
/** The town for these career ids (the ones the save has), `cats`: {id: category} for careers not placed above,
 * `skip`: landmark keys ('lm:karaoke') left out while their feature is off. */
export function plan(ids,cats={},skip=[]){
  const key=ids.join(',')+(skip.length?'|-'+skip.join(','):'');
  if(CACHE.has(key))return CACHE.get(key);
  const have=new Set(ids),gone=new Set(skip),rows=ROWS.map(r=>r.map(d=>({...d,items:d.items.filter(k=>k.startsWith('lm:')?!gone.has(k):have.has(k))})));
  const placed=new Set(ROWS.flat().flatMap(d=>d.items));
  for(const id of ids)if(!placed.has(id)){const row=['food','shop'].includes(cats[id])?3:2;rows[row][rows[row].length-1].items.push(id);}
  // Each row left to right: a lane after every third building and between districts.
  const lay=rows.map((ds,r)=>{
    let x=0;const items=[],gaps=[],districts=[];
    ds.forEach((d,di)=>{
      if(di>0){gaps.push([x,x+GAP]);x+=GAP;}
      const x0=x;
      d.items.forEach((k,i)=>{
        if(i>0&&i%3===0){gaps.push([x,x+GAP]);x+=GAP;}
        else if(i>0)x+=6;
        const kind=kindOf(k),w=WIDE[kind];items.push({key:k,kind,x0:x,x1:x+w,w});x+=w;
      });
      districts.push({id:d.id,name:d.name,emoji:d.emoji,x0,x1:x});
    });
    return {r,items,gaps,districts,width:x};
  });
  const W=Math.max(...lay.map(l=>l.width))+EDGE*2,H=TOP+rows.length*PITCH+10;
  const items=[],rects=[],rowsOut=[];
  for(const l of lay){
    const off=Math.round((W-l.width)/2),F=TOP+l.r*PITCH,G=F+FH;
    rowsOut.push({r:l.r,F,G,x0:off,x1:off+l.width,districts:l.districts.map(d=>({...d,x0:d.x0+off,x1:d.x1+off})),gaps:l.gaps.map(([a,b])=>[a+off,b+off])});
    for(const it of l.items){
      const x0=it.x0+off,x1=it.x1+off,cx=(x0+x1)/2,h=HIGH[it.kind],lm=it.key.startsWith('lm:')?it.key.slice(3):null;
      items.push({key:it.key,id:lm?null:it.key,lm,kind:it.kind,x0,x1,cx,w:it.w,h,row:l.r,F,G,stand:[cx,G+30],hit:[x0,G-h-8,x1,G+10]});
    }
    // The street under the row; the lanes and the two end roads join it to the street above (row 0 has none above).
    rects.push({kind:'street',row:l.r,x0:PAD,y0:G+14,x1:W-PAD,y1:G+SH-8});
    if(l.r>0){
      const lanes=[[0,off],...l.gaps.map(([a,b])=>[a+off,b+off]),[off+l.width,W]];
      for(const [a,b] of lanes){const x0=Math.max(PAD,a+PAD),x1=Math.min(W-PAD,b-PAD);if(x1-x0>=12)rects.push({kind:'lane',row:l.r,x0,y0:F-10,x1,y1:G+16});}
    }
  }
  // Portals: where two rectangles overlap (a lane meets a street), a point in the middle of the overlap.
  const portals=[];
  for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){
    const a=rects[i],b=rects[j],x0=Math.max(a.x0,b.x0),x1=Math.min(a.x1,b.x1),y0=Math.max(a.y0,b.y0),y1=Math.min(a.y1,b.y1);
    if(x1>=x0&&y1>=y0)portals.push({p:[(x0+x1)/2,(y0+y1)/2],a:i,b:j});
  }
  const pl={W,H,rows:rowsOut,items,rects,portals,key};
  if(CACHE.size>8)CACHE.clear();
  CACHE.set(key,pl);return pl;
}

/* ------------------------------------------------------------ walking */
const inR=(r,p,e=1e-6)=>p[0]>=r.x0-e&&p[0]<=r.x1+e&&p[1]>=r.y0-e&&p[1]<=r.y1+e;
/** Is p on the walkable floor? */
export const walkable=(pl,p)=>pl.rects.some(r=>inR(r,p));
/** The walkable point nearest to p (p itself when it is walkable). */
export function nearest(pl,p){
  if(walkable(pl,p))return [p[0],p[1]];
  let best=null,bd=Infinity;
  for(const r of pl.rects){const q=[Math.max(r.x0,Math.min(r.x1,p[0])),Math.max(r.y0,Math.min(r.y1,p[1]))],d=(q[0]-p[0])**2+(q[1]-p[1])**2;if(d<bd){bd=d;best=q;}}
  return best;
}
/** A path [from, …, to] over the floor: every leg inside one rectangle. `to` is moved onto the floor first. */
export function route(pl,from,to){
  from=nearest(pl,from);to=nearest(pl,to);
  const ra=pl.rects.map((r,i)=>inR(r,from)?i:-1).filter(i=>i>=0),rb=new Set(pl.rects.map((r,i)=>inR(r,to)?i:-1).filter(i=>i>=0));
  if(ra.some(i=>rb.has(i)))return [from,to];
  // Nodes: 0 = from, 1 = to, 2… = portals. Two nodes join when one rectangle holds both.
  const P=pl.portals,N=P.length+2,pt=k=>k===0?from:k===1?to:P[k-2].p;
  const rectsOf=k=>k===0?ra:k===1?[...rb]:[P[k-2].a,P[k-2].b];
  const byRect=new Map();for(let k=0;k<N;k++)for(const r of rectsOf(k)){if(!byRect.has(r))byRect.set(r,[]);byRect.get(r).push(k);}
  const dist=new Float64Array(N).fill(Infinity),prev=new Int32Array(N).fill(-1),done=new Uint8Array(N);dist[0]=0;
  for(;;){
    let u=-1,bd=Infinity;for(let k=0;k<N;k++)if(!done[k]&&dist[k]<bd){bd=dist[k];u=k;}
    if(u<0||u===1)break;done[u]=1;
    const pu=pt(u);
    for(const r of rectsOf(u))for(const v of byRect.get(r)){if(done[v])continue;const pv=pt(v),d=dist[u]+Math.hypot(pv[0]-pu[0],pv[1]-pu[1]);if(d<dist[v]){dist[v]=d;prev[v]=u;}}
  }
  if(dist[1]===Infinity)return null;
  const out=[];for(let k=1;k>=0;k=prev[k]){out.unshift(pt(k));if(k===0)break;}
  // Smooth a street→lane turn: a lane's portal x is kept, so the walk goes straight up the lane's middle.
  const lean=[out[0]];for(let i=1;i<out.length;i++){const a=lean[lean.length-1],b=out[i];if(Math.hypot(b[0]-a[0],b[1]-a[1])>.5)lean.push(b);}
  return lean.length>1?lean:[from,to];
}
/** Which building or landmark is at p (a tap), if any. */
export function itemAt(pl,p){
  let best=null;for(const it of pl.items){const [x0,y0,x1,y1]=it.hit;if(p[0]>=x0&&p[0]<=x1&&p[1]>=y0&&p[1]<=y1){if(!best||it.row>best.row)best=it;}}
  return best;
}
/** The district around p: the row whose street (or buildings) p is on, the district nearest along it. */
export function districtAt(pl,p){
  let row=pl.rows[0];for(const r of pl.rows)if(p[1]>=r.F-40)row=r;
  let best=row.districts[0],bd=Infinity;
  for(const d of row.districts){const dx=p[0]<d.x0?d.x0-p[0]:p[0]>d.x1?p[0]-d.x1:0;if(dx<bd){bd=dx;best=d;}}
  return best;
}

/* ------------------------------------------------------------ colours */
const hex=v=>{const m=/^#?([0-9a-f]{6})/i.exec(v||'');const n=m?parseInt(m[1],16):0xc4b49a;return [n>>16&255,n>>8&255,n&255];};
const rgb=a=>`rgb(${a.map(v=>Math.round(Math.max(0,Math.min(255,v)))).join(',')})`;
const mix=(a,b,t)=>rgb(hex(a).map((v,i)=>v+(hex(b)[i]-v)*t));
const INK='#4a3a30',CREAM='#fff8ea',WOOD='#a8743f',WOOD_D='#7a5230',GLASS='#cfe6ee',GLASS_D='#9ec3d0';
/** One palette for the ground (shared in spirit with the 2.5D island: sage lawn, warm stone, soft shade). */
const G_={lawn:'#c4d2a3',lawnD:'#b2c491',lawnL:'#d3dfb3',tree:'#93b37a',treeD:'#7fa268',treeL:'#a9c58d',trunk:'#8a6a4c',
  walk:'#ece0c8',walkJ:'#dccdb0',kerb:'#d3c4a6',kerbD:'#b9aa8c',road:'#c9c2b5',roadD:'#b8b0a2',roadL:'#d3ccc0',dash:'#f6f0e2',
  roof:'#d8b49a',roofD:'#c79f86',wallB:'#ebdfc9',shade:'rgba(74,58,48,.13)'};
/** A building's colours from its career colour (`col`), or grey when it is locked. */
function tones(col,lock){
  // Locked: the career's colour faded (the town stays cheerful), the shutter down and a 🔒 on the sign.
  if(lock)return {wall:mix(col,'#f3eee6',.86),trim:mix(col,'#c9c2b8',.62),dark:mix(col,'#9a938a',.7),roof:mix(col,'#c9c2b8',.55),sign:'#f6f2ec',ink:'#8a847b'};
  return {wall:mix(col,'#ffffff',.8),trim:col,dark:mix(col,'#000000',.32),roof:mix(col,'#000000',.12),sign:CREAM,ink:mix(col,'#000000',.45)};
}

/* ------------------------------------------------------------ painters */
/** The whole town that never moves: sky, rows, streets, every building with its sign and state.
 * `st(item)` → {color, emoji, name, lock, cur, x3, glow, paused, off} (off: a landmark this save does not have). */
export function back(c,pl,st,o={}){
  const {W,H}=pl;
  const sky=c.createLinearGradient(0,0,0,TOP+40);sky.addColorStop(0,'#b9e0ef');sky.addColorStop(.75,'#e9f1df');sky.addColorStop(1,'#f4eedb');
  c.fillStyle=sky;c.fillRect(-40,-40,W+80,TOP+80);
  // Two ranges of soft hills: the far one hazy blue-green, the near one the lawn's green.
  for(let i=0;i<9;i++){const x=(i+.3)*W/8,r=130+((i*53)%4)*30;E(c,x,TOP+4,r,r*.42,'#bcd6c0');}
  for(let i=0;i<11;i++){const x=i*W/10,r=70+((i*37)%5)*14;E(c,x,TOP-2,r,r*.5,i%2?G_.treeL:G_.tree);}
  for(const [x,y,s] of [[W*.18,38,1],[W*.55,26,.8],[W*.82,48,1.1]])cloud(c,x,y,s);
  for(const row of pl.rows)rowBand(c,pl,row);
  for(const row of pl.rows)street(c,pl,row);
  for(const it of pl.items)building(c,it,st(it),o);
  // The time of day over everything (owner: light, so signs stay easy to read), lit windows in the evening.
  const tint=o.tint;
  if(tint&&tint.alpha>.01){c.save();c.globalCompositeOperation='multiply';c.fillStyle=`rgba(${tint.rgb.map(Math.round).join(',')},${Math.min(.32,tint.alpha*.6)})`;c.fillRect(-40,-40,W+80,H+80);c.restore();}
  if(tint&&tint.lamps>.05){c.save();c.globalCompositeOperation='lighter';
    for(const it of pl.items){const s=st(it);if(s.lock||s.off)continue;glowAt(c,it.cx,it.G-40,70,.22*tint.lamps);}
    for(const row of pl.rows)for(const [a,b] of [[0,row.x0],...row.gaps,[row.x1,W]])if(b-a>=20&&a>0&&b<W)glowAt(c,(a+b)/2+11,row.G-72,60,.3*tint.lamps);
    c.restore();}
}
function glowAt(c,x,y,r,a){const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,`rgba(255,214,140,${a})`);g.addColorStop(1,'rgba(255,214,140,0)');c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);}
function cloud(c,x,y,s){E(c,x,y,40*s,16*s,'#ffffffcc');E(c,x-26*s,y+4*s,24*s,12*s,'#ffffffcc');E(c,x+28*s,y+5*s,26*s,12*s,'#ffffffcc');}
/** Behind a row's buildings: a soft back wall of trees and roofs (fields and hills for the outskirts). */
function rowBand(c,pl,row){
  const {F,G}=row,W=pl.W;
  if(row.r===0){const g=c.createLinearGradient(0,F-20,0,G);g.addColorStop(0,'#cfe5b4');g.addColorStop(1,'#b9d89a');c.fillStyle=g;c.fillRect(-40,F-20,W+80,G-F+20);
    for(let i=0;i<14;i++){const x=(i+.5)*W/14;tree(c,x,F+46+(i%3)*10,.8);}return;}
  // A lawn behind the shops, the rooftops of the next street over, then a line of round trees in front of them.
  c.fillStyle=G_.lawn;c.fillRect(-40,F-8,W+80,G-F+8);c.fillStyle=G_.lawnL;c.fillRect(-40,F+10,W+80,46);
  for(let i=0;i<16;i++){const x=(i+.3)*W/16,h=34+((i*29)%4)*12,y=F+30-h*.2;R(c,x-30,y,60,h,G_.wallB,4);P(c,[[x-38,y+4],[x,y-20-(i%3)*4],[x+38,y+4]],i%2?G_.roof:G_.roofD);}
  for(let i=0;i<15;i++){const x=(i+.5)*W/15+((i*41)%7-3)*9,s=.66+((i*17)%5)*.07;tree(c,x,F+58+(i%3)*5,s);}
  // A hedge along the back: the street above is behind these buildings, not theirs.
  R(c,-40,F-8,W+80,18,G_.tree,0);for(let x=-20;x<W+40;x+=34)E(c,x,F-6,22,12,(x/34|0)%2?G_.tree:G_.treeD);
}
function tree(c,x,y,s=1){c.save();c.translate(x,y);c.scale(s,s);E(c,4,22,22,6,G_.shade);R(c,-5,-6,10,30,G_.trunk,3);E(c,0,-28,30,26,G_.tree);E(c,-16,-16,18,15,G_.treeD);E(c,15,-18,18,15,G_.treeL);E(c,-8,-38,10,7,'#bfd6a4');c.restore();}
/** The street under a row: the pavement by the doors, the road, the far kerb with trees; the lanes up to the street
 * above and the road round both ends; the district name painted on the road (the stage says it too, top left). */
function street(c,pl,row){
  const {G,F}=row,W=pl.W,y1=G+SH;
  // The lanes up to the street above: paving stones between two grass edges, a bush at each corner.
  if(row.r>0)for(const [a,b] of [[0,row.x0],...row.gaps,[row.x1,W]]){if(b-a<20)continue;
    R(c,a+2,F-10,b-a-4,G-F+24,G_.lawnD,8);R(c,a+8,F-10,b-a-16,G-F+24,G_.walk,6);
    for(let y=F+6,k=0;y<G;y+=22,k++){L(c,a+12,y,b-12,y,G_.walkJ,1.3);const mx=(a+b)/2+(k%2?-8:8);L(c,mx,y,mx,Math.min(G,y+22),G_.walkJ,1.1);}
    if(b-a>=40){E(c,a+8,F+8,9,7,G_.treeD);E(c,b-8,F+8,9,7,G_.tree);}}
  // The pavement by the doors: square tiles, a kerb with its shadow on the road.
  R(c,-40,G,W+80,26,G_.walk,0);for(let x=8;x<W;x+=34)L(c,x,G+2,x,G+22,G_.walkJ,1.2);L(c,-40,G+13,W+40,G+13,G_.walkJ,1);
  R(c,-40,G+22,W+80,4,G_.kerb,0);
  const ry=G+26,rh=SH-46;
  R(c,-40,ry,W+80,rh,G_.road,0);R(c,-40,ry,W+80,4,G_.roadD,0);R(c,-40,ry+rh-3,W+80,3,G_.roadL,0);
  for(let x=24;x<W;x+=64)R(c,x,ry+rh/2-2,30,4,G_.dash,2);
  // The far side: a kerb, then a grass verge with small round trees (they stand in front of the next row's hedge).
  R(c,-40,y1-20,W+80,4,G_.kerb,0);R(c,-40,y1-16,W+80,16,G_.lawnD,0);
  // The district's name painted on the road, faint: the stage says it too (top left), so it should not shout.
  for(const d of row.districts){
    const cx=(d.x0+d.x1)/2,label=tr(d.name).toUpperCase();   // translated first: the capitals are drawn as they are
    c.save();c.globalAlpha=.55;T(c,label,cx,ry+rh/2,fit(c,label,Math.max(120,d.x1-d.x0-40),19,900),'#aea595',900);c.restore();
  }
  for(const [a,b] of [[0,row.x0],...row.gaps,[row.x1,W]])if(b-a>=20&&a>0&&b<W)lamp(c,(a+b)/2,G+12,row.r);   // at the lane mouths, on the pavement
}
/** A street lamp; every other one carries a red lantern (đèn lồng) under its arm. */
function lamp(c,x,y,k=0){E(c,x+3,y+2,9,3,G_.shade);L(c,x,y,x,y-74,'#5a5f68',3.5);L(c,x,y-74,x+10,y-80,'#5a5f68',3);R(c,x+4,y-84,14,10,'#fff1c4',4,'#5a5f68',2);
  if((Math.round(x/97)+k)%2)return;L(c,x+11,y-74,x+11,y-66,'#7a5230',1.2);E(c,x+11,y-58,7,9,'#d9483b');R(c,x+7,y-68,8,3,'#e9b44c',1);R(c,x+7,y-50,8,3,'#e9b44c',1);L(c,x+11,y-47,x+11,y-42,'#e9b44c',1.4);E(c,x+9,y-61,2,4,'#f47b6a');}

/** One building (or cart, or landmark) in its state. */
function building(c,it,s,o){
  if(s.off){emptyLot(c,it);return;}
  const t=tones(s.color,s.lock);
  if(s.glow&&!s.lock)glowAt(c,it.cx,it.G-it.h/2,it.w*.9,.55);
  if(s.cur)R(c,it.x0-7,it.G-it.h-14,it.w+14,it.h+20,'#ffd16655',14,'#e8a33a',3);
  if(it.kind!=='cart'&&it.kind!=='board')P(c,[[it.x1-2,it.G],[it.x1+12,it.G-it.h*.55],[it.x1+12,it.G],[it.x1+4,it.G+4]],G_.shade);   // the afternoon shade beside it
  c.save();if(s.lock)c.globalAlpha=.92;
  (DRAW[it.kind]||shop)(c,it,t,s);
  c.restore();
  if(s.lock&&it.kind==='cart')tarp(c,it);
  else if(s.lock){shutter(c,it.cx,it.G,Math.min(44,it.w*.36),62);}
  else if(s.paused)shutter(c,it.cx,it.G,Math.min(44,it.w*.36),62);   // ⏸ closed by the player: the shutter all the way down
  signBoard(c,it,t,s);
  if(s.paused&&!s.lock){const y=it.G-it.h+(it.kind==='cart'?-6:14)+34,text=tr('⏸ Tạm đóng');R(c,it.cx-38,y,76,20,'#fff3d6',10,'#c98a1b',1.5);T(c,text,it.cx,y+10.5,fit(c,text,68,11,800),'#7a4a00',800);}
}
/** The sign over the door: emoji + short name (a locked place: 🔒 and its emoji, no name yet). */
function signBoard(c,it,t,s){
  const y=it.G-it.h+(it.kind==='cart'?-6:14),w=Math.min(it.w-10,150),x=it.cx-w/2;
  R(c,x,y,w,30,t.sign,10,s.lock?t.trim:t.dark,2);
  if(s.lock){c.save();c.globalAlpha=.45;T(c,s.emoji,it.cx+12,y+15,16,INK,400);c.restore();T(c,'🔒',it.cx-12,y+15,15,INK,400);return;}
  const text=`${s.emoji} ${tr(s.name)}`;T(c,text,it.cx,y+15.5,fit(c,text,w-12,15,800),t.ink,800);   // the name alone translated ("Mẹ & bé" whole, not by its pieces)
  if(s.x3){E(c,x+w-2,y+1,11,11,'#e8572d');c.lineWidth=1.5;c.strokeStyle='#ffffff';c.stroke();T(c,'🔥',x+w-2,y+1.5,11,'#ffffff',400);}   // ×3 today: one small mark (the top bar says the number)
}
function emptyLot(c,it){
  const {x0,w,G,cx}=it;R(c,x0+4,G-34,w-8,34,'#c9dfae',8);
  for(let i=0;i<3;i++)E(c,x0+18+i*(w-36)/2,G-30,16,12,i%2?'#9cc68e':'#8dbf7c');
  R(c,cx-20,G-16,40,7,WOOD,3);L(c,cx-16,G-9,cx-16,G-2,WOOD_D,2);L(c,cx+16,G-9,cx+16,G-2,WOOD_D,2);
}
function tarp(c,it){const {x0,w,G}=it;P(c,[[x0+8,G-12],[x0+20,G-58],[x0+w-20,G-58],[x0+w-8,G-12]],'#b8c3c9');L(c,x0+30,G-56,x0+26,G-14,'#a2adb4',1.5);L(c,x0+w-30,G-56,x0+w-26,G-14,'#a2adb4',1.5);}
function shutter(c,x,G,hw,h){R(c,x-hw,G-h,hw*2,h,'#b9b3aa',3,'#8f897f',1.5);for(let y=G-h+5;y<G;y+=6)L(c,x-hw+2,y,x+hw-2,y,'#a39d93',1);}
function door(c,x,G,t,w=30,h=58){R(c,x-w/2-3,G-h-3,w+6,h+3,t.dark,5);R(c,x-w/2,G-h,w,h,mix(t.wall,'#000000',.06),4);R(c,x-w/2+3,G-h+4,w-6,h*.45,GLASS,3);E(c,x+w/2-6,G-h/2+4,2,2,t.dark);R(c,x-w/2-8,G-3,w+16,5,'#d8c8aa',2);}
function windowAt(c,x,y,w,h,t){R(c,x,y,w,h,t.dark,4);R(c,x+3,y+3,w-6,h-6,GLASS,3);L(c,x+w/2,y+3,x+w/2,y+h-3,GLASS_D,1.4);E(c,x+w*.3,y+h*.3,w*.12,h*.12,'#ffffff88');}
function awning(c,x0,x1,y,col,t){const n=Math.max(4,Math.round((x1-x0)/18)),sw=(x1-x0)/n;
  for(let i=0;i<n;i++)P(c,[[x0+i*sw,y],[x0+(i+1)*sw,y],[x0+(i+1)*sw+2,y+20],[x0+i*sw+2,y+20]],i%2?CREAM:col);
  for(let i=0;i<n;i++)E(c,x0+(i+.5)*sw+1,y+20,sw/2,5,i%2?CREAM:col);}

/** A shophouse: wall, cornice, awning, two windows, the door. */
function shop(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0,top+8,w,h-8,t.wall,6,t.trim,2);R(c,x0-4,top,w+8,14,t.roof,5);
  awning(c,x0+4,x0+w-4,top+50,t.trim,t);
  windowAt(c,x0+10,G-66,w/2-34,40,t);windowAt(c,cx+24,G-66,w/2-34,40,t);
  door(c,cx,G,t);
}
function office(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0,top+6,w,h-6,mix(t.trim,'#e8eef2',.82),4,t.dark,2);R(c,x0-3,top,w+6,10,t.dark,3);
  for(let r=0;r<3;r++)for(let i=0;i<3;i++)R(c,x0+12+i*(w-24)/3,top+52+r*26,(w-24)/3-8,18,r===2&&i===1?GLASS_D:GLASS,3);
  R(c,cx-22,G-50,44,50,t.dark,4);R(c,cx-19,G-47,17,47,GLASS,2);R(c,cx+2,G-47,17,47,GLASS,2);R(c,cx-30,G-3,60,5,'#d8d2c6',2);
}
function house(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h+30;
  R(c,x0+6,top,w-12,G-top,t.wall,6,t.trim,2);P(c,[[x0-4,top+4],[cx,G-h-4],[x0+w+4,top+4]],t.roof);L(c,x0-4,top+4,x0+w+4,top+4,t.dark,3);
  windowAt(c,x0+14,G-62,30,30,t);door(c,cx+18,G,t,26,52);
  for(const px of [x0+14,x0+w-16])E(c,px,G-6,9,7,'#7fb46f');
}
function cart(c,it,t,s){
  const {x0,w,G,cx,key}=it;
  // A big umbrella on a pole over a little cart, the vendor beside it.
  L(c,cx,G-24,cx,G-104,'#6b6f78',3);
  P(c,[[cx-w/2+2,G-92],[cx+w/2-2,G-92],[cx,G-118]],t.trim);for(let i=0;i<4;i++)P(c,[[cx-w/2+2+i*(w-4)/4,G-92],[cx-w/2+2+(i+.5)*(w-4)/4,G-92],[cx,G-118]],i%2?CREAM:t.trim);
  R(c,x0+14,G-46,w-28,30,WOOD,6,WOOD_D,2);E(c,x0+24,G-10,9,9,'#5a5f68');E(c,x0+w-24,G-10,9,9,'#5a5f68');E(c,x0+24,G-10,3,3,'#c9c9c9');E(c,x0+w-24,G-10,3,3,'#c9c9c9');
  const goods={tra_da:['#e9f4f7','#cfe6ee'],fruit:['#f08a3a','#e2462d','#f4c542'],ice_cream:['#f7b6cf','#fff1c4','#b6e3c9'],garbage:['#3f8f5b','#5aa06a'],drain:['#f0b44a','#5a6f88']}[key]||['#f4c542'];
  if(!s.lock)goods.forEach((g,i)=>E(c,x0+28+i*((w-56)/Math.max(1,goods.length-1)),G-50,9,7,g));
  if(key==='tra_da'&&!s.lock)for(const dx of [-44,44])R(c,cx+dx-9,G-16,18,14,'#3c8fd0',3);
  if(!s.lock)vendor(c,x0+w-6,G-2,s.color);
}
function vendor(c,x,y,col){E(c,x,y,12,4,'#00000022');R(c,x-7,y-24,6,24,'#4b5468',3);R(c,x+1,y-24,6,24,'#4b5468',3);R(c,x-10,y-46,20,24,mix(col,'#ffffff',.25),8);E(c,x,y-54,9,9,'#f2d0b0');E(c,x,y-60,10,6,'#3b2f2a');P(c,[[x-15,y-58],[x+15,y-58],[x,y-72]],'#e9d29a');}
function pagoda(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0+18,top+64,w-36,h-64,'#f3e2c0',4,'#a8641f',2);
  for(const [y,hw] of [[top+60,w/2+6],[top+24,w/2-30]]){P(c,[[cx-hw,y],[cx+hw,y],[cx+hw-14,y-24],[cx-hw+14,y-24]],'#b8442e');L(c,cx-hw-6,y-4,cx-hw,y,'#b8442e',5);L(c,cx+hw+6,y-4,cx+hw,y,'#b8442e',5);}
  R(c,cx-hw2(w),top+36,hw2(w)*2,24,'#f3e2c0',2);
  for(const px of [x0+30,x0+w-30,cx-30,cx+30])R(c,px-4,top+64,8,h-64,'#c0392b',2);
  R(c,cx-20,G-56,40,56,'#8a3a22',6);E(c,cx,G-56,20,12,'#8a3a22');R(c,x0+8,G-6,w-16,6,'#d8c8aa',2);
  E(c,cx-46,G-10,12,8,'#7fb46f');E(c,cx+46,G-10,12,8,'#7fb46f');
}
const hw2=w=>w/2-40;
function farm(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  for(let i=0;i<4;i++)R(c,x0+4,G-14-i*10,w-8,6,i%2?'#9cc68e':'#7fb46f',3);
  R(c,cx-52,top+46,104,h-70,'#c0563b',4,'#8a3a22',2);P(c,[[cx-60,top+48],[cx,top+6],[cx+60,top+48]],'#9b3a28');
  R(c,cx-18,G-70,36,46,'#f6e6c8',3,'#8a3a22',2);L(c,cx-18,G-70,cx+18,G-24,'#8a3a22',2);L(c,cx+18,G-70,cx-18,G-24,'#8a3a22',2);
  for(let x=x0+6;x<x0+w;x+=16)L(c,x,G-2,x,G-22,WOOD,3);L(c,x0+4,G-14,x0+w-4,G-14,WOOD,3);
}
function lodge(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h+40;
  R(c,x0+8,top,w-16,G-top,'#c89a68',6,'#7a5230',2);for(let y=top+10;y<G;y+=12)L(c,x0+10,y,x0+w-10,y,'#b0835a',1.4);
  P(c,[[x0-6,top+6],[cx,G-h],[x0+w+6,top+6]],'#5f7f58');
  windowAt(c,x0+18,top+26,30,28,t);windowAt(c,x0+w-48,top+26,30,28,t);door(c,cx,G,t,28,48);
  tree(c,x0-2,G-6,.6);tree(c,x0+w+2,G-6,.6);
}
function school(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h+20;
  R(c,x0,top,w,G-top,'#f4e3b4',4,'#b9a46c',2);R(c,x0-4,top-10,w+8,14,'#c8642a',4);
  for(let i=0;i<4;i++)windowAt(c,x0+10+i*(w-20)/4,top+42,(w-20)/4-8,26,t);
  door(c,cx,G,t,34,50);L(c,x0+w-14,top-10,x0+w-14,top-60,'#6b6f78',2.5);P(c,[[x0+w-14,top-60],[x0+w+12,top-52],[x0+w-14,top-44]],'#d9473b');
}
function kiosk(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0+6,top+30,w-12,h-30,t.wall,8,t.trim,2);R(c,x0,top+18,w,16,t.trim,6);
  R(c,x0+16,G-74,w-32,34,GLASS,4,t.dark,2);T(c,'🗺️',cx,G-57,18,INK,400);
  R(c,x0+12,G-36,w-24,36,t.dark,4);R(c,x0+16,G-32,w-32,10,'#f4efe4',3);
  if(it.key==='lighthouse'){const lx=x0+w-14;P(c,[[lx-9,top+34],[lx+9,top+34],[lx+6,top-30],[lx-6,top-30]],'#f8fafc');R(c,lx-8,top-4,16,8,'#d6382b',2);
    R(c,lx-7,top-40,14,10,'#f2c14e',3,'#26303b',1.5);P(c,[[lx-8,top-40],[lx+8,top-40],[lx,top-48]],'#d6382b');}
}
function air(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0,top+60,w,h-60,'#e8eef2',6,'#7a8b99',2);R(c,x0,top+60,w,12,t.trim,4);
  for(let i=0;i<4;i++)R(c,x0+10+i*(w-20)/4,top+82,(w-20)/4-6,34,GLASS,3);
  R(c,cx-22,G-48,44,48,'#5a6f88',4);R(c,cx-18,G-44,36,44,GLASS,2);
  if(it.key==='pilot'){R(c,x0+w-34,top+6,18,56,'#d8dee4',3,'#7a8b99',1.5);R(c,x0+w-44,top-6,38,18,GLASS_D,5,'#5a6f88',2);}
  else if(it.key==='oil'){P(c,[[x0+14,top+60],[x0+w-14,top+60],[x0+w-24,top+44],[x0+24,top+44]],'#4b5560');T(c,'H',cx,top+53,12,'#f2c14e',800);
    L(c,x0+w-20,top+60,x0+w-6,top+22,'#6f7d88',3);P(c,[[x0+w-6,top+22],[x0+w-11,top+10],[x0+w-5,top],[x0+w,top+10]],'#f08a3c');}
  else{c.save();c.translate(x0+30,top+30);c.rotate(-.18);R(c,-24,-4,48,9,'#ffffff',5,'#7a8b99',1.2);P(c,[[-4,-2],[10,-2],[-6,-18]],'#ffffff');P(c,[[-20,-2],[-14,-2],[-22,-12]],t.trim);c.restore();}
}
function bank(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0,top+36,w,h-36,'#efe9dc',4,'#a99a7c',2);P(c,[[x0-6,top+40],[cx,top+6],[x0+w+6,top+40]],'#c9b98f');
  for(let i=0;i<4;i++)R(c,x0+14+i*(w-28)/3-6,top+56,12,h-76,'#fbf7ee',3,'#c9b98f',1.2);
  R(c,cx-18,G-52,36,52,'#6b5a3c',4);R(c,x0-4,G-8,w+8,8,'#d8cfbe',2);
}
function garage(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0,top+20,w,h-20,'#dfe3e6',4,'#7a8b99',2);R(c,x0-4,top+12,w+8,14,'#5a6f88',4);
  R(c,x0+12,G-80,w-24,80,'#b9c0c6',4,'#7a8b99',2);for(let y=G-74;y<G;y+=8)L(c,x0+14,y,x0+w-14,y,'#a2a9b0',1.2);
}
function gate(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  for(const px of [x0+10,x0+w-10])R(c,px-7,top+30,14,h-30,'#c0392b',3,'#8f2d2a',1.5);
  R(c,x0-4,top+18,w+8,24,'#c8423a',8,'#8f2d2a',2);P(c,[[x0-12,top+20],[x0+w+12,top+20],[cx,top-4]],'#d9534f');
  for(let i=0;i<5;i++){const x=x0+18+i*(w-36)/4;L(c,x,top+42,x,top+52,'#5a3a2a',1.2);E(c,x,top+62,9,11,i%2?'#e6b34a':'#c8423a');}
  R(c,x0+20,G-30,w-40,30,'#f6e6c8',4);for(let i=0;i<3;i++)E(c,x0+36+i*(w-72)/2,G-16,6,6,['#e2462d','#3c8fd0','#5aa06a'][i]);
}
function board(c,it,t){
  const {x0,w,G,cx}=it;L(c,cx-30,G,cx-30,G-80,WOOD_D,4);L(c,cx+30,G,cx+30,G-80,WOOD_D,4);
  R(c,cx-44,G-104,88,58,'#c89f7f',8,WOOD_D,2);R(c,cx-38,G-98,76,46,'#fff7e7',5);
  for(const [px,py,col] of [[-24,-88,'#f7d58a'],[2,-90,'#bfe3f2'],[-10,-70,'#f7b6cf'],[18,-70,'#c9e7b8']])R(c,cx+px-9,G+py-6,20,14,col,2);
}
function park(c,it,t){
  const {x0,w,G,cx}=it;R(c,x0+4,G-30,w-8,30,'#c9dfae',10);tree(c,x0+22,G-10,.75);tree(c,x0+w-22,G-10,.75);
  R(c,cx-24,G-26,48,8,WOOD,3);R(c,cx-24,G-40,48,6,WOOD,3);L(c,cx-20,G-18,cx-20,G-6,WOOD_D,2.5);L(c,cx+20,G-18,cx+20,G-6,WOOD_D,2.5);
}
function home(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h+40;
  R(c,x0+6,top,w-12,G-top,'#f7e1c4',6,'#c8742c',2);P(c,[[x0-6,top+6],[cx,G-h],[x0+w+6,top+6]],'#d9573b');R(c,x0+w-34,G-h+14,14,26,'#a8442e',2);
  windowAt(c,x0+16,top+18,30,28,{dark:'#c8742c'});door(c,cx+20,G,{dark:'#c8742c',wall:'#f7e1c4'},28,50);
  E(c,x0+18,G-6,10,7,'#7fb46f');heartAt(c,cx-6,top-4);
}
function heartAt(c,x,y){c.save();c.translate(x,y);c.scale(.35,.35);c.beginPath();c.moveTo(0,6);c.bezierCurveTo(-25,-9,-15,-27,0,-13);c.bezierCurveTo(15,-27,25,-9,0,6);c.fillStyle='#e0708a';c.fill();c.restore();}
function quay(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h;
  R(c,x0+8,top+40,w-16,h-40,'#fff3df',6,'#c8742c',2);awning(c,x0+4,x0+w-4,top+28,'#e0892b',t);
  R(c,x0+12,G-40,w-24,40,WOOD,5,WOOD_D,2);for(let i=0;i<4;i++)E(c,x0+24+i*(w-48)/3,G-46,8,6,['#f08a3a','#f4c542','#5aa06a','#e2462d'][i]);
}
function plaza(c,it,t){
  const {x0,w,G,cx}=it;R(c,x0+2,G-40,w-4,40,'#ede2cc',12,'#d6c4a2',2);
  E(c,cx,G-20,34,12,'#9ec3d0');E(c,cx,G-22,26,8,'#cfe6ee');R(c,cx-4,G-60,8,40,'#d6c4a2',3);E(c,cx,G-62,12,5,'#cfe6ee');
  for(const [px,col] of [[x0+16,'#e2462d'],[x0+w-16,'#f0b44a']]){L(c,px,G-4,px,G-70,'#8a6644',2);P(c,[[px,G-70],[px+18,G-64],[px,G-58]],col);}
}
/** 🛟 The ward's pool: a low white building with a blue roof line, the water and its lane rope in front, the high chair. */
function pool(c,it,t){
  const {x0,w,G,h,cx}=it,top=G-h+40;
  R(c,x0+6,top,w-12,G-top,'#eef7fb',6,'#7fb3c8',2);R(c,x0,top-10,w,14,'#1f8fc4',4);
  windowAt(c,x0+16,top+14,30,26,t);windowAt(c,x0+w-46,top+14,30,26,t);door(c,cx,G,t,28,48);
  R(c,x0-8,G-22,w*.36,20,'#7fd0ee',6,'#4fb3dc',1.5);for(let x=x0-2;x<x0+w*.36-12;x+=9)E(c,x+3,G-12,3,2,(Math.floor((x-x0)/9)%2)?'#d6453a':'#ffffff');
  L(c,x0+w-30,G,x0+w-24,G-56,WOOD_D,3);L(c,x0+w-6,G,x0+w-12,G-56,WOOD_D,3);R(c,x0+w-28,G-62,20,8,WOOD,3);P(c,[[x0+w-34,G-66],[x0+w-18,G-84],[x0+w-2,G-66]],'#d6453a');
}
/** 🏗️ A town project's lot (s.stage from v4/town-projects-data.js): an empty plot with a "Sắp xây" board (bunting
 * and how much is raised while the street gives), a frame in scaffolding under a crane, or the finished building. */
function project(c,it,t,s){
  const {x0,w,G,h,cx}=it,x1=x0+w,top=G-h,stage=s.stage||'soon',id=(it.lm||'').slice(3);
  if(stage==='soon'||stage==='funding'){
    R(c,x0+2,G-12,w-4,12,'#cdb38a',4);for(let i=0;i<4;i++)E(c,x0+20+i*(w-40)/3,G-8,8,3,'#b49a72');
    for(let x=x0+6;x<=x1-6;x+=12)L(c,x,G-2,x,G-26,'#a07c55',3);L(c,x0+4,G-18,x1-4,G-18,'#c49d6f',3);
    L(c,cx-34,G,cx-34,top+44,WOOD_D,4);L(c,cx+34,G,cx+34,top+44,WOOD_D,4);
    R(c,x0+12,G-64,30,18,'#c97f5d',3);R(c,x0+16,G-80,22,16,'#cf8a66',3);R(c,x1-44,G-46,32,10,'#9c9b95',3);
    R(c,cx-44,top+52,88,26,'#fff3da',6,'#8a6a48',2);T(c,'Sắp xây',cx,top+65.5,fit(c,'Sắp xây',80,13,800),'#8a4f2d',800);
    if(stage==='funding'){
      const pct=Math.max(0,Math.min(100,Number(s.pct)||0));
      R(c,cx-44,top+84,88,12,'#efe3cc',6,'#8a6a48',1.5);R(c,cx-43,top+85,Math.max(4,86*pct/100),10,'#6aa56a',5);T(c,`${pct}%`,cx,top+104,12,'#4f6a3f',800);
      const flags=['#e07a5f','#f2cc8f','#81b29a','#3d85c6'];L(c,x0+2,top+50,x1-2,top+50,'#8a6a48',1.5);
      for(let i=0;i<9;i++){const x=x0+8+i*(w-16)/8;P(c,[[x-5,top+50],[x+5,top+50],[x,top+60]],flags[i%4]);}
    }
    return;
  }
  if(stage==='building'){
    R(c,x0+4,G-10,w-8,10,'#b3b0a8',3);
    const fh=h*.62,fx0=x0+20,fx1=x1-20;R(c,fx0,G-fh,fx1-fx0,fh,'#d9d5cc',2,'#9b968c',2);
    for(let y=G-fh;y<G;y+=fh/3)L(c,fx0,y,fx1,y,'#9b968c',3);for(let x=fx0;x<=fx1+.5;x+=(fx1-fx0)/3)L(c,x,G,x,G-fh,'#8c877d',3);
    c.save();c.globalAlpha=.35;R(c,fx0-8,G-fh-10,fx1-fx0+16,fh+10,'#7aaa6e',2);c.restore();
    for(let x=fx0-8;x<=fx1+8;x+=16)L(c,x,G,x,G-fh-14,'#d39a3d',2.5);for(let y=G-14;y>G-fh-12;y-=20)L(c,fx0-10,y,fx1+10,y,'#c48a2f',2);
    L(c,x0+10,G,x0+10,top+48,'#e0a419',5);L(c,x0-6,top+48,x1+4,top+52,'#e0a419',4);L(c,x1-20,top+52,x1-20,top+76,'#555',1.5);R(c,x1-27,top+76,14,9,'#c97f5d',2);
    if(s.left){const text=`⏳ ${s.left}h`;R(c,cx-30,G-fh/2-11,60,22,'#fff3d6',11,'#c98a1b',1.5);T(c,text,cx,G-fh/2,12,'#7a4a00',800);}
    return;
  }
  if(id==='cong_vien'){
    R(c,x0+2,G-30,w-4,30,'#a9cb88',10);E(c,cx,G-12,26,7,'#8cc3d8');R(c,cx-3,G-38,6,26,'#d9d4c8',2);E(c,cx,G-40,9,4,'#bfe2ef');
    tree(c,x0+22,G-14,.8);tree(c,x1-22,G-14,.8);tree(c,x0+52,G-24,.55);R(c,x1-62,G-24,30,6,WOOD,3);L(c,x1-58,G-18,x1-58,G-10,WOOD_D,2);L(c,x1-36,G-18,x1-36,G-10,WOOD_D,2);
    return;
  }
  if(id==='san_van_dong'){
    P(c,[[x0,G],[x0+10,top+70],[x1-10,top+70],[x1,G]],'#c7c1b4');R(c,x0+16,top+78,w-32,G-top-90,'#6fae5a',4,'#f4f4ee',2);L(c,cx,top+80,cx,G-14,'#f4f4ee',1.5);
    for(let i=0;i<3;i++)L(c,x0+12+i*4,top+74+i*6,x1-12-i*4,top+74+i*6,['#e07a5f','#3d85c6','#f2cc8f'][i],3);
    for(const x of [x0+6,x1-6]){L(c,x,G,x,top+10,'#6d6d6d',3);R(c,x-10,top,20,10,'#fff7d0',2,'#6d6d6d',1.5);}
    return;
  }
  if(id==='cau_ra_dao'){
    R(c,x0,G-22,w,22,'#9cc6cb',4);for(let i=0;i<5;i++)L(c,x0+10+i*28,G-10+(i%2)*5,x0+24+i*28,G-10+(i%2)*5,'#c4e1e3',2);
    R(c,x0-4,G-40,w+8,10,'#d9d3c6',3,'#aaa397',1.5);for(const x of [x0+20,x1-20])R(c,x-4,G-30,8,22,'#9c968c',2);
    R(c,cx-6,top+20,12,G-40-top-20,'#eae6dc',2,'#c4bfb3',1.5);
    for(let i=1;i<=4;i++){L(c,cx,top+30,cx-i*(w/2-6)/4,G-40,'#8f8a80',1.2);L(c,cx,top+30,cx+i*(w/2-6)/4,G-40,'#8f8a80',1.2);}
    for(let x=x0+6;x<x1;x+=24){L(c,x,G-40,x,G-56,'#4f5a5e',2);E(c,x,G-58,3,3,'#ffe9a8');}
    return;
  }
  if(id==='rap_phim'){
    R(c,x0+6,top+40,w-12,h-40,'#6c4f8f',4,'#4c3566',2);R(c,x0+14,top+52,w-28,26,'#2d2a36',3);T(c,'CINEMA',cx,top+65.5,13,'#ffd36b',800);
    for(let x=x0+18;x<x1-14;x+=10)E(c,x,top+82,2,2,'#ffe9a8');R(c,x0+14,G-50,w-28,8,'#c0392b',2);
    for(const x of [x0+18,x1-48])R(c,x,G-40,30,40,'#f4e9d0',2,'#8a6a48',1.5);door(c,cx,G,t,26,48);
    return;
  }
  if(id==='thu_vien'){
    R(c,x0+8,top+70,w-16,h-70,'#e9dcc0',3,'#c2b49a',2);P(c,[[x0,top+72],[cx,top+34],[x1,top+72]],'#a4543d');
    for(let x=x0+20;x<x1-14;x+=22)R(c,x,top+80,8,h-90,'#f6efe0',2,'#d8ccb4',1);R(c,x0+4,G-8,w-8,8,'#d8ccb4',2);door(c,cx,G-8,t,24,44);
    return;
  }
  R(c,x0+10,top+30,w-50,h-30,'#f4f4f2',4,'#c9c9c4',2);R(c,x1-44,top+90,38,h-90,'#efefec',3,'#c9c9c4',2);
  for(let r=0;r<3;r++)for(let i=0;i<3;i++)R(c,x0+18+i*26,top+84+r*24,18,14,'#8fb7d1',2);
  R(c,cx-30,top+50,28,28,'#ffffff',6,'#c0392b',2);R(c,cx-20,top+55,8,18,'#d64541',1);R(c,cx-25,top+60,18,8,'#d64541',1);door(c,x0+40,G,t,30,40);
}
const DRAW={shop,office,house,cart,pagoda,farm,lodge,school,kiosk,air,bank,garage,gate,board,park,home,quay,plaza,pool,project};

/* ------------------------------------------------------------ what moves */
/** The live layer, over the cached town: a soft pulse round the lit shops, the bobbing arrow over the suggested
 * first one, a ring at the door the player stands at. `o.t` seconds (frozen with reduced motion). */
export function marks(c,pl,o={}){
  const t=o.reduced?0:o.t||0;
  for(const it of o.glow||[]){const a=.45+.3*Math.sin(t*3);c.save();c.globalAlpha=a;R(c,it.x0-6,it.G-it.h-12,it.w+12,it.h+16,'rgba(255,209,102,0)',14,'#ffcf5a',4);c.restore();}
  if(o.arrow){const it=o.arrow,y=it.G-it.h-34-Math.abs(Math.sin(t*3))*8;
    P(c,[[it.cx-14,y-14],[it.cx+14,y-14],[it.cx,y+4]],'#e8572d');R(c,it.cx-6,y-30,12,18,'#e8572d',3);}
  if(o.near){const it=o.near;c.save();c.globalAlpha=.9;R(c,it.cx-34,it.G+16,68,22,'rgba(0,0,0,0)',11,'#ffffff',3);c.restore();}
}
