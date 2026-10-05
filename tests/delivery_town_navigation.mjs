import assert from 'node:assert/strict';
import * as town from '../public/js/v4/town-walk.js';
assert.equal(typeof town.destinations,'function');
const items=[{key:'shop'},{key:'closed'},{key:'hidden'},{key:'lm:bank'}];
const states={shop:{name:'Tiệm hoa',emoji:'🌼'},closed:{name:'Khóa',lock:true},hidden:{name:'Ẩn',off:true},'lm:bank':{name:'Ngân hàng',emoji:'🏦'}};
assert.deepEqual(town.destinations(items,it=>states[it.key]),[
 {key:'shop',label:'🌼 Tiệm hoa'},{key:'lm:bank',label:'🏦 Ngân hàng'}]);
assert.equal(typeof town.remainingPath,'function');
assert.deepEqual(town.remainingPath({x:10,y:0,path:[[20,0],[20,20]]},[{preview:[[20,20],[30,20]]}]),[[10,0],[20,0],[20,20],[30,20]]);
assert.deepEqual(town.remainingPath({x:30,y:20,path:null},[]),[],'arrival clears the route overlay');
console.log('town available destinations and remaining street route passed');
