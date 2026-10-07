/** 🎙️ Phòng hát mic trực tiếp (live/karaoke.py kara_mic / kara_listen, live/sfu.py; switch LIVE_KARAOKE_MIC).
 * Loaded by v4/karaoke.js only while the live service's welcome says `kara_mic` and a mic is in play.
 * The LiveKit browser SDK is ONE pinned file from jsDelivr, checked with SRI (server.py KARA_MIC_SDK is the only
 * script source the page's CSP adds for it). The singer publishes the microphone only (echo cancellation and noise
 * suppression on, music preset, no DTX, no RED: over TCP it only doubles the bytes); a listener subscribes only. Nothing is recorded: no MediaRecorder, no file.
 * The singer's voice plays in the page (Web Audio, so its volume works on iPhone too) over the YouTube player, whose
 * own volume stays the listener's: we never touch it. */
export const SDK={url:'https://cdn.jsdelivr.net/npm/livekit-client@2.22.3/dist/livekit-client.umd.js',
  sri:'sha384-G/xxtkVytOx/ia9Q8MXxM+V0ohsaY1fZAgVP3iSGTPz4wJ0s3+ulJNKXh/gnzEDZ'};
let sdk=null;

/** window.LivekitClient, once (a failed load may be retried). */
export function loadSDK(){
  if(window.LivekitClient?.Room)return Promise.resolve(window.LivekitClient);
  if(!sdk)sdk=new Promise((ok,bad)=>{
    const s=document.createElement('script');s.src=SDK.url;s.integrity=SDK.sri;s.crossOrigin='anonymous';s.referrerPolicy='no-referrer';s.async=true;
    s.onload=()=>window.LivekitClient?.Room?ok(window.LivekitClient):bad(new Error('sdk'));
    s.onerror=()=>{sdk=null;s.remove();bad(new Error('sdk'));};
    document.head.append(s);
  });
  return sdk;
}

export const canSing=()=>!!(navigator.mediaDevices?.getUserMedia&&window.RTCPeerConnection);

/** The singer: the permission prompt, then the SFU, then the microphone track. Resolves to {stop, room, track, stats}. */
export async function publish({url,token,onEnd}){
  const LK=await loadSDK();
  const track=await LK.createLocalAudioTrack({echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1});
  const room=new LK.Room({adaptiveStream:false,dynacast:false,disconnectOnPageLeave:true,stopLocalTrackOnUnpublish:true});
  let done=false;
  const stop=()=>{if(done)return;done=true;try{track.stop();}catch{/* gone */}room.disconnect().catch(()=>{});};
  room.on(LK.RoomEvent.Disconnected,()=>{const was=done;stop();if(!was)onEnd?.('sfu');});
  try{
    await room.connect(url,token,{autoSubscribe:false});
    await room.localParticipant.publishTrack(track,{source:LK.Track.Source.Microphone,audioPreset:LK.AudioPresets.music,dtx:false,red:false});
  }catch(e){stop();throw e;}
  return {stop,room,track,stats:()=>rtp(track,'outbound-rtp')};
}

/** A listener: the singer's voice, at `volume` (0..1). `onTap(true)` when the phone needs a tap to play sound. */
export async function listen({url,token,volume=1,onTap,onEnd}){
  const LK=await loadSDK();
  const room=new LK.Room({adaptiveStream:false,dynacast:false,webAudioMix:true,disconnectOnPageLeave:true});
  let done=false,vol=volume,muted=false,voice=null;
  const apply=()=>{for(const p of room.remoteParticipants.values())try{p.setVolume(muted?0:vol);}catch{/* not yet */}};
  const stop=()=>{if(done)return;done=true;try{voice?.detach().forEach(el=>el.remove());}catch{/* gone */}voice=null;room.disconnect().catch(()=>{});};
  room.on(LK.RoomEvent.TrackSubscribed,(track)=>{if(track.kind!=='audio')return;voice=track;const el=track.attach();el.hidden=true;el.dataset.krVoice='1';document.body.append(el);apply();});
  room.on(LK.RoomEvent.TrackUnsubscribed,(track)=>{try{track.detach().forEach(el=>el.remove());}catch{/* gone */}if(voice===track)voice=null;});
  room.on(LK.RoomEvent.AudioPlaybackStatusChanged,()=>onTap?.(!room.canPlaybackAudio));
  room.on(LK.RoomEvent.Disconnected,()=>{const was=done;stop();if(!was)onEnd?.('sfu');});
  try{await room.connect(url,token,{autoSubscribe:true});}catch(e){stop();throw e;}
  onTap?.(!room.canPlaybackAudio);
  return {stop,room,
    setVolume(v){vol=Math.max(0,Math.min(1,Number(v)||0));apply();},
    mute(on){muted=!!on;apply();},
    tap(){return room.startAudio();},   // inside a click: iPhone plays sound after it
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
/** For the checks: the RTP counters of the track (packets and bytes), from getStats. */
async function rtp(track,type){
  try{
    const rep=await track.getRTCStatsReport?.();if(!rep)return null;
    for(const s of rep.values())if(s.type===type&&(s.kind==='audio'||s.mediaType==='audio'))return {packets:s.packetsReceived??s.packetsSent??0,bytes:s.bytesReceived??s.bytesSent??0};
  }catch{/* closed */}
  return null;
}
