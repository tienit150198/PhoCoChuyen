// Unit test of the bottom button of a work screen (public/js/v4/guide.js stepCta): a step it can do is a filled
// button that sends it; a step it can only point at (go.sel) is an outlined "👆 …" pointer that never sends
// anything. Run by tests/test_guides.py (node tests/guide_cta.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {stepCta,bareLabel,pointsOnly,nextHint,barParts} from '../public/js/v4/guide.js';
import {actBar,whyAttrs,withWhy} from '../public/js/ui-kit.js';

const x={room:{metrics:{served:1}}};
const none={label:'',go:null,ready:false};

// The words without the leading emoji / 👉 and a trailing arrow.
assert.equal(bareLabel('🧋 Lấy ly M'),'Lấy ly M');
assert.equal(bareLabel('👉 Chọn cách xử lý →'),'Chọn cách xử lý');
assert.equal(bareLabel('<b>🍯 Đường</b> 50%'),'Đường 50%');
assert.equal(bareLabel('Ly M'),'Ly M');

assert.equal(pointsOnly({sel:'.a'}),true);
assert.equal(pointsOnly({sel:'.a',cmd:'x'}),false);
assert.equal(pointsOnly({act:'car:go'}),false);
assert.equal(pointsOnly(null),false);

// A command step (the first customer's guided button, D1): unchanged, filled, sends the command.
const cmd=stepCta(x,[{ok:null,label:'Lấy ly M',go:{act:'car:go',data:{op:'tea_cup'},label:'🧋 Lấy ly M'}}],none);
assert.match(cmd,/class="btn primary big grow gd-cta"/);
assert.match(cmd,/data-action="car:go"/);
assert.match(cmd,/>🧋 Lấy ly M</);
assert.doesNotMatch(cmd,/gd-point/);

// A pointer step: outlined (no "primary"), a hand, the step in words, read as "Chỉ chỗ: …"; it only scrolls (v4Go).
const pt=stepCta(x,[{ok:null,label:'Lấy ly M',go:{sel:'.mt-stations [data-k="cup_M"]',label:'🧋 Lấy ly M'}}],none);
assert.match(pt,/class="btn big grow gd-cta gd-point"/);
assert.doesNotMatch(pt,/primary/);
assert.match(pt,/data-action="v4Go"/);
assert.match(pt,/data-say="Lấy ly M"/);
assert.match(pt,/aria-label="Chỉ chỗ: Lấy ly M"/);
assert.match(pt,/>👆 Lấy ly M</);
assert.doesNotMatch(pt,/data-command|car:go/);

// No button label: the step's own label; markup in a label is never written raw.
const bare=stepCta(x,[{ok:null,label:'Chọn cách <xử lý>',go:{sel:'.sk-opts'}}],none,{style:'primary'});
assert.match(bare,/class="btn gd-cta gd-point"/);
assert.match(bare,/>👆 Chọn cách &lt;xử lý&gt;</);

// "hoặc …" (finish early) still sits under a pointer.
const alt=stepCta(x,[{ok:null,label:'Chọn cách xử lý',go:{sel:'.sk-opts'}}],{label:'Giao',go:{cmd:'serve',payload:{}},ready:true});
assert.match(alt,/class="gd-ctas"/);
assert.match(alt,/gd-point/);
assert.match(alt,/class="gd-alt" data-command="serve"/);

// The finishing button is never a pointer.
const fin=stepCta(x,[{ok:true,label:'Xong'}],{label:'🛎️ Giao món',go:{cmd:'serve',payload:{}},ready:true});
assert.match(fin,/gd-cta gd-final/);
assert.doesNotMatch(fin,/gd-point/);

// The header hint keeps its look (it is a line, not the main button).
const hint=nextHint(x,[{ok:null,label:'Lấy ly M',go:{sel:'.mt-stations [data-k="cup_M"]',label:'🧋 Lấy ly M'}}]);
assert.match(hint,/class="gd-hint" data-action="v4Go"/);
assert.doesNotMatch(hint,/gd-point/);

// UI foundation: a finishing button that cannot go yet is dimmed but tappable, with its reason (never `disabled`).
const wait=stepCta(x,[{ok:null,label:'Giặt khăn'}],{label:'🛵 Lên đường',go:{cmd:'go',payload:{}},ready:false});
assert.match(wait,/aria-disabled="true"/);
assert.match(wait,/data-why="Còn: Giặt khăn"/);
assert.doesNotMatch(wait,/\sdisabled[\s>]/);
// The server's pre-check wins over the page's guess, and carries a fix.
const srv=stepCta(x,[{ok:true,label:'Xong'}],{label:'💐 Trao hoa',go:{cmd:'fl_deliver',payload:{}},ready:true,can:{why:'Nhấc hoa khỏi xô trước.',fix:{cmd:'fl_lift',payload:{},label:'Nhấc'}}});
assert.match(srv,/data-why="Nhấc hoa khỏi xô trước."/);
assert.match(srv,/data-fix="[^"]*fl_lift/);
assert.doesNotMatch(stepCta(x,[{ok:true,label:'Xong'}],{label:'💐 Trao hoa',go:{cmd:'fl_deliver',payload:{}},ready:true,can:true}),/aria-disabled/);

// The shared bar's two slots: a command step is the main button; a pointer goes left with the finish on the right.
const fin2={label:'🚪 Mời khách kiểm',go:{cmd:'gv_check',payload:{}},ready:true};
let p=barParts(x,[{ok:null,label:'Giặt khăn',go:{cmd:'gv_wash',payload:{},label:'🧺 Giặt khăn'}}],fin2);
assert.match(p.main,/class="btn primary big gd-cta" data-command="gv_wash"/);
assert.match(p.next,/class="gd-alt"[^>]*data-command="gv_check"/);
p=barParts(x,[{ok:null,label:'Bàn',go:{sel:'.gv-spot',label:'🪑 Bàn'}}],fin2);
assert.match(p.next,/ui-next gd-cta gd-point/);
assert.match(p.main,/data-command="gv_check"/);
assert.doesNotMatch(p.main,/primary/);   // steps are left: the finish is there but not the main colour
p=barParts(x,[],{...fin2,ready:false,why:'chọn phòng'});
assert.match(p.main,/aria-disabled="true"/);
assert.match(p.next,/chọn phòng/);
p=barParts(x,[{ok:true,label:'Xong'}],fin2);
assert.equal(p.next,'');
assert.match(p.main,/class="btn primary big gd-cta gd-final"/);

// actBar: one row, the main button alone takes the whole width (no next slot), nothing at all is ''.
assert.equal(actBar({}),'');
assert.match(actBar({main:'<button class="btn primary">A</button>',cls:'sk-bar'}),/^<div class="ui-bar sk-bar"><div class="ui-bar-main">/);
assert.match(actBar({next:'n',main:'m',top:'t'}),/ui-bar-top">t<\/div><div class="ui-bar-next">n<\/div><div class="ui-bar-main">m/);
assert.equal(whyAttrs(true),'');
assert.match(whyAttrs({why:'Chọn chai trước',fix:{sel:'.gv-hand',label:'Chọn'}}),/aria-disabled="true" data-why="Chọn chai trước" data-fix=/);
assert.match(withWhy('<button type="button" class="btn x" disabled>A</button>',{why:'w'}),/class="btn x is-why"/);
assert.doesNotMatch(withWhy('<button type="button" class="btn x" disabled>A</button>',{why:'w'}),/disabled>/);

console.log('guide_cta ok');
