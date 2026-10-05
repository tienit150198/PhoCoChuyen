/** Read-only queue presentation. Only server-confirmed customers speak. */
const seedOf=value=>[...String(value)].reduce((n,c)=>(n*31+c.charCodeAt(0))%1000000,0);
/** Current customers and completed counter receipts are separate; neither creates a sale. */
export function counterActivity(st){
  const b=st.business||{},r=st.run&&!st.run.x?st.run:null;
  const closed=!!st.closed||!!b.paused||['paused','out_of_stock','no_funds'].includes(b.status)||(b.status==='no_staff'&&!r)||!!r?.out;
  const people=r?.crowd?.length?r.crowd:r?.cust?[{...r.cust,ticket:'current'},...(r.queue||[]).map((look,i)=>({look,ticket:`waiting:${i}`,name:'Khách đang chờ'}))]:[];
  const current=people.map((p,i)=>({id:`owner:${p.ticket}`,seed:p.look??seedOf(p.ticket),name:p.name||'Khách',state:i===0&&!closed?'serving':'waiting'}));
  for(const o of b.visitor_orders||[])if(o.status==='queued')current.push({id:`visitor:${o.id}`,seed:seedOf(o.id),name:o.buyer?.name||'Khách người chơi',state:o.staffed&&!closed?'serving':'waiting'});
  current.splice(8);
  // Receipt `name` is the employee who served the order; it does not identify the buyer.
  const slots=8-current.length,now=Number(b.server_now),completed=closed||!slots||!Number.isFinite(now)?[]:(b.recent||[]).filter(e=>e.channel==='counter'&&Number.isFinite(Number(e.at))&&now-Number(e.at)>=0&&now-Number(e.at)<=90).slice(-slots).reverse().map(e=>({id:`sale:${e.id}`,seed:seedOf(e.id),name:'Khách',state:'completed',dish:e.dish}));
  return {current,completed,closed};
}

export function counterActivityHTML(st,esc){
  const {current,completed}=counterActivity(st);
  if(!current.length&&!completed.length)return '';
  const people=[...current,...completed];
  return `<section class="qy-counter-activity" data-qk="activity:${esc(st.id)}" aria-label="Hoạt động khách tại quầy"><p>${current.length?`<b>${current.length} khách đang tại quầy</b>`:''}${current.length&&completed.length?' · ':''}${completed.length?`${completed.length} lượt vừa mua xong`:''}</p><ol>${people.map(p=>`<li data-qk="activity:${esc(p.id)}" class="qy-activity-person ${p.state}"><span aria-hidden="true">${p.state==='completed'?'🛍️':p.state==='serving'?'🧾':'🧍'}</span><span><b>${esc(p.name)}</b><small>${p.state==='completed'?'Vừa mua xong':p.state==='serving'?'Đang phục vụ':'Đang chờ'}</small></span></li>`).join('')}</ol>${completed.length?'<small>Lượt mua đã ghi sổ trong 90 giây gần đây.</small>':''}</section>`;
}

export function ownerArrivalText(run,business){
  const seconds=Math.max(0,Math.ceil(Number(run?.next_at||0)-Number(business?.server_now||0)));
  if(seconds>3600)return 'Quầy đã mở. Giá trên menu đang cao nên khách ghé thưa hơn; bạn vẫn có thể rời quầy bất cứ lúc nào.';
  if(seconds>60)return `Khách tiếp theo dự kiến tới trong khoảng ${Math.ceil(seconds/60)} phút. Giá cao hơn thường khiến khách cân nhắc lâu hơn.`;
  if(seconds>0)return `Khách tiếp theo đang tới, dự kiến khoảng ${seconds} giây. Đơn sẽ hiện ngay tại đây.`;
  return 'Khách đang ghé. Đơn mới tiếp tục tới trong lúc bạn chuẩn bị món và tính tiền.';
}

export function ownerQueueHTML(run,esc){
  const people=(run?.crowd||[]).slice(0,8);
  if(!people.length)return '';
  const mood={angry:['😤','Đang giục lớn'],impatient:['😠','Sốt ruột'],calm:['🙂','Bình tĩnh']};
  const chips=people.map((p,i)=>{
    const [emoji,label]=mood[p.mood]||mood.calm;
    return `<li class="qy-queue-person ${esc(p.mood||'calm')}${i===0?' current':''}" data-qk="queue:${esc(p.ticket)}"><span aria-hidden="true">${emoji}</span><span><b>${esc(p.name)}</b><small>${i===0?'Đang phục vụ':p.temperament==='relaxed'?'Dễ tính':label==='Bình tĩnh'?'Khó tính':label}</small></span></li>`;
  }).join('');
  const voices=(run.voices||[]).slice(0,3).map(p=>`<p class="qy-queue-voice ${esc(p.mood)}" data-qk="voice:${esc(p.ticket)}"><b>${esc(p.name)}:</b> “${esc(p.speech)}”</p>`).join('');
  return `<section class="qy-owner-queue" aria-label="Khách đang chờ"><div class="qy-queue-heading"><b>${people.length===1?'Có khách tại quầy':`${people.length} khách tại quầy`}</b><span>${people.length>1?`${people.length-1} người chờ tới lượt`:'Người tiếp theo đang ghé'}</span></div><ol class="qy-queue-people">${chips}</ol><div class="qy-queue-voices" aria-live="polite" aria-atomic="false">${voices}</div></section>`;
}
