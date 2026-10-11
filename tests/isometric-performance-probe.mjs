import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import vm from 'node:vm';
import {build} from 'esbuild';

const compiled=await build({entryPoints:['client/isometric/performance-probe.ts'],bundle:true,write:false,platform:'node',format:'cjs',logLevel:'silent'});
let now=0,publish,cleared=false;
const context=vm.createContext({module:{exports:{}},performance:{now:()=>now},setInterval(fn){publish=fn;return 1;},clearInterval(id){assert.equal(id,1);cleared=true;}});
vm.runInContext(compiled.outputFiles[0].text,context);
const engine={events:new EventEmitter(),renderer:{drawCount:20}},canvas={dataset:{}};
const stop=context.module.exports.installPerformanceProbe(engine,canvas,()=>({scene:'street'}));
function frame(start){now=start;engine.events.emit('prestep');now+=1;engine.events.emit('prerender');now+=2;engine.events.emit('postrender');}
for(let i=0;i<240;i++)frame(i*40);
publish();let data=JSON.parse(canvas.dataset.isoProfile);
assert.equal(data.totalMs.p95,3,'fast JavaScript alone cannot establish smooth frame cadence');
assert.equal(data.frameIntervalMs?.p95,40,'record frame start intervals, including time outside synchronous render');
assert.equal(data.slowFrameIntervals,239,'40 ms cadence exceeds the 30 fps interval');
assert.equal(data.scene,'street');
for(let i=0;i<300;i++)frame(9600+i*16);
publish();data=JSON.parse(canvas.dataset.isoProfile);
assert.equal(data.samples,240,'rolling diagnostic memory stays bounded');
assert.equal(data.frameIntervalMs.p95,16,'old slow samples expire instead of contaminating the next check');
assert.equal(data.slowFrameIntervals,0);
stop();assert.equal(cleared,true);assert.equal(canvas.dataset.isoProfile,undefined);
assert.equal(engine.events.eventNames().length,0);
console.log('performance probe: distinguishes JS cost from frame cadence; bounded samples and disposal passed');
