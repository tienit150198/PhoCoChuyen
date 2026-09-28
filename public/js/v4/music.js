/** Generative background music (WebAudio, no audio files, no network).
 * Each career has its own key, tempo and instrument; the shop being open adds
 * a soft rhythm. Everything is synthesised live, so it never repeats exactly. */
const NOTE=n=>440*Math.pow(2,(n-69)/12);
const MODES={major:[0,2,4,7,9],minor:[0,3,5,7,10],lydian:[0,2,4,6,7,9,11],dorian:[0,2,3,5,7,9,10]};
const PROGRESSIONS={major:[[0,4,7,11],[9,12,16,19],[5,9,12,16],[7,11,14,17]],minor:[[0,3,7,10],[5,8,12,15],[3,7,10,14],[7,10,14,17]]};
const STYLE={
  default:{root:60,mode:'major',bpm:78,inst:'keys'},
  mother_baby:{root:65,mode:'major',bpm:76,inst:'bell'},pharmacy:{root:62,mode:'major',bpm:70,inst:'keys'},
  accounting:{root:57,mode:'dorian',bpm:84,inst:'pluck'},customer_care:{root:60,mode:'major',bpm:80,inst:'keys'},
  teacher:{root:67,mode:'major',bpm:88,inst:'bell'},tour_guide:{root:62,mode:'lydian',bpm:92,inst:'pluck'},
  milk_tea:{root:64,mode:'major',bpm:82,inst:'bell'},restaurant:{root:62,mode:'dorian',bpm:96,inst:'pluck'},
  cafe_bakery:{root:58,mode:'major',bpm:72,inst:'keys'},florist:{root:65,mode:'lydian',bpm:70,inst:'bell'},
  grocery:{root:60,mode:'major',bpm:90,inst:'pluck'},repair:{root:55,mode:'dorian',bpm:86,inst:'pluck'},
  farm:{root:62,mode:'major',bpm:74,inst:'pluck'},delivery:{root:57,mode:'minor',bpm:100,inst:'pluck'},
  homestay:{root:60,mode:'lydian',bpm:66,inst:'keys'},pet_care:{root:67,mode:'major',bpm:84,inst:'bell'},
  salon:{root:63,mode:'dorian',bpm:88,inst:'keys'},corp_accounting:{root:57,mode:'minor',bpm:78,inst:'keys'},
  tax_payroll:{root:59,mode:'dorian',bpm:80,inst:'keys'},group_accounting:{root:55,mode:'minor',bpm:74,inst:'keys'},
};

export class Music{
  constructor(){this.ctx=null;this.on=false;this.volume=.45;this.hidden=false;this.style=STYLE.default;this.step=0;this.bar=0;this.timer=null;this.open=false;this.rand=Math.random;}
  unlock(){if(this.ctx?.state==='suspended')this.ctx.resume();this.refresh();}
  setHidden(h){this.hidden=h;this.refresh();}
  configure({on,volume,track,career,open}){
    this.on=!!on&&track!=='off';this.volume=Math.max(0,Math.min(1,(volume??45)/100));this.open=!!open;
    let st={...(STYLE[career]||STYLE.default)};
    if(track==='calm'){st.bpm=Math.round(st.bpm*.8);st.inst='keys';}
    if(track==='bright'){st.bpm=Math.round(st.bpm*1.15);st.mode=st.mode==='minor'?'dorian':st.mode;}
    this.style=st;
    if(this.master)this.master.gain.setTargetAtTime(this.volume*.32,this.ctx.currentTime,.3);
    this.refresh();
  }
  init(){
    if(this.ctx)return;
    const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;
    const c=this.ctx=new AC();
    this.master=c.createGain();this.master.gain.value=this.volume*.32;
    const lp=c.createBiquadFilter();lp.type='lowpass';lp.frequency.value=3200;lp.Q.value=.4;
    const delay=c.createDelay(1);delay.delayTime.value=.33;const fb=c.createGain();fb.gain.value=.28;const wet=c.createGain();wet.gain.value=.22;
    this.bus=c.createGain();this.bus.connect(lp);lp.connect(this.master);this.master.connect(c.destination);
    this.bus.connect(delay);delay.connect(fb);fb.connect(delay);delay.connect(wet);wet.connect(this.master);
    this.noise=c.createBuffer(1,c.sampleRate*.2,c.sampleRate);const d=this.noise.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;
  }
  refresh(){
    const play=this.on&&!this.hidden;
    if(play){this.init();if(!this.ctx)return;if(this.ctx.state==='suspended')this.ctx.resume().catch(()=>{});if(!this.timer){this.next=this.ctx.currentTime+.1;this.timer=setInterval(()=>this.schedule(),60);}}
    else if(this.timer){clearInterval(this.timer);this.timer=null;}
  }
  schedule(){
    const c=this.ctx;if(!c)return;
    const spb=60/this.style.bpm/4;
    while(this.next<c.currentTime+.18){this.tick(this.next,spb);this.next+=spb;this.step=(this.step+1)%16;if(this.step===0)this.bar=(this.bar+1)%4;}
  }
  tick(time,spb){
    const st=this.style,prog=PROGRESSIONS[st.mode==='minor'||st.mode==='dorian'?'minor':'major'],chord=prog[this.bar];
    if(this.step===0){chord.forEach((n,i)=>this.pad(NOTE(st.root-12+n),time,spb*16,i));this.bass(NOTE(st.root-24+chord[0]),time,spb*6);}
    if(this.step===8&&this.rand()<.7)this.bass(NOTE(st.root-24+chord[this.rand()<.5?0:2]),time,spb*4);
    const scale=MODES[st.mode],density=this.open?.34:.2;
    if(this.step%2===0&&this.rand()<density){
      const deg=scale[Math.floor(this.rand()*scale.length)],oct=this.rand()<.3?12:0;
      this.lead(NOTE(st.root+deg+oct),time,spb*(this.rand()<.3?4:2));
    }
    if(this.open&&this.step%4===2)this.hat(time,this.step===10?.05:.03);
    if(this.open&&(this.step===0||this.step===8))this.kick(time);
  }
  env(g,time,a,peak,dur){g.gain.setValueAtTime(0,time);g.gain.linearRampToValueAtTime(peak,time+a);g.gain.exponentialRampToValueAtTime(.0001,time+dur);}
  pad(f,time,dur,i){
    const c=this.ctx,g=c.createGain();this.env(g,time,.8,.035,dur*1.05);g.connect(this.bus);
    for(const det of[-6,6]){const o=c.createOscillator();o.type='triangle';o.frequency.value=f;o.detune.value=det+i;o.connect(g);o.start(time);o.stop(time+dur*1.1);}
  }
  bass(f,time,dur){const c=this.ctx,o=c.createOscillator(),g=c.createGain();o.type='sine';o.frequency.value=f;this.env(g,time,.02,.12,dur);o.connect(g);g.connect(this.bus);o.start(time);o.stop(time+dur+.05);}
  lead(f,time,dur){
    const c=this.ctx,g=c.createGain(),inst=this.style.inst;g.connect(this.bus);
    const o=c.createOscillator();o.frequency.value=f;
    if(inst==='bell'){o.type='sine';const m=c.createOscillator(),mg=c.createGain();m.frequency.value=f*3.5;mg.gain.value=f*.6;m.connect(mg);mg.connect(o.frequency);m.start(time);m.stop(time+dur*2);this.env(g,time,.005,.06,dur*2);}
    else if(inst==='pluck'){o.type='triangle';this.env(g,time,.004,.08,dur*1.2);}
    else{o.type='sine';const o2=c.createOscillator();o2.type='sine';o2.frequency.value=f*2;const g2=c.createGain();g2.gain.value=.25;o2.connect(g2);g2.connect(g);o2.start(time);o2.stop(time+dur*1.6);this.env(g,time,.01,.07,dur*1.5);}
    o.connect(g);o.start(time);o.stop(time+dur*2.1);
  }
  hat(time,vol){const c=this.ctx,s=c.createBufferSource(),f=c.createBiquadFilter(),g=c.createGain();s.buffer=this.noise;f.type='highpass';f.frequency.value=7000;this.env(g,time,.001,vol,.06);s.connect(f);f.connect(g);g.connect(this.bus);s.start(time);s.stop(time+.08);}
  kick(time){const c=this.ctx,o=c.createOscillator(),g=c.createGain();o.frequency.setValueAtTime(110,time);o.frequency.exponentialRampToValueAtTime(45,time+.12);this.env(g,time,.002,.09,.18);o.connect(g);g.connect(this.bus);o.start(time);o.stop(time+.2);}
}
