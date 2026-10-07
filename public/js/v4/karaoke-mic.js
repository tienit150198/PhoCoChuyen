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
  return {stop,room,track,stats:()=>rtp(track,'outbound-rtp')};
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
    heard:()=>!!voice};
}

/** For the checks: the network path the voice takes (udp / tcp; host / relay), from getStats. */
async function path(track){
  try{
    const rep=await track.getRTCStatsReport?.();if(!rep)return null;
    let pair=null;for(const s of rep.values())if(s.type==='candidate-pair'&&s.state==='succeeded'&&(s.nominated||!pair))pair=s;
    const loc=pair&&rep.get(pair.localCandidateId),rem=pair&&rep.get(pair.remoteCandidateId);
    return pair?{protocol:loc?.protocol||rem?.protocol,local:loc?.candidateType,remote:rem?.candidateType,rtt:pair.currentRoundTripTime??null}:null;
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
