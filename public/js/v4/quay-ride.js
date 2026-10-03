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
const line=(pts,attrs)=>`<polyline points="${pts.map(p=>p.join(',')).join(' ')}" fill="none" ${attrs}/>`;
/** The map as inline SVG: `route` the order's turns, `picks` the turns taken so far. */
export function rideSVG(route,picks){
  const want=pathOf(route),mine=pathOf(picks);
  // the crossings met so far: a stub for every way out of each (roads, not hints)
  const stubs=[];
  const nodes=pathOf(picks.slice(0,3));
  let h=0;
  for(let i=1;i<Math.min(nodes.length,4);i++){
    const [x,y]=nodes[i];
    for(const d of [-1,0,1]){const hh=(h+d+4)%4;stubs.push([[x,y],[x+DIRS[hh][0]*SEG*.55,y+DIRS[hh][1]*SEG*.55]]);}
    if(i-1<picks.length)h=(h+TURN[picks[i-1]]+4)%4;
  }
  const all=[...want,...mine,...stubs.flat()];
  const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]);
  const pad=26,minX=Math.min(...xs)-pad,minY=Math.min(...ys)-pad,w=Math.max(...xs)-minX+pad,hgt=Math.max(...ys)-minY+pad;
  const end=want[want.length-1],me=mine[mine.length-1],done=picks.length>=route.length;
  const road='stroke="#d9cbb8" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"';
  return `<svg class="qy-map" viewBox="${minX} ${minY} ${w} ${hgt}" role="img" aria-label="Bản đồ giao hàng">
    <rect x="${minX}" y="${minY}" width="${w}" height="${hgt}" fill="#eef3e4"/>
    ${stubs.map(s=>line(s,road)).join('')}${line(want,road)}${line(mine,road)}
    ${line(want,'stroke="#3f86c9" stroke-width="3" stroke-dasharray="5 6" stroke-linecap="round" opacity=".85"')}
    ${line(mine,'stroke="#e0483e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"')}
    <text x="0" y="12" text-anchor="middle" font-size="16">🏪</text>
    <text x="${end[0]}" y="${end[1]-4}" text-anchor="middle" font-size="18">📍</text>
    <text x="${me[0]}" y="${me[1]+6}" text-anchor="middle" font-size="${done?20:17}">${done&&me[0]===end[0]&&me[1]===end[1]?'🎉':'🛵'}</text>
  </svg>`;
}
