/** Shared building blocks for readable career screens: a requirement list
 * (what is asked, and whether it is done yet), a folded aside for flavour
 * text, and a look-up table for menus and price lists. Pure string builders;
 * pass the career context's `esc`. Styles live in app.css ("UI kit"). */

const MARK={true:['ok','✓','đúng'],false:['bad','✗','sai'],null:['','○','chưa làm']};

/** rows: [{ok:true|false|null, icon, label, value, note, tone:'danger'|'warn'}] */
export function reqList(rows,esc,label='Yêu cầu'){
  return `<ul class="req-list" aria-label="${esc(label)}">${rows.map(r=>{
    const [cls,mark,said]=MARK[r.ok===true?'true':r.ok===false?'false':'null'];
    return `<li class="req-row ${cls}${r.tone?' tone-'+esc(r.tone):''}"><span class="req-mark" aria-label="${said}">${mark}</span>${r.icon?`<span class="req-icon" aria-hidden="true">${esc(r.icon)}</span>`:''}<span class="req-label">${esc(r.label)}${r.note?`<small>${esc(r.note)}</small>`:''}</span>${r.value?`<b class="req-value">${esc(r.value)}</b>`:''}</li>`;
  }).join('')}</ul>`;
}

/** One-line summary that opens to the full text (summary/body are HTML). */
export function fold(summary,body,open=false){
  return `<details class="fold"${open?' open':''}><summary>${summary}</summary><div class="fold-body">${body}</div></details>`;
}

/** groups: [{title, rows:[{icon, name, price, stock, tags:[{label,tone}], locked}]}] */
export function refTable(groups,esc){
  return groups.map(g=>`<section class="ref-group"><h3>${esc(g.title)}</h3><ul class="ref-list">${g.rows.map(r=>`<li class="ref-row${r.locked?' locked':''}">
    <span class="ref-icon" aria-hidden="true">${esc(r.icon||'')}</span>
    <span class="ref-name"><b>${esc(r.name)}</b>${(r.tags||[]).length||r.stock!=null?`<span class="ref-tags">${(r.tags||[]).map(t=>`<span class="ref-tag${t.tone?' '+esc(t.tone):''}">${esc(t.label)}</span>`).join('')}${r.stock!=null?`<small class="ref-stock">${esc(String(r.stock))}</small>`:''}</span>`:''}</span>
    <b class="ref-price">${esc(String(r.price??''))}</b></li>`).join('')}</ul></section>`).join('');
}
