import test from 'node:test';
import assert from 'node:assert/strict';
import {venueForSpend,waitForPanels} from '../public/js/v4/venue-routing.js';

test('street and spend menu resolve the same physical venues',()=>{
  assert.equal(venueForSpend('quan'),'cafe');
  assert.equal(venueForSpend('spa'),'spa');
  assert.equal(venueForSpend('rap'),'cinema');
  assert.equal(venueForSpend('chua'),'temple');
  assert.equal(venueForSpend('style'),null);
});
test('child panels finish only after all nested dialogs close',async()=>{
  let notify,disconnected=false;
  const parent={open:true},child={open:false},confirmation={open:false};
  const doc={querySelectorAll:()=>[parent,child,confirmation].filter(x=>x.open),body:{}};
  class Observer{constructor(fn){notify=fn;}observe(){}disconnect(){disconnected=true;}}
  let ended=false;
  const pending=waitForPanels(async()=>{child.open=true;}, {document:doc,MutationObserver:Observer}).then(()=>{ended=true;});
  await Promise.resolve(); await Promise.resolve();
  assert.equal(ended,false);
  confirmation.open=true;child.open=false;notify();await Promise.resolve();assert.equal(ended,false);
  confirmation.open=false;notify();await pending;assert.equal(disconnected,true);
});
test('a cancelled opener leaves no pending lifecycle',async()=>{
  const doc={querySelectorAll:()=>[],body:{}};
  await waitForPanels(async()=>{}, {document:doc});
  await assert.rejects(waitForPanels(async()=>{throw Error('failed');},{document:doc}),/failed/);
});
