#!/usr/bin/env python3
"""Extract ZIP to a fresh folder, verify hashes, start server and test an API write."""
from pathlib import Path
from pg_test_support import test_env
import argparse,datetime,hashlib,http.cookiejar,json,re,subprocess,sys,tempfile,urllib.error,urllib.request,zipfile

def main():
    parser=argparse.ArgumentParser();parser.add_argument('zip',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    env=test_env()
    checks=[]
    with tempfile.TemporaryDirectory(prefix='mngln-package-') as temp:
        with zipfile.ZipFile(args.zip) as archive:
            if archive.testzip():raise RuntimeError('Bad ZIP CRC.')
            for entry in archive.namelist():
                dest=(Path(temp)/entry).resolve()
                if not dest.is_relative_to(Path(temp).resolve()):raise RuntimeError('Unsafe archive path.')
            archive.extractall(temp)
        root=Path(temp)/'mot-ngay-lam-nghe'
        manifest=json.loads((root/'MANIFEST.json').read_text())
        for entry in manifest['files']:
            data=(root/entry['path']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise RuntimeError('Hash mismatch: '+entry['path'])
        checks.append(f"All {len(manifest['files'])} source/asset hashes match")
        log=open(Path(temp)/'server.log','w+',encoding='utf-8')
        proc=subprocess.Popen([sys.executable,str(root/'server.py'),'--port','0','--namespace',str(Path(temp)/'package-test')],cwd=root,env=env,stdout=subprocess.PIPE,stderr=log,text=True)
        try:
            base=None
            for _ in range(40):
                line=proc.stdout.readline()
                match=re.search(r'http://127\.0\.0\.1:\d+',line)
                if match:base=match.group();break
                if not line and proc.poll() is not None:raise RuntimeError('Fresh server failed to start.')
            if not base:raise RuntimeError('Could not read server address.')
            client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            def get(path):return client.open(base+path,timeout=8)
            assert json.load(get('/api/health'))['status']=='ok';checks.append('Fresh extracted server starts with an isolated PostgreSQL schema')
            with get('/') as response:assert response.status==200 and b'world' in response.read()
            for asset in ['/js/app.js','/js/world.js','/js/boba-world.js','/js/operations-ui.js','/css/cozy.css','/js/experience-ui.js','/css/boba.css','/css/game.css','/favicon.svg','/audio/sfx/ting.mp3']:
                with get(asset) as response:assert response.status==200 and len(response.read())>0
            checks.append('Index, ES modules, styles and icon served from extracted paths')
            bootstrap=json.load(get('/api/bootstrap'))
            revision=bootstrap['revision'];serial=0
            def command(career,action,payload=None,expect_ok=True):
                nonlocal revision,serial
                serial+=1
                body={'request_id':f'package-smoke-{serial}','expected_revision':revision,'career':career,'action':action,'payload':payload or {}}
                req=urllib.request.Request(base+'/api/command',data=json.dumps(body).encode(),
                    headers={'Content-Type':'application/json','X-Game-CSRF':bootstrap['csrf'],'Origin':base},method='POST')
                try:
                    result=json.load(client.open(req,timeout=15))
                except urllib.error.HTTPError as error:
                    if expect_ok:raise RuntimeError(f'{action} failed: {error.read()[:300]!r}')
                    return error.code
                if not expect_ok:raise RuntimeError(f'{action} should have been refused')
                revision=result['revision']
                return result
            journey=bootstrap['state']['journey']
            assert journey['story'] and journey.get('gender') is None
            checks.append('A new player starts the story with no character chosen yet')
            assert command('pharmacy','select_career',expect_ok=False)==400
            checks.append('A workplace that is still locked is refused by the server')
            command('milk_tea','jr_profile',{'name':'Kiểm gói','gender':'male'})
            state=command('milk_tea','select_career')['state']
            assert state['journey']['gender']=='male' and state['current']=='milk_tea'
            state=command('milk_tea','start_day')['state']
            assert state['careers']['milk_tea']['open']
            checks.append('Profile, first workplace and first day open through the real HTTP endpoint')
            replay_body={'request_id':f'package-smoke-{serial}','expected_revision':revision-1,'career':'milk_tea','action':'start_day','payload':{}}
            req=urllib.request.Request(base+'/api/command',data=json.dumps(replay_body).encode(),
                headers={'Content-Type':'application/json','X-Game-CSRF':bootstrap['csrf'],'Origin':base},method='POST')
            replay=json.load(client.open(req,timeout=15));assert replay['replayed'] and replay['revision']==revision
            checks.append('A repeated request is replayed, not applied twice')
            backup=json.load(get('/api/save/export'))
            assert backup['format']=='mot-ngay-lam-nghe/save-v4' and backup['state']['schema']==4
            assert len(backup['state']['careers'])==len(bootstrap['state']['careers']) and 'journey' in backup['state']
            checks.append(f"Schema-4 backup with the journey and {len(backup['state']['careers'])} careers exports from a fresh installation")
        finally:
            proc.terminate();proc.wait(timeout=8);log.close()
    result={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'checks':checks,'zip_sha256':hashlib.sha256(args.zip.read_bytes()).hexdigest()}
    if args.report:args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
