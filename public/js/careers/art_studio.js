const NAMES={layout:'Bố cục',palette:'Bảng màu',medium:'Chất liệu'};
const PALETTE={warm:['#f9df99','#bd6748','#704934'],cool:['#d2eeee','#629db1','#326972'],muted:['#e6dbca','#a99480','#655d58'],bright:['#ffe493','#f08585','#5e93c3']};
const data=x=>x.room.data||{};
function painting(t,x){
 const p=t.plan||{},colors=PALETTE[p.palette]||PALETTE.muted,done=new Set(t.painted||[]),layout=p.layout||'landscape';
 const shape=layout==='portrait'?'<ellipse cx="160" cy="104" rx="33" ry="40"/><path d="M107 192 Q105 145 160 145 Q215 145 213 192Z"/>':layout==='poster'?'<path d="M70 174L160 75L250 174Z"/><circle cx="160" cy="90" r="20"/>':'<path d="M0 188L68 90L145 165L226 100L320 188Z"/>';
 return `<figure class="art-preview"><svg viewBox="0 0 320 230" role="img" aria-label="Bản xem trước các lớp tranh"><rect width="320" height="230" fill="${done.has('background')?colors[0]:'#faf7f1'}"/>${done.has('wash')?`<path d="M0 120 Q80 85 170 126 T320 110V230H0Z" fill="${colors[1]}" opacity=".35"/>`:''}${done.has('subject')?`<g fill="${colors[1]}" stroke="${colors[2]}" stroke-width="${p.medium==='ink'?4:1}">${shape}</g>`:''}${done.has('detail')?`<g stroke="${colors[2]}" stroke-width="3"><path d="M28 207H290M50 197H85M233 201H271"/></g>`:''}${layout==='series'?'<path d="M106 0V230M213 0V230" stroke="#faf7f1" stroke-width="7"/>':''}${done.has('lettering')?`<text x="160" y="39" text-anchor="middle" font-size="17" fill="${colors[2]}">MÀU NẮNG</text>`:''}${done.has('seal')?'<path d="M15 15H303V214" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="4"/>':''}</svg><figcaption>${x.esc(t.needs?.subject||'Bàn vẽ đang chờ một câu chuyện')}</figcaption></figure>`;
}
function journey(x){const d=data(x),s=d.stats||{};
 return `<details class="art-journey"><summary>Hành trình triển lãm · ${s.good||0} tranh đạt · ${s.active_days||0} ngày làm việc</summary><p>Ngày hoàn thành ít nhất hai tranh mới tính vào hành trình. Mốc nghề không thưởng thêm tiền.</p><ul>${(d.milestones||[]).map(m=>`<li>${m.done?'✓':'○'} <b>${x.esc(m.name)}</b> — ngày nghề ${m.day}, ${m.good} tranh đạt, ${m.active_days} ngày làm việc.</li>`).join('')}</ul><h4>Sổ tranh gần đây</h4><ul>${(d.portfolio||[]).slice().reverse().map(p=>`<li>Ngày ${p.day} · ${x.esc(p.name)} ${p.good?'✓':''}</li>`).join('')}</ul></details>`;
}
function job(t,x){
 if(!t.known)return `<div class="career-job art-studio"><h3>${x.esc(t.title)}</h3><p>${x.esc(t.opening)}</p>${x.cmd('Đọc phiếu đặt tranh','ask',{task:t.id},'primary')}${journey(x)}</div>`;
 const n=t.needs,p=t.plan||{},stage=t.stage;let body='';
 if(stage==='plan')body=Object.entries(NAMES).map(([field,label])=>`<fieldset><legend>${label}</legend><div class="art-options">${Object.entries(x.cc.options[field]).map(([v,l])=>x.cmd(`${p[field]===v?'✓ ':''}${x.esc(l)}`,'art_plan',{task:t.id,field,value:v},p[field]===v?'primary':'ghost')).join('')}</div></fieldset>`).join('')+x.cmd('Bắt đầu dựng tranh','art_begin',{task:t.id},'primary',Object.keys(p).length!==3);
 if(stage==='paint')body=`<p>${x.esc(n.rule)}</p><div class="art-options">${n.layers.map(l=>x.cmd(`${t.painted.includes(l.id)?'✓ ':''}${x.esc(l.label)}`,'art_layer',{task:t.id,layer:l.id},'ghost',t.painted.includes(l.id))).join('')}</div>`;
 if(stage==='proof'){
  const checks=(x.ui.artChecks??={})[t.id]||[];
  body=`<h4>Kiểm trước khi giao</h4><div class="art-options">${[['brief','Đối chiếu yêu cầu'],['surface','Kiểm bề mặt và mép tranh'],['signature','Ký tên và ghi nguồn mẫu']].map(([id,label])=>x.button(`${checks.includes(id)?'✓ ':''}${label}`,'car:artCheck',{task:t.id,key:id},checks.includes(id)?'primary':'ghost')).join('')}</div>${x.cmd('Chốt kiểm tranh','art_proof',{task:t.id,checks},'primary',checks.length!==3)}`;
 }
 if(stage==='deliver')body=`<h4>Giao theo phiếu nhận</h4><div class="art-options">${x.cc.recipients.map(recipient=>x.cmd(x.esc(recipient),'art_deliver',{task:t.id,recipient},'ghost')).join('')}</div>`;
 return `<div class="career-job art-studio"><header><span class="eyebrow">XƯỞNG VẼ MÀU NẮNG</span><h3>${x.esc(t.title)}</h3><p>${x.esc(n.brief)}</p></header><div class="art-ticket"><b>Người nhận: ${x.esc(n.recipient)}</b><p>${x.esc(n.layout)} · ${x.esc(n.palette)} · ${x.esc(n.medium)}</p><small>Công tối đa ${n.gross} xu · vật tư ${n.cost} xu. Làm khác yêu cầu giảm tiền công.</small></div>${painting(t,x)}<section class="art-work" aria-label="Bước làm tranh">${body}</section>${journey(x)}</div>`;
}
export default {id:'art_studio',css:true,job,idle:x=>`<div class="career-job art-studio"><h3>Xưởng vẽ Màu Nắng</h3><p>${x.esc(x.cc.guide)}</p>${journey(x)}</div>`,
 next:t=>!t.known?'Đọc phiếu đặt tranh':({plan:'Chọn bố cục, màu và chất liệu',paint:'Vẽ lớp tiếp theo',proof:'Kiểm và ký tranh',deliver:'Giao đúng người nhận'})[t.stage]||'Tranh đã giao',
 actions:{artCheck(d,el,x){const by=x.ui.artChecks??={},s=new Set(by[d.task]||[]);if(s.has(d.key))s.delete(d.key);else s.add(d.key);by[d.task]=[...s];x.render();}},
 summary:(s,x)=>`<p>${x.esc(s.note||'')}</p>`,dock:[]};
