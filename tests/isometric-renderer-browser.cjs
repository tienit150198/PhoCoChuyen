// playwright-cli run-code --filename tests/isometric-renderer-browser.cjs
// Requires a local scratch account at ?isometricdebug=1. Does not change saved economy.
async page => {
  await page.waitForFunction(()=>window.__isoWorld?.stage?.terrainChunks?.size>0);
  await page.setViewportSize({width:1280,height:720});
  const performanceCheck=await page.evaluate(async()=>{
    const w=window.__isoWorld,s=w.stage,ground=s.cacheGround,costs=[];
    Object.assign(w.player,{x:6.2,y:6.2,path:[]});w.recenter();
    s.cacheGround=function(...args){const begin=performance.now();try{return ground.apply(this,args);}finally{const ms=performance.now()-begin;if(ms>1)costs.push(ms);}};
    const actor=s.actor,frames=[],begin=performance.now();let last=begin;
    try{
      w.setMovementInput(.894,.447);
      await new Promise(resolve=>{const tick=t=>{frames.push(t-last);last=t;if(t-begin<6000)requestAnimationFrame(tick);else resolve();};requestAnimationFrame(tick);});
    }finally{w.setMovementInput(0,0);s.cacheGround=ground;}
    if(s.actor!==actor)throw new Error('Walking recreated the actor');
    if(w.player.x<15)throw new Error('Performance route did not actually travel');
    frames.sort((a,b)=>a-b);
    return {viewport:[innerWidth,innerHeight],samples:frames.length,frameMeanMs:frames.reduce((a,b)=>a+b)/frames.length,p95Ms:frames[Math.floor(frames.length*.95)],maxMs:frames.at(-1),groundBakeMs:costs,actorReused:true,textureFrames:s.characterFrames.size};
  });
  const sizes=[];
  for(const [width,height] of [[390,844],[844,390],[820,1180],[1180,820],[1440,900],[390,844],[1440,900]]){
    await page.setViewportSize({width,height});
    await page.waitForFunction(()=>{const w=window.__isoWorld;return w.canvas.width===innerWidth&&w.canvas.height===innerHeight;});
    // Two paints after ResizeObserver ensure the assertion samples the new bitmap.
    await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
    const sample=await page.evaluate(()=>{
      const c=document.getElementById('world'),ctx=c.getContext('2d'),colors=new Set();
      for(let y=40;y<c.height;y+=41)for(let x=40;x<c.width;x+=41)colors.add(Array.from(ctx.getImageData(x,y,1,1).data).join(','));
      return {width:c.width,height:c.height,colors:colors.size};
    });
    if(sample.colors<10)throw new Error('Blank scene after resize: '+JSON.stringify(sample));sizes.push(sample);
  }
  // Exercise the actual keyboard binding, then release and observe idle sleep.
  await page.locator('#world').focus();
  const before=await page.evaluate(()=>({...window.__isoWorld.player}));
  await page.keyboard.down('ArrowLeft');await page.keyboard.down('ArrowUp');
  await page.waitForTimeout(180);
  await page.keyboard.up('ArrowLeft');await page.keyboard.up('ArrowUp');
  const after=await page.evaluate(()=>({x:window.__isoWorld.player.x,y:window.__isoWorld.player.y}));
  if(before.x===after.x&&before.y===after.y)throw new Error('Keyboard did not move');
  await page.waitForTimeout(450);
  const idle=await page.evaluate(()=>window.__isoWorld.debug());
  if(!idle.loopSleeping)throw new Error('Idle renderer did not sleep');
  await page.screenshot({path:'output/playwright/main25d-town-desktop.png',scale:'css'});
  return {performanceCheck,sizes,idle:idle.loopSleeping,keyboardMoved:true};
}
