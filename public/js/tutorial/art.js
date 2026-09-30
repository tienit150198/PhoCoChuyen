/** Small inline illustrations for the tutorial (fixed colours are fine in
 * art; the CSS dims them with --scene-filter in the dark theme). */

/** "A working day" as a loop of five small stops. */
export const dayArt=()=>{
  const stops=[['🧺','Chuẩn bị'],['☀️','Mở cửa'],['🙋','Làm việc'],['🌙','Khép ca'],['📊','Tổng kết']];
  return `<ol class="tut-flow" aria-label="Một ngày làm việc">${stops.map(([e,l],i)=>`<li><span class="tut-flow-dot" aria-hidden="true">${e}</span><small>${l}</small>${i<stops.length-1?'<i aria-hidden="true">›</i>':''}</li>`).join('')}</ol>`;
};
