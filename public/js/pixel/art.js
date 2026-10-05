/** Native pixel artwork: integer cells, limited palettes and reusable stamps. No network textures. */
const INK='#343b35',CREAM='#fff0ce';
const cache=new Map(),MAX_CACHE=192;
const tints={den:'#3a3436',nau:'#8a5a3c',vang:'#e0b43f',bac:'#c7ccd4',hong:'#f4b0c4',do:'#d2453d',dao:'#f6a882',mint:'#8fd5c0',navy:'#3a4e7c',lavender:'#bba6e2',trang:'#f8f4ec'};
const hair={mau_nau:'#624331',mau_den:'#302d32',mau_mat_ong:'#ad793c',mau_hong:'#d98fa3',mau_xanh_khoi:'#6f8ea8',mau_bach_kim:'#e3d5b8'};
const skins={da_sang:'#f5cfae',da_hong:'#f8d8c6',da_trung:'#e3b389',da_ngam:'#c48d64'};
const tops={ao_thun_kem:'#efdfc4',ao_thun_xanh:'#9cc39a',ao_so_mi:'#f7f4ec',ao_len:'#c9806a',ao_hoodie:'#9d8cc4',ao_dai:'#5d9ea0',ao_chi_may:'#e7a0a8',ao_hoa:'#7cc0c8',ao_vest:'#56627a',ao_cuoi:'#c8453c',vest_cuoi:'#3e4a5c',dam_cong_chua:'#c3a4df',dam_du_tiec:'#395c81',dam_yem:'#c68468'};
const bottoms={quan_kem:'#f0d3b8',quan_xam:'#6f6a78',quan_jean:'#5b7ea6',quan_short:'#c9a978',vay_xoe:'#e39ab0',vay_dai:'#9fb7d8'};
const shoes={giay_nau:'#785c51',dep_lao:'#5b8fc0',giay_trang:'#f4f1ea',giay_do:'#c9514a',bot_den:'#3d3533'};
export function shade(hex,amount){const h=/^#[0-9a-f]{6}$/i.test(hex)?hex:'#8ba77a';return '#'+[1,3,5].map(i=>Math.max(0,Math.min(255,parseInt(h.slice(i,i+2),16)+amount)).toString(16).padStart(2,'0')).join('');}
function pen(width,height){
  const pixels=[];
  const R=(x,y,w,h,c)=>{x=Math.round(x);y=Math.round(y);w=Math.round(w);h=Math.round(h);if(w>0&&h>0)pixels.push({x,y,w,h,c});};
  const P=(points,c)=>{let minY=Math.floor(Math.min(...points.map(p=>p[1]))),maxY=Math.ceil(Math.max(...points.map(p=>p[1])));for(let y=minY;y<maxY;y++){const xs=[];for(let i=0;i<points.length;i++){const a=points[i],b=points[(i+1)%points.length];if((a[1]<=y+.5&&b[1]>y+.5)||(b[1]<=y+.5&&a[1]>y+.5))xs.push(a[0]+(y+.5-a[1])*(b[0]-a[0])/(b[1]-a[1]));}xs.sort((a,b)=>a-b);for(let i=0;i<xs.length;i+=2)R(Math.ceil(xs[i]-.5),y,Math.ceil(xs[i+1]-.5)-Math.ceil(xs[i]-.5),1,c);}};
  const box=(x,y,w,h,c)=>{R(x,y,w,h,INK);R(x+1,y+1,w-2,h-2,c);};
  return {width,height,pixels,R,P,box};
}
const chosen=(look,slot,base)=>tints[look?.tint?.[look[slot]]]||base;
/** Walk cycle is four inexpensive static poses; no continuous vector painting. */
export function pixelCharacterData(options={}){
  const look=options.look||{},gender=options.gender==='female'?'female':'male',direction=['se','sw','ne','nw'].includes(options.direction)?options.direction:'se',step=options.walkFrame===2?3:options.walkFrame===1?1:Math.abs(Math.trunc(options.step||0))%4;
  const back=direction==='nw'||direction==='ne',left=direction==='sw'||direction==='nw',flip=left?-1:1;
  const p=pen(48,64),{R,P,box}=p;
  const hc=hair[look.shade]||hair.mau_nau,skin=skins[look.skin]||skins.da_sang,tc=look.uniform&&options.uniformColor?options.uniformColor:chosen(look,'top',tops[look.top]||(gender==='female'?'#e39a8a':'#78a3b6')),bc=chosen(look,'bottom',bottoms[look.bottom]||'#6f6a78'),sc=chosen(look,'shoes',shoes[look.shoes]||shoes.giay_nau);
  const ha=look.hair||(gender==='female'?'toc_bui':'toc_ngan'),dress=String(look.top).startsWith('dam_'),skirt=dress||String(look.bottom).startsWith('vay_'),frontX=23+(left?-2:2),swing=step===1?2:step===3?-2:0;
  R(12,60,24,2,'#6c8060');R(16,62,16,1,'#91a879');
  // Long hairstyles are separate from the head and remain visible from behind.
  if(['toc_dai','toc_bob','toc_duoi_ngua','toc_bui_thap'].includes(ha)){box(12+(back?2:0),21,23,25,hc);R(14,22,3,21,shade(hc,15));}
  box(16,47+swing,7,12,bc);box(25,47-swing,7,12,bc);R(17,48+swing,2,8,shade(bc,23));R(26,48-swing,2,8,shade(bc,23));
  if(look.bottom==='quan_short'){R(17,53+swing,5,6,skin);R(26,53-swing,5,6,skin);}
  box(14+flip,57+swing,10,5,sc);box(24+flip,57-swing,10,5,sc);R(15+flip,58+swing,6,1,shade(sc,26));R(25+flip,58-swing,6,1,shade(sc,26));
  P([[15,32],[31,32],[36,38],[34,50],[14,50],[12,38]],INK);P([[16,33],[30,33],[34,38],[32,49],[16,49],[14,38]],tc);R(17,35,4,12,shade(tc,20));R(29,38,3,11,shade(tc,-26));
  if(skirt||look.top==='ao_dai'||look.top==='ao_cuoi'){const col=dress?tc:bc;P([[15,44],[33,44],[38,57],[11,57]],INK);P([[16,45],[32,45],[36,56],[13,56]],col);R(17,46,3,9,shade(col,22));R(29,47,2,9,shade(col,-20));}
  box(10,38-swing,5,12,skin);box(33,38+swing,5,12,skin);R(11,39-swing,2,6,shade(skin,10));R(34,39+swing,2,6,shade(skin,10));
  // Stepped head contour and three shade bands produce depth without shaders.
  P([[17,10],[31,10],[37,15],[39,25],[37,31],[31,36],[18,36],[11,31],[9,25],[11,16]],INK);
  P([[18,11],[30,11],[36,16],[38,25],[36,30],[30,35],[18,35],[12,30],[10,24],[12,17]],back?hc:skin);
  if(!back){R(left?11:33,20,4,9,shade(skin,-24));R(left?16:30,30,5,3,'#e5978a');R(frontX-6,22,3,5,INK);R(frontX+5,21,3,5,INK);R(frontX-6,22,1,2,CREAM);R(frontX+5,21,1,2,CREAM);R(frontX-1,30,4,1,'#ac7154');}
  P([[12,13],[17,7],[29,6],[35,9],[39,16],[37,22],[31,15],[24,18],[18,15],[12,23]],hc);R(17,9,10,2,shade(hc,24));R(13,12,7,3,shade(hc,14));R(32,12,4,7,shade(hc,-18));
  if(back){R(13,22,22,8,hc);R(16,30,17,3,shade(hc,-17));R(16,16,4,8,shade(hc,12));}
  if(ha.includes('bui')){const buns=ha==='toc_bui_doi'?[12,34]:[ha==='toc_bui_thap'?(left?13:33):25];for(const bx of buns){box(bx-5,ha==='toc_bui_thap'?25:2,10,9,hc);R(bx-3,ha==='toc_bui_thap'?26:3,5,2,shade(hc,24));}}
  if(ha==='toc_duoi_ngua'){box(left?6:35,16,7,20,hc);R(left?7:36,17,2,16,shade(hc,20));R(left?8:36,16,5,2,'#df8b9c');}
  if(ha==='toc_xoan')for(const [x,y] of [[10,11],[17,6],[26,5],[33,9],[35,19],[10,22]])box(x,y,7,6,hc);
  const detail=shade(tc,-28);
  if(!back){if(['ao_so_mi','ao_vest','vest_cuoi'].includes(look.top)){P([[18,35],[24,40],[30,35]],CREAM);R(23,39,2,7,look.top==='ao_so_mi'?detail:'#bd6d58');}else if(look.top==='ao_hoodie'){R(18,35,12,2,detail);R(21,37,1,6,CREAM);R(27,37,1,6,CREAM);}else if(look.top==='ao_len'){R(16,41,17,2,detail);R(16,46,17,2,detail);}else if(look.top==='ao_hoa'){for(const [x,y] of [[18,38],[28,42],[20,47]]){R(x,y,3,1,CREAM);R(x+1,y-1,1,3,CREAM);}}else if(look.top==='dam_yem'){R(18,34,2,13,detail);R(29,34,2,13,detail);R(20,42,9,5,detail);}}
  const acc=look.acc||'pk_khong',ac=chosen(look,'acc',acc==='non_la'?'#ecd394':acc==='mu_len'?'#d8736a':'#b07a4f');
  if(acc==='non_la'){P([[4,16],[24,1],[44,16],[40,20],[9,20]],INK);P([[6,16],[24,3],[42,16],[39,18],[10,18]],ac);R(15,12,18,1,shade(ac,-27));R(10,16,27,1,shade(ac,20));}
  if(acc==='mu_len'){P([[11,17],[12,8],[18,3],[31,3],[37,9],[38,17]],ac);box(10,16,29,5,shade(ac,-30));box(22,0,6,6,shade(ac,28));}
  if(acc==='no_toc'){box(left?9:32,7,8,5,ac);R(left?12:35,8,2,3,shade(ac,-30));}
  if(!back&&['kinh_tron','kinh_ram'].includes(acc)){const dark=acc==='kinh_ram'?ac:INK;box(frontX-8,20,7,7,dark);box(frontX+3,19,7,7,dark);if(acc==='kinh_tron'){R(frontX-7,21,5,5,skin);R(frontX+4,20,5,5,skin);R(frontX-6,22,2,3,INK);R(frontX+5,21,2,3,INK);}R(frontX-1,22,4,1,INK);}
  if(acc==='tui_cheo'){P([[15,35],[17,34],[34,46],[33,48]],shade(ac,-25));box(29,43,9,9,ac);R(30,44,7,2,shade(ac,25));}
  return p;
}
function canvasOf(data){const canvas=document.createElement('canvas');canvas.width=data.width;canvas.height=data.height;const ctx=canvas.getContext('2d');ctx.imageSmoothingEnabled=false;for(const p of data.pixels){ctx.fillStyle=p.c;ctx.fillRect(p.x,p.y,p.w,p.h);}return canvas;}
function cached(key,create){if(cache.has(key))return cache.get(key);const value=create();cache.set(key,value);while(cache.size>MAX_CACHE)cache.delete(cache.keys().next().value);return value;}
export function getPixelCharacter(options={}){const key='char:'+JSON.stringify([options.look,options.gender,options.direction,options.uniformColor,options.walkFrame,Math.abs(Math.trunc(options.step||0))%4]);return cached(key,()=>{const data=pixelCharacterData(options);return {canvas:canvasOf(data),width:data.width,height:data.height,ready:true};});}
export function pixelSVG(data,{width=data.width,height=data.height,label=''}={}){const safe=String(label).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));return `<svg class="pixel-art" width="${width}" height="${height}" viewBox="0 0 ${data.width} ${data.height}" shape-rendering="crispEdges" ${label?`role="img" aria-label="${safe}"`:'aria-hidden="true"'}>${data.pixels.map(p=>`<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" fill="${p.c}"/>`).join('')}</svg>`;}
export function pixelAssetData(kind,variant=0){
  const p=pen(128,128),{R,P,box}=p,seed=Number.isFinite(Number(variant))?Math.abs(Math.trunc(Number(variant))):0;
  const wall=['#edce98','#e8dfb5','#ccddc0'][seed%3],roof=['#c66043','#608374','#7191a2'][seed%3];
  if(['grocery','cafe','home'].includes(kind)){
    P([[9,91],[64,121],[118,92],[66,66]],'#6e9266');
    P([[15,54],[62,78],[62,113],[15,88]],shade(wall,-28));P([[62,78],[112,53],[112,88],[62,113]],wall);
    P([[9,53],[59,24],[119,54],[64,85]],INK);P([[12,52],[59,27],[115,54],[64,81]],roof);
    for(let row=0;row<5;row++)for(let col=0;col<6;col++){const x=16+col*9+row*4,y=51-col*4+row*4;R(x,y,7,2,shade(roof,row%2?16:-15));}
    P([[63,84],[114,59],[114,66],[63,93]],shade(roof,-22));
    if(kind==='home'){P([[78,84],[94,76],[94,100],[78,109]],INK);P([[80,85],[92,79],[92,99],[80,106]],'#749295');R(82,88,2,9,'#bddcbb');P([[22,65],[41,75],[41,91],[22,81]],INK);P([[24,68],[39,76],[39,87],[24,80]],'#7697a1');R(29,72,2,10,CREAM);}
    else {P([[67,91],[108,70],[108,89],[67,110]],INK);P([[70,92],[105,75],[105,89],[70,107]],'#b88149');for(let i=0;i<7;i++){const x=73+i*4,y=98-i*2;R(x,y,3,5,['#bd4f44','#7cac7a','#f3d377'][i%3]);}P([[64,86],[114,61],[120,70],[70,95]],CREAM);for(let i=0;i<6;i++)P([[66+i*8,85-i*4],[70+i*8,83-i*4],[77+i*8,91-i*4],[73+i*8,93-i*4]],kind==='cafe'?'#4c9a85':'#d77466');P([[60,101],[111,76],[117,84],[66,109]],'#dbae6d');R(62,108,3,11,'#937247');R(112,84,3,13,'#937247');}
    box(45,57,35,11,'#f4e1b1');R(48,60,7,5,kind==='cafe'?'#568d70':'#aa5a49');R(58,60,18,2,'#856b48');R(58,64,14,1,'#856b48');
    for(const x of [8,114]){box(x,102,7,10,'#aa6a4a');R(x-1,97,10,5,'#5e935e');R(x+2,92,3,8,'#75b066');}
    return p;
  }
  if(kind==='tree'||kind==='plant'){
    const small=kind==='plant',cx=64,base=small?113:120;box(cx-5,55,10,base-55,'#9b6e43');R(cx-3,60,3,base-65,'#ba8d53');
    for(const [x,y,w,h] of [[29,31,43,35],[62,28,36,37],[21,52,45,32],[55,49,49,37],[37,13,42,35]]){P([[x+6,y],[x+w-7,y],[x+w,y+8],[x+w,y+h-7],[x+w-9,y+h],[x+5,y+h],[x,y+h-9],[x,y+7]],'#3c7455');R(x+7,y+4,w-17,7,'#64a760');R(x+4,y+13,8,h-20,'#86bc70');R(x+w-14,y+h-8,9,5,'#2d634d');}
    if(small){box(49,101,31,20,'#ab714b');R(51,104,27,4,'#d79c62');}return p;
  }
  if(kind==='pond'||kind==='pool'){
    P([[9,68],[64,40],[120,68],[64,98]],'#416c64');P([[13,68],[64,43],[116,68],[64,94]],kind==='pool'?'#f3ddad':'#77a568');P([[22,67],[64,48],[107,68],[64,89]],'#4c9eb1');P([[25,67],[64,51],[102,68],[64,86]],'#67c1bf');
    for(let i=0;i<14;i++)R(36+(i*17)%53,61+(i*7)%17,6,1,'#d2ece1');
    if(kind==='pool'){R(88,48,2,21,'#e9e0ce');R(98,53,2,21,'#e9e0ce');R(90,58,8,2,'#e9e0ce');R(90,64,8,2,'#e9e0ce');box(10,83,14,6,'#e38865');R(11,84,7,2,CREAM);}
    else {for(const [x,y] of [[47,77],[80,65],[61,55]]){R(x,y,8,3,'#3a8860');R(x+3,y-2,2,2,'#ed9a92');}R(12,61,9,5,'#a68c5d');}return p;
  }
  if(kind==='boat'){
    P([[13,83],[73,49],[112,65],[54,103]],INK);P([[16,82],[74,53],[108,65],[54,98]],'#ac6e45');P([[25,81],[74,59],[95,67],[54,89]],'#dab376');for(let i=0;i<4;i++)P([[37+i*11,75-i*6],[41+i*11,73-i*6],[65+i*11,82-i*6],[61+i*11,84-i*6]],'#865c3d');P([[38,69],[44,64],[93,86],[86,89]],'#e9cb86');return p;
  }
  if(kind==='cat'){
    P([[41,82],[44,65],[53,72],[66,63],[77,73],[76,90],[67,96],[47,95]],INK);P([[44,82],[46,69],[53,75],[66,67],[74,74],[73,88],[65,93],[48,92]],'#cf9d63');R(50,81,3,3,INK);R(66,79,3,3,INK);R(59,87,3,2,'#9e5e54');R(38,93,8,5,'#cf9d63');R(35,85,4,12,'#cf9d63');return p;
  }
  if(kind==='cup'||kind==='bread'){
    box(48,82,32,19,kind==='cup'?'#d18f67':'#cd9955');R(50,83,27,3,kind==='cup'?'#5c4638':'#f6d99b');if(kind==='cup'){box(78,86,9,10,'#d18f67');R(80,88,5,6,'#fff0ce');}else{R(54,87,3,7,'#f1ce83');R(65,86,3,7,'#f1ce83');R(74,87,3,8,'#ad793f');R(51,97,23,2,'#ad793f');}return p;
  }
  if(kind==='lamp'){
    box(61,44,6,76,'#5c6760');box(51,25,25,21,'#f1d38a');R(55,29,5,12,'#fff2be');P([[47,25],[64,15],[81,25]],'#4d6759');R(53,119,22,3,'#4d6759');return p;
  }
  if(kind==='window'){
    box(28,34,73,61,'#a3754c');box(32,38,65,52,'#769f9c');R(35,41,23,21,'#b0d2bd');R(36,62,58,23,'#5b9865');R(62,40,4,49,'#e6c793');R(33,63,62,4,'#e6c793');R(25,95,80,5,'#c19159');return p;
  }
  if(kind==='bench'){
    P([[22,85],[69,61],[106,80],[59,105]],INK);P([[25,85],[69,65],[102,80],[59,101]],'#b8874d');P([[27,72],[71,50],[71,65],[27,87]],'#a67745');for(let i=0;i<3;i++)P([[30,70+i*5],[68,52+i*5],[68,55+i*5],[30,73+i*5]],'#d6ab64');R(29,89,4,27,'#6c6046');R(96,83,4,23,'#6c6046');return p;
  }
  if(kind==='shelf'){
    box(27,32,74,80,'#895e3f');R(30,35,68,72,'#614d39');for(let row=0;row<4;row++){R(30,50+row*17,68,3,'#c99b65');for(let col=0;col<8;col++){box(33+col*8,39+row*17,6,11,['#d3735b','#94bc81','#dcc476','#79a4ac'][(row+col)%4]);}}return p;
  }
  if(kind==='door'){box(32,27,65,91,'#946d4b');box(36,31,57,83,'#aac0a0');R(39,34,24,75,'#cedbbe');R(81,72,4,3,'#d6ab55');return p;}
  if(kind==='board'){box(32,33,64,68,'#9d7350');R(36,37,56,60,'#f3e4bb');for(let i=0;i<5;i++)R(42,47+i*9,35-(i%2)*9,2,'#9b9979');R(61,101,5,19,'#896e4b');return p;}
  // Furniture tops follow the same isometric ground; seeded colours differentiate tools and stock.
  const wood=kind==='desk'?'#be9b62':kind==='crates'?'#a7784e':'#c69556';
  P([[20,81],[64,59],[108,81],[64,104]],INK);P([[22,81],[64,62],[106,81],[64,101]],shade(wood,18));P([[21,83],[63,104],[63,121],[21,100]],shade(wood,-28));P([[65,104],[107,83],[107,100],[65,121]],wood);
  if(kind==='desk'){box(61,46,23,24,'#4c655f');R(64,49,17,16,'#9ac8bd');R(59,75,29,3,'#779b87');R(37,82,13,4,'#e7dec2');}
  else if(kind==='crates'){for(let i=0;i<5;i++)R(36+i*12,73-i%2*6,8,8,['#cb6e51','#9db363','#e3c379'][i%3]);}
  else {box(42,63,15,12,'#497977');R(44,65,11,7,'#b4d2b1');R(79,72,10,9,'#eee2b6');R(77,80,14,3,'#e38865');}
  return p;
}
export function getPixelAsset(kind,variant=0){return cached('asset:'+kind+':'+String(variant),()=>canvasOf(pixelAssetData(kind,variant)));}
/** Paint a saved wardrobe through any existing Canvas/SVG pen, retaining all old game interfaces. */
export function paintPixelFigure(ctx,F,K,step=0){const data=pixelCharacterData({look:F.L,gender:F.g,uniformColor:F.topC||F.classic,direction:'se',step});for(const cell of data.pixels)K.R(ctx,(cell.x-24)*2.2,(cell.y-64)*2.2,cell.w*2.2,cell.h*2.2,cell.c,0);}
