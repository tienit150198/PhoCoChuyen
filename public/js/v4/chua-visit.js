/** 🛕 Vào chùa: chùa Gió Lành as a place, opened from the "Đi chùa" section of the Đời thường sheet (./chua.js).
 * Its own full-screen dialog with a canvas scene (scenes/chua-place.js): the player walks the yard, the main hall
 * and the dining hall, and what they walk up to opens right there: incense at the burner, the bell at the bell
 * tower, sitting by the lotus pond, a wish at the fence, the broom, the vegetarian lunch (rằm, mùng 1), kneeling
 * on the mat to put a prayer together (khấn: who for, what for; nothing preset), the wooden fish (tụng kinh: the
 * player keeps the beat), thầy Huệ Minh and the others to talk to (free, unlimited, changes nothing).
 * Every rule and gain is game/chua.py (state.chua = chua.public(); jr_chua_do); this file draws and asks.
 * An older server sends no `more`/`khan`/`chant`: ./chua.js then shows no way in (the old button list stays).
 * Reduced motion: the player steps straight to where they tapped, nothing drifts, the chant's ring stays still
 * (the mõ lights up on the beat instead). */
import {icon,escapeHTML as esc} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {figure,paintPlayer,CANVAS} from './look.js';
import {audioContext,wantAudio,duck} from '../audio.js';
import {AREAS,VIEW,PEOPLE,LOOKS,plan,route,nearestFree,paintRoom,areaProps,person,R,E,L,T,fit} from '../scenes/chua-place.js';

const RM=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
const still=()=>Boolean(RM?.matches)||document.documentElement.classList.contains('reduce-motion')||document.body.classList.contains('reduce-motion');
const S={env:null,dlg:null,cv:null,ctx:null,stage:null,area:'san',port:false,k:1,ox:0,oy:0,dpr:1,cw:0,ch:0,cam:null,
  me:{x:0,y:0,path:null,pose:'stand',poseUntil:0,step:0},arrive:null,fx:{},panel:null,result:'',chant:null,khan:{who:'',what:''},
  talk:{},raf:0,last:0,drawn:0,time:0,fadeAt:-9,busy:false,bound:false};
const C=()=>S.env?.api.state?.chua;
const day=()=>({lunar:C()?.lunar|0,feast:!!C()?.feast});
const pl=()=>plan(S.area,S.port,day());
const actOf=id=>[...(C()?.acts||[]),...(C()?.more||[])].find(a=>a.id===id)||null;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
/** Can this server take the walkable pagoda? (the fields an older one does not send) */
export const hasScene=c=>!!(c?.enabled&&Array.isArray(c.more)&&c.khan&&c.chant);

/* ---- the words ---- */
const SHORT={huong:'Lư hương',chuong:'Gác chuông',ngoi:'Hồ sen',nguyen:'Rào lời nguyện',quet:'Chổi tre',com:'Bàn cơm chay',khan:'Chiếu lễ',tung:'Mõ'};
const LOOK_NAME={bode:'🌳 Cây bồ đề',giatri:'🔔 Chuông gia trì',ban:'🕯️ Bàn thờ',thoikhoa:'📋 Thời khóa',thucdon:'📋 Thực đơn'};
const INTRO={
  huong:'Lư hương lớn giữa sân. Khách thắp hương ở đây, trong điện chỉ một nén.',
  chuong:'Gác chuông có quả chuông đồng cả làng cùng đúc. Chuông thỉnh chậm, đều, chờ tiếng ngân tắt hẳn.',
  ngoi:'Hồ sen nhỏ, mấy con cá đỏ lượn chậm. Ngồi đây gió sông mát lắm.',
  nguyen:'Hàng rào tre buộc đầy giấy đỏ. Bạn chọn một lời nguyện để viết.',
  quet:'Mấy cây chổi tre dựng ở giá. Lá bàng rụng đầy sân.',
  com:'Bàn dài, bà Nhạn đang múc canh nấm.',
  khan:'Bạn quỳ trên chiếu trước điện Phật. Tự chọn khấn cho ai, mong điều gì.',
  tung:'Thầy giữ chuông gia trì, bạn giữ mõ. Gõ đúng lúc vòng sáng khép lại.',
};
const VERB={huong:'🪔 Thắp hương',chuong:'🔔 Đứng nghe chuông',ngoi:'🍃 Ngồi xuống',quet:'🧹 Cầm chổi quét',com:'🍚 Ngồi vào bàn',khan:'🙏 Chắp tay khấn',tung:'📿 Bắt đầu tụng'};
const POSE={huong:'pray',chuong:'pray',ngoi:'sit',nguyen:'pray',quet:'sweep',com:'sit',khan:'kneel',tung:'kneel'};
const NPC={
  na:['Bạn ơi, con cá đỏ to nhất tên là Mập đó. Con đặt tên đấy!','Bà con dặn đi trong chùa phải đi chậm, nói nhỏ. Con đang tập.','Sao hoa sen mọc dưới bùn mà vẫn thơm vậy ta?'],
  quyen:['Chiều nào chị cũng ra đây ngồi một lúc. Không cần nói gì cả.','Nghe chuông xong, tự nhiên thấy nhẹ người.','Cứ ngồi đi, ghế còn rộng mà.'],
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
 * the quiet loop of each area plays meanwhile and the game's own music steps aside (audio.js duck).
 * Fetched only once the pagoda is open (the loop of the area, the rest when its spot is reached), decoded at
 * 32 kHz like the music, freed when the pagoda closes; nothing plays before a tap has started the page's audio,
 * no loop on a data-saving connection. */
const FILES={bell:'chuong-dai-hong-2.mp3',mo:'mo-1.mp3',bowl:'chuong-gia-tri.mp3',voice:'su-tung-kinh.mp3'};
const LOOPS={san:['nen-chua-sang.mp3',.55],trai:['nen-chua-sang.mp3',.35],dien:['tung-kinh-loop.mp3',.3]};
const NEEDS={chuong:['bell'],khan:['bowl'],tung:['mo','bowl','voice']};
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
/** The area's quiet loop (null: none), crossfaded when the area changes. */
function ambience(area){
  const want=area&&S.dlg?.open&&musicOn()?LOOPS[area]:null,key=want?want.join('|'):'';
  if(key===LOOP.key)return;LOOP.key=key;
  const c=audioContext(),old=LOOP.cur;
  if(old&&want&&old.file===want[0]&&c){LOOP.cur=old;try{old.g.gain.setTargetAtTime(want[1]*musicVol(),c.currentTime,.6);}catch{/* gone */}return;}
  LOOP.cur=null;fadeOut(old,c,1.6);
  for(const f of [...BUF.keys()])if(Object.values(LOOPS).some(l=>l[0]===f)&&f!==want?.[0])BUF.delete(f);   // a decoded loop is MBs: keep one
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
  d.innerHTML=`<div class="cv-root"><header class="cv-head"><span class="cv-logo" aria-hidden="true">🛕</span><div class="grow"><h2 id="cvTitle">Chùa Gió Lành</h2><p class="cv-day"></p></div>
      <button type="button" class="icon-btn cv-mute" data-cv="mute" aria-label="Tiếng chùa" aria-pressed="true"></button>
      <button type="button" class="icon-btn" data-cv="close" aria-label="Ra về">${icon('x',20)}</button></header>
    <nav class="cv-areas" aria-label="Khu trong chùa"></nav>
    <div class="cv-stage"><canvas class="cv-canvas" tabindex="0" role="img" aria-label="Chùa Gió Lành"></canvas><div class="cv-panel" hidden></div></div>
    <div class="cv-here" role="group" aria-label="Ở đây có"></div></div>`;
  document.body.append(d);
  S.stage=d.querySelector('.cv-stage');S.cv=d.querySelector('canvas');S.ctx=S.cv.getContext('2d');
  d.addEventListener('click',e=>{const el=e.target.closest('[data-cv]');if(!el||!d.contains(el)||el.disabled)return;e.preventDefault();act(el.dataset.cv,el.dataset);});
  d.addEventListener('pointerdown',e=>{if(e.target.closest('.cv-mo')){e.preventDefault();tapMo();}});
  d.addEventListener('keydown',e=>{if(S.chant?.state==='run'&&(e.key===' '||e.key==='Enter')){e.preventDefault();tapMo();}});
  d.addEventListener('close',onClose);
  let down=null;
  S.cv.addEventListener('pointerdown',e=>{down={x:e.clientX,y:e.clientY,t:performance.now()};});
  S.cv.addEventListener('pointerup',e=>{const d0=down;down=null;if(!d0||Math.hypot(e.clientX-d0.x,e.clientY-d0.y)>14||performance.now()-d0.t>800)return;tapAt(e.clientX,e.clientY);});
  S.cv.addEventListener('keydown',e=>{const k={ArrowLeft:[-60,0],ArrowRight:[60,0],ArrowUp:[0,-40],ArrowDown:[0,40]}[e.key];if(!k)return;e.preventDefault();walkTo([S.me.x+k[0],S.me.y+k[1]]);});
  let sizing=0;new ResizeObserver(()=>{cancelAnimationFrame(sizing);sizing=requestAnimationFrame(size);}).observe(S.stage);
  S.dlg=d;return d;
}
function bind(){
  if(S.bound)return;S.bound=true;
  S.env.api.addEventListener('state',()=>{if(!S.dlg?.open)return;head();here();ambience(S.area);if(S.panel&&!S.result&&S.chant?.state!=='run')panel();});
}
/** Open the pagoda (from ./chua.js's "Vào chùa"); comes in through the gate. */
export async function openChua(env){
  S.env=env;bind();await stylesheet('/css/chua.css');
  if(!hasScene(C()))return;
  const d=dialog();
  S.area='san';S.panel=null;S.result='';S.chant=null;S.khan={who:'',what:''};S.fx={};S.me.pose='stand';S.me.path=null;S.arrive=null;
  if(!d.open)d.showModal();
  const toasts=document.getElementById('toasts');if(toasts)d.append(toasts);   // errors show over the scene
  size();place(pl().entry.gate);head();here();panel();
  wantAudio('chua',true);ambience(S.area);
  S.cv.focus({preventScroll:true});
  S.last=performance.now();cancelAnimationFrame(S.raf);S.raf=requestAnimationFrame(loop);
}
function onClose(){
  cancelAnimationFrame(S.raf);S.raf=0;S.chant=null;voice(false);ambience(null);wantAudio('chua',false);BUF.clear();
  const toasts=document.getElementById('toasts'),sheet=document.getElementById('sheet');if(toasts)(sheet?.open?sheet:document.body).append(toasts);
  S.env?.renderSheet?.(false);
}

/* ---- layout ---- */
function size(){
  if(!S.stage)return;
  const r=S.stage.getBoundingClientRect(),cw=Math.max(1,r.width),ch=Math.max(1,r.height),was=S.port;
  S.port=cw/ch<.95;S.dpr=Math.min(2,globalThis.devicePixelRatio||1);S.cw=cw;S.ch=ch;
  S.cv.width=Math.round(cw*S.dpr);S.cv.height=Math.round(ch*S.dpr);
  if(was!==S.port&&S.me.x){   // the other composition: keep the player where they were on the floor
    const a=plan(S.area,was,day()).floor,b=pl().floor,u=(S.me.x-a[0])/(a[2]-a[0]),v=(S.me.y-a[1])/(a[3]-a[1]);
    place([b[0]+u*(b[2]-b[0]),b[1]+v*(b[3]-b[1])]);
  }
  S.cam=null;view(0);S.drawn=0;
}
/** Scale and offset: the whole place on a wide screen; on a phone a closer view (at least 72% of each side)
 * that follows the player, and keeps them above the panel when the panel spans the stage. */
function view(dt){
  const [x0,y0,x1,y1]=VIEW[S.port?'port':'land'],vw=x1-x0,vh=y1-y0,cw=S.cw,ch=S.ch;if(!cw)return;
  const box=S.dlg?.querySelector('.cv-panel'),wide=box&&!box.hidden&&box.offsetWidth>cw*.8;
  const band=wide?Math.max(ch*.3,box.offsetTop-6):ch,Z=S.port?.72:1;
  const k=Math.min(cw/(vw*Z),band/(vh*Z),Math.max(cw/vw,band/vh)*1.6);
  const want=[S.me.x||(x0+x1)/2,(S.me.y||(y0+y1)/2)-(S.port?110:90)];
  if(!S.cam||still()||!dt)S.cam=want;else{const a=Math.min(1,dt*4);S.cam=[S.cam[0]+(want[0]-S.cam[0])*a,S.cam[1]+(want[1]-S.cam[1])*a];}
  const fitX=vw*k<=cw,fitY=vh*k<=band;
  S.k=k;
  S.ox=fitX?(cw-vw*k)/2-x0*k:Math.min(-x0*k,Math.max(cw-x1*k,cw/2-S.cam[0]*k));
  S.oy=fitY?(band-vh*k)/2-y0*k:Math.min(-y0*k,Math.max(band-y1*k,band/2-S.cam[1]*k));
}
function place(p){const q=nearestFree(pl(),p)||p;S.me.x=q[0];S.me.y=q[1];S.me.path=null;}
const toScene=(cx,cy)=>{const r=S.cv.getBoundingClientRect();return [(cx-r.left-S.ox)/S.k,(cy-r.top-S.oy)/S.k];};

/* ---- moving ---- */
function stand(){if(S.me.pose!=='stand'){S.me.pose='stand';S.me.poseUntil=0;}}
function walkTo(p,then=null){
  if(S.chant?.state==='run')return;
  stand();const path=route(pl(),[S.me.x,S.me.y],p);
  S.arrive=then;
  if(!path||still()){const end=path?path[path.length-1]:[S.me.x,S.me.y];S.me.x=end[0];S.me.y=end[1];S.me.path=null;arrived();return;}
  S.me.path=path.slice(1);
}
function arrived(){const f=S.arrive;S.arrive=null;S.me.path=null;if(f)f();}
function tapAt(cx,cy){
  if(S.chant?.state==='run')return;
  const p=toScene(cx,cy),spot=hitSpot(p);
  if(spot){goSpot(spot);return;}
  closePanel();walkTo(p);
}
function hitSpot(p){let best=null,bd=Infinity;for(const s of pl().spots){const d=Math.hypot(s.hit[0]-p[0],s.hit[1]-p[1]);if(d<=s.r&&d<bd){bd=d;best=s;}}return best;}
function goSpot(s){
  if(!s)return;closePanel();
  walkTo(s.stand,()=>{
    if(s.kind==='door')enterArea(s.to);
    else{S.panel=s;S.result='';if(s.kind==='npc')S.talk[s.who]=S.talk[s.who]??0;if(s.act)prefetch(s.act);panel();}
  });
}
function enterArea(id){
  if(id===S.area||!AREAS.some(a=>a.id===id))return;
  const from=S.area;S.area=id;closePanel();
  place(pl().entry[from]||Object.values(pl().entry)[0]);
  if(!still())S.fadeAt=S.time;
  head();here();S.drawn=0;ambience(id);
}

/* ---- the header, the area chips, "here" ---- */
function head(){
  const c=C();if(!c||!S.dlg)return;
  const m=S.dlg.querySelector('.cv-mute'),on=settings().sound!==false&&!quiet;
  m.innerHTML=icon(on?'volume':'mute',20);m.setAttribute('aria-pressed',String(on));m.disabled=settings().sound===false;
  m.title=settings().sound===false?'Âm thanh đang tắt trong Cài đặt':on?'Tắt tiếng chùa':'Bật tiếng chùa';
  S.dlg.querySelector('.cv-day').innerHTML=`<span>${esc(c.label||'')}</span>${c.feast?' · <span>chùa có cơm chay</span>':''} · <span>còn ${c.left|0}/${c.daily|0} việc hôm nay</span>`;
  S.dlg.querySelector('.cv-areas').innerHTML=AREAS.map(a=>`<button type="button" class="cv-chip${a.id===S.area?' on':''}" data-cv="area" data-id="${a.id}" aria-pressed="${a.id===S.area}"><span aria-hidden="true">${a.icon}</span><b>${esc(a.name)}</b></button>`).join('');
}
function spotName(s){
  if(s.kind==='door'){const a=AREAS.find(x=>x.id===s.to);return `${a.icon} ${a.name} ›`;}
  if(s.kind==='npc')return `${PEOPLE[s.who].icon} ${PEOPLE[s.who].name}`;
  if(s.kind==='look')return LOOK_NAME[s.look]||'👀';
  const a=actOf(s.act);return `${a?.emoji||'•'} ${SHORT[s.act]||a?.name||''}`;
}
function here(){
  if(!S.dlg)return;
  S.dlg.querySelector('.cv-here').innerHTML=pl().spots.map(s=>{const a=s.kind==='act'?actOf(s.act):null,done=a?.done;
    return `<button type="button" class="cv-spot${done?' done':''}${s.kind==='door'?' door':''}" data-cv="spot" data-id="${esc(s.id)}">${esc(spotName(s))}${done?' <i aria-label="đã làm">✓</i>':''}</button>`;}).join('');
}

/* ---- the panel: what happens here ---- */
function gain(a){
  if(a.id==='tung')return 'tinh thần +1…+4 theo nhịp mõ';
  const out=[];if(a.spirit)out.push(`tinh thần +${a.spirit}`);if(a.wake)out.push(`tỉnh táo +${a.wake}`);if(a.full)out.push(`no bụng +${a.full}`);
  return out.join(' · ');
}
const top=(emoji,title,sub='')=>`<div class="cv-p-head"><span class="cv-p-emoji" aria-hidden="true">${emoji}</span><div class="grow"><b>${esc(title)}</b>${sub?`<small>${esc(sub)}</small>`:''}</div>
  <button type="button" class="icon-btn small" data-cv="shut" aria-label="Đóng">${icon('x',16)}</button></div>`;
const why=a=>a.done?'Hôm nay làm rồi':a.why;
function actBody(a){
  const no=why(a),note=no?`<p class="cv-why">${esc(no)}</p>`:'';
  if(a.id==='nguyen')return `<p>${esc(INTRO.nguyen)}</p>${note}<div class="cv-chips">${(C().wishes||[]).map(w=>`<button type="button" class="cv-pick" data-cv="do" data-act="nguyen" data-wish="${esc(w.id)}"${a.ok?'':' disabled'}>📜 ${esc(w.text)}</button>`).join('')}</div>`;
  if(a.id==='khan')return khanBody(a,note);
  if(a.id==='tung')return `<p>${esc(INTRO.tung)}</p>${a.ok?'':`<p class="cv-why">${esc(no)} · vẫn tụng cùng thầy được, chỉ không tính thêm.</p>`}
    <div class="cv-p-acts"><button type="button" class="btn primary" data-cv="chant">${VERB.tung}</button></div>`;
  const intro=a.id==='com'&&!C().feast?'Hôm nay không phải rằm hay mùng 1, bàn ăn còn trống.':INTRO[a.id];
  return `<p>${esc(intro)}</p>${note}<div class="cv-p-acts"><button type="button" class="btn primary" data-cv="do" data-act="${esc(a.id)}"${a.ok?'':' disabled'}>${VERB[a.id]||esc(a.name)}</button></div>`;
}
function khanBody(a,note){
  const K=C().khan,who=K.who.find(w=>w.id===S.khan.who),what=K.what.find(w=>w.id===S.khan.what);
  const whoChips=K.who.map(w=>`<button type="button" class="cv-pick${w.id===S.khan.who?' on':''}" data-cv="who" data-id="${esc(w.id)}" aria-pressed="${w.id===S.khan.who}"${a.ok?'':' disabled'}>${esc(w.text)}</button>`).join('');
  const whatChips=K.what.map(w=>{const fits=who&&who.what.includes(w.id);return `<button type="button" class="cv-pick${w.id===S.khan.what?' on':''}" data-cv="what" data-id="${esc(w.id)}" aria-pressed="${w.id===S.khan.what}"${a.ok&&fits?'':' disabled'}>${esc(w.text)}</button>`;}).join('');
  return `<p>${esc(INTRO.khan)}</p>${note}
    <h4 class="cv-q">Khấn cho ai?</h4><div class="cv-chips">${whoChips}</div>
    <h4 class="cv-q">Mong điều gì?${who?'':' <small>chọn người trước</small>'}</h4><div class="cv-chips">${whatChips}</div>
    <p class="cv-prayer">${who&&what?`<b>“${esc(`Con cầu mong ${who.text} ${what.text}.`)}”</b>`:`“<span>Con cầu mong</span> <b>${who?esc(who.text):'…'}</b> <b>…</b>”`}</p>
    <div class="cv-p-acts"><button type="button" class="btn primary" data-cv="do" data-act="khan"${a.ok&&who&&what?'':' disabled'}>${VERB.khan}</button></div>`;
}
function talkBody(who){
  const p=PEOPLE[who],lines=who==='thay'?(C().abbot||[]):who==='nhan'&&C().feast?NPC.nhan_feast:NPC[who]||[];
  const i=(S.talk[who]|0)%Math.max(1,lines.length),line=lines[i]||'';
  const more=who==='thay'?`<button type="button" class="btn cream small" data-cv="talk" data-who="thay">Thưa thầy, con nghe thêm</button>
      <button type="button" class="btn primary small" data-cv="tothemo">📿 Xin tụng kinh cùng thầy</button>
      <button type="button" class="btn ghost small" data-cv="bye" data-who="thay">🙏 Chắp tay chào thầy</button>`
    :`<button type="button" class="btn cream small" data-cv="talk" data-who="${esc(who)}">Nói chuyện thêm</button><button type="button" class="btn ghost small" data-cv="shut">Chào</button>`;
  return top(p.icon,p.name,p.role)+`<p class="cv-line">“${esc(line)}”</p><div class="cv-p-acts">${more}</div>`;
}
function panel(){
  const box=S.dlg?.querySelector('.cv-panel');if(!box)return;
  const s=S.panel;
  if(!s){box.hidden=true;box.innerHTML='';S.stage.classList.remove('has-panel');return;}
  let html='';
  if(S.chant)html=chantHTML();
  else if(S.result)html=S.result;
  else if(s.kind==='npc')html=talkBody(s.who);
  else if(s.kind==='look')html=top('👀',spotName(s).replace(/^\S+\s/,''))+`<p>${esc(LOOKS[s.look]||'')}</p>`;
  else{const a=actOf(s.act);if(!a){closePanel();return;}html=top(a.emoji,a.name,gain(a))+actBody(a);}
  box.innerHTML=html;box.hidden=false;S.stage.classList.add('has-panel');
  if(S.chant)S.chant.el=null;
}
function closePanel(){if(S.chant?.state==='run')return;S.panel=null;S.result='';S.chant=null;stand();panel();}
function showResult(emoji,title,text){S.result=top(emoji,title)+`<p class="cv-result">${esc(text)}</p><div class="cv-p-acts"><button type="button" class="btn primary small" data-cv="shut">Đóng</button></div>`;panel();}

/* ---- doing ---- */
async function doAct(id,extra={}){
  const a=actOf(id);if(!a?.ok||S.busy)return;
  S.busy=true;S.me.pose=POSE[id]||'pray';S.me.poseUntil=0;
  if(id==='huong')S.fx.lit=S.time+6;
  if(id==='chuong'){S.fx.bell=S.time+4;sfx('bell',.8);}
  if(id==='khan')sfx('bowl',.7);
  const box=S.dlg.querySelector('.cv-panel .cv-p-acts');if(box)box.innerHTML='<p class="cv-wait" aria-live="polite">…</p>';
  try{
    const [r]=await Promise.all([S.env.cmd('jr_chua_do',{act:id,...extra},{quiet:true}),sleep(still()?0:900)]);
    if(r?.message)showResult(a.emoji,a.name,r.message);else{stand();panel();}
    if(id==='khan')S.khan={who:'',what:''};
  }finally{S.busy=false;}
  if(id==='huong'||id==='nguyen'||id==='chuong')S.me.poseUntil=S.time+3;
}
function act(kind,data){
  switch(kind){
    case'close':S.dlg.close();return;
    case'mute':quiet=!quiet;try{localStorage.setItem(QUIET_KEY,quiet?'1':'0');}catch{/* storage blocked */}
      if(quiet){voice(false);ambience(null);}else ambience(S.area);head();return;
    case'area':{const door=pl().spots.find(s=>s.kind==='door'&&s.to===data.id);if(S.chant?.state==='run')return;
      if(door&&!still())goSpot(door);else enterArea(data.id);return;}
    case'spot':goSpot(pl().spots.find(s=>s.id===data.id));return;
    case'shut':closePanel();return;
    case'do':doAct(data.act,data.act==='nguyen'?{wish:data.wish}:data.act==='khan'?{who:S.khan.who,what:S.khan.what}:{});return;
    case'who':{S.khan.who=data.id;const w=C().khan.who.find(x=>x.id===data.id);if(!w?.what.includes(S.khan.what))S.khan.what='';panel();return;}
    case'what':S.khan.what=data.id;panel();S.dlg.querySelector('.cv-panel [data-act="khan"]')?.scrollIntoView?.({block:'nearest'});return;
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
  return top('📿','Tụng kinh cùng thầy','Gõ mõ khi vòng sáng khép lại')+`<div class="cv-chant">
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
  ch.html=top('📿',title,`${n}/${ch.beats} nhịp`)+`<p class="cv-result">${esc(text)}</p><div class="cv-p-acts">${again}<button type="button" class="btn primary small" data-cv="shut">Đóng</button></div>`;
  panel();
}

/* ---- the loop ---- */
function loop(now){
  if(!S.dlg?.open)return;
  S.raf=requestAnimationFrame(loop);
  const dt=Math.min(.05,(now-S.last)/1000);S.last=now;S.time+=dt;
  const m=S.me;let moving=false;
  if(m.path?.length){
    const sp=(S.port?230:270)*dt,[tx,ty]=m.path[0],dx=tx-m.x,dy=ty-m.y,d=Math.hypot(dx,dy);moving=true;
    if(d<=sp){m.x=tx;m.y=ty;m.path.shift();if(!m.path.length)arrived();}else{m.x+=dx/d*sp;m.y+=dy/d*sp;}
    m.step+=dt*9;
  }
  if(m.poseUntil&&S.time>m.poseUntil){m.pose='stand';m.poseUntil=0;}
  chantTick();
  const was=[S.ox,S.oy,S.k];view(dt);const panned=Math.abs(was[0]-S.ox)+Math.abs(was[1]-S.oy)+Math.abs(was[2]-S.k)*100>.5;
  // ~30 fps when only the ambience moves, still frames at all when motion is reduced
  const busy=moving||panned||S.chant?.state==='run'||S.time-S.fadeAt<.4||S.fx.bell>S.time;
  if(!busy&&(still()?S.drawn>0:now-S.drawn<33))return;
  S.drawn=now||1;draw();
}
function fxOpts(){const reduced=still();return {t:S.time,reduced,feast:!!C()?.feast,lit:S.fx.lit>S.time,bell:S.fx.bell>S.time?1-(S.fx.bell-S.time)/4:0,wish:!!actOf('nguyen')?.done,mo:S.fx.mo>S.time};}
function draw(){
  const c=S.ctx;if(!c||!S.cw)return;
  c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,S.cv.width,S.cv.height);
  c.setTransform(S.dpr*S.k,0,0,S.dpr*S.k,S.dpr*S.ox,S.dpr*S.oy);
  const o=fxOpts(),w={ctx:c,isPortrait:()=>S.port,reduced:o.reduced,time:S.time,c:null},p=pl();
  try{
    paintRoom(w,S.area,o);
    const f=p.floor,depth=y=>.9+.18*(y-f[1])/Math.max(1,f[3]-f[1]),base=S.port?.9:.74;
    const items=[...areaProps(c,S.area,S.port,o)];
    for(const q of p.people)items.push([q.y,()=>person(c,q.x,q.y,base*depth(q.y)*1.05,q.who,{t:S.time,pose:q.sit?'sit':''})]);
    items.push([S.me.y+.5,()=>drawMe(c,base*depth(S.me.y))]);
    items.sort((a,b)=>a[0]-b[0]);for(const [,fn] of items)fn();
    marks(c,p,o);
  }catch(e){console.warn('chùa: draw',e);}
  if(S.time-S.fadeAt<.32&&!o.reduced){c.setTransform(1,0,0,1,0,0);c.globalAlpha=Math.max(0,1-(S.time-S.fadeAt)/.32)*.85;c.fillStyle='#fff6ed';c.fillRect(0,0,S.cv.width,S.cv.height);c.globalAlpha=1;}
}
function drawMe(c,s){
  const m=S.me,F=figure(S.env.api.state);c.save();c.translate(m.x,m.y);c.scale(s,s);
  const low=m.pose==='sit'||m.pose==='kneel';
  if(low){E(c,0,2,30,8,'#81644823');c.translate(0,22);c.beginPath();c.rect(-80,-220,160,196);c.clip();}
  else if(m.path?.length&&!still())c.translate(0,-Math.abs(Math.sin(m.step))*3);
  try{paintPlayer(c,F,CANVAS);}catch{/* look not ready */}
  c.restore();
  if(m.pose==='sweep'){L(c,m.x+22*s,m.y-60*s,m.x+40*s,m.y-4*s,'#b88b62',4*s);E(c,m.x+42*s,m.y-2*s,14*s,5*s,'#d9b97a');}
  if(m.pose==='pray'||m.pose==='kneel'){T(c,'🙏',m.x,m.y-(low?120:150)*s,20*s,'#5a3f2c',400);}
}
/** Badges over the things to do (dim when done or not today), signs over the doors. */
function marks(c,p,o){
  const big=S.port?1.25:1;
  for(const s of p.spots){
    const [x,y]=s.hit;
    if(s.kind==='door'){const a=AREAS.find(q=>q.id===s.to),label=`${a.icon} ${a.name} ›`;c.font=`800 ${14*big}px "Trebuchet MS", sans-serif`;
      const wd=Math.max(90,c.measureText(label).width+26),h=26*big,[v0,,v1]=VIEW[S.port?'port':'land'],tx=Math.max(v0+wd/2+4,Math.min(v1-wd/2-4,x));
      R(c,tx-wd/2,y-h/2-20,wd,h,'#fffaf0ee',h/2,'#c9b49a',1.5);T(c,label,tx,y-19,fit(c,label,wd-14,13*big),'#5a3f2c',800);continue;}
    if(s.kind==='act'){const a=actOf(s.act);if(!a||Math.hypot(S.me.x-s.stand[0],S.me.y-s.stand[1])<30)continue;const dim=a.done||!a.ok,bob=o.reduced||dim?0:Math.sin(o.t*2+x)*3;
      c.globalAlpha=dim?.55:1;E(c,x,y-26+bob,17*big,17*big,dim?'#efe6d8':'#fffaf0');c.strokeStyle=dim?'#c9b49a':'#d9a441';c.lineWidth=2;c.beginPath();c.arc(x,y-26+bob,17*big,0,Math.PI*2);c.stroke();
      T(c,a.done?'✓':a.emoji,x,y-25+bob,16*big,a.done?'#6b8f4a':'#5a3f2c',700);c.globalAlpha=1;continue;}
    if(s.kind==='npc'){E(c,x+18,y-6,12*big,10*big,'#fffaf0');T(c,'💬',x+18,y-5,11*big,'#5a3f2c',400);}
  }
}

/* ---- test hooks (scripts/browser_chua.py) ---- */
globalThis.__chua={state:()=>({open:!!S.dlg?.open,area:S.area,port:S.port,me:[S.me.x,S.me.y],pose:S.me.pose,panel:S.panel?.id||null,spots:pl().spots.map(s=>s.id),
  chant:S.chant?{state:S.chant.state,hits:S.chant.hits.reduce((a,b)=>a+b,0)}:null}),
  chantClock:()=>S.chant?{start:S.chant.start,period:PERIOD,beats:S.chant.beats}:null,
  go:id=>goSpot(pl().spots.find(s=>s.id===id)),enter:id=>enterArea(id),route:(id)=>{const s=pl().spots.find(q=>q.id===id);return s?route(pl(),[S.me.x,S.me.y],s.stand):null;}};
