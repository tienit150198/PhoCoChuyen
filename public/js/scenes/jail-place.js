/** 🚔 Trại tạm giữ phường as a place to walk around (v4/jail-map.js; owner 09/10: "vô tù có map, di chuyển này kia
 * được nữa đi chứ đừng mỗi cái hình"). A small, sunny holding camp, more summer camp than prison:
 *   back row   the cells (the bunk ends the jail day; the next cell's blankets to fold), the căng tin (rice counter,
 *              sink), the khu lao động (the camp library shelf, the old wall to paint, the storeroom ledger) and the
 *              cán bộ trực's booth and desk (landscape; in portrait the desk stands in the yard);
 *   the floor  the mop bucket, the vegetable table, the broken chair, the cây bàng and its leaf piles, the clothesline,
 *              the trash bins, the chicken coop, the bồn cây by the fence, the phòng thăm gặp window (bail) and the
 *              Cổng trại (the days left). Every công ích task of game/jail.py (TASK_SPOT) has its own corner.
 * Walking uses the pagoda's path finder (scenes/chua-place.js: one floor rectangle, footprints, a grid A*
 * string-pulled), so a plan has the same shape as the fair's and the pagoda's:
 *   plan(port) → {floor, blocks, spots:[{id, kind, hit, r, stand, task?, mark}], entry:{bunk}, walkers}
 *   kind 'task' (a công ích task, `task`), 'bunk', 'guard', 'visit', 'gate' (the jail's panels). `walkers`: the camp's
 *   people (two inmates and a cán bộ) and the points they stroll between; they are cosmetic, drawn by the caller,
 *   never footprints (the player walks through them like through a crowd).
 * Pure (no DOM, no server); scene pixels: landscape 1200×790, portrait 700×890 like the workplaces. Nothing moves
 * when `reduced` is set. back() paints what never moves (cached by the caller), props() what stands on the floor;
 * `o.done` (the tasks done today) and `o.today` (today's tasks) change the yard: the leaves go, the sprouts come up. */
import {R,E,L,T,P,fit} from './kit.js';
import {hash} from './interior.js';
import {route,blocked,nearestFree,lineFree} from './chua-place.js';
import {folk} from './fair-place.js';

export {route,blocked,nearestFree,lineFree,folk};
/** The drawn part of the scene per orientation (what the stage fits). */
export const VIEW={land:[50,100,1150,760],port:[14,104,686,868]};

/* ------------------------------------------------------------ where things are */
const LAYOUT={
  land:{floor:[80,448,1120,740],top:236,
    cell:[90,372],cant:[396,626],work:[650,890],booth:[930,1110],
    desk:{x:1020,y:480},tree:{x:590,y:614},bed:{x:160,y:724,w:130},kiosk:{x:810,y:718,w:120},gate:{x:1058,y:740,w:120},
    bucket:{x:150,y:578},veg:{x:420,y:580},chair:{x:720,y:575},line:{x:330,y:672,w:136},coop:{x:930,y:612},bins:{x:520,y:692},ledger:{x:905,y:494},
    yard:[470,600,710,705],
    spots:{bunk:{hit:[160,372],r:58,stand:[160,486]},fold:{hit:[300,372],r:58,stand:[300,486]},rice:{hit:[470,372],r:56,stand:[470,486]},
      dishes:{hit:[585,385],r:46,stand:[585,486]},books:{hit:[705,370],r:52,stand:[705,486]},paint:{hit:[840,372],r:52,stand:[840,486]},
      ledger:{hit:[905,452],r:40,stand:[905,534]},guard:{hit:[1020,400],r:60,stand:[1020,534]},mop:{hit:[150,545],r:42,stand:[150,614]},
      veg:{hit:[420,546],r:44,stand:[420,616]},fix:{hit:[720,540],r:44,stand:[720,612]},sweep:{hit:[640,600],r:44,stand:[652,656]},
      laundry:{hit:[330,632],r:48,stand:[330,706]},chicken:{hit:[930,570],r:46,stand:[930,664]},plant:{hit:[160,686],r:44,stand:[160,690]},
      trash:{hit:[520,652],r:42,stand:[520,726]},visit:{hit:[810,650],r:48,stand:[810,690]},gate:{hit:[1058,628],r:54,stand:[1058,702]}},
    walkers:[{who:'tu',path:[[520,520],[660,520],[700,700],[440,690]]},{who:'bay',path:[[540,500],[620,500]],idle:true},
      {who:'canbo',path:[[1000,580],[1060,600],[920,700],[860,560]]}]},
  port:{floor:[30,452,670,860],top:262,
    cell:[24,242],cant:[252,460],work:[470,684],booth:null,
    desk:{x:590,y:600},tree:{x:262,y:716},bed:{x:90,y:846,w:110},kiosk:{x:380,y:852,w:104},gate:{x:604,y:860,w:100},
    bucket:{x:80,y:592},veg:{x:296,y:596},chair:{x:440,y:592},line:{x:122,y:716,w:120},coop:{x:420,y:716},bins:{x:236,y:850},ledger:{x:528,y:718},
    yard:[150,630,360,770],
    spots:{bunk:{hit:[78,372],r:48,stand:[78,490]},fold:{hit:[188,372],r:48,stand:[188,490]},rice:{hit:[308,372],r:48,stand:[308,490]},
      dishes:{hit:[410,385],r:40,stand:[410,490]},books:{hit:[522,372],r:44,stand:[522,490]},paint:{hit:[636,380],r:40,stand:[636,490]},
      mop:{hit:[80,560],r:40,stand:[80,626]},veg:{hit:[296,562],r:42,stand:[296,630]},fix:{hit:[440,560],r:40,stand:[440,626]},
      guard:{hit:[590,540],r:48,stand:[590,652]},laundry:{hit:[122,672],r:44,stand:[122,752]},sweep:{hit:[306,690],r:40,stand:[312,760]},
      chicken:{hit:[420,676],r:42,stand:[420,766]},ledger:{hit:[528,680],r:40,stand:[528,760]},plant:{hit:[90,806],r:40,stand:[90,812]},
      trash:{hit:[236,808],r:40,stand:[236,818]},visit:{hit:[380,776],r:42,stand:[380,818]},gate:{hit:[604,764],r:46,stand:[604,830]}},
    walkers:[{who:'tu',path:[[180,540],[360,540],[340,800],[160,780]]},{who:'bay',path:[[340,510],[380,510]],idle:true},
      {who:'canbo',path:[[520,800],[640,690],[500,640],[600,720]]}]},
};
/** The công ích tasks (game/jail.py TASKS) and the place in the camp each is done at (one place each). */
export const TASK_SPOT={sweep:'sweep',plant:'plant',rice:'rice',paint:'paint',books:'books',laundry:'laundry',mop:'mop',trash:'trash',
  veg:'veg',dishes:'dishes',chicken:'chicken',fix:'fix',ledger:'ledger',fold:'fold'};
export const TASK_ICON={sweep:'🧹',plant:'🌱',rice:'🍚',paint:'🎨',books:'📚',laundry:'👕',mop:'🧽',trash:'🗑️',veg:'🥬',dishes:'🍜',
  chicken:'🐔',fix:'🔨',ledger:'📒',fold:'🛏️'};
export const PLACES={
  bunk:{icon:'🛏️',name:'Giường trong buồng'},fold:{icon:'🛏️',name:'Buồng bên cạnh'},rice:{icon:'🍚',name:'Quầy căng tin'},
  dishes:{icon:'🍜',name:'Bồn rửa căng tin'},books:{icon:'📚',name:'Thư viện trại'},paint:{icon:'🎨',name:'Bức tường cũ'},
  ledger:{icon:'📒',name:'Bàn sổ sách kho'},guard:{icon:'👮',name:'Bàn cán bộ trực'},mop:{icon:'🧽',name:'Xô lau sàn'},
  veg:{icon:'🥬',name:'Bàn nhặt rau'},fix:{icon:'🔨',name:'Ghế gãy chân'},sweep:{icon:'🧹',name:'Gốc bàng giữa sân'},
  laundry:{icon:'👕',name:'Dây phơi đồ'},chicken:{icon:'🐔',name:'Chuồng gà'},plant:{icon:'🌱',name:'Bồn cây ven rào'},
  trash:{icon:'🗑️',name:'Góc thùng rác'},visit:{icon:'🤝',name:'Phòng thăm gặp'},gate:{icon:'🚪',name:'Cổng trại'},
};
/** The camp's people: who they are and what they say now and then (cosmetic, client only). */
export const PEOPLE={
  tu:{name:'Anh Tư Sún',top:'#f0a868',seed:4,lines:['Quét sân xong là được giảm án đó, siêng lên!','Tui vô đây vì cá độ bầu cua. Thề không chơi nữa!',
    'Cơm căng tin hôm nay có trứng chiên, ngon ghê.','Ở đây ngủ sớm dậy sớm, khỏe re.','Mấy con gà ở chuồng kia lanh lắm, coi chừng bị mổ!']},
  bay:{name:'Chú Bảy',top:'#f0a868',seed:9,lines:['Chú ở đây ba ngày mà mập lên hai ký.','Thư viện trại có truyện Kiều đó, đọc hay lắm.',
    'Có bạn bè bảo lãnh là sướng nhất đời.','Tường này chú sơn hôm qua, đẹp hông?','Rau muống nhặt kỹ thì canh mới ngọt nghe.']},
  canbo:{name:'Cán bộ Hùng',top:'#5b7189',seed:15,guard:true,lines:['Làm công ích đàng hoàng, ra trại sớm nha!','Đi lại thoải mái, đừng trèo rào là được.',
    'Cần gì cứ ra bàn trực hỏi nhé.','Sáng mai điểm danh lúc sáu giờ đó!','Rác phân loại cho đúng thùng giùm tui nha.']},
};

const S=(id,kind,hit,r,stand,more={})=>({id,kind,hit,r,stand,...more});
const CACHE=new Map();
/** The camp for this orientation. */
export function plan(port){
  const key=port?'port':'land';
  if(CACHE.has(key))return CACHE.get(key);
  const Lo=LAYOUT[key],f=Lo.floor,sp=Lo.spots,big=port?1.2:1,blocks=[],spots=[];
  const mark=(id,dy=-44)=>[sp[id].hit[0],sp[id].hit[1]+dy*big];
  for(const [task,id] of Object.entries(TASK_SPOT))spots.push(S('task:'+task,'task',sp[id].hit,sp[id].r,sp[id].stand,{task,mark:mark(id)}));
  spots.push(S('bunk','bunk',sp.bunk.hit,sp.bunk.r,sp.bunk.stand,{mark:mark('bunk',-58)}));
  spots.push(S('guard','guard',sp.guard.hit,sp.guard.r,sp.guard.stand,{mark:mark('guard',-56)}));
  spots.push(S('visit','visit',sp.visit.hit,sp.visit.r,sp.visit.stand,{mark:mark('visit',-100)}));
  spots.push(S('gate','gate',sp.gate.hit,sp.gate.r,sp.gate.stand,{mark:mark('gate',-104)}));
  const box=(o,hw,up=12,down=4)=>blocks.push([o.x-hw,o.y-up,o.x+hw,o.y+down]);
  box(Lo.desk,48,22,4);box(Lo.tree,20);box(Lo.bed,Lo.bed.w/2,14,6);box(Lo.kiosk,Lo.kiosk.w/2,16,6);
  box(Lo.bucket,12);box(Lo.veg,32);box(Lo.chair,20);box(Lo.coop,35,22,6);box(Lo.bins,30);box(Lo.ledger,20);
  {const l=Lo.line;blocks.push([l.x-l.w/2-8,l.y-8,l.x-l.w/2+8,l.y+4],[l.x+l.w/2-8,l.y-8,l.x+l.w/2+8,l.y+4]);}
  const g=Lo.gate;blocks.push([g.x-g.w/2-8,g.y-16,g.x-g.w/2+8,g.y+4],[g.x+g.w/2-8,g.y-16,g.x+g.w/2+8,g.y+4]);
  const walkers=Lo.walkers.map(w=>({...w,path:w.path.map(p=>p.slice())}));
  const pl={floor:f,blocks,spots,entry:{bunk:sp.bunk.stand},walkers,port};
  CACHE.set(key,pl);return pl;
}
/** Which composition a stage of cw × ch pixels takes (the pagoda's rule: taller than wide → portrait). */
export const portraitFor=(cw,ch)=>cw/Math.max(1,ch)<.95;
/** Scale and offset of the scene in a stage of cw × ch (band: the height above a panel spanning the stage): the whole
 * camp on a wide screen; on a phone a closer view (at least 80% of each side) that follows `cam` (a scene point)
 * and never shows past the scene's edges. → {k, ox, oy}: screen = scene × k + offset. */
export function frame(port,cw,ch,cam,band=ch){
  const [x0,y0,x1,y1]=VIEW[port?'port':'land'],vw=x1-x0,vh=y1-y0,Z=port?.8:1;
  const k=Math.min(cw/(vw*Z),band/(vh*Z),Math.max(cw/vw,band/vh)*1.6);
  const fitX=vw*k<=cw+.5,fitY=vh*k<=band+.5;
  const ox=fitX?(cw-vw*k)/2-x0*k:Math.min(-x0*k,Math.max(cw-x1*k,cw/2-cam[0]*k));
  const oy=fitY?(band-vh*k)/2-y0*k:Math.min(-y0*k,Math.max(band-y1*k,band/2-cam[1]*k));
  return {k,ox,oy};
}
/** The 12 leaf-pile places of the yard (game/jail.py puzzle('sweep'): a 4 × 3 grid, `piles` are cell indices). */
export function leafAt(port,cell){
  const [x0,y0,x1,y1]=LAYOUT[port?'port':'land'].yard,i=cell%4,j=Math.floor(cell/4);
  return [x0+(i+.5)*(x1-x0)/4+(hash(cell+3)-.5)*14,y0+(j+.5)*(y1-y0)/3+(hash(cell+9)-.5)*10];
}

/* ------------------------------------------------------------ painters */
const INK='#3f4a56',WALL='#f3e7cf',WALL_D='#dccaa6',ROOF='#d9735a',ROOF_D='#b05a44',STEEL='#6d8299',STEEL_D='#4d6077',
  GRASS='#9bd07f',GRASS_D='#73b25c',SOIL='#9a6a42',WOOD='#b78450',WOOD_D='#86592f',CREAM='#fff6e4';
function sign(c,x,y,text,{size=15,bg=CREAM,ink=INK,edge=WOOD_D,min=80}={}){
  const sz=fit(c,text,300,size,800),wd=Math.max(min,c.measureText(text).width+sz*1.4),h=sz*1.9;
  R(c,x-wd/2,y-h/2,wd,h,bg,h/2.4,edge,2);T(c,text,x,y+1,sz,ink,800);
}
/** The backdrop: sky, the camp's wall with its flower pots, the back row of buildings, the yard's ground. */
export function back(c,port,o={}){
  const key=port?'port':'land',[x0,y0,x1,y1]=VIEW[key],Lo=LAYOUT[key],f=Lo.floor,top=Lo.top,big=port?1.2:1;
  const sky=c.createLinearGradient(0,y0,0,top);sky.addColorStop(0,'#8fd0f5');sky.addColorStop(1,'#dff3ff');
  c.fillStyle=sky;c.fillRect(x0-60,y0-60,x1-x0+120,f[1]-y0+60);
  E(c,x1-110*big,y0+62*big,30*big,30*big,'#ffe27a');E(c,x1-110*big,y0+62*big,40*big,40*big,'#ffe27a44');   // the sun
  for(const [cx,cy,s] of [[x0+140,y0+50,1],[x0+(x1-x0)*.48,y0+34,.8],[x0+(x1-x0)*.72,y0+70,.65]]){
    E(c,cx,cy,34*s*big,14*s*big,'#ffffffdd');E(c,cx+22*s*big,cy-8*s*big,22*s*big,14*s*big,'#ffffffdd');E(c,cx-20*s*big,cy-4*s*big,18*s*big,11*s*big,'#ffffffdd');}
  // the camp's outer wall behind the buildings: cream with a green trim and flower pots (no barbed wire)
  R(c,x0-60,top-34,x1-x0+120,f[1]-top+34,WALL,0);R(c,x0-60,top-40,x1-x0+120,10,'#8cc4a0',0);
  for(let x=x0;x<x1;x+=port?62:74){R(c,x+6,top-58,22,18,'#c97a54',4);E(c,x+17,top-62,14,9,'#79bd6a');E(c,x+11,top-66,4,4,'#f27f9c');E(c,x+22,top-64,4,4,'#ffd166');}
  // the ground: a light concrete yard, grass along the edges
  const ground=c.createLinearGradient(0,f[1]-30,0,y1+40);ground.addColorStop(0,'#e9dfcb');ground.addColorStop(1,'#f4ecdc');
  c.fillStyle=ground;c.fillRect(x0-60,f[1]-30,x1-x0+120,y1-f[1]+100);
  c.fillStyle=GRASS;c.fillRect(x0-60,y1-26,x1-x0+120,60);
  for(let i=0;i<46;i++){const x=x0+hash(i+70)*(x1-x0),y=f[1]+hash(i+90)*(y1-f[1]-30);E(c,x,y,6+hash(i)*9,2,'#cdbf9f55');}
  for(let i=0;i<30;i++){const x=x0+hash(i+130)*(x1-x0);L(c,x,y1-24,x+3,y1-34,GRASS_D,2);}
  // a painted walking line across the yard (the cán bộ's morning roll call)
  c.setLineDash?.([14,12]);L(c,f[0]+30,f[1]+(port?66:58),f[2]-30,f[1]+(port?66:58),'#ffffffcc',3);c.setLineDash?.([]);
  cells(c,Lo.cell[0],Lo.cell[1],top,f[1],big,o);
  canteen(c,Lo.cant[0],Lo.cant[1],top,f[1],big,o);
  workshop(c,Lo.work[0],Lo.work[1],top,f[1],big,o);
  if(Lo.booth)booth(c,Lo.booth[0],Lo.booth[1],top,f[1],big);
}
const has=(o,t)=>!!o.done?.includes?.(t),today=(o,t)=>!!o.today?.includes?.(t);
/** The cells: a low blue building, two barred rooms with a bunk each. The left one is the player's (the 🌙 bunk);
 * the right one's blankets lie in a heap until the 🛏️ xếp chăn màn is done today. */
function cells(c,x0,x1,top,base,big,o){
  const w=x1-x0,h=base-top;
  R(c,x0,top+18,w,h-18,'#cfe0ef',6,'#9fb5c9',2);P(c,[[x0-10,top+22],[x1+10,top+22],[x1-6,top-4],[x0+6,top-4]],'#7d9cc0');
  const room=(rx,rw,messy)=>{
    R(c,rx,top+60,rw,h-66,'#eef4f9',6,STEEL_D,2);
    const bx=rx+10,bw=rw-20,by=base-18;
    L(c,bx,by,bx,by-110,WOOD_D,4);L(c,bx+bw,by,bx+bw,by-110,WOOD_D,4);
    for(const yy of [by-16,by-74]){R(c,bx,yy-12,bw,12,WOOD,3);
      if(messy){P(c,[[bx+4,yy-12],[bx+bw*.45,yy-30],[bx+bw-6,yy-16],[bx+bw-2,yy-12]],'#9cc8e8');E(c,bx+bw*.62,yy-18,12,6,'#f6c66b');R(c,bx+bw*.18,yy-26,22,10,'#fff',4);}
      else{R(c,bx+2,yy-20,bw-4,9,'#9cc8e8',4);R(c,bx+4,yy-24,22,10,'#fff',4);for(let k=0;k<4;k++)R(c,bx+32+k*(bw-38)/4,yy-20,(bw-38)/8,9,'#f6c66b',2);}}
    for(let k=1;k<6;k++){const u=rx+k*rw/6;L(c,u,top+62,u,base-6,STEEL,3.4);}
    R(c,rx+rw-16,top+66,10,h-78,'#eef4f9',2);   // the door stands open
  };
  const rw=(w-36)/2;room(x0+12,rw,false);room(x0+24+rw,rw,today(o,'fold')&&!has(o,'fold'));
  sign(c,(x0+x1)/2,top+38,'PHÒNG GIAM',{size:15*big,bg:'#fff',ink:STEEL_D,edge:STEEL_D,min:110});
}
/** The căng tin: a striped awning, the rice pot steaming over the counter (🍚), the sink and its rack (🍜). */
function canteen(c,x0,x1,top,base,big,o){
  const w=x1-x0,cx=(x0+x1)/2;
  R(c,x0,top+14,w,base-top-14,'#fbe9c9',6,'#e0c08e',2);
  R(c,x0+14,top+70,w-28,base-top-120,'#fff7e6',6,'#e0c08e',1.5);
  for(let i=0;i<8;i++)E(c,x0+36+i*(w-72)/7,top+82,7,4,'#ffffff');
  const px=x0+w*.32,py=base-56;R(c,px-30,py-30,60,34,'#9aa3ad',10,'#6d7680',2);R(c,px-34,py-34,68,8,'#b8c0c8',4);
  for(let k=0;k<3;k++){const ph=o.reduced?0:(o.t||0)*1.4+k*2.1,yy=py-44-((ph*12)%26);E(c,px-12+k*12,yy,6,8,'#ffffff99');}
  // the sink: a tap, a basin of bowls (clean and racked once the 🍜 is done today)
  const sx=x0+w*.82;R(c,sx-34,base-64,68,26,'#d9e4ea',6,'#9fb0bd',2);L(c,sx+20,base-64,sx+20,base-84,'#8a96a2',3);L(c,sx+20,base-84,sx+6,base-84,'#8a96a2',3);
  const clean=has(o,'dishes')||!today(o,'dishes');
  for(let i=0;i<4;i++){if(clean)R(c,sx-30+i*16,base-104,12,16,'#ffffff',6,'#c9d4dc',1);else E(c,sx-18+i*12,base-60,9,5,i%2?'#e9e2cf':'#d8c9a0');}
  R(c,x0+6,base-38,w-12,38,WOOD,6,WOOD_D,2);R(c,x0+6,base-42,w-12,8,'#d39b62',4);
  for(let i=0;i<8;i++){const u0=x0-8+i*(w+16)/8,u1=u0+(w+16)/8;P(c,[[u0,top+46],[u1,top+46],[u1-2,top+14],[u0+2,top+14]],i%2?'#fff':'#5dbb8a');}
  for(let i=0;i<8;i++){const u=x0-8+(i+.5)*(w+16)/8;E(c,u,top+46,(w+16)/16,7,i%2?'#fff':'#5dbb8a');}
  sign(c,cx,top+4,'CĂNG TIN',{size:15*big,bg:'#fff4d6',ink:'#7a4a1a',edge:'#c08a52',min:100});
}
/** The khu lao động: the camp library shelf (📚, tidy once done today), an old wall to paint (🎨) and its bucket. */
function workshop(c,x0,x1,top,base,big,o){
  const w=x1-x0,h=base-top,mid=x0+w*.5;
  R(c,x0,top+20,w,h-20,'#e6efd9',6,'#b9c9a4',2);P(c,[[x0-8,top+24],[x1+8,top+24],[x1-6,top],[x0+6,top]],'#8fae6a');
  sign(c,(x0+x1)/2,top+42,'KHU LAO ĐỘNG',{size:14*big,bg:'#fff',ink:'#4d6a2d',edge:'#8fae6a',min:120});
  const sx=x0+12,sw=mid-x0-22,sy=top+74,sh=h-84,tidy=has(o,'books')||!today(o,'books');
  R(c,sx,sy,sw,sh,WOOD,4,WOOD_D,2);
  for(let r=0;r<3;r++){const yy=sy+10+r*(sh-18)/3,bh=(sh-18)/3-8;R(c,sx+6,yy+bh,sw-12,5,WOOD_D,2);
    for(let i=0;i<6;i++){const bw=(sw-16)/7,bx=sx+8+i*(bw+1.5),tilt=!tidy&&(i+r)%3===1;
      c.save();c.translate(bx+bw/2,yy+bh);if(tilt)c.rotate(-.28);R(c,-bw/2,-bh+4,bw,bh-4,['#d0663f','#4f8fc0','#5aa06a','#e0a63a','#9a6ac0','#d0607f'][(i+r*2)%6],2);c.restore();}}
  const wx=mid+4,ww=x1-mid-14,wy=top+74,wh=h-86,fresh=has(o,'paint');
  R(c,wx,wy,ww,wh,fresh?'#ffe9a8':'#c7c9c3',4,'#9a9a92',1.5);
  if(!fresh)for(let i=0;i<5;i++){const px=wx+8+hash(i+20)*(ww-30),py=wy+10+hash(i+33)*(wh-30);E(c,px,py,10+hash(i)*8,7+hash(i+5)*5,'#9da29a');}
  R(c,wx+ww-26,base-30,20,20,'#5f87b8',4);E(c,wx+ww-16,base-30,10,3,'#ffe9a8');
  L(c,wx+ww-40,base-8,wx+ww-52,base-40,WOOD_D,3);R(c,wx+ww-62,base-48,20,10,'#ffe9a8',3);
}
/** The cán bộ trực's booth (landscape): the KHO door, the duty window, the flag. */
function booth(c,x0,x1,top,base,big){
  const w=x1-x0,cx=(x0+x1)/2;
  R(c,x0+6,top+40,w-12,base-top-40,'#dbe7f3',6,'#9fb5c9',2);P(c,[[x0-4,top+44],[x1+4,top+44],[cx,top+6]],'#7d9cc0');
  R(c,cx+6,top+74,64,46,'#bfe3f7',6,STEEL_D,2.5);L(c,cx+38,top+74,cx+38,top+120,STEEL_D,2);
  R(c,x0+18,top+80,52,base-top-82,'#c9a27a',4,WOOD_D,2);E(c,x0+62,top+80+(base-top-82)/2,3,3,'#6b4a2c');T(c,'KHO',x0+44,top+98,13*big,'#5a3a1a',900);
  sign(c,cx+38,top+148,'CÁN BỘ TRỰC',{size:13*big,bg:'#fff',ink:STEEL_D,edge:STEEL_D,min:110});
  L(c,x1-14,base-6,x1-14,top-30,'#8a8f96',3);P(c,[[x1-14,top-30],[x1+28,top-20],[x1-14,top-10]],'#e2462d');T(c,'★',x1+2,top-20,9,'#ffd84a',800);
}

/** The things on the floor: [[depth y, draw]] (sorted with the people by the caller). */
export function props(c,pl,o={}){
  const port=pl.port,Lo=LAYOUT[port?'port':'land'],big=port?1.15:1,out=[],put=(at,fn)=>out.push([at.y,fn]);
  put(Lo.desk,()=>desk(c,Lo.desk.x,Lo.desk.y,big,o));
  put(Lo.tree,()=>tree(c,Lo.tree.x,Lo.tree.y,big*.72,o));
  put(Lo.bed,()=>garden(c,Lo.bed.x,Lo.bed.y,Lo.bed.w,o));
  put(Lo.kiosk,()=>kiosk(c,Lo.kiosk.x,Lo.kiosk.y,Lo.kiosk.w,port?.92:1));
  out.push([Lo.gate.y-70,()=>gate(c,Lo.gate.x,Lo.gate.y,Lo.gate.w,big,o)]);
  put(Lo.bucket,()=>bucket(c,Lo.bucket.x,Lo.bucket.y,o));
  put(Lo.veg,()=>vegTable(c,Lo.veg.x,Lo.veg.y,o));
  put(Lo.chair,()=>chair(c,Lo.chair.x,Lo.chair.y,o));
  put(Lo.line,()=>clothesline(c,Lo.line.x,Lo.line.y,Lo.line.w,o));
  put(Lo.coop,()=>coop(c,Lo.coop.x,Lo.coop.y,o));
  put(Lo.bins,()=>bins(c,Lo.bins.x,Lo.bins.y,o));
  put(Lo.ledger,()=>ledger(c,Lo.ledger.x,Lo.ledger.y,o));
  // the leaves on the yard: today's piles until the yard is swept (none on a day without the sweep)
  if(today(o,'sweep')&&!has(o,'sweep'))for(const cell of o.piles||[]){const [x,y]=leafAt(port,cell);out.push([y-30,()=>leaves(c,x,y,cell)]);}
  return out;
}
function desk(c,x,y,big,o){
  folk(c,x+4,y-16,.8*big,PEOPLE.canbo.seed+40,{t:o.t,reduced:o.reduced,top:'#5b7189',hair:'#2f2a28'});cap(c,x+4,y-16,.8*big);
  R(c,x-50,y-34,100,34,WOOD,5,WOOD_D,2);R(c,x-52,y-38,104,8,'#d39b62',4);
  R(c,x-38,y-46,30,10,'#fff',2,'#c9b49a',1);L(c,x-23,y-46,x-23,y-36,'#c9b49a',1);
  L(c,x+30,y-38,x+30,y-60,'#55606c',2.4);P(c,[[x+20,y-60],[x+40,y-60],[x+34,y-70],[x+26,y-70]],'#f0c24a');
}
/** The cán bộ's cap over a folk() figure drawn at (x,y) with scale s. */
export function cap(c,x,y,s){R(c,x-17*s,y-110*s,34*s,12*s,'#33475e',5*s);R(c,x-10*s,y-100*s,26*s,4*s,'#26364a',2*s);E(c,x,y-106*s,3*s,3*s,'#ffd84a');}
function tree(c,x,y,big,o){
  const sw=o.reduced?0:Math.sin((o.t||0)*.9)*2;
  E(c,x,y,40*big,9,'#00000018');R(c,x-10,y-110*big,20,112*big,'#8a6240',8);
  L(c,x+22,y,x+40,y-70,'#b88b62',4);E(c,x+20,y-2,14,5,'#d9b97a');   // the broom leaning on it
  for(const [dx,dy,r,col] of [[-46,-150,48,'#6fbf63'],[42,-156,50,'#62b25a'],[0,-196,58,'#7ccc6c'],[-14,-130,40,'#86d277'],[30,-118,36,'#74c466']])
    E(c,x+dx*big+sw,y+dy*big,r*big,r*.82*big,col);
  for(let i=0;i<6;i++)E(c,x+(-50+hash(i+60)*100)*big+sw,y+(-200+hash(i+61)*120)*big,5,4,'#e6b84a');
}
function garden(c,x,y,w,o){
  const grown=has(o,'plant'),n=5;
  R(c,x-w/2,y-20,w,24,'#c9b49a',6,'#9a8a6a',1.5);R(c,x-w/2+5,y-17,w-10,12,SOIL,4);
  for(let i=0;i<n;i++){const px=x-w/2+14+i*(w-28)/(n-1);
    if(grown){L(c,px,y-14,px,y-34,'#4f9a45',2.4);E(c,px-6,y-32,6,3.4,'#6fbf63');E(c,px+6,y-36,6,3.4,'#6fbf63');}
    else E(c,px,y-12,5,2.6,'#6b4a2c');}
}
function kiosk(c,x,y,w,k){
  const hw=w/2,top=y-112*k;
  R(c,x-hw,top,w,y-top,'#f7d7c9',8,'#d79b86',2);
  R(c,x-hw+10,top+26*k,w-20,42*k,'#cfeefc',6,'#7d9cc0',2);L(c,x,top+26*k,x,top+68*k,'#7d9cc0',2);
  folk(c,x+hw*.42,top+72*k,.4*k,22,{reduced:true,top:'#e3a7b8'});
  R(c,x-hw+6,y-32,w-12,28,'#e9b9a6',5,'#c98a74',1.5);R(c,x-hw*.6,y-44,16,10,'#3b3f45',3);L(c,x-hw*.6+8,y-44,x-hw*.6+2,y-58,'#3b3f45',2);
  sign(c,x,top-6,'THĂM GẶP',{size:12*k,bg:'#fff',ink:'#a0503c',edge:'#d79b86',min:90});
}
function gate(c,x,y,w,big,o){
  const hw=w/2,top=y-170*Math.min(big,1.1);
  for(const px of [x-hw,x+hw]){R(c,px-8,top,16,y-top,'#7d9cc0',4,STEEL_D,2);E(c,px,top-4,10,10,'#ffd166');}
  R(c,x-hw-14,top+6,w+28,26*big,'#fff',8,STEEL_D,2);T(c,'CỔNG TRẠI',x,top+19*big,fit(c,'CỔNG TRẠI',w,14*big,900),STEEL_D,900);
  R(c,x-hw+8,top+40*big,w-16,y-top-40*big,'#fff3c4',2);
  for(let i=0;i<7;i++){const u=x-hw+12+i*(w-24)/6;L(c,u,top+40*big,u,y-2,STEEL,3);}
  L(c,x-hw+8,top+44*big,x+hw-8,top+44*big,STEEL_D,3);L(c,x-hw+8,y-24,x+hw-8,y-24,STEEL_D,3);
}
/** 🧽 a mop in its bucket (a shine on the floor once the cells are mopped today). */
function bucket(c,x,y,o){
  if(has(o,'mop'))for(let i=0;i<3;i++)T(c,'✦',x-30+i*30,y-46-(i%2)*10,12,'#9fd3f5',900);
  E(c,x,y,16,5,'#00000018');R(c,x-13,y-26,26,26,'#4f8fc0',5,'#36668f',1.5);E(c,x,y-26,13,4,'#9fd3f5');
  L(c,x+4,y-24,x+16,y-86,WOOD_D,3);E(c,x+2,y-24,9,5,'#e8e2d0');
}
/** 🥬 the vegetable table: a heap of rau muống with yellow leaves in it, a bundle once picked over. */
function vegTable(c,x,y,o){
  E(c,x,y,36,6,'#00000018');L(c,x-26,y,x-26,y-26,WOOD_D,3);L(c,x+26,y,x+26,y-26,WOOD_D,3);R(c,x-36,y-34,72,10,WOOD,3,WOOD_D,1.5);
  if(has(o,'veg')){for(let i=0;i<5;i++)L(c,x-14+i*7,y-36,x-18+i*8,y-60,'#4f9a45',3);R(c,x-16,y-46,32,6,'#c9772e',2);}
  else for(let i=0;i<9;i++)E(c,x-24+i*6,y-40-(i%3)*4,6,3.4,today(o,'veg')&&i%3===1?'#e6c84a':'#6fbf63');
  E(c,x+20,y-38,9,5,'#f0d9a8');   // the basket
}
/** 🔨 a chair: one leg off and a hammer beside it, standing straight once fixed today. */
function chair(c,x,y,o){
  const ok=has(o,'fix')||!today(o,'fix'),tilt=ok?0:.18;
  E(c,x,y,22,5,'#00000018');c.save();c.translate(x,y);c.rotate(tilt);
  R(c,-18,-34,36,7,WOOD,2,WOOD_D,1.2);R(c,-16,-70,6,38,WOOD_D,2);R(c,10,-70,6,38,WOOD_D,2);R(c,-16,-70,32,6,WOOD,2);
  L(c,-14,-28,-14,0,WOOD_D,4);if(ok)L(c,14,-28,14,0,WOOD_D,4);else L(c,14,-28,14,-14,WOOD_D,4);
  c.restore();if(!ok){L(c,x+26,y-2,x+40,y-6,'#7a5230',3);R(c,x+36,y-12,10,8,'#6b737c',2);}
}
/** 👕 the clothesline between two posts: a basket of washing, or the clothes hung up to dry. */
function clothesline(c,x,y,w,o){
  const x0=x-w/2,x1=x+w/2,top=y-96,sag=10;
  L(c,x0,y,x0,top,'#8a8f96',3);L(c,x1,y,x1,top,'#8a8f96',3);
  c.strokeStyle='#d0d0c8';c.lineWidth=1.4;c.beginPath();c.moveTo(x0,top+4);c.quadraticCurveTo(x,top+4+sag*2,x1,top+4);c.stroke();
  const cols=['#e07a5f','#81b29a','#f2cc8f','#9fb0d8','#e3a7b8'];
  if(has(o,'laundry'))for(let i=0;i<5;i++){const u=x0+14+i*(w-28)/4,yy=top+6+sag*2*(1-((u-x)/(w/2))**2)*.9;R(c,u-9,yy,18,i%2?16:22,cols[i],3);}
  else{R(c,x-22,y-18,44,18,'#d8b98a',6,'#a8865a',1.5);for(let i=0;i<4;i++)E(c,x-14+i*9,y-18,6,4,cols[i]);}
}
/** 🐔 the chicken coop: a little hut, a fence, chickens (pecking at their grain once fed today). */
function coop(c,x,y,o){
  const fed=has(o,'chicken'),t=o.reduced?0:(o.t||0);
  R(c,x-34,y-44,40,40,'#d9a868',4,WOOD_D,1.5);P(c,[[x-38,y-44],[x+10,y-44],[x-14,y-62]],'#c0533a');R(c,x-22,y-24,14,18,'#6b4a2c',4);
  for(let i=0;i<5;i++)L(c,x+12+i*6,y,x+12+i*6,y-24,WOOD_D,2);L(c,x+8,y-16,x+38,y-16,WOOD,2);
  for(const [dx,dy,k] of [[18,-6,0],[-4,4,1],[30,6,2]]){const peck=fed?Math.abs(Math.sin(t*3+k))*4:0,bx=x+dx,by=y+dy;
    E(c,bx,by-8+peck*.4,9,7,k===1?'#c9772e':'#fff');E(c,bx+7,by-14+peck,4.5,4.5,k===1?'#c9772e':'#fff');E(c,bx+8,by-19+peck,2.4,2,'#e2462d');P(c,[[bx+11,by-14+peck],[bx+15,by-13+peck],[bx+11,by-12+peck]],'#f0b44a');}
  if(fed)for(let i=0;i<8;i++)E(c,x-6+hash(i+5)*44,y+8+hash(i+9)*6,1.6,1.2,'#e6b84a');
}
/** 🗑️ three bins (tái chế, giấy, hữu cơ), litter around them until sorted today. */
function bins(c,x,y,o){
  const cols=['#4f8fc0','#e6b84a','#5aa06a'],lab=['♻','📄','🍃'];
  for(let i=0;i<3;i++){const bx=x-22+i*22;R(c,bx-9,y-30,18,30,cols[i],4,'#00000033',1);R(c,bx-10,y-34,20,6,cols[i],3);T(c,lab[i],bx,y-16,9,'#fff',800);}
  if(today(o,'trash')&&!has(o,'trash'))for(let i=0;i<4;i++){const lx=x-50+hash(i+44)*100,ly=y+6+hash(i+47)*10;
    if(i%2)R(c,lx-5,ly-3,10,6,'#dfe4ea',2);else E(c,lx,ly,5,3,i?'#e6c84a':'#9bd07f');}
}
/** 📒 the kho's book on a small table: open with a pen, closed and ticked once done today. */
function ledger(c,x,y,o){
  E(c,x,y,22,5,'#00000018');L(c,x-14,y,x-14,y-22,WOOD_D,3);L(c,x+14,y,x+14,y-22,WOOD_D,3);R(c,x-22,y-30,44,9,WOOD,3,WOOD_D,1.2);
  if(has(o,'ledger')){R(c,x-12,y-40,24,10,'#4f6d8f',2);T(c,'✓',x,y-35,9,'#fff',900);}
  else{R(c,x-18,y-40,17,10,'#fffaf0',1.5,'#c9b49a',1);R(c,x+1,y-40,17,10,'#fffaf0',1.5,'#c9b49a',1);L(c,x+6,y-44,x+14,y-52,'#3b3f45',2);}
}
function leaves(c,x,y,seed){
  for(let i=0;i<5;i++)E(c,x-10+hash(seed*7+i)*20,y-4+hash(seed*5+i)*6,7,3.6,['#d99a3a','#c9772e','#e6b84a','#b8692a','#9bb04a'][i]);
}

/** A speech bubble over (x,y) (the speaker's head), clamped to [x0,x1]. */
export function bubble(c,x,y,text,{x0=-1e9,x1=1e9,size=14,ink=INK,bg='#fffdf6'}={}){
  const sz=fit(c,text,320,size,700),wd=Math.min(340,c.measureText(text).width+20),h=sz+14,bx=Math.max(x0+wd/2+4,Math.min(x1-wd/2-4,x));
  R(c,bx-wd/2,y-h-10,wd,h,bg,h/2,'#d8cdb8',1.5);P(c,[[x-6,y-11],[x+6,y-11],[x,y-2]],bg);
  T(c,text,bx,y-10-h/2+1,sz,ink,700);
}
/** Badges over the places: a task's emoji (dim, ✓ when done; not today: none), the panels' signs. */
export function marks(c,pl,o={},near=null){
  const big=pl.port?1.3:1;
  for(const s of pl.spots){
    if(s.kind==='look'||near===s.id)continue;
    let icon='',dim=false,ok=false;
    if(s.kind==='task'){if(!o.today?.includes?.(s.task))continue;ok=o.done?.includes?.(s.task);icon=ok?'✓':TASK_ICON[s.task];dim=ok;}
    else{icon={bunk:'🌙',guard:'📋',visit:'🤝',gate:'🚪'}[s.kind];dim=s.kind==='bunk'&&!o.ready;}
    const [x,y]=s.mark,bob=o.reduced||dim?0:Math.sin((o.t||0)*2+x)*3,yy=y+bob;
    c.globalAlpha=dim?.6:1;E(c,x,yy,17*big,17*big,dim?'#eef0f2':'#fffaf0');
    c.strokeStyle=s.kind==='task'?ok?'#6b8f4a':'#e0a63a':'#7d9cc0';c.lineWidth=2.4;c.beginPath();c.arc(x,yy,17*big,0,Math.PI*2);c.stroke();
    T(c,icon,x,yy+1,(ok?17:16)*big,ok?'#4f7a34':INK,ok?900:400);c.globalAlpha=1;
    if(s.kind==='gate'&&o.left){E(c,x+15*big,yy-13*big,9*big,9*big,'#e2462d');T(c,String(o.left),x+15*big,yy-12.5*big,11*big,'#fff',900);}
  }
}
export {T,fit,R,E,L};
