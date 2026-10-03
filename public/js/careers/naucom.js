/** Nấu cơm gia đình — a hired home cook, one family's meal a day (server: game/careers/naucom.py).
 * The request (how many eat, the market money, the child / the elder / the diet, what the family likes), the menu
 * (one canh, one mặn, one xào, one rau), the market (look, ask for another piece, buy enough portions, haggle once,
 * the receipt), the kitchen (the rice cooker's water line, bowls, the bowl of nước mắm, every dish washed, cut,
 * seasoned, on the right flame and stopped on the stove gauge; two burners), then the market book and the change.
 * The first meal the guide shows each choice; after that it points at the place and the player decides.
 * The server decides everything; one tap sends one command. */
import {stepRows,nextHint,finalGo,pending,stepLine,firstTime} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {data,cc,lower,tile,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput} from './street_kit.js';

const GROUP_ORDER=['canh','man','xao','rau'];
const DISH=(x,k)=>(cc(x).dishes||{})[k]||{name:k,emoji:'🍽️',group:'',ings:[],method:'nau',heat:'vua',tags:[]};
const ING=(x,k)=>(cc(x).ings||{})[k]||{name:k,emoji:'🧺',stall:'rau',price:1,kind:'veg'};
const METHOD=(x,m)=>(cc(x).methods||{})[m]||{name:m,ok:[10,20],burn:28};
const GROUP=(x,g)=>(cc(x).groups||{})[g]||{name:g,emoji:'🍽️'};
const STALL=(x,s)=>(cc(x).stalls||{})[s]||{name:s,short:s,emoji:'🧺',who:''};
const CONS=(x,t)=>(cc(x).cons||{})[t.needs?.con]||{avoid:[],rule:'',emoji:'',label:'',water:'mot'};
const TASTE=(x,t)=>(cc(x).tastes||{})[t.needs?.taste]||{label:'',tag:null,nem:null};
const FIX_FOR={man:'nuoc',lat:'mam',ngot:'chanh',chua:'duong'};
const portions=n=>Math.ceil(Number(n||0)/2);
const unit=(x,t,i)=>ING(x,i).price+(t.needs?.mod==='mua'&&ING(x,i).stall==='rau'?Number(cc(x).rain_up||1):0);
const dishCost=(x,t,k)=>DISH(x,k).ings.reduce((a,i)=>a+unit(x,t,i)*portions(t.needs?.n),0);
const menuCost=(x,t,menu)=>Object.values(menu||{}).reduce((a,k)=>a+dishCost(x,t,k),0);
const clash=(x,t,k)=>DISH(x,k).tags.filter(g=>CONS(x,t).avoid.includes(g));
const wantNem=(x,t)=>{const n=t.needs||{};return (cc(x).extra_nem||{})[`${n.fam}|${n.x}`]||CONS(x,t).nem||TASTE(x,t).nem||'vua';};
const wantCut=(x,t)=>(cc(x).extra_cut||{})[t.needs?.x]||CONS(x,t).cut||'vua';
const tagLabel=(x,g)=>(cc(x).tags||{})[g]||g;
const isMeal=t=>t.kind==='meal';
const FRESH={wash:false,cut:null,nem:null,heat:null,start:null,done:null,q:null,warm:0};
const withDish=t=>isMeal(t)||Object.keys(t.dishes||{}).length||!t.needs?.x?t:{...t,dishes:{[t.needs.x]:{...FRESH}}};
const mealOf=(x,t)=>(x.room.tasks||[]).find(m=>m.kind==='meal'&&m.day===t.day&&!['referred','cancelled'].includes(m.status));
const mealServed=(x,t)=>{const m=mealOf(x,t);return !m||['settle','done'].includes(m.stage)||m.status==='completed';};
const cooking=x=>Number(data(x).cooking||0);

/* ------------------------------------------------------------ the dishes on the stove */
function phase(x,st,k){
  if(st?.start==null||st.done!=null)return null;
  const M=METHOD(x,DISH(x,k).method),s=Math.max(0,x.now()-Number(st.start));
  return {s,lo:M.ok[0],hi:M.ok[1],burn:M.burn};
}
const doneWord=(x,s,lo,hi,burn)=>s<lo?'chưa chín…':s<=hi?'CHÍN TỚI — TẮT BẾP!':s<=burn?'hơi quá lửa…':'cháy khét!';
// A dish waiting on the table cools: after WARM_S seconds the family will notice.
const coolIn=(x,st)=>st?.done==null?null:Number(cc(x).warm_s||90)-(x.now()-Number(st.done));
// The order to cook: the slow dishes first, the raw salad last.
const order=(x,t)=>Object.keys(t.dishes||{}).sort((a,b)=>{const m=k=>DISH(x,k).method==='song'?-1:METHOD(x,DISH(x,k).method).ok[1];return m(b)-m(a);});

/* ------------------------------------------------------------ the tutorial menu (first meal only) */
function suggest(x,t){
  const menu={},tag=TASTE(x,t).tag;
  const dishes=GROUP_ORDER.map(g=>Object.entries(cc(x).dishes||{}).filter(([k,d])=>d.group===g&&!clash(x,t,k).length).map(([k])=>k));
  GROUP_ORDER.forEach((g,i)=>{menu[g]=[...dishes[i]].sort((a,b)=>dishCost(x,t,a)-dishCost(x,t,b))[0];});
  if(tag&&!Object.values(menu).some(k=>DISH(x,k).tags.includes(tag))){
    let best=null;
    GROUP_ORDER.forEach((g,i)=>dishes[i].filter(k=>DISH(x,k).tags.includes(tag)).forEach(k=>{
      const up=dishCost(x,t,k)-dishCost(x,t,menu[g]);if(!best||up<best.up)best={g,k,up};}));
    if(best)menu[best.g]=best.k;
  }
  return menu;
}

/* ------------------------------------------------------------ the request */
function ticket(t,x){
  if(!t.known)return askCard(x,t,'👂 Nghe chủ nhà dặn');
  const n=t.needs||{},c=CONS(x,t);
  if(!isMeal(t))return person(x,t,`<p class="small">${x.esc(n.note||'')}</p>`,'<span class="tag">🍽️ Nấu thêm</span>');
  const chips=[`👥 ${n.n} người`,`💰 ${n.budget} xu`,`${c.emoji} ${c.label}`,TASTE(x,t).label].filter(Boolean).map(s=>`<span class="nc-chip">${x.esc(s)}</span>`).join('');
  return person(x,t,`<p class="nc-chips">${chips}</p><p class="small nc-rule">${x.esc(c.rule)}</p>`);
}

/* ------------------------------------------------------------ ① the menu */
function planPanel(t,x){
  const n=t.needs||{},est=menuCost(x,t,t.menu),over=est>n.budget;
  const groups=GROUP_ORDER.map(g=>{const G=GROUP(x,g);
    const tiles=Object.entries(cc(x).dishes||{}).filter(([,d])=>d.group===g).map(([k,D])=>{const on=t.menu?.[g]===k;
      const tags=D.tags.map(tg=>`<i class="nc-tag ${clash(x,t,k).includes(tg)?'bad':''}">${x.esc(tagLabel(x,tg))}</i>`).join('');
      return tile(x,'nc_pick',{task:t.id,group:g,dish:k},`<span class="tile-emoji">${x.esc(D.emoji)}</span><b>${x.esc(D.name)}</b><small>${dishCost(x,t,k)} xu</small>${tags?`<span class="nc-tags">${tags}</span>`:''}`,on?'selected':'');}).join('');
    return `<div class="nc-group" data-group="${g}"><h4>${x.esc(G.emoji)} ${x.esc(G.name)}${t.menu?.[g]?` <small>· ${x.esc(DISH(x,t.menu[g]).name)}</small>`:''}</h4><div class="tile-grid nc-dishes">${tiles}</div></div>`;}).join('');
  return `<section class="card nc-menu"><h4>📝 Thực đơn hôm nay</h4><p class="small nc-est ${over?'nc-bad':''}">Dự tính <b>${est}</b>/${n.budget} xu · mỗi phần đủ hai người</p>
    <span class="sk-meter ${over?'bad':''}"><i style="width:${Math.min(100,est/Math.max(1,n.budget)*100)}%"></i></span>${groups}</section>`;
}
function planSteps(t,x){
  const rows=[],first=firstTime(x),pick=first?suggest(x,t):{};
  for(const g of GROUP_ORDER){const G=GROUP(x,g),k=t.menu?.[g];
    if(k){const bad=clash(x,t,k);rows.push({ok:bad.length?false:true,label:`${G.name}: ${DISH(x,k).name}`,note:bad.length?`không hợp: ${bad.map(b=>tagLabel(x,b)).join(', ')}`:'',
      go:bad.length?{sel:`.nc-group[data-group="${g}"]`,label:`👆 Đổi ${lower(G.name)}`}:null});continue;}
    rows.push(first&&pick[g]?{ok:null,label:`Chọn ${lower(G.name)}`,go:{cmd:'nc_pick',payload:{task:t.id,group:g,dish:pick[g]},label:`${DISH(x,pick[g]).emoji} ${DISH(x,pick[g]).name}`}}
      :{ok:null,label:`Chọn ${lower(G.name)}`,note:CONS(x,t).label,go:{sel:`.nc-group[data-group="${g}"]`,label:`👆 Chọn ${lower(G.name)}`}});
  }
  const tag=TASTE(x,t).tag;
  if(tag&&GROUP_ORDER.every(g=>t.menu?.[g])&&!Object.values(t.menu).some(k=>DISH(x,k).tags.includes(tag)))
    rows.push({ok:false,label:TASTE(x,t).label,note:'thực đơn chưa có',go:{sel:'.nc-menu',label:'👆 Xem lại thực đơn'}});
  const est=menuCost(x,t,t.menu);
  if(est>t.needs.budget)rows.push({ok:false,label:'Quá tiền chợ',note:`${est}/${t.needs.budget} xu`,go:{sel:'.nc-menu',label:'👆 Đổi món rẻ hơn'}});
  return rows;
}

/* ------------------------------------------------------------ ② the market */
function ingRow(t,x,i){
  const row=t.cart[i],I=ING(x,i),u=unit(x,t,i),look=row.look;
  const chip=look==='tuoi'?'<span class="nc-look ok">✓ tươi</span>':look==='uon'?'<span class="nc-look bad">✗ không tươi</span>':'<span class="nc-look">chưa xem</span>';
  let tools='';
  if(row.n>0)tools=`<span class="nc-got">🛒 ${row.n} phần · ${row.paid} xu</span>${x.cmd('↩️','nc_return',{task:t.id,ing:i},'small ghost nc-back')}`;
  else{
    const buy=[1,2,3,4].map(k=>x.cmd(`🛒 ${k}`,'nc_buy',{task:t.id,ing:i,n:k},'small nc-buy-n',t.purse<u*k)).join('');
    tools=`${row.seen?'':x.cmd('👀 Xem','nc_look',{task:t.id,ing:i},'small nc-eye')}${row.seen&&!row.swap?x.cmd('🔄 Đổi','nc_swap',{task:t.id,ing:i},'small ghost'):''}<span class="nc-buy" role="group" aria-label="Mua mấy phần">${buy}</span>`;
  }
  return `<li class="nc-ing" data-ing="${x.esc(i)}"><span class="nc-ing-head"><span aria-hidden="true">${x.esc(I.emoji)}</span><b>${x.esc(I.name)}</b><small>${u} xu/phần</small>${chip}</span><span class="nc-tools">${tools}</span></li>`;
}
function marketPanel(t,x){
  const stalls=Object.keys(t.bills||{}).map(st=>{const S=STALL(x,st),b=t.bills[st],ings=Object.keys(t.cart).filter(i=>ING(x,i).stall===st);
    const tools=[b.haggle==null?x.cmd('🙏 Xin bớt','nc_haggle',{task:t.id,stall:st},'small ghost',b.paid<3):`<span class="tag">${b.haggle==='ok'?`🙏 bớt ${b.off} xu`:'🙏 không bớt'}</span>`,
      b.receipt?'<span class="tag green">🧾 có hóa đơn</span>':x.cmd('🧾 Xin hóa đơn','nc_receipt',{task:t.id,stall:st},'small',!b.paid)].join('');
    return `<section class="card nc-stall" data-stall="${st}"><h4>${x.esc(S.emoji)} ${x.esc(S.name)} <small>· ${b.paid} xu</small></h4><ul class="nc-ings">${ings.map(i=>ingRow(t,x,i)).join('')}</ul><div class="nc-row">${tools}</div></section>`;}).join('');
  return `<p class="nc-purse">👛 Ví tiền chợ <b>${t.purse}</b> xu · mỗi phần đủ hai người</p>${stalls}`;
}
function marketSteps(t,x){
  const rows=[],first=firstTime(x),want=portions(t.needs.n);
  for(const st of Object.keys(t.bills||{})){
    const ings=Object.keys(t.cart).filter(i=>ING(x,i).stall===st);
    for(const i of ings){const row=t.cart[i],I=ING(x,i);
      if(row.n>0){rows.push({ok:true,label:`${I.name}: ${row.n} phần`});continue;}
      if(!row.seen){rows.push({ok:null,label:`Xem ${lower(I.name)}`,go:{cmd:'nc_look',payload:{task:t.id,ing:i},label:`👀 Xem ${lower(I.name)}`}});continue;}
      if(row.look==='uon'&&!row.swap){rows.push({ok:false,label:`${I.name} không tươi`,go:{cmd:'nc_swap',payload:{task:t.id,ing:i},label:'🔄 Xin phần khác'}});continue;}
      rows.push(first?{ok:null,label:`Mua ${lower(I.name)}`,note:`${t.needs.n} người · mỗi phần đủ hai người`,go:{cmd:'nc_buy',payload:{task:t.id,ing:i,n:want},label:`🛒 Mua ${want} phần ${lower(I.name)}`}}
        :{ok:null,label:`Mua ${lower(I.name)}`,note:'mỗi phần đủ hai người',go:{sel:`.nc-ing[data-ing="${i}"] .nc-buy`,label:`👆 Mua ${lower(I.name)}`}});
    }
    const b=t.bills[st];
    if(ings.every(i=>t.cart[i].n>0)&&!b.receipt)rows.push({ok:null,label:`Hóa đơn ${STALL(x,st).short}`,go:{cmd:'nc_receipt',payload:{task:t.id,stall:st},label:'🧾 Xin hóa đơn'}});
  }
  return rows;
}

/* ------------------------------------------------------------ ③ the kitchen */
function gauge(x,k,st){
  const p=phase(x,st,k);if(!p)return '';
  const max=p.burn+6,w=v=>`${v/max*100}%`;
  const zones=`<i class="nc-z raw" style="width:${w(p.lo)}"></i><i class="nc-z ok" style="width:${w(p.hi-p.lo)}"></i><i class="nc-z over" style="width:${w(p.burn-p.hi)}"></i><i class="nc-z burnt"></i>`;
  return `<div class="nc-gauge ${p.s>=p.lo&&p.s<=p.hi?'ready':''}" data-dish="${x.esc(k)}" data-nc-from="${Number(st.start)}" data-max="${max}" data-lo="${p.lo}" data-hi="${p.hi}" data-burn="${p.burn}"><div class="nc-track">${zones}<span class="nc-needle"></span></div><small class="nc-gauge-label">${p.s.toFixed(1)} giây · ${x.esc(doneWord(x,p.s,p.lo,p.hi,p.burn))}</small></div>`;
}
function dishCard(t,x,k,watch){
  const D=DISH(x,k),st=t.dishes[k],M=METHOD(x,D.method),c=cc(x),song=D.method==='song',tid=t.id;
  const opts=(map,cmd,field,cur)=>`<div class="nc-row nc-opts" role="group">${Object.entries(map||{}).map(([v,l])=>x.cmd(x.esc(l),cmd,{task:tid,dish:k,[field]:v},`small ${cur===v?'primary':'ghost'}`)).join('')}</div>`;
  let body='',line='';
  if(st.done!=null){
    const cool=coolIn(x,st);
    line=song?'bày ra đĩa':`${(c.done_note||{})[st.q]||st.q}${cool!=null&&cool<0?' · nguội rồi':''}`;
    if(!song&&isMeal(t)&&cool!=null&&cool<Number(c.warm_s||90)/3)body=x.cmd('♨️ Hâm nóng','nc_reheat',{task:tid,dish:k},'small ghost',cooking(x)>=Number(c.burners||2));
  }else if(st.start!=null){
    line=`${lower(c.heats?.[st.heat]||'')} · chín tới trong ${M.ok[0]}–${M.ok[1]} giây`;
    body=`${gauge(x,k,st)}<div class="nc-row">${x.cmd('✋ Tắt bếp','nc_off',{task:tid,dish:k},'primary nc-stop').replace('<button ',`<button data-dish="${x.esc(k)}"${watch===k?` data-fd-wait=".nc-gauge.ready[data-dish='${k}']"`:''} `)}</div>`;
  }else if(!st.wash){line='chưa rửa';body=x.cmd('🚿 Rửa sạch','nc_wash',{task:tid,dish:k},'small');}
  else if(!st.cut){line='sơ chế';body=opts(c.cuts,'nc_cut','cut',st.cut);}
  else if(!song&&st.nem==null){line='nêm nếm';body=opts(c.nems,'nc_nem','nem',st.nem);}
  else{line=`${M.name} · chọn lửa`;body=`<div class="nc-row nc-opts" role="group">${Object.entries(c.heats||{}).map(([v,l])=>x.cmd(`🔥 ${x.esc(l)}`,'nc_fire',{task:tid,dish:k,heat:v},'small ghost',cooking(x)>=Number(c.burners||2))).join('')}</div>${cooking(x)>=Number(c.burners||2)?'<small class="muted">Hai bếp đang bận</small>':''}`;}
  const marks=[st.wash?'🚿':'',st.cut?'🔪':'',st.nem?'🧂':'',st.done!=null?'✅':st.start!=null?'🔥':''].filter(Boolean).join(' ');
  return `<section class="card nc-dish ${st.start!=null&&st.done==null?'on-fire':''}" data-dish="${x.esc(k)}"><h4><span aria-hidden="true">${x.esc(D.emoji)}</span> ${x.esc(D.name)} <small>${marks}</small></h4><p class="small muted">${x.esc(line)}</p>${body}</section>`;
}
function riceCard(t,x){
  const r=t.rice,c=cc(x);
  if(!r)return `<section class="card nc-rice"><h4>🍚 Nồi cơm: đổ nước tới đâu?</h4><div class="nc-row nc-opts" role="group">${Object.entries(c.water||{}).map(([k,l])=>x.cmd(x.esc(l),'nc_rice',{task:t.id,water:k},'small ghost')).join('')}</div></section>`;
  const left=Math.ceil(Number(r.at)-x.now());
  return `<section class="card nc-rice"><h4>🍚 Nồi cơm <small>· ${x.esc(lower(c.water?.[r.w]||''))}</small></h4><p class="small" data-nc-rice="${Number(r.at)}">${left>0?`chín sau ${left}s`:'cơm chín, giữ ấm'}</p></section>`;
}
function tableCard(t,x){
  const tb=t.table||{},c=cc(x);
  const bowls=amountBox(x,`nc-bowls-${t.id}`,tb.bowls||1,{min:1,max:Number(c.bowls_max||12),label:tb.bowls?`Đã bày ${tb.bowls} bộ chén đũa`:'Bộ chén đũa',send:tb.bowls?'🥢 Bày lại':'🥢 Bày chén',cmd:'nc_bowls',payload:{task:t.id},field:'n',unit:'bộ'});
  const mam=!tb.tasted?x.cmd('🥄 Nếm nước mắm','nc_taste',{task:t.id},'small')
    :`<p class="small">🫙 ${x.esc((c.taste||{})[tb.mam]||'')}</p>${tb.mam==='ok'?'':`<div class="nc-row nc-opts nc-mam" role="group">${Object.entries(c.fix||{}).map(([k,l])=>x.cmd(x.esc(l),'nc_fix',{task:t.id,add:k},'small ghost')).join('')}</div>`}`;
  return `<section class="card nc-table"><h4>🍽️ Mâm cơm</h4><div class="nc-bowls">${bowls}</div><h4 class="section-title">🫙 Chén nước mắm chấm</h4>${mam}</section>`;
}
function stoveBar(t,x){
  const ks=order(x,t),b=Number(cc(x).burners||2),n=cooking(x);
  return `<div class="nc-stove" role="group" aria-label="Bếp"><span class="nc-burner ${n>0?'on':''}">🔥</span><span class="nc-burner ${n>1?'on':''}">🔥</span><small>${n}/${b} bếp đang nấu · ${ks.filter(k=>t.dishes[k].done!=null).length}/${ks.length} món xong</small></div>`;
}
function kitchenSteps(t,x){
  const rows=[],first=firstTime(x),c=cc(x),tb=t.table||{},meal=isMeal(t),full=cooking(x)>=Number(c.burners||2);
  let watch=null;
  // A dish in its window comes first: everything else can wait a few seconds.
  const hot=order(x,t).map(k=>({k,p:phase(x,t.dishes[k],k)})).filter(o=>o.p).sort((a,b)=>Number(t.dishes[a.k].start)-Number(t.dishes[b.k].start));
  for(const o of hot)if(o.p.s>=o.p.lo){watch=watch||o.k;rows.push({ok:null,label:`Tắt bếp ${lower(DISH(x,o.k).name)}`,note:o.p.s>o.p.hi?'quá lửa rồi':'chín tới',go:{cmd:'nc_off',payload:{task:t.id,dish:o.k},label:'✋ Tắt bếp'}});}
  if(meal){
    if(!t.rice)rows.push(first?{ok:null,label:'Nấu nồi cơm',go:{cmd:'nc_rice',payload:{task:t.id,water:CONS(x,t).water||'mot'},label:`🍚 Đổ nước ${lower(c.water?.[CONS(x,t).water||'mot']||'')}`}}
      :{ok:null,label:'Nấu nồi cơm',note:'nhớ người trong nhà',go:{sel:'.nc-rice .nc-opts',label:'👆 Đổ nước nồi cơm'}});
    else rows.push({ok:true,label:'Nồi cơm đã bắc'});
    if(!tb.bowls)rows.push(first?{ok:null,label:'Bày chén đũa',go:{cmd:'nc_bowls',payload:{task:t.id,n:t.needs.n},label:`🥢 Bày ${t.needs.n} bộ chén đũa`}}
      :{ok:null,label:'Bày chén đũa',note:'mỗi người một bộ',go:{sel:'.nc-bowls',label:'👆 Bày chén đũa'}});
    if(!tb.tasted)rows.push({ok:null,label:'Nếm nước mắm',go:{cmd:'nc_taste',payload:{task:t.id},label:'🥄 Nếm nước mắm'}});
    else if(tb.mam!=='ok'){const k=FIX_FOR[tb.mam];rows.push(first&&k?{ok:false,label:'Pha lại nước mắm',note:(c.taste||{})[tb.mam]||'',go:{cmd:'nc_fix',payload:{task:t.id,add:k},label:`🫙 ${(c.fix||{})[k]||'Pha lại'}`}}
      :{ok:false,label:'Pha lại nước mắm',note:(c.taste||{})[tb.mam]||'',go:{sel:'.nc-mam',label:'👆 Pha lại cho vừa'}});}
  }
  for(const k of order(x,t)){const D=DISH(x,k),st=t.dishes[k],song=D.method==='song',sel=s=>`.nc-dish[data-dish="${k}"] ${s}`;
    if(st.done!=null){const cool=coolIn(x,st);
      if(meal&&!song&&cool!=null&&cool<0)rows.push({ok:false,label:`${D.name} nguội rồi`,go:full?null:{cmd:'nc_reheat',payload:{task:t.id,dish:k},label:'♨️ Hâm nóng'}});
      else rows.push({ok:true,label:D.name});continue;}
    if(st.start!=null){const p=phase(x,st,k);if(p&&p.s<p.lo)rows.push({ok:null,label:`${D.name} đang ${METHOD(x,D.method).name}`,note:`còn ${Math.ceil(p.lo-p.s)} giây`,go:null,wait:k});continue;}
    if(!st.wash){rows.push({ok:null,label:`${D.name}: rửa`,go:{cmd:'nc_wash',payload:{task:t.id,dish:k},label:'🚿 Rửa sạch'}});continue;}
    if(!st.cut){const v=wantCut(x,t);rows.push(first?{ok:null,label:`${D.name}: cắt`,go:{cmd:'nc_cut',payload:{task:t.id,dish:k,cut:v},label:`🔪 ${(c.cuts||{})[v]||'Cắt'}`}}
      :{ok:null,label:`${D.name}: cắt`,note:CONS(x,t).label||'nhớ người ăn',go:{sel:sel('.nc-opts'),label:'👆 Cắt thế nào?'}});continue;}
    if(!song&&st.nem==null){const v=wantNem(x,t);rows.push(first?{ok:null,label:`${D.name}: nêm`,go:{cmd:'nc_nem',payload:{task:t.id,dish:k,nem:v},label:`🧂 ${(c.nems||{})[v]||'Nêm'}`}}
      :{ok:null,label:`${D.name}: nêm`,note:TASTE(x,t).label||'nhớ khẩu vị nhà',go:{sel:sel('.nc-opts'),label:'👆 Nêm thế nào?'}});continue;}
    if(full){rows.push({ok:null,label:`${D.name}: chờ bếp trống`,note:'hai bếp đang bận',go:null});continue;}
    rows.push(first?{ok:null,label:`${D.name}: bắc bếp`,go:{cmd:'nc_fire',payload:{task:t.id,dish:k,heat:D.heat},label:`🔥 ${(c.heats||{})[D.heat]||'Bắc bếp'}`}}
      :{ok:null,label:`${D.name}: bắc bếp`,note:`món ${METHOD(x,D.method).name}`,go:{sel:sel('.nc-opts'),label:'👆 Chọn lửa'}});
  }
  // Nothing else to do: watch the dish that will be ready first, and stop it in time.
  if(!pending(rows)?.go){const w=hot.find(o=>o.p.s<o.p.lo);
    if(w){watch=watch||w.k;const i=rows.findIndex(r=>r.wait===w.k);
      const row={ok:null,label:`Canh ${lower(DISH(x,w.k).name)}`,note:`còn ${Math.ceil(w.p.lo-w.p.s)} giây`,go:{sel:`.nc-stop[data-dish="${w.k}"]`,label:'👆 Tắt bếp khi kim vào vùng xanh'}};
      if(i>=0)rows[i]=row;else rows.unshift(row);}}
  return {rows,watch};
}

/* ------------------------------------------------------------ ④ the market book */
function settlePanel(t,x){
  const rows=Object.entries(t.bills||{}).filter(([,b])=>b.paid>0).map(([st,b])=>{const S=STALL(x,st),filed=(t.filed||[]).includes(st);
    return `<li class="nc-bill"><span aria-hidden="true">${x.esc(S.emoji)}</span><b>${x.esc(S.name)}</b><small>${b.paid} xu${b.receipt?' · 🧾 có hóa đơn':' · không hóa đơn'}</small>${filed?'<span class="tag green">✓ đã ghi</span>':x.cmd(b.receipt?'📒 Kẹp hóa đơn':'✍️ Ghi tay','nc_file',{task:t.id,stall:st},'small')}</li>`;}).join('');
  const spent=t.needs.budget-t.purse;
  return `<section class="card nc-book"><h4>📒 Sổ chợ</h4><ul class="nc-bills">${rows}</ul><p class="small">Tiền chợ ${t.needs.budget} xu · tiêu ${spent} xu · <b>gửi lại ${t.purse} xu</b></p></section>`;
}
function settleSteps(t,x){
  return Object.entries(t.bills||{}).filter(([,b])=>b.paid>0).map(([st,b])=>(t.filed||[]).includes(st)?{ok:true,label:`Sổ chợ: ${STALL(x,st).short}`}
    :{ok:null,label:`Ghi sổ ${STALL(x,st).short}`,go:{cmd:'nc_file',payload:{task:t.id,stall:st},label:b.receipt?'📒 Kẹp hóa đơn vào sổ':'✍️ Ghi tay vào sổ'}});
}

/* ------------------------------------------------------------ the guide */
const deskGuide={steps:[{ok:null,label:'Quyết chuyện trong nhà',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
const introGuide={steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'nc_intro',payload:{},label:'🍲 Vào việc thôi!'}}],final:null};
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return deskGuide;
  if(!d.intro)return introGuide;
  if(!t.known)return {steps:[{ok:null,label:'Nghe chủ nhà dặn',go:{cmd:'ask',payload:{task:t.id},label:'👂 Nghe chủ nhà dặn'}}],final:null,pulse:'.sk-ask'};
  if(!isMeal(t)){
    if(!mealServed(x,t)){const m=mealOf(x,t);return {steps:[{ok:null,label:'Dọn bữa chính xong rồi nấu thêm',go:m?{cmd:'task_select',payload:{task:m.id},label:'🍲 Về bữa chính'}:null}],final:null};}
    const {rows,watch}=kitchenSteps(withDish(t),x),k=t.needs?.x,ok=t.dishes?.[k]?.done!=null;
    return {steps:rows,watch,final:{label:'🍽️ MANG RA',go:finalGo(rows,'nc_bring',{task:t.id}),ready:ok,why:'nấu xong món đã'}};
  }
  if(t.stage==='plan'){const steps=planSteps(t,x),all=GROUP_ORDER.every(g=>t.menu?.[g]),fit=menuCost(x,t,t.menu)<=t.needs.budget;
    return {steps,final:{label:'📝 CHỐT THỰC ĐƠN',go:finalGo(steps,'nc_plan',{task:t.id}),ready:all&&fit,why:all?'quá tiền chợ':'chọn đủ bốn món'}};}
  if(t.stage==='market'){const steps=marketSteps(t,x),all=Object.values(t.cart||{}).every(r=>r.n>0);
    return {steps,final:{label:'🏠 VỀ NHÀ NẤU',go:finalGo(steps,'nc_home',{task:t.id}),ready:all,why:'mua đủ đồ đã'}};}
  if(t.stage==='settle'){const steps=settleSteps(t,x);return {steps,final:{label:'💵 GỬI TIỀN THỪA',go:finalGo(steps,'nc_done',{task:t.id}),ready:steps.every(s=>s.ok),why:'ghi sổ chợ đã'}};}
  const {rows,watch}=kitchenSteps(t,x),tb=t.table||{};
  const riceOk=t.rice&&x.now()>=Number(t.rice.at),dishes=Object.values(t.dishes||{}).every(s=>s.done!=null);
  const why=!t.rice?'nấu cơm đã':!dishes?'nấu xong các món đã':!tb.bowls?'bày chén đũa đã':!riceOk?'cơm chưa chín':'';
  return {steps:rows,watch,final:{label:'🍚 DỌN CƠM',go:finalGo(rows,'nc_serve',{task:t.id}),ready:!why,why}};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});
/** When the guide changes by itself (the rice cooked, a dish in its window or cooling): the workbench redraws then. */
function wakeAt(t,x){
  const now=x.now(),at=[],warm=Number(cc(x).warm_s||90);
  if(t?.rice&&Number(t.rice.at)>now)at.push(Number(t.rice.at));
  for(const [k,st] of Object.entries(t?.dishes||{})){const p=phase(x,st,k);
    if(p){const s0=Number(st.start);for(const v of [s0+p.lo,s0+p.hi,s0+p.burn])if(v>now)at.push(v);}
    else if(st.done!=null&&DISH(x,k).method!=='song')for(const v of [Number(st.done)+warm*2/3,Number(st.done)+warm])if(v>now)at.push(v);}
  return at.length?Math.min(...at)+0.2:0;
}

const top=x=>`${introCard(x,'nc_intro','🍲')}${deskCard(x,'nc_desk','Chuyện trong nhà')}`;

export default {
  id:'naucom',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return !t.known?'Nghe chủ nhà dặn':isMeal(t)?'Nấu bữa cơm cho nhà':'Nấu thêm một món';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk nc">${hint}${top(x)}${bottom(x,g)}</div>`;
    let main='',side='';
    if(!t.known)main='';
    else if(!isMeal(t)){
      if(!mealServed(x,t))main='<p class="card small muted">Dọn bữa chính xong rồi nấu thêm món này nhé.</p>';
      else{const tt=withDish(t);main=`${stoveBar(tt,x)}${dishCard(tt,x,t.needs?.x,g.watch)}`;side=stepRows(x,g.steps,'Món nấu thêm');}
    }
    else if(t.stage==='plan'){main=planPanel(t,x);side=stepRows(x,g.steps,'Lên thực đơn');}
    else if(t.stage==='market'){main=marketPanel(t,x);side=stepRows(x,g.steps,'Đi chợ');}
    else if(t.stage==='settle'||t.stage==='done'){main=settlePanel(t,x);side=stepRows(x,g.steps,'Sổ chợ');}
    else{main=`${stoveBar(t,x)}${riceCard(t,x)}${tableCard(t,x)}${order(x,t).map(k=>dishCard(t,x,k,g.watch)).join('')}`;side=stepRows(x,g.steps,'Trong bếp');}
    return `<div class="career-job sk nc" data-nc-wake="${wakeAt(t,x)}">${hint}${top(x)}${ticket(t,x)}${dayBar(x)}<div class="workbench"><section class="wb-main">${main}</section>${side?`<aside class="wb-side">${side}</aside>`:''}</div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x);
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?deskGuide:introGuide;return `<div class="career-job sk nc">${hintFor(g,x)}${top(x)}${bottom(x,g)}</div>`;}
    const f=d.family||{},visits=Number(d.families?.[f.id]?.visits||0),today=d.today||{};
    const done=today.meals?`<p class="small">🍲 Bữa cơm ${x.esc(lower(f.name||''))} xong rồi${today.extras?`, thêm ${today.extras} món`:''}. Gửi lại ${today.back||0} xu tiền chợ.</p>`:'';
    return `<div class="career-job sk nc">${top(x)}${dayBar(x)}<section class="card nc-home"><h4>${x.esc(f.emoji||'🏠')} ${x.esc(f.name||'')}</h4><p class="small muted">${visits?`Đã nấu ${visits} bữa cho nhà này.`:'Nhà mới, nghe dặn cho kỹ.'}</p>${done}</section></div>`;
  },
  tick(root,x){
    keepBarAboveFooter(root);
    const w=root.matches?.('[data-nc-wake]')?root:root.querySelector('[data-nc-wake]'),at=Number(w?.dataset.ncWake||0);
    if(at&&x.now()>=at){w.dataset.ncWake='0';x.render();return;}
    root.querySelectorAll('[data-nc-rice]').forEach(el=>{const left=Math.ceil(Number(el.dataset.ncRice)-x.now()),s=left>0?`chín sau ${left}s`:'cơm chín, giữ ấm';if(el.textContent!==s)el.textContent=s;});
  },
  // The stove gauges: the needle glides on the compositor; "Tắt bếp" holds it where the finger came down (tapStop).
  meters(root,x){
    root.querySelectorAll('[data-nc-from]').forEach(el=>{
      const from=Number(el.dataset.ncFrom),max=Number(el.dataset.max)||30,lo=Number(el.dataset.lo),hi=Number(el.dataset.hi),burn=Number(el.dataset.burn),s=Math.max(0,x.now()-from);
      x.slide(el.querySelector('.nc-needle'),s/max*100,100/max);
      const l=el.querySelector('.nc-gauge-label'),text=`${s.toFixed(1)} giây · ${doneWord(x,s,lo,hi,burn)}`;
      if(l&&l.textContent!==text)l.textContent=text;
      el.classList.toggle('ready',s>=lo&&s<=hi);el.classList.toggle('over',s>burn);
    });
  },
  tapStop:op=>op==='nc_off',
  input(el,x){return kitInput(el,x);},
  summary(data,x){
    if(!data||data.meals==null)return '';
    const tm=data.tomorrow,row=(l,v)=>`<div class="kv-row"><span>${l}</span><b>${v}</b></div>`;
    const plan=`<section class="nc-plan" aria-label="Ngày mai"><h4 class="section-title">🌅 Ngày mai</h4>${tm?`<p class="nc-tomorrow"><span aria-hidden="true">${x.esc(tm.fam_emoji||tm.emoji)}</span> <b>${x.esc(tm.family||'')}</b><small>${x.esc(tm.emoji)} ${x.esc(tm.label)} · ${x.esc(tm.hint)}</small></p>`:''}${data.cold?`<p class="small">♨️ ${data.cold} món nguội: món lâu chín bắc trước.</p>`:''}</section>`;
    const kv=`<div class="kv">${row('Bữa cơm',data.meals)}${data.extras?row('Món nấu thêm',data.extras):''}${data.budget?row('Tiền chợ',`${data.spent}/${data.budget} xu`):''}${data.back?row('Gửi lại',`${data.back} xu`):''}</div>`;
    return `<article class="card space-top nc-sum">${plan}<details class="nc-sum-more"><summary>🍲 Bếp nhà khách hôm nay</summary>${kv}</details></article>`;
  },
  actions:{...kitActions},
  dock:[],
};
