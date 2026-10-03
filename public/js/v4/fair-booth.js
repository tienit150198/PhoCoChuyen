/** 📸 Buồng chụp ảnh at the fair (tab 'pb'; owner 03/10: "photoboth thì rủ bạn bè tới chụp với nhau ở trong hội chợ
 * nhé … 2 chế độ là 1 mình, người lạ và bạn bè … thiết kế trang trí sao cho đẹp với nhiều khung hình nhé").
 * Three ways in: Một mình (all here, no socket), Người lạ (the live service pairs the player with someone else waiting,
 * a minute at most) and Bạn bè (a room with a 4-character code the friends type in, up to 4). In a room everyone sees
 * the others' characters (./look.js, the same painter as the fairground and the street) on the booth's backdrop; the
 * host picks the frame and the backdrop (./photo-frames.js, shared with the photobooth career), each player their pose
 * and prop; everyone pays their ticket (fair_photo, game/fair_photo.py) and gets ready, the host shoots: a 3-2-1 and
 * four shots, each browser drawing them from the room's state at that moment (poses may change between shots), then the
 * strip with the frame, a date stamp, the player's own filter and stickers, saved as a PNG on the device. Nothing of the
 * photos goes to any server; the room lives in memory on the live service (live/booth.py) until its last player leaves.
 * A ticket paid but not used (the room broke up before the shot) is kept for the next shoot in this tab.
 * The shared ways only show when the live service says welcome.flags.booth (an older one: only Một mình); the stall only
 * when the game server sells tickets (api.state.fair.photo; an older one: no booth on the fairground).
 * fair.js owns the dialog and passes its helpers in (setup); its render() patches the page in place and calls mount()
 * after: the booth's stage lives on a canvas in a data-fh-live slot, drawn when the room changes and by
 * requestAnimationFrame only while a shoot runs.
 * 1.5.4 (owner 03/10: "làm đẹp hơn nha, nhiều dáng với đẹp hơn nha"): thirty poses (./booth-poses.js: the character's
 * arms, hands, head and face really move; nine are made together, picking one sets it for the whole room:
 * booth_set {pose, all: true}, an older live service sets only one's own), a 🎲 that picks one (and the same for the
 * friends), the fair's own frames, backdrops, stickers and colours (./photo-frames.js FAIR_*), the words and the date
 * on the strip, a countdown with a ring and the shots dropping in. An id a client does not know is drawn as its
 * default (pose 'dung', frame 'dem_hoi', backdrop 'kem'): the 1.5.1 client in the same room keeps working. */
import {live} from './live.js';
import {lookOf,CANVAS} from './look.js';
import {FRAMES,FAIR_FRAMES,FRAME,BACKDROPS,FAIR_BACKDROPS,PROPS,STICKERS,FAIR_STICKERS,FAIR_FILTERS,draw as drawPrint,paintShot,thumb} from './photo-frames.js';
import {POSES,POSE,known as knownPose,paintPeople,poseThumb} from './booth-poses.js';
import {t as tr} from './i18n.js';

const SHOOTER={name:'Chị Mai chụp ảnh',emoji:'👩🏻‍🦰',
  idle:['Vô đây chụp tấm hình kỷ niệm đi nè! Một mình, rủ bạn, hay chụp chung với người lạ cũng vui!','Khung nào cũng đẹp hết, chọn đi rồi tạo dáng nha!','Bốn kiểu một lượt, in ra một dải xinh xắn mang về!'],
  wait:['Chờ chút nha, để chị kêu thêm người vô chụp chung.','Hội đông lắm, chắc có người ghé liền à.'],
  room:['Đông vui quá! Chọn dáng đi rồi sẵn sàng nha.','Ai cũng sẵn sàng là chụp liền!'],
  shoot:['Cười lên nào!','Tạo dáng đi, sắp chụp rồi!','Đẹp lắm, giữ nguyên nha!'],
  done:['Xinh xỉu! Lưu ảnh về máy liền nha.','Dải ảnh đẹp quá trời, chụp thêm lượt nữa không?']};
const PROP_IDS=new Set(PROPS.map(p=>p.id));
// the booth's frames: its own first, then the photobooth career's best for the fair, then the rest
const FIRST=['dem_hoi','tet','kawaii','pho_co','retro','trung_thu'];
const BOOTH_FRAMES=[...FAIR_FRAMES,...FIRST.map(id=>FRAME[id]).filter(Boolean),...FRAMES.filter(f=>!FIRST.includes(f.id))];
const BGS=[...FAIR_BACKDROPS,...BACKDROPS],BG_IDS=new Set(BGS.map(b=>b.id));
const STICKS=[...STICKERS,...FAIR_STICKERS];
// the words on the strip
const TEXTS=[['hoi','🏮','Hội chợ','Hội chợ Phố Có Chuyện'],['vui','🎉','Vui hết nấc','Vui hết nấc!'],['ban','💞','Bạn thân','Bạn thân mãi đỉnh'],['none','🚫','Không chữ','']];
const SHOTS=4,GAP=3200,STICKER_MAX=8,TICKET='mnl.fair.pbticket',PRINT_SCALE=3;
const CELL=[260,162];   // one photo of the strip (./photo-frames.js stripBox): the stage has its shape

export function setup(ctx){
  const {S,F,btn,say,xu,esc,send,render,sfx,pick,reduce}=ctx;
  const D=S.pb={step:'lobby',mode:null,room:null,me:null,frame:'hoi_dem',bg:'day_den',pose:'dung',prop:'none',say:'',
    ticket:readTicket(),paying:false,ready:false,waitUntil:0,shoot:null,shots:[],flash:0,count:0,filter:'none',stickers:[],
    text:'hoi',date:true,tab:'solo',
    url:'',blob:null,building:false,cv:null,raf:0,thumbs:{},sent:{},pendingJoin:false,tick:0};
  const P=()=>F().photo||null;

  /* ---- the ticket: paid once, used by the next shoot (kept in this tab if the room breaks up first) ---- */
  function readTicket(){try{return sessionStorage.getItem(TICKET)==='1';}catch{return false;}}
  function keepTicket(on){D.ticket=on;try{on?sessionStorage.setItem(TICKET,'1'):sessionStorage.removeItem(TICKET);}catch{/* storage blocked */}}
  async function pay(){
    if(D.ticket)return true;
    if(D.paying||S.busy)return false;
    D.paying=true;S.flash=null;render();
    const r=await send('fair_photo',{mode:D.mode||'solo'});
    D.paying=false;
    if(r?.fair?.game==='photo'){keepTicket(true);sfx('open');return true;}
    render();return false;
  }
  const canPay=()=>D.ticket||!!P()?.ok;
  const payWhy=()=>D.ticket?'':P()?.why||'';

  /* ---- who is in the booth ---- */
  const myState=()=>S.env?.api?.state||{};
  const shared=()=>Boolean(live.flags?.booth)&&live.state==='open';
  const inRoom=()=>D.step!=='lobby'&&D.step!=='wait'&&D.mode!=='solo'&&!!D.room;
  const isHost=()=>D.mode==='solo'||D.room?.host===D.me;
  function people(){
    if(D.mode!=='solo'&&D.room)return D.room.people||[];
    const st=myState();
    return [{pid:'me',name:st.name||tr('Bạn'),lk:lookOf(st),g:st.journey?.gender??null,pose:D.pose,prop:D.prop,ready:true}];
  }
  const frameId=()=>{const id=D.mode!=='solo'&&D.room?D.room.frame:D.frame;return FRAME[id]?id:'dem_hoi';};
  const bgId=()=>{const id=D.mode!=='solo'&&D.room?D.room.bg:D.bg;return BG_IDS.has(id)?id:'kem';};
  const many=()=>D.mode!=='solo'&&!!D.room&&(D.room.people||[]).length>1;
  const mine=()=>people().find(p=>p.pid===D.me||D.mode==='solo')||null;
  const look=()=>{const st=myState();return {look:lookOf(st),g:st.journey?.gender??null};};

  /* ---- the live room (live/booth.py) ---- */
  function wire(){
    if(wire.done)return;wire.done=true;
    live.on('booth_room',f=>{
      const fresh=!D.room||D.room.room!==f.room;
      D.room=f;D.me=f.me;D.pendingJoin=false;
      if(D.step==='lobby'||D.step==='wait'){D.step='room';D.mode=f.mode==='stranger'?'stranger':'friends';D.say=pick(SHOOTER.room);sfx('open');}
      const me=(f.people||[]).find(p=>p.pid===f.me);if(me){if(me.pose!==D.pose&&POSE[me.pose]?.group)D.tab='group';D.pose=knownPose(me.pose)?me.pose:'dung';D.prop=PROP_IDS.has(me.prop)?me.prop:'none';D.ready=!!me.ready;}
      if(fresh)S.flash=null;
      redraw();
    });
    live.on('booth_wait',f=>{D.step='wait';D.waitUntil=Date.now()+(Number(f.secs)||60)*1000;D.say=pick(SHOOTER.wait);redraw();});
    live.on('booth_none',()=>{if(D.step!=='wait')return;D.step='lobby';D.mode=null;S.flash={text:'Chưa có ai ghé chụp chung. Lát thử lại, hoặc chụp một mình nha.',kind:'warn'};redraw();});
    live.on('booth_left',f=>{
      if(f.why==='cancel'||f.why==='out')return;   // my own going: already back in the lobby
      const why={other:'Bạn đã vào buồng chụp ở một thẻ khác.',kick:'Chủ phòng đã mời bạn ra khỏi phòng.',blocked:'Bạn đã rời phòng chụp.',idle:'Phòng chụp đã đóng vì lâu không ai chụp.'}[f.why]||'Bạn đã rời phòng chụp.';
      toLobby();S.flash={text:why,kind:'warn'};redraw();
    });
    live.on('booth_shoot',f=>{if(D.mode==='solo'||!D.room)return;startShoot(Number(f.n)||SHOTS,Number(f.gap)||GAP);});
    live.on('error',f=>{
      if(typeof f.ref!=='string'||!f.ref.startsWith('booth_'))return;
      D.pendingJoin=false;
      if(f.ref==='booth_find'||f.ref==='booth_make'||f.ref==='booth_join'){if(D.step==='wait'&&f.ref==='booth_find')D.step='lobby';if(!D.room)D.mode=null;}
      S.flash={text:f.msg||'Chưa làm được, thử lại nha.',kind:'bad'};redraw();
    });
    const lost=()=>{if(D.step==='lobby'||D.mode==='solo'||!D.mode)return;toLobby();S.flash={text:'Mất kết nối, phòng chụp đã đóng. Vé chưa dùng vẫn giữ cho lượt sau.',kind:'warn'};redraw();};
    live.on('down',lost);live.on('welcome',lost);
  }
  function redraw(){if(S.tab==='pb'&&S.dlg?.open)render();else drawStage();}
  function toLobby(){stopLoop();D.step='lobby';D.tab='solo';D.mode=null;D.room=null;D.ready=false;D.shoot=null;D.pendingJoin=false;}

  /** Leave whatever shared thing is going on (the tab changes, the sheet closes). */
  function leave(){
    if(D.step==='wait')live.send({t:'booth_cancel'});
    else if(D.mode&&D.mode!=='solo'&&D.room)live.send({t:'booth_out'});
    if(D.step!=='print'||D.mode!=='solo')toLobby();
    if(D.step==='lobby')D.shots=[];
  }

  /* ---- actions ---- */
  function startSolo(){D.mode='solo';D.room=null;D.me='me';D.step='room';D.say=pick(SHOOTER.room);S.flash=null;render();}
  function find(){if(!shared())return;D.mode='stranger';S.flash=null;if(live.send({t:'booth_find',...look()})){D.step='wait';D.waitUntil=Date.now()+60000;D.say=pick(SHOOTER.wait);}render();}
  function make(){if(!shared())return;D.mode='friends';S.flash=null;D.pendingJoin=live.send({t:'booth_make',...look()});render();}
  function join(){
    if(!shared())return;
    const el=S.dlg?.querySelector('.fh-pb-code'),code=(el?.value||'').trim().toUpperCase();
    if(!/^[A-Z0-9]{4}$/.test(code)){S.flash={text:'Mã phòng có 4 ký tự, gồm chữ và số nha.',kind:'warn'};render();el?.focus();return;}
    D.mode='friends';S.flash=null;D.pendingJoin=live.send({t:'booth_join',code,...look()});render();
  }
  /** k: frame, bg (the host), pose, prop (one's own). A group pose (or the 🎲 with friends) is for everyone in the
   * room: booth_set {pose, all: true} (an older live service reads only `pose`: then it is one's own). */
  function set(k,v,all=false){
    if(k==='pose'&&!knownPose(v))return;if(k==='prop'&&v!=='none'&&!PROP_IDS.has(v))return;
    if(k==='frame'&&!FRAME[v])return;if(k==='bg'&&!BG_IDS.has(v))return;
    D[k]=v;
    if(D.mode!=='solo'&&D.room){
      if((k==='frame'||k==='bg')&&!isHost())return;
      const everyone=k==='pose'&&(all||POSE[v]?.group)&&many();
      live.send(everyone?{t:'booth_set',pose:v,all:true}:{t:'booth_set',[k]:v});
      if(k==='frame'||k==='bg')D.room[k]=v;
      else for(const p of D.room.people)if(p.pid===D.me||everyone)p[k]=v;
    }
    sfx('mark');redraw();
  }
  /** 🎲: a pose for me; with friends, often one made together, for the whole room. */
  function dice(){
    const cur=mine()?.pose||D.pose,group=many()&&Math.random()<.65;
    const pool=POSES.filter(p=>p.group===group&&p.id!==cur&&p.id!=='dung');
    const pick1=pool[Math.floor(Math.random()*pool.length)];
    if(pick1){if(pick1.group)D.tab='group';else if(!many())D.tab='solo';set('pose',pick1.id,many());}
  }
  async function ready(){
    if(D.ready||!inRoom())return;
    if(!await pay())return;
    if(live.send({t:'booth_ready'})){D.ready=true;sfx('mark');}
    render();
  }
  async function shootSolo(){
    if(D.mode!=='solo'||D.shoot)return;
    if(!await pay())return;
    startShoot(SHOTS,GAP);
  }
  function go(){if(!inRoom()||!isHost())return;live.send({t:'booth_go'});}
  function kick(pid){if(isHost()&&pid!==D.me)live.send({t:'booth_kick',pid});}
  function out(){
    if(D.step==='wait')live.send({t:'booth_cancel'});else if(D.mode!=='solo'&&D.room)live.send({t:'booth_out'});
    toLobby();D.shots=[];D.say='';S.flash=null;render();
  }
  async function copyCode(){
    const code=D.room?.code||'';if(!code)return;
    let ok=false;try{await navigator.clipboard.writeText(code);ok=true;}catch{/* no clipboard */}
    S.flash={text:ok?`Đã chép mã ${code}, gửi cho bạn bè nha.`:`Mã phòng là ${code}, đọc cho bạn bè nha.`,kind:'good'};render();
  }

  /* ---- the shoot: a 3-2-1 before each of the four shots, drawn from the room as it is at that moment ---- */
  function startShoot(n,gap){
    keepTicket(false);D.ready=false;
    D.shots=[];D.url='';D.blob=null;D.filter='none';D.stickers=[];
    D.shoot={t0:performance.now(),n:Math.max(1,Math.min(4,n)),gap:Math.max(1500,Math.min(6000,gap)),done:0,last:0};
    D.step='shoot';D.say=pick(SHOOTER.shoot);S.flash=null;render();loop();
  }
  function capture(){
    const ppl=people().map(p=>({pid:p.pid,name:p.name,lk:p.lk,g:p.g,pose:knownPose(p.pose)?p.pose:'dung',prop:PROP_IDS.has(p.prop)?p.prop:'none'}));
    const shot={people:ppl,bg:bgId()};
    try{const cv=document.createElement('canvas');cv.width=CELL[0];cv.height=CELL[1];paintCell(cv.getContext('2d'),shot,CELL[0],CELL[1]);shot.mini=cv;}catch{/* the stage goes without it */}
    shot.at=performance.now();D.shots.push(shot);D.flash=shot.at;sfx('shutter');
  }
  function tickShoot(now){
    const s=D.shoot;if(!s)return false;
    const due=s.t0+s.gap*(s.done+1);
    const left=Math.ceil((due-now)/1000);
    if(left!==s.last&&left>0&&left<=3){s.last=left;sfx('call');}
    D.count=left>0&&left<=3?left:0;
    if(now>=due){capture();s.done++;s.last=0;if(s.done>=s.n){D.shoot=null;D.count=0;setTimeout(()=>{D.step='print';D.say=pick(SHOOTER.done);render();build();},500);}else render();}
    return true;
  }
  function loop(){
    cancelAnimationFrame(D.raf);
    const step=()=>{D.raf=0;const now=performance.now();const on=tickShoot(now)||now-D.flash<520;drawStage(now);if(on&&S.dlg?.open)D.raf=requestAnimationFrame(step);};
    D.raf=requestAnimationFrame(step);
  }
  function stopLoop(){cancelAnimationFrame(D.raf);D.raf=0;D.shoot=null;D.count=0;}

  /* ---- drawing the characters (./booth-poses.js: the look, the pose, the prop; whole, side by side) ---- */
  /** One photo of w × h: the backdrop (./photo-frames.js), then the people, the first on the left. Returns their x. */
  function paintCell(c,shot,w,h,scale=0){
    paintShot(c,{backdrop:shot.bg||'kem',people:[],light:'soft'},w,h);
    try{return paintPeople(c,shot.people||[],w,h,{sign:tr('VUI QUÁ!'),scale});}catch(e){console.warn('chụp ảnh: look',e);return [];}
  }

  /* ---- the stage: the booth seen from the camera, names under the people, the count, the flash ---- */
  function drawStage(now=performance.now()){
    const cv=D.cv;if(!cv?.isConnected)return;
    const c=cv.getContext('2d'),W=CELL[0],H=CELL[1],k=cv.width/W;
    c.setTransform(k,0,0,k,0,0);c.clearRect(0,0,W,H);
    const ppl=D.step==='lobby'?people().slice(0,1):people();
    const at=paintCell(c,{people:ppl,bg:bgId()},W,H);
    // the curtain's edges and the marquee over the booth (its bulbs run while the camera counts)
    const g=c.createLinearGradient(0,0,22,0);g.addColorStop(0,'#8f1f2a');g.addColorStop(1,'#c8323a00');c.fillStyle=g;c.fillRect(0,0,22,H);
    const g2=c.createLinearGradient(W,0,W-22,0);g2.addColorStop(0,'#8f1f2a');g2.addColorStop(1,'#c8323a00');c.fillStyle=g2;c.fillRect(W-22,0,22,H);
    const fast=D.count?110:260;
    for(let i=0;i<13;i++){const on=reduce()||Math.floor(now/fast+i)%3!==0;CANVAS.E(c,6+i*(W-12)/12,4,2.6,2.6,on?'#ffe28a':'#b98f4a');}
    c.textAlign='center';c.textBaseline='middle';c.font='700 8px "Trebuchet MS",sans-serif';
    if(D.step!=='lobby')ppl.forEach((p,i)=>{
      const x=at[i]?.x??W*(i+.5)/ppl.length,room=ppl.length>1?Math.min(...at.map((a,j)=>j===i?Infinity:Math.abs(a.x-x)),W)-6:W*.6;
      const tick=p.ready&&D.mode!=='solo'?'✓ ':'';let name=String(p.name||tr('Khách đi hội')).slice(0,18);
      while(name.length>3&&c.measureText(tick+name).width+8>room)name=name.slice(0,-2)+'…';
      const tw=c.measureText(tick+name).width+8;
      c.fillStyle='rgba(255,250,240,.88)';c.beginPath();c.roundRect(x-tw/2,H-13,tw,11,5.5);c.fill();c.fillStyle='#4a3226';c.fillText(tick+name,x,H-7.2);});
    // the shots taken so far: small prints dropping in at the bottom right
    if(D.step==='shoot'){D.shots.forEach((sh,i)=>{if(!sh.mini)return;const age=now-(sh.at||0),drop=Math.min(1,age/380),x=W-28-i*7,y=H-26-(1-drop)*40;
      c.save();c.translate(x,y);c.rotate((i%2?.08:-.06));c.fillStyle='#fff';c.shadowColor='#0005';c.shadowBlur=3;c.fillRect(-15,-11,30,24);c.shadowColor='transparent';c.drawImage(sh.mini,-13.5,-9.5,27,17);c.restore();});
      c.font='800 9px "Trebuchet MS",sans-serif';
      const n=D.shoot?.n||SHOTS;for(let i=0;i<n;i++)CANVAS.E(c,W/2-(n-1)*6+i*12,15,3.4,3.4,i<D.shots.length?'#ffd36e':'#ffffff88');}
    if(D.count&&D.shoot){
      const s=D.shoot,due=s.t0+s.gap*(s.done+1),left=(due-now)/1000,frac=Math.max(0,Math.min(1,D.count-left)),pop=1+.35*Math.pow(1-Math.min(1,frac*3),2);
      c.fillStyle='#14082a3a';c.fillRect(0,0,W,H);
      c.save();c.translate(W/2,H/2-4);
      c.beginPath();c.arc(0,0,30,0,Math.PI*2);c.fillStyle='#ffffffd8';c.fill();
      c.lineWidth=4.5;c.lineCap='round';c.strokeStyle='#ffd36e55';c.beginPath();c.arc(0,0,30,0,Math.PI*2);c.stroke();
      c.strokeStyle='#ff8fab';c.beginPath();c.arc(0,0,30,-Math.PI/2,-Math.PI/2+Math.PI*2*frac);c.stroke();
      c.scale(pop,pop);c.font='900 38px "Trebuchet MS",sans-serif';c.fillStyle='#5a2d82';c.fillText(String(D.count),0,2);c.restore();
      const word=tr(D.count===3?'Sẵn sàng…':D.count===2?'Tạo dáng!':'Cười lên!');
      c.font='900 11px "Trebuchet MS",sans-serif';const ww=c.measureText(word).width+16;
      c.fillStyle='#5a2d82e6';c.beginPath();c.roundRect(W/2-ww/2,H/2+31,ww,16,8);c.fill();c.fillStyle='#fff';c.fillText(word,W/2,H/2+39.5);
    }
    const fl=now-D.flash;if(D.flash&&fl<520){const a=fl<80?.95:(1-(fl-80)/440)*.95;c.fillStyle=`rgba(255,255,255,${Math.max(0,a)})`;c.fillRect(0,0,W,H);}
  }

  /* ---- the strip ---- */
  const vnDate=()=>{const p=new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'2-digit',year:'2-digit',timeZone:'Asia/Ho_Chi_Minh'}).formatToParts(new Date());const g=t=>p.find(x=>x.type===t)?.value||'';return [g('day'),g('month'),g('year')];};
  const textOf=()=>(TEXTS.find(x=>x[0]===D.text)||TEXTS[0])[3];
  function printCanvas(scale=PRINT_SCALE){
    const cv=document.createElement('canvas'),[d,m,y]=vnDate(),names=[...new Set(D.shots.flatMap(s=>s.people.map(p=>p.name||'')).filter(Boolean))].slice(0,4).join(' · ');
    try{cv.getContext('2d',{willReadFrequently:true});}catch{/* the plain one */}
    // the same size of people in all four photos (the smallest one fits)
    let sc=Infinity;for(const sh of D.shots){try{sc=Math.min(sc,paintPeople(null,sh.people,CELL[0],CELL[1],{measure:true}));}catch{/* each fits on its own */}}
    const text=textOf();
    drawPrint(cv,{layout:'strip',shots:D.shots},frameId(),{stickers:D.stickers,filter:D.filter,title:text?tr(text):'',caption:D.date?`${d}/${m}/20${y}`:''},
      {scale,t:tr,brand:names,paintShot:(c,shot,w,h)=>paintCell(c,shot,w,h,Number.isFinite(sc)?sc:0)});
    return cv;
  }
  let building=0;
  function build(){
    if(!D.shots.length)return;
    const me=++building;D.building=true;
    setTimeout(()=>{
      if(me!==building)return;
      let cv;try{cv=printCanvas(2);}catch(e){console.warn('chụp ảnh: strip',e);D.building=false;render();return;}
      cv.toBlob(b=>{if(me!==building)return;if(D.url)URL.revokeObjectURL(D.url);D.blob=b;D.url=b?URL.createObjectURL(b):'';D.building=false;render();},'image/png');
    },30);
  }
  async function save(){
    if(!D.blob)return;
    const [d,m]=vnDate(),name=`hoi-cho-${d}-${m}-${Date.now()%100000}.png`;
    let file=null;try{file=new File([D.blob],name,{type:'image/png'});}catch{/* old browser */}
    if(matchMedia('(pointer: coarse)').matches&&file&&navigator.canShare?.({files:[file]})){
      try{await navigator.share({files:[file],title:tr('Ảnh hội chợ')});return;}catch(e){if(e?.name==='AbortError')return;}
    }
    const a=document.createElement('a');a.href=D.url;a.download=name;a.rel='noopener';document.body.append(a);a.click();a.remove();
    S.flash={text:'Đã lưu ảnh về máy. Trên iPhone: nhấn giữ ảnh để lưu.',kind:'good'};render();
  }
  function frameThumb(id){
    if(D.thumbs[id])return D.thumbs[id];
    try{const cv=document.createElement('canvas');thumb(cv,id,{scale:.3,t:tr});D.thumbs[id]=cv.toDataURL('image/png');}catch{D.thumbs[id]='';}
    return D.thumbs[id];
  }

  /* ---- the page ---- */
  const chip=(op,v,on,label,title,dis=false)=>`<button type="button" class="fh-pb-chip${on?' on':''}" data-fh="${op}" data-v="${esc(v)}" aria-pressed="${on}" data-fh-key="${op}-${esc(v)}" title="${esc(title)}"${dis?' disabled':''}>${label}</button>`;
  function stage(){return `<div class="fh-pb-booth"><div class="fh-pb-marquee" aria-hidden="true">📸 CHỤP ẢNH</div><div class="fh-pb-stage" data-fh-live data-fh-key="pb-stage"><canvas class="fh-pb-cv" role="img" aria-label="${esc(tr('Buồng chụp: các nhân vật trước phông'))}"></canvas></div></div>`;}
  function lobby(){
    const p=P(),why=shared()?'':'Buồng chụp chung đang nghỉ, chụp một mình nha.',busy=D.pendingJoin||S.busy;
    const card=(op,ico,title,sub,dis)=>`<button type="button" class="fh-pb-mode" data-fh="${op}" data-fh-key="${op}"${dis?' disabled':''}><span class="fh-pb-mico" aria-hidden="true">${ico}</span><span class="grow"><b>${title}</b><small>${sub}</small></span></button>`;
    return `${stage()}
      <div class="fh-pb-modes" role="group" aria-label="Cách chụp">
        ${card('pbsolo','🙋','Một mình','Chụp riêng nhân vật của bạn',false)}
        ${card('pbfind','🎲','Người lạ','Ghép với một người đang ở hội chợ',!shared()||busy)}
        ${card('pbmake','👫','Bạn bè · tạo phòng','Nhận mã phòng gửi cho bạn bè, tối đa 4 người',!shared()||busy)}
      </div>
      <div class="fh-pb-join"><label for="fh-pb-code">Có mã phòng của bạn bè?</label><div class="fh-pb-joinrow"><input id="fh-pb-code" class="fh-pb-code" data-fh-key="pb-code" maxlength="4" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="VD: A7K2"${shared()?'':' disabled'}>${btn(D.pendingJoin&&D.mode==='friends'?'Đang vào…':'Vào phòng','pbjoin',{},'primary',!shared()||busy?' disabled data-fh-key="pbjoin"':' data-fh-key="pbjoin"')}</div></div>
      ${why?`<p class="fh-why">${esc(why)}</p>`:''}
      <p class="fh-rule">Mỗi lượt chụp 4 kiểu, in thành một dải ảnh có khung. Mỗi người tự trả ${xu(p?.price||5)}${D.ticket?' (bạn đang có sẵn một vé chưa dùng)':''}. Ảnh chỉ nằm trên máy của bạn, không lưu lên đâu cả.</p>`;
  }
  function waiting(){
    const left=Math.max(0,Math.ceil((D.waitUntil-Date.now())/1000));
    return `${stage()}<div class="fh-card fh-pb-wait" role="status"><span class="fh-pb-spin" aria-hidden="true">🎲</span><div><b>Đang chờ người lạ ghé buồng…</b><small>Còn <span data-fh-count="pbwait">${left}</span> giây. Có người là vô chụp liền.</small></div></div>
      <div class="fh-go">${btn('Thôi, không chờ nữa','pbcancel',{},'ghost',' data-fh-key="pbcancel"')}</div>`;
  }
  function roomView(){
    const ppl=people(),host=isHost(),r=D.room,shooting=D.step==='shoot'||!!r?.shooting,me=mine();
    const code=D.mode==='friends'&&r?.code?`<div class="fh-pb-code-chip"><span>Mã phòng</span><b>${esc(r.code)}</b>${btn('📋 Chép mã','pbcopy',{},'cream small',' data-fh-key="pbcopy"')}</div>`:'';
    const list=D.mode==='solo'?'':`<ul class="fh-pb-people">${ppl.map(p=>`<li><span class="fh-pb-tick${p.ready?' on':''}" aria-hidden="true">${p.ready?'✓':'…'}</span><b>${esc(p.name||tr('Khách đi hội'))}</b>${p.pid===r.host?'<em>👑 chủ phòng</em>':''}${p.pid===D.me?'<em>bạn</em>':''}<small>${p.ready?'sẵn sàng':'đang chọn dáng'}</small>${host&&p.pid!==D.me&&D.mode==='friends'?btn('Mời ra','pbkick',{pid:p.pid},'ghost small',` data-fh-key="pbkick-${esc(p.pid)}"`):''}</li>`).join('')}${D.mode==='friends'&&ppl.length<(r.cap||4)?`<li class="empty"><span aria-hidden="true">＋</span><small>Còn ${(r.cap||4)-ppl.length} chỗ: gửi mã cho bạn bè</small></li>`:''}</ul>`;
    const fr=frameId(),frames=`<div class="fh-pb-sec"><b>Khung ảnh</b>${host?'':'<small>chủ phòng chọn</small>'}</div><div class="fh-pb-frames" role="group" aria-label="Khung ảnh">${BOOTH_FRAMES.map(f=>`<button type="button" class="fh-pb-frame${fr===f.id?' on':''}" data-fh="pbframe" data-v="${f.id}" aria-pressed="${fr===f.id}" data-fh-key="pbframe-${f.id}"${host&&!shooting?'':' disabled'}><img alt="" src="${frameThumb(f.id)}"><span><i aria-hidden="true">${f.emoji}</i> ${esc(f.name)}</span></button>`).join('')}</div>`;
    const bg=bgId(),bgs=`<div class="fh-pb-sec"><b>Phông nền</b></div><div class="fh-pb-chips" role="group" aria-label="Phông nền">${BGS.map(b=>chip('pbbg',b.id,bg===b.id,`<span aria-hidden="true">${b.emoji}</span> ${esc(b.name)}`,b.name,!host||shooting)).join('')}</div>`;
    const pose=me?.pose||D.pose,pr=me?.prop||D.prop;
    const poses=poseView(pose,shooting);
    const props=`<div class="fh-pb-sec"><b>Đạo cụ</b></div><div class="fh-pb-chips" role="group" aria-label="Đạo cụ">${chip('pbprop','none',pr==='none','<span aria-hidden="true">🚫</span> Không','Không')}${PROPS.map(p=>chip('pbprop',p.id,pr===p.id,`<span aria-hidden="true">${p.emoji}</span> ${esc(p.name)}`,p.name)).join('')}</div>`;
    let act='';
    const why=payWhy(),price=xu(P()?.price||5);
    if(D.step==='shoot')act=`<div class="fh-go"><span>📸 Đang chụp… nhìn vô máy nha!</span></div>`;
    else if(D.mode==='solo')act=`<div class="fh-go"><span>4 kiểu · ${D.ticket?'đã có vé':price}</span>${btn(D.paying?'Đang trả vé…':'📸 Chụp!','pbshoot',{},'primary big',!canPay()||D.paying?' disabled data-fh-key="pbshoot"':' data-fh-key="pbshoot"')}</div>`;
    else{
      const all=ppl.length>0&&ppl.every(p=>p.ready);
      const readyBtn=D.ready?'':btn(D.paying?'Đang trả vé…':D.ticket?'✋ Sẵn sàng (đã có vé)':`✋ Sẵn sàng · ${price}`,'pbready',{},host?'cream big':'primary big',!canPay()||D.paying||r?.shooting?' disabled data-fh-key="pbready"':' data-fh-key="pbready"');
      const goBtn=host?btn('📸 Chụp!','pbgo',{},'primary big',!all||r?.shooting?' disabled data-fh-key="pbgo"':' data-fh-key="pbgo"'):'';
      const line=r?.shooting?'Đang chụp, chờ lượt sau nha.':all?(host?'Mọi người sẵn sàng rồi!':'Chờ chủ phòng bấm chụp…'):D.ready?'Chờ mọi người sẵn sàng…':'Chọn dáng rồi bấm sẵn sàng';
      act=`<div class="fh-go fh-pb-act"><span>${esc(line)}</span>${readyBtn}${goBtn}</div>`;
    }
    return `${code}${stage()}${list}${act}${why&&!D.ticket&&D.step!=='shoot'?`<p class="fh-why">${esc(why)}: cần ${price} để chụp.</p>`:''}
      ${poses}${frames}${bgs}${props}
      <div class="fh-go">${btn(D.mode==='solo'?'‹ Đổi cách chụp':'Rời phòng','pbout',{},'ghost small',' data-fh-key="pbout"')}</div>`;
  }
  /** The pose picker: tiles of one's own character in each pose; with friends, the poses made together too. */
  function poseView(pose,shooting){
    const st=myState(),lk=lookOf(st),g=st.journey?.gender??null,grp=many();
    const tab=grp&&(D.tab==='group')?'group':'solo';
    const tabs=grp?`<div class="fh-pb-tabs" role="group" aria-label="Loại dáng">${[['solo','🙋','Một người'],['group','👯','Cả nhóm']].map(([v,e,n])=>`<button type="button" class="fh-pb-tab${tab===v?' on':''}" data-fh="pbtab" data-v="${v}" aria-pressed="${tab===v}" data-fh-key="pbtab-${v}"><span aria-hidden="true">${e}</span> ${n}</button>`).join('')}</div>`:'';
    const list=POSES.filter(p=>p.group===(tab==='group'));
    const tiles=list.map(p=>`<button type="button" class="fh-pb-pose${pose===p.id?' on':''}" data-fh="pbpose" data-v="${p.id}" aria-pressed="${pose===p.id}" data-fh-key="pbpose-${p.id}" title="${esc(p.name)}"><img alt="" src="${poseThumb(lk,g,p.id,128)}" width="64" height="64"><span><i aria-hidden="true">${p.emoji}</i> ${esc(p.name)}</span></button>`).join('');
    return `<div class="fh-pb-sec fh-pb-posehead"><b>Dáng</b>${shooting?'<small>đổi giữa các kiểu</small>':''}${btn('🎲 Ngẫu nhiên','pbdice',{},'cream small fh-pb-dice',' data-fh-key="pbdice"')}</div>
      ${tabs}${tab==='group'?'<p class="fh-pb-hint">Chọn là cả phòng cùng dáng</p>':''}<div class="fh-pb-poses" role="group" aria-label="Dáng">${tiles}</div>`;
  }
  function printView(){
    const img=D.url?`<img class="fh-pb-print" src="${D.url}" alt="${esc(tr('Dải ảnh hội chợ'))}">`:`<div class="fh-pb-print wait" role="status">${esc('Đang in ảnh…')}</div>`;
    const filters=`<div class="fh-pb-sec"><b>Màu ảnh</b></div><div class="fh-pb-chips" role="group" aria-label="Màu ảnh">${FAIR_FILTERS.map(f=>chip('pbfilter',f.id,D.filter===f.id,esc(f.name),f.name)).join('')}</div>`;
    const words=`<div class="fh-pb-sec"><b>Chữ</b></div><div class="fh-pb-chips" role="group" aria-label="Chữ">${TEXTS.map(([id,e,n])=>chip('pbtext',id,D.text===id,`<span aria-hidden="true">${e}</span> ${esc(n)}`,n)).join('')}${chip('pbdate','1',D.date,'<span aria-hidden="true">📅</span> Ngày','Ngày')}</div>`;
    const stickers=`<div class="fh-pb-sec"><b>Sticker</b><small>${D.stickers.length}/${STICKER_MAX}</small></div><div class="fh-pb-chips" role="group" aria-label="Sticker">${STICKS.map(s=>chip('pbsticker',s.id,D.stickers.includes(s.id),`<span aria-hidden="true">${s.emoji}</span> ${esc(s.name)}`,s.name,!D.stickers.includes(s.id)&&D.stickers.length>=STICKER_MAX)).join('')}</div>`;
    const again=D.mode==='solo'||D.room?btn('📸 Chụp lượt nữa','pbagain',{},'cream',' data-fh-key="pbagain"'):'';
    return `<div class="fh-pb-printbox">${img}</div>
      <div class="fh-go">${btn('⬇️ Lưu ảnh','pbsave',{},'primary big',D.blob?' data-fh-key="pbsave"':' disabled data-fh-key="pbsave"')}${again}</div>
      ${filters}${words}${stickers}
      <div class="fh-go">${btn(D.mode==='solo'?'‹ Về buồng chụp':'Rời phòng','pbout',{},'ghost small',' data-fh-key="pbout"')}</div>
      <p class="fh-rule">Bộ lọc và sticker chỉ đổi trên ảnh của bạn. Ảnh không lưu lên máy chủ: lưu về máy để giữ nha.</p>`;
  }
  function view(){
    if(!P())return '';
    wire();
    if(!D.say)D.say=pick(SHOOTER.idle);
    if(D.mode&&D.mode!=='solo'&&D.step!=='lobby'&&D.step!=='wait'&&D.step!=='print'&&!D.room&&!D.pendingJoin)toLobby();
    const body=D.step==='wait'?waiting():D.step==='print'?printView():D.step==='lobby'?lobby():roomView();
    return `<section class="fh-stall fh-pb" aria-label="Chụp ảnh">${say(SHOOTER,D.say)}${body}</section>`;
  }

  /** After every render: the stage canvas gets its size and a fresh frame; the code box its Enter key. */
  function mount(){
    const cv=S.dlg?.querySelector('.fh-pb-cv');
    if(cv&&!cv._pb){cv._pb=1;const size=()=>{const b=cv.getBoundingClientRect(),dpr=Math.min(2,globalThis.devicePixelRatio||1),w=Math.max(1,b.width);cv.width=Math.round(w*dpr);cv.height=Math.round(w*CELL[1]/CELL[0]*dpr);drawStage();};
      size();new ResizeObserver(size).observe(cv);}
    D.cv=cv||null;drawStage();
    const box=S.dlg?.querySelector('.fh-pb-code');
    if(box&&!box._pb){box._pb=1;box.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();join();}});box.addEventListener('input',()=>{const v=box.value.toUpperCase().replace(/[^A-Z0-9]/g,'').slice(0,4);if(v!==box.value)box.value=v;});}
    clearInterval(D.tick);
    if(D.step==='wait')D.tick=setInterval(()=>{const el=S.dlg?.querySelector('[data-fh-count="pbwait"]');if(!el||D.step!=='wait'){clearInterval(D.tick);return;}el.textContent=String(Math.max(0,Math.ceil((D.waitUntil-Date.now())/1000)));},1000);
  }
  function click(op,data){
    switch(op){
      case'pbsolo':startSolo();return true;
      case'pbfind':find();return true;
      case'pbmake':make();return true;
      case'pbjoin':join();return true;
      case'pbcancel':out();return true;
      case'pbout':if(D.step==='print'&&D.mode==='solo'){D.step='room';D.shots=[];render();}else out();return true;
      case'pbcopy':copyCode();return true;
      case'pbframe':set('frame',data.v);return true;
      case'pbbg':set('bg',data.v);return true;
      case'pbpose':set('pose',data.v);return true;
      case'pbprop':set('prop',data.v);return true;
      case'pbready':ready();return true;
      case'pbgo':go();return true;
      case'pbshoot':shootSolo();return true;
      case'pbkick':kick(data.pid);return true;
      case'pbdice':dice();return true;
      case'pbtab':if(data.v==='solo'||data.v==='group'){D.tab=data.v;render();}return true;
      case'pbfilter':if(FAIR_FILTERS.some(f=>f.id===data.v)){D.filter=data.v;build();render();}return true;
      case'pbtext':if(TEXTS.some(x=>x[0]===data.v)){D.text=data.v;build();render();}return true;
      case'pbdate':D.date=!D.date;build();render();return true;
      case'pbsticker':{const v=data.v;if(!STICKS.some(s=>s.id===v))return true;const i=D.stickers.indexOf(v);if(i>=0)D.stickers.splice(i,1);else if(D.stickers.length<STICKER_MAX)D.stickers.push(v);build();render();return true;}
      case'pbsave':save();return true;
      case'pbagain':D.step='room';D.shots=[];D.say=pick(SHOOTER.room);if(D.url){URL.revokeObjectURL(D.url);D.url='';D.blob=null;}render();return true;
    }
    return false;
  }
  const busy=()=>D.step==='shoot'||D.paying;
  const live_=()=>D.step!=='lobby';

  /* ---- test hooks (scripts/browser_fair_booth.py) ---- */
  globalThis.__fairBooth={state:()=>({shared:shared(),step:D.step,mode:D.mode,me:D.me,room:D.room&&{...D.room},ticket:D.ticket,ready:D.ready,shots:D.shots.length,url:!!D.url,frame:frameId(),bg:bgId(),filter:D.filter,stickers:[...D.stickers],
      pose:mine()?.pose||D.pose,text:D.text,date:D.date,count:D.count}),
    print:(scale=1)=>printCanvas(scale).toDataURL('image/png')};

  return {view,mount,click,leave,busy,live:live_};
}
