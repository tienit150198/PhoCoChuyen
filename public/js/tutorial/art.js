/** Small inline illustrations for the tutorial (fixed colours are fine in
 * art; the CSS dims them with --scene-filter in the dark theme). */

/** Welcome card: a little street at sunrise. */
export const streetArt=()=>`<svg class="tut-art" viewBox="0 0 320 150" role="img" aria-label="Một góc phố nhỏ">
  <defs><linearGradient id="tutSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe7c7"/><stop offset="1" stop-color="#fff6ea"/></linearGradient></defs>
  <rect width="320" height="150" rx="18" fill="url(#tutSky)"/>
  <circle cx="262" cy="34" r="17" fill="#ffc15e"/><circle cx="262" cy="34" r="25" fill="#ffc15e" opacity=".22"/>
  <path d="M18 40q10-8 22 0q10-7 18 2H18Z" fill="#fff" opacity=".9"/><path d="M190 26q8-6 16 0q9-6 15 2h-31Z" fill="#fff" opacity=".85"/>
  <rect x="0" y="122" width="320" height="28" fill="#e9d6bb"/><rect x="0" y="120" width="320" height="4" fill="#d8bf9d"/>
  <g><rect x="22" y="62" width="78" height="60" rx="6" fill="#fbe3ea"/><path d="M18 62h86l-6 14H24Z" fill="#e889a6"/><path d="M30 62v14M44 62v14M58 62v14M72 62v14M86 62v14" stroke="#fff" stroke-width="5" opacity=".75"/>
    <rect x="34" y="86" width="24" height="36" rx="4" fill="#fff"/><rect x="64" y="86" width="26" height="18" rx="3" fill="#fff" opacity=".85"/><text x="77" y="100" font-size="13" text-anchor="middle">🧋</text></g>
  <g><rect x="116" y="50" width="88" height="72" rx="6" fill="#e3f0dc"/><path d="M112 50h96l-6 15H118Z" fill="#6aa564"/><path d="M126 50v15M142 50v15M158 50v15M174 50v15M190 50v15" stroke="#fff" stroke-width="5" opacity=".7"/>
    <rect x="128" y="78" width="30" height="44" rx="4" fill="#fff"/><rect x="166" y="78" width="28" height="22" rx="3" fill="#fff" opacity=".85"/><text x="180" y="94" font-size="13" text-anchor="middle">🛒</text></g>
  <g><rect x="220" y="66" width="80" height="56" rx="6" fill="#fdebd3"/><path d="M216 66h88l-6 14H222Z" fill="#e0934a"/><path d="M228 66v14M242 66v14M256 66v14M270 66v14M284 66v14" stroke="#fff" stroke-width="5" opacity=".7"/>
    <rect x="232" y="90" width="22" height="32" rx="4" fill="#fff"/><rect x="262" y="90" width="28" height="16" rx="3" fill="#fff" opacity=".85"/><text x="276" y="103" font-size="12" text-anchor="middle">🥐</text></g>
  <circle cx="108" cy="104" r="11" fill="#7fb27a"/><rect x="106" y="108" width="4" height="14" fill="#8a6a4c"/>
  <path d="M112 30q48 14 96 0" stroke="#b58b62" stroke-width="1.4" fill="none"/><circle cx="136" cy="36" r="5" fill="#ff8a6b"/><circle cx="160" cy="38" r="5" fill="#ffc15e"/><circle cx="184" cy="36" r="5" fill="#ff8a6b"/>
  <text x="150" y="141" font-size="18" text-anchor="middle">🛵</text><text x="206" y="143" font-size="16" text-anchor="middle">🐈</text>
</svg>`;

/** "A working day" as a loop of five small stops. */
export const dayArt=()=>{
  const stops=[['🧺','Chuẩn bị'],['☀️','Mở cửa'],['🙋','Làm việc'],['🌙','Khép ca'],['📊','Tổng kết']];
  return `<ol class="tut-flow" aria-label="Một ngày làm việc">${stops.map(([e,l],i)=>`<li><span class="tut-flow-dot" aria-hidden="true">${e}</span><small>${l}</small>${i<stops.length-1?'<i aria-hidden="true">›</i>':''}</li>`).join('')}</ol>`;
};
