"""Load-time plumbing: versioned assets, the rendered page, /api/content, X-Game-Version, deploys."""
import base64,gzip,hashlib,http.client,json,os,re,shutil,subprocess,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from server import GameServer,PUBLIC
from game.storage import Store
from game import webassets
from game.webassets import WebAssets,content_hash,module_imports

ROOT=Path(__file__).resolve().parents[1]


def inline_scripts(html:str)->list[str]:
    return re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*type="application/json")[^>]*>(.*?)</script>',html,re.S)


class PageAndContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.server=GameServer(('127.0.0.1',0),Store(Path(cls.temp.name)/'state.db'))
        cls.server.cas_dir=Path(cls.temp.name)/'cas'
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start();cls.port=cls.server.server_port
        cls.quiet=patch.dict(os.environ,{'QUIET':'1'});cls.quiet.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.temp.cleanup();cls.quiet.stop()
    def req(self,path='/',headers=None):
        h={'Host':f'127.0.0.1:{self.port}'};h.update(headers or {})
        con=http.client.HTTPConnection('127.0.0.1',self.port,timeout=10);con.request('GET',path,headers=h);res=con.getresponse();data=res.read()
        out=(res.status,dict(res.getheaders()),data);con.close();return out
    def page(self):
        status,h,body=self.req('/');self.assertEqual(status,200);return h,body.decode()

    def test_page_versions_every_asset_and_csp_allows_only_its_inline_scripts(self):
        h,html=self.page()
        self.assertEqual(h['Cache-Control'],'no-cache');self.assertIn('ETag',h)
        for url in re.findall(r'(?:href|src)="(/(?:js|css|i18n|music)/[^"]+)"',html):
            path,_,query=url.partition('?');self.assertTrue(query.startswith('v='),url)
            self.assertEqual(query[2:],content_hash((PUBLIC/path.lstrip('/')).read_bytes()),url)
        imap=json.loads(re.search(r'<script type="importmap">(.*?)</script>',html,re.S).group(1))['imports']
        self.assertEqual(imap['/js/app.js'],f"/js/app.js?v={content_hash((PUBLIC/'js/app.js').read_bytes())}")
        self.assertIn('/js/careers/restaurant.js',imap);self.assertIn('/css/careers/food_kit.css',imap)
        csp=h['Content-Security-Policy'];self.assertNotIn('unsafe-inline',csp.split('style-src')[0])
        scripts=inline_scripts(html);self.assertEqual(len(scripts),2,'import map + boot script')
        for text in scripts:
            digest="'sha256-"+base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()+"'"
            self.assertIn(digest,csp)
        # The import map comes before any module load (modulepreload or module script).
        self.assertLess(html.index('type="importmap"'),html.index('rel="modulepreload"'))
        self.assertLess(html.index('type="importmap"'),html.index('type="module"'))
        # Every static import of app.js is preloaded in one round.
        preloaded={u.split('?')[0] for u in re.findall(r'rel="modulepreload" href="([^"]+)"',html)}
        self.assertTrue({'/js/api.js','/js/world.js','/js/v4/journey.js','/js/v4/stories.js'}<=preloaded)
        # 304 on revalidation.
        self.assertEqual(self.req('/',{'If-None-Match':h['ETag']})[0],304)

    def test_versioned_static_is_immutable_only_for_the_right_hash(self):
        good=content_hash((PUBLIC/'js/api.js').read_bytes())
        _,h,_=self.req(f'/js/api.js?v={good}');self.assertIn('immutable',h['Cache-Control'])
        _,h,_=self.req('/js/api.js');self.assertEqual(h['Cache-Control'],'no-cache')
        _,h,_=self.req('/js/api.js?v=000000000000');self.assertEqual(h['Cache-Control'],'no-cache')

    def test_old_version_is_served_from_the_content_addressed_store(self):
        old=b'export const OLD=1;\n';v=content_hash(old)
        dest=self.server.cas_dir/v/'js'/'api.js';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old)
        status,h,body=self.req(f'/js/api.js?v={v}');self.assertEqual((status,body),(200,old));self.assertIn('immutable',h['Cache-Control'])
        # A file removed by a later release is still there for pages of the older one.
        gone=self.server.cas_dir/v/'js'/'removed.js';gone.write_bytes(old)
        self.assertEqual(self.req(f'/js/removed.js?v={v}')[0],200)
        self.assertEqual(self.req('/js/removed.js')[0],404)
        # Bytes that do not match their name are never served as that version.
        bad=self.server.cas_dir/'aaaaaaaaaaaa'/'js'/'api.js';bad.parent.mkdir(parents=True,exist_ok=True);bad.write_bytes(b'x')
        _,h,body=self.req('/js/api.js?v=aaaaaaaaaaaa');self.assertEqual(h['Cache-Control'],'no-cache');self.assertEqual(body,(PUBLIC/'js/api.js').read_bytes())

    def test_content_split_out_of_bootstrap(self):
        status,h,body=self.req('/api/bootstrap?lite=1');data=json.loads(body)
        self.assertNotIn('content',data);self.assertTrue(data['content_url'].startswith('/api/content?v='))
        _,_,full=self.req('/api/bootstrap',{'Cookie':h['Set-Cookie'].split(';')[0]});full=json.loads(full)
        self.assertIn('content',full,'a page from before the split still gets the catalogue inline')
        status,ch,cbody=self.req(data['content_url'],{'Accept-Encoding':'gzip'})
        self.assertEqual(status,200);self.assertEqual(ch['Content-Encoding'],'gzip');self.assertIn('immutable',ch['Cache-Control'])
        self.assertEqual(json.loads(gzip.decompress(cbody)),full['content'])
        self.assertEqual(ch['ETag'],f'"{data["content_version"]}"')
        self.assertEqual(self.req(data['content_url'],{'If-None-Match':ch['ETag']})[0],304)
        _,ch,_=self.req('/api/content?v=stale');self.assertEqual(ch['Cache-Control'],'no-cache')
        # The page names the same content version.
        _,html=self.page();self.assertIn(f'content="{data["content_url"]}"',html)
        self.assertLess(len(json.dumps(data).encode()),80_000,'bootstrap stays small without the catalogue')

    def test_content_parts_rebuild_the_whole_catalogue(self):
        _,_,body=self.req('/api/bootstrap?lite=1');data=json.loads(body);url=data['content_url']
        whole=json.loads(self.req(url)[2])
        parts={}
        for name in ('core','more'):
            status,h,raw=self.req(f'{url}&part={name}',{'Accept-Encoding':'gzip'})
            self.assertEqual(status,200,name);self.assertIn('immutable',h['Cache-Control']);self.assertEqual(h['ETag'],f'"{data["content_version"]}-{name}"')
            parts[name]=json.loads(gzip.decompress(raw))
        core,more=parts['core'],parts['more']
        self.assertEqual(core.pop('part'),'core')
        self.assertLess(len(json.dumps(core,ensure_ascii=False).encode()),len(json.dumps(whole,ensure_ascii=False).encode())//2,'the first frame waits for under half')
        self.assertTrue(set(core['careers'])==set(whole['careers']) and not any(core['careers'].values()),'career ids only')
        for key in ('employment','operations','situations'):self.assertNotIn(key,core);self.assertEqual(more[key],whole[key])
        self.assertNotIn('certs',core['journey']);self.assertNotIn('stories',core['experiences'])
        rebuilt=dict(core)
        for key,value in more.items():rebuilt[key]={**core[key],**value} if isinstance(core.get(key),dict) else value
        rebuilt['careers']={cid:json.loads(self.req(f'{url}&career={cid}')[2]) for cid in core['careers']}
        self.assertEqual(json.dumps(rebuilt,sort_keys=True),json.dumps(whole,sort_keys=True))
        self.assertEqual(self.req(f'{url}&career=nope')[0],404);self.assertEqual(self.req(f'{url}&part=nope')[0],404)
        self.assertEqual(self.req(f'{url}&part=core',{'If-None-Match':f'"{data["content_version"]}-core"'})[0],304)

    def test_bootstrap_names_the_first_workplace_to_preload(self):
        _,h,body=self.req('/api/bootstrap?lite=1');view=json.loads(body)['state']
        place=view.get('current') or view.get('focus')
        warm=h.get('X-Game-Warm','').split(',');self.assertTrue(warm[0].startswith('/js/scenes/'),warm)
        _,html=self.page();imap=json.loads(re.search(r'<script type="importmap">(.*?)</script>',html,re.S).group(1))['imports']
        preloaded={u.split('?')[0] for u in re.findall(r'rel="modulepreload" href="([^"]+)"',html)}
        for path in warm:self.assertIn(path,imap);self.assertNotIn(path,preloaded,'already in the first round')
        if place in json.loads(self.req(json.loads(body)['content_url']+'&part=core')[2])['careers']:self.assertEqual(h.get('X-Game-Place'),place)
        else:self.assertNotIn('X-Game-Place',h)

    def test_game_version_header_on_every_api_response(self):
        _,html=self.page();own=re.search(r'<meta name="mnl-version" content="([^"]+)"',html).group(1)
        for path in ('/api/health','/api/bootstrap?lite=1','/api/state','/api/nope'):
            _,h,_=self.req(path);self.assertEqual(h.get('X-Game-Version'),own,path)
        self.assertNotIn('X-Game-Version',self.req('/js/api.js')[1])
        self.assertNotIn('X-Game-Version',self.req('/api/content')[1],'cacheable: a cached copy would carry an old version')
        self.assertEqual(json.loads(self.req('/api/health')[2])['game_version'],own)


class DeployTests(unittest.TestCase):
    """v1 is live (and cached by a player), then v2 is deployed: the v2 page names only v2 bytes, and a
    v1 page that is still open keeps getting v1 bytes for everything it asks for later."""
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp());self.public=self.tmp/'public'
        for rel in ('index.html','js/boot.js'):
            (self.public/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy(PUBLIC/rel,self.public/rel)
        (self.public/'js/app.js').write_text("import {a} from './lib.js';\nimport './v4/deep.js';\nexport const app=a;\n")
        (self.public/'js/lib.js').write_text("export const a='v1';\n")
        (self.public/'js/v4').mkdir();(self.public/'js/v4/deep.js').write_text("export {a} from '../lib.js';\n")
        (self.public/'js/careers').mkdir();(self.public/'js/careers/late.js').write_text("export default 'late v1';\n")
        (self.public/'css').mkdir();(self.public/'css/app.css').write_text('body{color:red}\n')
        self.cas=self.tmp/'cas'
    def tearDown(self):shutil.rmtree(self.tmp)
    def snapshot(self,assets):
        assets._checked=-1e9;return assets.snapshot()  # skip the 2 s recheck window
    def urls(self,html):
        # (the real template also names stylesheets this miniature public/ does not have: those stay unversioned)
        return {u for u in re.findall(r'(?:href|src)="(/(?:js|css)/[^"]+)"',html) if '?v=' in u}|set(json.loads(re.search(r'<script type="importmap">(.*?)</script>',html,re.S).group(1))['imports'].values())
    def resolve(self,url):
        """What the proxy returns for a ?v= URL: the CAS copy when present, else the current file."""
        path,_,q=url.partition('?v=');cas=self.cas/q/path.lstrip('/')
        return cas.read_bytes() if q and cas.exists() else (self.public/path.lstrip('/')).read_bytes()
    def test_v2_page_is_consistent_and_v1_page_keeps_v1_bytes(self):
        assets=WebAssets(self.public,"script-src 'self'",lambda:'c1','1.0.0')
        v1=self.snapshot(assets);assets.write_cas(self.cas);html1=v1.html.decode()
        self.assertEqual([u.split('?')[0] for u in v1.preload],['/js/app.js','/js/lib.js','/js/v4/deep.js'])
        cached={u:self.resolve(u) for u in self.urls(html1)}  # the player's browser cache after v1
        time.sleep(0.01)
        (self.public/'js/lib.js').write_text("export const a='v2';export const b=2;\n")
        (self.public/'js/careers/late.js').write_text("export default 'late v2';\n")
        v2=self.snapshot(assets);assets.write_cas(self.cas);html2=v2.html.decode()
        self.assertNotEqual(v1.version,v2.version)
        for url in self.urls(html2):
            path=url.split('?v=')[0]
            self.assertEqual(content_hash(self.resolve(url)),url.split('?v=')[1],url)
            self.assertEqual(self.resolve(url),(self.public/path.lstrip('/')).read_bytes(),'v2 page gets v2 bytes: '+url)
            if url in cached:self.assertEqual(cached[url],self.resolve(url),'a cached v1 entry reused by v2 is byte-identical')
        self.assertIn(b"'v2'",self.resolve(v2.url('/js/lib.js')))
        # The v1 tab, still open, lazily imports a module after the deploy: it gets the v1 bytes.
        # Compare the exact original fixture bytes: write_text uses CRLF on Windows.
        self.assertEqual(self.resolve(v1.url('/js/careers/late.js')),cached[v1.url('/js/careers/late.js')])
        self.assertEqual(self.resolve(v1.url('/js/lib.js')),cached[v1.url('/js/lib.js')])
        # Unchanged files keep their URL (still cached after the deploy); changed ones get a new one.
        self.assertEqual(v1.url('/css/app.css'),v2.url('/css/app.css'));self.assertNotEqual(v1.url('/js/lib.js'),v2.url('/js/lib.js'))
    def test_recheck_window_from_env(self):
        cases=[({},2.0),({'WORKERS':'4'},300.0),({'WORKERS':'4','STATIC_RECHECK_SECONDS':'3600'},3600.0),
               ({'STATIC_RECHECK_SECONDS':'0'},0.0),({'STATIC_RECHECK_SECONDS':'x','WORKERS':'1'},2.0),({'WORKERS':'bad'},2.0)]
        for env,want in cases:
            with patch.dict(os.environ,env,clear=False):
                for k in ('WORKERS','STATIC_RECHECK_SECONDS'):
                    if k not in env:os.environ.pop(k,None)
                self.assertEqual(webassets.recheck_seconds(),want,env)
    def test_snapshot_never_waits_for_a_recheck_in_progress(self):
        assets=WebAssets(self.public,"script-src 'self'",lambda:'c1','1.0.0')
        v1=self.snapshot(assets);assets._checked=-1e9
        with assets._lock:  # another thread is walking public/: the current snapshot answers at once
            self.assertIs(assets.snapshot(),v1)
        (self.public/'js/lib.js').write_text("export const a='v2, longer';\n")
        self.assertNotEqual(assets.snapshot().version,v1.version)
    def test_module_imports_parser(self):
        src="import {a,\n b} from './x.js';\nimport './side.js';\nexport {c} from \"../y.js\";\nexport const s='./not.js';\nconst m=import('./lazy.js');\n"
        self.assertEqual(sorted(module_imports(src)),['../y.js','./side.js','./x.js'])
        # Minified release files (scripts/build_static.py): statements share a line.
        mini='import{a as b}from"./x.js";import"./side.js";export*from"../y.js";export{c as d}from"./z.js";const m=import("./lazy.js");export const s="./not.js";'
        self.assertEqual(sorted(module_imports(mini)),['../y.js','./side.js','./x.js','./z.js'])

    def test_career_warm_lists_scene_workbench_and_stylesheets(self):
        warm=WebAssets(PUBLIC,"script-src 'self'",lambda:'c').snapshot().warm
        self.assertEqual(warm['milk_tea'].split(','),['/js/scenes/teabar.js','/js/careers/milk_tea.js','/js/careers/food_kit.js','/css/careers/milk_tea.css'])
        self.assertEqual(warm['restaurant'].split(',')[-2:],['/css/careers/food_kit.css','/css/careers/restaurant.css'],'the kit before the career sheet')
        self.assertEqual(warm['teacher'],'/js/scenes/classroom.js')
        self.assertEqual(set(warm),set(webassets.js_table((PUBLIC/'js/scenes/index.js').read_text(),'KIND_OF')))


class ClientChecks(unittest.TestCase):
    def test_update_pill_logic(self):
        node=shutil.which('node')
        if not node:self.skipTest('node not installed')
        out=subprocess.run([node,str(ROOT/'tests'/'update_pill.mjs')],cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(out.returncode,0,out.stderr+out.stdout)
    def test_career_stylesheets_have_no_import_chain(self):
        careers=(ROOT/'public/js/v4/careers.js').read_text()
        for css in (PUBLIC/'css/careers').glob('*.css'):
            self.assertNotIn('@import',css.read_text(),css.name)
        for kit in set(re.findall(r":'(\w+_kit)'",careers)):
            self.assertTrue((PUBLIC/'css/careers'/f'{kit}.css').exists(),kit)
    def test_boot_script_can_be_inlined(self):
        self.assertNotIn('</script',(PUBLIC/'js/boot.js').read_text().lower())


if __name__=='__main__':unittest.main()
