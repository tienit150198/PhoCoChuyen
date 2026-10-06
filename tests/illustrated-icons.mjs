import './phaser25d-wired.mjs';  // skipped while the 2.5D client is not wired (docs/PHASER_25D.md)
import test from 'node:test';
import assert from 'node:assert/strict';
import {readdirSync,readFileSync} from 'node:fs';
// Dynamic, after the guard: 1.8.0's icons.js has no careerIconNames, and a static import would fail to link.
const {icon,itemArt,portrait,hasIcon,careerIconNames}=await import('../public/js/icons.js');
const {uiIcon}=await import('../public/js/isometric/ui-icons.js');

const art = svg => svg.slice(svg.indexOf('>')+1,svg.lastIndexOf('</svg>'));
// Icon fields observed in the real GET /api/content, including products and upgrades.
const contentNames = 'home sun plant camera lock lamp gift cross book headphones bowl cake tractor cart paw flower scissors wrench bed compass coffee bike calculator building bag fish basket truck sparkles bell bear send people calendar settings bunny shirt cloth blocks card rattle teether bottle bib socks blanket envelope box rug chair shelf check board image tool'.split(' ');
const legacyNames = 'briefcase map alert music globe palette layout user inbox menu leaf coin star cloud clock chevron arrow back plus minus x chat chats search sparkle eye clipboard folder link question trash play pause volume mute grid flag award mail expand download upload shield heart cat note refresh exit move'.split(' ');
const hudNames = 'map briefcase bag store user people menu settings clipboard note clock leaf chats fish boat pool compass overview plus minus arrow x'.split(' ');
function sourceIcons(dir){
  const names=new Set();
  for(const file of readdirSync(dir,{withFileTypes:true})){
    const path=`${dir}/${file.name}`;
    if(file.isDirectory())for(const name of sourceIcons(path))names.add(name);
    else if(path.endsWith('.js'))for(const match of readFileSync(path,'utf8').matchAll(/(?:uiIcon|icon)\(\s*['"]([^'"]+)['"]/g))names.add(match[1]);
  }
  return names;
}
test('catalogue, product, upgrade, legacy and literal consumer names have actual artwork',()=>{
  const fallback=art(icon('__unknown__'));
  for(const name of new Set([...contentNames,...legacyNames,...hudNames,...sourceIcons('public/js')])){
    assert.notEqual(art(icon(name)),fallback,`${name} must not silently use the unknown icon`);
    assert.match(icon(name),/^<svg[^>]+aria-hidden="true"/);
  }
});
test('HUD and product surfaces render the same illustrated vocabulary',()=>{
  for(const name of hudNames)assert.equal(art(uiIcon(name,24)),art(icon(name,24)),name);
});
test('specialty artwork expresses the career rather than the old misleading symbol',()=>{
  for(const [career,old] of Object.entries({milk_tea:'coffee',ice_cream:'cake',com:'cake',pho:'cake',pilot:'send',nail:'sparkles',giupviec:'sparkles',pagoda:'bell'})){
    assert.ok(hasIcon(careerIconNames[career]),career);
    assert.notEqual(art(icon(careerIconNames[career])),art(icon(old)),career);
  }
  assert.ok(Object.values(careerIconNames).every(hasIcon));
  assert.equal(hasIcon('__proto__'),false,'prototype properties cannot masquerade as icon markup');
});
test('primary illustrations carry distinct silhouettes and layered material colors',()=>{
  const names='home store truck bowl flower bike bed paw calculator building cart cake tractor user people map bear fish basket'.split(' ');
  assert.equal(new Set(names.map(name=>art(icon(name)))).size,names.length);
  for(const name of names){
    assert.ok(new Set([...icon(name).matchAll(/fill="([^\"]+)"/g)].map(m=>m[1])).size>=3,`${name} has material color and depth`);
    assert.doesNotMatch(icon(name),/<image|data:image|<filter/,'small icons are native vector shapes');
  }
});
test('tiny functional controls retain simple currentColor marks without a background tile',()=>{
  for(const name of ['x','plus','minus','arrow','back','chevron','expand','move','check']){
    const svg=icon(name,12);
    assert.match(svg,/stroke="currentColor"/);
    assert.doesNotMatch(art(svg),/<rect|<circle|<ellipse/);
  }
});
test('SVG entry points keep safe dimensions, classes and legacy art exports',()=>{
  assert.match(icon('home',32,'nav-mark'),/width="32" height="32"/);
  assert.match(icon('home',32,'nav-mark'),/class="icon illustrated-ui-icon nav-mark"/);
  assert.doesNotMatch(icon('home','20" onload="alert(1)','" onload="alert(1)'),/ onload="/);
  assert.match(uiIcon('map',NaN),/width="20"/);
  assert.match(uiIcon('map',999),/width="64"/);
  assert.match(itemArt('bear'),/class="item-art"/);
  assert.match(portrait('florist_npc_01'),/class="portrait"/);
});
const liveURL=process.argv.find(arg=>arg.startsWith('--live='))?.slice(7);
test('all icon fields from the live server resolve, including all playable careers',{skip:!liveURL},async()=>{
  const response=await fetch(liveURL,{signal:AbortSignal.timeout(10000)});
  assert.ok(response.ok,`GET ${liveURL}: ${response.status}`);
  const content=await response.json();
  assert.ok(content.catalogue.length>=44);
  assert.ok(content.catalogue.filter(c=>c.playable).length>=41);
  const walk=(value,path='content')=>{
    if(!value||typeof value!=='object')return;
    if(typeof value.icon==='string')assert.notEqual(art(icon(value.icon)),art(icon('__unknown__')),`${path}.icon: ${value.icon}`);
    for(const [key,item] of Object.entries(value))walk(item,`${path}.${key}`);
  };
  walk(content);
});
