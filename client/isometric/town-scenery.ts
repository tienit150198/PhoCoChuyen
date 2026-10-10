import type Phaser from 'phaser';
import {project} from './model';
import {sampleTrailCurve} from './trail-geometry';
import {connectStreetDoors,streetProfile} from './trail-geometry';
import type {StreetDoor,StreetSample} from './trail-geometry';
import type {Navigation,Point,Rect} from './model';

export const DISTRICT_PALETTE:Record<string,{ground:number,path:number,edge:number,accent:number}>={
  brick:{ground:0xb9c795,path:0xe7be91,edge:0xc49874,accent:0xc87954},
  earth:{ground:0xa5bd83,path:0xdcc493,edge:0xaf996c,accent:0x82975a},
  stone:{ground:0xb5c797,path:0xd7d4b4,edge:0xabae8a,accent:0xd3ab8e},
  garden:{ground:0xa5c194,path:0xe7d9ae,edge:0xbdc195,accent:0xc6d5a0},
  paving:{ground:0xb9c8a6,path:0xe1d5bd,edge:0xb6bca6,accent:0xb3c4bc},
  slate:{ground:0xb1c4a4,path:0xcbd1c5,edge:0xa2b4aa,accent:0xd9d8bf},
  sandstone:{ground:0xc4cb9e,path:0xe5d1a8,edge:0xb6a386,accent:0xb4bda5},
  boardwalk:{ground:0xc9d3ab,path:0xd3b38c,edge:0xa58b6c,accent:0xb2cec0},
  promenade:{ground:0xc3cb9f,path:0xe9d3a9,edge:0xc1a47b,accent:0xb8c38e}
};
type District={id:string;material:string;bounds:Rect};
type Trail={district:string;width:number;points:Point[];sampled?:boolean};
const polygon=(g:Phaser.GameObjects.Graphics,pts:Point[],color:number,alpha=1)=>{g.fillStyle(color,alpha).fillPoints(pts.map(p=>project(p)),true);};
const floor=(g:Phaser.GameObjects.Graphics,r:Rect,color:number)=>polygon(g,[{x:r.x0,y:r.y0},{x:r.x1,y:r.y0},{x:r.x1,y:r.y1},{x:r.x0,y:r.y1}],color);
const disc=(g:Phaser.GameObjects.Graphics,p:Point,r:number,color:number,alpha=1)=>polygon(g,Array.from({length:24},(_,i)=>({x:p.x+Math.cos(i/24*Math.PI*2)*r,y:p.y+Math.sin(i/24*Math.PI*2)*r})),color,alpha);
const blend=(a:number,b:number,t:number)=>[16,8,0].reduce((color,shift)=>color|(Math.round((a>>shift&255)*(1-t)+(b>>shift&255)*t)<<shift),0);

// A shared warm stone surface runs through every neighbourhood. District character
// comes from buildings, planting and forecourts instead of overlapping road colours.
export const STREET_SURFACE={path:0xe5d4b4,edge:0xc8c4a1};
function ribbon(g:Phaser.GameObjects.Graphics,points:StreetSample[],extra:number,color:number){
  if(!points.length)return;
  const left:Point[]=[],right:Point[]=[];
  for(let i=0;i<points.length;i++){
    const p=points[i],a=points[Math.max(0,i-1)],b=points[Math.min(points.length-1,i+1)];
    const dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy)||1,r=p.radius+extra,nx=-dy/length*r,ny=dx/length*r;
    left.push({x:p.x+nx,y:p.y+ny});right.push({x:p.x-nx,y:p.y-ny});
  }
  polygon(g,[...left,...right.reverse()],color);
  // Only the two terminal caps need circles; curved joins are a continuous outline.
  disc(g,points[0],points[0].radius+extra,color);
  disc(g,points[points.length-1],points[points.length-1].radius+extra,color);
}

function doorstep(g:Phaser.GameObjects.Graphics,door:StreetDoor,index:number,extra:number,color:number){
  const points=Array.from({length:32},(_,i)=>{
    const a=i/32*Math.PI*2,r=1+.06*Math.sin(a*3+index)+.04*Math.cos(a*5-index);
    // Extend under the illustrated porch so the public doorway meets its house.
    return {x:door.at.x-.12+Math.cos(a)*(1.38+extra)*r,y:door.at.y-.6+Math.sin(a)*(1.22+extra)*r};
  });
  polygon(g,points,color);
}
/** Static geometry only: the scene flattens this into its existing viewport cache. */
export function drawNeighbourhoodGround(g:Phaser.GameObjects.Graphics,districts:District[],trails:Trail[],doors:StreetDoor[],navigation:Navigation){
  for(const d of districts){
    const p=DISTRICT_PALETTE[d.material],b=d.bounds,c={x:(b.x0+b.x1)/2,y:(b.y0+b.y1)/2};
    // Overlapping soft ground islands, never a visible rectangle enclosing a district.
    for(let i=0;i<10;i++){const a=i*2.4,r=Math.sqrt(i)*1.8,at=project({x:c.x+Math.cos(a)*r,y:c.y+Math.sin(a)*r});g.fillStyle(i%3?p.ground:blend(p.ground,p.accent,.12),.2).fillEllipse(at.x,at.y,660+(i%3)*115,330+(i%2)*75);}
  }
  const paletteFor=(_district:string)=>STREET_SURFACE;
  const branches=connectStreetDoors(trails,doors,navigation);
  const lanes=[...branches.map((branch,index)=>{
    const points=streetProfile(branch.points,.88,index),end=points[points.length-1];
    // A small flared mouth softens the wedge between a lane and the main road.
    for(const p of points){const d=Math.hypot(p.x-end.x,p.y-end.y);p.radius+=.23*Math.max(0,1-d/1.1)**2;}
    return {palette:paletteFor(branch.district),points,minor:true};
  }),...trails.map((trail,index)=>({palette:paletteFor(trail.district),points:streetProfile(sampleTrailCurve(trail.points,trail.sampled),trail.width,index),minor:false}))];
  // Draw ALL shoulders before ALL road surfaces. Drawing each complete road in
  // sequence leaves a dark transverse seam across every T/Y junction.
  for(const edge of [true,false]){
    for(const lane of lanes)ribbon(g,lane.points,edge?.13:0,edge?lane.palette.edge:lane.palette.path);
    doors.forEach((door,index)=>{const p=paletteFor(door.district);doorstep(g,door,index,edge?.09:0,edge?p.edge:p.path);});
  }
  // Sparse grains and worn patches; no repeated paving grid or extra objects.
  for(const lane of lanes){
    if(lane.minor)continue;
    for(let i=3;i<lane.points.length;i+=4){const p=project(lane.points[i]);g.fillStyle(i%3?0xffedca:lane.palette.edge,.22).fillEllipse(p.x+Math.sin(i)*15,p.y+Math.cos(i)*7,9+i%5*3,4+i%3);}
  }
  // The park has a circular sitting area, a flower meadow and a separate play lawn.
  disc(g,{x:6,y:30},2.55,0xe4d3ad);
  disc(g,{x:4,y:43},2.3,0x91b782);disc(g,{x:24,y:27.5},1.4,0xd5cbb2);
  // Vegetable terraces occupy the western garden; irregular banks leave a winding access lane.
  for(let row=0;row<3;row++){
    const r={x0:-21.8+row*.45,y0:24+row*1.7,x1:-17.6+row*.3,y1:25.3+row*1.7};floor(g,r,0x927352);
    for(let x=r.x0+.3;x<r.x1-.2;x+=.6)for(let y=r.y0+.25;y<r.y1;y+=.45){const p=project({x,y});g.fillStyle(row===2?0xe4c370:0x65874b).fillEllipse(p.x,p.y-3,15,10);g.fillStyle(row===1?0x93b15c:0xb2bf78).fillEllipse(p.x-3,p.y-5,9,7);}
  }
  // Airfield and waiting forecourt distinguish transport from a line of houses.
  floor(g,{x0:57,y0:20.6,x1:79,y1:23.7},0xa2b1a7);
  for(let x=58;x<78;x+=2.4)floor(g,{x0:x,y0:22.05,x1:x+1.2,y1:22.2},0xefeace);
  for(let y=21;y<23.5;y+=.4){floor(g,{x0:57.5,y0:y,x1:59,y1:y+.16},0xe7dfc5);floor(g,{x0:77,y0:y,x1:78.5,y1:y+.16},0xe7dfc5);}
  // A working harbour basin (off the walkable shore), quay planks and mooring stones.
  floor(g,{x0:80,y0:30,x1:87,y1:47},0x6faeb1);floor(g,{x0:79.4,y0:30,x1:80.2,y1:48},0xd0c2a1);
  for(let y=30;y<47;y+=1.4){floor(g,{x0:79.45,y0:y,x1:80.15,y1:y+.12},0xa4a98f);const p=project({x:83+Math.sin(y)*1.7,y});g.lineStyle(2,0xe3f4db,.35).lineBetween(p.x-15,p.y,p.x+17,p.y+1);}
  floor(g,{x0:78.4,y0:43.6,x1:84.2,y1:45.2},0xb6946e);
  for(let x=78.4;x<84.2;x+=.35)floor(g,{x0:x,y0:43.65,x1:x+.29,y1:45.15},0xd3b487);
}

/** Small civic props drawn once into a local texture; detailed buildings/trees stay painted WebP sprites. */
export function drawCivicProp(ctx:CanvasRenderingContext2D,kind:string){
  const c=ctx;c.lineJoin='round';c.lineCap='round';c.lineWidth=3;c.strokeStyle='#775c43';
  const poly=(p:number[][],fill:string)=>{c.beginPath();p.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=fill;c.fill();c.stroke();};
  const line=(x:number,y:number,u:number,v:number,color='#876b4d',w=4)=>{c.strokeStyle=color;c.lineWidth=w;c.beginPath();c.moveTo(x,y);c.lineTo(u,v);c.stroke();};
  const ellipse=(x:number,y:number,rx:number,ry:number,color:string)=>{c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fill();};
  ellipse(128,229,92,20,'#6f76532b');
  if(kind==='fountain'||kind==='well'){
    ellipse(128,208,94,40,'#9c997c');ellipse(128,199,94,40,'#d6c8a6');ellipse(128,196,80,30,'#72b8b3');ellipse(128,194,59,20,'#95d5c5');
    if(kind==='well'){poly([[50,130],[128,91],[211,131],[128,169]],'#ba7451');line(61,147,61,201);line(195,146,195,201);line(115,150,115,194,'#b4a584',2);poly([[105,178],[125,178],[123,195],[108,195]],'#ab8c6a');}
    else{poly([[105,181],[128,169],[150,181],[150,200],[129,214],[105,201]],'#ccbb91');ellipse(128,179,48,19,'#e1d0a7');ellipse(128,176,40,12,'#82c6bf');line(128,166,128,138,'#bcdfca',6);ellipse(128,136,9,5,'#cceadb');}
  }else if(kind==='playground'){
    line(48,104,22,213,'#bb8a5c',8);line(48,104,84,213,'#bb8a5c',8);line(186,89,159,197,'#bb8a5c',8);line(186,89,226,192,'#bb8a5c',8);line(47,103,186,89,'#ca9b65',10);
    line(91,99,93,175,'#887256',3);line(130,94,132,167,'#887256',3);poly([[86,174],[126,168],[143,177],[104,185]],'#73a795');
    poly([[163,148],[188,136],[219,192],[193,206]],'#a4b6b4');line(167,150,196,201,'#ead39c',5);line(187,139,217,190,'#ead39c',5);
  }else if(kind==='pergola'){
    for(const [x,y] of [[28,159],[131,210],[224,162],[120,111]])line(x,y-76,x,y,'#ab8156',7);
    for(let i=0;i<8;i++)line(21+i*14,80+i*7,114+i*14,127-i*6,'#c6a575',7);
    for(let i=0;i<22;i++)ellipse(34+(i*37)%176,92+(i*19)%48,10,6,['#92ae74','#729357','#a6bb7d'][i%3]);
    for(let i=0;i<7;i++)ellipse(48+i*25,117+Math.sin(i)*17,6,5,'#d39d9d');
  }else if(kind==='bike'){
    c.strokeStyle='#5e6557';c.lineWidth=7;for(const [x,y] of [[58,202],[197,202]]){c.beginPath();c.ellipse(x,y,30,32,0,0,Math.PI*2);c.stroke();}
    for(const [x,y,u,v] of [[58,202,105,190],[105,190,88,147],[58,202,88,147],[88,147,162,147],[162,147,105,190],[162,147,197,202],[162,147,169,123]])line(x,y,u,v,'#a97762',6);line(75,144,101,144,'#765c45',7);line(156,123,179,123,'#765c45',6);poly([[174,146],[213,151],[207,174],[185,171]],'#d8bd83');
  }else if(kind==='notice'){
    line(69,110,69,221,'#ac8158',9);line(187,111,187,213,'#ac8158',9);poly([[45,96],[193,78],[214,167],[65,186]],'#a47c53');poly([[57,105],[184,90],[201,156],[72,173]],'#efdeb5');
    for(let i=0;i<4;i++)poly([[77+i*29,116-i*3],[97+i*29,113-i*3],[102+i*29,150-i*3],[81+i*29,153-i*3]],['#a2b5a0','#dfa997','#dab96e','#b7c0ca'][i]);
  }else if(kind==='buoy'){
    line(120,114,120,212,'#ad9876',8);c.strokeStyle='#c9785a';c.lineWidth=18;c.beginPath();c.ellipse(130,155,33,40,-.15,0,Math.PI*2);c.stroke();line(112,119,127,118,'#f3e3be',13);line(135,194,149,190,'#f3e3be',13);
  }else{
    poly([[41,173],[118,139],[217,180],[142,221]],'#c99964');poly([[41,173],[142,215],[142,237],[41,195]],'#ae7d51');poly([[142,215],[217,180],[217,202],[142,237]],'#8c6c48');
    for(let i=0;i<18;i++)ellipse(65+(i*29)%120,172+(i*7)%29,10,7,['#a8b96f','#71934d','#d5b363','#c98862'][i%4]);
  }
}
