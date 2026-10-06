/** Thư viện – Lưu trữ phường Mây — the ward library and its archive (server: game/careers/library.py).
 * The morning (hygrometer, traps, the reading room), the desk (borrowing with the card rules, returns with a fee
 * the player names, repairs, a recommendation by taste), cataloguing (class, author mark, weeding), the reading-room
 * round, the archive window (briefing, papers, access level, the right box, copies, the log) and the awkward asks.
 * The server decides everything; one tap sends one command. Steps that need the player's judgement only point. */
import {stepRows,nextHint,finalGo,pending,stepLine} from '../v4/guide.js';
import {keepBarAboveFooter} from './food_kit.js';
import {planBox,stockLines,figures} from './plan_kit.js';
import {data,cc,lower,tile,pane,introCard,deskCard,dayBar,person,askCard,bottom,kitActions,amountBox,kitInput,choiceCard,debtBook,meter,clean} from './street_kit.js';

/** A panel button's label in two words on the clean layout (the bar names the step in full); readers get the full one. */
const say2=(full,short)=>clean()?`<span aria-hidden="true">${short}</span><span class="sr-only">${full}</span>`:full;

const DONE_ST=['completed','cancelled','referred'];
const tag=(x,text,kind='')=>`<span class="tag ${kind}">${x.esc(text)}</span>`;
const row=(x,emoji,label,text)=>`<li class="seen"><span aria-hidden="true">${emoji}</span><div><b>${x.esc(label)}</b>${text?`<small>${x.esc(text)}</small>`:''}</div></li>`;
const btnCmd=(x,label,cmd,payload,cls='ghost',dis=false)=>x.cmd(label,cmd,payload,`tv-btn ${cls}`,dis);

/* ------------------------------------------------------------ the person and their ask */
function ticket(t,x,inner=''){
  if(!t.known)return askCard(x,t,'👂 Nghe bạn đọc nói');
  const kind={desk:'🔖 Quầy mượn trả',catalog:'🏷️ Biên mục',room:'🤫 Phòng đọc',archive:'🗂️ Lưu trữ'}[t.kind]||'';
  return person(x,t,inner,kind?tag(x,kind,'blue'):'');
}
function askBox(t,x){
  const a=t.ask;if(!a||a.state!=='on')return '';
  const o=(choice,label,sub)=>({cmd:'tv_ask',payload:{task:t.id,choice},label,sub});
  return choiceCard(x,'tv-ask','🙋',`${a.who} nhờ việc`,a.text,[
    o('yes',`👍 ${x.esc(a.yes)}`,'chiều người ta'),o('alt',`💡 ${x.esc(a.alt)}`,'cách khác hợp nội quy'),
    o('no',`🙅 ${x.esc(a.no)}`,'có người dỗi'),o('boss','👩‍🏫 Nhờ cô Nguyệt','mất thêm thời gian')]);
}

/* ------------------------------------------------------------ the morning */
function openPanel(t,x){
  const st=t.st||{},ok=cc(x).hum_ok||[45,60],hum=t.hum;
  const humRow=hum==null?btnCmd(x,say2('🌡️ Xem ẩm kế kho','🌡️ Ẩm kế'),'tv_look',{task:t.id,what:'am'},'full')
    :`<div class="tv-hum ${hum>ok[1]?'hi':''}"><b>🌡️ ${hum}%</b>${meter(hum,100,hum>ok[1]?'bad':'')}<small>${clean()?`giữ ${ok[0]}–${ok[1]}%`:`Kho giấy giữ ${ok[0]}–${ok[1]}%`}</small></div>`;
  const dehum=x.cmd(st.dehum?say2('💧 Máy hút ẩm: đang chạy','💧 Đang hút ẩm'):say2('💧 Bật máy hút ẩm','💧 Hút ẩm'),'tv_dehum',{task:t.id},st.dehum?'tv-btn tv-on':'tv-btn ghost');
  const fixes=Object.entries(cc(x).pest_fix||{}).map(([k,l])=>x.cmd(x.esc(l),'tv_pest',{task:t.id,how:k},`tv-opt ${st.pest===k?'tv-on':''}`)).join('');
  const pest=t.pest==null?btnCmd(x,say2('🪤 Soi bẫy côn trùng','🪤 Soi bẫy'),'tv_look',{task:t.id,what:'bay'},'full')
    :`<p class="tv-note">🪤 ${x.esc((cc(x).pests||{})[t.pest]||'')}</p><div class="tv-opts tv-pests">${fixes}</div>`;
  const door=(done,full,short,what)=>done?tag(x,`✓ ${clean()?short:full}`,'green'):btnCmd(x,say2(full,short),'tv_look',{task:t.id,what});
  // Clean layout: the buttons name their own job, so the three cards lose their headings (icons stay).
  const h=(e,l)=>`<h4>${e}${clean()?'':` ${l}`}</h4>`;
  return `<section class="card tv-store">${h('🗄️','Kho lưu trữ')}${humRow}<div class="tv-row">${dehum}</div></section>
    <section class="card tv-trap">${h('🪤','Bẫy côn trùng')}${pest}</section>
    <section class="card tv-door">${h('🚪','Phòng đọc')}<div class="tv-row">${door(st.room,'🔑 Mở phòng đọc','🔑 Phòng đọc','phong')}${door(st.board,'📋 Dựng bảng nội quy','📋 Nội quy','bang')}</div></section>`;
}
function openSteps(t,x){
  const st=t.st||{},ok=cc(x).hum_ok||[45,60],rows=[];
  rows.push({ok:t.hum!=null||null,label:'Xem ẩm kế kho',go:{cmd:'tv_look',payload:{task:t.id,what:'am'},label:'🌡️ Xem ẩm kế kho'}});
  if(t.hum!=null&&t.hum>ok[1])rows.push({ok:st.dehum||null,label:'Kho quá ẩm: bật máy hút ẩm',go:{cmd:'tv_dehum',payload:{task:t.id},label:'💧 Bật máy hút ẩm'}});
  rows.push({ok:t.pest!=null||null,label:'Soi bẫy côn trùng',go:{cmd:'tv_look',payload:{task:t.id,what:'bay'},label:'🪤 Soi bẫy côn trùng'}});
  if(t.pest!=null)rows.push({ok:st.pest?true:null,label:'Chọn cách xử lý bẫy',go:{sel:'.tv-pests',label:'🪤 Chọn cách xử lý'},pulse:''});
  rows.push({ok:st.room||null,label:'Mở phòng đọc',go:{cmd:'tv_look',payload:{task:t.id,what:'phong'},label:'🔑 Mở phòng đọc'}});
  rows.push({ok:st.board||null,label:'Dựng bảng nội quy',go:{cmd:'tv_look',payload:{task:t.id,what:'bang'},label:'📋 Dựng bảng nội quy'}});
  return rows;
}

/* ------------------------------------------------------------ the desk: borrowing */
const STATUS={avail:['Còn trên kệ','green'],ref:['Sách tra cứu: chỉ đọc tại chỗ','amber'],out:['Đang có người mượn','danger']};
function borrowPanel(t,x){
  const st=t.st||{},i=t.info||{},card=t.cardinfo,offers=cc(x).offers||{};
  const look=st.looked?`<li class="seen"><span>🔎</span><div><b>${x.esc(i.call||'')} · ${x.esc(i.shelf||'')}</b>${tag(x,(STATUS[i.status]||['',''])[0]+(i.status==='out'?` · hẹn trả ngày ${i.back}`:''),(STATUS[i.status]||['',''])[1])}</div></li>`
    :`<li>${btnCmd(x,'🔎 Tra máy','tv_lookup',{task:t.id},'full')}</li>`;
  const cardTxt=card?{ok:['Thẻ còn hạn','green'],expired:['Thẻ hết hạn','amber'],limit:[`Đang mượn đủ ${cc(x).loan_max||3} cuốn`,'amber'],debt:[`Còn nợ ${card.owe} xu phí cũ`,'danger']}[card.card]:null;
  const cardRow=card?`<li class="seen"><span>🪪</span><div><b>Thẻ bạn đọc</b>${tag(x,cardTxt[0],cardTxt[1])}</div></li>`:`<li>${btnCmd(x,'🪪 Kiểm thẻ','tv_card',{task:t.id},'full')}</li>`;
  let fix='';
  if(card?.card==='expired')fix=st.renewed?tag(x,'✓ Đã gia hạn thẻ','green'):btnCmd(x,`🪪 Gia hạn thẻ (${cc(x).card_fee||5} xu)`,'tv_renew',{task:t.id},'');
  if(card?.card==='debt')fix=st.settled?tag(x,'✓ Đã thu nợ cũ','green'):amountBox(x,`owe-${t.id}`,card.owe,{min:0,max:card.owe,label:'Thu nợ phí cũ',send:'💵 Thu nợ',cmd:'tv_settle',payload:{task:t.id},field:'amount'});
  const lend=x.cmd('📗 Cho mượn, đóng dấu hạn trả','tv_lend',{task:t.id},'tv-btn primary',!(st.looked&&st.carded)||i.status==='out');
  const opts=Object.entries(offers).map(([k,l])=>x.cmd(x.esc(l),'tv_offer',{task:t.id,how:k},'tv-opt',!st.looked)).join('');
  return `<section class="card tv-desk"><h4>📖 “${x.esc(i.title||'')}”</h4><ul class="tv-list">${look}${cardRow}</ul>${fix?`<div class="tv-row">${fix}</div>`:''}</section>
    <section class="card tv-decide"><h4>🔖 Quyết ở quầy</h4><div class="tv-row">${lend}</div>${pane(x,`offer-${t.id}`,'🙏 Hoặc giúp cách khác',`<div class="tv-opts tv-offers">${opts}</div>`,!!st.looked&&(i.status!=='avail'||card?.card==='limit'))}</section>`;
}
function borrowSteps(t,x){
  const st=t.st||{},rows=[];
  rows.push({ok:st.looked||null,label:'Tra máy: ký hiệu, còn sách không',go:{cmd:'tv_lookup',payload:{task:t.id},label:'🔎 Tra máy'}});
  rows.push({ok:st.carded||null,label:'Kiểm thẻ bạn đọc',go:{cmd:'tv_card',payload:{task:t.id},label:'🪪 Kiểm thẻ'}});
  if(st.looked&&st.carded)rows.push({ok:null,label:'Cho mượn hoặc giúp cách khác',go:{sel:'.tv-decide',label:'🔖 Quyết ở quầy'},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ the desk: returns */
function returnPanel(t,x){
  const st=t.st||{},i=t.info||{},fee=t.fee||{},dmg=cc(x).damage||{},f=t.fees;
  const list=[
    t.damage!=null?row(x,t.damage==='none'?'📗':'📕','Tình trạng sách',(dmg[t.damage]||{}).label):`<li>${btnCmd(x,'📖 Kiểm sách','tv_inspect',{task:t.id},'full')}</li>`,
    t.late!=null?row(x,'📅','Dấu hạn trả',t.late?`Trễ ${t.late} ngày`:'Đúng hạn'):`<li>${btnCmd(x,'📅 Xem dấu hạn','tv_date',{task:t.id},'full')}</li>`,
    t.excuse!=null?row(x,'💬','Lý do',t.excuse):`<li>${btnCmd(x,'💬 Hỏi lý do','tv_why',{task:t.id},'full')}</li>`].join('');
  let money='';
  if(f){
    const due=f.late+f.damage;
    const parts=`<ul class="tv-fees"><li>Trễ hạn: ${t.late} ngày × ${cc(x).fine_day||1} xu${t.late*(cc(x).fine_day||1)>f.late?` (tối đa ${cc(x).fine_cap||15})`:''}<b>${f.late} xu</b></li>
      <li>${f.price!=null?'Làm mất: giá bìa':'Hỏng sách'}<b>${f.damage} xu</b></li></ul><p class="small muted">${x.esc(cc(x).excuse_rule||'')}</p>`;
    if(!due)money=`<p class="small">${tag(x,'Không có phí','green')}</p>`;
    else if(fee.state&&fee.state!=='open')money=`<p>${tag(x,{paid:`✓ Đã thu ${fee.paid} xu`,debt:'📒 Ghi sổ nợ',waived:'🤝 Đã miễn',none:'Không phí'}[fee.state]||'',fee.state==='paid'?'green':'amber')}</p>`;
    else{
      const tone=(x.ui.tone??={})[t.id]||'soft';
      const tones=`<div class="tv-row tv-tones">${x.button('🙂 Nói nhẹ','car:tone',{task:t.id,tone:'soft'},tone==='soft'?'small tv-on':'small ghost')}${x.button('📋 Nói theo nội quy','car:tone',{task:t.id,tone:'strict'},tone==='strict'?'small tv-on':'small ghost')}</div>`;
      const ctr=fee.counter!=null?`<p class="tv-counter">🗣️ Bạn đọc trả <b>${x.fmt(fee.counter)} xu</b> ${x.cmd(`Chốt ${x.fmt(fee.counter)} xu`,'tv_fine',{task:t.id,amount:fee.counter,tone},'small primary')}</p>`:'';
      money=`${parts}${tones}${ctr}${amountBox(x,`fee-${t.id}`,fee.counter??due,{min:0,max:300,label:'Phí bạn đề xuất',send:'🧾 Báo phí',cmd:'tv_fine',payload:{task:t.id,tone},field:'amount'})}
        <div class="tv-row tv-feeways">${btnCmd(x,'📒 Ghi sổ nợ','tv_fee',{task:t.id,how:'later'},'small ghost')}${btnCmd(x,'🤝 Miễn phí','tv_fee',{task:t.id,how:'waive'},'small ghost')}${btnCmd(x,'👩‍🏫 Nhờ cô Nguyệt','tv_fee',{task:t.id,how:'boss'},'small ghost')}</div>`;
    }
  }
  const needFix=t.damage&&!['none','lost'].includes(t.damage);
  const fixes=needFix?(st.repair?`<p>${tag(x,`✓ ${(cc(x).repair||{})[st.repair]||''}`,'green')}</p>`
    :`<div class="tv-opts tv-repairs">${Object.entries(cc(x).repair||{}).map(([k,l])=>x.cmd(x.esc(l),'tv_repair',{task:t.id,how:k},'tv-opt')).join('')}</div>`):'';
  return `<section class="card tv-desk"><h4>📚 Trả “${x.esc(i.title||'')}”</h4><ul class="tv-list">${list}</ul></section>
    ${f?`<section class="card tv-fee"><h4>💰 Phí theo nội quy</h4>${money}</section>`:''}
    ${needFix?`<section class="card tv-repair"><h4>🛠️ Sửa sách</h4>${fixes}</section>`:''}`;
}
function returnSteps(t,x){
  const st=t.st||{},rows=[],f=t.fees,fee=t.fee||{};
  rows.push({ok:t.damage!=null||null,label:'Kiểm sách',go:{cmd:'tv_inspect',payload:{task:t.id},label:'📖 Kiểm sách'}});
  rows.push({ok:t.late!=null||null,label:'Xem dấu hạn trả',go:{cmd:'tv_date',payload:{task:t.id},label:'📅 Xem dấu hạn'}});
  if(t.late)rows.push({ok:t.excuse!=null||null,label:'Hỏi lý do trả trễ',go:{cmd:'tv_why',payload:{task:t.id},label:'💬 Hỏi lý do'}});
  if(f&&f.late+f.damage>0)rows.push({ok:fee.state&&fee.state!=='open'?true:null,label:'Tính phí theo nội quy',go:{sel:'.tv-fee .sk-amt',label:'💰 Đề xuất phí'},pulse:''});
  if(t.damage&&!['none','lost'].includes(t.damage))rows.push({ok:st.repair?true:null,label:'Sửa sách',go:{sel:'.tv-repairs',label:'🛠️ Chọn cách sửa'},pulse:''});
  return rows;
}

/* ------------------------------------------------------------ the desk: a recommendation */
function recPanel(t,x){
  const st=t.st||{},clues=t.clues||{};
  const q=(k,label)=>clues[k]?row(x,'💬',label,clues[k]):`<li>${btnCmd(x,`💬 ${label}`,'tv_q',{task:t.id,q:k},'full')}</li>`;
  const books=(t.cands||[]).map(b=>tile(x,'tv_rec',{task:t.id,book:b.id},`<span class="tile-emoji">📘</span><b>${x.esc(b.title)}</b><small>${x.esc(b.genre)} · ${b.easy?'nhẹ nhàng, mỏng':'sâu, dày'}</small>`,st.pick===b.id?'selected':'')).join('');
  return `<section class="card tv-desk"><h4>💡 Hỏi gu trước đã</h4><ul class="tv-list">${q('last','Hỏi cuốn gần nhất thích')}${q('mood','Hỏi đang muốn đọc gì')}</ul></section>
    <section class="card tv-recs"><h4>📚 Bốn cuốn trên xe gợi ý</h4><div class="tile-grid tv-cands">${books}</div></section>`;
}
function recSteps(t,x){
  const clues=t.clues||{};
  return [{ok:clues.last?true:null,label:'Hỏi cuốn gần nhất thích',go:{cmd:'tv_q',payload:{task:t.id,q:'last'},label:'💬 Hỏi cuốn gần nhất thích'}},
    {ok:clues.mood?true:null,label:'Hỏi đang muốn đọc gì',go:{cmd:'tv_q',payload:{task:t.id,q:'mood'},label:'💬 Hỏi đang muốn đọc gì'}},
    {ok:null,label:'Chọn cuốn hợp gu',go:{sel:'.tv-cands',label:'📚 Chọn một cuốn'},pulse:''}];
}

/* ------------------------------------------------------------ cataloguing */
function bookDone(t,b){const st=t.st||{};return !!(st.weed?.[b]||(st.cls?.[b]&&st.mark?.[b]));}
function catalogPanel(t,x){
  const st=t.st||{},classes=cc(x).classes||[],weed=cc(x).weed||{},marks=t.needs?.marks||{};
  const first=(t.books||[]).find(b=>!bookDone(t,b.id));
  const cards=(t.books||[]).map((b,i)=>{
    const w=st.weed?.[b.id],cls=st.cls?.[b.id],mk=st.mark?.[b.id];
    const sum=`<span class="tv-book-sum"><b>${i+1}. ${x.esc(b.title)}</b><small>${x.esc(b.author)}${w?` · 🗑️ ${x.esc(weed[w]||'')}`:cls?` · ${x.esc(cls)}${mk?` ${x.esc(mk)}`:''}`:''}</small></span>${bookDone(t,b.id)?'<i class="tv-ok" aria-hidden="true">✓</i>':''}`;
    const body=w?`<p class="small">${tag(x,`🗑️ Để riêng: ${weed[w]||''}`,'amber')}</p>${x.cmd('↩️ Giữ lại cuốn này','tv_weed',{task:t.id,book:b.id,reason:''},'tv-btn small ghost')}`
      :`<p class="small muted">${x.esc(b.hint)}</p><h5>Lớp</h5><div class="tv-classes">${classes.map(([k,l])=>`<button type="button" class="tv-chip ${cls===k?'on':''}" data-command="tv_class" data-payload="${x.esc(JSON.stringify({task:t.id,book:b.id,cls:k}))}" title="${x.esc(l)}">${x.esc(k)}</button>`).join('')}</div>
        <h5>Ký hiệu tác giả</h5><div class="tv-marks">${(marks[b.id]||[]).map(m=>`<button type="button" class="tv-chip ${mk===m?'on':''}" data-command="tv_mark" data-payload="${x.esc(JSON.stringify({task:t.id,book:b.id,mark:m}))}">${x.esc(m)}</button>`).join('')}</div>
        ${pane(x,`weed-${t.id}-${b.id}`,'🗑️ Sách hỏng? Để riêng chờ thanh lý',`<div class="tv-opts">${Object.entries(weed).map(([k,l])=>x.cmd(x.esc(l),'tv_weed',{task:t.id,book:b.id,reason:k},'tv-opt')).join('')}</div>`,false,'tv-weed')}`;
    return pane(x,`book-${t.id}-${b.id}`,sum,body,first?first.id===b.id:false,`tv-book ${bookDone(t,b.id)?'done':''}`);
  }).join('');
  const legend=pane(x,'classes',`📇 Bảng phân lớp · mẹo xếp giá`,`<ul class="tv-legend">${classes.map(([k,l])=>`<li><b>${x.esc(k)}</b> ${x.esc(l)}</li>`).join('')}</ul><ul class="tv-tips">${(cc(x).class_tips||[]).map(s=>`<li>${x.esc(s)}</li>`).join('')}</ul>`,false,'tv-legendpane');
  return `<section class="card tv-cat"><h4>🏷️ Xe sách chờ biên mục</h4>${legend}<div class="tv-books">${cards}</div></section>`;
}
function catalogSteps(t,x){
  return (t.books||[]).map(b=>({ok:bookDone(t,b.id)||null,label:b.title,go:{sel:`.tv-book .sk-pane-sum`,label:`🏷️ Biên mục: ${x.esc(b.title)}`},pulse:''}));
}

/* ------------------------------------------------------------ the reading room */
function roomPanel(t,x){
  const st=t.st||{},done=st.done||{},lab=cc(x).answers||{};
  const cards=(t.offenders||[]).map(o=>{
    const d=done[o.id],again=d&&d.res==='blowup';
    const status=d&&!again?tag(x,{calm:'✓ Êm rồi',sulk:'✓ Lầm bầm rồi thôi',ignored:'🙈 Để kệ'}[d.res]||'✓',d.res==='ignored'?'amber':'green'):again?tag(x,'⚠️ Cãi lại: nói thêm một lần','danger'):'';
    const opts=d&&!again?'':`<div class="tv-opts tv-answers">${['soft','rule','offer','out','ignore'].map(k=>x.cmd(k==='offer'?`🙏 ${x.esc(o.offer)}`:x.esc(lab[k]||k),'tv_deal',{task:t.id,who:o.id,how:k},`tv-opt ${k==='ignore'?'ghost':''}`)).join('')}</div>`;
    return `<article class="tv-off ${d&&!again?'done':''}"><div class="tv-off-head"><span aria-hidden="true">${x.esc(o.emoji)}</span><div><b>${x.esc(o.title)}</b><small>${x.esc(o.text)}</small></div></div>${status}${opts}</article>`;
  }).join('');
  return `<section class="card tv-room"><h4>🤫 Phòng đọc</h4><div class="tv-quiet"><small>Độ yên tĩnh</small>${meter(st.quiet??100,100,(st.quiet??100)<50?'bad':'')}</div>${cards}</section>`;
}
function roomSteps(t,x){
  const done=t.st?.done||{};
  return (t.offenders||[]).map(o=>({ok:done[o.id]&&done[o.id].res!=='blowup'?true:null,label:o.title,go:{sel:'.tv-answers',label:`${x.esc(o.emoji)} ${x.esc(o.title)}`},pulse:''}));
}

/* ------------------------------------------------------------ the archive */
function trainCard(t,x){
  const qs=cc(x).training||[],ans=(x.ui.train??=[]);
  const rows=qs.map((q,i)=>`<li><b>${i+1}. ${x.esc(q.q)}</b><div class="tv-opts">${q.options.map(o=>`<button type="button" class="tv-opt ${ans[i]===o.id?'tv-on':''}" data-action="car:train" data-i="${i}" data-o="${x.esc(o.id)}">${x.esc(o.label)}</button>`).join('')}</div></li>`).join('');
  const ready=qs.length&&qs.every((_,i)=>ans[i]);
  return `<section class="card tv-train"><h4>👩‍🏫 Tập huấn nghiệp vụ lưu trữ</h4><p class="small">Cô Nguyệt: “Trước khi cầm chìa khóa kho, trả lời giúp cô mấy câu.”</p><ol class="tv-quiz">${rows}</ol>
    <button type="button" class="btn primary full" data-action="car:trainSend"${ready?'':' disabled'}>✅ Nộp bài tập huấn</button></section>`;
}
function archivePanel(t,x){
  const st=t.st||{},n=t.needs||{},docs=cc(x).docs||{},dec=cc(x).decisions||{},seen=st.seen||[];
  const checks=[
    seen.includes('id')?row(x,'🪪','Giấy tờ mang theo',(n.docs||[]).map(k=>docs[k]||k).join(', ')||'Không mang giấy tờ gì'):`<li>${btnCmd(x,'🪪 Xem giấy tờ','tv_see',{task:t.id,what:'id'},'full')}</li>`,
    seen.includes('form')?row(x,'📝','Phiếu yêu cầu','Đã điền, ký tên'):`<li>${btnCmd(x,'📝 Đưa phiếu yêu cầu','tv_see',{task:t.id,what:'form'},'full')}</li>`,
    t.index?row(x,'📇','Mục lục',`${t.index.label} · ${(n.boxes||[])[t.index.box]||''}`):`<li>${btnCmd(x,'📇 Tra mục lục','tv_see',{task:t.id,what:'index'},'full')}</li>`].join('');
  const head=`<section class="card tv-arc"><h4>🗂️ “${x.esc(n.record||'')}”</h4><p class="small muted">Mục đích: ${x.esc(n.purpose||'')}</p><ul class="tv-list">${checks}</ul></section>`;
  if(!data(x).trained)return head+trainCard(t,x);
  if(!st.decision){
    const ready=seen.includes('id')&&seen.includes('index');
    return head+`<section class="card tv-decide"><h4>⚖️ Quyết</h4><div class="tv-opts tv-decisions">${Object.entries(dec).map(([k,l])=>x.cmd(x.esc(l),'tv_decide',{task:t.id,choice:k},'tv-opt',!ready)).join('')}</div>${ready?'':'<p class="small muted">Xem giấy tờ và tra mục lục trước khi quyết.</p>'}</section>`;
  }
  const gear=['gang','khau_trang'].map(k=>(st.gear||[]).includes(k)?tag(x,k==='gang'?'✓ Găng tay vải':'✓ Khẩu trang','green'):btnCmd(x,k==='gang'?'🧤 Găng tay vải':'😷 Khẩu trang','tv_gear',{task:t.id,item:k},'small')).join('');
  const boxes=(n.boxes||[]).map((b,i)=>x.cmd(`📦 ${x.esc(b)}`,'tv_box',{task:t.id,box:i},`tv-opt ${st.box===i?'tv-on':''}`,st.found)).join('');
  const search=t.lost?`<section class="card tv-search"><h4>🔍 Không thấy hồ sơ</h4><div class="tv-opts tv-searches">${Object.entries(cc(x).search||{}).map(([k,l])=>x.cmd(x.esc(l),'tv_search',{task:t.id,where:k},'tv-opt',(st.search||[]).includes(k))).join('')}</div></section>`:'';
  const copy=st.found?`<section class="card tv-copy"><h4>🖨️ Cấp cho người xin</h4>${st.copy?`<p>${tag(x,`✓ ${(cc(x).copy||{})[st.copy]||''}`,st.copy==='copy'?'green':'amber')}</p>`
    :`<div class="tv-opts tv-copies">${Object.entries(cc(x).copy||{}).map(([k,l])=>x.cmd(x.esc(l),'tv_copy',{task:t.id,how:k},'tv-opt')).join('')}</div>`}
    <div class="tv-row">${st.logged?tag(x,'✓ Đã ghi sổ khai thác','green'):btnCmd(x,'📒 Ghi sổ khai thác','tv_log',{task:t.id},'small')}</div></section>`:'';
  return head+`<section class="card tv-fetch"><h4>📦 Vào kho</h4><div class="tv-row">${gear}</div><div class="tv-opts tv-boxes">${boxes}</div></section>${search}${copy}`;
}
function archiveSteps(t,x){
  const st=t.st||{},seen=st.seen||[],rows=[];
  rows.push({ok:seen.includes('id')||null,label:'Xem giấy tờ',go:{cmd:'tv_see',payload:{task:t.id,what:'id'},label:'🪪 Xem giấy tờ'}});
  rows.push({ok:seen.includes('form')||null,label:'Đưa phiếu yêu cầu',go:{cmd:'tv_see',payload:{task:t.id,what:'form'},label:'📝 Đưa phiếu yêu cầu'}});
  rows.push({ok:seen.includes('index')||null,label:'Tra mục lục',go:{cmd:'tv_see',payload:{task:t.id,what:'index'},label:'📇 Tra mục lục'}});
  if(!data(x).trained){rows.push({ok:null,label:'Tập huấn nghiệp vụ lưu trữ',go:{sel:'.tv-train',label:'👩‍🏫 Làm bài tập huấn'},pulse:''});return rows;}
  rows.push({ok:st.decision?true:null,label:'Quyết cách xử lý',go:{sel:'.tv-decisions',label:'⚖️ Quyết'},pulse:''});
  if(!['give','approve'].includes(st.decision))return rows;
  for(const k of ['gang','khau_trang'])rows.push({ok:(st.gear||[]).includes(k)||null,label:k==='gang'?'Đeo găng tay vải':'Đeo khẩu trang',go:{cmd:'tv_gear',payload:{task:t.id,item:k},label:k==='gang'?'🧤 Găng tay vải':'😷 Khẩu trang'}});
  rows.push({ok:st.found||null,label:'Lấy đúng hộp hồ sơ',go:{sel:t.lost?'.tv-searches':'.tv-boxes',label:t.lost?'🔍 Tìm hồ sơ':'📦 Chọn hộp'},pulse:''});
  if(st.found){rows.push({ok:st.copy?true:null,label:'Cấp bản sao',go:{sel:'.tv-copies',label:'🖨️ Cấp cho người xin'},pulse:''});
    rows.push({ok:st.logged||null,label:'Ghi sổ khai thác',go:{cmd:'tv_log',payload:{task:t.id},label:'📒 Ghi sổ khai thác'}});}
  return rows;
}

/* ------------------------------------------------------------ the guide */
function stepsOf(t,x){
  if(t.kind==='open')return openSteps(t,x);
  if(t.kind==='desk')return ({borrow:borrowSteps,return:returnSteps,recommend:recSteps}[t.needs?.mode]||borrowSteps)(t,x);
  return ({catalog:catalogSteps,room:roomSteps,archive:archiveSteps}[t.kind])(t,x);
}
function finalOf(t,x,steps){
  const st=t.st||{};
  if(t.kind==='open')return {label:'📚 MỞ CỬA THƯ VIỆN',go:finalGo(steps,'tv_openup',{task:t.id}),ready:!!st.room,why:'mở phòng đọc'};
  if(t.kind==='catalog')return {label:'🏷️ DÁN NHÃN, XẾP LÊN KỆ',go:finalGo(steps,'tv_catdone',{task:t.id}),ready:(t.books||[]).every(b=>bookDone(t,b.id)),why:'biên mục đủ các cuốn'};
  if(t.kind==='room')return {label:'🤫 XONG VÒNG PHÒNG ĐỌC',go:finalGo(steps,'tv_rounddone',{task:t.id}),ready:steps.every(s=>s.ok===true),why:'xử lý hết chuyện trong phòng'};
  if(t.kind==='archive')return st.found&&st.copy?{label:'🗂️ BÀN GIAO HỒ SƠ',go:finalGo(steps,'tv_handover',{task:t.id}),ready:true}:null;
  if(t.needs?.mode==='return'){const f=t.fees,paid=!f||!(f.late+f.damage)||(t.fee&&t.fee.state!=='open');
    return {label:'📚 CẤT SÁCH LÊN KỆ',go:finalGo(steps,'tv_shelve',{task:t.id}),ready:!!(t.damage!=null&&t.late!=null&&paid),why:'kiểm sách, tính phí'};}
  return null;
}
function guide(t,x){
  const d=data(x);
  if(d.desk?.ev)return {steps:[{ok:null,label:'Quyết chuyện bất ngờ',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null};
  if(!d.intro)return {steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'tv_intro',payload:{},label:'📚 Vào việc thôi!'}}],final:null};
  if(t.ask?.state==='on')return {steps:[{ok:null,label:'Có người nhờ việc',go:{sel:'.tv-ask',label:'👉 Trả lời người nhờ'},pulse:''}],final:null};
  if(!t.known)return {steps:[{ok:null,label:'Nghe bạn đọc nói',go:{cmd:'ask',payload:{task:t.id},label:'👂 Nghe bạn đọc nói'}}],final:null,pulse:'.sk-ask'};
  const steps=stepsOf(t,x);
  return {steps,final:finalOf(t,x,steps)};
}
const hintFor=(g,x)=>nextHint(x,g.steps,{final:g.final&&g.final.ready!==false&&g.final.go?{label:g.final.label.replace(/^[^\p{L}]+/u,''),go:g.final.go}:null,pulse:g.pulse});

function panelOf(t,x){
  if(t.kind==='open')return openPanel(t,x);
  if(t.kind==='desk')return ({borrow:borrowPanel,return:returnPanel,recommend:recPanel}[t.needs?.mode]||borrowPanel)(t,x);
  return ({catalog:catalogPanel,room:roomPanel,archive:archivePanel}[t.kind])(t,x);
}
function idleStats(x){
  const td=data(x).today||{};
  return `<section class="card tv-today"><h4>📊 Hôm nay</h4><ul class="kv"><li><span>Cho mượn</span><b>${td.lent||0}</b></li><li><span>Nhận trả</span><b>${td.returned||0}</b></li>
    <li><span>Biên mục</span><b>${td.shelved||0}</b></li><li><span>Hồ sơ</span><b>${td.records||0}</b></li><li><span>Phí đã thu</span><b>${x.fmt(td.fines||0)} xu</b></li></ul></section>`;
}

export default {
  id:'library',
  css:true,
  next(t,x){
    try{const g=guide(t,x),n=pending(g.steps);if(n)return x.esc(stepLine(n));if(g.final)return x.esc(g.final.label.replace(/^[^\p{L}]+/u,''));}catch{/* fixed lines below */}
    return t.kind==='open'?'Xem ẩm kế, soi bẫy, mở phòng đọc':!t.known?'Nghe bạn đọc nói':'Làm theo nội quy';
  },
  job(t,x){
    const g=guide(t,x),d=data(x),hint=hintFor(g,x);
    const top=`${introCard(x,'tv_intro','📚')}${deskCard(x,'tv_desk','Chuyện ở thư viện')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro)return `<div class="career-job sk tv">${hint}${top}${bottom(x,g)}</div>`;
    if(t.ask?.state==='on')return `<div class="career-job sk tv">${hint}${top}${ticket(t,x)}${askBox(t,x)}${bottom(x,g)}</div>`;
    if(!t.known)return `<div class="career-job sk tv">${hint}${top}${dayBar(x)}${ticket(t,x)}${bottom(x,g)}</div>`;
    const head=t.kind==='open'?dayBar(x):`${ticket(t,x)}${dayBar(x)}`;
    const side=stepRows(x,g.steps,t.kind==='open'?'Buổi sáng':'Việc cần làm',{chip:true});
    return `<div class="career-job sk tv">${hint}${top}${head}<div class="workbench"><section class="wb-main">${panelOf(t,x)}</section><aside class="wb-side">${side}</aside></div>${bottom(x,g)}</div>`;
  },
  idle(x){
    const d=data(x),top=`${introCard(x,'tv_intro','📚')}${deskCard(x,'tv_desk','Chuyện ở thư viện')}`;
    if(d.desk?.ev||!d.intro||x.ui.intro){const g=d.desk?.ev?{steps:[{ok:null,label:'Quyết chuyện bất ngờ',go:{sel:'.sk-opts',label:'👉 Chọn cách xử lý'}}],final:null}:{steps:[{ok:null,label:'Đọc giới thiệu nghề',go:{cmd:'tv_intro',payload:{},label:'📚 Vào việc thôi!'}}],final:null};
      return `<div class="career-job sk tv">${hintFor(g,x)}${top}${bottom(x,g)}</div>`;}
    return `<div class="career-job sk tv">${top}${dayBar(x)}${idleStats(x)}${debtBook(x,d.debts,'tv_chase')}</div>`;
  },
  input(el,x){return kitInput(el,x);},
  tick(root){keepBarAboveFooter(root);},
  summary(sum,x){
    if(!sum||sum.jobs==null)return '';
    const owe=(data(x).debts||[]).filter(d=>d.state==='open'),due=owe.reduce((n,d)=>n+(Number(d.owed)||0)-(Number(d.paid)||0),0);
    const plan=[...stockLines(x),owe.length?`📒 Còn ${owe.length} người nợ phí · ${x.fmt(due)} xu`:'',
      typeof sum.note==='string'&&sum.note?`<span aria-hidden="true">🌡️</span> ${x.esc(sum.note)}`:''];
    const rows=[['Việc đã làm',sum.jobs],['Cho mượn',sum.lent],['Biên mục (cuốn)',sum.shelved],['Lượt hồ sơ',sum.records],['Phí đã thu (xu)',sum.fines],['Miễn giảm (xu)',sum.waived],['Thu quá nội quy (xu)',sum.overcharged]];
    return planBox(x,{lines:plan,go:['📦 Mở kho vật tư','inventory'],more:[`📚 Hôm nay · ${sum.jobs} việc`,figures(x,rows,Array.isArray(sum.lines)?sum.lines:[])]});
  },
  actions:{...kitActions,
    async tone(d,el,x){(x.ui.tone??={})[d.task]=d.tone;x.render();},
    async train(d,el,x){(x.ui.train??=[])[Number(d.i)]=d.o;x.render();},
    async trainSend(d,el,x){const n=(x.cc?.training||[]).length,a=Array.from({length:n},(_,i)=>(x.ui.train||[])[i]||'');
      const r=await x.send('tv_train',{answers:a});if(r&&r.correct===false)x.ui.train=[];x.render();},
  },
  dock:[['inventory','box','Kho vật tư','Nhãn gáy, băng giấy, găng tay…']],
};
