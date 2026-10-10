import {FACADE_SIGNS} from './building-art';
import {isCareerArtKey} from './career-art';

type Structure='awning'|'scallop'|'banner'|'pergola'|'porch'|'workshop'|'civic';
type Prop='produce'|'flowers'|'parcels'|'books'|'trolley'|'stools'|'planter'|'toolbox'|'bins'|'luggage'|'barrels'|'lifering';
export interface CareerFacadeStyle {motif:string;structure:Structure;prop:Prop;main:string;light:string}
const style=(motif:string,structure:Structure,prop:Prop,main:string,light:string):CareerFacadeStyle=>({motif,structure,prop,main,light});

/** Legacy loading-fallback ornaments only. Finished career paintings include
 * their own architecture and equipment and must never receive these overlays. */
export const CAREER_FACADES:Readonly<Record<string,CareerFacadeStyle>>={
  grocery:style('basket','awning','produce','#85986a','#ece4b9'),
  mother_baby:style('bottle','scallop','trolley','#c68b9f','#f4dfc9'),
  pharmacy:style('capsule','civic','planter','#6b9b90','#e7edce'),
  accounting:style('ledger','banner','books','#9883ac','#eddec5'),
  customer_care:style('headset','banner','planter','#6e9fae','#dfead7'),
  restaurant:style('noodles','awning','stools','#b96754','#f1cfa0'),
  cafe_bakery:style('bread','scallop','flowers','#b88857','#f2dbac'),
  farm:style('sprout','pergola','produce','#829558','#e7dbb3'),
  pet_care:style('paw','scallop','trolley','#79a399','#e7e1bc'),
  florist:style('flower','pergola','flowers','#b67e91','#e5d6b6'),
  salon:style('scissors','scallop','planter','#8e9b9d','#edd7c4'),
  repair:style('wrench','workshop','toolbox','#8b968c','#dfcaa1'),
  homestay:style('bed','porch','luggage','#9c8ca8','#e7dabc'),
  teacher:style('chalkboard','civic','planter','#769886','#f1d399'),
  tour_guide:style('compass','pergola','luggage','#8ea36b','#efdcb2'),
  milk_tea:style('boba','scallop','stools','#c69a9e','#f5e0b9'),
  delivery:style('parcel','workshop','parcels','#c58c4f','#f2d9a6'),
  corp_accounting:style('calculator','banner','planter','#739285','#e6d9b5'),
  tax_payroll:style('payroll','banner','books','#b18d63','#f0ddbe'),
  group_accounting:style('group','civic','planter','#7896ad','#e2ddbd'),
  clothing:style('shirt','scallop','flowers','#bd8f93','#efd8c2'),
  pet_shop:style('fish','awning','produce','#7aa1aa','#e8dbb0'),
  tra_da:style('teapot','pergola','stools','#7f9a77','#eedfbd'),
  fruit:style('fruit','awning','produce','#c0a157','#f1dfa2'),
  garbage:style('recycle','workshop','bins','#779579','#dde1ae'),
  drain:style('pipe','workshop','toolbox','#719fa4','#e4dfb4'),
  homemaker:style('house','porch','planter','#bb917b','#f0ddbd'),
  ice_cream:style('icecream','scallop','stools','#ba91a9','#f3dfc4'),
  nail:style('polish','scallop','flowers','#c48d96','#f2d8ca'),
  pagoda:style('lotus','civic','flowers','#b78954','#f2dfb0'),
  pho:style('bowl','awning','stools','#9e7955','#f0dbb2'),
  com:style('rice','awning','produce','#b98953','#f3dcb0'),
  photobooth:style('camera','scallop','flowers','#9e8dab','#eddbcd'),
  giupviec:style('bucket','porch','trolley','#77a7a7','#deebd2'),
  naucom:style('pot','porch','produce','#ac8769','#f0d9b4'),
  babysitter:style('teddy','porch','trolley','#c8a167','#f3e1b4'),
  library:style('books','civic','books','#8c9878','#eae0c1'),
  pilot:style('plane','civic','luggage','#799aa8','#e1e8d3'),
  flight_attendant:style('suitcase','banner','luggage','#b58b9d','#eadac9'),
  oil:style('derrick','workshop','barrels','#bc9664','#ead7ac'),
  hr_admin:style('badge','banner','flowers','#9da174','#e8dfc1'),
  secretary:style('calendar','porch','planter','#ac879b','#efe0ce'),
  it_helpdesk:style('laptop','workshop','toolbox','#729895','#d9e5cf'),
  railway:style('signal','workshop','toolbox','#b59266','#ebd8b2'),
  nurse:style('heart','civic','trolley','#9baaae','#e8e8d0'),
  lighthouse:style('beacon','civic','barrels','#b59168','#f2deb0'),
  rescue:style('radio','civic','toolbox','#ba8669','#e6dbb7'),
  lifeguard:style('lifering','pergola','lifering','#81a9ad','#f0dab5'),
  police:style('shield','civic','planter','#7e9588','#e7dcb4'),
  zpop:style('record','scallop','books','#a592b6','#f0d4c6'),
};

type ArtSource=(HTMLImageElement|HTMLCanvasElement);
const REVISION='v1';
/** Bounds GPU uploads even when an older painted source is 768px wide. */
export function careerFacadeSize(source:{width:number;height:number}):{width:number;height:number}{
  const scale=Math.min(1,384/Math.max(1,source.width),512/Math.max(1,source.height));
  return {width:Math.max(1,Math.round(source.width*scale)),height:Math.max(1,Math.round(source.height*scale))};
}
/** A source family is part of the key so a loading fallback cannot poison the
 * final career texture. Callers should still wait for their art-<family> asset. */
export function careerFacadeTextureKey(career:string,baseKind:string):string|null{
  if(isCareerArtKey(baseKind))return null;
  return Object.prototype.hasOwnProperty.call(CAREER_FACADES,career)&&Object.prototype.hasOwnProperty.call(FACADE_SIGNS,baseKind)
    ?`career-facade-${REVISION}-${career}-${baseKind}`:null;
}

/** Optional CPU canvas cache for previews / non-Phaser consumers. Phaser can use
 * drawCareerFacade inside its own texture cache to avoid keeping a second copy.
 * Source identity invalidates replacement images; weak ownership lets old art go.
 * Only the finite authored career/family pairs can enter this cache. */
export class CareerFacadeCache {
  private sources=new WeakMap<ArtSource,Map<string,HTMLCanvasElement>>();
  constructor(private createCanvas:()=>HTMLCanvasElement=()=>document.createElement('canvas')){}
  get(career:string,baseKind:string,source:ArtSource):HTMLCanvasElement|null{
    const key=careerFacadeTextureKey(career,baseKind);if(!key||!source.width||!source.height)return null;
    let entries=this.sources.get(source);if(!entries){entries=new Map();this.sources.set(source,entries);}
    const cached=entries.get(key);if(cached)return cached;
    const canvas=this.createCanvas(),size=careerFacadeSize(source);canvas.width=size.width;canvas.height=size.height;
    const ctx=canvas.getContext('2d');if(!ctx)return null;
    drawCareerFacade(ctx,source,career,baseKind);entries.set(key,canvas);return canvas;
  }
}

/** Coordinate contract: same aspect and ground origin (.5, 1) as the source;
 * careerFacadeSize caps the upload. FACADE_SIGNS[baseKind] stays valid; no sign text or gameplay geometry is
 * changed. The base stays intact. Trade ornaments occupy the right side, below
 * the roof; trim is below the original name board; equipment stays at its feet.
 * Run on texture creation only, never from update(), camera or movement code. */
export function drawCareerFacade(c:CanvasRenderingContext2D,source:ArtSource,career:string,baseKind:string):void{
  const w=c.canvas.width,h=c.canvas.height;c.drawImage(source,0,0,w,h);
  if(!careerFacadeTextureKey(career,baseKind))return;
  const s=CAREER_FACADES[career],sign=FACADE_SIGNS[baseKind];
  c.save();c.imageSmoothingEnabled=true;c.lineJoin='round';c.lineCap='round';
  // Authored vector glazing on clear roof planes preserves the painted tile
  // light/shadow. It avoids image readback and never touches sign boards/vines.
  const roof:Record<string,number[][]>={
    office:[[.365,.034],[.65,.119],[.53,.239],[.153,.143]],
    home:[[.337,.067],[.598,.172],[.475,.335],[.184,.218]],
    cafe:[[.409,.078],[.701,.194],[.659,.248],[.328,.123]],
    garage:[[.353,.057],[.709,.201],[.652,.266],[.285,.134]],
    market:[[.363,.055],[.705,.175],[.653,.24],[.29,.125]],
  };
  if(roof[baseKind]){c.save();c.globalCompositeOperation='color';c.globalAlpha=.68;c.beginPath();roof[baseKind].forEach(([x,y],i)=>i?c.lineTo(x*w,y*h):c.moveTo(x*w,y*h));c.closePath();c.fillStyle=s.main;c.fill();c.restore();}
  drawStructure(c,s,sign,w,h);
  // Family placement respects painted name boards and distinct roof profiles.
  const mount:Record<string,[number,number]>={office:[.77,.345],home:[.77,.49],airport:[.80,.66],lighthouse:[.78,.74],pagoda:[.79,.66],school:[.79,.56]};
  const [mx,my]=mount[baseKind]||[.79,.56];
  c.save();c.translate(w*mx,h*my);c.scale(w*.265/100,w*.265/100);
  const p=paint(c,s);p.line([[-26,-36],[-41,-39],[-41,32]],'#806b53',5);p.line([[-39,-37],[-29,-25]],'#b3986f',3);
  drawMotif(c,s);c.restore();
  c.save();c.translate(w*.735,h*.88);c.scale(w*.24/100,w*.24/100);drawEquipment(c,s);c.restore();
  // Outdoor occupations need unmistakable working equipment as well as a sign.
  if(['lifeguard','railway','oil','delivery','farm'].includes(career)){
    c.save();c.translate(w*.52,h*.835);c.scale(w*.55/100,w*.55/100);drawOutdoorWork(c,s,career);c.restore();
  }
  c.restore();
}

function paint(c:CanvasRenderingContext2D,s:CareerFacadeStyle){
  const ink='#75634e',cream='#fbefd2';
  const gradient=(a:string,b:string)=>{const g=c.createLinearGradient(-30,-42,36,45);g.addColorStop(0,a);g.addColorStop(1,b);return g;};
  const finish=(fill:string|CanvasGradient,stroke:string|undefined=ink,width=2.5)=>{c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=width;c.stroke();}};
  const round=(x:number,y:number,w:number,h:number,r:number,fill:string|CanvasGradient,stroke:string|undefined=ink)=>{c.beginPath();c.roundRect(x,y,w,h,r);finish(fill,stroke);};
  const ellipse=(x:number,y:number,rx:number,ry:number,fill:string|CanvasGradient,stroke:string|undefined=ink)=>{c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);finish(fill,stroke);};
  const poly=(points:number[][],fill:string|CanvasGradient,stroke:string|undefined=ink)=>{c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();finish(fill,stroke);};
  const line=(points:number[][],color=ink,width=3)=>{c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.strokeStyle=color;c.lineWidth=width;c.stroke();};
  const arc=(x:number,y:number,r:number,start:number,end:number,color=ink,width=4)=>{c.beginPath();c.arc(x,y,r,start,end);c.strokeStyle=color;c.lineWidth=width;c.stroke();};
  const star=(x:number,y:number,r:number,color:string)=>poly(Array.from({length:10},(_,i)=>{const a=-Math.PI/2+i*Math.PI/5,v=i%2?r*.45:r;return [x+Math.cos(a)*v,y+Math.sin(a)*v];}),color);
  const heart=(x:number,y:number,size:number,color:string|CanvasGradient)=>{c.beginPath();c.moveTo(x,y+size*.65);c.bezierCurveTo(x-size*1.2,y-size*.05,x-size*.7,y-size*.95,x,y-size*.35);c.bezierCurveTo(x+size*.7,y-size*.95,x+size*1.2,y-size*.05,x,y+size*.65);finish(color);};
  return {ink,cream,gradient,finish,round,ellipse,poly,line,arc,star,heart,body:gradient(s.light,s.main)};
}

function drawStructure(c:CanvasRenderingContext2D,s:CareerFacadeStyle,sign:{x:number;y:number;width:number;height:number;angle:number},w:number,h:number){
  const {round,poly,line,ellipse}=paint(c,s),span=w*sign.width*.99;
  c.save();c.translate(w*sign.x,h*(sign.y+sign.height*.95));c.rotate(sign.angle);
  // A low eave adds a real architectural band without obscuring the name board.
  if(s.structure==='awning'||s.structure==='scallop'){
    const drop=Math.min(24,h*.052),count=s.structure==='scallop'?5:6;
    poly([[-span/2,-4],[span/2,-4],[span/2+9,drop],[-span/2-9,drop]],s.main);
    for(let i=0;i<count;i++){
      const x=-span/2+i*span/count,dx=span/count;
      if(i%2===0)poly([[x,-3],[x+dx,-3],[x+dx+(i/count)*8,drop],[x-(1-i/count)*8,drop]],s.light,undefined);
      if(s.structure==='scallop')round(x-2,drop-3,dx+3,10,6,i%2?s.main:s.light);
    }
    line([[-span/2-8,drop],[span/2+8,drop]],'#8d7756',2);
  }else if(s.structure==='pergola'){
    round(-span/2,-3,span,9,3,'#ac926a');
    for(let i=0;i<7;i++){const x=-span/2+7+i*(span-14)/6;line([[x,-9],[x+3,15]],'#b79e75',5);ellipse(x,4,7,3,s.main,undefined);}
  }else if(s.structure==='porch'){
    round(-span/2,-3,span,8,3,s.main);
    for(const side of [-1,1])poly([[side*span/2,3],[side*(span/2-20),3],[side*(span/2-8),35],[side*span/2,37]],s.light);
    line([[-span/2+5,24],[-span/2+12,23]],s.main,4);line([[span/2-12,23],[span/2-5,24]],s.main,4);
  }else if(s.structure==='banner'){
    round(-span/2,-3,span,6,2,s.main);
    for(const side of [-1,1])poly([[side*(span/2-4),0],[side*(span/2-21),0],[side*(span/2-21),29],[side*(span/2-12),24],[side*(span/2-4),29]],s.main);
  }else if(s.structure==='workshop'){
    poly([[-span/2,-2],[span/2,-2],[span/2+7,14],[-span/2-7,14]],s.main);
    for(let i=0;i<7;i++){const x=-span/2+4+i*(span-8)/6;line([[x,0],[x+2,10]],s.light,2);}
    round(-span/2-6,14,span+12,5,2,'#a68c69');
  }else{
    round(-span/2,-2,span,7,3,s.main);
    round(-span/2-4,4,12,15,3,s.light);round(span/2-8,4,12,15,3,s.light);
    line([[-span/2+10,4],[span/2-10,4]],s.light,2);
  }
  c.restore();
}

/** Painted cut-out shop signs: large simple masses with soft highlights. All
 * paths are vector game rendering; the raster base is never pixel-edited. */
function drawMotif(c:CanvasRenderingContext2D,s:CareerFacadeStyle){
  const {round,ellipse,poly,line,arc,star,heart,gradient,finish,body,cream,ink}=paint(c,s);
  switch(s.motif){
    case 'basket':
      arc(0,-7,25,Math.PI,0,'#93764f',6);poly([[-39,-8],[39,-8],[29,34],[-29,34]],gradient('#e8c58d','#b99361'));
      for(const x of [-21,-7,7,21])line([[x,-3],[x*.78,28]],'#eed7a9',4);line([[-31,9],[31,9]],'#a78255',3);
      ellipse(-19,-17,12,13,'#c79a61');ellipse(2,-21,13,14,'#9aad72');ellipse(23,-16,10,11,'#c87965');break;
    case 'bottle':
      round(-23,-19,46,55,13,body);round(-18,-32,36,17,5,s.main);round(-9,-42,18,13,7,'#e5c39b');
      round(-17,2,34,17,7,cream);heart(0,11,10,s.main);line([[-12,-7],[-12,-1]],cream,4);break;
    case 'capsule':
      c.save();c.rotate(-.47);round(-19,-40,38,80,18,cream);c.beginPath();c.roundRect(-19,-40,38,41,[18,18,0,0]);finish(body);line([[-10,-26],[-10,-10]],'#f8f1d7',4);c.restore();break;
    case 'ledger':
      poly([[-38,-30],[-5,-35],[0,-28],[5,-35],[38,-30],[38,32],[5,26],[0,31],[-5,26],[-38,32]],body);
      poly([[-32,-24],[-6,-27],[-4,20],[-32,25]],cream);poly([[5,-27],[32,-24],[32,25],[5,20]],'#f0ddb7');
      for(let y=-14;y<=13;y+=12){line([[-26,y],[-12,y-2]],s.main,2);line([[12,y-2],[26,y]],ink,2);}line([[0,-25],[0,25]],ink,3);break;
    case 'headset':
      arc(0,0,33,Math.PI,Math.PI*2,s.main,13);arc(0,0,25,Math.PI,Math.PI*2,cream,3);
      round(-41,-5,17,32,7,body);round(24,-5,17,32,7,body);line([[32,18],[25,35],[6,35]],ink,6);round(-4,28,18,10,5,s.light);break;
    case 'noodles':
      poly([[-40,-5],[40,-5],[29,31],[-26,31]],body);ellipse(0,-5,40,11,'#b7704e');
      for(let i=0;i<4;i++)line([[-24+i*13,-5],[-29+i*13,-15],[-20+i*13,-21]],cream,4);
      line([[2,-33],[38,-15]],'#9d7752',4);line([[8,-41],[42,-22]],'#bd9262',4);poly([[-21,-18],[-7,-29],[-4,-8]],'#9ca967');break;
    case 'bread':
      c.save();c.rotate(-.38);ellipse(0,0,43,23,gradient('#f1cd8f','#c68b4f'));for(const x of [-23,-3,17])line([[x-3,-12],[x+5,10]],'#f8e3b7',6);c.restore();break;
    case 'sprout':
      poly([[-30,9],[30,9],[21,37],[-20,37]],'#c39a69');ellipse(0,9,30,9,'#817456');line([[0,9],[0,-30]],'#749064',6);
      c.save();c.rotate(-.5);ellipse(-14,-18,20,10,body);c.restore();c.save();c.rotate(.4);ellipse(14,-31,21,11,'#a9ba7c');c.restore();break;
    case 'paw':
      ellipse(0,14,27,23,body);for(const [x,y,r] of [[-31,-10,12],[-12,-29,12],[13,-29,12],[32,-9,11]])ellipse(x,y,r,14,body);heart(0,15,11,cream);break;
    case 'flower':
      line([[0,37],[0,-3]],'#809360',6);ellipse(13,18,17,7,'#a7b474');for(let i=0;i<6;i++){const a=i*Math.PI/3;ellipse(Math.cos(a)*21,-12+Math.sin(a)*21,14,14,body);}ellipse(0,-12,13,13,'#edd28e');break;
    case 'scissors':
      line([[-12,11],[28,-36]],'#b8cac2',10);line([[12,11],[-24,-38]],'#dae0cd',10);
      ellipse(-21,24,16,15,s.main);ellipse(21,24,16,15,s.main);ellipse(-21,24,8,8,cream);ellipse(21,24,8,8,cream);ellipse(0,-2,5,5,'#b99d6e');break;
    case 'wrench':
      poly([[-8,38],[7,38],[12,-9],[28,-22],[28,-40],[13,-27],[1,-31],[-1,-44],[-16,-32],[-14,-15],[-7,-9]],gradient('#e1dbc1','#939e92'));ellipse(0,29,4,5,ink);break;
    case 'bed':
      round(-40,-2,80,34,7,body);round(-40,-25,11,67,4,s.main);round(31,6,9,36,4,s.main);round(-26,-9,23,19,6,cream);round(0,-5,32,28,6,s.light);line([[-33,31],[34,31]],ink,3);break;
    case 'chalkboard':
      line([[-26,27],[-32,43]],'#b4936b',7);line([[25,27],[32,43]],'#b4936b',7);round(-43,-36,86,67,6,'#c29e6d');round(-35,-28,70,49,3,'#6f927b');
      poly([[-26,10],[-14,-14],[-2,10]],'#e9e2b8',undefined);ellipse(17,-3,12,12,'#e2bd82');line([[-34,25],[37,25]],cream,4);break;
    case 'compass':
      ellipse(0,0,38,38,gradient('#e7d5a8','#a99063'));ellipse(0,0,29,29,cream);poly([[0,-31],[12,7],[0,0],[-12,7]],s.main);poly([[0,31],[-12,-7],[0,0],[12,-7]],'#bd8067');ellipse(0,0,5,5,'#cdb082');for(const x of [-23,23])line([[x,-2],[x,2]],ink,3);break;
    case 'boba':
      poly([[-28,-29],[28,-29],[21,38],[-20,38]],body);ellipse(0,-29,29,7,cream);line([[9,-47],[3,3]],'#b68977',6);
      for(const [x,y] of [[-10,22],[6,25],[13,13],[-2,9],[-15,11]])ellipse(x,y,4,4,'#80664d');line([[-18,-14],[-14,1]],cream,4);break;
    case 'parcel':
      poly([[-36,-20],[1,-35],[38,-17],[37,28],[0,43],[-36,22]],gradient('#dfb77d','#b58c60'));poly([[0,0],[38,-17],[37,28],[0,43]],'#bf986a');line([[-36,-20],[0,0],[38,-17]],'#f2dba9',4);poly([[-12,-30],[0,-35],[13,-29],[-23,-13],[-23,1],[-33,-4],[-33,-19]],cream);round(7,4,22,14,2,cream);break;
    case 'calculator':
      round(-29,-41,58,82,8,body);round(-21,-32,42,20,3,'#dce8cf');for(let row=0;row<3;row++)for(let col=0;col<3;col++)round(-20+col*15,-3+row*13,10,8,2,col===2?s.main:cream);line([[-14,-18],[13,-18]],'#89a098',3);break;
    case 'payroll':
      poly([[-30,-39],[18,-39],[30,-25],[30,35],[19,30],[9,35],[-1,30],[-11,35],[-21,30],[-30,35]],body);poly([[18,-39],[18,-24],[30,-25]],cream);for(const y of [-19,-7,5])line([[-19,y],[12,y]],cream,4);ellipse(21,25,17,17,'#dbc083');ellipse(21,25,10,10,'#f2dca5');line([[21,19],[21,31]],ink,3);break;
    case 'group':
      line([[0,-7],[0,10],[-29,10],[-29,23]],s.main,5);line([[0,10],[29,10],[29,23]],s.main,5);round(-15,-38,30,28,5,body);
      for(const x of [-29,0,29])round(x-12,21,24,22,5,x===0?s.main:s.light);line([[-8,-26],[8,-26]],cream,3);break;
    case 'shirt':
      poly([[-17,-33],[-40,-16],[-26,4],[-17,-3],[-18,36],[18,36],[17,-3],[26,4],[40,-16],[17,-33],[0,-24]],body);arc(0,-32,12,0,Math.PI,cream,4);line([[-9,26],[10,26]],cream,3);break;
    case 'fish':
      ellipse(-4,0,31,24,body);poly([[20,-2],[42,-22],[42,22]],s.main);poly([[-14,-22],[-2,-38],[11,-23]],s.light);ellipse(-18,-4,4,4,ink);arc(-14,3,8,0,1.7,cream,3);line([[0,-17],[0,17]],cream,3);break;
    case 'teapot':
      arc(25,2,17,-1.7,1.7,s.main,9);ellipse(-3,9,29,27,body);poly([[-28,6],[-45,-11],[-38,-19],[-19,-5]],s.light);ellipse(-3,-18,23,6,s.main);ellipse(-3,-27,7,7,s.light);line([[-13,-2],[-17,9]],cream,4);break;
    case 'fruit':
      ellipse(-18,8,23,26,'#dbad65');ellipse(21,14,24,24,'#c58a62');ellipse(7,-13,19,22,'#adc077');line([[8,-30],[11,-41]],ink,4);ellipse(22,-32,14,6,'#8ea567');line([[-23,-8],[-26,3]],cream,4);break;
    case 'recycle':
      for(let i=0;i<3;i++){c.save();c.rotate(i*Math.PI*2/3);poly([[-12,-39],[7,-39],[21,-14],[31,-21],[29,1],[8,-4],[15,-9],[1,-28],[-8,-12],[-22,-20]],body);c.restore();}break;
    case 'pipe':
      poly([[-35,-37],[-10,-37],[-10,7],[28,7],[28,31],[-23,31],[-35,18]],gradient('#cddbd1',s.main));round(-41,-39,36,12,3,s.light);round(24,2,13,34,3,s.light);
      c.beginPath();c.moveTo(38,17);c.quadraticCurveTo(55,39,40,40);c.quadraticCurveTo(28,39,38,17);finish('#a8c7c2');break;
    case 'house':
      round(-30,-4,60,41,4,body);poly([[-41,-5],[0,-39],[41,-5]],'#c39076');round(-12,9,23,28,3,cream);heart(0,-6,11,s.main);break;
    case 'icecream':
      poly([[-25,3],[25,3],[0,43]],gradient('#edcca0','#c79b64'));line([[-15,10],[8,29]],'#b99369',2);line([[15,10],[-8,29]],'#b99369',2);
      ellipse(-16,-11,18,19,'#e9c5c5');ellipse(16,-11,18,19,'#c1d0aa');ellipse(0,-28,19,19,'#f4e3bc');ellipse(2,-43,5,5,'#be857a');break;
    case 'polish':
      round(-24,-3,48,44,11,body);round(-14,-39,28,37,4,'#8f7e78');line([[-6,-31],[-6,-10]],s.light,4);round(-17,9,34,17,5,cream);star(0,18,10,s.main);break;
    case 'lotus':
      for(const a of [-.85,0,.85]){c.save();c.rotate(a);c.beginPath();c.moveTo(0,25);c.quadraticCurveTo(-32,-2,0,-39);c.quadraticCurveTo(32,-2,0,25);finish(a===0?s.light:s.main);c.restore();}ellipse(0,29,35,8,'#9eaa78');break;
    case 'bowl':
      c.beginPath();c.moveTo(-41,-2);c.quadraticCurveTo(-30,36,0,36);c.quadraticCurveTo(30,36,41,-2);c.closePath();finish(body);ellipse(0,-2,41,12,'#c99b62');
      for(const x of [-18,0,18]){c.beginPath();c.moveTo(x,-19);c.bezierCurveTo(x-10,-29,x+8,-34,x,-43);c.strokeStyle=cream;c.lineWidth=5;c.stroke();}ellipse(8,-3,14,4,'#a7b475');line([[-28,3],[27,3]],cream,3);break;
    case 'rice':
      ellipse(0,15,42,22,body);ellipse(0,10,35,17,cream);ellipse(-15,3,19,17,'#f7ebcf');round(2,-3,26,19,5,'#b77d52');for(const y of [1,7])line([[7,y],[25,y]],'#805b40',2);ellipse(18,-15,14,10,'#9cae71');ellipse(20,-14,8,5,'#e3d08e');break;
    case 'camera':
      round(-18,-34,34,14,4,s.main);round(-43,-25,86,57,9,body);ellipse(0,3,24,24,'#6f7e7b');ellipse(0,3,17,17,'#a9c6c0');ellipse(-5,-3,7,7,'#e2ebd8');round(26,-16,10,7,2,cream);break;
    case 'bucket':
      arc(-4,-1,26,Math.PI,Math.PI*2,ink,5);poly([[-33,-1],[25,-1],[18,38],[-24,38]],body);ellipse(-4,0,29,7,s.light);line([[13,9],[30,-41]],'#b99a70',6);poly([[20,-38],[33,-47],[41,-36],[29,-22]],cream);break;
    case 'pot':
      round(-33,-6,66,40,12,body);round(-44,0,14,11,4,s.main);round(30,0,14,11,4,s.main);ellipse(0,-8,34,9,cream);ellipse(0,-19,8,6,s.main);
      for(const x of [-14,12]){c.beginPath();c.moveTo(x,-30);c.quadraticCurveTo(x-10,-38,x,-44);c.strokeStyle='#efe6c9';c.lineWidth=4;c.stroke();}line([[-20,7],[-20,20]],cream,4);break;
    case 'teddy':
      ellipse(-25,-30,12,13,body);ellipse(25,-30,12,13,body);ellipse(0,19,27,27,body);ellipse(-26,25,13,14,s.light);ellipse(26,25,13,14,s.light);ellipse(0,-13,30,28,body);ellipse(0,-5,16,12,cream);ellipse(-12,-18,3,4,ink);ellipse(12,-18,3,4,ink);ellipse(0,-9,5,4,ink);heart(0,22,12,'#c58d85');break;
    case 'books':
      for(const [x,y,h,color] of [[-35,-25,63,s.main],[-12,-37,76,s.light],[12,-19,59,'#b98e73']] as const){round(x,y,21,h,3,color);line([[x+5,y+9],[x+15,y+9]],cream,3);line([[x+5,y+h-8],[x+15,y+h-8]],cream,3);}break;
    case 'plane':
      poly([[0,-45],[8,-18],[43,4],[43,15],[8,2],[8,26],[21,35],[21,42],[0,36],[-21,42],[-21,35],[-8,26],[-8,2],[-43,15],[-43,4],[-8,-18]],body);line([[0,-27],[0,26]],cream,4);break;
    case 'suitcase':
      round(-13,-42,27,15,5,s.main);round(-31,-30,62,65,8,body);for(const x of [-17,17])line([[x,-24],[x,27]],cream,4);ellipse(-19,39,5,5,ink);ellipse(19,39,5,5,ink);round(8,-10,14,18,3,'#f5e5bb');break;
    case 'derrick':
      poly([[-13,-44],[13,-44],[35,32],[-35,32]],body);line([[-9,-28],[19,-11],[-23,9],[31,28]],ink,4);line([[9,-28],[-19,-11],[23,9],[-31,28]],ink,3);round(-43,31,86,9,3,s.main);line([[-9,-44],[9,-44]],cream,4);break;
    case 'badge':
      line([[-14,-36],[-24,-46]],s.main,8);line([[14,-36],[24,-46]],s.main,8);round(-32,-35,64,78,7,body);round(-10,-40,20,9,3,cream);ellipse(0,-13,12,12,cream);c.beginPath();c.arc(0,16,20,Math.PI,Math.PI*2);finish(cream);line([[-15,30],[15,30]],cream,3);break;
    case 'calendar':
      round(-37,-34,74,74,6,body);round(-37,-34,74,18,5,s.main);for(const x of [-21,21])line([[x,-42],[x,-24]],'#d0b58d',5);
      for(const x of [-21,0,21])for(const y of [-3,13,29])round(x-5,y-4,10,8,2,cream);line([[-7,12],[0,19],[13,3]],'#7b9977',5);break;
    case 'laptop':
      round(-37,-32,74,52,5,body);round(-30,-25,60,36,2,'#718f89');line([[-18,-15],[-25,-7],[-18,1]],cream,3);line([[17,-15],[24,-7],[17,1]],cream,3);line([[4,-17],[-3,3]],s.light,3);poly([[-37,20],[37,20],[46,35],[-46,35]],s.light);line([[-9,29],[9,29]],s.main,3);break;
    case 'signal':
      line([[-15,-3],[-15,43]],ink,7);round(-33,-43,35,59,9,s.main);ellipse(-15,-27,10,10,'#c5816e');ellipse(-15,-1,10,10,'#b7c685');line([[-7,27],[42,8]],cream,9);for(const x of [5,25])line([[x,22-x*.38],[x+6,20-x*.38]],'#bb806c',7);break;
    case 'heart':
      heart(0,0,43,body);line([[-31,-2],[-16,-2],[-9,-15],[1,17],[10,-6],[18,-2],[32,-2]],cream,5);break;
    case 'beacon':
      poly([[-12,-23],[12,-23],[26,40],[-26,40]],body);round(-22,-35,44,17,4,'#efce83');poly([[-27,-35],[0,-46],[27,-35]],s.main);line([[-18,8],[18,8]],cream,10);poly([[-28,-31],[-45,-39],[-45,-19]],'#f2db98');poly([[28,-31],[45,-39],[45,-19]],'#f2db98');break;
    case 'radio':
      line([[14,-29],[25,-49]],ink,5);round(-26,-32,52,74,8,body);round(-18,-23,36,18,3,'#d8dec1');for(let y=4;y<=23;y+=7)line([[-16,y],[13,y]],ink,3);ellipse(10,33,4,4,cream);arc(13,-29,22,-.9,.4,s.main,3);arc(13,-29,31,-.9,.4,s.main,3);break;
    case 'lifering':
      ellipse(0,0,40,40,cream);ellipse(0,0,21,21,'#99bbb8');for(let i=0;i<4;i++){c.save();c.rotate(i*Math.PI/2);poly([[-12,-37],[12,-37],[7,-21],[-7,-21]],s.main);c.restore();}arc(0,0,43,.1,1.5,'#c3a57b',3);break;
    case 'shield':
      c.beginPath();c.moveTo(-34,-29);c.lineTo(0,-43);c.lineTo(34,-29);c.lineTo(29,13);c.quadraticCurveTo(16,32,0,44);c.quadraticCurveTo(-16,32,-29,13);c.closePath();finish(body);star(0,-5,23,'#f1dca1');line([[-14,22],[0,31],[14,22]],cream,3);break;
    case 'record':
      round(-39,-39,59,72,4,body);poly([[-31,11],[-8,-21],[12,12]],s.light);ellipse(14,8,33,33,'#7e777b');ellipse(14,8,25,25,'#9b8a98');ellipse(14,8,13,13,s.light);ellipse(14,8,4,4,cream);arc(14,8,29,3.7,4.7,'#d5c2c8',3);break;
  }
}

function drawOutdoorWork(c:CanvasRenderingContext2D,s:CareerFacadeStyle,career:string){
  const {round,ellipse,poly,line,arc,body,cream}=paint(c,s);
  if(career==='lifeguard'){
    poly([[-47,2],[8,-23],[48,2],[-8,28]],'#e8d9b9');poly([[-38,2],[8,-16],[38,2],[-8,20]],'#88b9b5');
    for(let i=0;i<3;i++)line([[-26+i*13,3-i*4],[i*13,13-i*4]],'#dceadc',1.4);
    line([[23,1],[23,-17],[29,-20],[33,-17],[33,-5]],cream,2.5);
    line([[-31,-5],[-31,-42]],'#b59c76',3);line([[-18,-11],[-18,-45]],'#b59c76',3);round(-35,-43,22,7,2,s.light);line([[-32,-34],[-17,-40]],cream,2);
  }else if(career==='railway'){
    line([[-42,13],[44,-4]],'#8c8271',3);line([[-39,24],[47,7]],'#8c8271',3);
    for(let i=0;i<7;i++)line([[-35+i*12,12-i*2.3],[-31+i*12,27-i*2.3]],'#b8a582',4);
    round(-42,-19,9,40,2,s.main);line([[-38,-17],[44,-33]],cream,6);
    for(let i=0;i<5;i++)line([[-32+i*16,-18-i*3.2],[-26+i*16,-19-i*3.2]],'#bd826e',5);
  }else if(career==='oil'){
    poly([[-45,5],[24,-10],[46,5],[-22,23]],'#b6a27e');
    line([[-31,10],[-31,-19],[12,-28],[12,0]],'#acc0b6',9);line([[-31,10],[-31,-19],[12,-28],[12,0]],'#e0e1c7',3);
    ellipse(12,-12,10,10,'#c99869');ellipse(12,-12,6,6,s.light);line([[5,-19],[19,-5]],'#91775b',2);line([[5,-5],[19,-19]],'#91775b',2);
    round(27,-17,14,26,4,body);ellipse(34,-17,7,3,cream);
  }else if(career==='delivery'){
    ellipse(-28,17,11,11,'#77796b');ellipse(29,17,11,11,'#77796b');ellipse(-28,17,5,5,cream);ellipse(29,17,5,5,cream);
    poly([[-30,7],[-15,-8],[15,-8],[25,9],[5,15],[-19,14]],body);line([[29,17],[26,-14],[18,-20]],'#a3b1a2',4);round(-27,-31,30,24,3,'#e3bf89');line([[-12,-29],[-12,-10]],cream,5);
  }else{
    poly([[-45,5],[15,-23],[44,-4],[-17,25]],'#b09771');
    for(let row=0;row<2;row++)for(let i=0;i<4;i++){
      const x=-30+i*15+row*13,y=3-i*6+row*8;line([[x,y+4],[x,y-7]],'#79865a',2);ellipse(x-4,y-5,6,3,'#a7b97c');ellipse(x+4,y-7,6,3,'#8fa665');
    }
  }
}

function drawEquipment(c:CanvasRenderingContext2D,s:CareerFacadeStyle){
  const {round,ellipse,poly,line,arc,body,cream}=paint(c,s);
  ellipse(0,27,46,10,'#6d624926',undefined);
  switch(s.prop){
    case 'produce':
      poly([[-43,-4],[26,-4],[36,5],[36,26],[-34,28],[-43,19]],'#b2956e');round(-41,4,67,21,3,'#d0b183');
      for(let i=0;i<6;i++){const x=-29+i*10;ellipse(x,-6-(i%2)*6,9,9,i%3===0?'#c68f65':i%3===1?'#b9bc78':'#9aa86d');}line([[-38,12],[24,12]],'#f0d5a3',3);break;
    case 'flowers':
      for(const x of [-24,13]){poly([[x-12,5],[x+13,5],[x+9,27],[x-7,27]],'#bd9271');for(let i=0;i<3;i++){const dx=x+(i-1)*10,y=-18-i%2*10;line([[x,9],[dx,y]],'#809163',3);ellipse(dx,y,9,9,i===1?s.light:s.main);ellipse(dx,y,3,3,'#e8cd8a');}}break;
    case 'parcels':
      round(-38,-1,42,28,3,'#cba575');round(4,-12,34,38,3,'#dfbc87');round(-25,-24,30,24,3,'#e3c592');for(const [x,y,h] of [[-18,0,24],[20,-10,33],[-10,-22,20]])round(x,y,6,h,1,cream,undefined);break;
    case 'books':
      for(let row=0;row<3;row++)round(-33+row*5,14-row*14,64-row*7,12,3,row%2?s.main:s.light);for(let row=0;row<3;row++)line([[-22+row*5,21-row*14],[25,21-row*14]],'#f5e7c8',3);break;
    case 'trolley':
      line([[-32,-30],[-23,-30],[-23,23],[32,23]],'#a68b66',5);round(-20,-12,48,13,3,s.main);round(-18,9,43,12,3,s.light);ellipse(-17,28,5,5,'#7a7766');ellipse(25,28,5,5,'#7a7766');round(-12,-29,13,17,3,cream);round(5,-24,17,12,4,s.light);break;
    case 'stools':
      for(const [x,y] of [[-24,9],[20,-4]]){for(const dx of [-10,10])line([[x+dx,y],[x+dx*1.2,y+22]],s.main,6);round(x-16,y-4,32,9,4,s.light);}break;
    case 'planter':
      poly([[-24,-2],[24,-2],[17,29],[-17,29]],'#c29e79');ellipse(0,-2,24,8,'#958762');for(let i=0;i<6;i++){c.save();c.rotate((i-2.5)*.34);ellipse(0,-21-i%2*8,8,22,i%2?'#9ead79':'#81986b');c.restore();}break;
    case 'toolbox':
      round(-11,-18,25,14,4,s.main);round(-35,-6,70,33,5,body);line([[-34,5],[34,5]],'#a18a66',3);round(-5,0,11,12,2,cream);line([[20,-8],[29,-31]],'#b7c8bd',6);break;
    case 'bins':
      for(const [i,color] of ['#94aa87','#cab278','#8aabad'].entries()){const x=-40+i*29;round(x,-11,24,37,4,color);round(x-2,-17,28,9,3,cream);round(x+7,-2,10,11,2,'#ece8cd');}break;
    case 'luggage':
      line([[-22,-19],[-22,-32],[-8,-32],[-8,-19]],'#b59b75',4);round(-33,-20,35,45,5,body);round(2,-8,33,33,5,s.light);for(const x of [-25,-7,9,27])ellipse(x,28,4,4,'#817461');line([[-21,-11],[-21,15]],cream,3);break;
    case 'barrels':
      for(const [x,y] of [[-22,0],[20,-9]]){round(x-16,y-21,32,48,8,body);ellipse(x,y-21,16,6,s.light);line([[x-15,y-6],[x+15,y-6]],cream,3);line([[x-15,y+13],[x+15,y+13]],cream,3);}break;
    case 'lifering':
      line([[-16,-23],[-16,26]],'#b29a74',6);line([[19,-23],[19,26]],'#b29a74',6);round(-26,-30,56,10,4,s.light);ellipse(0,5,25,25,cream);ellipse(0,5,13,13,'#9bb8b0');arc(0,5,19,-.5,.5,s.main,11);arc(0,5,19,2.7,3.7,s.main,11);break;
  }
}
