/** Opt-in synchronous JS diagnostics, not FPS or GPU/compositor timing.
 * updateMs includes Phaser's pre-render clear; draws counts display-list entries.
 * No timer, samples or DOM writes in ordinary play. */
export function installPerformanceProbe(engine:any,canvas:HTMLCanvasElement,read:()=>Record<string,unknown>){
  const samples:Array<{update:number;render:number;total:number;draws:number}>=[];
  let started=0,renderAt=0,updateMs=0,frames=0;
  const pre=()=>{started=performance.now();};
  const render=()=>{renderAt=performance.now();updateMs=renderAt-started;};
  const post=()=>{const end=performance.now();samples.push({update:updateMs,render:end-renderAt,total:end-started,draws:engine.renderer?.drawCount||0});if(samples.length>240)samples.shift();frames++;};
  const publish=()=>{
    const stat=(key:'update'|'render'|'total'|'draws')=>{const a=samples.map(s=>s[key]).sort((a,b)=>a-b);return {p50:+(a[Math.floor(a.length*.5)]||0).toFixed(2),p95:+(a[Math.floor(a.length*.95)]||0).toFixed(2),max:+(a[a.length-1]||0).toFixed(2)};};
    canvas.dataset.isoProfile=JSON.stringify({...read(),frames,samples:samples.length,updateMs:stat('update'),renderMs:stat('render'),totalMs:stat('total'),draws:stat('draws')});
  };
  engine.events.on('prestep',pre);engine.events.on('prerender',render);engine.events.on('postrender',post);
  const timer=setInterval(publish,1000);
  return ()=>{clearInterval(timer);engine.events.off('prestep',pre);engine.events.off('prerender',render);engine.events.off('postrender',post);delete canvas.dataset.isoProfile;};
}
