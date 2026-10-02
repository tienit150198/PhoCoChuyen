// 🙂 The chat face in node (tests/test_avatar.py runs it): the code round-trips, follows the save and the wardrobe,
// every part draws, and a hostile code never reaches the markup. Prints one JSON line: {ok, failures}.
const root=new URL('../public/js/v4/',import.meta.url).href;
const {faceSVG,avInner,NAMES}=await import(root+'face.js');
const {PARTS,ORDER,DEFAULT_FACE,EMOJIS,encode,faceCode,parseFace,autoFace}=await import(root+'face-code.js');
const fails=[];
const check=(cond,what)=>{if(!cond)fails.push(what);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

const state=(extra={})=>({journey:{gender:'female'},...extra});
// every value of every part: it round-trips and draws (no undefined / NaN in the markup)
for(const k of ORDER){
  const vals=k==='freckles'?[true,false]:PARTS[k];
  for(const v of vals){
    const f={...DEFAULT_FACE,[k]:v},code=encode('f1',f,state());
    const back=parseFace(code);
    check(back&&back.kind==='face'&&same(back.f,f),`round trip ${k}=${v}`);
    const svg=faceSVG(code,40);
    check(svg.startsWith('<svg')&&!/undefined|NaN|null/.test(svg),`draws ${k}=${v}`);
    if(k!=='freckles'&&k!=='hwc'&&k!=='shirt')check(typeof NAMES[k]?.[v]==='string',`a name for ${k}=${v}`);
  }
}
// a save that never opened the builder: the character's skin, hair and colour, and the wardrobe clothes in their colours
const s=state({wardrobe:{v:1,look:{hair:'toc_xoan',shade:'mau_den',skin:'da_ngam',top:'ao_hoodie',bottom:'quan_jean',shoes:'giay_nau',acc:'non_la',uniform:true}},
  colors:{v:1,have:['mint'],wear:{ao_hoodie:'mint'},deco:{}},wardrobe_colors:{v:1,wear:{non_la:'vang'},owned:['non_la:vang']}});
const auto=parseFace(faceCode(s));
check(faceCode(s).startsWith('a1.'),'an automatic face is tagged a1');
check(auto.f.skin==='s6'&&auto.f.hair==='xoan'&&auto.f.hc==='den'&&auto.f.shape==='oval',`auto face follows the character ${JSON.stringify(auto.f)}`);
check(auto.g==='female'&&auto.top==='ao_hoodie'&&auto.topTint==='mint'&&auto.acc==='non_la'&&auto.accTint==='vang',`wardrobe clothes ${JSON.stringify(auto)}`);
check(same(autoFace(s),auto.f),'autoFace = the parsed face');
// a built face: f1, its own parts; a plain tee drops the wardrobe clothes
const built={...s,avatar:{v:1,kind:'face',face:{...DEFAULT_FACE,hair:'afro',shirt:'navy'},emoji:'🌸'}};
const b=parseFace(faceCode(built));
check(faceCode(built).startsWith('f1.')&&b.f.hair==='afro'&&b.top==='ao_quen'&&b.acc==='pk_khong',`plain tee ${faceCode(built)}`);
check(faceCode({...s,avatar:{v:1,kind:'emoji',face:DEFAULT_FACE,emoji:'🐱'}})==='e1.🐱','emoji kind');
check(parseFace('e1.🐱')?.emoji==='🐱'&&parseFace('e1.💩')===null,'emoji whitelist');
// hostile codes: ids that are not ours fall back, nothing typed reaches the markup
const evil='f1.s9"><script>alert(1)</script>.tron.lon.ngan.den.cuoi.0.0.do.0.0.0.kem" onload="x.tu.m.ao_hoodie".mint.<img>.0';
const svg=faceSVG(evil,40);
check(svg.startsWith('<svg')&&!/script|onload|<img|alert/.test(svg),'a hostile code draws only our art');
check(parseFace(evil).f.skin==='s2','an unknown skin takes the default');
check(faceSVG('x'.repeat(300))===''&&faceSVG('')===''&&faceSVG(null)==='','no face for nonsense');
check(avInner({av:'<b>x</b>'})==='&lt;b&gt;x&lt;/b&gt;','an emoji avatar is escaped');
check(avInner({av:'🌸',fc:'e1.🐶'})==='🐶','an emoji code wins over av');
check(avInner({av:'🌸',fc:faceCode(built)}).startsWith('<svg'),'a face code draws the face');
check(EMOJIS.length>=30,'emoji choices');
console.log(JSON.stringify({ok:!fails.length,failures:fails}));
