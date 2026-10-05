/** Small, deterministic Canvas street paintings. All dimensions are metres;
 * x/y is the projected ground contact and k is pixels per metre.
 * Each entry point isolates Canvas state, including the caller's fog alpha. */
const TAU=Math.PI*2;
const identity=color=>color;
const SKIN=['#c99570','#deb08c','#b98262','#d7a07b'];
const HAIR=['#302c29','#41362e','#252b2c','#52443b'];
const TROUSERS=['#485159','#60594f','#394d51','#6c6257'];
const GREEN=[['#465d46','#526d4d','#688154','#7f925e'],['#435e4d','#52745b','#698768','#829a74'],['#525f43','#67764d','#7a885a','#94a06a']];
const CLUSTERS=[[-.53,.13,.49], [.5,.11,.5],[-.14,-.39,.56],[.34,-.34,.47],[-.49,-.27,.42],[.01,.17,.64],[-.23,-.13,.5],[.35,.05,.42],[-.59,-.07,.3],[.06,-.55,.31],[.57,-.21,.29],[-.24,.31,.33]];
const LOBES=[1,.88,1.06,.85,1,.94,1.04,.85,1.01,.9];
const valid=(x,y,k)=>Number.isFinite(x)&&Number.isFinite(y)&&Number.isFinite(k)&&k>0;
const variantIndex=(variant,n)=>Math.abs(Math.trunc(Number.isFinite(variant)?variant:0))%n;
function shade(color,amount){
  if(!/^#[\da-f]{6}$/i.test(color))return color;
  const n=parseInt(color.slice(1),16);
  const channel=value=>Math.max(0,Math.min(255,Math.round(value*amount))).toString(16).padStart(2,'0');
  return '#'+channel((n>>16)&255)+channel((n>>8)&255)+channel(n&255);
}
function oval(c,x,y,rx,ry,color,rotation=0){c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,rotation,0,TAU);c.fill();}
function shape(c,color,points){c.fillStyle=color;c.beginPath();c.moveTo(points[0],points[1]);for(let n=2;n<points.length;n+=2)c.lineTo(points[n],points[n+1]);c.closePath();c.fill();}
function line(c,color,width,points){c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.moveTo(points[0],points[1]);for(let n=2;n<points.length;n+=2)c.lineTo(points[n],points[n+1]);c.stroke();}
function shadow(c,rx,ry){const alpha=c.globalAlpha;c.globalAlpha=alpha*.2;oval(c,.09,.006,rx,ry,'#302d29');c.globalAlpha=alpha;}
// Tapered fabric/skin segments make knees and elbows distinct at close range.
function limb(c,x1,y1,x2,y2,r1,r2,color){
  const a=Math.atan2(y2-y1,x2-x1),dx=Math.sin(a),dy=-Math.cos(a);
  c.fillStyle=color;c.beginPath();c.moveTo(x1+dx*r1,y1+dy*r1);c.lineTo(x2+dx*r2,y2+dy*r2);
  c.quadraticCurveTo(x2+Math.cos(a)*r2,y2+Math.sin(a)*r2,x2-dx*r2,y2-dy*r2);
  c.lineTo(x1-dx*r1,y1-dy*r1);c.quadraticCurveTo(x1-Math.cos(a)*r1,y1-Math.sin(a)*r1,x1+dx*r1,y1+dy*r1);c.fill();
}

export function drawStreetPerson(c,{x,y,k,col='#92705c',hat=false,t=0,wave=false,variant=0,facing=1,calm=false,tint=identity}){
  if(!valid(x,y,k))return;
  const v=variantIndex(variant,4),near=k>25,back=facing<-.3,profile=Math.abs(facing)<.3,skin=tint(SKIN[v]),skinDark=tint(shade(SKIN[v],.82)),hair=tint(HAIR[v]);
  const shirt=tint(col),shirtDark=tint(shade(col,.76)),pants=tint(TROUSERS[v]),pantsDark=tint(shade(TROUSERS[v],.75));
  const phase=calm?0:(Number.isFinite(t)?t:0)*5.5,step=calm?0:Math.sin(phase),bob=calm?0:Math.cos(phase*2)*.012;
  c.save();c.translate(x,y);c.scale(k,k);c.lineCap='round';c.lineJoin='round';shadow(c,.32,.071);
  c.scale(profile?.74:1,1);
  // Far arm and leg are painted first, giving the stride real overlap.
  const farFoot=-.095-step*.13,nearFoot=.095+step*.13;
  limb(c,-.095,-.79+bob,-.11+step*.045,-.43,.092,.07,pantsDark);
  limb(c,-.11+step*.045,-.43,farFoot,-.065-Math.max(0,step)*.035,.07,.046,pantsDark);
  oval(c,farFoot+.027,-.044-Math.max(0,step)*.035,.102,.042,tint('#393a36'));
  limb(c,.09,-.79+bob,.1-step*.03,-.43,.094,.073,pants);
  limb(c,.1-step*.03,-.43,nearFoot,-.061-Math.max(0,-step)*.035,.073,.047,pants);
  oval(c,nearFoot+.025,-.037-Math.max(0,-step)*.035,.105,.042,tint('#343632'));
  if(near)line(c,tint('#bcb4a0'),.013,[nearFoot-.025,-.022,nearFoot+.098,-.022]);
  const elbow=-.26-step*.04,hand=-.23-step*.085;
  limb(c,-.19,-1.3+bob,elbow,-1.065+bob,.078,.061,shirtDark);
  limb(c,elbow,-1.065+bob,hand,-.86+bob,.051,.035,skinDark);oval(c,hand,-.835+bob,.041,.057,skinDark);
  // A fitted, curved shirt with sloping shoulders, rather than a box torso.
  c.fillStyle=shirt;c.beginPath();c.moveTo(-.075,-1.414+bob);c.quadraticCurveTo(-.19,-1.405+bob,-.225,-1.305+bob);
  c.lineTo(-.187,-.94+bob);c.lineTo(-.213,-.785+bob);c.quadraticCurveTo(0,-.75+bob,.208,-.794+bob);
  c.lineTo(.18,-.96+bob);c.lineTo(.214,-1.315+bob);c.quadraticCurveTo(.14,-1.406+bob,.071,-1.414+bob);c.closePath();c.fill();
  shape(c,shirtDark,[.13,-1.37+bob,.21,-1.3+bob,.18,-.95+bob,.208,-.794+bob,.12,-.79+bob,.092,-1.03+bob]);
  if(near){line(c,tint(shade(col,.88)),.018,[-.14,-.89+bob,.02,-.86+bob,.09,-.87+bob]);if(!back)line(c,tint(shade(col,.88)),.012,[.04,-1.29+bob,.04,-1.07+bob,.12,-1.07+bob,.13,-1.28+bob]);}
  // Neck, open collar and egg-shaped head.
  limb(c,0,-1.5+bob,0,-1.383+bob,.053,.05,skinDark);
  if(!back){
    shape(c,tint('#ded9c9'),[-.09,-1.41+bob,-.022,-1.356+bob,-.052,-1.3+bob,-.121,-1.375+bob]);
    shape(c,tint('#d0cbbd'),[.066,-1.414+bob,-.022,-1.356+bob,.021,-1.302+bob,.107,-1.378+bob]);
  }else line(c,shirtDark,.029,[-.083,-1.395+bob,0,-1.372+bob,.083,-1.395+bob]);
  oval(c,0,-1.582+bob,.123,.163,skin);
  oval(c,.11,-1.586+bob,.027,.044,skinDark);oval(c,-.113,-1.588+bob,.023,.039,skin);
  c.fillStyle=hair;c.beginPath();c.moveTo(-.115,-1.547+bob);c.bezierCurveTo(-.176,-1.748+bob,.074,-1.81+bob,.125,-1.647+bob);
  c.lineTo(.122,-1.55+bob);c.lineTo(.089,-1.598+bob);c.lineTo(.071,-1.682+bob);c.quadraticCurveTo(-.045,-1.619+bob,-.086,-1.651+bob);c.closePath();c.fill();
  if(v===1)oval(c,-.122,-1.59+bob,.054,.106,hair,-.17);
  if(back){
    c.fillStyle=hair;c.beginPath();c.moveTo(-.115,-1.67+bob);c.quadraticCurveTo(0,-1.785+bob,.12,-1.665+bob);c.lineTo(.097,-1.497+bob);c.quadraticCurveTo(0,-1.456+bob,-.097,-1.497+bob);c.closePath();c.fill();
  }
  if(profile&&!back)shape(c,skin,[.08,-1.62+bob,.157,-1.558+bob,.1,-1.543+bob]);
  if(near&&!back){
    if(!profile)line(c,tint('#554537'),.014,[-.071,-1.595+bob,-.043,-1.595+bob]);line(c,tint('#554537'),.014,[.036,-1.595+bob,.065,-1.595+bob]);
    line(c,skinDark,.012,[.008,-1.592+bob,.019,-1.548+bob,-.003,-1.54+bob]);
    line(c,tint('#96644d'),.012,[-.029,-1.503+bob,.012,-1.495+bob,.043,-1.505+bob]);
  }
  if(hat){
    oval(c,0,-1.67+bob,.285,.051,tint('#9d8356'));
    c.fillStyle=tint('#d2bd86');c.beginPath();c.moveTo(-.297,-1.681+bob);c.quadraticCurveTo(-.146,-1.776+bob,-.012,-1.896+bob);c.quadraticCurveTo(.17,-1.77+bob,.296,-1.681+bob);c.quadraticCurveTo(.01,-1.635+bob,-.297,-1.681+bob);c.fill();
    shape(c,tint('#e1cea0'),[-.272,-1.684+bob,-.012,-1.896+bob,-.063,-1.681+bob]);
    if(near)line(c,tint('#af986a'),.011,[-.17,-1.69+bob,-.012,-1.88+bob,.151,-1.69+bob]);
  }
  if(wave){
    const tilt=calm?0:Math.sin(phase*1.3)*.065;
    limb(c,.19,-1.31+bob,.36,-1.48+bob,.076,.061,shirt);
    limb(c,.36,-1.48+bob,.39+tilt,-1.73+bob,.052,.034,skin);
    oval(c,.394+tilt,-1.776+bob,.047,.071,skin,-.14);
    if(near)line(c,skinDark,.009,[.393+tilt,-1.81+bob,.398+tilt,-1.763+bob]);
  }else{
    limb(c,.195,-1.31+bob,.26+step*.05,-1.071+bob,.074,.06,shirt);
    limb(c,.26+step*.05,-1.071+bob,.24+step*.095,-.868+bob,.049,.035,skin);
    oval(c,.24+step*.095,-.845+bob,.04,.057,skin);
  }
  if(v===3){
    line(c,tint('#594d3b'),.024,[-.12,-1.38+bob,.208,-.89+bob]);
    c.fillStyle=tint('#a3906d');c.beginPath();c.moveTo(.1,-.94+bob);c.quadraticCurveTo(.21,-.98+bob,.33,-.94+bob);c.lineTo(.31,-.65+bob);c.quadraticCurveTo(.19,-.62+bob,.105,-.67+bob);c.closePath();c.fill();
    line(c,tint('#78684e'),.019,[.107,-.88+bob,.312,-.88+bob]);
  }
  c.restore();
}

// Ten soft lobes form each foliage mass; a fixed pattern avoids leaf shimmer.
function foliage(c,x,y,rx,ry,color,variant){
  c.fillStyle=color;c.beginPath();
  for(let n=0;n<=10;n++){
    const a=n/10*TAU,r=LOBES[(n+variant)%10],px=x+Math.cos(a)*rx*r,py=y+Math.sin(a)*ry*r;
    if(n===0)c.moveTo(px,py);else{const mid=(n-.5)/10*TAU;c.quadraticCurveTo(x+Math.cos(mid)*rx*1.1,y+Math.sin(mid)*ry*1.1,px,py);}
  }
  c.closePath();c.fill();
}

export function drawStreetTree(c,{x,y,k,r=1.5,variant=0,tint=identity,detail=true}){
  if(!valid(x,y,k)||!Number.isFinite(r)||r<=0)return;
  const v=variantIndex(variant,3),radius=Math.max(.55,Math.min(r,2.4)),near=detail&&k*radius>24;
  const height=2.9+v*.13,canopyY=-height,wide=radius*(v===1?.84:1),tall=radius*(v===1?1.08:.87),greens=GREEN[v];
  c.save();c.translate(x,y);c.scale(k,k);c.lineCap='round';c.lineJoin='round';shadow(c,radius*.78,.17);
  // Root flare and taper keep the tree planted on its sidewalk.
  shape(c,tint('#685e49'),[-.25,.01,-.095,-.34,-.073,-2.4,.045,-2.66,.125,-1.61,.112,-.3,.23,.008]);
  shape(c,tint('#928069'),[-.21,0,-.063,-.35,-.038,-2.42,.018,-2.57,.035,-.31,.095,0]);
  limb(c,0,-1.7,-.46,-2.46,.065,.026,tint('#75654e'));limb(c,.034,-1.95,.51,-2.67,.065,.024,tint('#625944'));
  limb(c,-.27,-2.18,-.6,-2.34,.034,.012,tint('#75654e'));
  if(near){line(c,tint('#514e3e'),.02,[.064,-.23,.058,-.81,.085,-1.13,.049,-1.65]);line(c,tint('#b09c7d'),.016,[-.049,-.18,-.065,-.94,-.027,-1.7]);}
  foliage(c,0,canopyY,wide,tall,tint(greens[0]),v);
  const count=near?CLUSTERS.length:6;
  for(let n=0;n<count;n++){
    const p=CLUSTERS[n],color=greens[n<2?1:n<5?2:n===5?1:n%3===0?3:2];
    foliage(c,p[0]*wide,canopyY+p[1]*tall,p[2]*wide,p[2]*tall*.83,tint(color),(n+v)%10);
  }
  if(near){
    // Broad small light-catching sprays, not individual expensive leaves.
    for(let n=0;n<5;n++){const p=CLUSTERS[n+2];foliage(c,p[0]*wide-.08*wide,canopyY+(p[1]-.11)*tall,.19*wide,.075*tall,tint(greens[3]),n);}
  }
  c.restore();
}

export function drawStreetScooter(c,{x,y,k,col='#81705e',helmet='#b1b4a1',front=false,tail=false,tint=identity,variant=0}){
  if(!valid(x,y,k))return;
  const v=variantIndex(variant,4),near=k>22,skin=tint(SKIN[v]),body=tint(col),bodyDark=tint(shade(col,.68));
  c.save();c.translate(x,y);c.scale(k,k);c.lineCap='round';c.lineJoin='round';shadow(c,.49,.095);
  // Tire, metal rim, fork and asymmetric exhaust establish depth below the fairing.
  oval(c,.018,-.225,.13,.235,tint('#272e30'));oval(c,.022,-.23,.063,.18,tint('#666d6c'));
  oval(c,.02,-.228,.035,.151,tint('#363e3e'));
  limb(c,-.085,-.51,-.069,-.2,.027,.026,tint('#8b9290'));limb(c,.085,-.51,.089,-.2,.027,.026,tint('#8b9290'));
  if(!front){limb(c,.3,-.55,.34,-.27,.053,.054,tint('#555c5c'));line(c,tint('#b4b7aa'),.028,[.305,-.53,.347,-.3]);}
  // Bent legs and shoes straddle the footwell.
  limb(c,-.155,-1.12,-.272,-.75,.089,.085,tint('#48515a'));limb(c,-.272,-.75,-.278,-.42,.085,.064,tint('#38444a'));
  limb(c,.155,-1.12,.272,-.75,.089,.085,tint('#566068'));limb(c,.272,-.75,.278,-.42,.085,.064,tint('#424e55'));
  oval(c,-.295,-.409,.114,.058,tint('#363d3e'));oval(c,.295,-.409,.114,.058,tint('#363d3e'));
  // Seat and moulded rear body panels.
  oval(c,0,-.952,.3,.127,tint('#343b3c'));
  c.fillStyle=bodyDark;c.beginPath();c.moveTo(-.29,-.91);c.bezierCurveTo(-.43,-.88,-.37,-.54,-.23,-.42);c.quadraticCurveTo(0,-.37,.23,-.42);c.bezierCurveTo(.37,-.54,.43,-.88,.29,-.91);c.closePath();c.fill();
  // Rider shoulders taper into the waist; helmet has a rim and shaded shell.
  c.fillStyle=body;c.beginPath();c.moveTo(-.07,-1.51);c.quadraticCurveTo(-.25,-1.51,-.29,-1.31);c.lineTo(-.19,-.99);c.quadraticCurveTo(0,-.91,.19,-.99);c.lineTo(.29,-1.31);c.quadraticCurveTo(.25,-1.51,.07,-1.51);c.closePath();c.fill();
  shape(c,bodyDark,[.12,-1.49,.26,-1.38,.19,-.99,.1,-.98,.12,-1.24]);
  limb(c,0,-1.64,0,-1.48,.059,.061,skin);
  oval(c,0,-1.687,.164,.182,skin);
  c.fillStyle=tint(helmet);c.beginPath();c.moveTo(-.191,-1.658);c.bezierCurveTo(-.21,-1.985,.21,-1.985,.191,-1.658);c.quadraticCurveTo(0,-1.616,-.191,-1.658);c.fill();
  c.fillStyle=tint(shade(helmet,.73));c.beginPath();c.moveTo(.055,-1.884);c.quadraticCurveTo(.209,-1.819,.191,-1.658);c.lineTo(.11,-1.64);c.quadraticCurveTo(.152,-1.805,.055,-1.884);c.fill();
  line(c,tint('#535b57'),.028,[-.19,-1.658,0,-1.635,.19,-1.658]);
  if(front){
    if(near){line(c,tint('#4b4940'),.018,[-.078,-1.621,-.045,-1.621]);line(c,tint('#4b4940'),.018,[.045,-1.621,.078,-1.621]);line(c,tint('#a37254'),.014,[-.032,-1.558,.029,-1.558]);}
  }else{shape(c,tint(shade(helmet,.82)),[-.13,-1.65,.13,-1.65,.11,-1.548,-.11,-1.548]);}
  // Elbows and hands reach the grips on both sides.
  for(const s of [-1,1]){
    limb(c,s*.23,-1.36,s*.33,-1.14,.079,.064,s<0?bodyDark:body);
    limb(c,s*.33,-1.14,s*.4,-1.185,.054,.042,skin);
    line(c,tint('#646e6d'),.027,[s*.35,-1.14,s*.43,-1.4]);
    oval(c,s*.459,-1.43,.089,.052,tint('#3c4849'),s*.18);
    oval(c,s*.459,-1.44,.065,.034,tint('#aabcb9'),s*.18);
  }
  line(c,tint('#323d3e'),.044,[-.43,-1.171,-.25,-1.13,.25,-1.13,.43,-1.171]);
  oval(c,-.399,-1.178,.058,.041,skin);oval(c,.399,-1.178,.058,.041,skin);
  if(front){
    c.fillStyle=body;c.beginPath();c.moveTo(-.258,-1.157);c.quadraticCurveTo(-.37,-1.098,-.26,-.91);c.lineTo(-.207,-.49);c.quadraticCurveTo(0,-.35,.207,-.49);c.lineTo(.26,-.91);c.quadraticCurveTo(.37,-1.098,.258,-1.157);c.quadraticCurveTo(0,-1.23,-.258,-1.157);c.fill();
    shape(c,bodyDark,[.16,-1.16,.29,-1.09,.26,-.91,.207,-.49,.098,-.453,.13,-.83]);
    oval(c,0,-1.096,.152,.071,tint('#596564'));oval(c,0,-1.098,.125,.052,tint('#e9e0b9'));
    line(c,tint('#c1b7a1'),.018,[-.087,-.938,0,-.969,.087,-.938]);
    if(near)line(c,tint(shade(col,.84)),.013,[0,-.875,0,-.53]);
  }else{
    c.fillStyle=body;c.beginPath();c.moveTo(-.274,-.878);c.quadraticCurveTo(0,-.932,.274,-.878);c.lineTo(.221,-.55);c.quadraticCurveTo(0,-.462,-.221,-.55);c.closePath();c.fill();
    line(c,tint('#a0a69b'),.025,[-.262,-.932,-.22,-.882,.22,-.882,.262,-.932]);
    shape(c,tint(tail?'#d46d50':'#98533e'),[-.132,-.809,.132,-.809,.105,-.714,-.105,-.714]);
    shape(c,tint('#d8d6c5'),[-.087,-.665,.087,-.665,.082,-.568,-.082,-.568]);
    if(near)line(c,tint('#626a62'),.013,[-.048,-.621,.046,-.621]);
  }
  c.restore();
}
