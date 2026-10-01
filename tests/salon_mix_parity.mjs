// The salon bowl preview (public/js/careers/salon_mix.js) against the server (game/careers/salon.py bowl_check).
// Run by tests/test_salon_mix_parity.py, which sends the grid on stdin and computes the same lines in Python:
//   {cc, grids:[{bowls, devs, ratios, hairs, wants}], views:[{view, kinds}], bowls, devs, ratios}
// Prints {grids:[[sha256 per bowl]], views:[[sha256 per view]]}; with argv[2] = "dump" and argv[3..] = where, the lines.
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {bowlCheck,previewInputs,recipeWant} from '../public/js/careers/salon_mix.js';

const spec=JSON.parse(readFileSync(0,'utf8'));
const cc=spec.cc;
/** One canonical line per case: the same fields, in the same order, as the Python side. */
const line=v=>JSON.stringify([v.issue,v.hit,v.mix&&[v.mix.den,v.mix.lv,v.mix.tn,v.mix.nat,v.mix.band,v.mix.color],v.text,
  v.level_ok,v.band_ok,v.nat_ok,v.dlv,v.dband,v.dev_note,v.need,v.cap,v.tones,v.block]);
const outcome=v=>JSON.stringify([v.issue,v.hit,v.mix&&[v.mix.den,v.mix.lv,v.mix.tn,v.mix.nat,v.mix.band,v.mix.color],v.text]);

function gridLines(g,bi){
  const [kind,shade,mx]=g.bowls[bi],out=[];
  for(const dev of g.devs)for(const ratio of g.ratios)for(const [warm,blind,lift] of g.hairs)for(const want of g.wants)
    out.push(line(bowlCheck(cc,kind,shade,mx,dev,ratio,want,warm,blind,lift)));
  return out;
}
function viewLines(entry){
  const out=[],t=entry.view;
  for(const kind of entry.kinds){
    if(kind==='color'){
      const p=previewInputs(t);
      for(const [,shade,mx] of spec.bowls)for(const dev of spec.devs)for(const ratio of spec.ratios)
        out.push(outcome(bowlCheck(cc,'color',shade,mx,dev,ratio,p.want,p.warm,p.photoBlind,p.lift)));
    }else{
      const want=recipeWant(t,kind),shades=kind==='toner'?cc.toners.map(d=>d.id):[null];
      for(const shade of shades)for(const dev of spec.devs)for(const ratio of spec.ratios)
        out.push(outcome(bowlCheck(cc,kind,shade,null,dev,ratio,want)));
    }
  }
  return out;
}
const sha=lines=>createHash('sha256').update(lines.join('\n'),'utf8').digest('hex');

if(process.argv[2]==='dump'){
  const [where,a,b]=process.argv.slice(3);
  const lines=where==='grid'?gridLines(spec.grids[Number(a)],Number(b)):viewLines(spec.views[Number(a)]);
  process.stdout.write(JSON.stringify(lines));
}else{
  process.stdout.write(JSON.stringify({grids:spec.grids.map(g=>g.bowls.map((_,i)=>sha(gridLines(g,i)))),
    views:spec.views.map(e=>sha(viewLines(e)))}));
}
