/** 🚶 Ở nhà: the player's character walks around inside the place they live in (the room drawn by v4/reno.js with
 * v4/deco-art.js), out of the decorating mode. Tap the floor to walk there, tap a piece to walk up to it and use it:
 *   🧊 a fridge opens the fridge (game/fridge.py: cất đồ ăn, lấy ra ăn, mua ăn liền); in the dorm the shared fridge is
 *      down the corridor, a card under the bunk opens it;
 *   🛏️ a bed: in the evening (state.needs.evening) the evening sheet (dinner, bedtime: v4/needs.js), else a line;
 *   🗄️ a wardrobe, a mirror, a dressing table: Tủ đồ (v4/wardrobe.js);
 *   🛁 the bathtub, the pool, a sun lounger: the relax act of the day (game/relax.py) when it can be done, else why not;
 *   anything else: a short line from the character in a bubble (nothing changes).
 * Like the fair's walk (v4/fair-walk.js) the player does the walking; like reno.js's cats the figure is one SVG group
 * moved by a CSS transition (no frame loop), frozen and resumed around a re-render. Reduced motion: it steps there.
 * reno.js owns the dialog and passes its helpers in (setup); every rule and number is the server's (deco.public
 * 'fridge'); a server from before sends no fridge and the fridge just says a line. */
import {figure,lookOf,figureSVG,wornColor} from './look.js';
import {escapeHTML as esc} from '../icons.js';
import {crowd} from './home-crowd.js';

const K=.42;                 // the figure (about 150 units tall) in room pixels
const SPEED=150;             // room pixels a second
const SAY_MS=4200;
const FRIDGES=new Set(['tu_lanh','tu_lanh_magnet']);
const WARDROBE=new Set(['tu_quan_ao','moc_ao','ban_trang_diem','guong']);
const CLOSET=new Set(['tu_quan_ao','moc_ao']);
const CLOTHES=new Set(['top','bottom','shoes','acc']);
const BEDS=new Set(['giuong','nem']);
const RELAX={bon_tam:'ngam',phao:'boi',phao_hong_hac:'boi',ghe_tam_nang:'nam'};
/* What the character says at a piece (one picked at random). Keys: item ids, then its category. */
const LINES={
  tv:['Bật ti vi xem dự báo thời tiết, mai trời nắng đẹp.','Chuyển kênh một vòng, toàn phim đã xem rồi.'],
  sofa:['Ngồi phịch xuống sofa, êm quá trời.','Dựa lưng vào sofa, nghỉ một chút đã.'],
  ban_lam_viec:['Ngồi vào bàn, lên kế hoạch cho ngày mai.','Sắp xếp lại giấy tờ trên bàn cho gọn.'],
  ban_hoc:['Mở sổ ra ôn lại mấy điều học được hôm nay.'],
  ke_sach:['Rút một cuốn sách ra đọc vài trang.','Kệ sách hơi bụi, lau sơ một chút.'],
  dan:['Gảy thử vài hợp âm, nghe cũng ra gì đó.'],dan_bau:['Gảy đàn bầu một khúc, tiếng ngân nghe thương ghê.'],
  be_ca:['Rắc chút thức ăn, đàn cá bơi lại đớp lia lịa.'],
  noi_com:['Nồi cơm còn ấm, thơm mùi gạo mới.'],lo_vi_song:['Lò vi sóng kêu tinh một tiếng, xong rồi.'],am_sieu_toc:['Đun ấm nước pha trà nóng.'],
  may_giat:['Bỏ đồ vào máy giặt, chiều phơi là khô.'],
  may_choi_game:['Chơi một ván game cho đỡ căng thẳng.'],loa:['Mở một bài nhạc nhẹ, phòng ấm hẳn lên.'],radio:['Vặn radio nghe tin tức buổi tối.'],
  cay_canh:['Tưới chút nước cho cây, lá xanh mướt.'],gau_bong:['Ôm gấu bông một cái cho đỡ mệt.'],
  ban_an:['Lau bàn ăn sạch sẽ.'],ban_tra:['Pha một ấm trà, ngồi nhâm nhi.'],
  table:['Ngồi nghỉ chân một chút.'],plant:['Tưới chút nước cho cây, lá xanh mướt.'],light:['Bật đèn lên, phòng sáng ấm hẳn.'],
  wall:['Ngắm nghía một chút, nhìn cũng xinh.'],fun:['Nghịch một chút cho vui.'],bed:['Sắp xếp lại góc này cho gọn.'],
  bath:['Rửa mặt cho tỉnh táo.'],pool:['Hít một hơi gió mát bên hồ.'],le:['Nhìn mà thấy Tết tới gần.'],
};
const BED_LINE=['Ngả lưng một chút cho đỡ mỏi. Tối rồi ngủ hẳn nhé.','Nằm nghe quạt chạy vù vù, suýt ngủ quên.'];
const FLOOR_LINE=['Đi một vòng quanh phòng.','Vươn vai một cái cho đỡ mỏi.'];
const pick=a=>a[Math.random()*a.length|0];

export function setup(ctx){
  const {S,A,roomOf,inRoom,hostFor,send,render,sfx,calm,roomSvg}=ctx;
  const W={room:'',x:0,y:0,to:null,until:0,timer:0,then:null,say:null,fridge:false,closet:null,note:null,walked:false};
  const st=()=>S.env?.api?.state||{};
  const FR=()=>S.remote?null:ctx.V?.()?.fridge||S.env?.api?.state?.journey?.deco?.fridge||null;
  const useRoom=rm=>[...inRoom(rm),...(ctx.mateIn?.(rm)||[])];
  const homeHost=()=>S.remote?.owner?.code||(ctx.V?.()?.place?.where==='own'?S.env.api.homeGuests?.own_home?.code||'':'');
  const homeScope=()=>{const sp=st().marriage?.spouse;return JSON.stringify([ctx.V?.()?.place?.key,sp?.pid,sp?.status,S.remote?.owner?.code||'']);};
  let crowdRender=0;
  // Replacing the room DOM during a gesture loses pointer capture and its furniture nodes.
  // Coalesce live events and wait for an idle dialog, including gestures started after scheduling.
  function redrawCrowd(){
    if(!S.dlg?.open||crowdRender)return;
    crowdRender=setTimeout(function flush(){
      crowdRender=0;if(!S.dlg?.open)return;
      if(S.busy||S.drag||S.press){crowdRender=setTimeout(flush,120);return;}
      // The short avatar pose can finish while the longer invitation is still open.
      // Restore that exact response control after replacing the room DOM.
      const focused=globalThis.document?.activeElement;
      const response=focused?.dataset?.dc==='hwReply'&&S.dlg?.contains?.(focused)
        ?{id:focused.dataset.id,answer:focused.dataset.answer}:null;
      render();
      if(response&&S.dlg?.open){
        const next=[...S.dlg.querySelectorAll('[data-dc="hwReply"]')]
          .find(el=>el.dataset.id===response.id&&el.dataset.answer===response.answer&&!el.disabled);
        next?.focus({preventScroll:true});
      }
    },16);
  }
  const HC=crowd({live:ctx.live,state:st,still:calm,svg:roomSvg,
    isWalking:()=>Boolean(W.to),
    redraw:redrawCrowd,
    xy:p=>{const rm=roomOf(S.room);if(!rm)return [0,0];const b=box(rm,A.geom(rm));return [b.x0+p[0]*(b.x1-b.x0),b.y0+p[1]*(b.y1-b.y0)];},
    approach:(p,then)=>{const rm=roomOf(S.room);if(!rm)return;const G=A.geom(rm),b=box(rm,G),x=b.x0+p[0]*(b.x1-b.x0),y=b.y0+p[1]*(b.y1-b.y0);
      walkTo(clampTo(rm,G,x+(x>(b.x0+b.x1)/2?-34:34),y+3),then,true);}});
  function fractions(p){const rm=roomOf(W.room);if(!rm)return [.5,.8];const b=box(rm,A.geom(rm));return [(p[0]-b.x0)/(b.x1-b.x0),(p[1]-b.y0)/(b.y1-b.y0)];}

  /* ---- where the feet may go ---- */
  function box(rm,G){return {x0:A.PX+12,x1:A.PX+rm.cols*A.CW-12,y0:G.FY+A.FR*.55,y1:G.FY+rm.frows*A.FR-3};}
  /** A point on the floor, out of the fixtures that keep pieces off (the pool, the counter, the door's cell). */
  function clampTo(rm,G,x,y){
    const b=box(rm,G);x=Math.max(b.x0,Math.min(b.x1,x));y=Math.max(b.y0,Math.min(b.y1,y));
    for(const f of rm.fix||[]){
      if(f.layer!=='floor'||!f.block)continue;
      const fx0=A.PX+f.x*A.CW,fx1=fx0+f.w*A.CW,fy0=G.FY+f.y*A.FR,fy1=fy0+f.h*A.FR;
      if(x>fx0-4&&x<fx1+4&&y>fy0-2&&y<fy1+6){
        if(fy1+8<=b.y1)y=fy1+8;
        else x=x-fx0<fx1-x?Math.max(b.x0,fx0-10):Math.min(b.x1,fx1+10);
      }
    }
    return [x,y];
  }
  /** Where to stand to use a placed piece: in front of it (under it for a wall piece; a small thing: its host's front). */
  function standFor(rm,G,o,list){
    const it=o.it,q=o.q,host=hostFor(rm,q,list);
    if(host?.it)return standFor(rm,G,{it:host.it,q:host.q,id:q.on},list);
    const a=A.anchor(it,q,G,host),cx=a[0]+it.w*A.CW/2;
    if(host?.fix){const f=host.fix;return clampTo(rm,G,cx,f.layer==='wall'?G.FY+A.FR*.7:G.FY+(f.y+f.h)*A.FR+8);}
    if(it.spot==='wall')return clampTo(rm,G,cx,G.FY+A.FR*.7);
    if(it.spot==='top')return clampTo(rm,G,cx,a[1]+10);
    return clampTo(rm,G,cx,a[1]+12);
  }
  /** Coming into a room: in front of its door, else in the middle at the front. */
  function enter(rm,G){
    const d=(rm.fix||[]).find(f=>f.t==='door'&&f.layer==='floor'),b=box(rm,G);
    const p=d?clampTo(rm,G,A.PX+(d.x+.5)*A.CW,G.FY+A.FR*1.2):clampTo(rm,G,(b.x0+b.x1)/2,b.y1-6);
    if(ctx.V?.()?.place?.where==='shared')p[0]=Math.min(b.x1,p[0]+28);
    stop();W.room=rm.id;W.x=p[0];W.y=p[1];W.say=null;
  }

  /* ---- the figure ---- */
  function markup(rm,G){
    if(W.room!==rm.id)enter(rm,G);
    const out=[];try{out.push(HC.figure(figure(st())));}catch{/* look not ready */}
    const at=W.to||{x:W.x,y:W.y};
    return `<g class="hw-me" data-y="${at.y}" aria-hidden="true" style="transform:translate(${W.x.toFixed(1)}px,${W.y.toFixed(1)}px)" data-to="${at.x.toFixed(1)},${at.y.toFixed(1)}"><g class="hw-fig${W.to?' walk':''}"><g transform="scale(${K})">${out.join('')}</g></g></g>${HC.markup(W.room,homeScope())}`;
  }
  const meEl=()=>roomSvg()?.querySelector('.hw-me');
  /** Put the figure among the pieces by where its feet are going: behind what stands further forward (reno.js marks each
   * floor piece with its front edge, data-y; the spouse's pieces in a shared home too). */
  function order(){
    const el=meEl();if(!el)return;
    const y=W.to?.y??W.y;el.dataset.y=String(y);
    const next=[...el.parentNode.querySelectorAll(':scope>g.dc-it[data-y],:scope>g.dc-mate[data-y],:scope>g.hc-person[data-y]')].find(g=>+g.dataset.y>y+2);
    const before=next||el.parentNode.querySelector(':scope>.dc-cats')||el;
    if(before!==el&&el.nextSibling!==before)el.parentNode.insertBefore(el,before);
  }
  /** Before reno.js redraws the room: where the walking figure is right now. */
  function freeze(){
    const el=meEl();if(!el||!W.to)return;
    const m=new DOMMatrixReadOnly(getComputedStyle(el).transform);W.x=m.e;W.y=m.f;
  }
  /** After it redrew: the walk carries on to where it was going. */
  function resume(){
    if(S.dlg?.open&&roomSvg()&&W.room===S.room){
      HC.join(W.room,fractions([W.x,W.y]),homeScope(),homeHost());HC.resume();}
    else HC.leave();
    order();
    const el=meEl();if(!el||!W.to)return;
    const left=Math.max(0,W.until-performance.now());
    if(left<40){arrive();return;}
    void el.getBoundingClientRect();
    el.style.transitionDuration=`${left}ms`;el.style.transform=`translate(${W.to.x.toFixed(1)}px,${W.to.y.toFixed(1)}px)`;
  }
  function stop(){clearTimeout(W.timer);W.timer=0;if(W.to){W.x=W.to.x;W.y=W.to.y;W.to=null;}W.then=null;}
  function arrive(){
    clearTimeout(W.timer);W.timer=0;
    if(W.to){W.x=W.to.x;W.y=W.to.y;W.to=null;}
    const el=meEl();if(el){el.style.transitionDuration='0ms';el.style.transform=`translate(${W.x.toFixed(1)}px,${W.y.toFixed(1)}px)`;el.querySelector('.hw-fig')?.classList.remove('walk');}
    const f=W.then;W.then=null;if(f)f();
  }
  function walkTo(p,then=null,approaching=false){
    clearTimeout(W.timer);
    const el=meEl();
    if(el&&W.to){const m=new DOMMatrixReadOnly(getComputedStyle(el).transform);W.x=m.e;W.y=m.f;}
    W.to=null;W.then=then;
    const d=Math.hypot(p[0]-W.x,p[1]-W.y);
    const ms=!el||calm()||d<3?0:Math.min(3000,Math.round(Math.max(250,d/SPEED*1000)));
    HC.walk([fractions([W.x,W.y]),fractions(p)],ms,approaching);
    if(!el||calm()||d<3){W.x=p[0];W.y=p[1];if(el){el.style.transitionDuration='0ms';el.style.transform=`translate(${W.x.toFixed(1)}px,${W.y.toFixed(1)}px)`;}arrive();return;}
    W.to={x:p[0],y:p[1]};W.until=performance.now()+ms;order();
    el.querySelector('.hw-fig')?.classList.add('walk');
    void el.getBoundingClientRect();
    el.style.transitionDuration=`${ms}ms`;el.style.transform=`translate(${p[0].toFixed(1)}px,${p[1].toFixed(1)}px)`;
    W.timer=setTimeout(arrive,ms+30);
  }

  /* ---- a tap in the room (not decorating) ---- */
  function tap(rm,pt,uid){
    if(!rm||!pt)return;
    if(!W.walked){W.walked=true;S.dlg?.querySelector('.hw-walkhint')?.remove();}   // the walking hint has done its job: it leaves the floor to the character
    const G=A.geom(rm),list=useRoom(rm);
    if(W.room!==rm.id)enter(rm,G);
    hush();
    const o=uid&&list.find(x=>x.id===uid);
    if(o){walkTo(standFor(rm,G,o,list),()=>use(rm,o));return;}
    const p=clampTo(rm,G,pt.x,pt.y+18);   // the finger points at the body: the feet are a little lower
    if(rm.type==='bunk')return walkTo(p,()=>say(pick(BED_LINE)));
    walkTo(p);
  }
  /** Arrows walk (the room has the focus). */
  function key(rm,e){
    const d={ArrowLeft:[-30,0],ArrowRight:[30,0],ArrowUp:[0,-20],ArrowDown:[0,20]}[e.key];
    if(!d||!rm)return false;
    e.preventDefault();const G=A.geom(rm);if(W.room!==rm.id)enter(rm,G);
    walkTo(clampTo(rm,G,(W.to?.x??W.x)+d[0],(W.to?.y??W.y)+d[1]));return true;
  }
  /** What a piece does when the character reaches it. */
  async function use(rm,o){
    const k=o.it.id,N=st().needs;
    if(S.remote){say(pick(LINES[k]||LINES[o.it.cat]||FLOOR_LINE));return;}
    if(FRIDGES.has(k)){openFridge();return;}
    if(BEDS.has(k)){
      if(N?.evening&&!N.evening.chosen&&S.env?.act){S.dlg.close();S.env.act('evening');return;}
      say(N?.evening?.chosen?'Chúc ngủ ngon nhé.':pick(BED_LINE));return;
    }
    if(CLOSET.has(k)&&S.env?.act){
      W.closet={room:rm.id,uid:o.id,pick:'',page:0};W.fridge=false;sfx('pop');render();
      requestAnimationFrame(()=>S.dlg?.querySelector('.hw-closet')?.scrollIntoView?.({block:'nearest',behavior:calm()?'auto':'smooth'}));return;
    }
    if(WARDROBE.has(k)&&S.env?.act){S.dlg.close();S.env.act('jrWardrobe');return;}
    const act=RELAX[k],a=act&&(ctx.V()?.relax||[]).find(x=>x.id===act);
    if(a){if(a.ok){const r=await send('jr_relax_do',{act:a.id},{loud:true,flash:false});if(r){sfx('chime');say(r.message.replace(/^\S+\s/,''),true);}}else say(a.why);return;}
    say(pick(LINES[k]||LINES[o.it.cat]||FLOOR_LINE));
  }
  /** A line in a bubble over the character (it stays a few seconds; `long`: a whole sentence from the server). */
  function say(text,long=false){
    W.say={text,at:performance.now(),long};
    const el=S.dlg?.querySelector('.hw-say');
    if(el){paintSay(el);return;}
    render();
  }
  function hush(){W.say=null;const el=S.dlg?.querySelector('.hw-say');if(el){el.hidden=true;el.textContent='';}}
  function paintSay(el){
    const rm=roomOf(S.room);if(!rm||!W.say)return;
    const G=A.geom(rm),x=W.to?.x??W.x,y=W.to?.y??W.y;
    el.textContent=W.say.text;el.hidden=false;
    const wrap=el.parentElement.getBoundingClientRect().width||G.W,half=el.offsetWidth/2+6;
    el.style.left=`${Math.max(half,Math.min(wrap-half,x/G.W*wrap)).toFixed(1)}px`;const high=el.parentElement.getBoundingClientRect().height||G.H;   // room for the bubble above the head, else it comes lower
    el.style.top=`${Math.max(el.offsetHeight+2,(y-150*K-6)/G.H*high).toFixed(1)}px`;
    clearTimeout(W.sayT);W.sayT=setTimeout(()=>{if(W.say&&performance.now()-W.say.at>=SAY_MS-50)hush();},W.say.long?SAY_MS*1.6:SAY_MS);
  }
  /** The bubble's slot, placed by paint() after a render. */
  const sayHTML=()=>'<p class="hw-say" role="status" aria-live="polite" hidden></p>';
  function paint(){const el=S.dlg?.querySelector('.hw-say');if(el&&W.say&&performance.now()-W.say.at<(W.say.long?SAY_MS*1.6:SAY_MS))paintSay(el);}

  /* ---- 🧊 the fridge ---- */
  function openFridge(){
    const F=FR();
    if(!F){say('Tủ lạnh chạy êm ru, mát rượi.');return;}   // a server from before: no food in it yet
    W.fridge=true;W.closet=null;W.note=null;sfx('pop');render();
    requestAnimationFrame(()=>S.dlg?.querySelector('.hw-fridge')?.scrollIntoView?.({block:'nearest',behavior:calm()?'auto':'smooth'}));
  }
  const shelf=F=>F.kind==='dorm'?'Ngăn của bạn trong tủ lạnh chung':'Tủ lạnh';
  const gainOf=x=>x.full?`No bụng +${x.full}`:`Tỉnh táo +${x.wake}`;
  const closetItems=()=>{
    const mine=new Set(st().wardrobe?.owned||[]);
    return (S.env?.api?.content?.journey?.wardrobe?.items||[]).filter(it=>it.id!=='pk_khong'&&CLOTHES.has(it.slot)&&(mine.has(it.id)||(!it.price&&!it.need)));
  };
  function closetPanel(rm){
    const c=W.closet;
    if(!c||!rm||c.room!==rm.id||!useRoom(rm).some(o=>o.id===c.uid&&CLOSET.has(o.it.id))){W.closet=null;return '';}
    const items=closetItems(),pages=Math.max(1,Math.ceil(items.length/8));c.page=Math.min(c.page,pages-1);
    const it=items.find(x=>x.id===c.pick),look=lookOf(st());
    if(it){look[it.slot]=it.id;look.uniform=false;const tint=wornColor(st(),it.id);if(tint)look.tint={...look.tint,[it.id]:tint};}
    const preview=figureSVG(look,st().journey?.gender,{w:112,h:160});
    const page=items.slice(c.page*8,c.page*8+8).map(x=>btn(esc(x.name),'hwClothesPick',{item:x.id},'ghost small',` aria-pressed="${x.id===c.pick}"`)).join('');
    return `<section class="bk-card hw-closet" aria-label="Quần áo trong tủ"><div class="hw-fridge-top"><h3>🗄️ Quần áo trong tủ</h3>${btn('Đóng tủ','hwClothesClose',{},'ghost small')}</div>
      <p class="bk-hint">Đồ mua ở shop tự xuất hiện ở đây, cùng quần áo cơ bản sẵn có. Chọn để ngắm thử, rồi mở Tủ đồ để mặc.</p>
      <div class="bk-center">${preview}<p>${it?esc(it.name):'Trang phục đang mặc'}</p></div>
      <div class="bk-actions">${page||'<p>Chưa có quần áo trong tủ.</p>'}</div>
      ${pages>1?`<div class="bk-actions">${btn('‹ Trước','hwClothesPage',{page:c.page-1},'ghost small',c.page?'':' disabled')}<span>${c.page+1}/${pages}</span>${btn('Sau ›','hwClothesPage',{page:c.page+1},'ghost small',c.page<pages-1?'':' disabled')}</div>`:''}
      <div class="bk-actions">${btn('👗 Mở Tủ đồ để thay','hwWardrobe',{},'primary')}</div></section>`;
  }
  function panel(v,rm){
    if(S.remote)return '';
    if(S.edit)return '';
    if(W.closet)return closetPanel(rm);
    const F=v?.fridge;
    if(!F)return '';
    if(!W.fridge){
      if(F.kind==='dorm'&&rm?.type==='bunk')return `<section class="bk-card hw-fridge-door"><p><span aria-hidden="true">🧊</span> <span>Tủ lạnh chung ở cuối phòng, mỗi người một ngăn.</span></p>${btn('🧊 Mở ngăn tủ của bạn','hwOpen',{},'ghost')}</section>`;
      return '';
    }
    if(!F.cap){W.fridge=false;return '';}
    const inside=F.foods.filter(x=>x.n);
    const have=inside.length?`<ul class="hw-in">${inside.map(x=>`<li><span class="hw-ico" aria-hidden="true">${x.emoji}</span><span class="hw-name"><b>${esc(x.name)}</b> <i class="hw-n">×${x.n}</i><small>${x.eat?`<em>${esc(x.eat)}</em>`:esc(gainOf(x))}</small></span>`
      +`${btn('🍽️ Ăn','hwEat',{item:x.id},'primary small',x.eat?' disabled':'')}</li>`).join('')}</ul>`
      :'<p class="hw-empty">Tủ còn trống. Cất vài món bên dưới, đói thì lấy ra ăn.</p>';
    // one reason for the whole shop when every food has it (the fridge is full, the wallet pays for none); per food only when it differs
    const why0=F.foods[0]?.buy||'',common=why0&&F.foods.every(x=>x.buy===why0)?why0:'';
    const shop=F.foods.map(x=>`<button type="button" class="hw-buy" data-dc="hwBuy" data-item="${esc(x.id)}"${x.buy||S.busy?' disabled':''}><span class="hw-ico" aria-hidden="true">${x.emoji}</span>`
      +`<span class="hw-name"><b>${esc(x.name)}</b><small><span>${x.price} xu</span> · <span>${esc(gainOf(x))}</span></small>${x.buy&&x.buy!==common?`<em>${esc(x.buy)}</em>`:''}</span></button>`).join('');
    return `<section class="bk-card hw-fridge" aria-label="${esc(shelf(F))}"><div class="hw-fridge-top"><h3><span aria-hidden="true">🧊</span> ${esc(shelf(F))}</h3><span class="hw-cap">${F.used}/${F.cap} món</span>${btn('Đóng tủ','hwClose',{},'ghost small')}</div>`
      +`<p class="bk-flash hw-note ${W.note?.kind||''}" role="status" aria-live="polite">${W.note?esc(W.note.text):''}</p>`
      +`<p class="hw-now"><span>🍚 No bụng ${F.full}</span><span>😴 Tỉnh táo ${F.wake}</span></p>${have}`
      +`<h4 class="hw-sub">🛒 Đi chợ cất tủ</h4>${common?`<p class="hw-why">🔒 ${esc(common)}</p>`:''}<div class="hw-shop">${shop}</div><p class="bk-hint">Mua bằng tiền trong ví. Đói lúc nào thì lấy ra ăn lúc đó.</p></section>`;
  }
  const btn=(label,op,data={},cls='',extra='')=>`<button type="button" class="btn ${cls}" data-dc="${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${S.busy?' disabled':''}${extra}>${label}</button>`;
  /** The hint on the room (markup): the fridge's, else how to walk until the first tap. */
  function hint(v,rm){
    const F=v?.fridge,pill=(t,c='')=>`<span class="dc-hint${c}" aria-hidden="true">${esc(t)}</span>`;
    if(F&&!F.cap&&rm&&['kitchen','studio'].includes(rm.type))return pill(F.why==='Tủ lạnh còn trong túi đồ'?'🧊 Bày tủ lạnh ra để cất đồ ăn':'🧊 Có tủ lạnh là cất được đồ ăn');
    return W.walked?'':pill('Chạm sàn để đi · chạm đồ để dùng',' hw-walkhint');
  }
  async function click(op,data){
    if(S.remote&&!['hwEmote','hwReply'].includes(op))return true;
    switch(op){
      case'hwEmote':HC.emote(data.kind,data.to);return true;
      case'hwReply':HC.reply(data.answer,data.id);return true;
      case'hwClothesClose':W.closet=null;render();return true;
      case'hwClothesPick':if(W.closet&&closetItems().some(x=>x.id===data.item)){W.closet.pick=data.item;render();}return true;
      case'hwClothesPage':if(W.closet){W.closet.page=Math.max(0,Math.min(Math.ceil(closetItems().length/8)-1,Number(data.page)||0));render();}return true;
      case'hwWardrobe':if(W.closet&&S.env?.act){
        const it=closetItems().find(x=>x.id===W.closet.pick),ui=S.env.ui;
        if(it&&ui){const wd=ui.wd??={tab:it.slot,draft:{}};wd.tab=it.slot;wd.draft={...wd.draft,[it.slot]:it.id};}
        S.dlg.close();S.env.act('jrWardrobe');}return true;
      case'hwOpen':openFridge();return true;
      case'hwClose':W.fridge=false;W.note=null;render();return true;
      case'hwBuy':case'hwEat':{
        const r=await send(op==='hwBuy'?'jr_fridge_buy':'jr_fridge_eat',{item:data.item},{loud:true,flash:false});
        W.note=r?{text:r.message,kind:'good'}:S.flash?{...S.flash}:null;S.flash=null;   // the answer shows in the fridge, next to the buttons
        if(r)sfx(op==='hwBuy'?'coins':'pop');
        render();if(r&&op==='hwEat')say(r.message.replace(/^\S+\s/,''),true);
        return true;}
    }
    return false;
  }
  function reset(){HC.leave();clearTimeout(crowdRender);crowdRender=0;stop();W.room='';W.say=null;W.fridge=false;W.closet=null;W.note=null;W.walked=false;}

  /* ---- test hooks (scratch browser checks) ---- */
  globalThis.__homeWalk={state:()=>({room:W.room,me:[W.x,W.y],to:W.to&&[W.to.x,W.to.y],fridge:W.fridge,say:W.say?.text||''}),
    screen:uid=>{const svg=roomSvg(),g=svg?.querySelector(`g[data-uid="${CSS.escape(uid)}"] .dc-hit`);if(!g)return null;const r=g.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2];}};

  return {markup,freeze,resume,tap,key,panel,hint,click,paint,sayHTML,reset,stop,socialPanel:()=>HC.panel(W.room,homeScope()),reopen:HC.reopen};
}
