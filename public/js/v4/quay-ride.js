/** 🛵 Quầy của bạn: the short ride to an online customer (game/quay_self.py, jr_quay_ship way 'self').
 * A small map: your counter at the bottom, the app's dotted route to the pin, three crossings; at each one the player
 * taps ⬅️ ⬆️ ➡️ and the scooter goes that way (the server checks the three turns against the order's route).
 * Built to be swapped for the first-person driving view (feat/delivery-drive) when it lands: a module that can drive
 * an order sets RIDE.external = async order => ['L'|'S'|'R', x3] and v4/quay.js hands the ride to it instead. */
export const RIDE={external:null};
const SEG=40,DIRS=[[0,-1],[1,0],[0,1],[-1,0]];   // up, right, down, left
const TURN={L:-1,S:0,R:1};
/** The points of a route from the counter: a first stretch up, then a turn and a stretch per step. */
export function pathOf(route){
  let x=0,y=0,h=0;const pts=[[x,y]];y-=SEG;pts.push([x,y]);
  for(const t of route){h=(h+TURN[t]+4)%4;x+=DIRS[h][0]*SEG;y+=DIRS[h][1]*SEG;pts.push([x,y]);}
  return pts;
}
/** The three ways out of the next crossing as the map shows them (#144: ⬅️ ⬆️ ➡️ were turns from the scooter's seat,
 * so a scooter heading right had no ⬇️ for a road going down). Each still sends the server its turn L/S/R. */
const WAYS=[['⬆️','Đi lên'],['➡️','Sang phải'],['⬇️','Đi xuống'],['⬅️','Sang trái']];
export function turnChoices(){return [{k:'L',d:3,emoji:'↰',label:'Rẽ trái'},{k:'S',d:0,emoji:'↑',label:'Đi thẳng'},{k:'R',d:1,emoji:'↱',label:'Rẽ phải'}];}

const line=(pts,attrs)=>`<polyline points="${pts.map(p=>p.join(',')).join(' ')}" fill="none" ${attrs}/>`;
/** The map as inline SVG: `route` the order's turns, `picks` the turns taken so far. */
export function rideSVG(route,picks){
 const done=picks.length>=route.length,next=route[picks.length],sign={L:'↰ RẼ TRÁI',S:'↑ ĐI THẲNG',R:'RẼ PHẢI ↱'}[next]||'ĐIỂM GIAO HÀNG';
 const wrong=picks.some((turn,i)=>turn!==route[i]);
 return `<svg class="qy-map qy-rider-view" viewBox="0 0 480 320" role="img" aria-label="Góc nhìn người lái, ${done?'đã qua các ngã tư':`ngã tư ${picks.length+1}, ${sign}`}" xmlns="http://www.w3.org/2000/svg">
 <rect width="480" height="320" rx="16" fill="#dcebed"/><circle cx="384" cy="49" r="23" fill="#fff5d2"/><path d="M0 148L87 124L137 130L188 120L263 127L344 117L480 136V205H0Z" fill="#c4d4b8"/>
 <path d="M0 111L157 133V211H0Z" fill="#e2bb95"/><path d="M480 104L322 132V211H480Z" fill="#d3c4a5"/>
 <g fill="#83a4a2" stroke="#f3dfbd" stroke-width="4"><path d="M16 136L55 143V176L16 173Z"/><path d="M80 147L112 152V180L80 178Z"/><path d="M362 147L400 139V175L362 180Z"/><path d="M423 132L462 124V172L423 175Z"/></g>
 <path d="M195 134H285L435 320H45Z" fill="#8d928a"/><path d="M0 178L480 178V218L0 218Z" fill="#8d928a"/>
 <path d="M195 134L45 320M285 134L435 320" stroke="#e6dfc5" stroke-width="5"/><path d="M240 139V158M240 182V207M240 230V278" stroke="#fff1c8" stroke-width="4" stroke-dasharray="13 9"/>
 <path d="M173 172H307" stroke="#f9f5df" stroke-width="8" stroke-dasharray="10 5"/><path d="M179 227H301" stroke="#f9f5df" stroke-width="10" stroke-dasharray="12 7"/>
 <rect x="165" y="37" width="150" height="43" rx="8" fill="#52776c" stroke="#fff5da" stroke-width="3"/><text x="240" y="63" text-anchor="middle" font-family="sans-serif" font-size="17" font-weight="700" fill="#fff5da">${sign}</text>
 <path d="M185 81V127M295 81V127" stroke="#77796f" stroke-width="4"/>
 ${done?`<rect x="312" y="93" width="71" height="54" rx="7" fill="#fff5dd"/><text x="347" y="126" text-anchor="middle" font-size="29">${wrong?'↪':'📦'}</text>`:''}
 <path d="M90 279L177 268M303 268L390 279" stroke="#494d48" stroke-width="13" stroke-linecap="round"/>
 <ellipse cx="72" cy="267" rx="36" ry="16" fill="#454e4b"/><ellipse cx="408" cy="267" rx="36" ry="16" fill="#454e4b"/>
 <ellipse cx="72" cy="264" rx="28" ry="11" fill="#b9d5d3"/><ellipse cx="408" cy="264" rx="28" ry="11" fill="#b9d5d3"/>
 <path d="M156 320L172 277Q240 245 308 277L324 320Z" fill="#a75344" stroke="#734f3b" stroke-width="3"/>
 <rect x="197" y="276" width="86" height="32" rx="12" fill="#edf0db"/><text x="240" y="297" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700" fill="#4e6557">${picks.length} / ${route.length} NGÃ TƯ</text>
 <ellipse cx="139" cy="291" rx="28" ry="17" fill="#d9ab8a"/><ellipse cx="341" cy="291" rx="28" ry="17" fill="#d9ab8a"/>
 </svg>`;
}
