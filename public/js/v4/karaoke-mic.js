/** 🎙️ Phòng hát mic trực tiếp (live/karaoke.py kara_mic / kara_listen, live/sfu.py; switch LIVE_KARAOKE_MIC).
 * Loaded by v4/karaoke.js only while the live service's welcome says `kara_mic` and a mic is in play.
 * The LiveKit browser SDK is ONE pinned file, checked with SRI: first our own copy (public/js/vendor/, the game's
 * origin, which every player already reaches), then the same bytes from jsDelivr (server.py KARA_MIC_SDK, the only
 * script source the page's CSP adds for it). 07/10: the one listener of the day never reached the SFU after its
 * token; the third-party CDN was the only step between (a network that cannot reach it hangs the script for good).
 * The singer publishes the microphone only (echo cancellation and noise suppression on, music preset, no DTX, no
 * RED: over TCP it only doubles the bytes); a listener subscribes only. Nothing is recorded: no MediaRecorder, no file.
 * The singer's voice plays in the page (Web Audio, so its volume works on iPhone too) over the YouTube player, whose
 * own volume stays the listener's: we never touch it.
 *
 * Stages (`onStage(name)`, for the page's state and its error beacon): sdk → signal (the SFU's WebSocket) → ice
 * (the media path, ICE/TCP on the production server) → track (listener: the voice subscribed; singer: published).
 * A failure throws an Error with `.stage` (the step that failed) and `.code` (short, no text of the player). */
export const SDK={urls:['/js/vendor/livekit-client-2.22.3.umd.js','https://cdn.jsdelivr.net/npm/livekit-client@2.22.3/dist/livekit-client.umd.js'],
  sri:'sha384-G/xxtkVytOx/ia9Q8MXxM+V0ohsaY1fZAgVP3iSGTPz4wJ0s3+ulJNKXh/gnzEDZ'};
const SDK_MS=15000,TRACK_MS=12000;
let sdk=null;

/** An Error that says where the mic path stopped. */
export function fail(stage,code,cause){
  const e=new Error(`${stage}: ${code}`);e.stage=stage;e.code=String(code||'?').slice(0,60);if(cause)e.cause=cause;return e;
}
/** A short code for any error (a LiveKit ConnectionError has a reason number and maybe an HTTP status). */
export function codeOf(err){
  if(!err)return '?';
  if(err.code&&err.stage)return err.code;
  const bits=[err.name&&err.name!=='Error'?err.name:'',err.reason!=null&&err.reason!==''?`r${err.reason}`:'',err.status?`s${err.status}`:''].filter(Boolean);
  const msg=String(err.message||'').replace(/https?:\/\/\S+/g,'').replace(/\s+/g,' ').trim().slice(0,48);
  return (bits.join(' ')+(msg?` ${msg}`:'')).trim().slice(0,72)||'?';
}
const tag=(err,stage)=>{if(err&&typeof err==='object'&&!err.stage){err.stage=stage;err.code=codeOf(err);}return err&&typeof err==='object'?err:fail(stage,String(err));};

function script(url){
  return new Promise((ok,bad)=>{
    const s=document.createElement('script');s.src=url;s.integrity=SDK.sri;s.crossOrigin='anonymous';s.referrerPolicy='no-referrer';s.async=true;
    const done=()=>{clearTimeout(t);s.onload=s.onerror=null;};
    const t=setTimeout(()=>{done();bad('timeout');},SDK_MS);   // a hung CDN: try the next copy (if this one lands later, fine)
    s.onload=()=>{done();window.LivekitClient?.Room?ok(window.LivekitClient):bad('noglobal');};
    s.onerror=()=>{done();s.remove();bad('load');};
    document.head.append(s);
  });
}
/** window.LivekitClient, once: our copy, else jsDelivr (a failed load may be retried later). */
export function loadSDK(){
  if(window.LivekitClient?.Room)return Promise.resolve(window.LivekitClient);
  if(!sdk)sdk=(async()=>{
    const why=[];
    for(const u of SDK.urls){
      try{return await script(u);}catch(w){why.push((u.startsWith('/')?'self ':'cdn ')+w);if(window.LivekitClient?.Room)return window.LivekitClient;}
    }
    throw fail('sdk',why.join(', '));
  })().catch(e=>{sdk=null;throw e;});
  return sdk;
}

export const canSing=()=>!!(navigator.mediaDevices?.getUserMedia&&window.RTCPeerConnection);

/** room.connect, split into its two stages: the signal WebSocket, then the media path (ICE). */
async function join(LK,room,url,token,opts,onStage){
  let signal=false;
  const seen=()=>{signal=true;onStage?.('signal');};
  room.once(LK.RoomEvent.SignalConnected,seen);
  try{await room.connect(url,token,opts);}
  catch(e){throw tag(e,signal?'ice':'signal');}
  finally{room.off(LK.RoomEvent.SignalConnected,seen);}
  if(!signal)onStage?.('signal');
  onStage?.('ice');
}

/** The singer: the permission prompt, then the SFU, then the microphone track. Resolves to {stop, room, track, stats}. */
export async function publish({url,token,onEnd,onStage}){
  const LK=await loadSDK();onStage?.('sdk');
  let track;
  try{track=await LK.createLocalAudioTrack({echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1});}
  catch(e){throw tag(e,'perm');}
  onStage?.('perm');
  const room=new LK.Room({adaptiveStream:false,dynacast:false,disconnectOnPageLeave:true,stopLocalTrackOnUnpublish:true});
  let done=false;
  const stop=()=>{if(done)return;done=true;try{track.stop();}catch{/* gone */}room.disconnect().catch(()=>{});};
  room.on(LK.RoomEvent.Disconnected,(reason)=>{const was=done;stop();if(!was)onEnd?.('sfu',reason);});
  try{
    await join(LK,room,url,token,{autoSubscribe:false},onStage);
    try{await room.localParticipant.publishTrack(track,{source:LK.Track.Source.Microphone,audioPreset:LK.AudioPresets.music,dtx:false,red:false});}
    catch(e){throw tag(e,'track');}
    onStage?.('track');
  }catch(e){stop();throw tag(e,'signal');}
  return {stop,room,track,stats:()=>rtp(track,'outbound-rtp'),path:()=>path(track)};
}

/** A listener: the singer's voice, at `volume` (0..1). Resolves once the voice is subscribed. `onTap(true)` when the
 * phone needs a tap to play sound (iPhone: a new AudioContext starts suspended). */
export async function listen({url,token,volume=1,onTap,onEnd,onStage}){
  const LK=await loadSDK();onStage?.('sdk');
  const room=new LK.Room({adaptiveStream:false,dynacast:false,webAudioMix:true,disconnectOnPageLeave:true});
  let done=false,vol=volume,muted=false,voice=null,got=null;
  const first=new Promise(ok=>{got=ok;});
  const apply=()=>{for(const p of room.remoteParticipants.values())try{p.setVolume(muted?0:vol);}catch{/* not yet */}};
  const stop=()=>{if(done)return;done=true;got?.(null);try{voice?.detach().forEach(el=>el.remove());}catch{/* gone */}voice=null;room.disconnect().catch(()=>{});};
  room.on(LK.RoomEvent.TrackSubscribed,(track)=>{if(track.kind!=='audio')return;voice=track;const el=track.attach();el.hidden=true;el.dataset.krVoice='1';document.body.append(el);apply();got?.(track);});
  room.on(LK.RoomEvent.TrackUnsubscribed,(track)=>{try{track.detach().forEach(el=>el.remove());}catch{/* gone */}if(voice===track)voice=null;});
  room.on(LK.RoomEvent.AudioPlaybackStatusChanged,()=>onTap?.(!room.canPlaybackAudio));
  room.on(LK.RoomEvent.Disconnected,(reason)=>{const was=done;stop();if(!was)onEnd?.('sfu',reason);});
  try{
    await join(LK,room,url,token,{autoSubscribe:true},onStage);
    let timer=0;
    const t=await Promise.race([first,new Promise(ok=>{timer=setTimeout(()=>ok(undefined),TRACK_MS);})]);
    clearTimeout(timer);
    if(t===null)throw fail('track','gone');           // stopped (or the SFU dropped us) while waiting
    if(t===undefined)throw fail('track','none');      // connected, but no voice to subscribe to
    onStage?.('track');
  }catch(e){stop();throw tag(e,'signal');}
  onTap?.(!room.canPlaybackAudio);
  return {stop,room,
    setVolume(v){vol=Math.max(0,Math.min(1,Number(v)||0));apply();},
    mute(on){muted=!!on;apply();},
    tap(){return room.startAudio();},   // inside a click: iPhone plays sound after it
    canPlay:()=>!!room.canPlaybackAudio,
    stats:()=>voice?rtp(voice,'inbound-rtp'):Promise.resolve(null),
    path:()=>voice?path(voice):Promise.resolve(null),
    delay:()=>voice?delay(voice):Promise.resolve(null),
    heard:()=>!!voice};
}

/** For the checks: the network path the voice takes (udp / tcp; host / relay), from getStats. */
async function path(track){
  try{
    const rep=await track.getRTCStatsReport?.();if(!rep)return null;
    let pair=null;for(const s of rep.values())if(s.type==='candidate-pair'&&s.state==='succeeded'&&(s.nominated||!pair))pair=s;
    const loc=pair&&rep.get(pair.localCandidateId),rem=pair&&rep.get(pair.remoteCandidateId);
    let back=null;for(const s of rep.values())if(s.type==='remote-inbound-rtp'&&Number.isFinite(s.roundTripTime))back=s.roundTripTime;   // a sender's own report
    return pair?{protocol:loc?.protocol||rem?.protocol,local:loc?.candidateType,remote:rem?.candidateType,rtt:pair.currentRoundTripTime??back}:back!==null?{rtt:back}:null;
  }catch{return null;}
}
/** For the voice's delay (lagStep): the jitter buffer's running totals and the media path's round trip, raw. */
async function delay(track){
  try{
    const rep=await track.getRTCStatsReport?.();if(!rep)return null;
    let jbd,jbn,pair=null;
    for(const s of rep.values()){
      if(s.type==='inbound-rtp'&&(s.kind==='audio'||s.mediaType==='audio')){jbd=s.jitterBufferDelay;jbn=s.jitterBufferEmittedCount;}
      else if(s.type==='candidate-pair'&&s.state==='succeeded'&&(s.nominated||!pair))pair=s;
    }
    return {jbd,jbn,rtt:pair?.currentRoundTripTime};
  }catch{return null;}
}
/** The RTP counters of the track (packets and bytes), from getStats: the "audio flows" stage and the checks. */
async function rtp(track,type){
  try{
    const rep=await track.getRTCStatsReport?.();if(!rep)return null;
    for(const s of rep.values())if(s.type===type&&(s.kind==='audio'||s.mediaType==='audio'))return {packets:s.packetsReceived??s.packetsSent??0,bytes:s.bytesReceived??s.bytesSent??0};
  }catch{/* closed */}
  return null;
}

/* ---------------------------------------------------------------- 🎙️ voice and music together (07/10 "bị delay xíu")
 * The singer sings to their OWN video; the voice reaches a listener `voiceLag` seconds later. So while a listener
 * hears the voice, their video follows the singer's (kara_vt: its time `vt` at server time `at`, relayed by the live
 * service) minus that delay, instead of the shared server clock. Pure functions: v4/karaoke.js sync() and the tests. */
export const LAG={base:.04,guess:.2,max:1.5,fresh:3,span:15,a:.3};
const num=Number.isFinite;
/** One getStats reading (delay(): {jbd, jbn, rtt}) into the running estimate `s` ({} at first): the jitter buffer's
 * delay over the samples played since the last reading (Δ jitterBufferDelay / Δ jitterBufferEmittedCount, seconds;
 * the first reading: since the voice was subscribed), and the path's round trip, each smoothed (factor LAG.a). A
 * reading without the counters changes nothing. */
export function lagStep(s,raw){
  const o={...s};if(!raw)return o;
  if(num(raw.jbd)&&num(raw.jbn)){
    const d0=num(s.jbd)?s.jbd:0,n0=num(s.jbn)?s.jbn:0;
    if(raw.jbn>n0&&raw.jbd>=d0){const x=(raw.jbd-d0)/(raw.jbn-n0);if(x>=0&&x<LAG.max*2)o.jb=num(s.jb)?s.jb+(x-s.jb)*LAG.a:x;}
    o.jbd=raw.jbd;o.jbn=raw.jbn;
  }
  if(num(raw.rtt)&&raw.rtt>=0&&raw.rtt<5)o.rtt=num(s.rtt)?s.rtt+(raw.rtt-s.rtt)*LAG.a:raw.rtt;
  return o;
}
/** Seconds from the singer's mouth to my ear: capture and encode (LAG.base), half the singer's round trip to the SFU
 * (`up`, seconds, theirs when the frame carried it, else as mine), half of mine, and my jitter buffer (LAG.guess
 * until getStats has one). Within 0..LAG.max. */
export function voiceLag(s,up){
  const mine=num(s?.rtt)?s.rtt:0,theirs=num(up)&&up>=0?up:mine;
  return Math.max(0,Math.min(LAG.max,LAG.base+(num(s?.jb)?s.jb:LAG.guess)+(mine+theirs)/2));
}
/** Where my video should be now. `clock` the shared server-clock position (pos()), `vt` the last kara_vt
 * ({vt, at, r?}), `now` my server-clock time, `age` seconds since it came, `lag` voiceLag(), `voice` true while I hear
 * the voice. Following: vt + (now − at) × r − lag (r: the singer's playback rate while their own sync nudges it),
 * only with a fresh vt (under LAG.fresh s) and the voice playing, and never more than LAG.span from the clock;
 * otherwise the clock, exactly as without a mic. */
export function followTarget({clock,vt,now,age,lag,voice}){
  if(!voice||!vt||!num(vt.vt)||!num(vt.at)||!num(now)||!(age>=0&&age<LAG.fresh))return {t:clock,voice:false};
  const r=num(vt.r)&&vt.r>=.5&&vt.r<=2?vt.r:1;
  const t=vt.vt+Math.max(0,Math.min(age+LAG.fresh,now-vt.at))*r-(num(lag)?lag:0);
  return num(t)&&Math.abs(t-clock)<=LAG.span?{t,voice:true}:{t:clock,voice:false};
}
/** A delay in ms as one letter for the error beacon, whose server masks digits: a 0–99, b 100–199, … p ≥ 1500. */
export const bucket=ms=>num(ms)?String.fromCharCode(97+Math.max(0,Math.min(15,Math.floor(ms/100)))):'-';
