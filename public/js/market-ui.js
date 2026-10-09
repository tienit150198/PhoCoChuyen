/** 📈 Lãi nhân viên theo thị trường + 🔥 Nghề hot hôm nay (game/staff_market.py; owner 09/10).
 * state.market = {hot, x: {career: hundredths}, slot}: every staffed career's multiplier now and today's hot career.
 * A workplace's business.market = {x, was, hot, curve, slot}: its own line, the 2-hour trend and the 48 h curve.
 * Few words: one tag or chip, a number and an arrow; the curve is a 64×16 line. */

/** ×1,3 (Vietnamese decimal comma; one decimal, ×2 for whole numbers). */
export function mx(h){const v=Math.round(Number(h||0)/10)/10;return '×'+(Number.isInteger(v)?String(v):v.toFixed(1).replace('.',','));}

/** [text, tone] for a career's tag, or null when its staff earn about as usual (×0,9 … ×1,1). */
export function marketTag(state,cid){
  const m=state?.market;if(!m||!m.x||m.x[cid]==null)return null;
  const x=m.x[cid];
  if(m.hot===cid)return [`🔥 Nghề hot ${mx(x)}`,'amber'];
  if(x>=110)return [`📈 Lãi cao ${mx(x)}`,'green'];
  if(x<=90)return [`📉 Lãi thấp ${mx(x)}`,''];
  return null;
}

/** The workplace card's line: "🔥 Hôm nay lãi cao ×2" / "📈 Lãi đang cao ×1,3 ↑" / "📉 ×0,8 ↓" / "Lãi bình thường ×1". */
export function marketLine(v){
  if(!v||!v.x)return '';
  const arrow=v.x>v.was?' ↑':v.x<v.was?' ↓':'';
  if(v.hot)return `🔥 Hôm nay lãi cao ${mx(v.x)}`;
  if(v.x>=110)return `📈 Lãi đang cao ${mx(v.x)}${arrow}`;
  if(v.x<=90)return `📉 Lãi đang thấp ${mx(v.x)}${arrow}`;
  return `Lãi bình thường ${mx(v.x)}${arrow}`;
}

/** A tiny line of the last 48 h (decorative: the words above say the number). */
export function sparkline(curve,w=64,h=16){
  if(!Array.isArray(curve)||curve.length<2)return '';
  const lo=Math.min(...curve,60),hi=Math.max(...curve,160),k=(w-2)/(curve.length-1);
  const pts=curve.map((v,i)=>`${(1+i*k).toFixed(1)},${(h-1-(v-lo)/(hi-lo||1)*(h-2)).toFixed(1)}`).join(' ');
  const base=(h-1-(100-lo)/(hi-lo||1)*(h-2)).toFixed(1);
  return `<svg class="mk-spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><path d="M1 ${base}H${w-1}" stroke="currentColor" stroke-opacity=".25" stroke-dasharray="2 2"/><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}

/** The average multiplier between two moments (ms), from a curve that ends at serverNow (s): the away card's "×1,3". */
export function curveAverage(v,fromMs,toMs){
  if(!v||!Array.isArray(v.curve)||!v.curve.length||!v.slot)return null;
  const n=v.curve.length,cur=Math.floor((v.server_now||toMs/1000)/v.slot);
  const a=Math.max(0,n-1-(cur-Math.floor(fromMs/1000/v.slot))),b=Math.min(n-1,n-1-(cur-Math.floor(toMs/1000/v.slot)));
  if(b<a)return null;
  const part=v.curve.slice(a,b+1);
  return {x:Math.round(part.reduce((s,x)=>s+x,0)/part.length),hot:part.some(x=>x>=200)};
}
