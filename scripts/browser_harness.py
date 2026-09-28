"""Optional in-process browser harness for environments with navigation disabled.

Loads *unchanged app modules* into isolated scopes on about:blank, then bridges
fetch to the local development server using httpx. No browser network policy is
changed. This validates the real DOM/game UI against the real HTTP API, but is
not a direct-browser network/CSP compatibility test. Normal mode uses page.goto.
"""
from pathlib import Path
import re
import httpx
ROOT=Path(__file__).resolve().parents[1]

class BrowserHarness:
    def __init__(self, page, base='http://127.0.0.1:8765', bridge=False):
        self.page=page; self.base=base;self.bridge=bridge
        self.client=httpx.Client(base_url=base,timeout=15)
    def load(self):
        if not self.bridge:
            self.page.goto(self.base,wait_until='networkidle');return
        self.page.expose_binding('__test_http',self.http)
        self.reload()
    def reload(self):
        if not self.bridge:self.page.reload(wait_until='networkidle');return
        self.page.goto('about:blank')  # Fresh JS global: no duplicate event listeners on reload.
        html=(ROOT/'public/index.html').read_text()
        html=re.sub(r'<link[^>]*>','',html)
        html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S)
        css=(ROOT/'public/css/game.css').read_text()+'\n'+(ROOT/'public/css/boba.css').read_text()+'\n'+(ROOT/'public/css/cozy.css').read_text()
        self.page.set_content(html.replace('</head>',f'<style>{css}</style></head>'))
        modules=[]
        exports={'icons':['icon','portrait','itemArt','escapeHTML'],'api':['GameAPI'],'world':['World'],'audio':['Sound'],'boba-world':['BobaWorld'],'operations-ui':['operationsView'],'experience-ui':['nextStep','lifeNav','guestRibbon','experienceView','extendedJob','experienceSummary']}
        for name,names in exports.items():
            source=(ROOT/f'public/js/{name}.js').read_text()
            source=re.sub(r'^import .*?;\s*$', '',source,flags=re.M)
            if name=='boba-world':source='const {World}=__world;\n'+source
            if name in ('operations-ui','experience-ui'):source='const {icon,portrait,escapeHTML:esc}=__icons;\n'+source
            source=re.sub(r'\bexport\s+(?=(?:class|const|let|function)\b)','',source)
            module_name=name.replace('-', '_')
            modules.append(f'const __{module_name}=(()=>{{{source}\nreturn {{{",".join(names)}}};}})();')
        app=(ROOT/'public/js/app.js').read_text()
        app=re.sub(r'^import .*?;\s*$', '',app,flags=re.M)
        prelude="""
        window.fetch=async (url,options={})=>{
          const response=await window.__test_http({url:String(url),method:options.method||'GET',headers:options.headers||{},body:options.body||null});
          return new Response(response.body,{status:response.status,headers:response.headers});
        };
        """
        bindings='const {nextStep,lifeNav,guestRibbon,experienceView,extendedJob,experienceSummary}=__experience_ui;const {BobaWorld}=__boba_world,{operationsView}=__operations_ui;const {GameAPI}=__api,{World}=__world,{Sound}=__audio,{icon,portrait,itemArt,escapeHTML:esc}=__icons;'
        self.page.evaluate('()=>{'+prelude+'\n'.join(modules)+'\nvoid(async()=>{'+bindings+app+'})();}')
        self.page.wait_for_selector('#app:not([hidden])',timeout=15000)
    def http(self,source,request):
        path=request['url']
        if not path.startswith('/api/') or path.startswith('//'):raise ValueError('Only the local game API is permitted in this harness.')
        headers=request.get('headers',{});headers['Origin']=self.base
        response=self.client.request(request['method'],path,headers=headers,content=request.get('body'))
        return {'status':response.status_code,'body':response.text,'headers':{'Content-Type':response.headers.get('content-type','application/json')}}
    def close(self):self.client.close()
