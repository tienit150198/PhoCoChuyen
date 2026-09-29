/** Tiny original synthesised sounds. No audio files or third-party recordings. */
export class Sound {
  constructor(){this.ctx=null;this.enabled=true;this.volume=1;}
  /** Create the (suspended) context ahead of time, in idle time: creating it is slow on phones (~100 ms
   * on a throttled CPU) and used to land on the player's very first tap. unlock() then only resumes it. */
  prepare(){try{this.ctx??=new (window.AudioContext||window.webkitAudioContext)();}catch{/* no Web Audio */}}
  unlock(){try{this.ctx??=new (window.AudioContext||window.webkitAudioContext)();if(this.ctx.state==='suspended')this.ctx.resume();}catch{/* Silent play remains fully usable. */}}
  tone(freq,time=.08,volume=.045,delay=0,type='sine'){
    if(!this.ctx||!this.enabled)return;const t=this.ctx.currentTime+delay,o=this.ctx.createOscillator(),g=this.ctx.createGain();o.type=type;o.frequency.value=freq;g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(volume*this.volume,t+.015);g.gain.exponentialRampToValueAtTime(.0001,t+time);o.connect(g);g.connect(this.ctx.destination);o.start(t);o.stop(t+time+.03);
  }
  click(){this.tone(660,.07,.024);}
  success(){[523.25,659.25,783.99,1046.5].forEach((f,i)=>this.tone(f,.36,.038,i*.11));}
  error(){this.tone(245,.14,.03);}
  // Background music lives in v4/music.js; this class only plays short UI sounds.
  configure(settings){this.enabled=settings.sound!==false;this.volume=Math.max(0,Math.min(1.5,(settings.sfxVolume??70)/70));}
  stopMusic(){}
}
