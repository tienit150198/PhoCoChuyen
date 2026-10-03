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
 * Always open (owner 03/10: "mở 24/24 chứ k được nghỉ"): the booth opened with the socket not open connects it at once
 * (live.reconnect(true), once per wait), shows "Đang nối buồng chung…" and redraws on the socket's welcome / down;
 * only after CONN_MS a line to try again. A lost socket in a friends' room comes back in by its code on the next
 * welcome (live/booth.py keeps the room for the last one in, GRACE_SECS); Một mình never needs the socket.
 * fair.js owns the dialog and passes its helpers in (setup); its render() patches the page in place and calls mount()
 * after: the booth's stage lives on a canvas in a data-fh-live slot, drawn when the room changes and by
 * requestAnimationFrame only while a shoot runs. */
import {live,liveBoot} from './live.js';
import {lookOf,figureOf,paintPlayer,CANVAS} from './look.js';
import {FRAMES,FRAME,BACKDROPS,PROPS,STICKERS,FILTERS,draw as drawPrint,paintShot,thumb} from './photo-frames.js';
import {t as tr} from './i18n.js';

const SHOOTER={name:'Chị Mai chụp ảnh',emoji:'👩🏻‍🦰',
  idle:['Vô đây chụp tấm hình kỷ niệm đi nè! Một mình, rủ bạn, hay chụp chung với người lạ cũng vui!','Khung nào cũng đẹp hết, chọn đi rồi tạo dáng nha!','Bốn kiểu một lượt, in ra một dải xinh xắn mang về!'],
  wait:['Chờ chút nha, để chị kêu thêm người vô chụp chung.','Hội đông lắm, chắc có người ghé liền à.'],
  room:['Đông vui quá! Chọn dáng đi rồi sẵn sàng nha.','Ai cũng sẵn sàng là chụp liền!'],
  shoot:['Cười lên nào!','Tạo dáng đi, sắp chụp rồi!','Đẹp lắm, giữ nguyên nha!'],
  done:['Xinh xỉu! Lưu ảnh về máy liền nha.','Dải ảnh đẹp quá trời, chụp thêm lượt nữa không?']};
const POSES=[['dung','🧍','Đứng thẳng'],['vay','👋','Vẫy tay'],['v','✌️','Chữ V'],['tim','🫶','Thả tim'],['hoan_ho','🙌','Hoan hô'],['nhay','🤸','Nhảy lên'],['nghieng','😊','Nghiêng đầu']];
const POSE_IDS=new Set(POSES.map(p=>p[0]));
const PROP_IDS=new Set(PROPS.map(p=>p.id));
const ARMS={vay:{r:[38,-98]},v:{r:[30,-84]},tim:{l:[-8,-56],r:[8,-56]},hoan_ho:{l:[-40,-104],r:[40,-104]},nhay:{l:[-40,-108],r:[40,-108]}};
const SHOTS=4,GAP=3200,STICKER_MAX=8,TICKET='mnl.fair.pbticket',CONN_MS=10000;
const CELL=[260,162];   // one photo of the strip (./photo-frames.js stripBox): the stage has its shape

export function setup(ctx){
  const {S,F,btn,say,xu,esc,send,render,sfx,pick,reduce}=ctx;
  const D=S.pb={step:'lobby',mode:null,room:null,me:null,frame:'dem_hoi',bg:'kem',pose:'dung',prop:'none',say:'',
    ticket:readTicket(),paying:false,ready:false,waitUntil:0,shoot:null,shots:[],flash:0,count:0,filter:'none',stickers:[],
    url:'',blob:null,building:false,cv:null,raf:0,thumbs:{},sent:{},pendingJoin:false,tick:0,
    conn0:0,connTimer:0,rejoin:'',back:null};   // since when the socket is awaited; a friends' room's code to come back to
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
  const bgId=()=>{const id=D.mode!=='solo'&&D.room?D.room.bg:D.bg;return BACKDROPS.some(b=>b.id===id)?id:'kem';};
  const mine=()=>people().find(p=>p.pid===D.me||D.mode==='solo')||null;
  const look=()=>{const st=myState();return {look:lookOf(st),g:st.journey?.gender??null};};

  /* ---- the socket: connected at once when the booth needs it, once per wait (never a loop: live.js backs off) ---- */
  function wake(again=false){
    if(shared()){D.conn0=0;return;}
    if(D.conn0&&!again)return;
    D.conn0=Date.now();
    try{if(!liveBoot.done&&S.env)liveBoot(S.env);live.reconnect(true);}catch(e){console.warn('chụp ảnh: live',e);}
  }
  const slowConn=()=>!shared()&&D.conn0&&Date.now()-D.conn0>=CONN_MS;

  /* ---- the live room (live/booth.py) ---- */
  function wire(){
    if(wire.done)return;wire.done=true;
    live.on('booth_room',f=>{
      const fresh=!D.room||D.room.room!==f.room,back=D.back;
      D.room=f;D.me=f.me;D.pendingJoin=false;D.back=null;D.rejoin='';
      if(D.step==='lobby'||D.step==='wait'){D.step='room';D.mode=f.mode==='stranger'?'stranger':'friends';D.say=pick(SHOOTER.room);sfx('open');}
      const me=(f.people||[]).find(p=>p.pid===f.me);if(me){D.pose=POSE_IDS.has(me.pose)?me.pose:'dung';D.prop=PROP_IDS.has(me.prop)?me.prop:'none';D.ready=!!me.ready;}
      if(fresh||back)S.flash=null;
      if(back&&me){const k={};if(back.pose!==D.pose)k.pose=back.pose;if(back.prop!==D.prop)k.prop=back.prop;   // my pose and prop as they were
        if(Object.keys(k).length&&live.send({t:'booth_set',...k})){Object.assign(me,k);D.pose=k.pose||D.pose;D.prop=k.prop||D.prop;}}
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
      if(f.ref==='booth_join'&&D.back){D.back=null;roomGone();redraw();return;}   // the room did not wait (an older service, too long away)
      if(f.ref==='booth_find'||f.ref==='booth_make'||f.ref==='booth_join'){if(D.step==='wait'&&f.ref==='booth_find')D.step='lobby';if(!D.room)D.mode=null;}
      S.flash={text:f.msg||'Chưa làm được, thử lại nha.',kind:'bad'};redraw();
    });
    live.on('down',()=>{
      if(!D.conn0&&S.tab==='pb'&&S.dlg?.open)D.conn0=Date.now();   // live.js tries again on its own: wait CONN_MS before "Thử lại"
      D.pendingJoin=false;if(D.step==='lobby')D.mode=null;   // a make / join on its way went with the socket
      if(D.step!=='lobby'&&D.mode&&D.mode!=='solo'){
        if(D.mode==='friends'&&D.room?.code&&D.step!=='wait'){D.rejoin=D.room.code;S.flash={text:'Mất kết nối, đang nối lại phòng…',kind:'warn'};}   // back in by the code on the welcome
        else roomGone();
      }
      redraw();
    });
    live.on('welcome',()=>{
      D.conn0=0;
      if(D.rejoin&&D.room&&D.mode==='friends'){
        const code=D.rejoin;D.rejoin='';D.back={pose:D.pose,prop:D.prop};
        D.pendingJoin=live.send({t:'booth_join',code,...look()});
        if(!D.pendingJoin){D.back=null;roomGone();}
      }else if(D.step!=='lobby'&&D.mode&&D.mode!=='solo')roomGone();
      redraw();
    });
  }
  /** The shared room is gone with the socket: the lobby (a strip already printed stays on screen). */
  function roomGone(){
    D.rejoin='';
    if(D.step==='print'){D.room=null;return;}
    toLobby();S.flash={text:'Mất kết nối, phòng chụp đã đóng. Vé chưa dùng vẫn giữ cho lượt sau.',kind:'warn'};
  }
  function redraw(){if(S.tab==='pb'&&S.dlg?.open)render();else drawStage();}
  function toLobby(){stopLoop();D.step='lobby';D.mode=null;D.room=null;D.ready=false;D.shoot=null;D.pendingJoin=false;D.rejoin='';D.back=null;}

  /** Leave whatever shared thing is going on (the tab changes, the sheet closes). */
  function leave(){
    D.conn0=0;clearTimeout(D.connTimer);
    if(D.step==='wait')live.send({t:'booth_cancel'});
    else if(D.mode&&D.mode!=='solo'&&D.room)live.send({t:'booth_out'});
    if(D.step!=='print'||D.mode!=='solo')toLobby();
    if(D.step==='lobby')D.shots=[];
  }

  /* ---- actions ---- */
  function startSolo(){D.mode='solo';D.room=null;D.me='me';D.step='room';D.say=pick(SHOOTER.room);S.flash=null;render();}
  function find(){if(!shared()){wake(true);render();return;}D.mode='stranger';S.flash=null;if(live.send({t:'booth_find',...look()})){D.step='wait';D.waitUntil=Date.now()+60000;D.say=pick(SHOOTER.wait);}render();}
  function make(){if(!shared()){wake(true);render();return;}D.mode='friends';S.flash=null;D.pendingJoin=live.send({t:'booth_make',...look()});render();}
  function join(){
    if(!shared()){wake(true);render();return;}
    const el=S.dlg?.querySelector('.fh-pb-code'),code=(el?.value||'').trim().toUpperCase();
    if(!/^[A-Z0-9]{4}$/.test(code)){S.flash={text:'Mã phòng có 4 ký tự, gồm chữ và số nha.',kind:'warn'};render();el?.focus();return;}
    D.mode='friends';S.flash=null;D.pendingJoin=live.send({t:'booth_join',code,...look()});render();
  }
  function set(k,v){
    if(k==='pose'&&!POSE_IDS.has(v))return;if(k==='prop'&&v!=='none'&&!PROP_IDS.has(v))return;
    if(k==='frame'&&!FRAME[v])return;if(k==='bg'&&!BACKDROPS.some(b=>b.id===v))return;
    D[k]=v;
    if(D.mode!=='solo'&&D.room){
      if((k==='frame'||k==='bg')&&!isHost())return;
      live.send({t:'booth_set',[k]:v});
      if(k==='frame'||k==='bg')D.room[k]=v;else{const me=D.room.people.find(p=>p.pid===D.me);if(me)me[k]=v;}
    }
    sfx('mark');redraw();
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
    const ppl=people().map(p=>({pid:p.pid,name:p.name,lk:p.lk,g:p.g,pose:POSE_IDS.has(p.pose)?p.pose:'dung',prop:PROP_IDS.has(p.prop)?p.prop:'none'}));
    D.shots.push({people:ppl,bg:bgId()});D.flash=performance.now();sfx('shutter');
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
    const step=()=>{D.raf=0;const now=performance.now();const on=tickShoot(now)||now-D.flash<450;drawStage(now);if(on&&S.dlg?.open)D.raf=requestAnimationFrame(step);};
    D.raf=requestAnimationFrame(step);
  }
  function stopLoop(){cancelAnimationFrame(D.raf);D.raf=0;D.shoot=null;D.count=0;}

  /* ---- drawing the characters ---- */
  /** One person (feet at the origin, 1 = the game's own size): their look, the pose, the prop. */
  function figure(c,p,t=0){
    const pose=POSE_IDS.has(p.pose)?p.pose:'dung',arms=ARMS[pose]||null,F0=figureOf(p.lk||{},p.g);
    c.save();
    if(pose==='nhay'){c.translate(0,-16);}
    if(pose==='nghieng')c.rotate(-.12);
    if(pose==='nhay'){c.save();c.translate(0,16);CANVAS.E(c,0,0,22,6,'#81644833');c.restore();}
    paintPlayer(c,F0,CANVAS,arms);
    if(pose==='v'){const [x,y]=arms.r;CANVAS.L(c,x-2,y-5,x-6,y-17,F0.skin.hand,3.4);CANVAS.L(c,x+2,y-5,x+5,y-17,F0.skin.hand,3.4);}
    if(pose==='tim')CANVAS.heart(c,0,-60,.5,'#e8335a');
    prop(c,p.prop,arms,F0);
    c.restore();
  }
  function star(c,x,y,R,r,fill){c.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,d=i%2?r:R;c.lineTo(x+Math.cos(a)*d,y+Math.sin(a)*d);}c.closePath();c.fillStyle=fill;c.fill();}
  function prop(c,id,arms,F0){
    const {R,E,L,P,heart,bloom}=CANVAS,hand=arms?.r||[25,-36],[hx,hy]=hand;
    switch(id){
      case'mu_tiec':c.save();c.translate(10,-112);c.rotate(.28);P(c,[[-14,0],[14,0],[0,-38]],'#5bb6d9');for(let i=1;i<4;i++){const y=-38*i/4,w=14*(1-i/4);L(c,-w,y,w,y,'#f2c84b',3);}E(c,0,-39,5,5,'#e2574c');c.restore();break;
      case'non_la':P(c,[[-46,-104],[46,-104],[0,-142]],'#efd79a');L(c,-46,-104,46,-104,'#c9a75a',2.5);L(c,-30,-115,30,-115,'#d8bc72',1.2);L(c,-16,-126,16,-126,'#d8bc72',1.2);break;
      case'mu_tn':P(c,[[-38,-118],[0,-132],[38,-118],[0,-104]],'#1f2a44');R(c,-20,-118,40,14,'#1f2a44',4);E(c,0,-118,3,2.4,'#f2c84b');L(c,0,-118,24,-113,'#f2c84b',1.6);L(c,24,-113,25,-98,'#f2c84b',3);break;
      case'tai_tho':c.strokeStyle='#ffffff';c.lineWidth=4;c.beginPath();c.arc(0,-84,34,Math.PI*1.1,Math.PI*1.9);c.stroke();
        for(const s of [-1,1]){c.save();c.translate(s*15,-130);c.rotate(s*.2);E(c,0,0,8,22,'#ffffff');E(c,0,2,4,15,'#ffb3cf');c.restore();}break;
      case'vuong_mien':P(c,[[-20,-110],[-21,-132],[-10,-120],[0,-136],[10,-120],[21,-132],[20,-110]],'#f2c84b');E(c,0,-117,3.2,3.2,'#e2574c');E(c,-12,-115,2.4,2.4,'#5bb6d9');E(c,12,-115,2.4,2.4,'#5bb6d9');break;
      case'kinh_tim':heart(c,-11,-75,.36,'#e8335a');heart(c,11,-75,.36,'#e8335a');L(c,-4,-80,4,-80,'#e8335a',2);break;
      case'kinh_ram':R(c,-21,-85,19,13,'#1d1d24',6);R(c,2,-85,19,13,'#1d1d24',6);L(c,-2,-80,2,-80,'#1d1d24',2);E(c,-15,-81,3,1.6,'#ffffff55');break;
      case'bang_chu':{R(c,-30,-44,60,26,'#fffaf0',5,'#c79879',2);const w=tr('VUI QUÁ!');c.font='900 11px "Trebuchet MS",sans-serif';c.fillStyle='#d0567f';c.textAlign='center';c.textBaseline='middle';c.fillText(w,0,-30.5,54);
        E(c,-29,-32,6,6,F0.skin.hand);E(c,29,-32,6,6,F0.skin.hand);break;}
      case'hoa':for(let i=0;i<5;i++)bloom(c,hx-7+(i%3)*7,hy-12+Math.floor(i/3)*7,6,['#ff8fab','#f2c84b','#ffffff','#d9506c','#ffb3cf'][i]);P(c,[[hx-8,hy-2],[hx+6,hy-2],[hx-1,hy+14]],'#9cc58a');E(c,hx,hy,6,6,F0.skin.hand);break;
      case'bong_bay':{const bx=hx+10,by=hy-58;c.strokeStyle='#9c7b6a';c.lineWidth=1.2;c.beginPath();c.moveTo(hx,hy);c.quadraticCurveTo(hx+14,hy-24,bx,by+20);c.stroke();
        E(c,bx,by,15,18,'#e2574c');P(c,[[bx-3,by+18],[bx+3,by+18],[bx,by+14]],'#e2574c');E(c,bx-5,by-6,3.4,6,'#ffffff66');E(c,hx,hy,6,6,F0.skin.hand);break;}
      case'long_den':{L(c,hx,hy,hx+8,hy-30,'#8b5e3c',2.4);const lx=hx+14,ly=hy-26;star(c,lx,ly+14,15,6.8,'#c0392b');star(c,lx,ly+14,11.5,5.2,'#f2c84b');E(c,lx,ly+14,2.6,2.6,'#fff3c4');E(c,hx,hy,6,6,F0.skin.hand);break;}
    }
  }
  /** One photo of w × h: the backdrop (./photo-frames.js), then the people side by side, the first on the left. */
  function paintCell(c,shot,w,h){
    paintShot(c,{backdrop:shot.bg||'kem',people:[],light:'soft'},w,h);
    const ppl=shot.people||[],n=Math.max(1,ppl.length),s=Math.min(h*.8/150,w/(n*64));   // the whole person, hats and ears in the picture
    ppl.forEach((p,i)=>{const x=w*(i+.5)/n,y=h*.96;c.save();c.translate(x,y);c.scale(s,s);try{figure(c,p);}catch(e){console.warn('chụp ảnh: look',e);}c.restore();});
  }

  /* ---- the stage: the booth seen from the camera, names under the people, the count, the flash ---- */
  function drawStage(now=performance.now()){
    const cv=D.cv;if(!cv?.isConnected)return;
    const c=cv.getContext('2d'),dpr=cv.width/Math.max(1,cv.clientWidth||1),W=CELL[0],H=CELL[1],k=cv.width/W;
    c.setTransform(k,0,0,k,0,0);c.clearRect(0,0,W,H);
    const ppl=D.step==='lobby'?people().slice(0,1):people();
    try{paintCell(c,{people:ppl,bg:bgId()},W,H);}catch(e){console.warn('chụp ảnh: stage',e);}
    // the curtain's edges and the marquee over the booth
    const g=c.createLinearGradient(0,0,22,0);g.addColorStop(0,'#8f1f2a');g.addColorStop(1,'#c8323a00');c.fillStyle=g;c.fillRect(0,0,22,H);
    const g2=c.createLinearGradient(W,0,W-22,0);g2.addColorStop(0,'#8f1f2a');g2.addColorStop(1,'#c8323a00');c.fillStyle=g2;c.fillRect(W-22,0,22,H);
    for(let i=0;i<13;i++){const on=reduce()||Math.floor(now/260+i)%3!==0;CANVAS.E(c,6+i*(W-12)/12,4,2.6,2.6,on?'#ffe28a':'#b98f4a');}
    const n=Math.max(1,ppl.length);c.textAlign='center';c.textBaseline='middle';c.font='700 8px "Trebuchet MS",sans-serif';
    ppl.forEach((p,i)=>{if(D.step==='lobby')return;const x=W*(i+.5)/n,name=String(p.name||tr('Khách đi hội')).slice(0,18),tw=c.measureText(name).width+(p.ready&&D.mode!=='solo'?14:8);
      c.fillStyle='rgba(255,250,240,.88)';c.beginPath();c.roundRect(x-tw/2,H-13,tw,11,5.5);c.fill();c.fillStyle='#4a3226';c.fillText((p.ready&&D.mode!=='solo'?'✓ ':'')+name,x,H-7.2);});
    if(D.count){c.fillStyle='#00000040';c.fillRect(0,0,W,H);c.font='900 64px "Trebuchet MS",sans-serif';c.fillStyle='#fff';c.strokeStyle='#4a2a66';c.lineWidth=4;c.strokeText(String(D.count),W/2,H/2+2);c.fillText(String(D.count),W/2,H/2+2);}
    const fl=now-D.flash;if(D.flash&&fl<450){c.fillStyle=`rgba(255,255,255,${(1-fl/450)*.92})`;c.fillRect(0,0,W,H);}
    if(D.step==='shoot'&&D.shoot){c.font='800 9px "Trebuchet MS",sans-serif';c.fillStyle='#fff';c.fillText(`${tr('Kiểu')} ${Math.min(D.shoot.n,D.shoot.done+1)}/${D.shoot.n}`,W-30,16);}
    void dpr;
  }

  /* ---- the strip ---- */
  const vnDate=()=>{const p=new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'2-digit',year:'2-digit',timeZone:'Asia/Ho_Chi_Minh'}).formatToParts(new Date());const g=t=>p.find(x=>x.type===t)?.value||'';return [g('day'),g('month'),g('year')];};
  function printCanvas(scale=2){
    const cv=document.createElement('canvas'),[d,m,y]=vnDate(),names=[...new Set(D.shots.flatMap(s=>s.people.map(p=>p.name||'')).filter(Boolean))].slice(0,4).join(' · ');
    drawPrint(cv,{layout:'strip',shots:D.shots},frameId(),{stickers:D.stickers,date:`${d}.${m}.${y}`,filter:D.filter,caption:`${tr('Hội chợ Phố Có Chuyện')} · ${d}/${m}`},
      {scale,t:tr,brand:names,paintShot:(c,shot,w,h)=>paintCell(c,shot,w,h)});
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
    const p=P(),busy=D.pendingJoin||S.busy;
    const conn=shared()?'':slowConn()?`<p class="fh-why" role="status">${esc('Chưa nối được buồng chung. Kiểm tra mạng rồi bấm Thử lại nha, chụp một mình vẫn được.')}</p><div class="fh-go">${btn('Thử lại','pbretry',{},'cream small',' data-fh-key="pbretry"')}</div>`
      :`<div class="fh-card fh-pb-wait" role="status"><span class="fh-pb-spin" aria-hidden="true">⏳</span><div><b>Đang nối buồng chung…</b><small>Chụp một mình thì vô liền được nha.</small></div></div>`;
    const card=(op,ico,title,sub,dis)=>`<button type="button" class="fh-pb-mode" data-fh="${op}" data-fh-key="${op}"${dis?' disabled':''}><span class="fh-pb-mico" aria-hidden="true">${ico}</span><span class="grow"><b>${title}</b><small>${sub}</small></span></button>`;
    return `${stage()}${conn}
      <div class="fh-pb-modes" role="group" aria-label="Cách chụp">
        ${card('pbsolo','🙋','Một mình','Chụp riêng nhân vật của bạn',false)}
        ${card('pbfind','🎲','Người lạ','Ghép với một người đang ở hội chợ',!shared()||busy)}
        ${card('pbmake','👫','Bạn bè · tạo phòng','Nhận mã phòng gửi cho bạn bè, tối đa 4 người',!shared()||busy)}
      </div>
      <div class="fh-pb-join"><label for="fh-pb-code">Có mã phòng của bạn bè?</label><div class="fh-pb-joinrow"><input id="fh-pb-code" class="fh-pb-code" data-fh-key="pb-code" maxlength="4" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="VD: A7K2"${shared()?'':' disabled'}>${btn(D.pendingJoin&&D.mode==='friends'?'Đang vào…':'Vào phòng','pbjoin',{},'primary',!shared()||busy?' disabled data-fh-key="pbjoin"':' data-fh-key="pbjoin"')}</div></div>
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
    const list=D.mode==='solo'?'':`<ul class="fh-pb-people">${ppl.map(p=>`<li><span class="fh-pb-tick${p.ready?' on':''}" aria-hidden="true">${p.ready?'✓':'…'}</span><b>${esc(p.name||tr('Khách đi hội'))}</b>${p.pid===r.host?'<em>👑 chủ phòng</em>':''}${p.pid===D.me?'<em>bạn</em>':''}<small>${p.away?'đang quay lại…':p.ready?'sẵn sàng':'đang chọn dáng'}</small>${host&&p.pid!==D.me&&D.mode==='friends'?btn('Mời ra','pbkick',{pid:p.pid},'ghost small',` data-fh-key="pbkick-${esc(p.pid)}"`):''}</li>`).join('')}${D.mode==='friends'&&ppl.length<(r.cap||4)?`<li class="empty"><span aria-hidden="true">＋</span><small>Còn ${(r.cap||4)-ppl.length} chỗ: gửi mã cho bạn bè</small></li>`:''}</ul>`;
    const fr=frameId(),frames=`<div class="fh-pb-sec"><b>Khung ảnh</b>${host?'':'<small>chủ phòng chọn</small>'}</div><div class="fh-pb-frames" role="group" aria-label="Khung ảnh">${FRAMES.map(f=>`<button type="button" class="fh-pb-frame${fr===f.id?' on':''}" data-fh="pbframe" data-v="${f.id}" aria-pressed="${fr===f.id}" data-fh-key="pbframe-${f.id}"${host&&!shooting?'':' disabled'}><img alt="" src="${frameThumb(f.id)}"><span><i aria-hidden="true">${f.emoji}</i> ${esc(f.name)}</span></button>`).join('')}</div>`;
    const bg=bgId(),bgs=`<div class="fh-pb-sec"><b>Phông nền</b></div><div class="fh-pb-chips" role="group" aria-label="Phông nền">${BACKDROPS.map(b=>chip('pbbg',b.id,bg===b.id,`<span aria-hidden="true">${b.emoji}</span> ${esc(b.name)}`,b.name,!host||shooting)).join('')}</div>`;
    const pose=me?.pose||D.pose,pr=me?.prop||D.prop;
    const poses=`<div class="fh-pb-sec"><b>Dáng của bạn</b>${shooting?'<small>đổi dáng giữa các kiểu nha</small>':''}</div><div class="fh-pb-chips" role="group" aria-label="Dáng">${POSES.map(([id,e,n])=>chip('pbpose',id,pose===id,`<span aria-hidden="true">${e}</span> ${esc(n)}`,n)).join('')}</div>`;
    const props=`<div class="fh-pb-sec"><b>Đạo cụ</b></div><div class="fh-pb-chips" role="group" aria-label="Đạo cụ">${chip('pbprop','none',pr==='none','<span aria-hidden="true">🚫</span> Không','Không')}${PROPS.map(p=>chip('pbprop',p.id,pr===p.id,`<span aria-hidden="true">${p.emoji}</span> ${esc(p.name)}`,p.name)).join('')}</div>`;
    let act='';
    const why=payWhy(),price=xu(P()?.price||5);
    if(D.step==='shoot')act=`<div class="fh-go"><span>📸 Đang chụp… nhìn vô máy nha!</span></div>`;
    else if(D.mode==='solo')act=`<div class="fh-go"><span>4 kiểu · ${D.ticket?'đã có vé':price}</span>${btn(D.paying?'Đang trả vé…':'📸 Chụp!','pbshoot',{},'primary big',!canPay()||D.paying?' disabled data-fh-key="pbshoot"':' data-fh-key="pbshoot"')}</div>`;
    else{
      const all=ppl.some(p=>!p.away)&&ppl.every(p=>p.ready||p.away);   // someone whose socket dropped (live/booth.py away) never holds the shoot
      const readyBtn=D.ready?'':btn(D.paying?'Đang trả vé…':D.ticket?'✋ Sẵn sàng (đã có vé)':`✋ Sẵn sàng · ${price}`,'pbready',{},host?'cream big':'primary big',!canPay()||D.paying||r?.shooting?' disabled data-fh-key="pbready"':' data-fh-key="pbready"');
      const goBtn=host?btn('📸 Chụp!','pbgo',{},'primary big',!all||r?.shooting?' disabled data-fh-key="pbgo"':' data-fh-key="pbgo"'):'';
      const line=r?.shooting?'Đang chụp, chờ lượt sau nha.':all?(host?'Mọi người sẵn sàng rồi!':'Chờ chủ phòng bấm chụp…'):D.ready?'Chờ mọi người sẵn sàng…':'Chọn dáng rồi bấm sẵn sàng';
      act=`<div class="fh-go fh-pb-act"><span>${esc(line)}</span>${readyBtn}${goBtn}</div>`;
    }
    return `${code}${stage()}${list}${act}${why&&!D.ticket&&D.step!=='shoot'?`<p class="fh-why">${esc(why)}: cần ${price} để chụp.</p>`:''}
      ${poses}${props}${frames}${bgs}
      <div class="fh-go">${btn(D.mode==='solo'?'‹ Đổi cách chụp':'Rời phòng','pbout',{},'ghost small',' data-fh-key="pbout"')}</div>`;
  }
  function printView(){
    const img=D.url?`<img class="fh-pb-print" src="${D.url}" alt="${esc(tr('Dải ảnh hội chợ'))}">`:`<div class="fh-pb-print wait" role="status">${esc('Đang in ảnh…')}</div>`;
    const filters=`<div class="fh-pb-sec"><b>Bộ lọc</b></div><div class="fh-pb-chips" role="group" aria-label="Bộ lọc">${FILTERS.map(f=>chip('pbfilter',f.id,D.filter===f.id,esc(f.name),f.name)).join('')}</div>`;
    const stickers=`<div class="fh-pb-sec"><b>Sticker</b><small>${D.stickers.length}/${STICKER_MAX}</small></div><div class="fh-pb-chips" role="group" aria-label="Sticker">${STICKERS.map(s=>chip('pbsticker',s.id,D.stickers.includes(s.id),`<span aria-hidden="true">${s.emoji}</span> ${esc(s.name)}`,s.name,!D.stickers.includes(s.id)&&D.stickers.length>=STICKER_MAX)).join('')}</div>`;
    const again=D.mode==='solo'||D.room?btn('📸 Chụp lượt nữa','pbagain',{},'cream',' data-fh-key="pbagain"'):'';
    return `<div class="fh-pb-printbox">${img}</div>
      <div class="fh-go">${btn('⬇️ Lưu ảnh','pbsave',{},'primary big',D.blob?' data-fh-key="pbsave"':' disabled data-fh-key="pbsave"')}${again}</div>
      ${filters}${stickers}
      <div class="fh-go">${btn(D.mode==='solo'?'‹ Về buồng chụp':'Rời phòng','pbout',{},'ghost small',' data-fh-key="pbout"')}</div>
      <p class="fh-rule">Bộ lọc và sticker chỉ đổi trên ảnh của bạn. Ảnh không lưu lên máy chủ: lưu về máy để giữ nha.</p>`;
  }
  function view(){
    if(!P())return '';
    wire();
    if(!D.say)D.say=pick(SHOOTER.idle);
    if(D.step==='lobby')wake();
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
    clearTimeout(D.connTimer);   // the "try again" line when the socket has not come in CONN_MS
    if(D.step==='lobby'&&D.conn0&&!shared()&&!slowConn())D.connTimer=setTimeout(()=>{if(D.step==='lobby'&&S.tab==='pb'&&S.dlg?.open)render();},CONN_MS-(Date.now()-D.conn0)+50);
    clearInterval(D.tick);
    if(D.step==='wait')D.tick=setInterval(()=>{const el=S.dlg?.querySelector('[data-fh-count="pbwait"]');if(!el||D.step!=='wait'){clearInterval(D.tick);return;}el.textContent=String(Math.max(0,Math.ceil((D.waitUntil-Date.now())/1000)));},1000);
  }
  function click(op,data){
    switch(op){
      case'pbsolo':startSolo();return true;
      case'pbfind':find();return true;
      case'pbmake':make();return true;
      case'pbjoin':join();return true;
      case'pbretry':wake(true);render();return true;
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
      case'pbfilter':if(FILTERS.some(f=>f.id===data.v)){D.filter=data.v;build();render();}return true;
      case'pbsticker':{const v=data.v;if(!STICKERS.some(s=>s.id===v))return true;const i=D.stickers.indexOf(v);if(i>=0)D.stickers.splice(i,1);else if(D.stickers.length<STICKER_MAX)D.stickers.push(v);build();render();return true;}
      case'pbsave':save();return true;
      case'pbagain':D.step='room';D.shots=[];D.say=pick(SHOOTER.room);if(D.url){URL.revokeObjectURL(D.url);D.url='';D.blob=null;}render();return true;
    }
    return false;
  }
  const busy=()=>D.step==='shoot'||D.paying;
  const live_=()=>D.step!=='lobby';

  /* ---- test hooks (scripts/browser_fair_booth.py) ---- */
  globalThis.__fairBooth={state:()=>({shared:shared(),step:D.step,mode:D.mode,me:D.me,room:D.room&&{...D.room},ticket:D.ticket,ready:D.ready,shots:D.shots.length,url:!!D.url,frame:frameId(),bg:bgId(),filter:D.filter,stickers:[...D.stickers]}),
    print:(scale=1)=>printCanvas(scale).toDataURL('image/png')};

  return {view,mount,click,leave,busy,live:live_};
}
