/** 🏝️ Đảo riêng: the map of each private island (game/island_content.py `look`), shared by both interfaces: the old
 * one's 2D walk (v4/island-walk.js) and the new one's isometric scene (client/isometric/private-island.ts). Positions
 * are fractions of the island's square map (x to the east, y to the south, 0..1), the same numbers the live room
 * sends (live/island.py isl_mv). Pure data and geometry: no DOM, no canvas.
 *   shore   the coast (walkable inside), sand  how wide the beach is, palms, villa {x,y,w,h,floors}, dock {x,y,w,h}
 *   (walkable, a boat arrives at its far end), pad {x,y,kind: heli|strip} (a helicopter / a plane arrives there),
 *   spots [{id, emoji, name, x, y, pose}] (walk up to one: a line, a pose, the others see it), deco (the island's own
 *   art: reef, rocks, steam, lighthouse, pool…), blocks (not walkable: the villa, a mountain). */

const TAU=Math.PI*2;
/** An organic coast: an ellipse whose radius wobbles by `bumps` (one value per control point), smoothed. */
function blob(cx,cy,rx,ry,bumps,steps=48){
  const n=bumps.length,out=[];
  for(let i=0;i<steps;i++){
    const a=i/steps*TAU,f=a/TAU*n,k=Math.floor(f),t=f-k,b0=bumps[k%n],b1=bumps[(k+1)%n],w=b0+(b1-b0)*(1-Math.cos(t*Math.PI))/2;
    out.push([+(cx+Math.cos(a)*rx*w).toFixed(4),+(cy+Math.sin(a)*ry*w).toFixed(4)]);
  }
  return out;
}

export const EMOTES=[['wave','👋','Vẫy tay'],['heart','❤️','Thả tim'],['laugh','😂','Cười lớn'],['wow','😮','Ồ'],['dance','💃','Nhảy'],['cheers','🥂','Cụng ly']];

const SPOTS={
  vong:{emoji:'🛏️',name:'Võng giữa hai cây dừa',pose:'lie',lines:['Đung đưa trên võng, gió biển thổi mát rượi.','Nằm võng nghe sóng vỗ, suýt ngủ quên.']},
  lua:{emoji:'🔥',name:'Lửa trại',pose:'sit',lines:['Ngồi quanh lửa trại, nướng mấy con mực khô.','Lửa tí tách, ai cũng kể một chuyện cũ.']},
  bar:{emoji:'🍹',name:'Quầy bar bãi biển',pose:'stand',lines:['Gọi ly nước dừa ướp lạnh, cắm thêm cây dù nhỏ.','Bartender lắc một ly mocktail chanh dây.']},
  lan:{emoji:'🤿',name:'Chỗ lặn biển',pose:'swim',lines:['Lặn xuống thấy đàn cá sọc vàng bơi ngang.','Nước trong veo, nhìn rõ cả sao biển dưới đáy.']},
  nha_san:{emoji:'🛖',name:'Nhà sàn trên biển',pose:'sit',lines:['Ngồi thả chân xuống làn nước xanh dưới sàn gỗ.','Nhìn qua sàn kính thấy cá bơi ngay dưới chân.']},
  san_ho:{emoji:'🪸',name:'Rạn san hô',pose:'swim',lines:['San hô đủ màu, một chú cá hề thò đầu ra chào.','Bơi chậm qua rạn san hô, không chạm vào đâu nhé.']},
  suoi:{emoji:'♨️',name:'Suối nước nóng',pose:'swim',lines:['Ngâm mình trong suối nóng, mây trôi ngang vai.','Hơi nước bốc lên, mệt mỏi tan hết.']},
  dai:{emoji:'🔭',name:'Đài ngắm sao',pose:'stand',lines:['Chỉnh ống nhòm, thấy cả vành đai sao mờ.','Trên đỉnh đồi, mây trôi ngay dưới chân.']},
  hai_dang:{emoji:'🗼',name:'Hải đăng',pose:'stand',lines:['Leo lên ngọn hải đăng, cả vịnh trải dài trước mặt.','Ánh đèn quét một vòng qua mặt biển.']},
  ho_boi:{emoji:'🏊',name:'Hồ bơi tràn bờ',pose:'swim',lines:['Bơi ra mép hồ, biển và trời liền một màu.','Tựa mép hồ ngắm mặt trời lặn đỏ rực.']},
};
const spot=(id,x,y)=>({id,x,y,...SPOTS[id]});

export const LOOKS={
  dua:{name:'Đảo Dừa',sea:'#58b4c8',deep:'#2f8aa6',sand:'#f2dfae',grass:'#8cc56f',grassDark:'#6fae58',
    shore:blob(.5,.5,.38,.36,[1,.96,1.04,.98,1.02,.93,1,1.05]),sandWidth:.07,
    palms:[[.24,.38],[.3,.3],[.2,.55],[.31,.64],[.72,.3],[.78,.42],[.62,.24],[.4,.78],[.66,.8]],
    villa:{x:.5,y:.36,w:.17,h:.11,floors:1,roof:'#b7663f',wall:'#f4e6cc'},
    dock:{x:.47,y:.82,w:.06,h:.16},pad:{x:.76,y:.58,kind:'heli'},
    spots:[spot('vong',.25,.47),spot('lua',.42,.7),spot('bar',.62,.68),spot('lan',.15,.42)],deco:[]},
  san_ho:{name:'Đảo San Hô',sea:'#4fc3c9',deep:'#2c95ad',sand:'#f7ead0',grass:'#9fd07a',grassDark:'#7cb860',
    shore:blob(.48,.55,.4,.27,[1,1.05,.92,1,1.06,.95,1.02,.97]),sandWidth:.085,
    palms:[[.2,.5],[.27,.44],[.66,.42],[.74,.5],[.36,.7],[.58,.72],[.8,.62]],
    villa:{x:.47,y:.48,w:.14,h:.09,floors:1,roof:'#4f9bb5',wall:'#fbf3e4'},
    dock:{x:.24,y:.2,w:.05,h:.26},pad:{x:.72,y:.62,kind:'heli'},
    spots:[spot('nha_san',.3,.12),spot('san_ho',.86,.32),spot('vong',.6,.55),spot('bar',.38,.62),spot('lua',.2,.62)],
    deco:[{t:'reef',x:.86,y:.28,r:.07},{t:'reef',x:.12,y:.84,r:.05},{t:'reef',x:.7,y:.9,r:.04},{t:'hut',x:.33,y:.09},{t:'hut',x:.4,y:.13}],
    walk:[{x:.33,y:.12,w:.14,h:.04}]},
  may_da:{name:'Đảo Mây Đá',sea:'#5a9fb6',deep:'#336f8c',sand:'#cbb994',grass:'#7fa86a',grassDark:'#5f8a54',rock:'#5d5560',
    shore:blob(.5,.5,.39,.37,[1,.9,1.06,.96,1.04,.9,1.02,1.08,.94]),sandWidth:.05,
    palms:[[.24,.62],[.3,.72],[.7,.72],[.78,.6],[.2,.45]],
    villa:{x:.33,y:.38,w:.13,h:.09,floors:2,roof:'#4b4650',wall:'#e6ddd2'},
    dock:{x:.6,y:.84,w:.05,h:.14},pad:{x:.72,y:.42,kind:'heli'},
    spots:[spot('dai',.56,.24),spot('suoi',.4,.58),spot('lua',.52,.7),spot('lan',.87,.62)],
    deco:[{t:'peak',x:.56,y:.3,r:.13},{t:'steam',x:.4,y:.55},{t:'steam',x:.6,y:.18},{t:'rocks',x:.18,y:.3},{t:'rocks',x:.82,y:.8}],
    blocks:[{x:.5,y:.3,w:.14,h:.08}]},
  hoang_hon:{name:'Đảo Hoàng Hôn',sea:'#e59a6a',deep:'#b4627a',sand:'#f6d6a6',grass:'#9bbf6a',grassDark:'#7da356',
    shore:blob(.5,.52,.43,.4,[1,1.03,.97,1.05,1,.95,1.04,.98]),sandWidth:.06,
    palms:[[.18,.5],[.22,.62],[.8,.56],[.76,.68],[.35,.85],[.66,.86],[.14,.38]],
    villa:{x:.48,y:.44,w:.2,h:.12,floors:3,roof:'#8a4d3a',wall:'#fff4e2'},
    dock:{x:.6,y:.88,w:.06,h:.11},pad:{x:.5,y:.2,kind:'strip'},
    spots:[spot('hai_dang',.86,.36),spot('ho_boi',.5,.6),spot('bar',.3,.7),spot('vong',.72,.74),spot('lua',.42,.82)],
    deco:[{t:'strip',x:.5,y:.2,w:.56,h:.06},{t:'lighthouse',x:.86,y:.32},{t:'pool',x:.5,y:.6,w:.16,h:.06}]},
};
export const LOOK_IDS=Object.keys(LOOKS);
export const layout=look=>LOOKS[look]||LOOKS.dua;

export function inPoly(pts,x,y){
  let inside=false;
  for(let i=0,j=pts.length-1;i<pts.length;j=i++){const [ax,ay]=pts[i],[bx,by]=pts[j];if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;}
  return inside;
}
const inRect=(r,x,y)=>x>=r.x-r.w/2&&x<=r.x+r.w/2&&y>=r.y-r.h/2&&y<=r.y+r.h/2;
/** The villa's footprint, a mountain: not walkable. */
export function blocks(L){
  const v=L.villa;return [{x:v.x,y:v.y,w:v.w*.9,h:v.h*.8},...(L.blocks||[])];
}
/** Can a player stand here? Inside the coast (a hair in from the water), on the dock or a pier, never in a block. */
export function walkable(L,x,y){
  if(!(x>=0&&x<=1&&y>=0&&y<=1))return false;
  if(blocks(L).some(b=>inRect(b,x,y)))return false;
  if(inRect(L.dock,x,y)||(L.walk||[]).some(r=>inRect(r,x,y)))return true;
  return inPoly(L.shore,x,y);
}
/** The far end of the dock (a boat), the pad (a helicopter, a plane), the dock for the island's own boat. */
export function arrival(L,kind){
  if(kind==='heli'||kind==='plane')return [L.pad.x,L.pad.y+(L.pad.kind==='strip'?.05:.02)];
  const d=L.dock;const north=d.y<.5;return [d.x,north?d.y-d.h/2+.02:d.y+d.h/2-.02];
}
/** One step of walking from (x,y) toward (tx,ty), at most `len`: slides along a wall rather than stopping dead. */
export function step(L,x,y,tx,ty,len){
  const dx=tx-x,dy=ty-y,d=Math.hypot(dx,dy);if(d<1e-6)return [x,y,true];
  const k=Math.min(1,len/d),nx=x+dx*k,ny=y+dy*k;
  if(walkable(L,nx,ny))return [nx,ny,k>=1];
  if(walkable(L,nx,y))return [nx,y,false];
  if(walkable(L,x,ny))return [x,ny,false];
  return [x,y,true];
}
/** The walkable point nearest (x,y) along the way back toward the island's middle. */
export function nearestWalkable(L,x,y){
  if(walkable(L,x,y))return [x,y];
  const c=centre(L);
  for(let i=1;i<=40;i++){const t=i/40,px=x+(c[0]-x)*t,py=y+(c[1]-y)*t;if(walkable(L,px,py))return [px,py];}
  return c;
}
export function centre(L){
  const v=L.villa;for(const [px,py] of [[v.x,v.y+v.h*.8],[.5,.62],[.5,.5]])if(walkable(L,px,py))return [px,py];
  return arrival(L,'boat');
}
/** The spot within `r` of (x,y), nearest first. */
export function spotNear(L,x,y,r=.06){
  let best=null,bd=r;for(const s of L.spots){const d=Math.hypot(s.x-x,s.y-y);if(d<=bd){best=s;bd=d;}}return best;
}
/** Where to stand to use a spot: the spot itself, or the nearest walkable point toward the middle (a dive spot at sea). */
export const standAt=(L,s)=>nearestWalkable(L,s.x,s.y);
export const spotById=(L,id)=>L.spots.find(s=>s.id===id)||null;
export const spotLine=(s,n=0)=>s.lines[Math.abs(n|0)%s.lines.length];
