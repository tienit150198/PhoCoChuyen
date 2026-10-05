// Run with playwright-cli run-code --filename tests/isometric-hud-layout.cjs
// against an authenticated town or workplace page. Includes the independently mounted presence label.
async page => {
  const output=[];
  await page.locator('#isoHUD').waitFor({state:'visible'});
  await page.evaluate(()=>document.fonts.ready);
  for(const [width,height] of [[320,568],[390,844],[667,375],[844,390],[820,1180],[1180,820],[1440,900]]){
    await page.setViewportSize({width,height});
    const result=await page.evaluate(()=>{
      const items=Array.from(document.querySelectorAll('.iso-profile,.iso-pockets,.iso-settings,.iso-quick,.iso-mission,.iso-camera,.iso-chat,.iso-scene,.iso-nav,.iso-movement,#townPresenceStatus,#dock,#taskHUD'))
        .map(e=>({name:e.id||e.className,r:e.getBoundingClientRect(),display:getComputedStyle(e).display,visibility:getComputedStyle(e).visibility}))
        .filter(x=>x.r.width&&x.r.height&&x.display!=='none'&&x.visibility!=='hidden');
      const overlap=[];
      for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){
        const a=items[i],b=items[j];
        if(Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left)>1&&Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top)>1)overlap.push([a.name,b.name]);
      }
      const outside=items.filter(x=>x.r.left<0||x.r.top<0||x.r.right>innerWidth+1||x.r.bottom>innerHeight+1).map(x=>x.name);
      const chat=document.querySelector('.iso-chat'),r=chat.getBoundingClientRect();
      const pixelFonts=Array.from(document.querySelectorAll('#isoHUD button,#townPresenceStatus')).filter(e=>/Pixel|VT323/i.test(getComputedStyle(e).fontFamily)).map(e=>e.className);
      const clippedLabels=Array.from(document.querySelectorAll('.iso-chat-copy b,.iso-chat-copy small,.iso-tab > span')).filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent);
      return {mode:document.documentElement.dataset.sceneMode,width:innerWidth,height:innerHeight,coarse:matchMedia('(pointer:coarse)').matches,stick:items.some(x=>x.name==='isoMovement'),chatHit:chat.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)),presence:items.some(x=>x.name==='townPresenceStatus'),overlap,outside,pixelFonts,clippedLabels};
    });
    output.push(result);
    await page.screenshot({path:`output/playwright/soft-hud-${result.mode}-${width}x${height}.png`,scale:'css'});
    if(result.mode==='town'){
      await page.locator('.iso-outings > summary').click();
      const dropdown=await page.locator('.iso-outings-menu').evaluate(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,viewport:[innerWidth,innerHeight]};});
      if(dropdown.left<0||dropdown.right>width||dropdown.top<0||dropdown.bottom>height)throw new Error('Outings menu is clipped: '+JSON.stringify(dropdown));
      await page.locator('.iso-outings > summary').click();
    }
  }
  const failures=output.filter(r=>r.overlap.length||r.outside.length||r.pixelFonts.length||r.clippedLabels.length||!r.chatHit||r.presence!==(r.mode==='town'));
  if(failures.length)throw new Error(JSON.stringify(failures,null,2));
  return output;
}
