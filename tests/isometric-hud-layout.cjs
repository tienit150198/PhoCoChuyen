// Run with playwright-cli run-code --filename tests/isometric-hud-layout.cjs
// against an authenticated town or workplace page. Includes the independently mounted presence label.
async page => {
  const output=[];
  await page.locator('#isoHUD').waitFor({state:'visible'});
  await page.evaluate(()=>document.fonts.ready);
  for(const [width,height] of [[320,568],[390,844],[667,375],[844,390],[820,1180],[1180,820],[1440,900]]){
    await page.setViewportSize({width,height});
    const measure=()=>{
      const items=Array.from(document.querySelectorAll('.iso-profile,.iso-pockets,.iso-settings,.iso-quick,.iso-mission,.iso-camera,.iso-camera-options,.iso-chat,.iso-scene,.iso-nav,.iso-movement,#townPresenceStatus,#dock,#taskHUD'))
        .map(e=>({e,name:e.id||e.className,r:e.getBoundingClientRect(),display:getComputedStyle(e).display,visibility:getComputedStyle(e).visibility}))
        .filter(x=>x.r.width&&x.r.height&&x.display!=='none'&&x.visibility!=='hidden');
      const overlap=[];
      for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){
        const a=items[i],b=items[j];
        if(a.e.contains(b.e)||b.e.contains(a.e))continue;
        if(Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left)>1&&Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top)>1)overlap.push([a.name,b.name]);
      }
      const outside=items.filter(x=>x.r.left<0||x.r.top<0||x.r.right>innerWidth+1||x.r.bottom>innerHeight+1).map(x=>x.name);
      const chat=document.querySelector('.iso-chat'),r=chat.getBoundingClientRect();
      const pixelFonts=Array.from(document.querySelectorAll('#isoHUD button,#townPresenceStatus')).filter(e=>/Pixel|VT323/i.test(getComputedStyle(e).fontFamily)).map(e=>e.className);
      const clippedLabels=Array.from(document.querySelectorAll('.iso-chat-copy b,.iso-chat-copy small,.iso-tab > span')).filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent);
      const smallCamera=Array.from(document.querySelectorAll('.iso-camera button')).filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.width<44||r.height<44;}).map(e=>e.getAttribute('aria-label'));
      return {mode:document.documentElement.dataset.sceneMode,width:innerWidth,height:innerHeight,coarse:matchMedia('(pointer:coarse)').matches,stick:items.some(x=>x.name==='isoMovement'),chatHit:chat.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)),presence:items.some(x=>x.name==='townPresenceStatus'),overlap,outside,pixelFonts,clippedLabels,smallCamera};
    };
    const result=await page.evaluate(measure);
    output.push(result);
    await page.screenshot({path:`output/playwright/soft-hud-${result.mode}-${width}x${height}.png`,scale:'css'});
    const camera=page.locator('[data-action="isoCamera"]');
    if(await camera.isVisible()){
      await camera.click();
      if(await camera.getAttribute('aria-expanded')!=='true')throw new Error('Camera disclosure did not open');
      output.push({...await page.evaluate(measure),cameraOpen:true});
      if(width===320){
        // Keyboard activation emits no outside pointerdown; a modal still owns Escape.
        await camera.press('Tab');
        for(let step=0;step<4;step++)await page.keyboard.press('Tab');
        if(await page.evaluate(()=>document.activeElement?.dataset.action)!=='isoChat')throw new Error('Camera tab order did not reach chat');
        await page.keyboard.press('Enter');
        await page.locator('#townChat').waitFor({state:'visible'});
        if(await camera.getAttribute('aria-expanded')!=='false')throw new Error('Modal opening did not reset camera');
        await page.keyboard.press('Escape');
        await page.locator('#townChat').waitFor({state:'hidden'});
        if(await page.locator('#pauseOverlay').isVisible())throw new Error('Dismissing chat also paused the game');
        result.cameraModalKeyboard=true;
      }else{
        await camera.press('Escape');
        if(await camera.getAttribute('aria-expanded')!=='false')throw new Error('Escape did not close camera');
      }
    }
    // Utilities are a native keyboard disclosure. Its scroll panel must leave walking/chat usable.
    const tools=page.locator('.iso-tools'),toolsSummary=tools.locator('summary').first();
    await toolsSummary.press('Enter');
    if(!await tools.evaluate(e=>e.open))throw new Error('Utilities did not open with Enter');
    const panel=page.locator('.iso-tools-options');
    const utilityBounds=await panel.evaluate(e=>{
      const r=e.getBoundingClientRect(),protectedRects=Array.from(document.querySelectorAll('.iso-movement,.iso-chat,.iso-guide-button')).filter(n=>n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden').map(n=>({name:n.className,r:n.getBoundingClientRect()}));
      return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,covered:protectedRects.filter(x=>Math.min(r.right,x.r.right)>Math.max(r.left,x.r.left)&&Math.min(r.bottom,x.r.bottom)>Math.max(r.top,x.r.top)).map(x=>x.name)};
    });
    if(utilityBounds.left<0||utilityBounds.right>width||utilityBounds.top<0||utilityBounds.bottom>height||utilityBounds.covered.length)throw new Error('Utilities overlap protected controls: '+JSON.stringify(utilityBounds));
    for(const button of await page.locator('.iso-tools-options > button').all()){
      await button.scrollIntoViewIfNeeded();
      if(!await button.evaluate(b=>{const r=b.getBoundingClientRect();return b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}))throw new Error('Utilities action is covered: '+await button.textContent());
    }
    result.utilities=utilityBounds;
    // Exercise the nested disclosure at every town viewport, including narrow landscape.
    if(result.mode==='town'){
      await page.locator('.iso-outings > summary').click();
      const dropdown=await panel.evaluate(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,viewport:[innerWidth,innerHeight]};});
      if(dropdown.left<0||dropdown.right>width||dropdown.top<0||dropdown.bottom>height)throw new Error('Outings menu is clipped: '+JSON.stringify(dropdown));
      dropdown.actions=[];
      for(const button of await page.locator('.iso-outings-menu button').all()){
        await button.scrollIntoViewIfNeeded();
        const action=await button.evaluate(b=>{const r=b.getBoundingClientRect();return {label:b.textContent,hit:b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))};});
        if(!action.hit)throw new Error('Outings action is covered: '+JSON.stringify(action));
        dropdown.actions.push(action);
      }
      result.outings=dropdown;
      await page.locator('.iso-outings > summary').press('Escape');
      if(!await tools.evaluate(e=>e.open))throw new Error('Nested Escape incorrectly closed the utilities parent');
    }
    await toolsSummary.press('Escape');
    if(await tools.evaluate(e=>e.open))throw new Error('Escape did not close utilities');
    if(await page.locator('#pauseOverlay').isVisible())throw new Error('Dismissing utilities also paused the game');
    if(result.mode==='town'){
      const mission=page.locator('.iso-mission');
      await mission.locator('summary').press('Enter');
      if(!await mission.evaluate(e=>e.open))throw new Error('Task details did not open with Enter');
      await mission.locator('summary').press('Escape');
      if(await mission.evaluate(e=>e.open))throw new Error('Escape did not close task details');
    }
  }
  const failures=output.filter(r=>r.overlap.length||r.outside.length||r.pixelFonts.length||r.clippedLabels.length||r.smallCamera.length||!r.chatHit||r.presence!==(r.mode==='town'));
  if(failures.length)throw new Error(JSON.stringify(failures,null,2));
  return output;
}
