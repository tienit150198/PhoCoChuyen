/** 🏮 Hội chợ dân gian as a place to walk around (v4/fair-walk.js): one evening fairground under strings of lanterns.
 * Back row: cô Bảy's gánh lô tô stage, chú Tám's bầu cua tent, cô Tư's ném vòng counter, anh Sáu's phóng dao board
 * (when the server has the stall). On the ground: the ô ăn quan mat (Bé Bi, Ông Hai), the Bảng vàng, bà Sáu's
 * vay nóng stool by the Cổng hội (when the server lends), dì Hai's vé số cào stand (when the server sells them), the
 * 📸 photobooth with its curtain and marquee lights (when the server sells tickets; v4/fair-booth.js), anh
 * Ba's chiếu trong tucked in a dark corner, two food carts and the crowd. Walking uses the pagoda's path finder (scenes/chua-place.js: one floor rectangle, footprints,
 * a grid A* string-pulled), so a plan here has the same shape:
 *   plan(port, has) → {floor, blocks, spots:[{id, kind, hit, r, stand, tab?, line?}], entry:{gate}, crowd:[{x,y,seed}]}
 *   kind 'stall' opens the stall `tab` of v4/fair.js, 'look' (the gate, the carts) and 'npc' (the crowd) say a line;
 *   a cart (cart: true) opens its menu instead when the server sells food.
 *   has: {dt, loan, xs, pb} (stalls an older server does not have are left out; a crowd member standing where the
 *   photobooth goes steps out when it is there).
 * Pure (no DOM, no server); scene pixels: landscape 1200×790, portrait 700×890 like the workplaces. Nothing moves
 * when `reduced` is set. back() paints what never moves (cached by the caller), props() what stands on the floor. */
import {R,E,L,T,P,fit} from './kit.js';
import {sitter,hash} from './interior.js';
import {route,blocked,nearestFree,lineFree} from './chua-place.js';

export {route,blocked,nearestFree,lineFree};
/** The drawn part of the scene per orientation (what the stage fits). */
export const VIEW={land:[50,100,1150,760],port:[14,104,686,868]};

/* ------------------------------------------------------------ where things are */
const LAYOUT={
  land:{floor:[80,440,1120,740],
    lt:{x:225,y:420,w:270},bc:{x:490,y:420,w:170},ring:{x:710,y:420,w:170},dt:{x:920,y:420,w:150},
    xd:{x:1075,y:520,w:110,stand:[1065,562]},oaq:{x:565,y:600,w:250},board:{x:820,y:610},loan:{x:290,y:610},
    xs:{x:720,y:686},pb:{x:1062,y:712,w:96},gate:{x:140,y:740,w:130},candy:{x:380,y:705},cane:{x:960,y:705},
    crowd:[[180,522],[600,505],[815,500],[380,528],[1000,612],[1075,652,'pb'],[470,702]],back:['lt','bc','ring','dt']},
  port:{floor:[30,445,670,860],
    lt:{x:137,y:430,w:220},bc:{x:367,y:435,w:175},ring:{x:582,y:435,w:175},dt:{x:597,y:632,w:135},
    xd:{x:615,y:850,w:110,stand:[528,826]},oaq:{x:290,y:640,w:220},board:{x:65,y:572},loan:{x:260,y:800},
    xs:{x:565,y:722},pb:{x:322,y:822,w:74},gate:{x:105,y:860,w:126},candy:{x:430,y:770},cane:{x:460,y:540},
    crowd:[[230,522],[545,522],[190,762],[372,702,'pb'],[120,692]],back:['lt','bc','ring']},
};
/** The stalls: the tab of v4/fair.js they open, their badge and the words on their sign. */
export const STALLS={
  lt:{tab:'lt',icon:'🎱',name:'Gánh lô tô'},bc:{tab:'bc',icon:'🦀',name:'Bầu cua'},ring:{tab:'ring',icon:'💍',name:'Ném vòng'},
  dt:{tab:'dt',icon:'🗡️',name:'Phóng dao'},xd:{tab:'xd',icon:'🕯️',name:'Chiếu trong'},oaq:{tab:'oaq',icon:'🪨',name:'Ô ăn quan'},
  board:{tab:'board',icon:'🏆',name:'Bảng vàng'},loan:{tab:'loan',icon:'💸',name:'Vay nóng'},xs:{tab:'xs',icon:'🎟️',name:'Vé số cào'},
  pb:{tab:'pb',icon:'📸',name:'Chụp ảnh'},
};
export const LOOKS={
  gate:'Cổng chợ đen treo lồng đèn đỏ lờ mờ. Nộp bảo kê rồi vô chơi nha!',
  candy:'Kẹo bông gòn đây! Hồng hồng, xốp xốp, ngọt lịm nè!',
  cane:'Nước mía ép tại chỗ, thêm chút tắc cho thơm, mát lạnh luôn!',
};
export const CROWD_LINES=['Chợ năm nay vui quá trời!','Qua coi cô Bảy hô lô tô kìa, vui lắm!','Tui ném vòng trúng ba chai rồi đó!','Bầu cua chỗ chú Tám đông ghê ha.',
  'Mẹ ơi, con muốn ăn kẹo bông!','Đi chậm thôi, đông người lắm.','Ông Hai chơi ô ăn quan cao tay lắm đó.','Tối nay có đèn lồng đẹp ghê.',
  'Tui mới cào vé số chỗ dì Hai, trúng gấp đôi nè!','Rủ bạn vô buồng chụp ảnh đi, khung Tết đẹp lắm!'];

const S=(id,kind,hit,r,stand,more={})=>({id,kind,hit,r,stand,...more});
const CACHE=new Map();
/** The fairground for this orientation; `has` {dt, loan, xs, pb}: the optional stalls. */
export function plan(port,has={}){
  const key=[port,!!has.dt,!!has.loan,!!has.xs,!!has.pb].join('|');
  if(CACHE.has(key))return CACHE.get(key);
  const Lo=LAYOUT[port?'port':'land'],big=port?1.25:1,blocks=[],spots=[],on=id=>!['dt','loan','xs','pb'].includes(id)||!!has[id];
  // mark: where the stall's badge floats (clear of the keeper's face and the signs)
  const stall=(id,block,hit,r,stand,mark)=>{if(!on(id))return;blocks.push(block);spots.push(S(id,'stall',hit,r,stand,{tab:STALLS[id].tab,mark}));};
  for(const id of ['lt','bc','ring','dt']){
    const s=Lo[id],back=Lo.back.includes(id),hw=s.w/2;
    if(back)stall(id,[s.x-hw+8,s.y-40,s.x+hw-8,s.y+8],[s.x,s.y-80],Math.max(66,s.w*.42)*big,[s.x,s.y+44],[s.x+hw-24*big,s.y-(id==='lt'?150:128)*big]);
    else stall(id,[s.x-hw+8,s.y-30,s.x+hw-8,s.y+6],[s.x,s.y-70],62*big,[s.x,s.y+42],[s.x-hw+4,s.y-96*big]);
  }
  {const s=Lo.xd;stall('xd',[s.x-s.w/2,s.y-50,s.x+s.w/2,s.y+(s.y>=Lo.floor[3]-20?40:0)],   // in the bottom corner: no sliver of floor under it
    [s.x,s.y-56],58*big,s.stand,[s.x+s.w/2-14*big,s.y-150*big]);}
  {const s=Lo.oaq;stall('oaq',[s.x-s.w/2,s.y-45,s.x+s.w/2,s.y],[s.x,s.y-34],Math.max(80,s.w*.4)*big,[s.x,s.y+40],[s.x,s.y-70*big]);}
  {const s=Lo.board;stall('board',[s.x-30,s.y-18,s.x+30,s.y],[s.x,s.y-62],50*big,[s.x,s.y+40],[s.x+40*big,s.y-122*big]);}
  {const s=Lo.loan;stall('loan',[s.x-35,s.y-18,s.x+35,s.y],[s.x,s.y-56],48*big,[s.x,s.y+40],[s.x-44*big,s.y-62*big]);}
  {const s=Lo.xs;stall('xs',[s.x-62,s.y-20,s.x+38,s.y],[s.x-8,s.y-58],50*big,[s.x,s.y+36],[s.x+58*big,s.y-84*big]);}
  {const s=Lo.pb,hw=s.w/2;stall('pb',[s.x-hw,s.y-20,s.x+hw,s.y],[s.x,s.y-70*big],56*big,[s.x,s.y+24],[s.x+hw+16*big,s.y-176*big]);}
  const g=Lo.gate,entry=[g.x,g.y-40];
  blocks.push([g.x-g.w/2-8,g.y-14,g.x-g.w/2+8,g.y],[g.x+g.w/2-8,g.y-14,g.x+g.w/2+8,g.y]);
  spots.push(S('gate','look',[g.x,g.y-150],62*big,entry,{line:LOOKS.gate}));
  for(const id of ['candy','cane']){const c=Lo[id];blocks.push([c.x-35,c.y-20,c.x+35,c.y]);spots.push(S(id,'look',[c.x,c.y-62],44*big,[c.x,c.y+30],{line:LOOKS[id],cart:true}));}
  const crowd=Lo.crowd.map(([x,y,away],i)=>({x,y,seed:i*7+3,away})).filter(q=>!q.away||!on(q.away));   // seeds by place: the others never change
  for(const q of crowd){blocks.push([q.x-24,q.y-7,q.x+24,q.y+6]);
    spots.push(S('npc:'+q.seed,'npc',[q.x,q.y-58],34*big,[q.x,Math.min(Lo.floor[3]-4,q.y+40)],{line:CROWD_LINES[q.seed%CROWD_LINES.length]}));}
  const pl={floor:Lo.floor,blocks,spots,entry:{gate:entry},crowd,port,has:{dt:on('dt'),loan:on('loan'),xs:on('xs'),pb:on('pb')}};
  if(CACHE.size>16)CACHE.clear();
  CACHE.set(key,pl);return pl;
}

/* ------------------------------------------------------------ painters */
const WOOD='#a8743f',WOOD_D='#7a5230',RED='#c8423a',RED_D='#8f2d2a',GOLD='#e6b34a',CREAM='#fff4df',INK='#4a3226';
const HAIR=['#3b2f2a','#5b4636','#2f2a28','#6e4f3c','#b9b1a8'],SKIN=['#f6d8bf','#eec7a6','#e2b48f','#f9dfc8'],
  TOPS=['#e07a5f','#81b29a','#f2cc8f','#9fb0d8','#e3a7b8','#c4b2e0','#8fc0c9','#f0a868'];
/** A fairgoer standing at (x,y) = feet, s = scale, seed picks the colours; `kid` smaller; t sways them a little. */
export function folk(c,x,y,s,seed,{t=0,reduced=false,kid=false,top=null,hair=null,hat=''}={}){
  const n=Math.floor(hash(seed)*997),h=hair||HAIR[n%5],sk=SKIN[n%4],tp=top||TOPS[n%8],sw=reduced?0:Math.sin(t*1.7+seed)*1.6;
  c.save();c.translate(x,y);c.scale(s*(kid?.74:1),s*(kid?.74:1));
  E(c,0,0,22,6,'#2a1c1626');
  R(c,-12,-40,10,40,'#4b5468',4);R(c,2,-40,10,40,'#4b5468',4);
  c.translate(sw,0);
  R(c,-19,-76,38,42,tp,13);E(c,-21,-58,6,13,tp);E(c,21,-58,6,13,tp);
  E(c,0,-92,18,19,h);E(c,0,-88,15,16,sk);
  if(n%3===0)R(c,-16,-108,32,10,h,5);else E(c,-5,-104,11,7,h);
  E(c,-5,-89,1.8,2.2,'#3a2a22');E(c,5,-89,1.8,2.2,'#3a2a22');E(c,-9,-84,3,1.6,'#f0a3a0aa');E(c,9,-84,3,1.6,'#f0a3a0aa');
  if(hat==='non'){P(c,[[-26,-100],[26,-100],[0,-126]],'#e9d29a');L(c,-26,-100,26,-100,'#b89a5a',2);}
  else if(hat==='shades'){R(c,-12,-93,10,6,'#222',3);R(c,2,-93,10,6,'#222',3);L(c,-2,-90,2,-90,'#222',2);}
  else if(hat==='mic'){L(c,16,-70,22,-88,'#333',3);E(c,23,-91,4,4,'#555');}
  c.restore();
}
/** A string of lanterns between (x0,y0) and (x1,y1) sagging `sag`, every `step` px. */
function lanterns(c,x0,y0,x1,y1,sag,step,o,big=1){
  c.strokeStyle='#5a3a2a';c.lineWidth=1.6;c.beginPath();
  const at=u=>[x0+(x1-x0)*u,y0+(y1-y0)*u+sag*4*u*(1-u)];
  for(let i=0;i<=24;i++){const [x,y]=at(i/24);i?c.lineTo(x,y):c.moveTo(x,y);}c.stroke();
  const n=Math.max(2,Math.round(Math.abs(x1-x0)/step));
  for(let i=1;i<n;i++){const [x,y]=at(i/n),col=i%3===1?GOLD:RED;
    E(c,x,y+16*big,20*big,20*big,col===RED?'#ff8a5c22':'#ffd77a22');
    L(c,x,y,x,y+6*big,'#5a3a2a',1.4);E(c,x,y+16*big,9*big,11*big,col);R(c,x-5*big,y+5*big,10*big,3*big,WOOD_D,1);R(c,x-5*big,y+26*big,10*big,3*big,WOOD_D,1);
    L(c,x,y+29*big,x,y+35*big,col,1.4);E(c,x-3*big,y+12*big,2.4*big,4*big,'#ffffff55');}
}
function sign(c,x,y,text,{size=16,bg=CREAM,ink=INK,edge=WOOD_D,min=70,bitmap=null}={}){
  if(bitmap){bitmap('sign:'+text,[x-190,y-34,380,68],q=>sign(q,x,y,text,{size,bg,ink,edge,min}));return;}
  const sz=fit(c,text,320,size,800),wd=Math.max(min,c.measureText(text).width+sz*1.4),h=sz*1.9;
  R(c,x-wd/2,y-h/2,wd,h,bg,h/2.4,edge,2);T(c,text,x,y+1,sz,ink,800);
}
/** The backdrop: the evening sky, the trees, the ground, the strings of lanterns, the back row of stalls. */
export function back(c,port,has={},o={}){
  const [x0,y0,x1,y1]=VIEW[port?'port':'land'],Lo=LAYOUT[port?'port':'land'],f=Lo.floor,big=port?1.35:1;
  const sky=c.createLinearGradient(0,y0,0,f[1]-40);sky.addColorStop(0,'#3a3a6a');sky.addColorStop(.55,'#8c5f86');sky.addColorStop(1,'#f0a77a');
  c.fillStyle=sky;c.fillRect(x0-60,y0-60,x1-x0+120,f[1]-y0+60);
  for(let i=0;i<14;i++){const x=x0+hash(i+1)*(x1-x0),y=y0+12+hash(i+40)*110;E(c,x,y,1.6,1.6,'#fff6d8cc');}
  E(c,x1-90*big,y0+56*big,22*big,22*big,'#fff1c9');E(c,x1-82*big,y0+50*big,22*big,22*big,'#8c6a92');   // a slim moon
  for(let i=0;i<9;i++){const x=x0+i*(x1-x0)/8,r=(60+hash(i+9)*40)*big;E(c,x,f[1]-70,r,r*.8,i%2?'#5b5a6e':'#4f5066');}
  const ground=c.createLinearGradient(0,f[1]-60,0,y1+40);ground.addColorStop(0,'#c9a27a');ground.addColorStop(1,'#e2c49a');
  c.fillStyle=ground;c.fillRect(x0-60,f[1]-60,x1-x0+120,y1-f[1]+120);
  for(let i=0;i<40;i++){const x=x0+hash(i+70)*(x1-x0),y=f[1]+hash(i+90)*(y1-f[1]);E(c,x,y,8+hash(i)*10,2.4,'#b98f6644');}
  lanterns(c,x0-10,y0+30,x1+10,y0+40,46,port?90:96,o,big);
  lanterns(c,x0-10,y0+100,x1+10,y0+90,30,port?110:130,o,big);
  const Lb=Lo.back;
  if(Lb.includes('lt'))stage(c,Lo.lt,big,o);
  if(Lb.includes('bc'))tent(c,Lo.bc,big,'#d9534f','BẦU CUA',o,'bc');
  if(Lb.includes('ring'))tent(c,Lo.ring,big,'#4f8fc0','NÉM VÒNG',o,'ring');
  if(Lb.includes('dt')&&has.dt)tent(c,Lo.dt,big,'#5aa06a','PHÓNG DAO',o,'dt');
  else if(Lb.includes('dt'))emptyStall(c,Lo.dt,big);
}
/** Cô Bảy's gánh lô tô: a little wooden stage, red curtains, a bulb string, her mic. */
function stage(c,s,big,o){
  const {x,y,w}=s,top=y-200*Math.min(big,1.15),hw=w/2;
  R(c,x-hw,top,w,y-40-top,RED_D,10);
  for(let i=0;i<8;i++){const u=x-hw+8+i*(w-16)/7;L(c,u,top+10,u,y-44,'#a83a36',5);}
  R(c,x-hw-6,top-12,w+12,30*big,GOLD,8,WOOD_D,2);T(c,'GÁNH LÔ TÔ',x,top+3*big,fit(c,'GÁNH LÔ TÔ',w-20,17*big,900),RED_D,900);
  for(let i=0;i<9;i++){const u=x-hw+12+i*(w-24)/8;E(c,u,top+26*big,4*big,4*big,i%2?'#ffe9a6':'#ffd27a');}
  folk(c,x,y-40,.95*Math.min(big,1.2),11,{t:o.t,reduced:o.reduced,top:'#e86aa0',hair:'#2f2a28',hat:'mic'});
  R(c,x-hw-4,y-44,w+8,44,WOOD,6,WOOD_D,2);for(let i=1;i<6;i++)L(c,x-hw+i*w/6,y-40,x-hw+i*w/6,y-4,WOOD_D,1.4);
}
const KEEP={bc:{seed:21,top:'#7d5a8c',hat:''},ring:{seed:5,top:'#f0a868',hat:'non'},dt:{seed:14,top:'#4b7a5a',hat:''}};
/** A striped tent with its keeper behind the counter and the stall's own things on it. */
function tent(c,s,big,col,label,o,id){
  const {x,y,w}=s,hw=w/2,top=y-170*Math.min(big,1.15);
  R(c,x-hw+6,top+20,w-12,y-top-20,'#f6e6c8',4);
  L(c,x-hw+8,top+16,x-hw+8,y,WOOD_D,5);L(c,x+hw-8,top+16,x+hw-8,y,WOOD_D,5);
  if(id==='ring')for(let r=0;r<3;r++)for(let i=0;i<5;i++){const bx=x-hw+26+i*(w-52)/4,by=top+64+r*28;R(c,bx-5,by-16,10,18,['#7cc79a','#8fb6e8','#f0b46a'][(i+r)%3],3);R(c,bx-2,by-22,4,7,'#5a7d6a',1);R(c,x-hw+14,by+2,w-28,4,WOOD,1);}
  if(id==='dt')knifeBoard(c,x,top+78,30);
  if(id==='bc'){for(let i=0;i<3;i++)E(c,x-30+i*30,top+60,9,9,['#fff','#fde3d8','#fff'][i]);}
  const k=KEEP[id];folk(c,id==='dt'?x+hw-32:x,y-26,.9*Math.min(big,1.2),k.seed,{t:o.t,reduced:o.reduced,top:k.top,hat:k.hat});
  // the awning: stripes, scallops, the sign
  for(let i=0;i<8;i++){const u0=x-hw-8+i*(w+16)/8,u1=u0+(w+16)/8;P(c,[[u0,top+22],[u1,top+22],[u1-2,top-10],[u0+2,top-10]],i%2?CREAM:col);}
  for(let i=0;i<8;i++){const u=x-hw-8+(i+.5)*(w+16)/8;E(c,u,top+22,(w+16)/16,8,i%2?CREAM:col);}
  sign(c,x,top-26*big,label,{size:15*big,min:90});
  // the counter
  R(c,x-hw+4,y-38,w-8,38,WOOD,6,WOOD_D,2);R(c,x-hw+4,y-40,w-8,8,'#c08a52',4);
  if(id==='bc'){const fw=(w-40)/3;['🎃','🦀','🦐','🐟','🐓','🦌'].forEach((e,i)=>{const fx=x-hw+20+(i%3)*fw,fy=y-36+(i>2?16:0);R(c,fx+1,fy+1,fw-2,14,i%2?'#fff3df':'#ffe2c8',3);T(c,e,fx+fw/2,fy+8,10,INK,400);});}
  if(id==='ring')for(let i=0;i<4;i++){c.strokeStyle=['#e2462d','#f0b44a','#3c8fd0','#5aa06a'][i];c.lineWidth=3;c.beginPath();c.ellipse(x-36+i*24,y-22,9,4,0,0,Math.PI*2);c.stroke();}
}
/** Anh Sáu's board: a round of wood, its growth rings, a red heart and three knives stuck in it (v4/fair-knife.js). */
function knifeBoard(c,x,y,r){
  E(c,x+2,y+3,r+3,r+3,'#00000030');E(c,x,y,r+3,r+3,WOOD_D);E(c,x,y,r,r,'#d9a868');
  c.strokeStyle='#8a5a2666';c.lineWidth=1;for(let k=.3;k<1;k+=.22){c.beginPath();c.arc(x,y,r*k,0,Math.PI*2);c.stroke();}
  E(c,x,y,r*.22,r*.22,'#d9472b');E(c,x,y,r*.08,r*.08,GOLD);
  for(const a of [-.6,1.7,3.4]){const cs=Math.cos(a),sn=Math.sin(a),t0=r*.7,t1=r*1.55,mid=r*1.05;
    L(c,x+cs*t0,y+sn*t0,x+cs*mid,y+sn*mid,'#dfe4ea',3.4);L(c,x+cs*mid,y+sn*mid,x+cs*t1,y+sn*t1,'#7a4a22',4);}
}
/** Where the phóng dao stands on a server that has none: a folded tent. */
function emptyStall(c,s,big){const {x,y,w}=s;R(c,x-w/2+20,y-30,w-40,26,'#b4936c',6);L(c,x-w/2+24,y-30,x+w/2-24,y-30,'#8a6a48',3);T(c,'…',x,y-50,18*big,'#8a6a48',800);}

/** The things on the floor: [[depth y, draw]] (sorted with the player by the caller). */
export function props(c,pl,o={}){
  const port=pl.port,Lo=LAYOUT[port?'port':'land'],big=port?1.25:1,out=[],s1=(port?.92:.78);
  const ts={t:o.t||0,reduced:!!o.reduced,bitmap:o.bitmap};
  // Keep the original depth ordering; only these unchanging floor objects use caller-owned bitmaps.
  const fixed=(id,s,paint,half=150,head=270)=>out.push([s.y,()=>o.bitmap?o.bitmap('prop:'+id,[s.x-half,s.y-head,half*2,head+24],paint):paint(c)]);
  if(!Lo.back.includes('dt')&&pl.has.dt){const s=Lo.dt;out.push([s.y,()=>booth(c,s,big,ts)]);}
  {const s=Lo.xd;out.push([s.y,()=>corner(c,s,big,ts)]);}
  {const s=Lo.oaq;fixed('oaq',s,q=>mat(q,s,big,ts));}
  {const s=Lo.board;fixed('board',s,q=>board(q,s,big),80,160);}
  if(pl.has.loan){const s=Lo.loan;fixed('loan',s,q=>lender(q,s,big),120,170);}
  if(pl.has.xs){const s=Lo.xs;out.push([s.y,()=>tickets(c,s,big,ts)]);}
  if(pl.has.pb){const s=Lo.pb;out.push([s.y,()=>photobooth(c,s,port?1.12:1,ts)]);}
  {const g=Lo.gate;fixed('gate',g,q=>gate(q,g,big));out[out.length-1][0]=g.y-110;}   // the player walks through it: in front of it at the way in
  for(const id of ['candy','cane'])fixed(id,Lo[id],q=>cart(q,Lo[id],big,id),65,110);
  for(const q of pl.crowd)out.push([q.y,()=>folk(c,q.x,q.y,s1,q.seed,{...ts,kid:q.seed%5===0,hat:q.seed%4===2?'non':''})]);
  return out;
}
/** Anh Sáu's phóng dao as a booth on the floor (portrait). */
function booth(c,s,big,ts){
  const {x,y,w}=s,hw=w/2,cy=y-118;
  L(c,x-hw+12,y,x-hw+12,cy-40,WOOD_D,5);L(c,x+hw-12,y,x+hw-12,cy-40,WOOD_D,5);R(c,x-hw+8,cy-56,w-16,22,'#5aa06a',6);sign(c,x,cy-66,'PHÓNG DAO',{size:14*big,min:80,bitmap:ts.bitmap});
  knifeBoard(c,x,cy,32);
  folk(c,x+hw-20,y-4,.86,14,{...ts,top:'#4b7a5a'});
  R(c,x-hw+6,y-30,w-12,30,WOOD,6,WOOD_D,2);
}
/** Anh Ba's chiếu trong: a dark tarp in the corner, a mat, a candle, sunglasses. */
function corner(c,s,big,ts){
  const {x,y,w}=s,hw=w/2;
  P(c,[[x-hw-8,y-4],[x+hw+12,y-4],[x+hw+12,y-150],[x-hw+18,y-118]],'#3d3f55');P(c,[[x-hw-8,y-4],[x-hw+18,y-118],[x-hw+30,y-112],[x-hw+6,y-4]],'#2e3044');
  R(c,x-hw+6,y-42,w-12,30,'#c9a65a',5,'#8a6a2a',1.5);for(let i=1;i<6;i++)L(c,x-hw+6+i*(w-12)/6,y-41,x-hw+6+i*(w-12)/6,y-13,'#a8883e',1);
  E(c,x+hw-22,y-30,14,14,'#ffcf6a33');R(c,x+hw-25,y-36,6,10,'#fff3df',2);E(c,x+hw-22,y-39,2.4,4,'#ffb43a');
  folk(c,x-6,y-30,.82*Math.min(big,1.2),31,{...ts,top:'#2f3d4a',hat:'shades'});
  const candle=q=>T(q,'🕯️',x-hw+20,y-128,14*big,'#fff',400);
  if(ts.bitmap)ts.bitmap('candle',[x-hw,y-148,40,40],candle);else candle(c);
}
/** The ô ăn quan board drawn on a mat, Bé Bi on one end and Ông Hai on the other. */
function mat(c,s,big,ts){
  const {x,y,w}=s,hw=w/2,top=y-44;
  sitter(c,x-hw+18,top+6,.95,3,'kid');sitter(c,x+hw-18,top+6,.95,8);
  E(c,x+hw-18,top-40,12,6,'#e8e4dc');   // Ông Hai's white hair
  R(c,x-hw+30,top,w-60,40,'#d9b878',8,'#8a5a26',2);
  const bx0=x-hw+56,bx1=x+hw-56,by=top+8,bh=24;R(c,bx0-16,by,bx1-bx0+32,bh,'#e9c98f',12,'#8a5a26',1.6);
  for(let i=0;i<=5;i++){const u=bx0+i*(bx1-bx0)/5;L(c,u,by,u,by+bh,'#8a5a26',1.4);}L(c,bx0,by+bh/2,bx1,by+bh/2,'#8a5a26',1.4);
  for(let i=0;i<10;i++)E(c,bx0+8+((i*37)%((bx1-bx0)-16)),by+5+(i%2)*13,2,2,'#6b7a88');
  E(c,bx0-8,by+bh/2,5,5,'#5b4636');E(c,bx1+8,by+bh/2,5,5,'#5b4636');
}
function board(c,s,big){
  const {x,y}=s;L(c,x-22,y,x-22,y-56,WOOD_D,4);L(c,x+22,y,x+22,y-56,WOOD_D,4);
  R(c,x-40*big,y-110*big,80*big,60*big,GOLD,8,'#9a6a1a',2.5);T(c,'🏆',x,y-94*big,18*big,INK,400);T(c,'BẢNG VÀNG',x,y-70*big,fit(c,'BẢNG VÀNG',72*big,12*big,900),'#6a3a0a',900);
}
/** Bà Sáu on her stool by the gate with a tin box: vay nóng. */
function lender(c,s,big){
  const {x,y}=s;R(c,x-26,y-22,52,22,WOOD,5,WOOD_D,1.5);sitter(c,x-6,y-22,.95,17);E(c,x-6,y-68,11,6,'#b9b1a8');
  R(c,x+16,y-34,24,14,'#7a8b99',3,'#4a5560',1.2);sign(c,x+4,y-100*big,'💸 VAY NÓNG',{size:12*big,bg:'#fff1d6',min:80});
}
/** Dì Hai's vé số cào: dì Hai in her nón lá with a fan of tickets, a little glass case on legs, a sign. */
const TICKET=['#e2462d','#f0b44a','#3c8fd0','#5aa06a','#c86bb0'];
function tickets(c,s,big,ts){
  const {x,y}=s;
  folk(c,x-48,y-2,.84*Math.min(big,1.15),26,{...ts,top:'#7fb07a',hat:'non'});
  for(let i=0;i<3;i++){c.save();c.translate(x-34,y-60);c.rotate(-.3+i*.32);R(c,-3,-16,7,14,TICKET[i+1],1.5);c.restore();}   // a fan of tickets in her hand
  L(c,x-30,y,x-30,y-34,WOOD_D,3);L(c,x+30,y,x+30,y-34,WOOD_D,3);
  R(c,x-38,y-62,76,34,WOOD,5,WOOD_D,2);R(c,x-34,y-58,68,26,'#d8eef5',3,'#7a9aa8',1.2);
  for(let r=0;r<2;r++)for(let i=0;i<5;i++){const tx=x-30+i*12.5,ty=y-55+r*12;R(c,tx,ty,10,9,TICKET[(i+r*2)%5],1.5);R(c,tx+2,ty+3,6,3,'#dfe3e8',1);}
  E(c,x-20,y-56,10,2,'#ffffff66');
  L(c,x-26,y-62,x-26,y-80,WOOD_D,2.4);L(c,x+26,y-62,x+26,y-80,WOOD_D,2.4);
  sign(c,x,y-86,'VÉ SỐ CÀO',{size:12*big,bg:'#fff1d6',edge:RED_D,ink:RED_D,min:84,bitmap:ts.bitmap});
}
/** The 📸 photobooth: a little purple kiosk, a marquee of bulbs round its sign, a camera on top, a red velvet curtain
 * drawn half open over the stool inside, a strip of sample photos pinned on its side. */
function photobooth(c,s,k,ts){
  const {x,y,w}=s,hw=w/2,h=150*k,top=y-h,on=i=>ts.reduced||Math.floor((ts.t||0)*3+i)%3!==0;
  E(c,x,y,hw+8,7,'#2a1c1630');
  R(c,x-hw,top,w,h,'#6b3f8f',8,'#4a2a66',2);                        // the cabin
  R(c,x-hw+5,top+34*k,w-10,h-40*k,'#2e2140',4);                     // inside
  R(c,x-hw+14,y-30*k,w*.36,8*k,'#c08a52',3);L(c,x-hw+18,y-22*k,x-hw+18,y-6,'#7a5230',2.4);L(c,x-hw+10+w*.36,y-22*k,x-hw+10+w*.36,y-6,'#7a5230',2.4);   // the stool
  const cx0=x-hw+5+w*.42,cx1=x+hw-5;                               // the curtain over the right part, pleated
  P(c,[[cx0,top+34*k],[cx1,top+34*k],[cx1,y-6],[cx0+8,y-6],[cx0-6,top+34*k+h*.45]],'#c8323a');
  for(let i=1;i<5;i++){const u=cx0+i*(cx1-cx0)/5;L(c,u,top+36*k,u+(i%2?2:-2),y-8,'#9e2530',2);}
  R(c,x-hw+3,top+30*k,w-6,7*k,'#e6b34a',3);                         // the rail
  R(c,x-hw+2,y-8,w-4,8,'#4a2a66',3);
  // the sign and its marquee
  const sy=top-4*k,sh=30*k;R(c,x-hw-6,sy-sh,w+12,sh,'#fff4df',8,'#e6b34a',2.5);
  const label=q=>T(q,'CHỤP ẢNH',x,sy-sh/2+1,fit(q,'CHỤP ẢNH',w-6,13*k,900),'#6b3f8f',900);
  if(ts.bitmap)ts.bitmap('photo-label',[x-hw,sy-sh,w,sh],label);else label(c);
  const n=8;for(let i=0;i<n;i++){const bx=x-hw-2+i*(w+4)/(n-1);E(c,bx,sy-sh-1,2.6*k,2.6*k,on(i)?'#ffe28a':'#b98f4a');E(c,bx,sy+1,2.6*k,2.6*k,on(i+1)?'#ffe28a':'#b98f4a');}
  // the camera on the roof, its flash
  R(c,x-14*k,sy-sh-20*k,28*k,16*k,'#3b3b46',4);E(c,x,sy-sh-12*k,5.5*k,5.5*k,'#9fc3e8');E(c,x,sy-sh-12*k,2.5*k,2.5*k,'#2a3a5a');R(c,x+7*k,sy-sh-24*k,7*k,5*k,'#dfe4ea',1.5);
  // a strip of sample photos pinned to the side
  const px=x-hw+8,py=top+42*k;R(c,px,py,13*k,44*k,'#fffaf0',2,'#d8c7a8',1);
  for(let i=0;i<3;i++){R(c,px+2*k,py+2*k+i*14*k,9*k,12*k,['#f6b6cf','#9fc3e8','#ffe28a'][i],1.5);E(c,px+6.5*k,py+9*k+i*14*k,2.2*k,2.2*k,'#6b4a3a');}
  E(c,px+6.5*k,py-1,2*k,2*k,'#e2462d');
}
function gate(c,g,big){
  const {x,y,w}=g,hw=w/2,top=y-200*Math.min(big,1.1);
  for(const px of [x-hw,x+hw]){R(c,px-8,top,16,y-top,RED,4,RED_D,2);R(c,px-12,y-12,24,12,'#7a3a2a',3);}
  R(c,x-hw-22,top-6,w+44,16,RED_D,6);R(c,x-hw-6,top+12,w+12,30*big,GOLD,8,RED_D,2);
  T(c,'CHỢ ĐEN',x,top+27*big,fit(c,'CHỢ ĐEN',w,17*big,900),RED_D,900);
  for(let i=0;i<3;i++){const lx=x-hw+18+i*(w-36)/2;L(c,lx,top+42*big,lx,top+56*big,'#5a3a2a',1.4);E(c,lx,top+66*big,9*big,11*big,i===1?GOLD:RED);}
}
function cart(c,s,big,kind){
  const {x,y}=s;
  if(kind==='candy'){for(let i=0;i<5;i++){const cx=x-28+i*14,cy=y-62-(i%2)*10;L(c,cx,cy+12,cx,y-36,'#c9b49a',1.6);E(c,cx,cy,10,9,['#f6b6cf','#fbd0e0','#f6b6cf','#c9e6f6','#fbd0e0'][i]);}}
  else{for(let i=0;i<6;i++)L(c,x+14+i*3,y-30,x+10+i*4,y-92,'#7ab36a',3.4);E(c,x-16,y-50,13,13,'#9aa3ad');E(c,x-16,y-50,4,4,'#5b6370');}
  const word=kind==='candy'?'KẸO BÔNG':'NƯỚC MÍA';R(c,x-42,y-40,84,30,kind==='candy'?'#f5d7e3':'#d9ecc6',6,'#8a6a48',1.6);
  T(c,word,x,y-25,fit(c,word,76,14*big,800),INK,800);
  E(c,x-22,y-6,7,7,'#5a4636');E(c,x+22,y-6,7,7,'#5a4636');E(c,x-22,y-6,2.4,2.4,'#c9b49a');E(c,x+22,y-6,2.4,2.4,'#c9b49a');
}
/** Badges over the stalls (dim while one cannot be played), a dot over a game in progress. */
export function marks(c,pl,o={},near=null){
  const big=pl.port?1.35:1;
  for(const s of pl.spots){
    if(s.kind!=='stall'||near===s.id)continue;
    const [x,y]=s.mark||[s.hit[0],s.hit[1]-30],bob=o.reduced?0:Math.sin((o.t||0)*2+x)*3,st=STALLS[s.id],yy=y+bob;
    const live=!!o.live?.[s.id],paint=q=>{
      E(q,0,0,17*big,17*big,'#fffaf0');q.strokeStyle=GOLD;q.lineWidth=2;q.beginPath();q.arc(0,0,17*big,0,Math.PI*2);q.stroke();
      T(q,st.icon,0,1,16*big,INK,400);
      if(live){E(q,13*big,-13*big,6*big,6*big,'#e2462d');E(q,13*big,-13*big,2.4*big,2.4*big,'#fff');}
    };
    c.save();c.translate(x,yy);
    if(o.bitmap){const r=21*big;o.bitmap('mark:'+s.id+':'+live,[-r,-r,2*r,2*r],paint);}else paint(c);
    c.restore();
  }
}
export {T,fit,R,E,L};
