/** 🛕 Vào chùa: chùa Gió Lành as a place, opened from the "Đi chùa" section of the Đời thường sheet (./chua.js).
 * 15/10 (owner: "tối ưu hết chỗ chùa … đẹp hơn, theo dạng 2.5d trình bày rõ ràng và đẹp"): one 2.5D courtyard drawn
 * like the town map (scenes/chua-iso.js), everything in sight, no rooms to switch: the main hall with its steps (khấn on
 * the mat, the mõ for tụng kinh, thầy Huệ Minh), the bell pavilion, the incense burner, the lotus pond and its bench, the
 * broom rack, the dining table (rằm, mùng 1) and 🌳 Vườn ước nguyện: one tree per wish tree with its newest ribbons.
 * Walk by tapping the ground (drag to look around), or tap a thing to walk up to it; what you walk up to opens right
 * there in the panel (the same panels as before: incense, the bell, khấn — who for, what for —, the chant with the mõ
 * kept on the beat, the people to talk to). A wish tree opens its own dialog (./wish-trees.js): write your wish, hang it.
 * Every rule and gain is game/chua.py (state.chua = chua.public(); jr_chua_do); this file draws and asks.
 * An older server sends no `more`/`khan`/`chant`: ./chua.js then shows no way in (the old button list stays); without
 * `wish_trees` the grove is not drawn and "Lời chúc" is the old card composer.
 * Reduced motion: the player steps straight to where they tapped, nothing sways, the camera does not glide, the chant's
 * ring stays still (the mõ lights up on the beat instead). */
import {icon,escapeHTML as esc} from '../icons.js';
import {cardComposer,cardHistory,cardText,spiritGain,actionDone,actionWhy,createCardBoard,cardBoardHTML,cardBoardTabs,pagodaArt} from './chua.js';
import {loadOlder} from '../archive.js';
import {stylesheet} from '../lazy.js';
import {figure} from './look.js';
import {getCharacterStamp} from '../isometric/character-art.js';
import {audioContext,wantAudio,duck} from '../audio.js';
import {VIEW,IMAGES,PEOPLE,LOOKS,GROVE,plan,route,nearestFree,project,unproject,ground,props,treeBoard,groveSign,npc,E,L,T} from '../scenes/chua-iso.js';

const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');
const S={env:null,dlg:null,cv:null,ctx:null,stage:null,area:'san',port:false,k:1,ox:0,oy:0,dpr:1,cw:0,ch:0,cam:null,pan:null,
  me:{x:0,y:0,path:null,pose:'stand',poseUntil:0,step:0,dir:'se'},arrive:null,fx:{},panel:null,result:'',chant:null,khan:{who:'',what:''},
  card:{recipient:'',blessing:'',name:'',message:'',public:false},board:null,talk:{},raf:0,last:0,drawn:0,time:0,busy:false,bound:false,covered:false,
  view:'',help:false,trees:[],plan:null,planKey:''};
const C=()=>S.env?.api.state?.chua;
const day=()=>({lunar:C()?.lunar|0,feast:!!C()?.feast});
const wishTrees=()=>!!C()?.wish_trees;
/** The courtyard of today (people change with the lunar day; the grove with the trees the server has). */
function pl(){const key=`${day().lunar}|${day().feast}|${S.trees.length}`;if(S.planKey!==key){S.plan=plan(day(),wishTrees()?S.trees:[]);S.planKey=key;}return S.plan;}
const actOf=id=>[...(C()?.acts||[]),...(C()?.more||[])].find(a=>a.id===id)||null;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
/** Can this server take the walkable pagoda? (the fields an older one does not send) */
export const hasScene=c=>!!(c?.enabled&&Array.isArray(c.more)&&c.khan&&c.chant);

/* ---- the town's paintings (the map's own: cached already for most players) ---- */
const IMG={};
function images(){
  for(const [k,src] of Object.entries(IMAGES))if(!IMG[k]){const i=new Image();i.decoding='async';i.onload=()=>{S.drawn=0;};i.src=globalThis.__mnlBoot?.asset?.(src)||src;IMG[k]=i;}
  return IMG;
}

/* ---- the words ---- */
const SHORT={huong:'Lư hương',chuong:'Gác chuông',ngoi:'Hồ sen',nguyen:'Vườn ước nguyện',quet:'Chổi tre',com:'Bàn cơm chay',khan:'Chiếu lễ',tung:'Mõ'};
const LOOK_NAME={bode:'🌳 Cây bồ đề',giatri:'🔔 Chuông gia trì',ban:'🕯️ Bàn thờ',thoikhoa:'📋 Thời khóa',thucdon:'📋 Thực đơn'};
const INTRO={
  huong:'Lư hương lớn giữa sân. Khách thắp hương ở đây, trong điện chỉ một nén.',
  chuong:'Gác chuông có quả chuông đồng cả làng cùng đúc. Chuông thỉnh chậm, đều, chờ tiếng ngân tắt hẳn.',
  ngoi:'Hồ sen nhỏ, mấy con cá đỏ lượn chậm. Ngồi đây gió sông mát lắm.',
  nguyen:'Vườn có nhiều cây ước nguyện. Chọn một cây, viết điều bạn mong rồi treo lên.',
  quet:'Mấy cây chổi tre dựng ở giá. Lá bàng rụng đầy sân.',
  com:'Bàn dài ngoài sân, bà Nhạn đang múc canh nấm.',
  khan:'Bạn quỳ trên chiếu trước điện Phật. Tự chọn khấn cho ai, mong điều gì.',
  tung:'Thầy giữ chuông gia trì, bạn giữ mõ. Gõ đúng lúc vòng sáng khép lại.',
};
/** The visit as four steps in the bar under the scene (one tap walks there); everything else is "Quanh đây". */
const STEPS=[{id:'huong',icon:'🪔',name:'Thắp hương'},{id:'khan',icon:'🙏',name:'Khấn'},{id:'nguyen',icon:'🌳',name:'Ước nguyện'},{id:'tung',icon:'📿',name:'Tụng kinh'}];
const HELP={...INTRO,
  board:'Lời chúc Công khai hiện cho cả phố, kèm tên và lời nhắn. Đổi lại lúc nào cũng được.',
  here:'Chạm sân để đi, kéo để nhìn quanh. Chạm một chỗ để đi tới. Mọi việc ở chùa đều miễn phí và làm lại được.',
  chant:'Thầy gõ ba tiếng mõ mở đầu. Gõ mõ đúng lúc vòng sáng khép lại.'};
const VERB={huong:'🪔 Thắp hương',chuong:'🔔 Đứng nghe chuông',ngoi:'🍃 Ngồi xuống',quet:'🧹 Cầm chổi quét',com:'🍚 Ngồi vào bàn',khan:'🙏 Chắp tay khấn',tung:'📿 Bắt đầu tụng'};
const POSE={huong:'pray',chuong:'pray',ngoi:'sit',nguyen:'pray',quet:'sweep',com:'sit',khan:'kneel',tung:'kneel'};
const NPC={
  na:['Bạn ơi, con cá đỏ to nhất tên là Mập đó. Con đặt tên đấy!','Bà con dặn đi trong chùa phải đi chậm, nói nhỏ. Con đang tập.','Sao hoa sen mọc dưới bùn mà vẫn thơm vậy ta?','Con mới treo điều ước lên cây Học hành đó. Bạn treo chưa?'],
  quyen:['Chiều nào chị cũng ra đây ngồi một lúc. Không cần nói gì cả.','Nghe chuông xong, tự nhiên thấy nhẹ người.','Cứ ngồi đi, ghế còn rộng mà.','Đọc mấy dải lụa trên cây mới thấy ai cũng có điều mong.'],
  bay:['Rằm nào ông cũng lên. Chân yếu rồi, nhưng lên được là vui.','Hồi xưa ông chở đò cho cả xóm qua sông đi chùa đó.','Thắp hương thì một nén thôi con, thành tâm là được.'],
  nhan:['Bữa nay không phải rằm, bà chỉ nhặt rau thôi. Rằm với mùng một ghé ăn cơm chay nhé!','Bếp chùa không dùng hành tỏi, con biết chưa?'],
  nhan_feast:['Ngồi xuống ăn đi con, canh nấm còn nóng!','Ăn chậm thôi. Ăn xong nhớ để chén vô thau giùm bà nha.'],
};
/** The chant: short lines of our own (two mõ beats each), the traditional "Nam mô A Di Đà Phật" around them. */
const CHANT=['Nam mô A Di Đà Phật.','Sáng nay xin lòng yên như mặt hồ.','Lời nói ra, xin là lời hiền.','Việc tay làm, xin là việc lành.','Thương người gần, nhớ người xa.','Nam mô A Di Đà Phật.'];
const PERIOD=.95,LEAD=3,WINDOW=.26;

/* ---- sound: recorded CC0 / public-domain files (public/audio/chua/, credits in public/music/CREDITS.md).
 * Like the wedding party's music, the pagoda's sounds are the place's own: they follow the "Âm thanh" switch and
 * its volume (on by default, unlike the background music) and the 🔊 in the pagoda's header (kept per device);
 * the courtyard's quiet loop plays meanwhile and the game's own music steps aside (audio.js duck).
 * Fetched only once the pagoda is open (the loop, the rest when its spot is reached), decoded at 32 kHz like the
 * music, freed when the pagoda closes; nothing plays before a tap has started the page's audio, no loop on a
 * data-saving connection. */
const FILES={bell:'chuong-dai-hong-2.mp3',mo:'mo-1.mp3',bowl:'chuong-gia-tri.mp3',voice:'su-tung-kinh.mp3'};
const LOOPS={san:['nen-chua-sang.mp3',.5]};
const NEEDS={chuong:['bell'],khan:['bowl'],huong:['bowl'],nguyen:['bowl'],tung:['mo','bowl','voice']};
const soundUrl=f=>globalThis.__mnlBoot?.asset?.(`/audio/chua/${f}`)||`/audio/chua/${f}`;
const settings=()=>S.env?.api.state?.settings||{};
const QUIET_KEY='mnl.chua.quiet';
let quiet=false;try{quiet=localStorage.getItem(QUIET_KEY)==='1';}catch{/* storage blocked */}
const sfxOn=()=>settings().sound!==false&&!quiet;
const musicOn=()=>sfxOn()&&!globalThis.navigator?.connection?.saveData;
const BUF=new Map();   // file → Promise<AudioBuffer|null>
function decode32(data,c){
  const OAC=globalThis.OfflineAudioContext||globalThis.webkitOfflineAudioContext;
  let dec=c;try{if(OAC)dec=new OAC(1,1,32000);}catch{/* rate not supported: the page context */}
  return new Promise((ok,no)=>{const p=dec.decodeAudioData(data,ok,no);p?.catch?.(()=>{/* no() had it */});});
}
function bufOf(f){
  let p=BUF.get(f);
  if(!p){const c=audioContext();if(!c||!globalThis.fetch)return Promise.resolve(null);
    p=fetch(soundUrl(f),{credentials:'same-origin'}).then(r=>r.ok?r.arrayBuffer():null).then(b=>b&&decode32(b,c)).catch(()=>null);BUF.set(f,p);}
  return p;
}
/** Fetch what a spot will play (when the player reaches it). */
function prefetch(id){for(const n of NEEDS[id]||[])if(n==='voice'?musicOn():sfxOn())bufOf(FILES[n]);}
function start(buf,c,vol,when,loop=false,fade=0){
  const src=c.createBufferSource(),g=c.createGain();src.buffer=buf;src.loop=loop;
  if(fade){g.gain.setValueAtTime(0,when);g.gain.linearRampToValueAtTime(vol,when+fade);}else g.gain.value=vol;
  src.connect(g).connect(c.destination);src.start(when);return {src,g};
}
/** A one-shot (bell, mõ, bowl), `delay` s from now. */
function sfx(name,vol=1,delay=0){
  if(!sfxOn()||!S.dlg?.open)return;
  const c=audioContext();if(!c||c.state!=='running')return;
  const when=c.currentTime+delay,v=vol*Math.max(0,Math.min(1.5,(settings().sfxVolume??70)/70));
  bufOf(FILES[name]).then(buf=>{if(buf&&S.dlg?.open)try{start(buf,c,v,Math.max(c.currentTime,when));}catch{/* audio gone */}});
}
const musicVol=()=>Math.max(0,Math.min(1,(settings().sfxVolume??70)/70));
function fadeOut(x,c,sec=.5){if(!x||!c)return;try{const t=c.currentTime;x.g.gain.cancelScheduledValues(t);x.g.gain.setValueAtTime(x.g.gain.value,t);x.g.gain.linearRampToValueAtTime(0,t+sec);x.src.stop(t+sec+.05);}catch{/* stopped */}}
const LOOP={key:'',cur:null};
/** The courtyard's quiet loop (null: none), faded in and out. */
function ambience(area){
  const want=area&&S.dlg?.open&&musicOn()?LOOPS[area]||LOOPS.san:null,key=want?want.join('|'):'';
  if(key===LOOP.key)return;LOOP.key=key;
  const c=audioContext(),old=LOOP.cur;
  LOOP.cur=null;fadeOut(old,c,1.6);
  if(!want||!c){duck('chua',false);return;}
  duck('chua',true);
  bufOf(want[0]).then(buf=>{if(!buf||LOOP.key!==key||!S.dlg?.open)return;try{const x=start(buf,c,want[1]*musicVol(),c.currentTime+.05,true,1.6);LOOP.cur={...x,file:want[0]};}catch{/* no audio */}});
}
const VOICE={cur:null};
/** Thầy's voice under the chant (on with the first beat, faded out after the last). */
function voice(on,at=0){
  const c=audioContext();
  if(!on){fadeOut(VOICE.cur,c,1.2);VOICE.cur=null;return;}
  if(!musicOn()||!c||c.state!=='running')return;
  const when=c.currentTime+Math.max(0,at);
  bufOf(FILES.voice).then(buf=>{if(!buf||S.chant?.state!=='run')return;try{VOICE.cur=start(buf,c,.55*musicVol()+.15,Math.max(c.currentTime,when),false,1.2);}catch{/* no audio */}});
}

/* ---- dialog ---- */
function dialog(){
  if(S.dlg)return S.dlg;
  const d=document.createElement('dialog');
  d.className='sheet v4-sheet cv-sheet';d.setAttribute('aria-labelledby','cvTitle');
  d.innerHTML=`<div class="cv-root"><header class="cv-head">${pagodaArt(34,'cv-logo')}<div class="grow"><h2 id="cvTitle">Chùa Gió Lành</h2><p class="cv-day"></p></div>
      <button type="button" class="btn ghost small cv-donate" data-cv="donate" hidden><span aria-hidden="true">🪷</span><span class="cv-donate-t">Công đức</span></button>
      <button type="button" class="icon-btn cv-mute" data-cv="mute" aria-label="Tiếng chùa" aria-pressed="true"></button>
      <button type="button" class="icon-btn" data-cv="close" aria-label="Ra về">${icon('x',20)}</button></header>
    <div class="cv-stage"><canvas class="cv-canvas" tabindex="0" role="img" aria-label="Sân chùa Gió Lành"></canvas>
      <p class="cv-hint" aria-hidden="true">Chạm sân để đi · kéo để nhìn quanh</p><div class="cv-panel" role="region" aria-label="Ở đây" hidden></div></div>
    <nav class="cv-path" aria-label="Các bước đi lễ"></nav></div>`;
  document.body.append(d);
  S.stage=d.querySelector('.cv-stage');S.cv=d.querySelector('canvas');S.ctx=S.cv.getContext('2d');
  d.addEventListener('click',e=>{const el=e.target.closest('[data-cv]');if(!el||!d.contains(el)||el.disabled)return;e.preventDefault();act(el.dataset.cv,el.dataset);});
  d.addEventListener('pointerdown',e=>{if(e.target.closest('.cv-mo')){e.preventDefault();tapMo();}});
  d.addEventListener('keydown',e=>{if(S.chant?.state==='run'&&(e.key===' '||e.key==='Enter')){e.preventDefault();tapMo();}});
  d.addEventListener('close',onClose);
  d.addEventListener('input',e=>{const field=e.target.dataset?.cardField;if(field!=='name'&&field!=='message')return;S.card[field]=e.target.value;liveTag();});
  // a tap walks (or goes to what it hits); a drag looks around (the camera stays there until the next walk)
  let down=null;
  S.cv.addEventListener('pointerdown',e=>{down={x:e.clientX,y:e.clientY,t:performance.now(),drag:false,id:e.pointerId};});
  S.cv.addEventListener('pointermove',e=>{if(!down||down.id!==e.pointerId)return;const dx=e.clientX-down.x,dy=e.clientY-down.y;
    if(!down.drag&&Math.hypot(dx,dy)>12){down.drag=true;try{S.cv.setPointerCapture(e.pointerId);}catch{/* gone */}S.pan=S.pan||[0,0];down.base=[...S.pan];down.x0=e.clientX;down.y0=e.clientY;}
    if(down.drag){S.pan=[down.base[0]-(e.clientX-down.x0)/S.k,down.base[1]-(e.clientY-down.y0)/S.k];hinted();S.drawn=0;}});
  const up=e=>{const d0=down;down=null;if(!d0||d0.drag||e.type!=='pointerup')return;if(Math.hypot(e.clientX-d0.x,e.clientY-d0.y)>14||performance.now()-d0.t>800)return;tapAt(e.clientX,e.clientY);};
  S.cv.addEventListener('pointerup',up);S.cv.addEventListener('pointercancel',up);
  S.cv.addEventListener('keydown',e=>{if(S.covered)return;const k={arrowleft:[-.7,.7],a:[-.7,.7],arrowright:[.7,-.7],d:[.7,-.7],arrowup:[-.7,-.7],w:[-.7,-.7],arrowdown:[.7,.7],s:[.7,.7]}[e.key.toLowerCase()];if(!k)return;e.preventDefault();closePanel();walkTo([S.me.x+k[0],S.me.y+k[1]]);});
  let sizing=0;new ResizeObserver(()=>{cancelAnimationFrame(sizing);sizing=requestAnimationFrame(size);}).observe(S.stage);
  S.dlg=d;return d;
}
function bind(){
  if(S.bound)return;S.bound=true;
  S.env.api.addEventListener('state',()=>{if(!S.dlg?.open)return;S.drawn=0;head();path();if(!S.covered)ambience(S.area);if(S.panel&&!S.result&&S.chant?.state!=='run'&&!S.dlg.contains(document.activeElement?.closest?.('.cv-card-compose')))panel();});
}
/** The wish trees for the grove (names, counts, newest ribbons): game/chua_wish.py through ./wish-trees.js. */
async function loadTrees(){
  if(!wishTrees())return;
  try{const {fetchTrees}=await import('./wish-trees.js');const d=await fetchTrees(S.env.api);if(d?.trees){S.trees=d.trees;S.drawn=0;}}
  catch{/* the grove waits for the next open */}
}
/** Open the pagoda (from ./chua.js's "Vào chùa"); comes in through the gate. */
export async function openChua(env){
  S.env=env;bind();await stylesheet('/css/chua.css');
  if(!hasScene(C()))return;
  images();
  S.card.public=false;S.board=C().sharing?createCardBoard(S.env.api,refreshBoard):null;
  const d=dialog();
  S.panel=null;S.result='';S.view='';S.help=false;S.chant=null;S.khan={who:'',what:''};S.fx={};S.me.pose='stand';S.me.path=null;S.arrive=null;S.pan=null;S.stage?.classList.remove('hinted');
  if(!d.open)d.showModal();
  const toasts=document.getElementById('toasts');if(toasts)d.append(toasts);   // errors show over the scene
  size();place(pl().entry);S.me.dir='sw';lookAt(FIRST_LOOK);head();path();panel();
  loadTrees();
  if(!wishTrees())S.board?.load('mine');   // the old "Chia sẻ" knows whether a card is already public
  wantAudio('chua',true);ambience(S.area);
  S.cv.focus({preventScroll:true});
  S.last=performance.now();cancelAnimationFrame(S.raf);S.raf=requestAnimationFrame(loop);
}
function onClose(){
  cancelAnimationFrame(S.raf);S.raf=0;S.chant=null;voice(false);ambience(null);wantAudio('chua',false);BUF.clear();
  const toasts=document.getElementById('toasts'),sheet=document.getElementById('sheet');if(toasts)(sheet?.open?sheet:document.body).append(toasts);
  S.env?.renderSheet?.(false);
}

/* ---- layout: the camera ---- */
function size(){
  if(!S.stage)return;
  const r=S.stage.getBoundingClientRect(),cw=Math.max(1,r.width),ch=Math.max(1,r.height);
  S.port=cw/ch<.95;S.dpr=Math.min(2,globalThis.devicePixelRatio||1);S.cw=cw;S.ch=ch;
  S.cv.width=Math.round(cw*S.dpr);S.cv.height=Math.round(ch*S.dpr);
  S.cam=null;view(0);S.drawn=0;
}
/** Scale and offset: the whole courtyard when it fits legibly (a wide screen); on a phone a closer view (never below
 * MIN_K) that follows the player (or where a drag looked), and keeps them above the panel when the panel spans it. */
const MIN_K=.62;
function view(dt){
  const [x0,y0,x1,y1]=VIEW,vw=x1-x0,vh=y1-y0,cw=S.cw,ch=S.ch;if(!cw)return;
  const box=S.dlg?.querySelector('.cv-panel'),open=box&&!box.hidden,wide=open&&box.offsetWidth>cw*.8,avail=open&&!wide?Math.max(cw*.4,box.offsetLeft-8):cw;
  const band=wide?Math.max(ch*.3,box.offsetTop-6):ch;
  const k=Math.max(MIN_K,Math.min(cw/vw,ch/vh),S.port?Math.min(1,ch/vh*1.05):0);   // the zoom does not jump when a panel opens
  const me=project(S.me.x,S.me.y),want=[me[0]+(S.pan?.[0]||0),me[1]-50+(S.pan?.[1]||0)];
  if(!S.cam||still()||!dt||S.pan)S.cam=want;else{const a=Math.min(1,dt*4);S.cam=[S.cam[0]+(want[0]-S.cam[0])*a,S.cam[1]+(want[1]-S.cam[1])*a];}
  const fitX=vw*k<=avail,fitY=vh*k<=band;
  S.k=k;
  const tx=fitX?(avail-vw*k)/2-x0*k:Math.min(-x0*k,Math.max(avail-x1*k,avail/2-S.cam[0]*k));
  const ty=fitY?(band-vh*k)/2-y0*k:Math.min(-y0*k,Math.max(band-y1*k,band/2-S.cam[1]*k));
  if(S.pan){   // a drag past the courtyard's edge goes no further
    const cx=fitX?null:(avail/2-tx)/k,cy=fitY?null:(band/2-ty)/k;
    if(cx!==null&&Math.abs(cx-want[0])>2)S.pan[0]+=cx-want[0];if(cy!==null&&Math.abs(cy-want[1])>2)S.pan[1]+=cy-want[1];
  }
  if(still()||!dt||S.pan){S.ox=tx;S.oy=ty;}else{const a=Math.min(1,dt*6);S.ox+=(tx-S.ox)*a;S.oy+=(ty-S.oy)*a;}
}
/** The first view: the grove and the hall's steps together (the player stands at the gate, a tap walks in). */
const FIRST_LOOK=[-90,250];
/** Point the camera at a scene point (as a drag would); the next walk brings it back to the player. */
function lookAt([sx,sy]){const m=project(S.me.x,S.me.y);S.pan=[sx-m[0],sy-(m[1]-50)];S.cam=null;view(0);S.drawn=0;}
function place(p){const q=nearestFree(pl(),p)||p;S.me.x=q[0];S.me.y=q[1];S.me.path=null;}
/** A point of the canvas (client px) in scene px. */
const toScene=(cx,cy)=>{const r=S.cv.getBoundingClientRect();return [(cx-r.left-S.ox)/S.k,(cy-r.top-S.oy)/S.k];};

/* ---- moving ---- */
function stand(){if(S.me.pose!=='stand'){S.me.pose='stand';S.me.poseUntil=0;}}
function walkTo(p,then=null){
  if(S.covered||S.chant?.state==='run')return;
  stand();S.pan=null;const path=route(pl(),[S.me.x,S.me.y],p);
  if(!path){S.arrive=null;S.me.path=null;return;}
  S.arrive=then;
  if(!path.length||still()){const end=path[path.length-1]||[S.me.x,S.me.y];S.me.x=end[0];S.me.y=end[1];S.me.path=null;S.drawn=0;arrived();return;}
  S.me.path=path;
}
/** The first tap or drag hides "Chạm sân để đi · kéo để nhìn quanh". */
function hinted(){S.stage?.classList.add('hinted');}
function arrived(){const f=S.arrive;S.arrive=null;S.me.path=null;if(f)f();}
function tapAt(cx,cy){
  if(S.covered||S.chant?.state==='run')return;
  hinted();
  const p=toScene(cx,cy),spot=hitSpot(p);
  if(spot){goSpot(spot);return;}
  closePanel();walkTo(unproject(p[0],p[1]));
}
/** The spot under a scene point: the thing itself (lifted above its foot), its badge, or a tree's name board. */
function hitSpot(p){
  let best=null,bd=Infinity;const ls=labelScale();
  for(const s of pl().spots){if(!s.r)continue;const a=project(...s.at),d=Math.min(Math.hypot(a[0]-p[0],a[1]-s.lift-p[1]),s.kind==='tree'?Math.hypot((a[0]-p[0])*.6,(a[1]+8+12*ls)-p[1])*1.2:Infinity);
    if(d<=s.r&&d<bd){bd=d;best=s;}}
  return best;
}
function goSpot(s,view=''){
  if(!s)return;closePanel();
  walkTo(s.stand,()=>{
    S.me.dir=faceTo(s.at);
    if(s.kind==='tree'){openTree(s.tree);return;}
    if(s.kind==='grove'&&wishTrees()){openTree('');return;}
    S.panel=s.kind==='grove'?{...s,kind:'act'}:s;S.result='';S.view=view;if(s.kind==='npc')S.talk[s.who]=S.talk[s.who]??0;if(s.act)prefetch(s.act);panel();
    if(s.act==='nguyen'&&S.board&&!wishTrees())S.board.load(S.board.tab);
  });
}
/** The four facings of the town's character (sw, se, nw, ne) toward a world point. */
function faceTo(q){const dx=q[0]-S.me.x,dy=q[1]-S.me.y,sx=dx-dy,sy=dx+dy;return sy<0?(sx<0?'nw':'ne'):(sx<0?'sw':'se');}
function goTo(id,view=''){
  if(S.covered||S.chant?.state==='run')return;
  const s=pl().spots.find(q=>q.id===id);if(s)goSpot(s,view);
}
/** 🌳 A wish tree (or the whole garden: tree ''): its own dialog over the pagoda; the grove refreshes after. */
async function openTree(tree){
  if(S.covered)return;
  S.covered=true;S.me.pose='pray';
  try{const m=await import('./wish-trees.js');
    const ok=await m.openWishTrees({...S.env,onClose:()=>{S.covered=false;stand();S.last=performance.now();S.drawn=0;if(S.dlg?.open){loadTrees();S.cv.focus({preventScroll:true});}}},tree?{tree}:{});
    if(!ok){S.covered=false;stand();}}
  catch(error){S.covered=false;stand();S.env.toast?.(error.message||'Chưa mở được vườn ước nguyện.',true);}
}

/* ---- the header, the step bar ---- */
function head(){
  const c=C();if(!c||!S.dlg)return;
  const m=S.dlg.querySelector('.cv-mute'),on=settings().sound!==false&&!quiet;
  S.dlg.querySelector('.cv-donate').hidden=typeof S.env.onDonate!=='function';
  m.innerHTML=icon(on?'volume':'mute',20);m.setAttribute('aria-pressed',String(on));m.disabled=settings().sound===false;
  m.title=settings().sound===false?'Âm thanh đang tắt trong Cài đặt':on?'Tắt tiếng chùa':'Bật tiếng chùa';
  const sp=Math.max(0,Math.min(100,c.spirit|0));
  S.dlg.querySelector('.cv-day').innerHTML=`<span>${esc(c.label||'')}</span>${c.feast?' · <span>🍚 cơm chay</span>':''}<span class="cv-spirit" title="Tinh thần ${sp}/100"><span class="cv-meter" aria-hidden="true"><i style="width:${sp}%"></i></span><span>Tinh thần ${sp}</span></span>`;
}
function spotName(s){
  if(s.kind==='npc')return `${PEOPLE[s.who].icon} ${PEOPLE[s.who].name}`;
  if(s.kind==='look')return LOOK_NAME[s.look]||'👀';
  if(s.kind==='tree'){const t=S.trees.find(x=>x.id===s.tree);return t?`${t.emoji} Cây ${t.name}`:'🌳';}
  const a=actOf(s.act);return `${s.kind==='grove'?'🌳':a?.emoji||'•'} ${SHORT[s.act]||a?.name||''}`;
}
/** A step is done once today (repeatable anyway). */
function stepDone(id){return !!actOf(id)?.done;}
const nextStep=(skip='')=>STEPS.find(x=>x.id!==skip&&!stepDone(x.id))||null;
function path(){
  const bar=S.dlg?.querySelector('.cv-path');if(!bar)return;
  const cur=nextStep(),here=S.panel?.kind==='act'?S.panel.act:'';
  bar.innerHTML=`<ol class="cv-steps">${STEPS.map(x=>{const done=stepDone(x.id),on=here===x.id&&S.view!=='board';
    return `<li><button type="button" class="cv-step${done?' done':''}${cur?.id===x.id?' next':''}${on?' on':''}" data-cv="step" data-id="${x.id}"${on?' aria-current="step"':''}><span class="cv-step-ico" aria-hidden="true">${x.icon}${done?'<i>✓</i>':''}</span><span class="cv-step-name">${esc(x.name)}</span></button></li>`;}).join('')}</ol>
    <button type="button" class="cv-step cv-more${S.panel?.kind==='here'?' on':''}" data-cv="here"><span class="cv-step-ico" aria-hidden="true">🧭</span><span class="cv-step-name">Quanh đây</span></button>`;
}
/** "Quanh đây": every place in the courtyard, one tap walks there; the old card board when the player has cards. */
function hereBody(){
  const spots=pl().spots.filter(s=>s.kind!=='tree');
  const old=(C()?.cards||[]).length>0&&S.board?`<button type="button" class="cv-spot" data-cv="board">📜 Bảng lời chúc cũ</button>`:'';
  return top('🧭','Quanh đây','🌿 Sân chùa',HELP.here)+`<div class="cv-tiles">${spots.map(s=>{const a=s.kind==='act'?actOf(s.act):null,done=actionDone(C(),a)||!!a?.done;
    return `<button type="button" class="cv-spot${done?' done':''}" data-cv="spot" data-id="${esc(s.id)}">${esc(spotName(s))}${done?' <i aria-label="đã làm">✓</i>':''}</button>`;}).join('')}${old}</div>`;
}

/* ---- the panel: what happens here ---- */
function gain(a){
  if(a.id==='tung')return C()?.unlimited?`tinh thần +${spiritGain(C(),1)}…+${spiritGain(C(),4)} theo nhịp mõ`:'tinh thần +1…+4 theo nhịp mõ';
  const out=[];if(a.spirit)out.push(`tinh thần +${spiritGain(C(),a.spirit)}`);if(a.wake)out.push(`tỉnh táo +${a.wake}`);if(a.full)out.push(`no bụng +${a.full}`);
  return out.join(' · ');
}
const top=(emoji,title,sub='',help='')=>`<div class="cv-p-head"><span class="cv-p-emoji" aria-hidden="true">${emoji}</span><div class="grow"><b>${esc(title)}</b>${sub?`<small>${esc(sub)}</small>`:''}</div>
  ${help?`<button type="button" class="icon-btn small cv-q-btn" data-cv="help" aria-expanded="${S.help}" aria-label="Giải thích">?</button>`:''}<button type="button" class="icon-btn small" data-cv="shut" aria-label="Đóng">${icon('x',16)}</button></div>
  ${help&&S.help?`<p class="cv-help">${esc(help)}</p>`:''}`;
const why=a=>actionWhy(C(),a);
const main=(html,cv,data='',off=false)=>`<div class="cv-p-acts"><button type="button" class="btn primary big full" data-cv="${cv}"${data}${off?' disabled':''}>${html}</button></div>`;
function actBody(a){
  const no=why(a),note=no?`<p class="cv-why">${esc(no)}</p>`:'';
  if(a.id==='nguyen'&&C().card_choices)return note+cardComposer(C().card_choices,S.card,a.ok,!!S.board);
  if(a.id==='nguyen')return note+`<div class="cv-chips">${(C().wishes||[]).map(w=>`<button type="button" class="cv-pick" data-cv="do" data-act="nguyen" data-wish="${esc(w.id)}"${a.ok?'':' disabled'}>📜 ${esc(w.text)}</button>`).join('')}</div>`;
  if(a.id==='khan')return khanBody(a,note);
  if(a.id==='tung')return (a.ok?'':`<p class="cv-why">${esc(no)} · vẫn tụng cùng thầy được, chỉ không tính thêm.</p>`)+main(VERB.tung,'chant');
  return note+main(VERB[a.id]||esc(a.name),'do',` data-act="${esc(a.id)}"`,!a.ok);
}
/** Khấn, one question at a time: who for → what for (only what fits) → the prayer, read back before kneeling. */
function khanBody(a,note){
  const K=C().khan,who=K.who.find(w=>w.id===S.khan.who),what=who?K.what.find(w=>w.id===S.khan.what&&who.what.includes(w.id)):null;
  const pick=(kind,w)=>`<button type="button" class="cv-pick" data-cv="${kind}" data-id="${esc(w.id)}" aria-pressed="false"${a.ok?'':' disabled'}>${esc(w.text)}</button>`;
  const back='<button type="button" class="cv-crumb" data-cv="khan-back" aria-label="Quay lại">‹</button>';
  const dots=n=>`<span class="cv-dots" aria-hidden="true">${[1,2,3].map(i=>`<i${i<=n?' class="on"':''}></i>`).join('')}</span>`;
  if(!who)return note+`${dots(1)}<h4 class="cv-q">Khấn cho ai?</h4><div class="cv-chips grid">${K.who.map(w=>pick('who',w)).join('')}</div>`;
  if(!what)return note+`${dots(2)}<h4 class="cv-q">${back}Mong <b>${esc(who.text)}</b>…</h4><div class="cv-chips">${K.what.filter(w=>who.what.includes(w.id)).map(w=>pick('what',w)).join('')}</div>`;
  return note+`${dots(3)}<div class="cv-q-row">${back}<p class="cv-prayer"><span>“${esc(`Con cầu mong ${who.text} ${what.text}.`)}”</span></p></div>`+main(VERB.khan,'do',' data-act="khan"',!a.ok);
}
function talkBody(who){
  const p=PEOPLE[who],lines=who==='thay'?(C().abbot||[]):who==='nhan'&&C().feast?NPC.nhan_feast:NPC[who]||[];
  const i=(S.talk[who]|0)%Math.max(1,lines.length),line=lines[i]||'';
  const more=who==='thay'?`<div class="cv-p-acts"><button type="button" class="btn primary big full" data-cv="tothemo">📿 Xin tụng kinh cùng thầy</button></div>
      <div class="cv-p-sub"><button type="button" class="btn ghost small" data-cv="talk" data-who="thay">Con nghe thêm</button><button type="button" class="btn ghost small" data-cv="bye" data-who="thay">🙏 Chào thầy</button></div>`
    :`<div class="cv-p-sub"><button type="button" class="btn ghost small" data-cv="talk" data-who="${esc(who)}">Nói chuyện thêm</button><button type="button" class="btn ghost small" data-cv="shut">Chào</button></div>`;
  return top(p.icon,p.name,p.role)+`<blockquote class="cv-line">${esc(line)}</blockquote>${more}`;
}
function boardBody(){
  const a=actOf('nguyen');
  return top('📖','Bảng lời chúc','',HELP.board)+(S.board?cardBoardHTML(S.board,C().card_choices,true):cardHistory(C()))+
    (a&&!wishTrees()?main('📜 Viết lời chúc','compose'):'');
}
function panel(){
  const box=S.dlg?.querySelector('.cv-panel');if(!box)return;
  const s=S.panel;
  if(!s){box.hidden=true;box.innerHTML='';S.stage.classList.remove('has-panel');path();return;}
  let html='';
  if(S.chant)html=chantHTML();
  else if(S.result)html=S.result;
  else if(s.kind==='here')html=hereBody();
  else if(s.kind==='board')html=boardBody();
  else if(s.kind==='npc')html=talkBody(s.who);
  else if(s.kind==='look')html=top('👀',spotName(s).replace(/^\S+\s/,''))+`<p class="cv-look">${esc(LOOKS[s.look]||'')}</p>`;
  else if(s.act==='nguyen'&&S.view==='board')html=boardBody();
  else{const a=actOf(s.act);if(!a){closePanel();return;}
    html=top(a.emoji,a.name,gain(a),HELP[a.id]||'')+actBody(a);}
  const kind=S.chant?'chant':S.result?'result':s.kind==='board'||s.kind==='act'&&S.view==='board'?'board':s.kind;
  box.innerHTML=html;box.hidden=false;box.dataset.kind=kind;S.stage.classList.add('has-panel');
  if(S.chant)S.chant.el=null;
  path();
}
function closePanel(){if(S.chant?.state==='run')return;S.panel=null;S.result='';S.view='';S.help=false;S.chant=null;stand();panel();}
/** What came of it: the place's words on a paper slip, then one main button (the next step of the visit, or Xong). */
function showResult(emoji,title,text,body=null,opt={}){
  const a=S.panel?.kind==='act'?actOf(S.panel.act):null,next=a?nextStep(a.id):null;
  const again=C()?.unlimited&&a?.ok?`<button type="button" class="btn ghost small" data-cv="again">${a.id==='nguyen'?'Viết thêm':'Làm lần nữa'}</button>`:'';
  const go=opt.main||(next?`<button type="button" class="btn primary big full" data-cv="step" data-id="${next.id}">Tiếp: ${next.icon} ${esc(next.name)} ›</button>`:'<button type="button" class="btn primary big full" data-cv="shut">Xong</button>');
  S.result=top(emoji,title,opt.gain||'')+`<div class="cv-done">${body??`<p class="cv-result">${esc(text)}</p>`}</div><div class="cv-p-acts">${go}</div>${again||opt.main||next||opt.sub?`<div class="cv-p-sub">${again}${opt.sub||''}${opt.main||next?'<button type="button" class="btn ghost small" data-cv="shut">Xong</button>':''}</div>`:''}`;
  panel();
}
/** The card preview follows the name and message as they are typed (no re-render: the field keeps its focus). */
function liveTag(){
  const tag=S.dlg?.querySelector('.cv-tag-live');if(!tag)return;
  const who=tag.querySelector('[data-tag="who"]'),dflt=tag.querySelector('[data-tag="who-default"]'),msg=tag.querySelector('[data-tag="msg"]');
  if(who)who.textContent=S.card.name.trim();if(dflt)dflt.hidden=!!S.card.name.trim();if(msg)msg.textContent=S.card.message.trim();
}
async function shareCard(id){
  const b=S.board;if(!b||b.busy||!id)return;
  if(!b.mine.rows.some(r=>r.id===id))await b.load('mine');
  if(await b.setPublic({id},true)&&S.dlg?.open&&S.panel?.act==='nguyen'){S.result='';S.view='board';b.tab='public';panel();}
}
function refreshBoard(board){
  if(S.board!==board||!S.dlg?.open)return;
  path();if(S.panel?.act!=='nguyen'&&S.panel?.kind!=='board')return;
  const box=S.dlg.querySelector('.cv-card-board');if(box)box.outerHTML=cardBoardHTML(board,C().card_choices,box.dataset.withTabs==='true');
  for(const tabs of S.dlg.querySelectorAll('.cv-card-tabs'))tabs.outerHTML=cardBoardTabs(board);
}
async function readOlderCards(){
  const pending=loadOlder(S.env.api,'','chua.cards',C()?.cards?.length||0);S.result='';S.view='board';panel();
  try{await pending;if(S.dlg?.open)panel();}
  catch(error){if(S.dlg?.open)showResult('📜','Bảng lời chúc',error.message||'Chưa tải được bảng cũ. Bạn thử lại nhé.');}
}
async function donate(){
  if(S.covered||S.chant?.state==='run'||S.busy||!S.env.onDonate)return;
  S.covered=true;ambience(null);wantAudio('chua',false);
  try{await S.env.onDonate();}
  finally{S.covered=false;if(S.dlg?.open){S.last=performance.now();S.drawn=0;wantAudio('chua',true);ambience(S.area);S.cv.focus({preventScroll:true});}}
}

/* ---- doing ---- */
async function doAct(id,extra={}){
  const a=actOf(id);if(!a?.ok||S.busy)return;
  const got=id==='tung'?'':gain(a);
  S.busy=true;S.me.pose=POSE[id]||'pray';S.me.poseUntil=0;
  if(id==='huong')S.fx.lit=S.time+6;
  if(id==='chuong'){S.fx.bell=S.time+4;sfx('bell',.8);}
  if(id==='khan')sfx('bowl',.7);
  const box=S.dlg.querySelector('.cv-panel .cv-p-acts');if(box)box.innerHTML='<p class="cv-wait" aria-live="polite"><span class="cv-wait-dots" aria-hidden="true"><i></i><i></i><i></i></span></p>';
  try{
    const [r]=await Promise.all([S.env.cmd('jr_chua_do',{act:id,...extra},{quiet:true}),sleep(still()?0:900)]);
    if(r?.message){
      if(id==='huong'||id==='nguyen')sfx('bowl',.35);
      const spirit=a.spirit&&spiritGain(C(),a.spirit);if(spirit&&!still())S.fx.gain={until:S.time+2.4,text:`✨ +${a.spirit}`};
      const card=id==='nguyen'?C()?.cards?.at(-1):null;
      if(card){
        const shared=r.chua_card?.public===true,share=S.board&&!shared?`<button type="button" class="btn primary big full" data-cv="share" data-id="${esc(card.id)}">💌 Chia sẻ lên bảng chung</button>`:'';
        showResult(a.emoji,'Đã treo lời chúc',r.message,`<figure class="cv-tag cv-result"><span class="cv-tag-knot" aria-hidden="true"></span><b>${cardText(card,C().card_choices)}</b><figcaption>${shared?'🌏 Công khai':'🔒 Chỉ mình tôi'}</figcaption></figure>`,{gain:got,main:share,sub:'<button type="button" class="btn ghost small" data-cv="board">📖 Bảng</button>'});
      }else showResult(a.emoji,a.name,r.message,null,{gain:got});
    }else{stand();panel();}
    if(id==='khan')S.khan={who:'',what:''};
    if(id==='nguyen'&&r?.message){S.card={...S.card,recipient:'',blessing:'',name:'',message:'',public:false};S.drawn=0;if(S.board){S.board.load('mine');S.board.load('public');}}
  }finally{S.busy=false;}
  if(id==='huong'||id==='nguyen'||id==='chuong')S.me.poseUntil=S.time+3;
}
function act(kind,data){
  if(S.covered)return;
  switch(kind){
    case'close':S.dlg.close();return;
    case'mute':quiet=!quiet;try{localStorage.setItem(QUIET_KEY,quiet?'1':'0');}catch{/* storage blocked */}
      if(quiet){voice(false);ambience(null);}else ambience(S.area);head();return;
    case'donate':donate().catch(error=>S.env.toast?.(error.message,true));return;
    case'spot':goSpot(pl().spots.find(s=>s.id===data.id));return;
    case'shut':closePanel();return;
    case'help':S.help=!S.help;panel();return;
    case'note':{const n=S.dlg.querySelector('.cv-card-note'),el=S.dlg.querySelector('[data-cv="note"]');if(n){n.hidden=!n.hidden;el?.setAttribute('aria-expanded',String(!n.hidden));}return;}
    case'here':if(S.panel?.kind==='here'){closePanel();return;}if(S.chant?.state==='run')return;closePanel();S.panel={id:'here',kind:'here'};panel();return;
    case'step':goTo(data.id);return;
    case'board':S.view='board';S.result='';S.help=false;if(S.panel?.kind==='here'||!S.panel)S.panel={id:'board',kind:'board'};panel();S.board?.load(S.board.tab);return;
    case'compose':S.view='';S.result='';S.help=false;panel();return;
    case'share':shareCard(data.id).catch(error=>S.env.toast?.(error.message,true));return;
    case'card-back':if(S.card.blessing)S.card.blessing='';else S.card.recipient='';panel();return;
    case'khan-back':if(S.khan.what)S.khan.what='';else S.khan.who='';panel();return;
    case'again':S.result='';stand();panel();return;
    case'older-cards':readOlderCards();return;
    case'card-public':if(S.board){S.card.public=data.public==='true';panel();}return;
    case'card-tab':if(S.board&&['mine','public'].includes(data.id)){S.board.tab=data.id;S.result='';S.view='board';panel();S.board.load(data.id);}return;
    case'card-refresh':S.board?.load(S.board.tab);return;
    case'card-more':S.board?.load(S.board.tab,true);return;
    case'card-toggle':if(S.board)S.board.setPublic({id:data.id},data.public==='true');return;
    case'card-recipient':{S.card.recipient=data.id;const who=C().card_choices.recipients.find(x=>x.id===data.id);if(!who?.blessings.includes(S.card.blessing))S.card.blessing='';panel();return;}
    case'card-blessing':S.card.blessing=data.id;panel();return;
    case'card-send':{const who=C().card_choices.recipients.find(x=>x.id===S.card.recipient);if(who?.blessings.includes(S.card.blessing)){const payload={...S.card};if(!C().sharing)delete payload.public;doAct('nguyen',payload);}return;}
    case'do':doAct(data.act,data.act==='nguyen'?{wish:data.wish}:data.act==='khan'?{who:S.khan.who,what:S.khan.what}:{});return;
    case'who':{S.khan.who=data.id;const w=C().khan.who.find(x=>x.id===data.id);if(!w?.what.includes(S.khan.what))S.khan.what='';panel();return;}
    case'what':S.khan.what=data.id;panel();return;
    case'talk':S.talk[data.who]=(S.talk[data.who]|0)+1;panel();return;
    case'bye':showResult('🙏','Thầy Huệ Minh','Thầy gật đầu: “Đi đường bình an nhé con.”');return;
    case'tothemo':goSpot(pl().spots.find(s=>s.id==='tung'));return;
    case'chant':startChant();return;
    case'chant-again':S.chant=null;S.result='';startChant();return;
  }
}

/* ---- tụng kinh: the player keeps the mõ on the beat ---- */
function startChant(){
  const a=actOf('tung');if(!a)return;
  const beats=Math.max(4,C().chant?.beats|0||12),now=performance.now()/1000;
  S.chant={state:'run',beats,start:now+LEAD*PERIOD+.6,hits:new Array(beats).fill(0),count:!!a.ok,flash:0,el:null};
  S.me.pose='kneel';S.me.poseUntil=0;
  // the bowl bell opens, thầy gives three beats on the mõ, his voice comes in with the first of the player's
  sfx('bowl',.6);for(let i=0;i<LEAD;i++)sfx('mo',.55,.6+i*PERIOD);voice(true,LEAD*PERIOD+.6);
  panel();
}
function chantHTML(){
  const ch=S.chant;
  if(ch.state==='done')return ch.html;
  return top('📿','Tụng kinh cùng thầy','Gõ khi vòng sáng khép lại')+`<div class="cv-chant">
    <ol class="cv-lines" aria-live="off">${CHANT.map(l=>`<li>${esc(l)}</li>`).join('')}</ol>
    <div class="cv-beats" aria-hidden="true">${ch.hits.map(()=>'<i></i>').join('')}</div>
    <button type="button" class="cv-mo" aria-label="Gõ mõ"><span class="cv-ring" aria-hidden="true"></span><svg class="cv-mo-face" viewBox="0 0 60 44" width="54" height="40" aria-hidden="true"><ellipse cx="30" cy="25" rx="25" ry="17" fill="#a5642f"/><ellipse cx="22" cy="18" rx="8" ry="4" fill="#c98a4a"/><path d="M10 27Q30 33 50 27" stroke="#5a3216" stroke-width="3" fill="none" stroke-linecap="round"/><rect x="4" y="38" width="52" height="6" rx="3" fill="#b44a3a"/></svg><b>Gõ mõ</b></button>
    <p class="cv-count" aria-live="polite"></p></div>`;
}
function tapMo(){
  const ch=S.chant;if(ch?.state!=='run')return;
  const t=performance.now()/1000,i=Math.round((t-ch.start)/PERIOD);
  S.fx.mo=S.time+.12;sfx('mo',.9);ch.flash=t;
  if(i>=0&&i<ch.beats&&!ch.hits[i]&&Math.abs(t-(ch.start+i*PERIOD))<=WINDOW){ch.hits[i]=1;ch.good=t;}
}
function chantTick(){
  const ch=S.chant;if(ch?.state!=='run')return;
  const box=S.dlg.querySelector('.cv-panel');if(!box)return;
  if(!ch.el)ch.el={lines:[...box.querySelectorAll('.cv-lines li')],dots:[...box.querySelectorAll('.cv-beats i')],ring:box.querySelector('.cv-ring'),mo:box.querySelector('.cv-mo'),count:box.querySelector('.cv-count')};
  const t=performance.now()/1000,rel=(t-ch.start)/PERIOD,cur=Math.max(0,Math.min(ch.beats-1,Math.ceil(rel-WINDOW/PERIOD)));
  const per=Math.ceil(ch.beats/CHANT.length),line=rel<0?-1:Math.min(CHANT.length-1,Math.floor(Math.max(0,rel)/per));
  ch.el.lines.forEach((li,i)=>{const on=i===line;if(li.classList.contains('on')!==on)li.classList.toggle('on',on);if(on&&!still())li.scrollIntoView?.({block:'nearest'});});
  ch.el.dots.forEach((d,i)=>{const s=ch.hits[i]?'hit':rel>i+WINDOW/PERIOD?'miss':'';if(d.className!==s)d.className=s;});
  const next=ch.start+cur*PERIOD,left=Math.max(0,next-t),win=Math.abs(t-Math.round((t-ch.start)/PERIOD)*PERIOD-ch.start)<=WINDOW&&rel>-.3&&rel<ch.beats-1+.3;
  if(ch.el.ring)ch.el.ring.style.transform=still()?'scale(1)':`scale(${1+Math.min(1,left/PERIOD)*.5})`;
  ch.el.mo?.classList.toggle('beat',win);
  ch.el.mo?.classList.toggle('hit',!!ch.good&&t-ch.good<.25);
  const lead=Math.ceil(-rel);ch.el.count&&(ch.el.count.textContent=rel<-.3?`Thầy thỉnh chuông… ${Math.min(LEAD,lead)}`:`${ch.hits.reduce((a,b)=>a+b,0)}/${ch.beats} nhịp`);
  if(rel>ch.beats-1+.6)finishChant();
}
async function finishChant(){
  const ch=S.chant;ch.state='finishing';
  const n=ch.hits.reduce((a,b)=>a+b,0);voice(false);sfx('bowl',.6);
  const again=`<button type="button" class="btn cream small" data-cv="chant-again">Tụng thêm lần nữa</button>`;
  let text=`Bạn giữ được ${n}/${ch.beats} nhịp mõ. Thầy gật đầu, tụng xong một thời kinh ngắn.`,title='Tụng kinh cùng thầy';
  if(ch.count&&actOf('tung')?.ok){const r=await S.env.cmd('jr_chua_do',{act:'tung',beat:n},{quiet:true});if(r?.message)text=r.message;}
  ch.state='done';stand();
  ch.html=top('📿',title,`${n}/${ch.beats} nhịp`)+`<div class="cv-done"><p class="cv-result">${esc(text)}</p></div><div class="cv-p-acts"><button type="button" class="btn primary big full" data-cv="shut">Xong</button></div><div class="cv-p-sub">${again}</div>`;
  panel();
}

/* ---- the loop ---- */
const SPEED=4.2;   // tiles a second
function loop(now){
  if(!S.dlg?.open)return;
  S.raf=requestAnimationFrame(loop);
  if(S.covered){S.last=now;return;}
  const dt=Math.min(.05,(now-S.last)/1000);S.last=now;S.time+=dt;
  const m=S.me;let moving=false;
  if(m.path?.length){
    const sp=SPEED*dt,[tx,ty]=m.path[0],dx=tx-m.x,dy=ty-m.y,d=Math.hypot(dx,dy);moving=true;
    if(d>.001){const sx=dx-dy,sy=dx+dy;m.dir=sy<0?(sx<0?'nw':'ne'):(sx<0?'sw':'se');}
    if(d<=sp){m.x=tx;m.y=ty;m.path.shift();if(!m.path.length)arrived();}else{m.x+=dx/d*sp;m.y+=dy/d*sp;}
    m.step+=dt*7;
  }
  if(m.poseUntil&&S.time>m.poseUntil){m.pose='stand';m.poseUntil=0;}
  chantTick();
  const was=[S.ox,S.oy,S.k];view(dt);const panned=Math.abs(was[0]-S.ox)+Math.abs(was[1]-S.oy)+Math.abs(was[2]-S.k)*100>.5;
  // ~20 fps when only the ribbons and the smoke move, still frames at all when motion is reduced
  const busy=moving||panned||S.chant?.state==='run'||S.fx.bell>S.time||S.fx.gain?.until>S.time;
  if(!busy&&(still()?S.drawn>0:now-S.drawn<50))return;
  S.drawn=now||1;draw(moving);
}
/** The tree the player stands at (its board lights up). */
function nearTree(){for(const s of pl().spots)if(s.kind==='tree'&&Math.hypot(S.me.x-s.stand[0],S.me.y-s.stand[1])<.6)return s.tree;return '';}
function fxOpts(){const reduced=still();return {t:S.time,reduced,feast:!!C()?.feast,lit:S.fx.lit>S.time,bell:S.fx.bell>S.time?1-(S.fx.bell-S.time)/4:0,mo:S.fx.mo>S.time,
  images:IMG,trees:wishTrees()?S.trees:[],near:nearTree(),night:document.documentElement.dataset.theme==='dem',ls:labelScale()};}
/** Labels (tree boards, badges) never shrink under ~11 px on screen however far the camera is. */
const labelScale=()=>Math.max(1,.82/S.k);
function draw(moving=false){
  const c=S.ctx;if(!c||!S.cw)return;
  c.setTransform(1,0,0,1,0,0);c.fillStyle=document.documentElement.dataset.theme==='dem'?'#4d5a3e':'#aec48b';c.fillRect(0,0,S.cv.width,S.cv.height);
  c.setTransform(S.dpr*S.k,0,0,S.dpr*S.k,S.dpr*S.ox,S.dpr*S.oy);
  const o=fxOpts(),p=pl();
  try{
    ground(c,o);
    const items=props(c,o);
    for(const q of p.people)items.push([project(q.x,q.y)[1],()=>npc(c,q,.44,S.time)]);
    items.push([project(S.me.x,S.me.y)[1]+.5,()=>drawMe(c,moving)]);
    items.sort((a,b)=>a[0]-b[0]);for(const [,fn] of items)fn();
    if(o.trees.length)groveSign(c,o);
    o.trees.slice(0,GROVE.length).forEach((t,i)=>treeBoard(c,t,i,o));
    marks(c,p,o);
  }catch(e){console.warn('chùa: draw',e);}
}
/** The player: the town map's own character (its four facings, three walking frames), the pose shown over it. */
function drawMe(c,moving){
  const m=S.me,[x,y]=project(m.x,m.y),F=figure(S.env.api.state);
  E(c,x,y,14,5,'#4a3a2630');
  const low=m.pose==='sit'||m.pose==='kneel',bob=moving&&!still()?-Math.abs(Math.sin(m.step))*2:0;
  const st=getCharacterStamp({look:F.L,gender:F.g,direction:m.dir||'se',walkFrame:moving&&!still()?Math.floor(m.step)%3:0,onReady:()=>{S.drawn=0;}});
  const w=54,h=72;
  if(st?.canvas){c.save();if(low){c.beginPath();c.rect(x-w,y-h-20,w*2,h+6);c.clip();}c.drawImage(st.canvas,x-w/2,y-h+(low?12:0)+bob,w,h);c.restore();}
  if(m.pose==='sweep'){L(c,x+10,y-30,x+20,y-2,'#b88b62',3);E(c,x+21,y-1,8,3,'#d9b97a');}
  if(m.pose==='pray'||m.pose==='kneel')T(c,'🙏',x,y-h-6+(low?12:0),16,'#5a3f2c',400);
  const g=S.fx.gain;if(g&&g.until>S.time){const k=1-(g.until-S.time)/2.4;c.globalAlpha=Math.max(0,Math.min(1,(1-k)*2.2));
    T(c,g.text,x,y-h-26-k*30,18,'#b07a1c',800);c.globalAlpha=1;}
}
/** Badges over the things to do (dim when done or not today), 💬 over the people. */
function marks(c,p,o){
  const big=labelScale();
  for(const s of p.spots){
    const [x,y0]=project(...s.at),y=y0-s.lift;
    if(s.kind==='act'){const a=actOf(s.act);if(!a||Math.hypot(S.me.x-s.stand[0],S.me.y-s.stand[1])<.5)continue;const done=actionDone(C(),a)||!!a.done,dim=done||!a.ok,bob=o.reduced||dim?0:Math.sin(o.t*2+x)*2.5;
      const by=y-22*big+bob;c.globalAlpha=dim?.6:1;E(c,x,by,15*big,15*big,dim?'#efe6d8':'#fffaf0');c.strokeStyle=dim?'#c9b49a':'#d9a441';c.lineWidth=2;c.beginPath();c.arc(x,by,15*big,0,Math.PI*2);c.stroke();
      T(c,done?'✓':a.emoji,x,by+1,14*big,done?'#6b8f4a':'#5a3f2c',700);c.globalAlpha=1;continue;}
    if(s.kind==='npc'){E(c,x+16*big,y-6,11*big,9*big,'#fffaf0');T(c,'💬',x+16*big,y-5,10*big,'#5a3f2c',400);}
  }
}

/* ---- test hooks (scripts/browser_chua.py) ---- */
globalThis.__chua={state:()=>({open:!!S.dlg?.open,area:S.area,port:S.port,k:S.k,me:[S.me.x,S.me.y],pose:S.me.pose,panel:S.panel?.id||null,spots:pl().spots.map(s=>s.id),
  trees:S.trees.length,covered:S.covered,chant:S.chant?{state:S.chant.state,hits:S.chant.hits.reduce((a,b)=>a+b,0)}:null}),
  chantClock:()=>S.chant?{start:S.chant.start,period:PERIOD,beats:S.chant.beats}:null,
  /** where a spot's badge / thing is on the page (client px), to tap it like a player */
  screen:id=>{const s=pl().spots.find(q=>q.id===id);if(!s)return null;const [x,y]=project(...s.at),r=S.cv.getBoundingClientRect();return [r.left+S.ox+x*S.k,r.top+S.oy+(y-s.lift)*S.k];},
  look:id=>{const s=pl().spots.find(q=>q.id===id);if(s){const [x,y]=project(...s.at);lookAt([x,y-s.lift]);}},
  go:id=>goSpot(pl().spots.find(s=>s.id===id)),route:id=>{const s=pl().spots.find(q=>q.id===id);return s?route(pl(),[S.me.x,S.me.y],s.stand):null;}};
