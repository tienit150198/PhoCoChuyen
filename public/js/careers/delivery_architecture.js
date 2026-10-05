/** Street-facing details for the courier's projected Canvas buildings.
 * All heights are world metres. Decoration stays on the existing building face;
 * the renderer retains ownership of walls, visibility, fog and collision.
 */
const AWNINGS = ['#657c70', '#a16c56', '#647b88', '#a18d66'];
const SHOP_NAMES = ['TẠP HÓA', 'CÀ PHÊ', 'TIỆM MAY'];

// Interpolation inside a projected face keeps reflections attached to its slant.
function onFace(s, u, v) {
  const x0=s[0][0]+(s[1][0]-s[0][0])*u, y0=s[0][1]+(s[1][1]-s[0][1])*u;
  const x1=s[3][0]+(s[2][0]-s[3][0])*u, y1=s[3][1]+(s[2][1]-s[3][1])*u;
  return [x0+(x1-x0)*v,y0+(y1-y0)*v];
}
function reflection(c,s,col) {
  if(!s)return;
  const p=[onFace(s,.08,.1),onFace(s,.24,.1),onFace(s,.76,.94),onFace(s,.51,.94)];
  c.beginPath();c.moveTo(...p[0]);for(let i=1;i<p.length;i++)c.lineTo(...p[i]);
  c.closePath();c.fillStyle=col;c.fill();
}

function windowPane(c,b,u0,u1,v0,v1,z,pal,H) {
  const {fquad:q}=H,t=pal.tint;
  if(z>=45){q(c,b,u0,u1,v0,v1,H.windowCol(pal));return;}
  const w=u1-u0,edge=Math.min(.018,w*.12),lit=pal.lamps>.45;
  // Recess, warm jambs, cool glass, then a sunlit sill give the flat wall depth.
  q(c,b,u0-edge,u1+edge,v0-.10,v1+.10,t('#635e55'));
  q(c,b,u0,u1,v0,v1,t('#d0c7b2'));
  const pane=q(c,b,u0+edge,u1-edge,v0+.09,v1-.09,lit?H.windowCol(pal):t('#587477'));
  if(z<32&&!lit)reflection(c,pane,t('#9aafb0'));
  q(c,b,u0+edge,u1-edge,v1-.21,v1-.09,t(lit?'#d6ba83':'#40575b'));
  const mid=(u0+u1)/2;
  q(c,b,mid-edge*.45,mid+edge*.45,v0+.08,v1-.08,t('#d4ccb8'));
  q(c,b,u0-edge*1.5,u1+edge*1.5,v0-.15,v0-.06,t('#b3a793'));
  q(c,b,u0-edge*1.5,u1+edge*1.5,v0-.06,v0+.015,t('#ede1c7'));
}

function awning(c,b,u0,u1,top,col,z,pal,H) {
  const q=H.fquad,t=pal.tint;
  q(c,b,u0,u1,top-.55,top-.17,t('#625f53'));
  q(c,b,u0,u1,top-.34,top,t(col));
  if(z<45){
    const width=(u1-u0)/10;
    for(let i=1;i<10;i+=2)q(c,b,u0+i*width,u0+(i+1)*width,top-.34,top,t('#ded5bc'));
    q(c,b,u0,u1,top-.38,top-.29,t(H.shade(col,.77)));
    q(c,b,u0,u1,top-.025,top+.045,t('#e4d8bd'));
  }
}

function planter(c,b,u,v,pal,H) {
  const q=H.fquad,t=pal.tint;
  q(c,b,u-.038,u+.038,v,v+.32,t('#92664e'));
  q(c,b,u-.047,u+.047,v+.27,v+.35,t('#bf8b67'));
  q(c,b,u-.045,u+.015,v+.34,v+.68,t('#536c45'));
  q(c,b,u-.008,u+.048,v+.35,v+.59,t('#70845a'));
  q(c,b,u-.024,u+.015,v+.52,v+.79,t('#7e8e60'));
}

export function drawHouseFacade(c,b,z,pal,H) {
  const q=H.fquad,t=pal.tint,base=b.zb||0,top=base+b.h;
  const no=Math.abs(Math.trunc(Number(b.no)||0)),variant=no%4,near=z<45;
  // A 5.5 m tube house still has room for one upper row of windows.
  const floors=Math.max(1,Math.floor((b.h-2.36)/3)+1),accent=AWNINGS[variant];
  c.save();
  try {
    // Weathered plinth, pale edge pillars and a layered cornice unify each house.
    q(c,b,0,1,base,base+.32,t(H.shade(b.col,.70)));
    q(c,b,.025,.065,base+.32,top-.22,t(H.shade(b.col,1.06)));
    q(c,b,.935,.975,base+.32,top-.22,t(H.shade(b.col,.83)));
    q(c,b,0,1,top-.27,top-.12,t(H.shade(b.col,.72)));
    q(c,b,0,1,top-.12,top,t('#ddd1b7'));
    if(b.shop){
      q(c,b,.10,.90,base+.04,base+2.54,t('#514f49'));
      if(near){
        q(c,b,.13,.33,base+.12,base+2.20,t('#354f50'));
        const s=q(c,b,.38,.86,base+.45,base+2.2,pal.lamps>.45?H.windowCol(pal):t('#738c88'));
        if(z<32&&pal.lamps<=.45)reflection(c,s,t('#acbab0'));
        q(c,b,.13,.86,base+1.00,base+1.05,t('#cec3ab'));
        q(c,b,.34,.38,base+.10,base+2.21,t('#d0c3aa'));
        q(c,b,.61,.625,base+.45,base+2.21,t('#c0b69f'));
        q(c,b,.12,.89,base+.1,base+.25,t('#b6aa90'));
        const sign=q(c,b,.12,.88,base+2.22,base+2.58,t(accent));
        if(sign&&z<30)H.label(c,sign,SHOP_NAMES[no%3],t('#f0e6ce'));
      }
    }else{
      q(c,b,.16,.65,base+.04,base+2.40,t('#514c42'));
      q(c,b,.19,.62,base+.08,base+2.24,t(variant%2?'#7d8272':'#8b7963'));
      if(near){
        q(c,b,.20,.61,base+1.76,base+2.16,t('#394c48'));
        for(let k=0;k<4;k++)q(c,b,.24+k*.095,.25+k*.095,base+.20,base+2.15,t('#a79b80'));
        q(c,b,.19,.62,base+.62,base+.67,t('#655e50'));
        q(c,b,.19,.62,base+1.7,base+1.75,t('#b4aa92'));
        q(c,b,.49,.515,base+1.05,base+1.16,t('#d0b67b'));
        q(c,b,.13,.68,base,base+.10,t('#c7bca5'));
      }
    }
    if(b.awn)awning(c,b,.07,.93,base+2.96,accent,z,pal,H);
    if(z<78)for(let f=1;f<floors;f++){
      const v=base+f*3+.65;
      if(near){
        q(c,b,.065,.935,base+f*3-.1,base+f*3+.04,t(H.shade(b.col,.77)));
        q(c,b,.065,.935,base+f*3+.04,base+f*3+.13,t('#dbcfb8'));
      }
      if(b.win===1)windowPane(c,b,.30,.70,v,v+1.44,z,pal,H);
      else{windowPane(c,b,.14,.43,v,v+1.44,z,pal,H);windowPane(c,b,.57,.86,v,v+1.44,z,pal,H);}
      if(near&&b.win===2&&f===1){
        q(c,b,.085,.915,base+3.06,base+3.19,t('#79786a'));
        q(c,b,.08,.92,base+3.17,base+3.25,t('#d4c7ad'));
        for(let k=0;k<8;k++)q(c,b,.12+k*.108,.132+k*.108,base+3.25,base+3.83,t('#52665e'));
        q(c,b,.09,.91,base+3.81,base+3.88,t('#53675f'));
        if(z<28&&variant===1)planter(c,b,.75,base+3.26,pal,H);
      }
    }
    if(z<28){
      if(variant===0&&b.h>6){
        q(c,b,.69,.88,base+5.22,base+5.78,t('#766f60'));
        q(c,b,.67,.87,base+5.3,base+5.82,t('#d4cdb8'));
        for(let k=0;k<3;k++)q(c,b,.70,.84,base+5.39+k*.1,base+5.42+k*.1,t('#918f80'));
        q(c,b,.84,.855,base+4.80,base+5.30,t('#b2aa94'));
      }
      if(variant!==2)planter(c,b,.89,base+.10,pal,H);
    }
    if(b.no&&z<45){
      const s=q(c,b,.71,.88,base+1.77,base+2.19,t('#315d78'));
      if(s)H.label(c,s,String(b.no),'#f5eddb');
    }
  }finally{c.restore();}
}

export function drawLandmarkFacade(c,b,z,pal,H) {
  const q=H.fquad,t=pal.tint,base=b.zb||0,top=base+b.h,near=z<45,L=b.L;
  c.save();
  try {
    if(b.pump){
      q(c,b,.12,.88,base+.7,base+1.42,t('#dedbc8'));
      q(c,b,.21,.79,base+.96,base+1.29,t('#314843'));
      if(near){q(c,b,.29,.70,base+1.07,base+1.15,t('#b3c7ac'));q(c,b,.72,.84,base+.3,base+.82,t('#303c37'));}
      return;
    }
    if(b.canopy){
      q(c,b,0,1,base+.06,base+.16,t('#f1ddba'));
      q(c,b,0,1,top-.16,top-.07,t('#dfb696'));
      return;
    }
    if(b.arch){
      q(c,b,.025,.975,base+.07,top-.08,t('#8b4838'));
      q(c,b,0,1,top-.12,top,t('#d9b77c'));
      const s=q(c,b,.10,.90,base+.15,top-.18,t('#783c30'));
      if(s&&L)H.label(c,s,L.name,'#ffe7a8');
      return;
    }
    q(c,b,0,1,base,base+.24,t(H.shade(b.col,.72)));
    q(c,b,0,1,top-.23,top-.12,t(H.shade(b.col,.76)));
    q(c,b,0,1,top-.12,top,t('#ded2bb'));
    if(near){q(c,b,.02,.045,base+.24,top-.23,t(H.shade(b.col,1.09)));q(c,b,.955,.98,base+.24,top-.23,t(H.shade(b.col,.85)));}
    if(b.tower){
      const fl=Math.floor(b.h/3);
      for(let f=1;f<fl&&z<80;f++){
        const v=base+f*3+.6;
        if(near)q(c,b,.04,.96,base+f*3+.04,base+f*3+.18,t('#b8b7a9'));
        for(let k=0;k<4;k++)windowPane(c,b,.065+k*.235,.225+k*.235,v,v+1.5,z,pal,H);
      }
      q(c,b,.37,.63,base,base+2.7,t('#465a5b'));
      if(near){q(c,b,.495,.505,base+.05,base+2.6,t('#bfbea9'));q(c,b,.33,.67,base,base+.12,t('#c9c3b2'));}
    }
    if(b.shopfront||b.open||b.stalls){
      q(c,b,.07,.93,base+.06,base+2.75,t(b.open?'#39443f':'#59594d'));
      if(b.shopfront&&z<65){
        windowPane(c,b,.14,.46,base+.55,base+2.40,z,pal,H);
        windowPane(c,b,.54,.86,base+.15,base+2.40,z,pal,H);
      }
      if(b.open&&near){
        q(c,b,.09,.91,base+2.3,base+2.72,t('#64685b'));
        q(c,b,.11,.89,base+.08,base+.21,t('#aaa18c'));
        q(c,b,.13,.32,base+.38,base+1.30,t('#6b7467'));
        q(c,b,.64,.85,base+.30,base+.73,t('#9b8466'));
      }
    }
    if(b.stalls)for(let k=0;k<4;k++){
      const u=.05+k*.24,col=['#b89253','#84925c','#b67b64','#c7b36d'][k];
      q(c,b,u,u+.20,base+.45,base+1.22,t('#92775c'));
      q(c,b,u-.01,u+.21,base+1.16,base+1.36,t(col));
      if(near){q(c,b,u,u+.2,base+.65,base+.69,t('#beaa84'));q(c,b,u+.025,u+.075,base+1.34,base+1.55,t(col));q(c,b,u+.10,u+.18,base+1.34,base+1.49,t(H.shade(col,1.13)));}
    }
    if(b.awn)awning(c,b,.02,.98,base+3.26,b.awn,z,pal,H);
    if(b.win&&!b.tower){
      const fl=Math.max(1,Math.floor(b.h/3));
      for(let f=b.gate?0:1;f<fl&&z<80;f++){
        const v=base+f*3+.7;
        for(let k=0;k<b.win;k++){const u=(k+.5)/b.win;windowPane(c,b,u-.12,u+.12,v,v+1.4,z,pal,H);}
      }
    }
    if(b.gate){
      q(c,b,.34,.66,base,base+2.1,t('#4e5d4d'));
      if(near){
        for(let k=0;k<7;k++)q(c,b,.36+k*.045,.368+k*.045,base+.1,base+2.07,t('#a99874'));
        q(c,b,.33,.36,base,base+2.2,t('#d3c4a7'));q(c,b,.64,.67,base,base+2.2,t('#d3c4a7'));
        q(c,b,.35,.65,base+.62,base+.70,t('#a99874'));
      }
    }
    if(!b.sign)return;
    const signTop=base+(b.h>9?Math.min(b.h-.4,6.8):b.h-.3);
    if(near){q(c,b,.045,.955,signTop-1.71,signTop+.06,t('#766f5d'));q(c,b,.055,.945,signTop-1.65,signTop+.02,t('#d3c2a0'));}
    const sign=q(c,b,.06,.94,signTop-1.6,signTop,t('#f2e9d4'));
    if(sign&&L)H.label(c,sign,`${L.emoji} ${L.name}`,'#433b2c');
  }finally{c.restore();}
}
