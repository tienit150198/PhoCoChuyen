// These shells live on the room perimeter or above head height. They never add
// unrecorded obstacles to the server's editable floor or move a saved fixture.
const KINDS=['ky_tuc_xa','tro_moi','tap_the','can_ho_studio','can_ho_mini','can_ho_1pn','can_ho_2pn','penthouse','nha_pho','nha_san','biet_thu_vuon','biet_thu_song'];
export function interiorProfile(room,scope=''){
  const bits=String(scope).split(':'),kind=KINDS.find(k=>bits.includes(k))||(bits[0]==='estate'?'estate':bits[0]==='attic'?'attic':'home');
  const type=room.type||room.id,privateRoom=['bath','bathc','bed','bed2','suite','cinema','cellar','closet'].includes(type);
  return {kind,id:kind+':'+type,room:type,windowDepth:{can_ho_studio:.6,can_ho_1pn:.85,penthouse:.72,biet_thu_song:.9}[kind]||0,sideHeight:privateRoom?null:({can_ho_mini:.75,nha_pho:.36,nha_san:.5,biet_thu_vuon:.42,biet_thu_song:.58}[kind]??null)};
}
export function addInteriorArchitecture(room,scope,painters,size){
  const profile=interiorProfile(room,scope),{width:w,depth:d,height:h}=size,{solid,back,side}=painters;
  // Architectural trim is never an editable item or an invisible click blocker.
  const wrap=p=>Object.fromEntries(Object.entries(p).map(([name,fn])=>[name,(...args)=>{const m=fn(...args);m.userData.architectureOnly=true;return m;}]));
  const A=wrap(solid),W=wrap(back),L=wrap(side),B=A.box,z=-d/2-.05;
  const wood='#956d4a',cream='#fff0d5',mint='#85ac9b',dark='#5f7772',glass='#a8cbd0';
  const pillar=(x,zz,top=h)=>A.box(x,top/2,zz,.15,top,.15,cream);
  function cornice(level=h){W.box(0,level,z,w+.35,.18,.34,cream);L.box(-w/2-.07,level,0,.32,.18,d+.2,cream);}
  function arch(x,zz,span,rise,base=h-.55,p=W){
    for(let i=0;i<12;i++){const a=i*Math.PI/12,b=(i+1)*Math.PI/12,x1=Math.cos(a)*span/2,y1=Math.sin(a)*rise,x2=Math.cos(b)*span/2,y2=Math.sin(b)*rise,m=p.box(x+(x1+x2)/2,base+(y1+y2)/2,zz,Math.hypot(x2-x1,y2-y1)+.035,.13,.17,cream);m.rotation.z=Math.atan2(y2-y1,x2-x1);}
  }
  function rafters(pitch=.27,woodColor=wood){
    for(let zz=-d/2;zz<d/2;zz+=Math.max(.65,d/4))for(const s of [-1,1]){const m=B(s*w*.25,h+.25,zz,w*.51,.12,.12,woodColor);m.rotation.z=-s*pitch;}
    B(0,h+.25+w*.25*Math.sin(pitch),0,.14,.14,d+.2,woodColor);
    const eave=h+.25-w*.255*Math.sin(pitch);
    for(const x of [-w/2-.05,w/2+.05]){B(x,eave,0,.13,.15,d+.2,woodColor);pillar(x,d/2+.04,eave);}
  }
  function bay(span=w*.55,depth=.55){
    // Clerestory above the preserved wall grid; the deep bay itself is fitted to
    // the real reserved window cells by roomStructure, so it remains visible.
    W.box(0,h+.18,z-depth*.45,span,.36,.07,glass);
    for(const x of [-span/2,0,span/2])W.box(x,h+.18,z-depth*.45+.05,.065,.42,.1,cream);
    W.box(0,h+.4,z-depth*.3,span+.3,.1,depth*.6+.25,cream);
  }
  function veranda(){
    L.box(-w/2-.53,-.02,0,.95,.12,d+.15,wood);for(const zz of [-d*.42,0,d*.42]){const m=L.cyl(-w/2-.9,h/2,zz,.12,h,.12,cream);m.userData.architectureOnly=true;}
    L.box(-w/2-.55,h,0,1.1,.14,d+.2,wood);for(let zz=-d/2;zz<=d/2;zz+=.36)L.box(-w/2-.55,h+.12,zz,1.2,.08,.065,cream);
  }
  if(room.out){
    if(['pool','infinity'].includes(profile.room)){for(const x of [-w/2-.13,w/2+.13])for(const zz of [-d/2,d/2])pillar(x,zz,1.65);B(0,.09,-d/2-.25,w+.4,.14,.38,cream);B(0,.2,-d/2-.27,w+.35,.035,.16,glass);}
    else if(['yard','pavilion'].includes(profile.room)){veranda();for(let zz=-d/2;zz<=d/2;zz+=.5)L.box(-w/2-.14,.7,zz,.1,1.4,.07,wood);L.box(-w/2-.14,1.35,0,.14,.12,d+.2,wood);}
    else {W.box(0,.58,z,w+.3,1.1,.055,glass);for(let x=-w/2;x<=w/2;x+=.6)W.box(x,.58,z+.06,.04,1.2,.05,dark);W.box(0,1.2,z+.07,w+.35,.07,.09,wood);if(profile.kind==='penthouse'||profile.room==='terrace'){veranda();B(0,2.35,z,w+.4,.12,.8,cream);}}
    return profile;
  }
  switch(profile.kind){
    case 'attic':rafters(.36);for(let x=-w/2;x<w/2;x+=.55)W.box(x,h*.72,z+.13,.04,.9,.05,wood);break;
    case 'ky_tuc_xa':
      for(const x of [-w/2-.07,w/2+.07])for(const zz of [-d/2,d/2])pillar(x,zz,h+.5);
      B(0,h+.27,-d*.25,w+.22,.18,d*.55,wood);for(let x=-w/2;x<=w/2;x+=.45)W.box(x,h+.56,-d*.49,.055,.65,.055,mint);W.box(0,h+.85,-d*.49,w,.07,.07,mint);L.box(-w/2-.1,h*.6,0,.09,.85,d*.75,mint);break;
    case 'tro_moi':
      B(0,h+.15,-d*.28,w+.15,.18,d*.46,wood);for(let x=-w/2;x<=w/2;x+=.52)W.box(x,h+.48,-d*.05,.055,.62,.055,dark);W.box(0,h+.8,-d*.05,w,.07,.07,wood);
      for(let zz=-d/2;zz<d/2;zz+=.65)L.box(-w/2-.12,h-.3,zz,.25,.12,.14,wood);break;
    case 'tap_the':
      W.box(0,h-.17,z+.12,w,.25,.26,'#b4afa0');for(const x of [-w*.45,w*.4])W.box(x,h/2,z+.09,.19,h,.23,'#b4afa0');
      L.cyl(-w/2-.07,h/2,d*.2,.07,h,.07,'#929f98');for(let zz=-d*.4;zz<d*.5;zz+=.32)L.box(-w/2-.15,.67,zz,.12,.9,.07,mint);break;
    case 'can_ho_studio':bay(w*.72,.6);W.box(0,h+.2,z,w+.4,.35,.18,cream);L.box(-w/2-.1,h*.5,0,.08,h,d*.82,glass);break;
    case 'can_ho_mini':cornice();arch(0,z+.14,w*.65,.38,h-.4);veranda();break;
    case 'can_ho_1pn':bay(w*.43,.85);cornice();for(let x=-w/2;x<w/2;x+=.7)W.box(x,h-.08,z+.16,.11,.3,.4,wood);break;
    case 'can_ho_2pn':
      cornice();for(const x of [-w*.25,w*.25])arch(x,z+.16,w*.45,.52,h-.55);
      arch(0,0,w+.1,.5,h-.55,A);for(const x of [-w/2-.06,w/2+.06])pillar(x,0,h-.55);break;
    case 'penthouse':
      rafters(.16,dark);bay(w*.82,.72);for(let x=-w/2;x<=w/2;x+=w/3)W.box(x,h+.2,z,.1,.55,.1,dark);W.box(0,h+.45,z,w,.055,.6,glass);veranda();break;
    case 'nha_pho':
      cornice(h+.17);for(let i=0;i<8;i++)L.box(-w/2-.58,.13+i*.19,-d*.36+i*d*.09,.9,.14+i*.38,d*.085,wood);
      L.box(-w/2-.65,h+.1,-d*.1,1.05,.16,d*.85,cream);W.box(w*.35,h+.38,z,w*.3,.65,.14,glass);break;
    case 'nha_san':veranda();rafters(.23);arch(0,z+.13,w*.8,.5,h-.4);break;
    case 'biet_thu_vuon':
      veranda();cornice();for(const x of [-w*.33,0,w*.33]){arch(x,z+.17,w*.3,.58,h-.5);W.box(x-w*.15,h/2,z+.15,.16,h,.23,cream);}rafters(.22);break;
    case 'biet_thu_song':
      bay(w*.86,.9);cornice(h+.35);W.box(0,h+.1,z,w,.28,.13,glass);for(let zz=-d/2;zz<d/2;zz+=d/3)B(0,h+.28,zz,w+.4,.16,.16,cream);veranda();break;
    case 'estate':
      cornice(h+.2);if(['living','suite','bed','hall'].includes(profile.room)){veranda();for(const x of [-w*.26,w*.26])arch(x,z+.18,w*.48,.6,h-.4);rafters(.12);}
      break;
    default:cornice();
  }
  // Functional room structures remain visually distinct even inside the same home.
  if(['bath','bathc'].includes(profile.room)){
    for(let x=-w/2;x<w/2;x+=.45){W.box(x,.7,z+.12,.42,1.36,.05,'#b6d0c5');W.box(x,1.41,z+.15,.42,.04,.07,cream);}
    for(let y=.2;y<h;y+=.42)L.box(-w/2+.035,y,0,.035,.025,d,'#f5eade');
  }else if(profile.room==='kitchen'){
    W.box(-w*.12,h-.24,z+.18,w*.55,.36,.34,wood);for(let x=-w*.38;x<w*.18;x+=.42)W.box(x,h-.25,z+.37,.035,.28,.025,cream);
  }else if(['bed','bed2','suite'].includes(profile.room)){
    W.box(0,h-.05,z+.17,w*.72,.16,.38,wood);for(const x of [-w*.34,w*.34])W.box(x,h*.57,z+.19,.13,h*.82,.23,cream);
  }else if(profile.room==='cinema'){
    for(let x=-w/2;x<w/2;x+=.36)W.box(x,h/2,z+.15,.16,h,.12,'#8e5154');L.box(-w/2+.03,h/2,0,.08,h,d,'#65575c');
  }else if(profile.room==='cellar'){for(const zz of [-d*.44,0,d*.44]){arch(0,zz,w+.15,.6,h-.3,A);for(const x of [-w/2-.075,w/2+.075])pillar(x,zz,h-.3);}}
  else if(profile.room==='gym'){L.box(-w/2+.035,h*.55,0,.045,h*.73,d*.85,glass);B(0,h-.12,z,w*.85,.04,.045,cream);}
  else if(profile.room==='study'){for(const x of [-w*.42,w*.42])W.box(x,h/2,z+.18,.13,h,.25,wood);W.box(0,h-.12,z+.16,w,.16,.35,wood);}
  else if(profile.room==='closet'){cornice(h-.08);W.box(0,h*.4,z+.1,w,.035,.16,'#d5a193');}
  else if(profile.room==='showroom'){for(let x=-w/2;x<=w/2;x+=w/3)B(x,h+.07,0,.1,.16,d+.2,dark);L.box(-w/2+.02,.17,0,.08,.09,d,'#d5b673');}
  return profile;
}
