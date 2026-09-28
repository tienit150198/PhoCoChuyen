/** Boba-inspired, original 2D storefront. No scraped art, stock fonts or CDN.
 * Reuses the World path/snapshot interface; adds working staff, visible lease
 * upgrades, security equipment and in-world incident feedback.
 *
 * Floor plan: each composition (landscape 1200×790, portrait 700×890) has a
 * PLAN in scene pixels. Feet may only stand inside `floor`, never on a
 * furniture footprint (`blocks`, tier furniture, floor decor) or inside
 * another person's space. Behind the counter is a corridor reached through a
 * clear gap at the counter's right end. Every interactive thing has approach
 * spots on its facing side. `?navdebug=1` draws the grid (off by default).
 */
import {World} from './world.js';
import {t as tr} from './v4/i18n.js';
import {R,E,L,T,P,fit,heart,bloom,plantAt,mascot} from './scenes/kit.js';
import {sceneFor,wordsFor} from './scenes/index.js';
const themes={
 teacher:{primary:'#8ca97c',dark:'#556e46',light:'#f0f2dc',mint:'#e5d8ac',wall:'#fcf5df',awning:'#b5c897',title:'Lớp học Mầm Nắng',sub:'CÙNG THỬ · CÙNG HIỂU · CÙNG TIẾN BỘ',shelves:['Góc học liệu','Hộp đồ lớp mình']},
 tour_guide:{primary:'#78b3b6',dark:'#467c7f',light:'#eaf4e5',mint:'#e2caae',wall:'#eef5e8',awning:'#b3d2c4',title:'Mây Lang Thang',sub:'ĐI CÙNG NHAU · MANG VỀ MỘT CÂU CHUYỆN',shelves:['Bưu thiếp khu phố','Bản đồ & hành trang']},
 milk_tea:{primary:'#dc8ca8',dark:'#995571',light:'#ffe7ef',mint:'#d4ddb9',wall:'#fff4df',awning:'#eea1b7',title:'Trà Mây & Trân Châu',sub:'MỘT CHÚT TRÀ · MỘT CHÚT CHUYỆN',shelves:['Trà & lớp bọt mây','Vị trái cây & topping']},
 mother_baby:{primary:'#cf839c',dark:'#965367',light:'#ffe8ee',mint:'#a8d8c8',wall:'#fff1e6',awning:'#edaabe',title:'Tiệm Mây Nhỏ',sub:'MẸ & BÉ · GÓI NHỮNG NIỀM VUI',shelves:['Đồ mềm xinh','Quà nhỏ mỗi ngày']},
 pharmacy:{primary:'#64ada0',dark:'#327d77',light:'#e5f7ef',mint:'#afcfdf',wall:'#f2faec',awning:'#9bcebd',title:'Quầy Bình An',sub:'ĐỌC KỸ MÃ · CẨN THẬN TỪNG CHÚT',shelves:['Hộp theo mã','Khay & phiếu']},
 accounting:{primary:'#a38cbd',dark:'#75618d',light:'#f0e8fb',mint:'#bdd5c5',wall:'#faf2e8',awning:'#c6b1dc',title:'Góc Sổ Xinh',sub:'CHỨNG TỪ NHỎ · CÂU CHUYỆN RÕ RÀNG',shelves:['Hồ sơ có nguồn','Sổ & kỷ niệm']},
 customer_care:{primary:'#80abc9',dark:'#527a9a',light:'#eaf4fc',mint:'#c3b6df',wall:'#f3faf8',awning:'#adcbdc',title:'Trạm Lắng Nghe',sub:'NGHE THẬT LÒNG · LÀM ĐẾN NƠI',shelves:['Góc lời nhắn','Hồ sơ hỗ trợ']},
};
const HEX=/^#[0-9a-f]{6}$/i;
const mix=(a,b,t)=>{const p=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));const A=p(a),B=p(b);return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join('');};
/** Scene palette for plugin careers, derived from their catalogue colours. */
function pluginTheme(m){
  const col=HEX.test(m.color||'')?m.color:'#cf839c',light=HEX.test(m.light||'')?m.light:mix(col,'#ffffff',.88);
  const motto=String(m.tagline||'').split(/[.!]/)[0];
  return {primary:col,dark:mix(col,'#000000',.32),light,mint:mix(col,'#a8d8c8',.65),wall:mix(light,'#fff8ee',.45),awning:mix(col,'#ffffff',.38),
    title:m.place||m.short||'',sub:[tr(m.short||''),tr(motto)].filter(Boolean).join(' · ').toUpperCase(),shelves:[m.station||m.short||'',m.work||'']};
}
/* ------------------------------------------------------------ Floor plan */
const CLEAR={x:22,y:7};          // walker's own half-size around footprints
const PERSON={rx:46,ry:15};       // two people closer than this overlap badly
/** Does segment AB pass through the open rectangle (x0,y0)-(x1,y1)? */
function segHitsRect(A,B,x0,y0,x1,y1){let t0=0,t1=1;const dx=B.x-A.x,dy=B.y-A.y;
  for(const [p,q] of [[-dx,A.x-x0],[dx,x1-A.x],[-dy,A.y-y0],[dy,y1-A.y]]){if(p===0){if(q<=0)return false;continue;}const t=q/p;if(p<0){if(t>t0)t0=t;}else if(t<t1)t1=t;if(t0>=t1)return false;}
  return t0<t1;}
/** Does segment AB come strictly inside the ellipse at o with radii rx, ry? */
function segHitsEllipse(A,B,o,rx,ry){const u0=(A.x-o.x)/rx,v0=(A.y-o.y)/ry,du=(B.x-A.x)/rx,dv=(B.y-A.y)/ry,len=du*du+dv*dv;
  const t=len?Math.max(0,Math.min(1,-(u0*du+v0*dv)/len)):0,u=u0+t*du,v=v0+t*dv;return u*u+v*v<1;}
const DECOR_FOOT={plant:[-14,-6,14,2],lamp:[-18,-5,18,5],seat:[-25,-2,25,9]};
// Outfit per career for the male player look; the female look keeps the apron.
const OUTFIT={pharmacy:'coat',pet_care:'coat',salon:'coat',accounting:'shirt',corp_accounting:'shirt',tax_payroll:'shirt',group_accounting:'shirt',customer_care:'shirt',teacher:'shirt',
  tour_guide:'vest',homestay:'vest',delivery:'vest',repair:'overalls',farm:'overalls'};

export class BobaWorld extends World {
 isPortrait(){return !this.previewRendering&&this.width<=620;}
 /** The scene kind for this career (public/js/scenes); redraws once a lazily loaded kind arrives. */
 scene(){return sceneFor(this.career,()=>{if(this.c&&this.width)this.setupObjects();});}
 words(){return wordsFor(this.career);}
 plan(){const s=this.scene();return this.isPortrait()?s.plan.port:s.plan.land;}
 preview(career){this.previewRendering=true;try{return super.preview(career);}finally{this.previewRendering=false;}}
 resize(){const was=this.isPortrait();super.resize();if(this.c){if(was!==this.isPortrait()){this.player.path=[];this.player.goal=null;this.pending=null;}this.setupObjects();}}
 say(text,npc=null){super.say(text,npc);this.speech.npc=npc;}
 drawSpeech(){
   if(!this.speech)return;
   // Follow the current projection after a resize; never retain desktop pixels
   // in the portrait scene or draw a bubble outside the playable frame.
   const c=this.ctx,npc=this.speech.npc,portrait=this.isPortrait();
   const target=this.hotspots.find(h=>h.id===`npc:${npc}`)||(npc==='event'?this.hotspots.find(h=>h.id==='event'):null);
   const point=target?this.project(target.x,target.y,155):this.project(this.player.x,this.player.y,155);
   const width=portrait?360:270,size=portrait?21:13,lineHeight=portrait?28:21;
   c.font=`500 ${size}px "Trebuchet MS", "Segoe UI", sans-serif`;
   const lines=[];let current='';
   for(const word of tr(this.speech.text).split(/\s+/)){const next=current?current+' '+word:word;if(current&&c.measureText(next).width>width-28){lines.push(current);current=word;}else current=next;}
   if(current)lines.push(current);
   const shown=lines.slice(0,3);if(lines.length>3)shown[2]=shown[2].slice(0,-1)+'…';
   const height=shown.length*lineHeight+24,frame=portrait?700:1200;
   const x=Math.max(width/2+20,Math.min(frame-width/2-20,point.x)),y=Math.max(height+145,point.y);
   R(c,x-width/2,y-height,width,height,'#fff9ea',15,'#daccb0',1.5);
   P(c,[[x-8,y],[x,y+10],[x+8,y]],'#fff9ea');
   shown.forEach((line,i)=>T(c,line,x,y-height+20+i*lineHeight,size,'#617056',500));
 }
 project(x,y,z=0){return this.isPortrait()?{x:45+x*51,y:285+y*57-z}:{x:150+x*82,y:238+y*45-z};}
 unproject(x,y){return this.isPortrait()?{x:(x-45)/51,y:(y-285)/57}:{x:(x-150)/82,y:(y-238)/45};}
 layout(){if(this.isPortrait()){this.scale=Math.min(this.width/705,Math.max(180,this.height-205)/890);this.offset={x:(this.width-700*this.scale)/2,y:106+Math.max(0,(this.height-215-890*this.scale)/2)};return;}const reserve=this.width>1100?260:this.width>780?210:0;const avail=this.width-reserve;
   this.scale=Math.min(avail/1150,(this.height-55)/780);this.offset={x:(avail-1200*this.scale)/2+10,y:(this.height-790*this.scale)/2+20};
   if(this.width<=780){this.scale=Math.min(this.width/1130,(this.height-190)/650);this.offset={x:(this.width-1200*this.scale)/2,y:Math.max(76,(this.height-790*this.scale)/2-25)};}
 }
 /* ------------------------------------------------------ Nav model */
 navMetric(){const p=this.plan();return {kx:p.kx,ky:p.ky};}
 navBounds(){const f=this.plan().floor,a=this.unproject(f[0],f[1]),b=this.unproject(f[2],f[3]);return {x0:a.x-.2,y0:a.y-.2,x1:b.x+.2,y1:b.y+.2};}
 navHome(){const h=this.plan().home;return this.unproject(h[0],h[1]);}
 navSnap(){return 150;}
 navSignature(){return JSON.stringify([this.isPortrait(),this.props||[],(this.people||[]).map(q=>[q.x.toFixed(3),q.y.toFixed(3),q.rx])]);}
 /** Floor bounds and furniture only (no people). */
 navStaticBlocked(x,y){const s=this.project(x,y),f=this.plan().floor,e=1e-6;
   if(!(s.x>=f[0]-e&&s.x<=f[2]+e&&s.y>=f[1]-e&&s.y<=f[3]+e))return true;
   for(const r of this.props||[])if(s.x>r[0]-CLEAR.x&&s.x<r[2]+CLEAR.x&&s.y>r[1]-CLEAR.y&&s.y<r[3]+CLEAR.y)return true;
   return false;}
 navFree(x,y){if(this.navStaticBlocked(x,y))return false;const s=this.project(x,y);
   for(const q of this.people||[]){const o=this.project(q.x,q.y),dx=(s.x-o.x)/q.rx,dy=(s.y-o.y)/q.ry;if(dx*dx+dy*dy<1)return false;}
   return true;}
 free(x,y){return this.navFree(x,y);}
 /** Exact segment test in scene pixels (same open shapes as navFree), so a
  * smoothed shortcut can never graze a footprint corner between samples. */
 lineClear(a,b){const A=this.project(a.x,a.y),B=this.project(b.x,b.y),f=this.plan().floor,e=1e-6,inside=p=>p.x>=f[0]-e&&p.x<=f[2]+e&&p.y>=f[1]-e&&p.y<=f[3]+e;
   if(!inside(A)||!inside(B))return false;
   for(const r of this.props||[])if(segHitsRect(A,B,r[0]-CLEAR.x,r[1]-CLEAR.y,r[2]+CLEAR.x,r[3]+CLEAR.y))return false;
   for(const q of this.people||[]){const o=this.project(q.x,q.y);if(segHitsEllipse(A,B,o,q.rx,q.ry))return false;}
   return true;}
 decorFootprints(){const pl=this.plan(),out=[];
   for(const [id,entry] of Object.entries(this.c?.decor||{})){const at=pl.decor[entry?.spot],f=DECOR_FOOT[id];if(at&&f)out.push([at[0]+f[0],at[1]+f[1],at[0]+f[2],at[1]+f[3]]);}
   return out;}
 setupObjects(){const c=this.c||{},pl=this.plan(),tile=([x,y])=>this.unproject(x,y),tier=c.ops?.property?.tier||'cozy';
   this.hotspots=[];this.people=[];
   this.props=[...pl.blocks,...(tier!=='cozy'?[pl.bench]:[]),...(tier==='garden'?pl.garden.map(([x,y])=>[x-12,y-6,x+12,y+4]):[]),...this.decorFootprints()];
   const add=(id,label,at,range,go,z=0)=>{const t=tile(at);this.hotspots.push({id,label,x:t.x,y:t.y,z,range,point:this.project(t.x,t.y,z),approach:go.map(tile)});};
   const spot=(key,id,label)=>{const [at,range,go]=pl.spots[key];add(id,label,at,range,go);};
   // Talk to someone across the counter when they stand in front of it,
   // otherwise from their left or right side.
   const beside=([x,y])=>[[-82,0],[82,0],[-62,-26],[62,-26],[0,-34],[-62,26],[62,26],[0,34]].map(([dx,dy])=>[x+dx,y+dy]);
   const person=(id,label,feet,{across=false,sway=0,go=null}={})=>{const t=tile(feet);
     const spots=go||[...(across&&feet[0]>=pl.counterSpan[0]&&feet[0]<=pl.counterSpan[1]?[[feet[0],pl.lane]]:[]),...beside(feet)];
     add(id,label,feet,39,spots,49);this.people.push({id,x:t.x,y:t.y,rx:PERSON.rx+sway,ry:PERSON.ry});};
   const w=this.words(),station=this.game?.catalogue?.find(x=>x.id===this.career)?.station;
   spot('shelf','shelf',w.shelf);
   spot('evidence','evidence',w.evidence);
   spot('workbench','workbench',station||'Bàn làm việc');
   spot('counter','counter',w.counter);
   spot('warehouse','warehouse',this.career==='milk_tea'||!c.inventory||w.warehouse!=='Kho sau tiệm'?w.warehouse:'Kho & nhập hàng');
   spot('board','board',w.board);
   spot('finance','ops:finance',w.finance);
   spot('property','ops:property',w.property);
   spot('security','ops:security',w.security);
   spot('door','door',c.open?w.door_open:w.door_closed);
   spot('pet','pet',w.pet);
   const active=c.tasks?.filter(t=>!['completed','referred','cancelled'].includes(t.status))||[],used=new Set();let slot=0;
   for(const t of active){if(slot>=4)break;if(used.has(t.npc))continue;used.add(t.npc);person('npc:'+t.npc,this.npcName(t.npc),pl.customers[slot++],{across:true});}
   if(c.event&&c.event.stage!=='resolved')person('event','Chuyện mới',pl.event);
   const hired=(c.ops?.staff||[]).filter(e=>e.status==='hired');
   hired.forEach((e,i)=>{const base=this.staffBase(i),working=this.staffWorking(e);person('staff:'+e.id,e.name+' · '+(working?'đang phụ':'nghỉ'),base,{sway:working?pl.sway:0,go:[[base[0],pl.lane]]});});
   if(c.upgrades?.includes('assistant')&&!hired.length){const base=this.staffBase(0);person('assistant','Bạn phụ việc cũ',base,{go:[[base[0],pl.lane]]});}
   const caseNow=c.ops?.security?.current_case;
   if(caseNow&&['reported','result'].includes(caseNow.status))person('officer','Công an khu phố',pl.officer);
   // Staff hit targets start at their base spot; animate() keeps them in step.
   hired.forEach((e,i)=>{const h=this.hotspots.find(h=>h.id==='staff:'+e.id);if(h){Object.assign(h,this.staffPosition(i,e));h.point=this.project(h.x,h.y,h.z);}});
   this.navBuild();
 }
 staffBase(i){const s=this.plan().staff;return [s.x+i*s.step,s.y];}
 staffWorking(e){return !!(this.c?.open&&e.on_shift&&e.rest_until<=this.c.turn);}
 staffPosition(i,e){const pl=this.plan(),[bx,by]=this.staffBase(i),moving=this.staffWorking(e);
   const shift=moving&&!this.reduced?Math.sin(this.time*.55+i)*pl.sway:0,t=this.unproject(bx+shift,by);
   return {x:t.x,y:t.y,moving};
 }
 animate(dt){const keys=this.keys;this.keys=new Set();super.animate(dt);this.keys=keys;
   if(keys.size){let dx=0,dy=0;if(keys.has('a')||keys.has('arrowleft'))dx--;if(keys.has('d')||keys.has('arrowright'))dx++;if(keys.has('w')||keys.has('arrowup'))dy--;if(keys.has('s')||keys.has('arrowdown'))dy++;
     this.keyMove(dx,dy,dt,this.isPortrait()?170:230);}
   // Staff hit targets follow the visible walking sprites, not a stale position.
   (this.c?.ops?.staff||[]).filter(e=>e.status==='hired').forEach((e,i)=>{const h=this.hotspots.find(h=>h.id==='staff:'+e.id);if(h){Object.assign(h,this.staffPosition(i,e));h.point=this.project(h.x,h.y,h.z);}});
 }
 palette(){const meta=!themes[this.career]&&this.game?.catalogue?.find(x=>x.id===this.career);const p={...(themes[this.career]||(meta?pluginTheme(meta):themes.mother_baby))};if(this.c?.life?.shop_name)p.title=this.c.life.shop_name;if(this.c?.theme==='sage')p.wall='#edf5e8';if(this.c?.theme==='lavender')p.wall='#f3e9fb';if(this.c?.theme==='warm')p.wall='#fff0da';return p;}
 plantAt(x,y,size=1){plantAt(this.ctx,x,y,size);}
 drawRoom(){this.scene().room(this,this.palette());}
 /** Storefront back wall (scenes/shop.js). */
 shopRoom(){if(this.isPortrait()){this.portraitRoom();return;}const c=this.ctx,p=this.palette();
   E(c,605,724,503,30,'#cba88d22');R(c,85,165,1030,550,'#e3b694',35);R(c,96,168,1008,533,'#fff9ee',30,'#d9ac90',3);
   // Windowed back wall and soft checkerboard floor.
   R(c,108,179,984,301,p.wall,22);R(c,108,445,984,244,'#fbecd7',16);
   c.save();c.beginPath();c.roundRect(108,445,984,244,16);c.clip();for(let x=108;x<1095;x+=82)for(let y=445;y<690;y+=61){c.fillStyle=((x-108)/82+(y-445)/61)%2===0?'#fff5e4':'#f1e0c7';c.fillRect(x,y,82,61);}c.restore();
   for(let x=125;x<1100;x+=28)L(c,x,190,x,440,'#f2dace3a',1);
   // Central arched window: sunshine, tree silhouettes and quiet street.
   R(c,432,228,282,191,'#e2bea0',25);R(c,441,237,264,174,'#cbe8e7',20);E(c,648,264,21,21,'#fff0be');
   E(c,467,396,52,54,'#aacead');E(c,702,389,51,55,'#a7cdb4');E(c,642,416,90,28,'#d7e6b6');
   L(c,574,242,574,409,'#fffaf0',8);L(c,447,323,700,323,'#fffaf0',8);
   R(c,425,410,296,12,'#d4a487',5);for(let i=0;i<6;i++){R(c,436+i*6,237,6,140-i*12,'#efd4cb',3);R(c,702-i*6,237,6,140-i*12,'#efd4cb',3);}
   if(['teacher','tour_guide','milk_tea'].includes(this.career))this.professionBoard(448,241,251,156);
   // Back shelves with profession-specific objects, not boba products in every career.
   this.cabinet(135,250,258,166,0);this.cabinet(750,250,253,166,1);
   // A scalloped pastel canopy and frosted sign.
   R(c,112,141,980,58,'#d1a284',15);
   c.save();c.beginPath();c.roundRect(108,148,984,77,17);c.clip();for(let i=0;i<16;i++){R(c,108+i*61.5,148,62,65,i%2?'#fff5e6':p.awning,0);E(c,139+i*61.5,211,31,13,i%2?'#fff5e6':p.awning);}c.restore();
   R(c,351,75,460,101,'#c39377',34);R(c,358,68,446,98,'#fff9ec',32,'#e4c2a8',3);R(c,367,77,428,80,'#fffaf1',26,'#eddbbc',2);
   this.mascot(397,120,.67);T(c,p.title,590,112,p.title.length>24?29:37,p.dark,800);T(c,p.sub,585,145,10,p.dark,700);
   heart(c,763,116,.48,p.primary);
   // String lights and climbing leaves.
   c.strokeStyle='#d2b48c';c.lineWidth=2;c.beginPath();c.moveTo(130,213);c.quadraticCurveTo(575,271,1060,213);c.stroke();
   for(let i=0;i<13;i++){const x=144+i*74,y=214+Math.sin(i/12*Math.PI)*25;L(c,x,y,x,y+8,'#cab494',1);E(c,x,y+11,4,6,'#ffe8a4');}
   for(let i=0;i<9;i++){E(c,98+Math.sin(i)*13,186+i*19,15,7,i%2?'#a2c596':'#81b095');E(c,1102+Math.cos(i)*10,185+i*19,15,7,i%2?'#a2c596':'#81b095');}
   // Tiny menu/notebook on the wall.
   R(c,1023,311,62,108,'#c49878',9);R(c,1028,316,52,97,'#fff6e4',6);T(c,'CHUYỆN',1054,333,9,p.dark);T(c,'PHỐ',1054,347,12,p.dark);for(let i=0;i<3;i++){R(c,1036,361+i*14,34,8,[p.light,'#e6edcf','#f4d7cf'][i],3);}
   this.securityProps();
 }
 /** Things standing on the floor, as [depth, draw] pairs sorted with people. */
 floorProps(){const c=this.ctx,p=this.palette(),out=this.scene().props(this,p);
   out.push(...this.decorProps(p));return out;}
 /** Storefront furniture (scenes/shop.js): counter, store, ledger, door sign, bench. */
 shopProps(){const c=this.ctx,p=this.palette(),w=this.words(),tier=this.c?.ops?.property?.tier||'cozy',open=this.c?.open,items=this.c?.ops?.security?.items||[],out=[];
   if(this.isPortrait()){
     out.push([626,()=>this.portraitCounter()],[612,()=>{R(c,24,524,62,92,'#c6a27f',6);R(c,30,530,50,78,'#ecd1af',4);T(c,w.store,55,570,17,p.dark,800);if(items.includes('lock')){R(c,62,553,17,20,'#d8c596',5);L(c,66,553,66,546,'#a09675',3);L(c,75,553,75,546,'#a09675',3);}}]);
     out.push([752,()=>{R(c,560,701,90,50,'#d6b492',10);R(c,553,693,104,13,'#eed3b0',5);R(c,576,668,57,28,'#fff8e9',5,'#d5b395',1);L(c,577,671,604,685,p.primary,1.5);L(c,632,671,604,685,p.primary,1.5);T(c,w.ledger,605,730,16,p.dark,800);}]);
     out.push([795,()=>this.plantAt(62,791,1.03)],[824,()=>this.plantAt(642,822,.75)]);
     out.push([820,()=>{R(c,470,786,114,32,'#fff8e8',13,'#c6a182',2);T(c,open?w.open_sign:w.closed_sign,527,803,12,p.dark);}]);
     if(tier!=='cozy')out.push([826,()=>{R(c,80,793,121,16,p.mint,7);R(c,80,765,121,30,p.mint,9);L(c,90,810,90,825,'#af8b6c',6);L(c,193,810,193,825,'#af8b6c',6);T(c,'ngồi nghỉ nhé',140,780,12,p.dark);if(tier==='garden')bloom(c,190,758,12,p.primary);}]);
     if(tier==='garden')for(const [x,y] of this.plan().garden)out.push([y+4,()=>this.plantAt(x,y,.7)]);
   }else{
     out.push([563,()=>this.drawCounter()],[536,()=>{R(c,140,438,69,95,'#c8a27e',7);R(c,146,444,57,81,'#e8c6a4',4);T(c,w.store,173,484,13,'#826249');R(c,151,517,7,4,'#a88e70',2);if(items.includes('lock')){R(c,180,448,18,24,'#d2c290',5,'#a59470',1);c.beginPath();c.arc(189,448,6,Math.PI,0);c.strokeStyle='#968f79';c.lineWidth=3;c.stroke();}}]);
     out.push([566,()=>{R(c,985,503,94,61,'#d4b391',12);R(c,979,494,106,15,'#f0d2ad',7);R(c,1000,469,65,29,'#fff8e7',5,'#d9b596',1);L(c,1001,470,1032,486,p.primary,1.5);L(c,1064,470,1032,486,p.primary,1.5);T(c,w.ledger,1032,548,11,'#7c604e');}]);
     out.push([582,()=>this.plantAt(118,578,1.25)]);
     out.push([668,()=>{R(c,970,625,112,42,'#fdf7e8',16,'#b99171',2);T(c,open?w.open_sign:w.closed_sign,1026,642,12,p.dark);T(c,'một nhịp thật dịu',1026,657,8,'#a38a7a',500);}]);
     if(tier!=='cozy')out.push([676,()=>{R(c,148,625,125,19,p.mint,8);L(c,162,644,162,674,'#af8b6c',7);L(c,261,644,261,674,'#af8b6c',7);R(c,149,587,125,45,p.mint,13);T(c,'ngồi nghỉ nhé ♡',211,608,11,'#50796b');if(tier==='garden')bloom(c,262,575,15,p.primary);}]);
     if(tier==='garden')for(const [x,y] of this.plan().garden)out.push([y+2,()=>this.plantAt(x,y,.6)]);
   }
   return out;
 }
 /** Decor bought by the player stands on its chosen floor spot. */
 decorProps(p){const c=this.ctx,pl=this.plan(),out=[];
   for(const [id,entry] of Object.entries(this.c?.decor||{})){const at=pl.decor[entry?.spot];if(!at||id==='rug'||id==='poster')continue;const [x,y]=at;
     if(id==='plant')out.push([y,()=>this.plantAt(x,y,.8)]);
     if(id==='lamp')out.push([y,()=>{L(c,x,y,x,y-83,'#c6a47f',5);P(c,[[x-13,y-100],[x+13,y-100],[x+26,y-70],[x-26,y-70]],'#f5ddb1');E(c,x,y,18,5,'#cead8e');}]);
     if(id==='seat')out.push([y+9,()=>{R(c,x-25,y-31,50,26,p.mint,10);L(c,x-19,y-6,x-19,y+9,'#bf9d7a',5);L(c,x+19,y-6,x+19,y+9,'#bf9d7a',5);}]);
   }
   return out;
 }
 /** Flat or wall-hung decor, drawn before anyone stands on the floor. */
 wallDecor(){const c=this.ctx,p=this.palette(),pl=this.plan(),portrait=this.isPortrait();
   for(const [id,entry] of Object.entries(this.c?.decor||{})){
     if(id==='rug'){const at=pl.decor[entry?.spot]||pl.sill.rug;E(c,at[0],at[1],portrait?40:45,portrait?15:16,'#d4b6ce66');T(c,'♡',at[0],at[1],19,'#b6869e');}
     // "By the window" means on the sill: no footprint on the floor.
     if(entry?.spot==='window'&&pl.sill[id]&&id!=='rug'){const [x,y]=pl.sill[id];
       if(id==='plant')this.plantAt(x,y,.5);
       if(id==='lamp'){L(c,x,y,x,y-30,'#c6a47f',3);P(c,[[x-8,y-40],[x+8,y-40],[x+14,y-26],[x-14,y-26]],'#f5ddb1');E(c,x,y,9,3,'#cead8e');}
       if(id==='seat'){R(c,x-22,y-11,44,12,p.mint,6,'#c9a88a',1);E(c,x,y-9,12,3,'#ffffff55');}}
     if(id==='poster'){const [x,y]=portrait?[170,472]:[1054,285];R(c,x-25,y-24,50,48,'#fff6e9',9,'#d1ad8e',2);heart(c,x,y+4,.58,p.primary);}
   }
   if(this.c?.upgrades?.includes('shelf')&&!portrait){R(c,1009,440,65,21,'#e3b99c',6);for(let i=0;i<2;i++)this.tinyItem(1023+i*30,442,i+2);}
 }
 cabinet(x,y,w,h,index){const c=this.ctx,p=this.palette();R(c,x-4,y-21,w+8,h+29,'#dcb396',10,'#b78b6c',2);R(c,x+5,y+6,w-10,h-9,'#fff3e0',7);
   R(c,x+17,y-34,w-34,32,p.light,12,'#d9b7a1',1.5);T(c,p.shelves[index],x+w/2,y-17,13,p.dark);
   for(let row=0;row<3;row++){const yy=y+47+row*52;for(let col=0;col<(w<210?3:5);col++)this.tinyItem(x+29+col*(w-55)/(w<210?2:4),yy,((row*5+col+index*2)%8));R(c,x,yy+8,w,9,'#d6a581',2);R(c,x+3,yy+7,w-6,3,'#efcbaa',1);}
 }
 tinyItem(x,y,index){const c=this.ctx,p=this.palette(),colors=['#eeb8c7','#a9d6c6','#b6c9e3','#e8cc95','#c9b5dc','#f6d8c1'];const col=colors[index%6];
   if(this.career==='milk_tea'){if(index%2){R(c,x-9,y-32,18,35,col,5,'#ad8662',1.6);R(c,x-5,y-42,10,12,'#f5ebd1',2,'#9c7b57',1);L(c,x,y-43,x,y-48,'#765943',3);L(c,x,y-48,x+14,y-48,'#765943',3);R(c,x-6,y-19,12,14,'#fff3db',4);heart(c,x,y-12,.2,p.primary);}else{R(c,x-16,y-26,32,30,col,5,'#a88964',1.5);R(c,x-18,y-32,36,8,'#e6d5ae',4,'#a88964',1.5);T(c,['茶','●','☁'][index%3],x,y-10,13,'#fff9e9');}}
   else if(this.career==='tour_guide'){R(c,x-14,y-29,28,35,col,4,'#a78864',1.5);L(c,x-5,y-26,x-5,y+4,'#fff2da',2);L(c,x+4,y-26,x+4,y+4,'#fff2da',2);L(c,x-11,y-10,x+10,y-15,'#ac815e',2);T(c,'⚑',x+7,y-15,12,'#806046');}
   else if(this.career==='teacher'){R(c,x-13,y-30,26,34,col,3,'#a58b68',1.3);R(c,x-10,y-28,3,28,'#fff3d4',2);T(c,['A','3','★','B'][index%4],x+2,y-11,17,'#fffbe9',800);}
   else if(this.career==='mother_baby'&&index%4===0){E(c,x-10,y-22,7,10,'#f3dbb0');E(c,x+10,y-22,7,10,'#f3dbb0');E(c,x,y-13,17,18,'#f7e4c5');E(c,x-6,y-16,2,3,'#705345');E(c,x+6,y-16,2,3,'#705345');E(c,x,y-10,3,2,'#c18d80');R(c,x-11,y-1,22,5,col,2);}
   else if(this.career==='mother_baby'&&index%4===1){R(c,x-16,y-30,32,35,col,6,'#c8a68c',1);c.beginPath();c.arc(x,y-31,9,Math.PI,0);c.strokeStyle='#b7997d';c.lineWidth=3;c.stroke();heart(c,x,y-15,.35,'#fff7e9');}
   else if(['accounting','customer_care'].includes(this.career)){R(c,x-14,y-30,29,36,col,4,'#b89d97',1);R(c,x-11,y-27,4,29,'#ffffff60',2);R(c,x-3,y-19,14,12,'#fff8e8',2);L(c,x,y-15,x+7,y-15,p.primary,1);L(c,x,y-11,x+7,y-11,p.primary,1);}
   else{R(c,x-14,y-29,28,35,col,5,'#c0ac97',1);R(c,x-12,y-27,24,7,'#ffffff80',2);R(c,x-8,y-15,16,11,'#fff9eb',2);T(c,this.career==='pharmacy'?'P-'+(index+1):'♡',x,y-9,this.career==='pharmacy'?7:12,p.dark);}
 }
 mascot(x,y,scale=1){mascot(this.ctx,x,y,scale);}
 securityProps(){if(this.isPortrait()){this.portraitSecurity();return;}const c=this.ctx,p=this.palette(),items=this.c?.ops?.security?.items||[];
   if(items.includes('camera')){L(c,148,241,162,232,'#b79b85',5);R(c,151,220,39,21,'#f5f2eb',7,'#a7aaa2',2);E(c,185,230,8,9,'#7a8992');E(c,186,230,4,5,'#b4d9df');E(c,157,225,2,2,'#90bd8b');}
   else {R(c,183,206,43,24,'#fff6e9',8,'#d5b59a',1);T(c,'♧',204,218,15,p.dark);}
   if(items.includes('bell')){L(c,1070,226,1070,241,'#ac8f73',2);P(c,[[1060,258],[1080,258],[1077,245],[1063,245]],'#f0ce85');E(c,1070,260,4,3,'#d4ad64');}
   if(items.includes('light')){const g=c.createRadialGradient(1078,456,0,1078,456,100);g.addColorStop(0,'#ffe1a44a');g.addColorStop(1,'#ffe1a400');c.fillStyle=g;c.fillRect(978,356,200,200);R(c,1065,426,27,39,'#fff0b8',8,'#b69b79',2);L(c,1078,413,1078,426,'#b69b79',3);}
 }
 drawCounter(){const c=this.ctx,p=this.palette();E(c,546,565,326,17,'#bb97781d');
   R(c,232,485,628,88,p.mint,15,'#8daf9e',2);R(c,244,497,604,62,'#ffffff19',8);for(let x=266;x<850;x+=32)L(c,x,504,x,558,'#689c8620',1.3);
   R(c,220,473,652,25,'#e6bd99',10,'#b99476',2);R(c,225,475,642,7,'#f5d7b6',3);
   R(c,479,513,187,35,'#fff7e9',17,'#c7ad90',2);T(c,'chăm chút từng ngày',572,531,14,p.dark);heart(c,461,533,.38,p.primary);heart(c,684,533,.38,p.primary);
   // Tools are tied to the profession; the wrapping tray is not just decorative UI.
   if(this.career==='mother_baby'){
     R(c,398,450,160,20,'#f2d6dd',6);R(c,444,412,61,44,'#f9e5bd',8,'#caaa83',1.5);L(c,474,414,474,457,p.primary,7);L(c,446,435,503,435,p.primary,6);E(c,465,409,13,6,p.primary);E(c,485,409,13,6,p.primary);R(c,521,431,35,19,'#c2d9c8',5);T(c,'✦',538,441,15,'#fff8eb');
   } else if(this.career==='pharmacy'){
     R(c,397,439,157,28,'#f3faf6',9,'#96b8a7',2);this.tinyItem(441,439,1);this.tinyItem(487,439,2);R(c,538,420,40,48,'#fff5df',4,'#d2b595',2);T(c,'✓',558,436,19,p.dark);T(c,'P-03',558,454,8,p.dark);
   } else {
     R(c,384,424,65,47,'#fff8eb',4,'#d3b7a1',1);R(c,394,419,65,46,'#fff9ed',4,'#d3b7a1',1);for(let i=0;i<4;i++)L(c,405,431+i*7,444,431+i*7,i===0?p.primary:'#c2b8b1',2);R(c,470,433,45,35,p.light,6);T(c,this.career==='accounting'?'550':'♡',492,450,14,p.dark);
   }
   if(this.career==='teacher'){R(c,644,403,165,61,'#fff7db',6,'#b99c70',2);T(c,'3 + 4 = 7',727,432,20,p.dark);for(let i=0;i<3;i++){R(c,670+i*24,453,18,16,['#e3b57f','#b2ce8e','#d8a8b4'][i],3);}}else if(this.career==='tour_guide'){R(c,650,409,176,61,'#f8efc9',6,'#b7aa76',2);L(c,665,456,806,423,'#9fbe94',7);for(let i=0;i<3;i++)T(c,'⚑',679+i*59,449-i*10,20,p.dark);}else this.monitor(741,451);this.bobaCup(650,466,.8);bloom(c,846,428,14,p.primary);L(c,846,430,846,456,'#8eaf82',2);R(c,833,453,27,18,'#f4e6d1',5);
   if((this.c?.ops?.equipment?.condition||100)<100){R(c,264,463,91,14,'#f7d995',4);T(c,'CẦN KIỂM',310,470,9,'#94643d');L(c,276,450,288,463,'#e6ad63',4);L(c,292,450,304,463,'#e6ad63',4);}
 }
 monitor(x,y){const c=this.ctx,p=this.palette();R(c,x-21,y+4,54,10,p.dark,5);R(c,x-4,y-19,17,31,p.dark,4);R(c,x-50,y-71,107,61,p.dark,10);R(c,x-44,y-65,95,48,'#f9fff5',6);R(c,x-36,y-57,34,31,p.light,4);T(c,'♡',x-19,y-40,22,p.primary);for(let i=0;i<3;i++)R(c,x+6,y-53+i*10,34-i*4,4,i===0?p.primary:'#c8d8c8',2);R(c,x-30,y+12,77,8,'#e9ebdf',4,'#aebfae',1);
   if(this.career==='customer_care'){c.beginPath();c.arc(x+67,y-8,18,Math.PI,0);c.strokeStyle=p.primary;c.lineWidth=6;c.stroke();R(c,x+45,y-10,8,20,p.dark,4);R(c,x+79,y-10,8,20,p.dark,4);}
 }
 bobaCup(x,y,scale=1){const c=this.ctx;c.save();c.translate(x,y);c.scale(scale,scale);P(c,[[-18,-45],[18,-45],[14,0],[-14,0]],'#e9c8a3');R(c,-21,-50,42,8,'#fff3e5',4,'#d8b597',1);L(c,4,-49,12,-77,'#be86a8',6);for(let i=0;i<9;i++)E(c,-9+i%3*9,-7-Math.floor(i/3)*8,3.8,3.8,'#8e6c59');R(c,-12,-35,24,15,'#fff5e7',6);heart(c,0,-25,.3,'#d693ac');c.restore();}
 /** The player's chosen look: 'female' keeps the original bun, flower and
  * long hair; 'male' gets short hair and a work outfit fitting the career;
  * no choice yet gives a neutral short-haired look without accessories. */
 playerLook(){const g=this.state?.journey?.gender;return g==='male'||g==='female'?g:'neutral';}
 character(x,y,id,player=false,moving=false){const c=this.ctx,p=this.project(x,y),pal=this.palette();
   const employee=this.c?.ops?.staff?.find(e=>e.id===id),officer=id==='officer';const n=employee?.avatar??(Number(String(id).slice(-2))||0);const old=!player&&!employee&&n===2;
   const look=player?this.playerLook():null,long=player?look==='female':n%2===1;const hair=old?'#ada59f':player?(look==='male'?'#4f3a30':'#74503f'):n%2?'#755440':'#544641';
   const outfit=officer?'#719c95':employee?.color|| (player?pal.primary:['#aacabb','#c8b7da','#dfb6a2','#94b7c8'][n%4]);const blink=!this.reduced&&Math.sin(this.time*1.1+n)>.992;const bob=this.reduced?0:Math.sin(this.time*(moving?7:1.8)+n)*(moving?2:1);
   c.save();c.translate(p.x,p.y+bob);c.scale(1.08,1.08);E(c,0,0,26,8,'#81644823');
   const step=moving&&!this.reduced?Math.sin(this.time*8)*3:0;R(c,-19,-20,15,20,look==='male'?'#6f6a78':'#f0d3b8',5);R(c,4,-20,15,20,look==='male'?'#6f6a78':'#f0d3b8',5);R(c,-21,-7+step,19,10,'#785c51',5);R(c,3,-7-step,19,10,'#785c51',5);
   if(long)R(c,-28,-92,56,64,hair,22);
   R(c,-23,-52,46,36,outfit,15);E(c,-25,-36,8,14,'#f5d5ba');E(c,25,-36,8,14,'#f5d5ba');
   if(player&&look==='male')this.workOutfit(pal);
   else if(player||employee){P(c,[[-14,-47],[14,-47],[19,-16],[-19,-16]],'#fff7e8');L(c,-15,-49,-10,-59,'#fff7e8',4);L(c,15,-49,10,-59,'#fff7e8',4);R(c,-10,-31,20,10,pal.light,4);heart(c,0,-26,.22,pal.primary);}
   // Generous face, warm cheeks, layered hair and eye highlights.
   E(c,0,-84,33,35,hair);E(c,-29,-71,5,8,'#f3ceb1');E(c,29,-71,5,8,'#f3ceb1');E(c,0,-77,29,28,'#f8dcc2');
   c.beginPath();
   if(look==='male'){c.moveTo(-31,-80);c.bezierCurveTo(-35,-118,24,-124,32,-84);c.quadraticCurveTo(26,-95,12,-99);c.quadraticCurveTo(-4,-92,-18,-97);c.quadraticCurveTo(-26,-92,-31,-80);}
   else{c.moveTo(-30,-88);c.bezierCurveTo(-33,-119,19,-120,31,-90);c.quadraticCurveTo(19,-93,7,-105);c.quadraticCurveTo(5,-88,-12,-84);c.quadraticCurveTo(-17,-91,-16,-101);c.quadraticCurveTo(-21,-89,-30,-88);}
   c.fillStyle=hair;c.fill();
   E(c,-20,-67,7,4,look==='male'?'#efb3a466':'#efa7a0');E(c,20,-67,7,4,look==='male'?'#efb3a466':'#efa7a0');
   if(blink){L(c,-16,-78,-7,-78,'#654739',2);L(c,7,-78,16,-78,'#654739',2);}else{for(const ex of [-11,11]){E(c,ex,-78,5,7,'#705140');E(c,ex-1.3,-80.4,1.8,2.3,'#fffdf3');E(c,ex+1,-75,1,1,'#d7b895');}}
   if(look==='male'){L(c,-16,-89,-6,-90,hair,2.4);L(c,6,-90,16,-89,hair,2.4);}
   c.beginPath();c.arc(0,-66,4,0,Math.PI);c.strokeStyle='#b17c69';c.lineWidth=1.6;c.stroke();
   if(look==='female'){E(c,-18,-113,17,15,hair);L(c,-25,-112,-12,-120,'#9f7660',2);bloom(c,20,-99,8,'#ffe5b0');}
   if(old){for(const ex of [-11,11]){c.beginPath();c.arc(ex,-78,9,0,Math.PI*2);c.strokeStyle='#89736a';c.lineWidth=1.6;c.stroke();}L(c,-2,-78,2,-78,'#89736a',1);}
   if(officer){R(c,-34,-109,68,14,'#69938c',8);R(c,-25,-119,50,18,'#82aca0',7);T(c,'★',0,-110,10,'#f7dd93');R(c,9,-39,10,9,'#f0d995',2);}
   if(this.career==='customer_care'&&player){c.beginPath();c.arc(0,-84,32,Math.PI,0);c.strokeStyle=pal.dark;c.lineWidth=5;c.stroke();R(c,27,-82,9,17,pal.primary,4);L(c,32,-69,17,-64,pal.dark,2);}
   c.restore();
 }
 /** Male player's torso layer: apron for shops and kitchens, a white coat,
  * shirt and tie, work vest or overalls depending on the career. */
 workOutfit(pal){const c=this.ctx,kind=OUTFIT[this.career]||'apron';
   if(kind==='coat'){R(c,-24,-53,48,38,'#f8f6ee',14,'#d8d4c6',1.2);P(c,[[-7,-52],[7,-52],[0,-38]],pal.primary);L(c,-7,-52,-3,-30,'#d8d4c6',1.5);L(c,7,-52,3,-30,'#d8d4c6',1.5);R(c,8,-34,9,7,'#e9e5d8',2);}
   else if(kind==='shirt'){R(c,-23,-52,46,36,'#f6f3ea',15);P(c,[[-10,-52],[0,-44],[10,-52]],'#e2ddcf');P(c,[[-3,-46],[3,-46],[5,-26],[0,-21],[-5,-26]],pal.dark);R(c,-23,-40,8,20,pal.primary,6);R(c,15,-40,8,20,pal.primary,6);}
   else if(kind==='vest'){P(c,[[-20,-50],[-6,-50],[-4,-18],[-20,-18]],pal.dark);P(c,[[20,-50],[6,-50],[4,-18],[20,-18]],pal.dark);R(c,-17,-34,9,6,'#f3e6cf',2);R(c,8,-34,9,6,'#f3e6cf',2);}
   else if(kind==='overalls'){R(c,-15,-38,30,22,pal.dark,6);L(c,-11,-38,-15,-52,pal.dark,4);L(c,11,-38,15,-52,pal.dark,4);E(c,-10,-36,2,2,'#f3d590');E(c,10,-36,2,2,'#f3d590');R(c,-6,-32,12,7,'#ffffff30',2);}
   else{P(c,[[-13,-46],[13,-46],[18,-16],[-18,-16]],pal.dark);L(c,-14,-48,-10,-59,pal.dark,3);L(c,14,-48,10,-59,pal.dark,3);R(c,-8,-31,16,9,'#ffffff28',3);heart(c,0,-26,.2,'#fff7e8');}
 }
 drawFurnitureAndActors(){const staff=this.c?.ops?.staff?.filter(e=>e.status==='hired')||[],items=[];
   this.wallDecor();
   // Mướp naps on the window sill, out of everyone's way.
   const cat=this.plan().cat,ct=this.unproject(cat[0],cat[1]);this.cat(ct.x,ct.y);
   this.drawMarker();
   staff.forEach((e,i)=>{const p=this.staffPosition(i,e);items.push([this.project(p.x,p.y).y,()=>this.character(p.x,p.y,e.id,false,p.moving)]);});
   for(const h of this.hotspots){const id=h.id.startsWith('npc:')?h.id.slice(4):h.id==='event'?this.c.event.npc:h.id==='officer'?'officer':h.id==='assistant'?this.career+'_npc_04':null;if(id)items.push([this.project(h.x,h.y).y,()=>this.character(h.x,h.y,id)]);}
   const me=this.player;if(Number.isFinite(me.x)&&Number.isFinite(me.y))items.push([this.project(me.x,me.y).y+.01,()=>this.character(me.x,me.y,'player',true,me.path.length>0||this.keys.size>0)]);
   // Painter's order by the y of each thing's feet/base: nobody is drawn on
   // top of a counter they stand behind, or hidden by one they stand before.
   items.push(...this.floorProps());
   items.sort((a,b)=>a[0]-b[0]).forEach(([,draw])=>draw());
 }
 /** Soft ring where a floor tap will take the player. */
 drawMarker(){const m=this.marker;if(!m||this.time>m.until||!Number.isFinite(m.x))return;const c=this.ctx,p=this.project(m.x,m.y),k=Math.max(0,(m.until-this.time)/1.1),pal=this.palette();
   c.save();c.globalAlpha=.35+.5*k;c.strokeStyle=pal.primary;c.lineWidth=3;c.beginPath();c.ellipse(p.x,p.y,18+10*(1-k),6+3*(1-k),0,0,Math.PI*2);c.stroke();c.restore();}
 labels(){const c=this.ctx,p=this.palette(),activeNPC=this.c?.tasks?.find(t=>t.id===this.c.active_task)?.npc;
   for(const h of this.hotspots){const isNPC=h.id.startsWith('npc:'),isStaff=h.id.startsWith('staff:'),hover=this.hover?.id===h.id;
     if(isNPC||isStaff||h.id==='event'||h.id==='officer'){
       // Staff tags show just the name plus a dot (green: on shift); the full
       // status is in the hover label, so neighbouring tags don't collide.
       const staff=isStaff?this.c?.ops?.staff?.find(e=>'staff:'+e.id===h.id):null;
       const pt=this.project(h.x,h.y,141),name=isNPC?this.npcName(h.id.slice(4)):staff?staff.name:h.label,selected=isNPC&&h.id.slice(4)===activeNPC;const w=Math.min(250,Math.max(60,name.length*(this.isPortrait()?10:7)+22+(staff?12:0)));R(c,pt.x-w/2,pt.y-(this.isPortrait()?16:13),w,this.isPortrait()?32:26,selected?p.primary:'#fff9ef',13,selected?p.dark:'#d9bca6',1.5);T(c,name,pt.x+(staff?6:0),pt.y,this.isPortrait()?18:11,selected?'#fffaf2':p.dark);
       if(staff)E(c,pt.x-w/2+13,pt.y,4.5,4.5,this.staffWorking(staff)?'#6fae7c':'#c9b8a6');
     }else if(['workbench','counter','shelf','board','ops:finance'].includes(h.id)){
       const pt=this.project(h.x,h.y,h.z+15),nudge=this.plan().badge?.[h.id];if(nudge){pt.x+=nudge[0];pt.y+=nudge[1];}E(c,pt.x,pt.y,13,13,'#fff9ee');E(c,pt.x,pt.y,9,9,p.light);T(c,'+',pt.x,pt.y,16,p.dark,700);
     }
     if(hover){const pt=this.project(h.x,h.y,h.z+52),w=Math.min(290,h.label.length*7+25);R(c,pt.x-w/2,pt.y-17,w,32,p.dark,12);T(c,h.label,pt.x,pt.y,12,'#fff8ed');}
   }
 }
 hit(pos){if(!this.isPortrait())return super.hit(pos);return this.hotspots.map(h=>({h,d:Math.hypot(pos.x-h.point.x,pos.y-h.point.y)/Math.max(h.range,22/this.scale)})).filter(x=>x.d<1).sort((a,b)=>a.d-b.d)[0]?.h||null;}

 professionBoard(x,y,w,h){const c=this.ctx,p=this.palette();R(c,x-5,y-5,w+10,h+10,'#a27b51',8);R(c,x,y,w,h,'#355847',4);if(this.career==='teacher'){T(c,'HÔM NAY MÌNH CÙNG HỌC',x+w/2,y+24,10,'#fff0c9',800);T(c,'3 + 4 = ?',x+w/2,y+64,30,'#fff7e1',800);for(let i=0;i<7;i++)T(c,'★',x+30+i*27,y+112,21,i<3?'#f1cb73':'#b9d3a9');}else if(this.career==='tour_guide'){R(c,x+9,y+9,w-18,h-18,'#e7e5ba',4);L(c,x+33,y+h-30,x+w-43,y+35,'#a7b981',16);for(const [ix,iy,k] of [[.15,.7,'⚑'],[.4,.5,'★'],[.74,.25,'⚑']]){E(c,x+w*ix,y+h*iy,16,16,'#fff5da');T(c,k,x+w*ix,y+h*iy,20,p.dark);}T(c,'MÂY LANG THANG',x+w/2,y+h-14,11,'#84663e',800);}else{T(c,'MENU HÔM NAY',x+w/2,y+25,18,'#fff5d9',800);for(const [i,l]of ['Trà sữa    ·    Matcha','Hồng trà   ·   Vị trái cây','Trân châu  ·   Bọt mây'].entries())T(c,l,x+w/2,y+57+i*29,12,'#e9e7c4');}}
 portraitRoom(){const c=this.ctx,p=this.palette();
   E(c,350,857,324,23,'#cba88d22');R(c,22,114,656,738,'#e1b594',31);R(c,29,117,642,724,'#fff9ed',26,'#d9ae91',3);R(c,40,139,620,406,p.wall,21);
   R(c,40,506,620,323,'#f6e8d2',15);c.save();c.beginPath();c.roundRect(40,506,620,323,15);c.clip();
   for(let x=40;x<660;x+=62)for(let y=506;y<830;y+=62){c.fillStyle=((x-40)/62+(y-506)/62)%2?'#f3e1c9':'#fff3df';c.fillRect(x,y,62,62);}c.restore();
   R(c,248,211,180,263,'#dec2a0',23);R(c,256,218,164,247,'#c7e5e2',18);E(c,380,250,23,23,'#fff0bb');E(c,287,447,60,34,'#a8cbae');E(c,391,430,36,61,'#b9d8bb');L(c,338,223,338,463,'#fffaf0',7);L(c,262,329,414,329,'#fffaf0',7);R(c,240,467,196,12,'#d8b394',5);
   this.cabinet(62,269,165,166,0);this.cabinet(454,269,181,166,1);
   c.save();c.beginPath();c.roundRect(35,117,630,90,19);c.clip();for(let i=0;i<10;i++){R(c,35+i*63,117,63,66,i%2?'#fff6e8':p.awning,0);E(c,66.5+i*63,184,31.5,15,i%2?'#fff6e8':p.awning);}c.restore();
   if(['teacher','tour_guide','milk_tea'].includes(this.career))this.professionBoard(260,196,190,118);
   R(c,130,41,440,103,'#c79879',31);R(c,135,34,430,103,'#fff9ed',30,'#e7c9ad',3);R(c,145,44,410,82,'#fffaf2',25,'#efdcc0',2);this.mascot(180,83,.56);T(c,p.title,364,76,fit(c,p.title,320,p.title.length>21?23:30,800),p.dark,800);T(c,p.sub,360,110,fit(c,p.sub,330,13),p.dark);heart(c,532,85,.36,p.primary);
   c.strokeStyle='#cfb693';c.lineWidth=2;c.beginPath();c.moveTo(53,195);c.quadraticCurveTo(345,252,643,195);c.stroke();for(let i=0;i<9;i++){const x=60+i*72,y=197+Math.sin(i/8*Math.PI)*27;L(c,x,y,x,y+7,'#c8ad89',1);E(c,x,y+11,4,6,'#ffe5a1');}
   for(let i=0;i<10;i++){E(c,34+Math.sin(i)*9,170+i*24,13,7,i%2?'#a2c596':'#81b095');E(c,665+Math.cos(i)*9,169+i*24,13,7,i%2?'#a2c596':'#81b095');}
   R(c,571,425,65,77,'#c89f7f',9);R(c,577,431,53,65,'#fff7e7',6);T(c,'CHUYỆN',603,449,10,p.dark);T(c,'PHỐ',603,465,14,p.dark);heart(c,603,484,.35,p.primary);
   this.securityProps();
 }
 portraitSecurity(){const c=this.ctx,items=this.c?.ops?.security?.items||[];
   if(items.includes('camera')){L(c,62,255,79,243,'#b89d84',4);R(c,73,231,39,22,'#f4f1e7',6,'#a5a89e',2);E(c,108,242,7,8,'#7a8992');E(c,109,242,3,4,'#b4d9df');}
   if(items.includes('bell')){L(c,638,220,638,232,'#ad9073',2);P(c,[[628,249],[648,249],[645,235],[631,235]],'#f1d189');E(c,638,251,4,3,'#d3ad67');}
   if(items.includes('light')){const g=c.createRadialGradient(629,548,0,629,548,55);g.addColorStop(0,'#ffe2a56a');g.addColorStop(1,'#ffe2a500');c.fillStyle=g;c.fillRect(574,493,110,110);R(c,618,528,23,31,'#fff0bc',6,'#b89b7e',2);}
 }
 portraitCounter(){const c=this.ctx,p=this.palette();E(c,325,642,235,13,'#b795761e');R(c,105,566,440,74,p.mint,16,'#96b8a6',2);R(c,95,553,460,24,'#eac39d',9,'#c2a180',2);R(c,103,557,444,5,'#f7dfc0',2);
   if(this.career==='mother_baby'){R(c,207,531,128,16,'#f1d3dc',6);R(c,228,489,56,45,'#fae7bd',8,'#c8a88a',2);L(c,256,490,256,534,p.primary,6);L(c,230,512,283,512,p.primary,5);E(c,248,486,11,5,p.primary);E(c,266,486,11,5,p.primary);}
   else if(this.career==='pharmacy'){R(c,198,526,137,24,'#f4fbf5',8,'#9db9a9',2);this.tinyItem(234,527,1);this.tinyItem(284,527,2);T(c,'MÃ · LÔ · LƯỢNG',266,540,10,p.dark);}
   else{R(c,201,507,60,42,'#fff9ee',5,'#d3b7a1',1);R(c,210,502,60,42,'#fff9ee',5,'#d3b7a1',1);for(let i=0;i<3;i++)L(c,220,513+i*9,257,513+i*9,i===0?p.primary:'#c0b4a8',2);R(c,285,519,45,31,p.light,6);T(c,this.career==='accounting'?'550':'♡',307,534,14,p.dark);}
   if(this.career==='teacher'){R(c,401,473,132,69,'#fff8dd',5,'#ba9b76',2);T(c,'3 + 4 = 7',468,505,20,p.dark);}else if(this.career==='tour_guide'){R(c,393,476,146,65,'#f6edc8',6,'#b79c73',2);L(c,412,524,522,492,'#8eb68c',8);T(c,'⚑',432,503,22,p.dark);T(c,'⚑',514,490,20,p.dark);}else this.monitor(458,530);this.bobaCup(353,550,.7);
   if((this.c?.ops?.equipment?.condition||100)<100){R(c,113,548,80,14,'#f4d591',4);T(c,'CẦN KIỂM',153,555,10,'#90633e');}
 }
 pet(){this.say('Mrrr… hôm nay tiệm có thêm bạn mới không?');const [x,y]=this.plan().cat;this.ping(x,y-30,'#d790a9');this.petUntil=this.time+4;}
 /** ?navdebug=1 only: walkable cells, footprints, people, approach spots, path. */
 drawNavDebug(){const c=this.ctx,g=this.nav;if(!g)return;c.save();
   const me=this.navCell(this.player.x,this.player.y),main=me>=0&&g.walk[me]?g.comp[me]:g.comp[this.navNearest(this.player.x,this.player.y)];
   for(let k=0;k<g.walk.length;k++){const q=this.navPoint(k),s=this.project(q.x,q.y);c.fillStyle=!g.walk[k]?'rgba(210,40,40,.22)':g.comp[k]===main?'rgba(20,150,60,.6)':'rgba(240,150,0,.8)';c.fillRect(s.x-2,s.y-2,4,4);}
   c.strokeStyle='rgba(200,30,30,.8)';c.lineWidth=1.5;for(const r of this.props||[])c.strokeRect(r[0],r[1],r[2]-r[0],r[3]-r[1]);
   c.setLineDash([5,4]);for(const r of this.props||[])c.strokeRect(r[0]-CLEAR.x,r[1]-CLEAR.y,r[2]-r[0]+2*CLEAR.x,r[3]-r[1]+2*CLEAR.y);c.setLineDash([]);
   c.strokeStyle='rgba(230,120,0,.9)';for(const q of this.people||[]){const s=this.project(q.x,q.y);c.beginPath();c.ellipse(s.x,s.y,q.rx,q.ry,0,0,Math.PI*2);c.stroke();}
   for(const h of this.hotspots)for(const a of h.approach||[]){const s=this.project(a.x,a.y),ok=this.navFree(a.x,a.y);c.fillStyle=ok?'#1d5fd1':'#d11d8a';c.beginPath();c.arc(s.x,s.y,4,0,Math.PI*2);c.fill();}
   const f=this.plan();c.strokeStyle='rgba(20,20,160,.5)';c.setLineDash([8,6]);L(c,f.floor[0],f.line,f.floor[2],f.line,'rgba(20,20,160,.5)',1);c.setLineDash([]);
   const path=[this.player,...(this.player.path||[])];if(path.length>1){c.strokeStyle='#0a0';c.lineWidth=2.5;c.beginPath();path.forEach((q,i)=>{const s=this.project(q.x,q.y);i?c.lineTo(s.x,s.y):c.moveTo(s.x,s.y);});c.stroke();}
   c.restore();}
 draw(){const c=this.ctx;if(!this.width)this.resize();c.setTransform(this.dpr,0,0,this.dpr,0,0);c.fillStyle='#fff6ed';c.fillRect(0,0,this.width,this.height);
   for(let x=14;x<this.width;x+=34)for(let y=14;y<this.height;y+=34)E(c,x,y,1,1,'#dec6b838');
   c.translate(this.offset.x,this.offset.y);c.scale(this.scale,this.scale);this.drawRoom();this.drawFurnitureAndActors();this.labels();
   this.fx?.draw(this); // live happenings (v4/scene-events.js)
   for(const p of this.particles){c.globalAlpha=Math.max(0,p.life/p.max);R(c,p.x,p.y,p.size,p.size,p.color,2);}c.globalAlpha=1;this.drawSpeech();
   if(this.navDebug)this.drawNavDebug();
 }
}
