/** Decorative neighbourhood view of the courier's existing 7 × 5 road grid.
 * The horizontal-then-vertical trace preserves the planner's Manhattan legs.
 * This module has no game state, events, random scenery or network requests. */
const CELL=84,X=48,Y=60,W=600,H=444;
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const point=n=>[X+n.x*CELL,Y+n.y*CELL];
const valid=n=>n&&Number.isFinite(n.x)&&Number.isFinite(n.y);

export function routePoints(nodes,from,route){
  let current=nodes[from];if(!valid(current))return '';
  const points=[point(current)];
  for(const id of route){const next=nodes[id];if(!valid(next))continue;
    points.push(point({x:next.x,y:current.y}),point(next));current=next;
  }
  return points.map(p=>p.join(',')).join(' ');
}

function scenery(){
  const out=[];
  for(let row=0;row<4;row++)for(let col=0;col<6;col++){
    const x=X+col*CELL+12,y=Y+row*CELL+12,district=Math.floor(col/2);
    const garden=(col+row*3)%5===0;
    out.push(`<g class="dm-block district-${district}"><rect x="${x}" y="${y}" width="60" height="60" rx="8" fill="${['#e3e8cf','#eee1ca','#dce8d8'][district]}"/>`);
    if(garden){
      out.push(`<rect x="${x+8}" y="${y+8}" width="44" height="44" rx="13" fill="#c7d9af"/><path d="M${x+12} ${y+30}h36" stroke="#eaf0d7" stroke-width="5"/>`);
    }else{
      for(let b=0;b<2;b++){
        const bx=x+7+b*25,by=y+8+(col+row+b)%3*3;
        out.push(`<g class="dm-building"><rect x="${bx+2}" y="${by+3}" width="20" height="33" rx="3" fill="#394d4620"/><rect x="${bx}" y="${by}" width="20" height="33" rx="3" fill="${['#dbbfa2','#d2c6b4','#b8cbb8'][district]}" stroke="#fff8ec" stroke-width="1.5"/><path d="M${bx+4} ${by+5}h12v22h-12z" fill="none" stroke="#7b877a" stroke-opacity=".35"/><path d="M${bx+7} ${by+7}v18" stroke="#fff8ec" stroke-opacity=".7"/></g>`);
      }
    }
    for(let tree=0;tree<(garden?3:1);tree++){
      const tx=x+10+tree*19,ty=y+49-(garden?tree%2*29:0);
      out.push(`<g class="dm-tree"><ellipse cx="${tx+2}" cy="${ty+3}" rx="6" ry="4" fill="#43654925"/><circle cx="${tx}" cy="${ty}" r="5.5" fill="#8cb48a"/><circle cx="${tx-1}" cy="${ty-1}" r="3.5" fill="#a8c895"/></g>`);
    }
    out.push('</g>');
  }
  return out.join('');
}
const SCENERY=scenery();

function roads(){
  const lines=[];
  for(let col=0;col<7;col++)lines.push({x1:X+col*CELL,y1:Y-14,x2:X+col*CELL,y2:Y+4*CELL+14,major:col===3});
  for(let row=0;row<5;row++)lines.push({x1:X-14,y1:Y+row*CELL,x2:X+6*CELL+14,y2:Y+row*CELL,major:row===2});
  const line=(l,cls,color,width,extra='')=>`<line class="${cls}" x1="${l.x1}" y1="${l.y1}" x2="${l.x2}" y2="${l.y2}" stroke="${color}" stroke-width="${width}" stroke-linecap="round" ${extra}/>`;
  return lines.map(l=>line(l,'dm-road-edge','#d2d3c7',l.major?19:14)).join('')+
    lines.map(l=>line(l,'dm-road','#fffdf5',l.major?16:11)).join('')+
    lines.filter(l=>l.major).map(l=>line(l,'dm-road-center','#c7caba',1.2,'stroke-dasharray="5 8"')).join('');
}
const ROADS=roads();

/** `bare` (the clean layout, docs/UI_KIT.md): no title bar, district names or legend; a stop shows its name only where
 * something happens (you are there, a parcel waits, it is on the route); every other stop is its emoji (its name stays
 * in the pin's <title>). */
export function renderNeighborhoodMap({nodes={},at,route=[],draft=[],status={},signs=[],minutes=3,text={},bare=false}){
  const words={title:'Khu phố Mây Chiều',here:'Bạn đang ở',planned:'Tuyến đã chốt',draft:'Tuyến nháp',pick:'Điểm lấy hàng',drop:'Điểm giao hàng',residential:'Khu dân cư',services:'Khu dịch vụ',garden:'Khu nhà vườn',order:'Thứ tự điểm dừng',...text};
  const here=nodes[at],from=route.length?route[route.length-1]:at;
  const trace=(points,cls,color,dashed=false)=>points?`${dashed?'':`<polyline class="dm-route-under" points="${points}" fill="none" stroke="#fffdf5" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>`}<polyline class="${cls}" points="${points}" fill="none" stroke="${color}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round" ${dashed?'stroke-dasharray="5 7"':''}/>`:'';
  const paths=(route.length?trace(routePoints(nodes,at,route),'dm-route','#27816e'):'')+(draft.length?trace(routePoints(nodes,from,draft),'dm-draft','#bd741c',true):'');
  const sequence=[...route,...draft];
  const pins=Object.entries(nodes).filter(([,n])=>valid(n)).map(([id,n])=>{
    const [px,py]=point(n),s=status[id]||{},current=id===at;
    const numbers=sequence.flatMap((stop,i)=>stop===id?[i+1]:[]),isDraft=numbers.length&&numbers[0]>route.length;
    const color=s.drop?'#27816e':s.pick?'#517faa':'#b7bcad';
    const hazard=signs.find(g=>g.node===id),symbol=hazard?{jam:'🚦',works:'🚧',flood:'🌊'}[hazard.kind]:'';
    const label=bare&&!(current||s.pick||s.drop||numbers.length)?'':String(n.label??n.name??id),labelWidth=Math.max(32,Math.min(110,[...label].length*7.3+10));
    return `<g class="dm-pin${current?' here':''}${s.pick?' pick':''}${s.drop?' drop':''}" transform="translate(${px},${py})"><title>${esc(n.name??id)}${current?' · '+esc(words.here):''}${numbers.length?' · '+esc(words.order)+': '+numbers.join(', '):''}</title>
      ${current?'<circle class="dm-current" r="25" fill="#d4eeea" stroke="#27816e" stroke-width="2" stroke-dasharray="3 4"/>':''}
      <circle class="dm-pin-disc" r="17" fill="#fffdf8" stroke="${color}" stroke-width="${s.pick||s.drop?3:1.5}"/>
      <text class="dm-emoji" y="6" text-anchor="middle" font-size="18">${esc(n.emoji??'📍')}</text>
      ${label?`<rect class="dm-label-bg" x="${-labelWidth/2}" y="22" width="${labelWidth}" height="17" rx="5" fill="#fffdf5" fill-opacity=".94"/>
      <text class="dm-label" y="35" text-anchor="middle" font-size="13" font-weight="700" fill="#35463d" data-no-translate>${esc(label)}</text>`:''}
      ${numbers.length?`<g class="dm-stop-number${isDraft?' draft':''}" transform="translate(19,-19)"><circle r="11" fill="${isDraft?'#bd741c':'#27816e'}" stroke="#fffdf8" stroke-width="2"/><text y="4" text-anchor="middle" fill="#fff" font-size="11" font-weight="800">${numbers[0]}${numbers.length>1?'+':''}</text></g>`:''}
      ${symbol?`<text x="-29" y="-14" font-size="14">${symbol}</text>`:''}</g>`;
  }).join('');
  const districts=bare?'':[words.residential,words.services,words.garden].map((name,i)=>`<text class="dm-district-label" x="${132+i*168}" y="27" text-anchor="middle" font-size="12" font-weight="700" letter-spacing=".5" fill="#758477">${esc(name)}</text>`).join('');
  return `<figure class="dl-map${bare?' bare':''}">${bare?'':`<div class="dl-map-head"><b>${esc(words.title)}</b><span>🛵 ${esc(words.here)}: <strong>${esc(here?.name??at??'')}</strong></span></div>`}
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(words.title)} · ${esc(words.here)}: ${esc(here?.name??at??'')}"><rect class="dm-ground" width="${W}" height="${H}" fill="#f1f1e7"/>${districts}<g aria-hidden="true">${SCENERY}${ROADS}</g>${paths}${pins}<g class="dm-north" transform="translate(576,20)" aria-hidden="true"><path d="M0 0l-4 9 4-2 4 2z" fill="#758477"/><text y="22" text-anchor="middle" fill="#758477" font-size="10" font-weight="700">N</text></g></svg>
    ${bare?'':`<figcaption><div class="dl-map-legend"><span><i class="route"></i>${esc(words.planned)}</span><span><i class="draft"></i>${esc(words.draft)}</span><span><i class="pick"></i>${esc(words.pick)}</span><span><i class="drop"></i>${esc(words.drop)}</span></div><small class="muted">${esc(text.scale??`Mỗi ô phố ${minutes} phút`)}</small></figcaption>`}</figure>`;
}
