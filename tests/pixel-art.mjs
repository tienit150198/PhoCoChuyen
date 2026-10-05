import assert from 'node:assert/strict';
import {pixelCharacterData,pixelAssetData,pixelSVG,shade} from '../public/js/pixel/art.js';
import {pixelIconData} from '../public/js/pixel/icons.js';
const look={hair:'toc_bui_doi',shade:'mau_hong',skin:'da_ngam',top:'ao_hoodie',bottom:'vay_xoe',shoes:'giay_do',acc:'non_la',uniform:false,tint:{ao_hoodie:'mint'}};
const views=['sw','se','nw','ne'].map(direction=>pixelCharacterData({look,gender:'female',direction}));
assert.equal(new Set(views.map(v=>JSON.stringify(v.pixels))).size,4,'all four views differ');
assert.notDeepEqual(pixelCharacterData({look,step:1}).pixels,pixelCharacterData({look,step:3}).pixels,'walk cycle changes feet');
assert.deepEqual(pixelCharacterData({look,walkFrame:2}).pixels,pixelCharacterData({look,step:3}).pixels);
assert.ok(views[0].pixels.some(p=>p.c==='#8fd5c0'),'saved clothing tint is used');
assert.ok(views[0].pixels.some(p=>p.c==='#c48d64'),'saved skin is used');
for(const data of views){assert.equal(data.width,48);assert.equal(data.height,64);for(const p of data.pixels)for(const k of ['x','y','w','h'])assert.ok(Number.isInteger(p[k]));}
const kinds=['grocery','cafe','home','tree','bench','counter','shelf','desk','crates','board','door','plant','window','lamp','cat','cup','bread','pond','boat','pool'];
for(const kind of kinds){const data=pixelAssetData(kind);assert.ok(data.pixels.length>5,kind);assert.ok(data.pixels.length<2000,'bounded primitives');assert.ok(!pixelSVG(data).includes('<path'),'native cells');}
for(const id of ['map','user','coin','pool','boat','fish','settings'])assert.ok(pixelIconData(id).pixels.length>10);
assert.equal(shade('#ffffff',15),'#ffffff');assert.equal(shade('#000000',-10),'#000000');
console.log('Native pixel assets, directions, walking frames, wardrobe and HUD checks passed');
