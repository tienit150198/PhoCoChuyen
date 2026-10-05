"""Check the actual furniture drawings: changing facing must change what the player sees."""
import pathlib
import shutil
import subprocess
import unittest


class FacingArtwork(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'node is required for the SVG renderer check')
    def test_front_back_and_mirror_are_independent(self):
        module = pathlib.Path(__file__).resolve().parents[1] / 'public/js/v4/deco-art.js'
        script = r"""
          import assert from 'node:assert/strict';
          const {pieceAt,ART}=await import(process.argv[1]);
          for(const id of ['tv','sofa']){
            const it={id,w:2,h:1,spot:'floor'};
            const front=pieceAt(it,10,20,0),back=pieceAt(it,10,20,0,null,'back');
            assert.notEqual(front,back,`${id}: front/back must change the SVG`);
            assert.equal(back.includes(ART[id].d(80,30)),false,'rear view must not reuse the front drawing');
            assert.ok(pieceAt(it,10,20,1,null,'back').includes('scale(-1 1)'));
            assert.notEqual(pieceAt(it,10,20,1,null,'back'),pieceAt(it,10,20,1));
            assert.notEqual(pieceAt(it,10,20,0,'hong','back'),back,'rear view must take the furniture tint');
          }
          assert.ok(pieceAt({id:'tv',w:2,h:1,spot:'floor'},0,0,0).includes('#7ec8e3'));
          assert.equal(pieceAt({id:'tv',w:2,h:1,spot:'floor'},0,0,0,null,'back').includes('#7ec8e3'),false,'TV screen is only visible from the front');
          const nondirectional={id:'ban_tra',w:2,h:1,spot:'floor'};
          assert.equal(pieceAt(nondirectional,0,0,0,null,'back'),pieceAt(nondirectional,0,0,0));
        """
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script, module.as_uri()],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('node'), 'node is required for the home interaction check')
    def test_walk_uses_spouse_bed_fridge_and_own_clothes_in_spouse_closet(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        script = r"""
          import assert from 'node:assert/strict';
          const {setup}=await import(process.argv[1]);
          const A=await import(process.argv[2]);
          globalThis.requestAnimationFrame=f=>f();
          const rm={id:'living',type:'living',cols:7,wrows:2,frows:4,fix:[]};
          let rendered=0,closed=0,evening=0;
          const state={journey:{gender:'female',deco:{fridge:{kind:'own',cap:10,used:0,full:40,wake:60,foods:[]}}},needs:{evening:{chosen:false}},wardrobe:{owned:['ao_len']}};
          const S={room:rm.id,edit:false,env:{api:{state,content:{journey:{wardrobe:{items:[{id:'ao_len',slot:'top',price:10,name:'Áo len'},{id:'ao_moi',slot:'top',price:20,name:'Áo mới'},{id:'ao_quen',slot:'top',price:0,name:'Áo quen'}]}}}},act:n=>{if(n==='evening')evening++;}},dlg:{querySelector:()=>null,close:()=>closed++}};
          const pieces=['tu_lanh','giuong','tu_quan_ao'].map((id,i)=>({id:'p:d'+i,it:{id,w:2,h:1,spot:'floor'},q:{r:rm.id,x:0,y:20,f:0},mate:true}));
          const w=setup({S,A,V:()=>state.journey.deco,roomOf:()=>rm,inRoom:()=>[],mateIn:()=>pieces,hostFor:()=>null,send:async()=>null,render:()=>rendered++,sfx:()=>{},calm:()=>true,roomSvg:()=>null});
          w.tap(rm,{x:20,y:100},pieces[0].id);
          assert.equal(globalThis.__homeWalk.state().fridge,true,'spouse fridge opens');
          w.tap(rm,{x:20,y:100},pieces[1].id);
          assert.equal(evening,1,'spouse bed opens personal evening choices');
          assert.equal(closed,1);
          w.tap(rm,{x:20,y:100},pieces[2].id);
          const panel=w.panel(state.journey.deco,rm);
          assert.ok(panel.includes('Áo len'),'closet shows the acting player’s owned clothes');
          assert.ok(panel.includes('Áo quen'));
          assert.equal(panel.includes('Áo mới'),false,'unowned clothes do not transfer through the shared closet');
          pieces.length=0;
          assert.equal(w.panel(state.journey.deco,rm),'','a removed spouse closet closes');
        """
        result = subprocess.run([shutil.which('node'), '--input-type=module', '-e', script,
                                 (root / 'public/js/v4/home-walk.js').as_uri(),
                                 (root / 'public/js/v4/deco-art.js').as_uri()], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
