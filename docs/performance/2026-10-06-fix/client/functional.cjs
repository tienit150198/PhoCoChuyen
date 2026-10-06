async page => {
  await page.bringToFront();
  await page.setViewportSize({width:1280,height:720});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.getByRole('button',{name:'Đưa góc nhìn về nhân vật',exact:true}).click();
  const zoom=await page.evaluate(()=>window.__isoWorld.debug().camera.zoom);
  await page.getByRole('button',{name:'Phóng to cảnh',exact:true}).click();
  const zoomed=await page.evaluate(()=>window.__isoWorld.debug().camera.zoom);
  if(zoomed<=zoom)throw new Error('Zoom in did not increase zoom');
  await page.getByRole('button',{name:'Thu nhỏ cảnh',exact:true}).click();
  await page.getByRole('button',{name:'Xem toàn đảo',exact:true}).click();
  const overview=await page.evaluate(()=>({overview:window.__isoWorld.stage.islandOverview,zoom:window.__isoWorld.debug().camera.zoom}));
  if(!overview.overview||overview.zoom>=zoom)throw new Error('Island overview did not fit map');
  await page.getByRole('button',{name:'Đưa góc nhìn về nhân vật',exact:true}).click();
  await page.locator('#world').focus();
  const before=await page.evaluate(()=>({x:window.__isoWorld.player.x,y:window.__isoWorld.player.y}));
  await page.keyboard.down('ArrowRight');await page.waitForTimeout(200);await page.keyboard.up('ArrowRight');
  await page.waitForTimeout(450);
  const after=await page.evaluate(()=>({x:window.__isoWorld.player.x,y:window.__isoWorld.player.y}));
  if(Math.hypot(after.x-before.x,after.y-before.y)<.05)throw new Error('Keyboard did not move player');
  const idle=await page.evaluate(()=>window.__isoWorld.debug());
  if(!idle.loopSleeping)throw new Error('Renderer did not sleep after keyboard release');
  await page.screenshot({path:'output/client-perf-20261006/desktop.png',scale:'css'});
  await page.getByRole('button',{name:'Cài đặt',exact:true}).click();
  const modal=await page.evaluate(()=>({dialogs:[...document.querySelectorAll('dialog[open]')].map(d=>({label:d.getAttribute('aria-label'),text:d.textContent.slice(0,100)})),world:window.__isoWorld.debug()}));
  if(modal.world.movementInput.x||modal.world.movementInput.y)throw new Error('Modal retained movement input');
  await page.keyboard.press('Escape');
  const sizes=[];
  for(const [width,height]of [[390,844],[1280,720]]){
    await page.setViewportSize({width,height});
    await page.waitForFunction(()=>window.__isoWorld.canvas.width===innerWidth&&window.__isoWorld.canvas.height===innerHeight);
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const size=await page.evaluate(()=>{const w=window.__isoWorld;return {width:innerWidth,height:innerHeight,canvas:[w.canvas.width,w.canvas.height],scroll:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],world:w.debug()};});
    sizes.push(size);await page.screenshot({path:`output/client-perf-20261006/${width===390?'mobile':'desktop-final'}.png`,scale:'css'});
  }
  if(errors.length)throw new Error('Browser errors: '+errors.join(';'));
  return {keyboard:{before,after,idle:idle.loopSleeping},camera:{zoom,zoomed,overview},modal,sizes,errors};
}
