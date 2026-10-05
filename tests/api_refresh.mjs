import assert from 'node:assert/strict';
import {GameAPI} from '../public/js/api.js';
const api=new GameAPI();let calls=0,resolve,accepts=0;
api.json=()=>{calls++;return new Promise(r=>resolve=r);};api.accept=()=>accepts++;
const a=api.refresh(),b=api.refresh();assert.equal(calls,1);
resolve({revision:1});assert.deepEqual(await a,await b);assert.equal(accepts,1);
api.json=async()=>{calls++;throw new Error('offline');};await assert.rejects(api.refresh(),/offline/);
api.json=async()=>{calls++;return {revision:2};};assert.equal((await api.refresh()).revision,2);assert.equal(calls,3);
console.log('Simultaneous refreshes share one request; errors release the next refresh.');
