#!/usr/bin/env python3
"""Create a clean source ZIP with hashes; excludes runtime data and secrets.
The public/ JS and CSS go in minified (scripts/build_static.py, needs node/npx); --no-minify keeps the source bytes."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
BLOCKED_DIRS={'_v','.git','.venv','node_modules','__pycache__','.pytest_cache','test-results','todo','done','screens','output','.playwright-cli'}
BLOCKED_SUFFIXES={'.zip','.sqlite','.sqlite3','.db','.pyc','.pyo','.ttf','.otf','.eot'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT.parent/'Mot_ngay_lam_nghe_Source_Code_v0_5.zip')
    parser.add_argument('--no-minify',action='store_true',help='ship public/ JS and CSS as written (no node needed)');args=parser.parse_args()
    paths=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(ROOT)
        if any(part in BLOCKED_DIRS for part in rel.parts):continue
        if path.suffix.lower() in BLOCKED_SUFFIXES or path.name in {'.env','.DS_Store','vapid.json'} or rel==Path('MANIFEST.json'):continue
        if rel.parts[0]=='storage' and path.name!='.gitkeep':continue
        if 'failure' in path.name and path.name.startswith('browser'):continue
        if path.name.endswith(('-wal','-shm')):continue
        paths.append(path)
    built={}
    if not args.no_minify:
        sys.path.insert(0,str(ROOT/'scripts'))
        from build_static import BuildError,minify
        try:built=minify(ROOT)
        except BuildError as e:sys.exit(f'package: {e}')
    data=lambda p:built.get(p.relative_to(ROOT).as_posix()) or p.read_bytes()
    version=re.search(r'^__version__\s*=\s*"([^"]+)"',(ROOT/'game/__init__.py').read_text(encoding='utf-8'),re.M).group(1)
    manifest={'project':'Một ngày làm nghề','version':version,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'public web game: character journey, multiplayer street, AI personas, web push, vi/en','minified':len(built),'files':[{'path':str(p.relative_to(ROOT)),'bytes':len(data(p)),'sha256':hashlib.sha256(data(p)).hexdigest()} for p in paths]}
    mp=ROOT/'MANIFEST.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for path in [*paths,mp]:
            arc=str(Path(ROOT.name)/path.relative_to(ROOT));rel=path.relative_to(ROOT).as_posix()
            if rel in built:  # the minified copy, with the source file's mode and time
                info=zipfile.ZipInfo.from_file(path,arc);info.compress_type=zipfile.ZIP_DEFLATED;out.writestr(info,built[rel],compresslevel=9)
            else:out.write(path,arc)
    with zipfile.ZipFile(args.output) as archive:
        bad=archive.testzip()
        if bad:raise RuntimeError('Corrupt ZIP member: '+bad)
    print(json.dumps({'zip':str(args.output),'files':len(paths)+1,'minified':len(built),'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
