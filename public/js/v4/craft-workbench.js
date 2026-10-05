import {confirmPurchase} from './payment.js';
import {workpieceArt} from './craft-art.js';
import {RECIPES,PATHS,SIZES,pathFor,sampledPath,traceStart,tracePoint,traceKeyboard,newDraft,draftKey,reconcileDraft,saveDraft,stepComplete,nextStep,craftWork,submitCraft,distance} from './craft-gestures.js';
export {RECIPES,PATHS,newDraft,draftKey,restoreDraft,saveDraft,stepComplete,nextStep,craftWork,submitCraft} from './craft-gestures.js';

// Intent: a relaxed visit to a real craft table, with the object occupying most of the view.
// Linen, walnut, cutting-mat green and pink thread; subtle shadows, warm raised paper,
// inherited Be Vietnam Pro, 4px spacing. Tools and stitches replace generic progress cards.
const names={teddy:'Bạn gấu do mình may',tote:'Chiếc túi do mình may',pot:'Chiếc chậu do mình nặn',bracelet:'Vòng tay do mình xâu',card:'Tấm thiệp do mình làm'};
const labels={measure:'Đo vải',cut:'Cắt mẫu',sew:'May viền',stuff:'Nhồi bông',straps:'Gắn quai',decorate:'Hoàn thiện',shape:'Tạo dáng',glaze:'Phủ men',thread:'Luồn dây',beads:'Xâu hạt',fold:'Gấp thiệp'};
const tools={measure:['↔','Thước dây'],cut:['✂','Kéo cắt vải'],sew:['╱','Kim & chỉ'],stuff:['☁','Bông mềm'],straps:['∩','Hai quai túi'],decorate:['✿','Góc trang trí'],shape:['◒','Bàn tay nặn'],glaze:['▰','Cọ phủ men'],thread:['〰','Sợi dây'],beads:['●','Hạt gỗ'],fold:['▱','Nếp gấp']};
const instructions={measure:'Kéo hai đầu thước: ngang 32 cm, dọc 36 cm.',cut:'Giữ kéo ở chấm sáng, đi theo nét đứt quanh tấm vải.',sew:'Giữ kim ở chấm sáng, may dọc hai bên và đáy túi.',straps:'Kéo từng quai từ khay vào vị trí sáng trên miệng túi.',decorate:'Chạm lên sản phẩm để in dấu của riêng bạn.',shape:'Đưa tay theo đường sáng để tạo thành và đáy chậu.',glaze:'Đưa cọ theo từng hàng để phủ men lên chậu.',thread:'Kéo sợi dây theo đường sáng để chuẩn bị xâu hạt.',beads:'Chọn hạt trong khay, rồi chạm vào một vị trí trên dây.',fold:'Miết dọc đường giữa để gấp tấm thiệp.'};
const markFor=p=>({plain:'♡',flower:'✿',stars:'✦',waves:'≈'}[p]||'✿');
const btn=(text,action,extra='')=>`<button type="button" data-craft="${action}" ${extra}>${text}</button>`;
const poly=p=>p.map(x=>x.join(',')).join(' ');
const beadSlots=Array.from({length:8},(_,i)=>{const a=i*Math.PI/4;return [280+104*Math.cos(a),256+88*Math.sin(a)];});
const stuffSlots=[[280,162],[245,240],[315,240],[280,287]],faceSlots=[[261,176],[299,176],[280,192],[280,224]],faceNames=['Mắt trái','Mắt phải','Mũi','Nơ'];


export async function openCraftWorkbench(env,selection={}){
 if(document.querySelector('.craft-workbench'))return false;
 const catalog=env.api.content.journey.outings,account=env.api.account?.username;
 const selected=newDraft(selection),key=draftKey(account,selected.kind);let storage=null,raw=null;
 try{storage=window.localStorage;raw=key&&storage.getItem(key);}catch{}
 let d=reconcileDraft(raw,selection),drag=null,dragPoint=null,held=null,busy=false,saved=false,status='';
 let draftSaved=saveDraft(storage,key,d);
 const full=()=>env.api.state.journey.outings.crafts.length>=catalog.max_crafts;
 if(full()){await env.confirmAction('Kệ kỷ niệm đã đầy','Kệ đã đủ 24 món. Những món bạn đã làm vẫn được giữ trên kệ.','Đã hiểu');return false;}
 if(!document.querySelector('link[data-craft-style]')){const link=document.createElement('link');link.rel='stylesheet';link.href=new URL('../../css/craft-workbench.css',import.meta.url).href;link.dataset.craftStyle='';document.head.append(link);}
 const id=`craft-${Math.random().toString(36).slice(2,8)}`,dialog=document.createElement('dialog');dialog.className='craft-workbench';dialog.setAttribute('aria-labelledby',`${id}-title`);
 const opener=document.activeElement;
 dialog.innerHTML=`<div class="cw-shell"><header class="cw-head"><div><span class="cw-eyebrow">XƯỞNG NHỎ · TỰ TAY LÀM</span><h2 id="${id}-title">${names[d.kind]}</h2></div>${btn('×','close','class="cw-close" aria-label="Cất bản nháp và đóng xưởng"')}</header><nav class="cw-steps" aria-label="Các bước thủ công"></nav><section class="cw-instruction"><h3></h3><p></p></section><div class="cw-mat"><svg viewBox="0 0 560 440" class="cw-stage" tabindex="0" role="application" aria-label="Bàn thủ công tương tác" aria-describedby="${id}-help"><defs><pattern id="${id}-grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#f1edcd" stroke-width=".6" opacity=".2"/></pattern><pattern id="${id}-linen" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M0 1H5M1 0V5" stroke="#fff4df" stroke-width=".5" opacity=".35"/></pattern></defs><rect width="560" height="440" rx="14" fill="#617c6e"/><rect width="560" height="440" rx="14" fill="url(#${id}-grid)"/><g class="cw-art"></g></svg><span class="cw-mat-label">GÓC CỦA BẠN</span></div><div class="cw-tools"></div><p id="${id}-help" class="cw-help"></p><div class="cw-feedback" role="status" aria-live="polite"></div><footer class="cw-footer"><div class="cw-draft"></div><div class="cw-actions">${btn('Làm lại bước này','retry','class="cw-secondary"')}${btn('Tiếp theo →','next','class="cw-primary"')}</div></footer></div>`;
 document.body.append(dialog);
 const q=s=>dialog.querySelector(s),stage=q('.cw-stage');
 if(d.kind==='teddy'){stage.setAttribute('viewBox','140 65 280 350');q('.cw-mat-label').hidden=true;}
 const current=()=>RECIPES[d.kind][d.step];
 const persist=()=>{draftSaved=saveDraft(storage,key,d);};
 const color=()=>{const value=catalog.colors.find(c=>c.id===d.color)?.hex;return /^#[\da-f]{3,8}$/i.test(value||'')?value:'#eedcc4';};
 const trace=()=>{const s=current();return d.trace[s]??=traceStart(sampledPath(pathFor(d,s)));};
 function refresh(controls=false){
  const focused=document.activeElement,restoreFocus=controls&&q('.cw-tools').contains(focused),focusData=restoreFocus?{...focused.dataset}:null;
  const s=current(),ready=stepComplete(d),t=PATHS[s]?trace():null,path=PATHS[s]?sampledPath(pathFor(d,s)):null;
  let overlay='';
  if(s==='measure'){
   const base=d.kind==='teddy'?184:152,side=d.kind==='teddy'?402:429,x=base+d.measure[0]*8,y=110+d.measure[1]*8,[w,h]=SIZES[d.kind];
   overlay=`<path d="M${base} 91H${x}M${side} 110V${y}" stroke="#f5d98f" stroke-width="15"/><path d="M${base} 91H${base+w*8}M${side} 110V${110+h*8}" stroke="#645440" stroke-width="2" stroke-dasharray="2 14"/><circle cx="${x}" cy="91" r="16" fill="#fff1cb" stroke="#795b40" stroke-width="3"/><circle cx="${side}" cy="${y}" r="16" fill="#fff1cb" stroke="#795b40" stroke-width="3"/><text x="280" y="78" text-anchor="middle" fill="#fff8ec" font-size="12">${d.measure[0]} / ${w} cm</text><text x="${side-12}" y="270" fill="#fff8ec" font-size="12" transform="rotate(-90 ${side-12} 270)">${d.measure[1]} / ${h} cm</text>`;
  }else if(path){
   overlay=`<polyline points="${poly(pathFor(d,s))}" fill="none" stroke="#fff6cf" stroke-width="3" stroke-dasharray="7 7"/><polyline points="${poly(path.slice(0,t.count))}" fill="none" stroke="${s==='sew'?'#a84969':'#efd38a'}" stroke-width="${s==='glaze'?22:5}" stroke-linecap="round" stroke-linejoin="round"/>${!ready?`<circle cx="${path[t.count][0]}" cy="${path[t.count][1]}" r="15" fill="#fff4be" fill-opacity=".55" stroke="#fff4be" stroke-width="2"/><circle cx="${path[t.count][0]}" cy="${path[t.count][1]}" r="3" fill="#fff4be"/><circle cx="${t.cursor[0]}" cy="${t.cursor[1]}" r="10" fill="#604632" stroke="#fff3de" stroke-width="1.5"/><text x="${t.cursor[0]}" y="${t.cursor[1]+4}" text-anchor="middle" fill="#fff4de" font-size="14">${tools[s][0]}</text>`:''}`;
  }else if(s==='straps'){
   overlay=[0,1].map(i=>!d.placed.includes(i)?`<rect x="${i?302:190}" y="106" width="68" height="48" rx="12" fill="#fff1cc" fill-opacity=".5" stroke="#7c5c42" stroke-dasharray="5 5"/><g><rect x="${i?450:42}" y="174" width="68" height="112" rx="12" fill="#f2dfb9"/><path d="M${i?466:58} 260V218Q${i?484:76} 176 ${i?502:94} 218V260" fill="none" stroke="${color()}" stroke-width="13"/><text x="${i?484:76}" y="280" text-anchor="middle" font-size="12" fill="#634b37">${i?'Quai 2':'Quai 1'}</text></g>`:'').join('');
  }else if(s==='stuff'){
   overlay=`${stuffSlots.map(([x,y],i)=>d.stuffed.includes(i)?'':`<circle cx="${x}" cy="${y}" r="20" fill="#fff6dd" fill-opacity=".5" stroke="#fff6dd" stroke-width="2" stroke-dasharray="4 4"/><text x="${x}" y="${y+4}" text-anchor="middle" fill="#78583f" font-size="12">${i+1}</text>`).join('')}<g><rect x="151" y="371" width="73" height="36" rx="10" fill="#e4d3b7"/><path d="M164 396Q150 385 167 382Q170 371 182 379Q194 368 201 382Q218 382 211 394Z" fill="#fffaf0"/><text x="295" y="394" fill="#fff5df" text-anchor="middle" font-size="11">Bông mềm · ${d.stuffed.length}/4 vùng</text></g>`;
  }else if(s==='decorate'&&d.kind==='teddy'&&held!==null&&String(held).startsWith('face')){
   const i=Number(held.slice(4)),[x,y]=faceSlots[i];overlay=`<circle cx="${x}" cy="${y}" r="22" fill="#fff6dd" fill-opacity=".4" stroke="#fff6dd" stroke-dasharray="4 4"/>`;
  }
  if(drag==='stuff'&&dragPoint)overlay+=`<g transform="translate(${dragPoint[0]-182} ${dragPoint[1]-387})"><path d="M164 396Q150 385 167 382Q170 371 182 379Q194 368 201 382Q218 382 211 394Z" fill="#fffaf0" stroke="#e1d1b4"/></g>`;
  q('.cw-art').innerHTML=`<ellipse cx="280" cy="408" rx="151" ry="11" fill="#203c2f" opacity=".14"/>${workpieceArt(d,color(),id)}${overlay}`;
  q('.cw-instruction h3').textContent=`${String(d.step+1).padStart(2,'0')} · ${labels[s]}`;
  q('.cw-instruction p').textContent=d.kind==='teddy'?({measure:'Kéo đầu thước đo vải: ngang 24 cm, dọc 30 cm.',cut:'Giữ kéo ở chấm sáng, cắt hai lớp vải theo dáng bạn gấu.',sew:'Giữ kim theo đường sáng, chừa một khe nhỏ để nhồi bông.',stuff:'Kéo bông mềm vào bốn vùng để bạn gấu đầy đặn dần.',decorate:'Gắn mắt, mũi, nơ và in một dấu lên bụng bạn gấu.'}[s]):instructions[s];
  q('.cw-feedback').textContent=status||(ready?(s==='decorate'?'Dấu ấn của bạn đã sẵn sàng. Thêm dấu hoặc cất lên kệ nhé.':'Đẹp rồi! Mình sang bước tiếp theo nhé.'):(t?`${Math.min(100,Math.round(t.count/path.length*100))}% đường ${s==='sew'?'may':'hướng dẫn'} · cứ thong thả làm nhé.`:s==='beads'?`Đã xâu ${d.placed.length}/8 hạt.`:s==='straps'?`Đã gắn ${d.placed.length}/2 quai.`:s==='stuff'?`Đã nhồi ${d.stuffed.length}/4 vùng. Bạn gấu đang mềm và đầy hơn.`:s==='decorate'&&d.kind==='teddy'?`Đã gắn ${d.face.length}/4 chi tiết · ${d.marks.length}/12 dấu trên bụng.`:'Không cần vội, bạn có thể làm lại bất cứ lúc nào.'));
  if(t&&!ready&&document.activeElement===stage){const [x,y]=path[t.count],dx=x-t.cursor[0],dy=y-t.cursor[1];q('.cw-feedback').textContent+=` Phím tiếp: ${Math.abs(dx)>Math.abs(dy)?dx>0?'phải →':'trái ←':dy>0?'xuống ↓':'lên ↑'}.`;}
  q('.cw-draft').textContent=busy?'Đang cất thành phẩm…':draftSaved?'✓ Bản nháp đã giữ trên máy này':key?'Bản nháp chỉ giữ khi cửa sổ này còn mở':'Chơi thử · bản nháp giữ trong lần mở này';
  const next=q('[data-craft="next"]');next.disabled=busy||!ready;next.textContent=busy?'Đang lưu…':d.step===RECIPES[d.kind].length-1?`Cất lên kệ · ${catalog.craft_fee} xu`:'Tiếp theo →';
  q('[data-craft="retry"]').disabled=busy;q('[data-craft="close"]').disabled=busy;
  if(controls){
   q('.cw-steps').innerHTML=RECIPES[d.kind].map((step,i)=>`<span class="${i===d.step?'active':i<d.step?'complete':''}" ${i===d.step?'aria-current="step"':''}><b>${i<d.step?'✓':i+1}</b><span>${labels[step]}</span></span>`).join('');
   let controlsHTML='';
   if(s==='measure')controlsHTML=d.measure.map((value,i)=>`<label class="cw-ruler">${i?'Dọc':'Ngang'} · ${SIZES[d.kind][i]} cm<input type="range" data-axis="${i}" min="8" max="${d.kind==='teddy'?(i?36:28):40}" step="1" value="${value}" aria-label="Đo ${i?'dọc':'ngang'} tấm vải bằng cm"/><output>${value} cm</output></label>`).join('');
   else if(s==='stuff')controlsHTML=`<div class="cw-place">${btn('☁ Cầm bông mềm','cotton')}<div>${stuffSlots.map((_,i)=>btn(`Nhồi vùng ${i+1}`,'stuff',`data-item="${i}" ${d.stuffed.includes(i)?'disabled':''}`)).join('')}</div></div>`;
   else if(s==='straps'||s==='beads')controlsHTML=`<div class="cw-place">${(s==='straps'?[0,1]:[0]).map(i=>btn(s==='straps'?`Cầm quai ${i+1}`:'Cầm một hạt','pick',`data-item="${i}" ${d.placed.includes(i)&&s==='straps'?'disabled':''}`)).join('')}<div>${(s==='straps'?[[224,126],[336,126]]:beadSlots).map((_,i)=>btn(s==='straps'?`Gắn quai ${i+1}`:`Vị trí ${i+1}`,'place',`data-item="${i}" ${d.placed.includes(i)?'disabled':''}`)).join('')}</div></div>`;
   else if(s==='decorate')controlsHTML=`${d.kind==='teddy'?`<div class="cw-face-tools">${faceNames.map((name,i)=>btn(`${d.face.includes(i)?'✓ ':''}${name}`,'face-pick',`data-item="${i}" ${d.face.includes(i)?'disabled':''}`)).join('')}${btn('Gắn vào chỗ sáng','face-place',held!==null&&String(held).startsWith('face')?'':'disabled')}</div>`:''}<div class="cw-stamps">${btn(markFor(d.pattern)+' In chính giữa','stamp','data-x="0.5" data-y="0.52"')}${btn('In góc trái','stamp','data-x="0.24" data-y="0.3"')}${btn('In góc phải','stamp','data-x="0.76" data-y="0.3"')}${btn('↶ Bỏ dấu cuối','undo',d.marks.length?'':'disabled')}</div>`;
   else controlsHTML=`<span class="cw-tool-label">Giữ và kéo trên đường sáng</span>${btn('Dùng phím mũi tên','keyboard','class="cw-secondary"')}`;
   q('.cw-tools').innerHTML=`<div class="cw-tool"><span aria-hidden="true">${tools[s][0]}</span><b>${tools[s][1]}</b></div><div class="cw-tool-controls">${controlsHTML}</div>`;
   q('.cw-help').textContent=PATHS[s]?'Bàn phím: chọn “Dùng phím mũi tên”, rồi dùng ↑ ↓ ← → để đưa dụng cụ theo đường.':s==='measure'?'Có thể dùng hai thanh thước bên dưới; Tab để chọn, phím mũi tên để chỉnh từng cm.':s==='decorate'?'Tối đa 12 dấu. Dùng nút in để thao tác bằng bàn phím.':'Có thể dùng các nút cầm và gắn bên dưới để thao tác bằng bàn phím.';
   if(restoreFocus){const candidates=[...q('.cw-tools').querySelectorAll('button:not(:disabled),input')];const next=focusData.craft==='face-pick'?candidates.find(x=>x.dataset.craft==='face-place'):candidates.find(x=>x.dataset.craft===focusData.craft&&x.dataset.item===focusData.item&&x.dataset.x===focusData.x);(next||candidates[0])?.focus();}
  }
 }
 function act(){status='';persist();refresh();}
 function stamp(x,y){if(d.marks.length>=12){status='Đã đủ 12 dấu. Bỏ dấu cuối nếu bạn muốn đổi vị trí.';refresh();return;}d.marks.push([Math.max(0,Math.min(1,x)),Math.max(0,Math.min(1,y))]);act();refresh(true);}
 function place(i){if(held===null||d.placed.includes(i)){status='Cầm một món trong khay trước nhé.';refresh();return;}if(current()==='straps'&&held!==i){status='Đặt quai vào vị trí cùng số nhé.';refresh();return;}d.placed.push(i);held=null;act();refresh(true);}
 function stuff(i){if(held!=='cotton'||d.stuffed.includes(i)){status='Cầm bông mềm trong khay rồi chọn một vùng còn trống.';refresh();return;}d.stuffed.push(i);held=null;act();refresh(true);}
 function facePlace(){if(held===null||!String(held).startsWith('face'))return;const i=Number(held.slice(4));if(!d.face.includes(i))d.face.push(i);held=null;act();refresh(true);}
 const point=e=>{const p=stage.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const v=p.matrixTransform(stage.getScreenCTM().inverse());return [v.x,v.y];};
 stage.addEventListener('pointerdown',e=>{if(busy||e.button!==0)return;const p=point(e),s=current();
  if(s==='decorate'){if(d.kind==='teddy'){const fat=1+d.stuffed.length*.02,bp=[280+(p[0]-280)/fat,235+(p[1]-235)/fat];if(held!==null&&String(held).startsWith('face')){if(distance(bp,faceSlots[Number(held.slice(4))])<26)facePlace();}else if(bp[0]>=248&&bp[0]<=312&&bp[1]>=247&&bp[1]<=305)stamp((bp[0]-252)/56,(bp[1]-253)/43);}else if(p[0]>=152&&p[0]<=408&&p[1]>=130&&p[1]<=378)stamp((p[0]-152)/256,(p[1]-130)/248);return;}
  if(s==='measure'){if(distance(p,[(d.kind==='teddy'?184:152)+d.measure[0]*8,91])<30)drag=0;else if(distance(p,[d.kind==='teddy'?402:429,110+d.measure[1]*8])<30)drag=1;}
  else if(PATHS[s]){const t=trace(),path=sampledPath(pathFor(d,s));if(t.count<path.length&&distance(p,path[t.count])<30){drag='trace';d.trace[s]=tracePoint({...t,last:null},path,p);}}
  else if(s==='straps'){const i=p[0]<140?0:p[0]>420?1:null;if(i!==null&&!d.placed.includes(i)){held=i;drag='place';status=`Quai ${i+1}: kéo vào ô sáng cùng bên.`;}}
  else if(s==='beads'&&held!==null){const i=beadSlots.findIndex(x=>distance(x,p)<30);if(i>=0)place(i);}
  else if(s==='stuff'){if(p[0]>=146&&p[0]<=228&&p[1]>=363){held='cotton';drag='stuff';status='Kéo bông vào một vùng sáng trên bạn gấu.';}else if(held==='cotton'){const i=stuffSlots.findIndex(x=>distance(x,p)<25);if(i>=0)stuff(i);}}
  if(drag!==null){dragPoint=p;e.preventDefault();stage.setPointerCapture(e.pointerId);refresh();}
 });
 stage.addEventListener('pointermove',e=>{if(busy||drag===null)return;const p=point(e),s=current();if(typeof drag==='number'){const max=d.kind==='teddy'?(drag?36:28):40;d.measure[drag]=Math.max(8,Math.min(max,Math.round((p[drag]-(drag?110:d.kind==='teddy'?184:152))/8)));q(`[data-axis="${drag}"]`).value=d.measure[drag];q(`[data-axis="${drag}"]`).nextElementSibling.textContent=`${d.measure[drag]} cm`;}
  else if(drag==='trace'){d.trace[s]=tracePoint(trace(),sampledPath(pathFor(d,s)),p);}dragPoint=p;act();
 });
 const release=e=>{if(drag==='place'&&e.type!=='pointercancel'){const p=point(e),i=[[224,126],[336,126]].findIndex(x=>distance(x,p)<45);if(i>=0)place(i);}if(drag==='stuff'&&e.type!=='pointercancel'){const p=point(e),i=stuffSlots.findIndex(x=>distance(x,p)<25);if(i>=0)stuff(i);}drag=null;if(stage.hasPointerCapture(e.pointerId))stage.releasePointerCapture(e.pointerId);persist();refresh();};
 stage.addEventListener('pointerup',release);stage.addEventListener('pointercancel',release);
 stage.addEventListener('keydown',e=>{if(busy||!PATHS[current()]||!e.key.startsWith('Arrow'))return;e.preventDefault();const path=sampledPath(pathFor(d));let t=trace();if(!t.count)t=tracePoint(t,path,path[0]);d.trace[current()]=traceKeyboard(t,path,e.key);act();});
 dialog.addEventListener('input',e=>{if(busy||e.target.dataset.axis===undefined)return;const axis=Number(e.target.dataset.axis);d.measure[axis]=Number(e.target.value);e.target.nextElementSibling.textContent=`${d.measure[axis]} cm`;act();});
 dialog.addEventListener('click',async e=>{const b=e.target.closest('[data-craft]');if(!b||busy)return;switch(b.dataset.craft){
  case 'close':dialog.close();break;
  case 'keyboard':stage.focus();break;
  case 'cotton':held='cotton';status='Đang cầm bông mềm. Chọn vùng cần nhồi trên bạn gấu.';refresh();break;
  case 'stuff':stuff(Number(b.dataset.item));break;
  case 'face-pick':held=`face${b.dataset.item}`;status=`Đang cầm ${faceNames[Number(b.dataset.item)].toLowerCase()}. Chạm vào chỗ sáng hoặc chọn nút gắn.`;refresh(true);break;
  case 'face-place':facePlace();break;
  case 'pick':held=Number(b.dataset.item);status=current()==='straps'?`Đang cầm quai ${held+1}. Chọn vị trí cùng số.`:'Đang cầm một hạt. Chọn vị trí còn trống.';refresh();break;
  case 'place':place(Number(b.dataset.item));break;
  case 'stamp':stamp(Number(b.dataset.x),Number(b.dataset.y));break;
  case 'undo':d.marks.pop();act();refresh(true);break;
  case 'retry':{const s=current();if(PATHS[s])delete d.trace[s];else if(s==='measure')d.measure=[12,12];else if(s==='decorate'){d.marks=[];d.face=[];}else if(s==='stuff')d.stuffed=[];else d.placed=[];d.done=d.done.filter(x=>x!==s);held=null;act();refresh(true);break;}
  case 'next':{
   if(!stepComplete(d))break;
   if(d.step<RECIPES[d.kind].length-1){nextStep(d);held=null;act();refresh(true);q('.cw-instruction h3').setAttribute('tabindex','-1');q('.cw-instruction h3').focus();break;}
   if(!craftWork(d))break;
   if(full()){status='Kệ đã đủ 24 món. Bản nháp của bạn vẫn được giữ.';refresh();break;}
   busy=true;refresh();
   try{const pay=await confirmPurchase(env,{title:'Cất món tự tay làm lên kệ',message:`${names[d.kind]}. Phí nguyên liệu ${catalog.craft_fee} xu, thanh toán một lần khi cất thành phẩm.`,label:`Thanh toán · ${catalog.craft_fee} xu`,cost:catalog.craft_fee});
    if(!pay){status='Chưa thanh toán. Thành phẩm vẫn ở đây để bạn cất sau.';break;}
    const result=await submitCraft(env,d,pay,{storage,key});if(result){saved=true;dialog.close();env.renderSheet?.(false);}else status='Chưa cất được thành phẩm. Bản nháp vẫn còn; hãy thử lại khi kết nối ổn định.';
   }catch{status='Kết nối bị gián đoạn. Bản nháp vẫn còn, bạn có thể thử cất lại.';}finally{busy=false;if(dialog.isConnected)refresh();}
   break;
  }
 }});
 dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
 dialog.addEventListener('close',()=>{if(!saved)persist();dialog.remove();if(opener?.isConnected)opener.focus();},{once:true});
 if(raw&&d!==selected)status='Mình làm tiếp món đang dở nhé. Bản nháp đã được mở lại.';
 refresh(true);dialog.showModal();q('[data-craft="close"]').focus();return true;
}
