/** Local public rooms. Coordinates, collision and pathfinding share the same furniture layout. */
export const VENUE_IDS=['cafe','spa','cinema','karaoke','bark','salon','nails','craft','books','art','music','reading','garden','family'];
const NAMES={cafe:'Quán cà phê',spa:'Spa thư giãn',cinema:'Rạp chiếu phim',karaoke:'Phòng karaoke',bark:'Sân chơi thú cưng',salon:'Tiệm tóc',nails:'Tiệm làm móng',craft:'Góc thủ công',books:'Hiệu sách',art:'Xưởng vẽ',music:'Phòng nhạc',reading:'Thư viện',garden:'Vườn cộng đồng',family:'Góc gia đình'};
const prop=(kind,x,y,w,h,colour,label='')=>({kind,x,y,w,h,colour,label});
const station=(id,label,x,y,detail)=>({id,label,x,y,detail});
export function venueLayout(id){
  if(!VENUE_IDS.includes(id))throw new Error(`Unknown venue: ${id}`);
  const room={id,title:NAMES[id],width:460,height:360,entry:{x:230,y:325},outdoor:id==='garden',floor:'#e9d2ad',wall:'#f3e6cc',accent:'#986a47',props:[],stations:[]};
  const p=room.props,s=room.stations;
  if(id==='bark'){
    room.outdoor=true;room.floor='#c4d3a8';room.accent='#8ba572';
    p.push(prop('bench',35,40,100,32,'#ad8b62'),prop('tree',360,25,60,65,'#88a371'),prop('play',165,28,125,40,'#ddc69a'),prop('cone',65,150,24,24,'#d89461'),prop('cone',365,140,24,24,'#d89461'),prop('dog',310,210,48,32,'#b68c68'),prop('bench',45,255,85,30,'#ad8b62'));
    s.push(station('game','Kéo co chó sủa',230,115,'Chọn lượt chơi cùng các chú cún'),station('lounge','Góc chơi với cún',240,240,'Xem trò chơi dành cho thú cưng'));
  }else if(id==='cafe'){
    room.accent='#a36944';room.floor='#e7c89f';
    p.push(prop('counter',35,25,235,48,room.accent,'Quầy phục vụ'),prop('shelf',320,18,110,28,'#765d45'),prop('table',60,130,65,55,'#c38e58'),prop('table',295,140,68,55,'#c38e58'),prop('chair',70,215,42,36,'#8aab8b'),prop('sofa',305,230,110,40,room.accent));
    s.push(station('counter','Gọi món',185,100,'Xem đồ uống và món tại quầy'),station('lounge','Góc trò chuyện',280,240,'Chọn hoạt động tại quán'));
  }else if(id==='cinema'){
    room.floor='#aaa5bb';room.wall='#c9c1d9';room.accent='#78628a';
    p.push(prop('screen',110,16,240,22,'#e5eef2','Màn ảnh'),prop('counter',365,250,65,45,'#977354','Vé & bắp'));
    for(const y of [100,180])for(const x of [65,135,280,350])p.push(prop('seat',x,y,42,40,'#a45967'));
    s.push(station('screen','Chọn phim',230,90,'Xem lịch chiếu và vé phim'),station('tickets','Quầy vé',330,280,'Chọn suất chiếu'));
  }else if(['spa','salon','nails'].includes(id)){
    room.accent=id==='spa'?'#7c9a85':id==='salon'?'#b78363':'#c88d9e';room.floor='#eaded0';
    p.push(prop('counter',35,25,140,40,room.accent,'Tiếp đón'),prop('shelf',325,20,95,24,'#b99070'),prop('plant',390,280,35,35,'#718e65'));
    if(id==='spa')p.push(prop('bed',60,140,70,105,'#bacfb8'),prop('bed',285,140,70,105,'#bacfb8'),prop('table',365,145,42,42,'#af8467'));
    else if(id==='salon')p.push(prop('mirror',240,35,65,25,'#b8d2ce'),prop('chair',255,100,55,55,'#ad806b'),prop('mirror',65,160,65,25,'#b8d2ce'),prop('chair',75,225,55,50,'#ad806b'));
    else p.push(prop('table',70,150,90,45,'#ddb1bb'),prop('chair',85,230,45,36,'#b48c9f'),prop('table',280,145,90,45,'#ddb1bb'),prop('chair',290,225,45,36,'#b48c9f'));
    s.push(station('reception','Chọn dịch vụ',190,85,'Xem dịch vụ và giá trước khi chọn'),station('care',id==='spa'?'Góc thư giãn':id==='salon'?'Ghế tạo kiểu':'Bàn làm móng',220,200,'Chọn dịch vụ chăm sóc'));
  }else if(['karaoke','music'].includes(id)){
    room.floor='#c9bfda';room.wall='#e6ddec';room.accent='#8b79a3';
    p.push(prop('screen',120,15,210,22,'#dce4ec',id==='karaoke'?'Sân khấu':'Phòng tập'),prop('speaker',40,45,40,42,'#5c596b'),prop('speaker',375,45,40,42,'#5c596b'),prop('sofa',45,200,130,42,'#a58cad'),prop('sofa',295,200,120,42,'#a58cad'),prop('table',195,245,60,38,'#c7a37d'),prop('piano',290,115,115,42,'#655d6a'));
    s.push(station('stage',id==='karaoke'?'Chọn bài hát':'Chơi nhạc',230,100,'Mở hoạt động âm nhạc'),station('lounge','Góc nghỉ',230,200,'Xem hoạt động trong phòng'));
  }else if(['books','reading'].includes(id)){
    room.accent='#79907b';room.floor='#d6c8a9';
    p.push(prop('shelf',30,20,160,26,'#937253'),prop('shelf',270,20,160,26,'#937253'),prop('shelf',30,125,45,100,'#937253'),prop('shelf',380,125,45,100,'#937253'),prop('table',155,130,140,58,'#b8956c'),prop('chair',160,220,42,38,'#8b9d7e'),prop('chair',260,220,42,38,'#8b9d7e'));
    s.push(station('books',id==='books'?'Chọn sách':'Tìm sách',230,80,'Xem các lựa chọn sách'),station('reading','Góc đọc sách',230,220,'Chọn hoạt động đọc sách'));
  }else if(['art','craft'].includes(id)){
    room.accent=id==='art'?'#ba8364':'#729c9c';
    p.push(prop('shelf',30,20,145,26,'#ab8058'),prop('shelf',290,20,140,26,'#ab8058'),prop('easel',60,120,55,60,'#ddb67b'),prop('easel',340,130,55,60,'#ddb67b'),prop('table',170,140,120,62,'#c99562'),prop('chair',180,250,38,32,'#c28b7f'),prop('chair',260,250,38,32,'#8ea995'));
    s.push(station('workshop',id==='art'?'Bàn vẽ':'Bàn thủ công',230,110,'Chọn buổi sáng tạo'),station('gallery','Góc trưng bày',110,230,'Xem hoạt động sáng tạo'));
  }else if(id==='garden'){
    room.floor='#b7cc94';room.wall='#dce6c9';room.accent='#75995a';
    p.push(prop('tree',35,30,70,70,'#699b67'),prop('tree',355,25,70,70,'#789c5b'),prop('flowerbed',140,40,150,50,'#c08b73'),prop('flowerbed',45,180,70,70,'#c18c6d'),prop('flowerbed',335,180,70,70,'#b7986a'),prop('bench',145,245,70,35,'#a08360'),prop('bench',265,245,70,35,'#a08360'));
    s.push(station('garden','Chăm vườn',225,125,'Chọn hoạt động ngoài trời'),station('rest','Góc nghỉ',245,235,'Dừng chân ở khu vườn'));
  }else{
    room.floor='#e9d6bb';room.accent='#c58e79';
    p.push(prop('sofa',35,35,135,45,'#bc9d87'),prop('shelf',315,20,110,28,'#a5b092'),prop('table',65,155,90,55,'#c8a077'),prop('chair',85,245,42,38,'#89a6a0'),prop('play',295,155,110,80,'#d8b287'),prop('plant',385,280,35,35,'#80976d'));
    s.push(station('family','Sinh hoạt gia đình',220,110,'Chọn hoạt động gia đình'),station('play','Góc vui chơi',250,220,'Xem hoạt động chung'));
  }
  if(!room.outdoor)p.push(prop('plant',22,295,32,32,'#759365'));
  return room;
}
export const projectVenue=({x,y})=>({x:320+(x-y)*.67,y:76+(x+y)*.38});
export const unprojectVenue=({x,y})=>({x:((x-320)/.67+(y-76)/.38)/2,y:((y-76)/.38-(x-320)/.67)/2});
export function walkableVenue(room,x,y,radius=9){
  if(!Number.isFinite(x)||!Number.isFinite(y)||x<radius||y<radius||x>room.width-radius||y>room.height-radius)return false;
  return !room.props.some(p=>p.solid!==false&&x>p.x-radius&&x<p.x+p.w+radius&&y>p.y-radius&&y<p.y+p.h+radius);
}
function clearSegment(room,a,b){const n=Math.ceil(Math.hypot(b.x-a.x,b.y-a.y)/4);for(let i=1;i<=n;i++)if(!walkableVenue(room,a.x+(b.x-a.x)*i/n,a.y+(b.y-a.y)*i/n))return false;return true;}
/** Breadth-first routing on this small room grid; final legs are collision checked too. */
export function venuePath(room,from,to){
  if(!walkableVenue(room,to.x,to.y))return [];
  if(clearSegment(room,from,to))return [{x:to.x,y:to.y}];
  const size=10,key=(x,y)=>`${x},${y}`,base={x:Math.floor(from.x/size)*size,y:Math.floor(from.y/size)*size};
  // A rounded node can lie behind an inflated furniture corner. Connect every clear
  // neighboring node so a valid keyboard position never becomes a pathfinding dead end.
  const queue=[],seen=new Map();let end=null;
  for(let ix=-1;ix<=2;ix++)for(let iy=-1;iy<=2;iy++){const start={x:base.x+ix*size,y:base.y+iy*size};if(walkableVenue(room,start.x,start.y)&&clearSegment(room,from,start)){queue.push(start);seen.set(key(start.x,start.y),null);}}
  queue.sort((a,b)=>Math.hypot(a.x-from.x,a.y-from.y)-Math.hypot(b.x-from.x,b.y-from.y));
  for(let i=0;i<queue.length;i++){
    const node=queue[i];if(Math.hypot(node.x-to.x,node.y-to.y)<20&&clearSegment(room,node,to)){end=node;break;}
    for(const [dx,dy] of [[size,0],[-size,0],[0,size],[0,-size]]){const n={x:node.x+dx,y:node.y+dy},k=key(n.x,n.y);if(seen.has(k)||!walkableVenue(room,n.x,n.y)||!clearSegment(room,node,n))continue;seen.set(k,node);queue.push(n);}
  }
  if(!end)return [];
  const path=[{x:to.x,y:to.y}];while(end){path.unshift(end);end=seen.get(key(end.x,end.y));}return path;
}
export function createVenueWalk(room,{onInteract=()=>{},onExit=()=>{}}={}){
  const state={...room.entry,direction:'ne',moving:false,suspended:false,destroyed:false};let vector={x:0,y:0},path=[];
  const reset=()=>{vector={x:0,y:0};path=[];state.moving=false;};
  const nearby=()=>room.stations.find(s=>Math.hypot(s.x-state.x,s.y-state.y)<38)||null;
  return {state,room,nearby,
    setInput(x,y){if(state.destroyed||state.suspended)return;path=[];const n=Math.hypot(x,y);vector=Number.isFinite(n)?{x:x/Math.max(1,n),y:y/Math.max(1,n)}:{x:0,y:0};},
    goTo(point){if(state.destroyed||state.suspended)return false;vector={x:0,y:0};path=venuePath(room,state,point);return !!path.length;},
    step(dt){
      if(state.destroyed||state.suspended)return;
      let dx=vector.x,dy=vector.y,speed=94*Math.min(.05,Math.max(0,Number(dt)||0));
      if(path.length){const t=path[0],d=Math.hypot(t.x-state.x,t.y-state.y);if(d<=speed){state.x=t.x;state.y=t.y;path.shift();state.moving=!!path.length;return;}dx=(t.x-state.x)/d;dy=(t.y-state.y)/d;}
      const old={x:state.x,y:state.y};if(walkableVenue(room,state.x+dx*speed,state.y))state.x+=dx*speed;if(walkableVenue(room,state.x,state.y+dy*speed))state.y+=dy*speed;
      state.moving=Math.hypot(state.x-old.x,state.y-old.y)>.01;
      if(state.moving){const screenX=dx-dy,screenY=dx+dy;state.direction=screenY<0?(screenX<0?'nw':'ne'):(screenX<0?'sw':'se');}
    },
    interact(id){if(state.destroyed||state.suspended)return false;const s=id?room.stations.find(s=>s.id===id):nearby();if(!s||Math.hypot(s.x-state.x,s.y-state.y)>=38)return false;reset();onInteract(s);return true;},
    exit(){if(state.destroyed||state.suspended||Math.hypot(state.x-room.entry.x,state.y-room.entry.y)>38)return false;reset();onExit();return true;},
    needsFrame:()=>!state.destroyed&&!state.suspended&&!!(vector.x||vector.y||path.length),reset,
    suspend(){reset();state.suspended=true;},resume(){if(!state.destroyed){reset();state.suspended=false;}},destroy(){reset();state.destroyed=true;state.suspended=true;}
  };
}

function polygon(c,points,fill,stroke='#927c6255'){c.beginPath();points.forEach((p,i)=>i?c.lineTo(p.x,p.y):c.moveTo(p.x,p.y));c.closePath();c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=1;c.stroke();}}
function slab(c,p,z,colour){const a=projectVenue(p),b=projectVenue({x:p.x+p.w,y:p.y}),d=projectVenue({x:p.x,y:p.y+p.h}),e=projectVenue({x:p.x+p.w,y:p.y+p.h}),lift=q=>({x:q.x,y:q.y-z});polygon(c,[d,e,lift(e),lift(d)],colour);polygon(c,[b,e,lift(e),lift(b)],colour);c.fillStyle='#00000018';c.beginPath();c.moveTo(b.x,b.y);c.lineTo(e.x,e.y);c.lineTo(e.x,e.y-z);c.lineTo(b.x,b.y-z);c.fill();polygon(c,[lift(a),lift(b),lift(e),lift(d)],colour);return {a,b,d,e};}
function dot(c,x,y,r,colour){c.fillStyle=colour;c.beginPath();c.ellipse(x,y,r,r*.76,0,0,Math.PI*2);c.fill();}
function furniture(c,p){
  const center=projectVenue({x:p.x+p.w/2,y:p.y+p.h/2}),z=({shelf:52,counter:35,table:27,bed:22,sofa:21,chair:20,seat:20,bench:19,piano:30,screen:70,mirror:65,easel:55,speaker:48,flowerbed:9,play:8,plant:13,tree:16})[p.kind]||25;
  if(p.kind==='dog'){dot(c,center.x,center.y,18,'#73613b22');dot(c,center.x,center.y-14,15,p.colour);dot(c,center.x+12,center.y-26,12,p.colour);dot(c,center.x+7,center.y-30,6,'#795d49');dot(c,center.x+20,center.y-22,6,'#e2c6a0');dot(c,center.x+23,center.y-23,2,'#514a43');dot(c,center.x+15,center.y-29,1.5,'#514a43');c.strokeStyle=p.colour;c.lineWidth=5;c.beginPath();c.moveTo(center.x-12,center.y-18);c.lineTo(center.x-22,center.y-28);c.stroke();for(const x of [-8,7]){c.fillStyle=p.colour;c.fillRect(center.x+x,center.y-9,5,11);}return;}
  if(p.kind==='cone'){dot(c,center.x,center.y,12,'#efd7af');polygon(c,[{x:center.x-9,y:center.y},{x:center.x,y:center.y-26},{x:center.x+9,y:center.y}],p.colour);c.strokeStyle='#fff2ce';c.lineWidth=4;c.beginPath();c.moveTo(center.x-4,center.y-11);c.lineTo(center.x+4,center.y-11);c.stroke();return;}
  const shape=slab(c,p,z,p.colour);
  if(p.kind==='machine'){const q=shape.d;c.strokeStyle='#576979';c.lineWidth=3;c.beginPath();c.ellipse(q.x+16,q.y-14,10,11,0,0,Math.PI*2);c.stroke();c.fillStyle='#dbe6e8';c.fill();c.fillStyle='#4f6d65';c.fillRect(q.x+8,q.y-31,7,3);}
  if(['chair','seat','sofa','bench'].includes(p.kind)){slab(c,{...p,h:8},z+18,p.colour);if(p.kind==='sofa'){slab(c,{...p,w:8},z+10,p.colour);slab(c,{...p,x:p.x+p.w-8,w:8},z+10,p.colour);}}
  if(p.kind==='bed'){slab(c,{...p,x:p.x+5,y:p.y+5,w:p.w-10,h:25},z+3,'#fff8e6');slab(c,{...p,y:p.y+45,h:p.h-45},z+2,'#93af9c');}
  if(['shelf','counter'].includes(p.kind)){for(let i=0;i<Math.floor(p.w/15);i++){const q=projectVenue({x:p.x+8+i*15,y:p.y+8});c.fillStyle=['#cb9371','#8dada3','#d2bc82','#a69aba'][i%4];c.fillRect(q.x-3,q.y-z-10,6,13);}if(p.kind==='counter'){const q=projectVenue({x:p.x+p.w-25,y:p.y+p.h/2});c.fillStyle='#f3e4c9';c.fillRect(q.x-9,q.y-z-6,18,8);}}
  if(['screen','mirror','easel'].includes(p.kind)){const a=shape.d,e=shape.e;polygon(c,[{x:a.x+4,y:a.y-z+5},{x:e.x-4,y:e.y-z+5},{x:e.x-4,y:e.y-12},{x:a.x+4,y:a.y-12}],p.kind==='mirror'?'#b9d4d6':'#f1eee1');if(p.kind==='screen'){c.fillStyle='#aaa6ba';c.font='bold 12px sans-serif';c.textAlign='center';c.fillText('✦',center.x,center.y-z/2);}if(p.kind==='easel'){dot(c,center.x,center.y-30,9,'#a7bba0');dot(c,center.x+5,center.y-23,6,'#dd9a76');}}
  if(p.kind==='piano'){const a=projectVenue({x:p.x+5,y:p.y+p.h-12});for(let i=0;i<12;i++){c.fillStyle=i%3?'#f2ecda':'#353644';c.fillRect(a.x+i*5,a.y-27+i*2.8,4,9);}}
  if(p.kind==='speaker'){dot(c,center.x,center.y-33,10,'#343947');dot(c,center.x,center.y-15,7,'#343947');}
  if(['plant','tree'].includes(p.kind)){c.fillStyle='#8b7050';c.fillRect(center.x-3,center.y-z-22,6,24);const size=p.kind==='tree'?27:14;dot(c,center.x,center.y-z-23,size,p.colour);dot(c,center.x-size*.6,center.y-z-17,size*.65,'#88a878');dot(c,center.x+size*.55,center.y-z-25,size*.65,'#92b080');}
  if(p.kind==='flowerbed')for(let i=0;i<8;i++){const q=projectVenue({x:p.x+10+(i%4)*(p.w-20)/3,y:p.y+10+Math.floor(i/4)*(p.h-20)});dot(c,q.x,q.y-z-2,5,'#91a676');dot(c,q.x,q.y-z-6,3,['#e6a18d','#f3d99a','#bd9eca'][i%3]);}
  if(p.kind==='table'){slab(c,{x:p.x+9,y:p.y+9,w:13,h:14},z+2,'#eee9ce');const q=projectVenue({x:p.x+p.w-12,y:p.y+12});dot(c,q.x,q.y-z-2,4,'#f3e8d0');}
  if(p.kind==='play')for(let i=0;i<5;i++)slab(c,{x:p.x+10+i*15,y:p.y+15+(i%2)*22,w:14,h:14},15,['#afc3b2','#d29985','#e3c77d'][i%3]);
}
/** Rendering is retained-mode only at the wrapper level: this scene owns no listeners or animation. */
export function renderVenue(canvas,room,state,{avatar,time=0,translate=text=>text,peers=[],bubbles=[]}={}){
  const c=canvas.getContext('2d');if(!c)return;c.clearRect(0,0,640,470);c.fillStyle=room.outdoor?'#edf1df':'#f7f0e4';c.fillRect(0,0,640,470);
  const a=projectVenue({x:0,y:0}),b=projectVenue({x:room.width,y:0}),d=projectVenue({x:0,y:room.height}),e=projectVenue({x:room.width,y:room.height});
  if(!room.outdoor){polygon(c,[{x:a.x,y:a.y-61},{x:b.x,y:b.y-61},b,a],room.wall);polygon(c,[{x:d.x,y:d.y-61},{x:a.x,y:a.y-61},a,d],'#dfd0b6');}
  polygon(c,[a,b,e,d],room.floor);for(let x=0;x<=room.width;x+=40){const p=projectVenue({x,y:0}),q=projectVenue({x,y:room.height});c.strokeStyle=room.outdoor?'#ffffff10':'#9c7e5320';c.beginPath();c.moveTo(p.x,p.y);c.lineTo(q.x,q.y);c.stroke();}
  if(room.outdoor){polygon(c,[projectVenue({x:205,y:10}),projectVenue({x:250,y:10}),projectVenue({x:250,y:350}),projectVenue({x:205,y:350})],'#e1d7ae');}
  slab(c,{x:room.entry.x-30,y:room.height-12,w:60,h:12},3,'#b99f77');
  const entrance=projectVenue(room.entry);c.strokeStyle='#846c4d';c.lineWidth=2;c.beginPath();c.ellipse(entrance.x,entrance.y,24,12,0,0,Math.PI*2);c.stroke();c.fillStyle='#645d49';c.font='bold 11px sans-serif';c.textAlign='center';c.fillText(translate('LỐI RA'),entrance.x,entrance.y+27);
  for(const s of room.stations){const q=projectVenue(s),near=Math.hypot(s.x-state.x,s.y-state.y)<38;c.fillStyle=near?'#b6bc7caa':'#fffbe580';c.beginPath();c.ellipse(q.x,q.y,18,9,0,0,Math.PI*2);c.fill();}
  const items=[...room.props.map(p=>({depth:p.x+p.y+(p.w+p.h)/2,paint:()=>furniture(c,p)})),{depth:state.x+state.y,paint(){const q=projectVenue(state);dot(c,q.x,q.y,12,'#5544382b');const stamp=avatar?.(state.direction,state.moving?(Math.floor(time/150)%3):0);if(stamp)c.drawImage(stamp.canvas||stamp,q.x-24,q.y-61,48,64);else{dot(c,q.x,q.y-40,10,'#e9c5a3');c.fillStyle='#8aaa9b';c.fillRect(q.x-9,q.y-31,18,25);}}}];items.sort((a,b)=>a.depth-b.depth).forEach(item=>item.paint());
  for(const actor of [...(room.actors||[]),...peers.map(p=>({...p,colour:'#7e9dc2'}))]){const q=projectVenue(actor);dot(c,q.x,q.y,10,'#5544382b');dot(c,q.x,q.y-33,8,'#e9c5a3');c.fillStyle=actor.colour||'#8aaa9b';c.fillRect(q.x-7,q.y-25,14,20);c.font='600 10px sans-serif';c.textAlign='center';c.fillStyle='#494f43';c.fillText(actor.name||'',q.x,q.y-46);}
  for(const s of room.stations){const q=projectVenue(s),near=Math.hypot(s.x-state.x,s.y-state.y)<38,label=translate(s.label);c.font='600 12px sans-serif';c.textAlign='center';const w=c.measureText(label).width+16;c.fillStyle=near?'#445747':'#fffcf0ee';c.beginPath();c.roundRect(q.x-w/2,q.y+11,w,22,7);c.fill();c.fillStyle=near?'#fff8e7':'#5a574b';c.fillText(label,q.x,q.y+26);}
  const placedBubbles=[];
  for(const bubble of bubbles){
    if(!Number.isFinite(bubble.x)||!Number.isFinite(bubble.y)||typeof bubble.text!=='string')continue;
    const q=projectVenue(bubble),lines=[];let line='';c.save();c.font='600 12px sans-serif';c.textAlign='center';
    for(const word of bubble.text.slice(0,120).match(/\S{1,24}/gu)||[]){const next=line?line+' '+word:word;if(line&&c.measureText(next).width>190){lines.push(line);line=word;}else line=next;}if(line)lines.push(line);
    if(!lines.length){c.restore();continue;}
    const visible=lines.slice(0,4),width=Math.max(38,...visible.map(text=>c.measureText(text).width+20)),height=visible.length*16+12,x=Math.max(width/2+8,Math.min(632-width/2,q.x));let y=Math.max(8,q.y-67-height);
    for(let n=0;n<placedBubbles.length;n++){const hit=placedBubbles.find(r=>Math.abs(x-r.x)<(width+r.width)/2+4&&y<r.y+r.height+4&&y+height+4>r.y);if(!hit)break;const above=Math.max(8,hit.y-height-5);if(above===y)break;y=above;}placedBubbles.push({x,y,width,height});
    c.fillStyle='#fffdf3';c.strokeStyle='#a99a7f';c.lineWidth=1;c.beginPath();c.roundRect(x-width/2,y,width,height,9);c.fill();c.stroke();
    polygon(c,[{x:q.x-5,y:y+height-1},{x:q.x+5,y:y+height-1},{x:q.x,y:y+height+6}],'#fffdf3');
    c.fillStyle='#3f4c3b';visible.forEach((text,i)=>c.fillText(text,x,y+18+i*16));c.restore();
  }

}
