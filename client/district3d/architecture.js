import * as T from 'three';

// Authored footprints, not random boxes. Each row is x,z,width,depth,height,roof.
// The front of every plot is +z; the live walking corridor stays outside the plot.
const FORMS={
  rent:[
    ['corridor',[[0,-1,5.4,2.1,1.75,'gable'],[-2.1,1,1.15,1.35,1.15,'shed']],['gallery','laundry']],
    ['l-court',[[0,-1.6,5.2,1.5,1.7,'shed'],[-1.8,.5,1.6,2.7,1.7,'gable']],['court','laundry']],
    ['paired',[[ -1.8,-.2,1.8,4,1.65,'shed'],[1.8,-.8,1.8,2.8,1.95,'gable'],[.1,-1.8,1.5,1,1.2,'flat']],['lane','laundry']],
    ['pavilion',[[.7,-.6,3.4,3.1,1.9,'hip'],[-2,0,1.4,2,1.35,'shed']],['veranda','laundry']],
    ['u-court',[[0,-1.7,5.3,1.2,1.6,'gable'],[-2,.1,1.3,2.3,1.75,'shed'],[2,.4,1.3,2.9,1.5,'shed']],['court','laundry']],
    ['staggered',[[ -1.9,-1.1,1.5,2.4,1.45,'gable'],[0,-.45,1.8,3.4,1.8,'gable'],[1.9,-.95,1.5,2.5,1.65,'gable']],['veranda','laundry']],
    ['garden-rooms',[[ -1.65,-1.1,2.1,2.1,1.85,'hip'],[1.55,.15,2.2,2.6,1.65,'hip'],[.2,-1.55,1.8,.9,1.25,'flat']],['pergola','laundry']],
    ['sawtooth',[[ -1.7,-.7,1.65,3.1,1.7,'shed'],[0,-1.25,1.5,2.1,2.05,'shed'],[1.65,-.35,1.65,3.5,1.45,'shed']],['court','laundry']],
  ],
  apartment:[
    ['walkup',[[ -.8,-.55,3.3,3.1,5.3,'flat'],[1.75,-1.2,1.7,2.1,3.4,'flat']],['stairs','gallery']],
    ['sun-steps',[[ -1.7,-.5,1.9,3.3,6.1,'flat'],[.35,-.5,2,3.3,4.65,'flat'],[2,-.15,1.25,2.6,3.1,'flat']],['terraces']],
    ['lift-tower',[[ -.7,-.9,3.5,2.7,5.8,'flat'],[1.65,-.3,1.6,3.7,6.7,'flat'],[-.6,1.45,3.5,1.25,1.5,'flat']],['lobby','balconies']],
    ['skybridge',[[ -1.65,-.8,2.2,3.2,5.9,'flat'],[1.65,-.5,2.1,2.8,4.4,'flat']],['bridge','balconies']],
    ['family-court',[[0,-1.5,5.4,1.5,3.25,'flat'],[-1.95,.2,1.55,2.5,5.9,'flat'],[1.95,.7,1.55,1.7,4.8,'flat']],['court','balconies']],
    ['penthouse',[[0,-.4,5,3.8,4.5,'flat'],[-1.2,-.9,2.5,2.3,2,'butterfly',4.5]],['roofgarden','balconies']],
    ['corner-ribbon',[[ -1.5,-.4,2.3,3.5,6.2,'flat'],[1,-1.3,2.8,1.7,4.6,'flat'],[1.4,1,1.9,1.8,2.2,'round']],['lobby','terraces']],
    ['courtyard-tiers',[[0,-1.55,5.2,1.2,6.3,'flat'],[-1.8,.05,1.6,2.2,4.5,'flat'],[1.7,.8,1.8,2.1,2.9,'flat']],['pergola','terraces']],
  ],
  townhouse:[
    ['shop-house',[[ -.85,-.35,2.65,3.8,4.8,'gable'],[1.5,-1.35,1.9,1.8,2.8,'flat']],['shopfront','balconies']],
    ['garden-l',[[0,-1.5,5.1,1.65,2.75,'hip'],[-1.8,.45,1.65,2.4,3.35,'gable']],['pergola','court']],
    ['twin-gables',[[ -1.35,-.5,2.25,3.4,3.8,'gable'],[1.2,-.8,2.25,2.7,2.4,'gable']],['veranda','bay']],
    ['stepped-courtyard',[[ -1.8,-.5,1.8,3.7,4.5,'flat'],[.15,-1.35,2.1,1.9,3,'flat'],[1.9,-1,1.5,2.5,1.65,'flat']],['terraces','court']],
    ['patio-house',[[0,-1.7,5.2,1.25,2.6,'gable'],[-1.95,.05,1.3,2.5,2.6,'gable'],[1.9,.45,1.4,1.7,3.9,'flat']],['court','veranda']],
    ['round-corner',[[ -.85,-.9,3.6,2.6,3.1,'hip'],[1.55,.3,1.85,2.15,4.2,'round']],['bay','balconies']],
    ['butterfly',[[ .4,-.65,4.5,3.3,3.15,'butterfly'],[-2.25,.55,1,2.15,1.9,'flat']],['portal','terraces']],
    ['split-pavilions',[[ -1.65,-1,2.1,2.5,3.75,'hip'],[1.35,.05,2.5,3.3,2.75,'gable']],['bridge','pergola']],
  ],
  villa:[
    ['garden-l',[[0,-1.5,5.4,1.7,2.5,'hip'],[-1.85,.35,1.7,2.7,3.7,'hip']],['pool','pergola']],
    ['river-terraces',[[ -1.55,-.5,2.5,3.4,4.9,'flat'],[1.2,-1.2,2.6,2.1,3.1,'flat'],[1.2,1.1,2.5,1.8,1.55,'flat']],['pool','terraces']],
    ['u-colonnade',[[0,-1.65,5.5,1.3,2.6,'hip'],[-2,.15,1.4,2.3,2.6,'hip'],[2,.15,1.4,2.3,2.6,'hip']],['court','pool']],
    ['glass-pavilion',[[ -.8,-.25,3.55,3.55,2.3,'butterfly'],[1.85,-1.1,1.6,2.1,1.5,'flat']],['pergola','bay']],
    ['orangery',[[ -1.25,-.65,2.8,3.2,3.55,'gable'],[1.65,.15,1.7,2.4,1.9,'gable'],[.65,-1.75,1.25,.7,1.8,'flat']],['veranda','court']],
    ['rotunda',[[ -.95,-1.05,3.5,2.15,2.5,'hip'],[1.55,.4,2.1,2.1,3.85,'round'],[-1.85,1.2,1.7,1.4,1.5,'flat']],['pool','bay']],
    ['twin-roofs',[[ -1.65,-.75,2.1,3,3.2,'hip'],[1.2,-.3,2.8,3.7,2.1,'hip']],['bridge','pergola']],
    ['courtyard-manor',[[0,-1.65,5.45,1.2,3.15,'gable'],[-2.05,0,1.35,2.25,2.2,'hip'],[2.05,.3,1.35,2.7,4,'hip']],['portal','court']],
  ],
};
const PREFERRED={ky_tuc_xa:0,tro_moi:1,tap_the:0,can_ho_studio:1,can_ho_mini:2,can_ho_1pn:3,can_ho_2pn:4,penthouse:5,nha_pho:0,nha_san:1,biet_thu_vuon:0,biet_thu_song:1};
const PALETTE={rent:['#efd4a1','#b3664b'],apartment:['#e8dfc8','#638787'],townhouse:['#e9d2ae','#ae624b'],villa:['#f3e7cc','#9e6750']};
function hash(s){let n=0;for(const c of String(s))n=(n*31+c.charCodeAt(0))>>>0;return n;}
export function districtArchitecture(group,homes=[]){
  group=FORMS[group]?group:'rent';const used=new Set();
  return Array.from({length:8},(_,lot)=>{
    const home=homes[lot],kind=home?.kindId||home?.kind||'',preferred=PREFERRED[kind];let index=Number.isInteger(preferred)?preferred:hash(home?.id||lot)%8;
    while(used.has(index))index=(index+1)%8;used.add(index);
    const [name,masses,features]=FORMS[group][index];return {id:group+'-'+name,group,index,kind,lot,masses,features,wall:PALETTE[group][0],roof:PALETTE[group][1]};
  });
}

/** Seven shared primitive buffers per open district; the scene batches by paint. */
export function createResidenceKit(material,geometries){
  const triangle=new T.Shape();triangle.moveTo(-.5,0);triangle.lineTo(0,1);triangle.lineTo(.5,0);triangle.closePath();
  const shapes={box:new T.BoxGeometry(1,1,1),cylinder:new T.CylinderGeometry(.5,.5,1,16),hip:new T.ConeGeometry(Math.SQRT1_2,1,4).rotateY(Math.PI/4).translate(0,.5,0),round:new T.ConeGeometry(.5,1,16).translate(0,.5,0),gable:new T.ExtrudeGeometry(triangle,{depth:1,bevelEnabled:false}).translate(0,0,-.5),arch:new T.TorusGeometry(.5,.07,6,14,Math.PI),leaf:new T.IcosahedronGeometry(.5,1)};
  for(const key of Object.keys(shapes)){if(shapes[key].index){const old=shapes[key];shapes[key]=old.toNonIndexed();old.dispose();}geometries.add(shapes[key]);}
  const C={trim:'#fff0d2',wood:'#846044',dark:'#536a60',glass:'#719da2',brick:'#b28362',leaf:'#7ea36a',water:'#8cc3c6'};
  function build(plan){
    const root=new T.Group();root.name=plan.id;root.userData.architecture=plan;
    const part=(kind,color,x,y,z,w,h,d,label='detail')=>{const m=new T.Mesh(shapes[kind],material(color));m.position.set(x,y,z);m.scale.set(w,h,d);m.userData.structure=label;root.add(m);return m;};
    const B=(x,y,z,w,h,d,c=C.trim,label)=>part('box',c,x,y,z,w,h,d,label),cyl=(x,y,z,w,h,d,c)=>part('cylinder',c,x,y,z,w,h,d);
    const roof=(x,y,z,w,d,style)=>{
      if(style==='flat'){B(x,y+.09,z,w+.15,.18,d+.15,C.trim,'roof');for(const s of [-1,1]){B(x+s*w/2,y+.27,z,.1,.36,d+.12,C.trim);B(x,y+.27,z+s*d/2,w,.36,.1,C.trim);}return;}
      if(style==='shed'){const m=B(x,y+.22,z,w+.25,.13,d+.28,plan.roof,'roof');m.rotation.x=-.14;for(let i=-w/2;i<w/2;i+=.28)B(x+i,y+.3,z,.025,.03,d+.25,C.trim).rotation.x=-.14;return;}
      if(style==='butterfly'){for(const side of [-1,1]){const m=B(x+side*w*.25,y+.25,z,w*.56,.16,d+.25,plan.roof,'roof');m.rotation.z=side*.22;}B(x,y+.16,z,.12,.1,d+.28,C.dark);return;}
      const h=style==='gable'?Math.min(.95,w*.28):Math.min(1.2,w*.33);part(style==='round'?'round':style==='hip'?'hip':'gable',plan.roof,x,y,z,w+.26,h,d+.24,'roof');
      if(style==='gable')B(x,y+h+.025,z,.12,.08,d+.2,C.trim);
      if(style!=='round')for(const s of [-1,1])B(x+s*w*.5,y+.02,z,.1,.09,d+.24,C.trim);
    };
    function window(x,y,z,w=.65,h=.85){B(x,y,z,w+.12,h+.12,.12,C.trim);B(x,y,z+.075,w,h,.035,C.glass);B(x,y,z+.1,.045,h,.025,C.trim);B(x,y-h*.5-.06,z+.12,w+.24,.09,.3,C.trim);}
    function rail(x,y,z,w,d=.65){B(x,y,z,w,.12,d,C.trim);for(let p=-w*.45;p<=w*.46;p+=.32)B(x+p,y+.36,z+d*.46,.045,.65,.045,C.dark);B(x,y+.69,z+d*.46,w,.06,.06,C.dark);}
    function porch(x,z,w,d,h=1.65,pergola=false,base=0){B(x,base+.13,z,w,.16,d,C.brick);for(const a of [-1,1])for(const b of [-1,1])cyl(x+a*w*.44,base+h/2,z+b*d*.4,.1,h,.1,C.wood);B(x,base+h,z,w+.12,.12,d+.12,C.wood);if(pergola){for(let q=-w/2;q<=w/2;q+=.28)B(x+q,base+h+.12,z,.07,.1,d+.35,C.trim);}else{B(x,base+h+.09,z,w+.22,.13,d+.16,plan.roof);for(let q=-w*.34;q<w*.4;q+=w/3)part('arch',C.trim,x+q,base+h-.25,z+d*.41,w*.27,.65,.55);}}
    const flower=(x,z)=>{cyl(x,.18,z,.34,.36,.34,C.brick);part('leaf',C.leaf,x,.48,z,.53,.48,.5);};
    B(0,.02,0,5.9,.1,5.7,plan.group==='villa'?'#a8bd90':'#c5b38e');
    for(const [index,mass]of plan.masses.entries()){
      const [x,z,w,d,h,style,base=0]=mass,y=base+.18,round=style==='round';
      part(round?'cylinder':'box',plan.wall,x,y+h/2,z,w,h,d,'mass');B(x,y-.04,z,w+.12,.16,d+.12,C.brick);
      for(const side of [-1,1]){B(x+side*(w/2-.055),y+h/2,z+d/2+.03,.11,h,.13,C.trim);B(x,y+.15,z+side*d/2,w,.18,.08,C.brick);}
      const floors=Math.max(1,Math.floor(h/1.45));
      for(let f=0;f<floors;f++){
        const wy=y+.84+f*(h/floors);if(wy+.52>y+h)continue;
        for(let wx=x-w*.3;wx<=x+w*.31;wx+=Math.max(.75,w*.58))window(wx,wy,z+d/2+.075,Math.min(.68,w*.35),.77);
        // Window recesses on the return facade make wings legible from an orbit.
        for(const side of [-1,1]){B(x+side*(w/2+.025),wy,z,.08,.82,d*.38,C.trim);B(x+side*(w/2+.07),wy,z,.03,.68,d*.29,C.glass);}
        if(f>0&&(plan.features.includes('balconies')||plan.features.includes('terraces')))rail(x,y+f*h/floors-.08,z+d/2+.32,w*.86,.58);
      }
      roof(x,y+h,z,w,d,style);
      if(index===0||plan.group==='rent'){const dx=x+(plan.group==='rent'?-.15:0),dz=z+d/2+.12;B(dx,y+.58,dz,.58,1.16,.12,C.wood);for(let j=0;j<4;j++)B(dx,y+.2+j*.22,dz+.075,.43,.035,.025,C.trim);B(dx+.18,y+.64,dz+.09,.06,.07,.04,'#dfbb6a');B(dx,y+.02,dz+.19,.95,.13,.52,C.trim);}
    }
    const has=f=>plan.features.includes(f);
    if(has('gallery')){porch(0,1.15,5.45,.82,1.65);for(let i=-2.2;i<=2.2;i+=1.1)flower(i,1.75);}
    if(has('veranda'))porch(.2,1.65,3.8,.75,1.8);
    if(has('pergola'))porch(.45,1.6,2.25,1.3,1.85,true);
    if(has('court')){for(let i=0;i<5;i++)B(.25,.095,1.2+i*.25,.65,.03,.13,C.trim);flower(-.7,1.7);flower(1.2,1.9);}
    if(has('lane')){for(let i=0;i<7;i++)B(0,.085,-1.3+i*.52,.7,.04,.3,C.trim);}
    if(has('laundry')){for(const x of [-1,1])cyl(x*.8,1.15,2.38,.045,2.3,.045,C.dark);B(0,2.18,2.38,1.7,.025,.025,C.wood);for(let i=0;i<4;i++){B(-.6+i*.4,1.96,2.38,.28,.42,.035,['#e4ae8c','#e9e4cd','#aac7b9','#ddb7c0'][i]);B(-.6+i*.4,2.15,2.38,.38,.1,.04,C.trim);}}
    if(has('stairs')){for(let i=0;i<10;i++)B(2.14,.15+i*.19,.9-i*.3,.78,.3+i*.38,.28,C.brick);for(const x of [1.72,2.56]){const m=B(x,1.95,-.45,.045,.065,3.1,C.dark);m.rotation.x=.56;}}
    if(has('bridge')){B(0,2.15,-.2,1.5,.18,.95,C.trim);for(const z of [-.62,.22]){B(0,2.58,z,1.5,.66,.06,C.glass);B(0,2.94,z,1.56,.06,.08,C.dark);}}
    if(has('roofgarden')){porch(1.35,.45,1.85,1.8,1.5,true,4.68);for(let i=0;i<3;i++){B(1+i*.5,4.93,.95,.4,.35,.45,C.brick);part('leaf',C.leaf,1+i*.5,5.18,.95,.5,.45,.5);}}
    if(has('lobby')){B(-.7,.8,1.8,1.8,1.4,.05,C.glass);B(-.7,1.7,2.05,2.4,.13,.9,C.trim);for(const x of [-1.75,.4])cyl(x,.85,2.26,.11,1.7,.11,C.dark);}
    if(has('shopfront')){B(-.85,.86,1.6,2.15,1.35,.05,C.glass);B(-.85,1.75,1.87,2.7,.13,.65,C.wood);for(let i=0;i<6;i++)B(-1.96+i*.43,1.82,1.87,.24,.055,.68,i%2?C.trim:'#b77864');}
    if(has('portal')){for(const x of [-.9,.9])B(x,1.1,2.25,.24,2.2,.28,C.trim);part('arch',C.trim,0,2.1,2.25,1.8,1.25,1.7);}
    if(has('pool')){B(.55,.12,1.45,2,.2,1.15,C.trim);B(.55,.23,1.45,1.78,.025,.92,C.water);for(let i=0;i<3;i++)B(-.04+i*.43,.25,1.5,.25,.015,.035,C.trim);}
    if(has('bay')){B(-1.5,.95,1.65,1.6,1.6,.06,C.glass);for(const x of [-2.31,-.69])B(x,.94,1.78,.09,1.88,.5,C.trim);B(-1.5,1.91,1.78,1.7,.12,.55,C.trim);}
    flower(-2.62,2.12);flower(2.6,2.15);
    return root;
  }
  return {build};
}
