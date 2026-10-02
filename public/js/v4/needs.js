/** 🍚 No bụng · 😴 Tỉnh táo (server: game/needs.py → state.needs). Markup only: every number, price and rule comes
 * from the server.
 *
 * - needBars(N): the two small bars, drawn like the spirit meter (life.css .lf-meter), for the Đời thường card and
 *   sheet and the evening;
 * - lunchStrip(N): the lunch moment inside the calm card (from 11:30 on the shop clock, one tap, never a modal);
 * - snackStrip(N): "Ăn thêm", paid snacks and a coffee any time in the work day (the calm card when hungry or
 *   sleepy, and the Đời thường sheet);
 * - eveningBody(N,pick): the evening sheet after closing the day (dinner, bedtime, "như mọi khi");
 * - needsAction(): ndLunch / ndSnack / ndMeal / ndBed / ndEve / ndUsual.
 * Story mode only (state.needs.enabled), like tinh thần. */
import {escapeHTML as esc} from '../icons.js';

const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const price=n=>n>0?`${fmt(n)} xu`:'Miễn phí';

/** One bar: emoji, name, value and a thin bar coloured by tone (good / mid / low). */
function bar(emoji,name,b,{wide=false}={}){
  const v=Math.max(0,Math.min(100,b?.value|0)),label=b?.label||'';
  return `<div class="lf-meter nd-meter small ${esc(b?.tone||'good')}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}" aria-label="${esc(name)} ${v} trên 100, ${esc(label)}"><span class="lf-mood" aria-hidden="true">${emoji}</span><div class="grow"><div class="lf-meter-row"><b>${esc(name)}</b><span>${wide?`${v}/100 · ${esc(label)}`:v}</span></div><div class="lf-bar"><i style="width:${Math.max(3,v)}%"></i></div></div></div>`;
}
/** The two bars side by side (they stack below 330 px). `wide`: with the words ("Hơi đói"). */
export function needBars(N,opts={}){
  if(!N?.enabled)return '';
  return `<div class="nd-bars${opts.wide?' wide':''}">${bar('🍚','No bụng',N.full,opts)}${bar('😴','Tỉnh táo',N.wake,opts)}</div>`;
}

/** Lunch, inside the calm card while the shift is open: four one-tap choices. */
export function lunchStrip(N,wallet=0){
  const L=N?.enabled&&N.lunch;if(!L)return '';
  const chip=c=>{
    const off=!c.ok,sub=c.id==='nhin'?'Bỏ bữa':price(c.price);
    return `<button type="button" class="nd-chip${c.id==='nhin'?' skip':''}" data-action="ndLunch" data-meal="${esc(c.id)}"${off?' disabled':''}><span aria-hidden="true">${c.emoji}</span><b>${esc(c.short||c.name)}</b><small>${esc(sub)}</small></button>`;
  };
  return `<div class="nd-lunch" role="group" aria-label="Giờ ăn trưa"><p class="nd-lunch-head"><span aria-hidden="true">🍱</span><b>Trưa rồi, ăn gì đây?</b><small>No bụng ${N.full?.value|0}</small></p><div class="nd-lunch-row">${L.choices.map(chip).join('')}</div></div>`;
}

/** True when the calm card should offer a snack: hungry or sleepy, and no lunch strip already there. */
export function snackDue(N){
  return !!(N?.enabled&&N.snack&&!N.lunch&&((N.full?.value|0)<50||(N.wake?.value|0)<40));
}
/** Ăn thêm: four one-tap paid choices (same chips as lunch). `head`: the line above them. */
export function snackStrip(N,{head='Đói bụng rồi? Ăn thêm gì đó'}={}){
  const S=N?.enabled&&N.snack;if(!S)return '';
  const chip=c=>{
    const sub=c.ok?price(c.price):c.why;
    return `<button type="button" class="nd-chip" data-action="ndSnack" data-item="${esc(c.id)}"${c.ok?'':' disabled'} title="${esc(c.name)}"><span aria-hidden="true">${c.emoji}</span><b>${esc(c.short||c.name)}</b><small>${esc(sub)}</small></button>`;
  };
  return `<div class="nd-lunch nd-snack" role="group" aria-label="Ăn thêm"><p class="nd-lunch-head"><span aria-hidden="true">🍢</span><b>${esc(head)}</b><small>No bụng ${N.full?.value|0} · tỉnh táo ${N.wake?.value|0}</small></p><div class="nd-lunch-row">${S.map(chip).join('')}</div></div>`;
}

/** The pick shown in the evening sheet: the player's taps, else "như mọi khi"; a bedtime the dinner rules out moves on. */
export function evePick(N,pick){
  const E=N?.evening;if(!E)return null;
  const meal=E.meals.find(m=>m.id===pick?.meal&&m.ok)||E.meals.find(m=>m.id===E.usual.meal)||E.meals[0];
  const beds=(meal.beds||[]).filter(b=>b.ok);
  const bed=beds.find(b=>b.bed===pick?.bed)||beds.find(b=>b.bed===E.usual.bed)||beds.find(b=>b.bed>=1380)||beds[beds.length-1];
  return {meal,bed};
}

function effectLine(m){
  const out=[`<span class="up">No bụng +${m.full}</span>`];
  if(m.spirit)out.push(`<span class="up">tinh thần +${m.spirit}</span>`);
  out.push(`<span>${m.minutes} phút</span>`);
  return out.join(' · ');
}
/** "Ngủ sớm · Sáng mai tỉnh táo 100 · tinh thần +1 sáng mai": one element per part (each translates alone). */
function bedLine(b){
  const sp=b.spirit?`<span class="up">tinh thần +${b.spirit}${b.when==='morning'?' sáng mai':' tối nay'}</span>`:'';
  return `<b>${esc(b.text)}</b><span>Sáng mai tỉnh táo ${b.wake}</span>${sp}`;
}

/** The evening sheet's body and foot (the caller adds the header). `start`: the "Bắt đầu ngày N" button. */
export function eveningBody(N,pick,{start='',wallet=0}={}){
  const E=N?.evening;if(!E)return '';
  if(E.chosen){
    const c=E.chosen;
    return `<div class="sheet-body nd-eve"><div class="nd-night"><span class="nd-moon" aria-hidden="true">🌙</span><div><b>Chúc ngủ ngon!</b><p>${c.emoji} ${esc(c.name)} · ngủ lúc ${esc(c.time)}</p><p class="muted"><span>Sáng mai tỉnh táo ${c.wake}.</span> <span>Bữa sáng có sẵn, không tốn thêm xu.</span></p></div></div>${needBars(N,{wide:true})}</div>`+
      `<footer class="sheet-foot"><p></p><div class="row wrap">${start}</div></footer>`;
  }
  const sel=evePick(N,pick),u=E.usual;
  const meals=E.meals.map(m=>{
    const on=m.id===sel.meal.id,sub=m.price?`${fmt(m.price)} xu`:'Miễn phí';
    return `<button type="button" role="radio" aria-checked="${on}" class="lf-choice nd-opt${on?' on':''}" data-action="ndMeal" data-meal="${esc(m.id)}"${m.ok?'':' disabled'}><span class="lf-ch-emoji" aria-hidden="true">${m.emoji}</span><span class="lf-ch-text"><b>${esc(m.name)} <i class="nd-price${m.price?'':' free'}">${sub}</i></b><small>${esc(m.note)}</small><small class="nd-eff">${effectLine(m)}</small>${m.why?`<em>${esc(m.why)}</em>`:''}</span></button>`;
  }).join('');
  const beds=sel.meal.beds.map(b=>{
    const on=b.ok&&b.bed===sel.bed.bed;
    return `<button type="button" role="radio" aria-checked="${on}" class="nd-bed${on?' on':''}" data-action="ndBed" data-bed="${b.bed}"${b.ok?'':' disabled'}><b>${esc(b.time)}</b><small>${b.ok?esc(b.text):'Ăn chưa xong'}</small></button>`;
  }).join('');
  const usual=`<button type="button" class="nd-usual" data-action="ndUsual"><span aria-hidden="true">🌙</span><span class="grow"><b>Như mọi khi</b><small><span>${u.emoji} ${esc(u.name)}</span>${u.price?` <i class="nd-price">${fmt(u.price)} xu</i>`:''} · <span>ngủ lúc ${esc(u.time)}</span></small></span><i>Chọn</i></button>`;
  return `<div class="sheet-body nd-eve">${needBars(N,{wide:true})}${usual}
    <h3 class="jr-sub">Tối nay ăn gì?</h3><div class="lf-choices nd-meals" role="radiogroup" aria-label="Bữa tối">${meals}</div>
    <p class="nd-fine"><span>Cơm nhà đã tính trong tiền cơm nước mỗi ngày, nên không tốn thêm.</span> <span>Ví còn ${fmt(wallet)} xu.</span></p>
    <h3 class="jr-sub">Mấy giờ đi ngủ?</h3><div class="nd-beds" role="radiogroup" aria-label="Giờ đi ngủ">${beds}</div>
    <p class="nd-bed-say">${bedLine(sel.bed)}</p></div>`+
    `<footer class="sheet-foot"><p></p><div class="row wrap"><button type="button" class="btn primary big" data-action="ndEve" data-meal="${esc(sel.meal.id)}" data-bed="${sel.bed.bed}">🌙 Đi ngủ lúc ${esc(sel.bed.time)}</button></div></footer>`;
}

/** Buttons of this module. env: {api, ui, cmd, renderSheet, renderMain}. */
export async function needsAction(action,data,el,env){
  if(!action?.startsWith('nd'))return false;
  const {api,ui,cmd}=env,N=api.state?.needs;
  switch(action){
    case'ndLunch':{if(el)el.disabled=true;await cmd('jr_needs_lunch',{meal:data.meal});env.renderMain?.();return true;}
    case'ndSnack':{if(el)el.disabled=true;const r=await cmd('jr_needs_snack',{item:data.item});if(el)el.disabled=false;
      env.renderMain?.();if(r&&document.getElementById('sheet')?.open)env.renderSheet?.(false);return true;}
    case'ndMeal':ui.eve={...(ui.eve||{}),meal:data.meal};env.renderSheet(false);return true;
    case'ndBed':ui.eve={...(ui.eve||{}),bed:Number(data.bed)};env.renderSheet(false);return true;
    case'ndEve':case'ndUsual':{
      const E=N?.evening;if(!E)return true;
      const p=action==='ndUsual'?{meal:E.usual.meal,bed:E.usual.bed}:{meal:data.meal,bed:Number(data.bed)};
      if(el)el.disabled=true;const r=await cmd('jr_needs_eve',p);if(el)el.disabled=false;
      if(r){ui.eve=null;env.renderSheet(false);}
      return true;
    }
  }
  return false;
}
