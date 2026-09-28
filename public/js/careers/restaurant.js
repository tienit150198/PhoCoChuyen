/** Quán Mì Cay Mây — the kitchen desk: tables and app orders up top, the
 * guest's words, pots with portion counts, two boiling baskets with a timing
 * bar, the bowl with a live status line, chili, one big "Giao món" and the
 * toppings grid. Only renders server state and sends commands; the server
 * checks every rule (and keeps order details hidden until they are known). */
import {reqList,fold,refTable} from '../ui-kit.js';
import {dayStrip,flash,eventCard,actionBar,keepBarAboveFooter,idlePanel,gradeCard,patience,openTasks} from './food_kit.js';

const BASE_SCALE=25; // seconds shown on the boiling bar
const NOODLE={raw:'sống',perfect:'chín tới',soft:'hơi mềm',mushy:'nát'};
const item=(x,id)=>x.cc.items?.find(i=>i.id===id)||x.content.inventory?.items?.restaurant?.find(i=>i.id===id)||{name:id,emoji:'•'};
const brothOf=(x,id)=>x.cc.broths?.find(v=>v.id===id);
const data=x=>x.room.data||{};
const lower=s=>String(s||'').toLowerCase();
const pay=(x,o)=>x.esc(JSON.stringify(o));
const stockOf=(x,id)=>x.room.inventory?.stock?.[id]??0;
const isGroup=t=>!!t.needs?.party?.length;
const started=b=>!!(b&&(b.container||b.noodles.length||b.boiling));
const plated=t=>isGroup(t)&&!!t.plates?.[t.cur];
const pending=t=>isGroup(t)?(t.plates||[]).map((p,i)=>p?-1:i).filter(i=>i>=0&&i!==t.cur):[];

/** The order as seen from one bowl (a table's party, or the order itself). */
function specOf(t,i){
  const n=t.needs;if(!n||n.masked)return n;
  const p=n.party||[];if(!p.length)return n;
  return {...n,...p[i??t.cur??0]};
}

function bowlPrice(b,x){
  if(!b.broth)return 0;
  const d=data(x),prices=x.room.life?.prices||{};
  let p=(prices[b.broth]??x.cc.prices?.[b.broth]??0)+Object.entries(b.toppings||{}).reduce((s,[k,q])=>s+(item(x,k).price||0)*q,0);
  p+=10*Math.max(0,b.noodles.length-1)+(b.container==='box'?3:0);
  return Math.max(1,Math.round(p*(d.price_mult||1)));
}

/* ---------------------------------------------------------------- the floor */
/** Four tables (patience ring, "N tô") and the delivery-app row. */
function floor(x,active){
  const tasks=openTasks(x),dine=tasks.filter(t=>!t.app),apps=tasks.filter(t=>t.app);
  // With nobody waiting, the idle panel shows its own "Đón khách" button.
  const canAdd=x.room.open&&tasks.length>0&&tasks.length<4;
  const seats=[];
  for(let i=0;i<4;i++){
    const t=dine[i];
    if(t){
      const who=x.npc(t.npc),on=!!active&&t.id===active.id,p=Math.max(0,Math.min(100,t.patience??100)),n=t.bowls_total||1,g=t.guest||{};
      const badge=t.vip==='critic'?'📝':(g.emoji||'🙂');
      seats.push(`<button type="button" class="rs-seat${on?' on is-selected':''}${p<50?' low':''}" data-command="task_select" data-payload="${pay(x,{task:t.id})}" aria-label="${x.esc(`${who.display_name} · ${n} tô · ${g.label||'Khách'} · kiên nhẫn ${p}%`)}"${on?' aria-current="true"':''}>
        <span class="rs-ring" style="--p:${p}">${x.portrait(who,40)}</span><em class="rs-mood" aria-hidden="true">${badge}</em>
        <span class="rs-n" aria-hidden="true">${n} tô</span><b>${x.esc(who.display_name)}</b></button>`);
    }else if(canAdd&&i===dine.length){
      seats.push(`<button type="button" class="rs-seat empty add" data-command="more_work" data-payload="{}" aria-label="Đón thêm một khách"><span class="rs-plus" aria-hidden="true">＋</span><b>Đón khách</b></button>`);
    }else seats.push(`<div class="rs-seat empty" aria-hidden="true"><b>Bàn trống</b></div>`);
  }
  const cards=apps.map(t=>{
    const who=x.npc(t.npc),on=!!active&&t.id===active.id,p=Math.max(0,Math.min(100,t.patience??100)),n=t.needs;
    const what=!t.known||!n?'🧾 Đơn mới, bấm để đọc':n.masked?'Món quen':n.style==='open'?`Tô tùy quán · ≤ ${n.open.budget} xu`:`${brothOf(x,n.broth)?.name||''} · cấp ${n.spice}`;
    return `<button type="button" class="rs-app${on?' on is-selected':''}${p<50?' low':''}" data-command="task_select" data-payload="${pay(x,{task:t.id})}" aria-label="${x.esc(`Đơn app ${t.app} · ${who.display_name} · kiên nhẫn ${p}%`)}"${on?' aria-current="true"':''}>
      ${x.portrait(who,30)}<span class="rs-app-txt"><b>${x.esc(t.app)} · ${x.esc(who.display_name)}</b><small>${x.esc(what)}</small><i class="rs-app-bar" aria-hidden="true"><i style="width:${p}%"></i></i></span></button>`;
  }).join('');
  const appRow=apps.length?`<div class="rs-apps" role="group" aria-label="Đơn app"><span class="rs-apps-tag" aria-hidden="true">🛵<small>Đơn app</small></span><div class="rs-app-list">${cards}</div></div>`:'';
  return `<section class="rs-floor" aria-label="Khách trong quán"><div class="rs-tables" role="group" aria-label="Bàn ăn">${seats.join('')}</div>${appRow}</section>`;
}

/* ---------------------------------------------------------------- the order */
function picture(sp,x){
  const b=brothOf(x,sp.broth);
  const tops=Object.entries(sp.toppings).map(([k,q])=>item(x,k).emoji.repeat(q)).join(' ');
  return `<p class="rs-picture" aria-label="Phiếu bằng hình">${x.esc(b?.emoji||'')} ${sp.spice?'🌶️'.repeat(sp.spice):'🚫🌶️'} ${x.esc(tops)} ${sp.extra_noodle?'🍜🍜':''} ${sp.takeaway?'🥡':'🥣'} ${sp.allergy?'🚫🦐':''}</p><p class="muted small">Khách chỉ vào hình trên thực đơn. Đọc từng hình nhé.</p>`;
}
/** Only the two orders that hide their spec on purpose get a lead line:
 * a regular's "như mọi khi" (look it up or ask) and a picture order. */
function lead(t,x){
  const n=t.needs,d=data(x);
  if(n.masked){
    const known=(d.notebook||[]).includes(t.npc);
    return `<p class="rs-say">🏠 “Như mọi khi nhé!”</p>
      <div class="row wrap rs-recall">${x.cmd('📒 Tra sổ khách quen','rs_recall',{task:t.id},'primary',!known)}${x.cmd('🙋 Hỏi lại món','rs_reask',{task:t.id},'ghost')}</div>
      <p class="muted small">${known?'Sổ đã ghi món quen của khách này.':'Sổ chưa ghi món của khách này. Hỏi lại thì khách chờ lâu hơn một chút.'}</p>`;
  }
  if(n.style==='picture')return picture(n,x);
  return '';
}
/** Story and the guest's own words, folded to one line. */
function voice(t,x){
  const note=t.needs?.masked?'':t.needs?.note,story=t.story;
  if(!note&&!story)return '';
  if(!story)return `<p class="rs-note">💬 “${x.esc(note)}”</p>`;
  return fold(`💬 ${note?`“${x.esc(note)}”`:'Chuyện của khách'}`,`<p class="rs-story">${x.esc(story)}</p>`);
}
/** Tô 1 · Tô 2 · Tô 3 for a table's order (done ones are struck through). */
function tabs(t,x){
  if(!isGroup(t))return '';
  const lock=started(t.bowl)&&!plated(t);
  return `<div class="rs-tabs" role="tablist" aria-label="Các tô của bàn">${t.needs.party.map((p,i)=>{
    const done=!!t.plates[i],on=i===t.cur&&!done;
    const label=`Tô ${i+1}${done?' ✓':''}`;
    return `<button type="button" role="tab" class="rs-tab${done?' done':''}${on?' on':''}" data-command="rs_tab" data-payload="${pay(x,{task:t.id,index:i})}" aria-selected="${on}"${on||(lock&&!on)?' disabled':''} title="${done?'Đã xong, bấm để lấy xuống sửa':on?'Đang làm':'Chuyển sang tô này'}">${label}</button>`;
  }).join('')}</div>`;
}
function ticket(t,x){
  const who=x.npc(t.npc),g=t.guest||{},n=t.needs;
  const price=n.style==='open'?(t.bowl.broth?`${bowlPrice(t.bowl,x)}/${n.open.budget} xu`:`≤ ${n.open.budget} xu`):t.quoted_price?x.money(t.quoted_price):'';
  return `<article class="card rs-order${t.vip==='critic'?' critic':''}"><div class="rs-order-head">${x.portrait(who,44)}<div class="grow">
    <div class="row spread"><h3>${x.esc(who.display_name)}</h3><b class="price">${x.esc(price)}</b></div>
    <p class="rs-guest"><span class="tag">${x.esc(g.emoji||'')} ${x.esc(g.label||'')}</span>${t.app?` <span class="tag">🛵 Đơn app ${x.esc(t.app)}</span>`:''}${isGroup(t)?` <span class="tag">🍜 ${t.needs.party.length} tô</span>`:''}${t.vip==='critic'?' <span class="tag amber">📝 Người viết review</span>':''}</p></div></div>
    ${patience(t.patience)}${lead(t,x)}${tabs(t,x)}${reqList(checklistRows(t,x),x.esc,'Phiếu order')}${voice(t,x)}</article>`;
}

/* ---------------------------------------------------------------- checklist */
/** The order as a requirement list, each row checked live against the bowl. */
const row=(ok,icon,label,value='',tone='')=>({ok,icon,label,value,tone});
function checklistRows(t,x){
  const n=t.needs,b=t.bowl,rows=[],tops=b.toppings||{},count=Object.values(tops).reduce((a,v)=>a+v,0);
  if(plated(t))return [row(true,'🍜',`Đủ ${t.plates.length} tô trên khay, giao một lượt`)];
  const pic=n.style==='picture',name=(k)=>pic?item(x,k).emoji:item(x,k).name;
  const paper=data(x).rules?.paper&&!n.takeaway;
  rows.push(row(b.container?((b.container==='box')===n.takeaway||(paper&&b.container==='box')):null,n.takeaway?'🥡':'🥣',n.takeaway?'Hộp mang về + nắp':'Tô ăn tại quán',n.takeaway&&b.container==='box'&&!b.lid?'chưa đậy nắp':''));
  if(n.masked){
    rows.push(row(b.noodles.length?b.noodles.every(v=>v==='perfect'):null,'🍜','Mì chín tới'));
    rows.push(row(null,'📒','Món quen: tra sổ hoặc hỏi lại'));
    return rows;
  }
  const sp=specOf(t),nb=n.style==='open'?Math.max(1,b.noodles.length):(sp.extra_noodle?2:1);
  rows.push(row(b.noodles.length?b.noodles.length===nb&&b.noodles.every(v=>v==='perfect'):null,'🍜',`${nb} vắt mì chín tới`,b.noodles.length?b.noodles.map(v=>NOODLE[v]).join(', '):''));
  const meat=x.cc.meat||[];
  if(n.style==='open'){
    const o=n.open,names=(o.broths||[]).map(id=>brothOf(x,id)?.name).join(' hoặc ');
    rows.push(row(b.broth?(!o.broths||o.broths.includes(b.broth))&&!(o.veg&&brothOf(x,b.broth)?.allergen):null,'🍲',o.broths?`Nước dùng ${names}`:'Nước dùng tùy bạn chọn',b.broth?brothOf(x,b.broth)?.name||'':''));
    for(const k of o.must)rows.push(row(tops[k]?true:null,item(x,k).emoji,`Phải có ${lower(item(x,k).name)}`));
    for(const k of o.avoid)rows.push(row(tops[k]?false:(b.broth?true:null),'🚫',`Không ${lower(item(x,k).name)}`,'','warn'));
    if(o.veg)rows.push(row(Object.keys(tops).some(k=>meat.includes(k))?false:(b.broth?true:null),'🌱','Ăn chay: không thịt, cá, đồ biển','','warn'));
    rows.push(row(count>=o.min_tops?true:null,'➕',`Ít nhất ${o.min_tops} phần topping`,`${count}/${o.min_tops}`));
    const [lo,hi]=o.spice;
    rows.push(row(b.chili>hi?false:b.chili>=lo&&(b.chili||b.broth)?true:null,'🌶️',lo===hi?`Cay cấp ${lo}`:`Cay cấp ${lo}–${hi}`,`${b.chili} lượt`));
    const price=bowlPrice(b,x);
    rows.push(row(price>o.budget?false:b.broth?true:null,'💰',`Trong ngân sách ${o.budget} xu`,b.broth?`${price} xu`:''));
  }else{
    const br=brothOf(x,sp.broth);
    rows.push(row(b.broth?b.broth===sp.broth:null,pic?br?.emoji||'🍲':'🍲',pic?'Nước dùng theo hình':`Nước dùng ${br?.name||''}`));
    const want={...sp.toppings};
    for(const [k,v] of Object.entries(t.subs||{})){if(want[k]){want[v]=(want[v]||0)+want[k];delete want[k];}}
    for(const [k,q] of Object.entries(want)){const have=tops[k]||0,sub=Object.values(t.subs||{}).includes(k);rows.push(row(have>q?false:have===q?true:null,item(x,k).emoji,pic?`${q} ×`:`${name(k)}${sub?' (đổi món)':''}`,`${have}/${q}`));}
    const pampered=data(x).rules?.pamper===t.id;
    for(const [k,q] of Object.entries(tops)){if(!want[k])rows.push(row(pampered?true:false,item(x,k).emoji,`${item(x,k).name} (${pampered?'tặng thêm':'khách không gọi'})`,`${q}`));}
    rows.push(row(b.chili>sp.spice?false:b.chili===sp.spice&&(b.chili||b.broth)?true:null,'🌶️',sp.spice?`Cay cấp ${sp.spice}`:'Không cay',`${b.chili}/${sp.spice} lượt`));
  }
  if(n.allergy)rows.push(row(!Object.keys(tops).some(k=>item(x,k).allergen===n.allergy)&&(!b.broth||!brothOf(x,b.broth)?.allergen),'⚠️','Dị ứng hải sản: không tomyum, cá viên, hải sản','','danger'));
  return rows;
}

/* ---------------------------------------------------------------- next step */
function nextStep(t,x){
  if(!t.known)return t.app?'Đọc đơn app':'Nhận order của khách';
  const b=t.bowl,n=t.needs,g=isGroup(t),tag=g?`Tô ${t.cur+1}: `:'';
  if(n.masked)return 'Tra sổ khách quen hoặc hỏi lại món';
  if(plated(t))return `Đủ ${t.plates.length} tô, giao một lượt!`;
  if(!b.container)return tag+(n.takeaway?'lấy hộp mang về':'lấy tô');
  if(b.boiling)return tag+'vớt mì khi thanh vào vùng xanh';
  const sp=specOf(t),nb=n.style==='open'?1:(sp.extra_noodle?2:1);
  if(b.noodles.length<nb)return tag+'thả mì vào rổ luộc';
  if(!b.broth)return tag+'chan nước dùng';
  if(n.style==='open'){
    const count=Object.values(b.toppings).reduce((a,v)=>a+v,0),[lo]=n.open.spice;
    if(n.open.must.some(k=>!b.toppings[k]))return 'Thêm món khách muốn có';
    if(count<n.open.min_tops)return `Thêm topping (${count}/${n.open.min_tops})`;
    if(b.chili<lo)return `Bơm ớt (cấp ${n.open.spice[0]}–${n.open.spice[1]})`;
  }else{
    if(Object.entries(sp.toppings).some(([k,q])=>(b.toppings[t.subs?.[k]||k]||0)<q))return tag+'thêm topping theo phiếu';
    if(b.chili<sp.spice)return `${tag}bơm ớt (${b.chili}/${sp.spice})`;
  }
  if(n.takeaway&&!b.lid)return 'Đậy nắp hộp';
  if(pending(t).length)return `Tô ${t.cur+1} xong! Đặt lên khay rồi làm tô ${pending(t)[0]+1}`;
  return g?'Đủ tô rồi, giao một lượt!':'Giao món cho khách!';
}

/* ---------------------------------------------------------------- kitchen */
function tileBtn(x,o){
  const cls=['rs-tile',o.cls||'',o.selected?'is-selected':'',o.locked?'is-locked':'',o.empty?'is-empty':'',o.wanted?'wanted':'',o.avoid?'avoid':''].filter(Boolean).join(' ');
  const badge=o.count!=null?`<span class="count-badge${o.zero?' is-empty':''}" data-count="${o.zero?0:x.esc(String(o.count))}">${x.esc(String(o.count))}</span>`:'';
  return `<button type="button" class="${cls}" data-command="${o.cmd}" data-payload="${pay(x,o.payload)}"${o.disabled||o.locked?' disabled':''} aria-pressed="${o.selected?'true':'false'}" aria-label="${x.esc(o.label)}">
    ${badge}<span class="rs-emoji" aria-hidden="true">${x.esc(o.emoji)}</span><b>${x.esc(o.name)}</b>${o.sub?`<small>${x.esc(o.sub)}</small>`:''}${o.have?`<em class="rs-have" aria-hidden="true">×${o.have}</em>`:''}</button>`;
}
/** Bowls, boxes and the four broth pots, each with a count badge. */
function pots(t,x){
  const d=data(x),b=t.bowl,n=t.needs,level=x.room.level,r=d.rules||{},portions=d.portions||1,sp=specOf(t);
  const max=x.cc.dirty_max||3,dirtyOn=r.dirty!==undefined,clean=dirtyOn?Math.max(0,max-r.dirty):null,locked=plated(t);
  const hide=n.masked||n.style==='picture';
  const wantBroth=hide?[]:n.style==='open'?(n.open.broths||[]):[sp.broth];
  const tiles=[
    tileBtn(x,{cmd:'rs_container',payload:{task:t.id,kind:'bowl'},emoji:'🥣',name:'Lấy tô',count:dirtyOn?clean:'∞',zero:dirtyOn&&!clean,selected:b.container==='bowl',
      disabled:!!b.container||locked||(dirtyOn&&!clean),wanted:!hide&&!b.container&&!n.takeaway,label:dirtyOn?`Lấy tô, còn ${clean} tô sạch`:'Lấy tô ăn tại quán'}),
    tileBtn(x,{cmd:'rs_container',payload:{task:t.id,kind:'box'},emoji:'🥡',name:'Hộp',count:stockOf(x,'box'),zero:!stockOf(x,'box'),selected:b.container==='box',
      disabled:!!b.container||locked||!stockOf(x,'box'),wanted:!hide&&!b.container&&n.takeaway,label:`Hộp mang về, còn ${stockOf(x,'box')}`}),
    ...x.cc.broths.map(p=>{const q=d.pots?.[p.id]??0,lock=p.unlock>level;
      return tileBtn(x,{cmd:'rs_broth',payload:{task:t.id,broth:p.id},emoji:p.emoji,name:p.name,count:lock?null:q,zero:q<portions,locked:lock,selected:b.broth===p.id,
        wanted:!b.broth&&wantBroth.includes(p.id),disabled:q<portions||!!b.broth||!b.container||locked,cls:'pot',
        label:lock?`Nước dùng ${p.name}, mở ở cấp ${p.unlock}`:`Chan nước dùng ${p.name}, nồi còn ${q} phần`});})];
  // Cooking a pot is offered when it runs low (a pot holds 12 portions, one batch adds 6).
  const low=x.cc.broths.filter(p=>p.unlock<=level&&(d.pots?.[p.id]??0)<=Math.min(6,2*portions));
  const cook=low.length?`<div class="rs-cook"><small>🔥 Nấu thêm nồi</small>${low.map(p=>{const packs=stockOf(x,p.pack);return x.cmd(`${p.emoji} ${x.esc(p.name)} · ${packs} gói`,'rs_pot',{broth:p.id},'ghost small',!packs);}).join('')}</div>`:'';
  return `<div class="rs-grid rs-pots" role="group" aria-label="Tô, hộp và nồi nước dùng">${tiles.join('')}</div>${portions>1?'<p class="muted small">🥶 Trời lạnh: mỗi tô chan 2 phần nồi.</p>':''}${cook}`;
}
function boilBar(start,x,id,shift){
  const w=x.cc.boil||{raw:7,perfect:13,soft:19},scale=BASE_SCALE+shift,z=v=>(v+shift)/scale*100;
  const elapsed=start?Math.max(0,x.now()-start):0;
  return `<div class="boil" data-boil-start="${start||''}" data-shift="${shift}" data-task="${x.esc(id||'')}">
    <div class="boil-track"><i class="zone raw" style="width:${z(w.raw)}%"></i><i class="zone perfect" style="left:${z(w.raw)}%;width:${(w.perfect-w.raw)/scale*100}%"></i><i class="zone soft" style="left:${z(w.perfect)}%;width:${(w.soft-w.perfect)/scale*100}%"></i><b class="boil-fill" style="width:${Math.min(100,elapsed/scale*100)}%"></b></div>
    <small class="boil-label">${start?elapsed.toFixed(1)+' giây':'Rổ trống'}${shift?' · lửa nhỏ':''}</small></div>`;
}
/** Two baskets. The one for this bowl says "Vớt mì"; a free one "Thả mì". */
function stove(t,x){
  const d=data(x),b=t.bowl,baskets=d.baskets||[],shift=d.boil_shift||0;
  let offered=false;
  return `<div class="rs-stove" role="group" aria-label="Rổ luộc mì">${[0,1].map(i=>{
    const k=baskets[i];
    if(k){
      const mine=k.task===t.id,other=mine?null:(x.room.tasks||[]).find(v=>v.id===k.task),who=other?x.npc(other.npc).display_name:'';
      return `<div class="rs-basket busy">${boilBar(k.start,x,k.task,shift)}${x.cmd(mine?'🥢 Vớt mì':`🥢 Vớt · ${x.esc(who)}`,'rs_drain',{task:k.task},mine?'primary small':'ghost small')}</div>`;
    }
    if(offered)return `<div class="rs-basket"><small class="muted">Rổ trống</small></div>`;
    offered=true;
    const sp=specOf(t),need=t.needs&&!t.needs.masked&&t.needs.style!=='open'?(sp.extra_noodle?2:1):2;
    const can=b.container&&!b.boiling&&b.noodles.length<2&&baskets.length<2&&!plated(t);
    return `<div class="rs-basket">${boilBar(null,x,'',shift)}${x.cmd(`🍜 Thả mì (${stockOf(x,'noodle')})`,'rs_boil',{task:t.id},can&&b.noodles.length<need?'primary small':'small',!can||!stockOf(x,'noodle'))}</div>`;
  }).join('')}</div>`;
}
function bowlArt(b,x){
  const broth=brothOf(x,b.broth);
  const tops=Object.entries(b.toppings||{}).flatMap(([k,q])=>Array(q).fill(item(x,k).emoji||'•')).slice(0,8);
  const cls=['bowl-art',b.container||'none',b.lid?'lid':''].join(' ');
  return `<div class="${cls}" role="img" aria-label="Tô mì đang làm">
    <div class="bowl-shell">
      ${broth?`<div class="bowl-broth" style="--broth:${x.esc(broth.color)}"></div>`:''}
      ${b.noodles.map((n,i)=>`<div class="bowl-noodle ${x.esc(n)}" style="--i:${i}"></div>`).join('')}
      <div class="bowl-tops">${tops.map((e,i)=>`<span style="--i:${i}">${x.esc(e)}</span>`).join('')}</div>
      ${b.chili?`<div class="bowl-chili" style="--n:${Math.min(10,b.chili)}"></div>`:''}
    </div></div>`;
}
/** Live status line under the bowl: "Kim chi · chưa có mì". */
function bowlStatus(t,x){
  const b=t.bowl;
  if(plated(t))return `Đủ ${t.plates.length} tô trên khay`;
  if(!b.container)return 'Chưa lấy tô';
  const parts=[b.broth?brothOf(x,b.broth)?.name||'':b.container==='box'?'Hộp chưa có nước':'Tô chưa có nước'];
  parts.push(b.boiling?'mì đang luộc':b.noodles.length?`${b.noodles.length} vắt ${b.noodles.map(v=>NOODLE[v]).join(', ')}`:'chưa có mì');
  const n=Object.values(b.toppings||{}).reduce((a,v)=>a+v,0);
  if(n)parts.push(`${n} topping`);
  if(b.chili)parts.push(`cay ${b.chili}`);
  if(b.container==='box')parts.push(b.lid?'đã đậy nắp':'chưa đậy nắp');
  return parts.join(' · ');
}
function tray(t,x){
  if(!isGroup(t))return '';
  return `<p class="rs-tray" aria-label="Khay">${t.plates.map((p,i)=>`<span class="${p?'on':''}${i===t.cur&&!p?' cur':''}" title="Tô ${i+1}">${p?'🍜':i===t.cur?'🥢':'◌'}<small>${i+1}</small></span>`).join('')}</p>`;
}
function chili(t,x){
  const b=t.bowl,n=t.needs,sp=specOf(t),q=stockOf(x,'chili');
  const [lo,hi]=!n||n.masked?[0,0]:n.style==='open'?n.open.spice:[sp.spice,sp.spice];
  const target=n.masked?Math.max(b.chili,1):Math.max(hi,b.chili,1);
  const can=b.container&&q>0&&!plated(t)&&b.chili<10;
  const goal=n.masked?`${b.chili} lượt`:lo===hi?`cấp ${b.chili}/${hi}`:`${b.chili} · cần ${lo}–${hi}`;
  return `<div class="rs-chili"><button type="button" class="rs-tile rs-bottle${!q?' is-empty':''}" data-command="rs_chili" data-payload="${pay(x,{task:t.id})}"${can?'':' disabled'} aria-label="Bơm sốt ớt, còn ${q} lượt">
      <span class="count-badge${!q?' is-empty':''}" data-count="${q}">${q}</span><span class="rs-emoji" aria-hidden="true">🌶️</span><b>Sốt ớt</b><small>${x.esc(goal)}</small></button>
    <div class="pumps" aria-hidden="true">${Array.from({length:Math.min(10,target)},(_,i)=>`<i class="${i<b.chili?(n.masked||i<hi?'on':'over'):''}${!n.masked&&i<lo?' need':''}"></i>`).join('')}</div></div>`;
}
function toppings(t,x){
  const b=t.bowl,n=t.needs,level=x.room.level,sp=specOf(t),r=data(x).rules||{};
  const hide=n.masked||n.style==='picture';
  const want=hide?{}:n.style==='open'?Object.fromEntries(n.open.must.map(k=>[k,1])):(()=>{const w={...sp.toppings};for(const [k,v] of Object.entries(t.subs||{})){if(w[k]){w[v]=(w[v]||0)+w[k];delete w[k];}}return w;})();
  const avoid=n.style==='open'?new Set([...n.open.avoid,...(n.open.veg?x.cc.meat||[]:[])]):new Set();
  const openOrder=n.style==='open';
  const tiles=x.cc.toppings.map(k=>{const i=item(x,k),q=stockOf(x,k),lock=(i.unlock||1)>level,have=b.toppings[k]||0;
    return tileBtn(x,{cmd:'rs_topping',payload:{task:t.id,item:k},emoji:i.emoji,name:i.name,sub:openOrder&&!lock?`${i.price||0} xu`:'',count:lock?null:q,zero:!q,locked:lock,
      selected:have>0,have,wanted:!!want[k]&&have<want[k],avoid:avoid.has(k),disabled:!q||!b.container||plated(t),
      label:lock?`${i.name}, mở ở cấp ${i.unlock||1}`:`Thêm ${i.name}, còn ${q}${have?`, trong tô ${have}`:''}`});}).join('');
  const outOf=openOrder||n.masked?[]:Object.entries(sp.toppings).filter(([k,q])=>(stockOf(x,k)<q||(k==='beef'&&r.bad_beef))&&!(t.subs||{})[k]&&(b.toppings[k]||0)<q);
  const subs=outOf.length?`<div class="notice amber">Thiếu ${outOf.map(([k])=>x.esc(item(x,k).name)).join(', ')}? Hỏi khách đổi món: ${outOf.map(([k])=>['mushroom','egg','sausage','kimchi_side','tofu'].filter(s=>s!==k&&stockOf(x,s)>0&&!(n.allergy&&item(x,s).allergen===n.allergy)).slice(0,2).map(s=>x.cmd(`${item(x,s).emoji} ${x.esc(item(x,s).name)}`,'rs_sub',{task:t.id,item:k,substitute:s},'small ghost')).join('')).join('')}</div>`:'';
  return `${subs}<div class="rs-grid rs-tops" role="group" aria-label="Topping">${tiles}</div>`;
}
function extras(x){
  const d=data(x),r=d.rules||{},bits=[];
  const b=r.batch;
  if(b&&b.status==='open'){
    const pot=d.pots?.[b.broth]??0;
    bits.push(`<article class="card rs-batch"><div class="row spread"><h4>📦 Đơn văn phòng: ${b.done}/${b.goal} hộp</h4><small>${x.esc(brothOf(x,b.broth)?.name||'')} · cấp ${b.spice}</small></div>
      <div class="rs-batch-bar" aria-hidden="true"><i style="width:${b.done/b.goal*100}%"></i></div>
      <p class="muted small">Xong trước khi phục vụ thêm ${Math.max(0,b.due+1-(d.day?.served||0))} khách. Mỗi hộp: 1 vắt mì, 1 hộp, ${b.spice} lượt ớt, ${d.portions||1} phần nồi (nồi còn ${pot}).</p>
      ${x.cmd('📦 Đóng 1 hộp đơn đặt','rs_batch',{},'primary')}</article>`);
  }
  if(r.dirty!==undefined){
    const max=x.cc.dirty_max||3;
    bits.push(`<p class="rs-dishes ${r.dirty>=max?'full':''}">🍽️ Tô bẩn: <b>${r.dirty}/${max}</b> ${x.cmd('🧽 Rửa tô','rs_wash',{},r.dirty>=max?'primary small':'ghost small',!r.dirty)}</p>`);
  }
  return bits.join('');
}

/** The one primary action: "Xong tô N" while a table still waits for bowls, else "Giao món". */
function primary(t,x,rows,big){
  const b=t.bowl,blocked=!!data(x).day?.open_event;
  const ready=plated(t)||(b.container&&b.broth&&b.noodles.length&&!b.boiling&&(b.container!=='box'||b.lid));
  if(pending(t).length){
    return x.cmd(`✅ Xong tô ${t.cur+1}`,'rs_plate',{task:t.id},'primary'+(big?' big':''),!ready);
  }
  const label=big?'🛎️ Giao món':'🛎️ Giao';
  const allOk=rows.every(r=>r.ok===true);
  return allOk&&!blocked?x.cmd(label,'rs_serve',{task:t.id,confirm:true},'primary'+(big?' big':''),!ready)
    :x.confirmCmd(label,'rs_serve',{task:t.id,confirm:true},blocked?'Có chuyện bất ngờ đang chờ bạn quyết. Xử lý xong rồi hãy giao nhé.':'Tô chưa khớp hết phiếu. Vẫn giao? Khách sẽ đánh giá đúng những gì có trong tô.','primary'+(big?' big':''),!ready);
}

/** "📖 Thực đơn": what each broth and topping costs, how much is left, which
 * ones carry seafood or meat, and the few kitchen rules worth remembering. */
function menuPage(x){
  const d=data(x),level=x.room.level,mult=d.price_mult||1,prices=x.room.life?.prices||{},meat=x.cc.meat||[],w=x.cc.boil||{raw:7,perfect:13};
  const xu=v=>`${Math.max(1,Math.round(v*mult))} xu`,lock=u=>u>level?`🔒 cấp ${u}`:null;
  const seafood={label:'🦐 Hải sản',tone:'bad'},veg={label:'🌱 Chay được',tone:'good'},savory={label:'🥩 Mặn'};
  const broths=x.cc.broths.map(p=>({icon:p.emoji,name:p.name,price:xu(prices[p.id]??x.cc.prices?.[p.id]??0),locked:p.unlock>level,
    stock:lock(p.unlock)||`nồi còn ${d.pots?.[p.id]??0}`,tags:[p.allergen?seafood:veg]}));
  const tops=x.cc.toppings.map(k=>{const i=item(x,k),u=i.unlock||1;
    return {icon:i.emoji,name:i.name,price:`+${xu(i.price||0)}`,locked:u>level,stock:lock(u)||`còn ${stockOf(x,k)}`,
      tags:[i.allergen?seafood:meat.includes(k)?savory:veg]};});
  const extra=[{icon:'🍜',name:'Thêm 1 vắt mì',price:`+${xu(10)}`},{icon:'🥡',name:'Hộp mang về',price:`+${xu(3)}`,stock:`còn ${stockOf(x,'box')}`}];
  const rules=[`🍜 Vớt mì khi thanh vào vùng xanh: ${w.raw}–${w.perfect} giây.`,'🌶️ Mỗi lượt bơm ớt là 1 cấp cay. Cấp 0 là không bơm.',
    '🔄 Hết topping khách gọi: hỏi khách đổi món ở ô vàng trên kệ.','🥡 Mang về: lấy hộp, làm xong nhớ đậy nắp.','⚠️ Khách dị ứng hải sản: không tomyum, cá viên, hải sản.'];
  return `<header class="sheet-head"><div class="grow"><span class="eyebrow">QUÁN MÌ CAY · SỔ TRA CỨU</span><h2>📖 Thực đơn</h2><p>Giá bán, còn bao nhiêu, món nào có hải sản hay thịt.</p></div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${x.icon('x',21)}</button></header>
  <div class="sheet-body ref-sheet">${refTable([{title:'Nước dùng (giá một tô)',rows:broths},{title:'Topping',rows:tops},{title:'Thêm',rows:extra}],x.esc)}
    <section class="ref-group"><h3>Nhớ nhanh</h3><ul class="ref-rules">${rules.map(r=>`<li>${x.esc(r)}</li>`).join('')}</ul></section></div>`;
}

export default {
  id:'restaurant',
  css:true,
  next(t,x){return nextStep(t,x);},
  idle(x){
    const d=data(x);
    return idlePanel(x,d.day,'rs_event',extras(x),v=>floor(v,null),'rs');
  },
  job(t,x){
    const d=data(x),day=d.day;
    const head=`${dayStrip(x,day,true)}${flash(x,day)}${eventCard(x,day,'rs_event')}${floor(x,t)}`;
    if(!t.known){
      const who=x.npc(t.npc),g=t.guest||{};
      return `<div class="career-job rs food">${head}<article class="card rs-order"><div class="rs-order-head">${x.portrait(who,56)}<div class="grow"><h3>${x.esc(who.display_name)}</h3>
        <p class="rs-guest"><span class="tag">${x.esc(g.emoji||'')} ${x.esc(g.label||'')}</span>${t.app?` <span class="tag">🛵 Đơn app ${x.esc(t.app)}</span>`:''}${(t.bowls_total||1)>1?` <span class="tag">🍜 ${t.bowls_total} tô</span>`:''}${t.vip==='critic'?' <span class="tag amber">📝 Người viết review</span>':''}</p></div></div>
        ${t.story?`<p class="rs-story">💬 ${x.esc(t.story)}</p>`:''}<p class="rs-say">“${x.esc(t.opening)}”</p>${patience(t.patience)}
        ${x.cmd(t.app?'🧾 Đọc đơn app':'📝 Nhận order','ask',{task:t.id},'primary full')}</article>${extras(x)}</div>`;
    }
    const b=t.bowl,rows=checklistRows(t,x);
    const dump=x.confirmCmd('🗑️ Đổ tô','rs_dump',{task:t.id,confirm:true},'Đổ tô này và làm lại? Nguyên liệu đã dùng được ghi hao hụt.','danger small',!started(b)||plated(t));
    const lid=b.container==='box'&&!b.lid&&!plated(t)?x.cmd('📦 Đậy nắp','rs_lid',{task:t.id},'small'):'';
    const clean=d.clean_checked_day===x.room.day;
    const desk=`<section class="rs-desk" aria-label="Bếp">
      ${pots(t,x)}
      <div class="rs-cookline">${stove(t,x)}<div class="rs-bowlbox">${bowlArt(b,x)}<p class="rs-status" aria-live="polite">${x.esc(bowlStatus(t,x))}</p>${tray(t,x)}</div>${chili(t,x)}</div>
      <div class="rs-cta"><div class="fk-wide-only">${primary(t,x,rows,true)}</div>${lid}${dump}</div>
      ${toppings(t,x)}
      <p class="row wrap rs-tools">${clean?'<span class="tag green">🧽 Đã kiểm vệ sinh hôm nay</span>':x.cmd('🧽 Kiểm vệ sinh bếp','rs_clean',{},'ghost small')} ${x.button('📖 Thực đơn','prices',{},'ghost small')} ${x.button('📦 Kho & nhập hàng','inventory',{},'ghost small')}</p>
    </section>`;
    const bar=actionBar(x.esc(nextStep(t,x)),(lid?lid:'')+primary(t,x,rows,false));
    return `<div class="career-job rs food">${head}<div class="rs-work"><div class="rs-side">${ticket(t,x)}${extras(x)}</div>${desk}</div>${bar}</div>`;
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const w=x.cc.boil||{raw:7,perfect:13,soft:19};
    root.querySelectorAll('[data-boil-start]').forEach(el=>{
      const start=Number(el.dataset.boilStart);if(!start)return;
      const shift=Number(el.dataset.shift)||0,scale=BASE_SCALE+shift,s=Math.max(0,x.now()-start);
      el.querySelector('.boil-fill').style.width=Math.min(100,s/scale*100)+'%';
      el.querySelector('.boil-label').textContent=s.toFixed(1)+' giây · '+(s<w.raw+shift?'chưa chín':s<=w.perfect+shift?'VỚT NGAY!':s<=w.soft+shift?'hơi mềm':'nát rồi');
      el.classList.toggle('ready',s>=w.raw+shift&&s<=w.perfect+shift);el.classList.toggle('over',s>w.soft+shift);
    });
  },
  page(view,x){return view==='prices'?menuPage(x):'';},
  summary(data,x){return gradeCard(data,x);},
  dock:[['prices','book','Thực đơn','Giá & món'],['inventory','box','Kho','Nhập & đếm hàng']],
};
