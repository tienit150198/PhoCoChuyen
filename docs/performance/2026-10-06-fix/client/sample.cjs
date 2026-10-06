// playwright-cli -s=frame-diagnosis run-code --filename output/client-perf-20261006/sample.cjs
// Set window.__sampleOptions = {label:'before',rate:1}, save returned JSON.
async page => {
  await page.waitForFunction(()=>window.__isoWorld?.stage?.terrainChunks?.size>0);
  await page.bringToFront();
  const options=await page.evaluate(()=>window.__sampleOptions||{label:'before',rate:1});
  await page.setViewportSize({width:options.width||1280,height:options.height||720});
  await page.waitForFunction(()=>window.__isoWorld.canvas.width===innerWidth&&window.__isoWorld.canvas.height===innerHeight);
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate',{rate:options.rate});
  await cdp.send('Performance.enable');
  const results=[];
  for(const peerCount of options.peerCounts||[0,29]){
    await page.evaluate(({n,follow,zoom})=>{
      const w=window.__isoWorld;
      w.setMovementInput(0,0);w.setRemotePlayers([]);w.player.path=[];
      Object.assign(w.player,{x:6.2,y:6.2});w.recenter();
      if(zoom)w.setZoom(zoom);
      clearInterval(window.__peerDiagnosticTimer);
      if(n){
        const start=performance.now();
        const move=()=>w.setRemotePlayers(Array.from({length:n},(_,i)=>({pid:'diagnostic-'+i,name:'Khách '+(i+1),gender:i%2?'female':'male',look:{},x:(follow?w.player.x-1.7:6.5)+i*.12+Math.sin((performance.now()-start)/1300)*.6,y:6.2,direction:'se'})));
        move();window.__peerDiagnosticTimer=setInterval(move,270);
      }
    },{n:peerCount,follow:options.followPeers,zoom:options.zoom});
    // Warm the character poses and scene assets before recording steady-state work.
    await page.waitForTimeout(1200);
    if(options.zoom){
      await page.evaluate(zoom=>window.__isoWorld.setZoom(zoom),options.zoom);
      const actualZoom=await page.evaluate(()=>window.__isoWorld.debug().camera.zoom);
      if(Math.abs(actualZoom-options.zoom)>.001)throw new Error(`Requested zoom ${options.zoom}, got ${actualZoom}`);
    }
    const before=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(x=>[x.name,x.value]));
    const sample=await page.evaluate(async({peerCount,rate})=>{
      const w=window.__isoWorld,s=w.stage,costs={},originals=[];
      const summarize=values=>{const sorted=[...values].sort((a,b)=>a-b);return {n:values.length,totalMs:values.reduce((a,b)=>a+b,0),p50Ms:sorted[Math.floor(sorted.length*.5)]||0,p95Ms:sorted[Math.floor(sorted.length*.95)]||0,maxMs:sorted.at(-1)||0};};
      const wrap=(object,key,label)=>{const fn=object[key];if(typeof fn!=='function')return;const values=costs[label]=[];object[key]=function(...args){const begin=performance.now();try{return fn.apply(this,args);}finally{values.push(performance.now()-begin);}};originals.push(()=>object[key]=fn);};
      wrap(w,'step','worldStep');wrap(s,'cacheGround','groundCache');wrap(s,'syncRemotePlayers','syncPeers');wrap(s,'stepRemotePlayers','stepPeers');wrap(w.engine.renderer,'render','canvasRender');
      const longTasks=[];const observer=new PerformanceObserver(list=>longTasks.push(...list.getEntries().map(e=>({start:e.startTime,duration:e.duration}))));observer.observe({type:'longtask'});
      const frames=[],positions=[],visiblePeers=[],begin=performance.now();let last=null;
      const actor=s.actor;
      try{
        w.setMovementInput(.894,.447);
        await new Promise(resolve=>{const tick=t=>{if(last!==null)frames.push(t-last);last=t;positions.push({t,x:w.player.x,y:w.player.y});const view=s.cameras.main.worldView;visiblePeers.push([...s.remoteActors.values()].filter(a=>view.contains(a.image.x,a.image.y-55)).length);if(t-begin<6000)requestAnimationFrame(tick);else resolve();};requestAnimationFrame(tick);});
      }finally{w.setMovementInput(0,0);for(const restore of originals.reverse())restore();observer.disconnect();clearInterval(window.__peerDiagnosticTimer);}
      return {peerCount,visiblePeers:{min:Math.min(...visiblePeers),max:Math.max(...visiblePeers)},rate,viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,userAgent:navigator.userAgent,frames:summarize(frames),over25ms:frames.filter(x=>x>25).length,over50ms:frames.filter(x=>x>50).length,costs:Object.fromEntries(Object.entries(costs).map(([k,v])=>[k,summarize(v)])),longTasks,actorReused:s.actor===actor,start:positions[0],end:positions.at(-1),textureFrames:s.characterFrames.size,sceneChildren:s.children.length,rawFrames:frames,debug:w.debug()};
    },{peerCount,rate:options.rate});
    const after=Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(x=>[x.name,x.value]));
    sample.metrics=Object.fromEntries(['TaskDuration','ScriptDuration','LayoutDuration','RecalcStyleDuration','LayoutCount','RecalcStyleCount','JSHeapUsedSize'].map(k=>[k,k==='JSHeapUsedSize'?after[k]:after[k]-before[k]]));
    results.push(sample);
  }
  await cdp.send('Emulation.setCPUThrottlingRate',{rate:1});
  await page.evaluate(()=>{const w=window.__isoWorld;w.setRemotePlayers([]);w.setMovementInput(0,0);});
  await page.waitForTimeout(500);
  const idle=await page.evaluate(()=>window.__isoWorld.debug());
  await cdp.detach();
  return {options,browser:page.context().browser().version(),results,idle};
}
