import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const equipment=readFileSync(new URL('../public/js/v4/work-equipment.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');
const app=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
const wiring=app.match(/^const stopStaffRefresh=staffRefresh\(.*\);$/m)?.[0];
assert.ok(wiring,'exercise the actual app staff-refresh wiring');
function fixture(){
 let tick,interval,calls=0,now=100000;
 const open=new Set(),ui={view:'job'},document={hidden:false,querySelector:selectors=>selectors.split(',').map(s=>s.trim()).find(s=>open.has(s))||null};
 const api={state:{careers:{other:{business_running:true}}},syncedAt:0,refresh:async()=>{calls++;}};
 const scroll={busy:false},sheetScroll={busy:()=>scroll.busy};
 const context=vm.createContext({api,ui,document,sheetScroll,Date:{now:()=>now},setInterval:(fn,ms)=>{tick=fn;interval=ms;return 1;},clearInterval:()=>{}});
 vm.runInContext(equipment+'\n'+wiring,context);
 return {ui,document,open,api,scroll,tick:()=>tick(),calls:()=>calls,interval:()=>interval};
}

test('app staff refresh pauses throughout the open fair and resumes after it closes',async()=>{
 const f=fixture();assert.equal(f.interval(),30000);
 await f.tick();assert.equal(f.calls(),1);
 f.open.add('dialog.fh-sheet[open]');await f.tick();await f.tick();assert.equal(f.calls(),1,'open fair suppresses background full-state refresh');
 f.open.delete('dialog.fh-sheet[open]');await f.tick();assert.equal(f.calls(),2,'the next due tick resumes after the fair closes');
});

test('app staff refresh preserves investment, counter, busy, visibility and fresh-state guards',async()=>{
 const f=fixture();
 f.ui.view='home';f.ui.jrView='invest';await f.tick();assert.equal(f.calls(),0);
 f.ui.view='job';f.open.add('dialog.qy-sheet[open]');await f.tick();assert.equal(f.calls(),0);f.open.clear();
 f.ui.busy=true;await f.tick();assert.equal(f.calls(),0);f.ui.busy=false;
 f.ui.ivBusy=true;await f.tick();assert.equal(f.calls(),0);f.ui.ivBusy=false;
 f.document.hidden=true;await f.tick();assert.equal(f.calls(),0);f.document.hidden=false;
 f.api.syncedAt=99000;await f.tick();assert.equal(f.calls(),0);f.api.syncedAt=0;
 f.scroll.busy=true;await f.tick();assert.equal(f.calls(),0,'a sheet fling also suppresses the background refresh');f.scroll.busy=false;
 await f.tick();assert.equal(f.calls(),1);
});
