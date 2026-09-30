#!/usr/bin/env python3
"""Create a clean source ZIP with hashes; excludes runtime data and secrets."""
from pathlib import Path
import argparse,datetime,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
BLOCKED_DIRS={'_v','.git','.venv','node_modules','__pycache__','.pytest_cache','test-results','todo','done','screens'}
BLOCKED_SUFFIXES={'.zip','.sqlite','.sqlite3','.db','.pyc','.pyo','.ttf','.otf','.eot'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT.parent/'Mot_ngay_lam_nghe_Source_Code_v0_5.zip');args=parser.parse_args()
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
    manifest={'project':'Một ngày làm nghề','version':'0.9.5','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'public web game: one character journey across 20 careers, multiplayer street, AI personas, web push, vi/en','files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    mp=ROOT/'MANIFEST.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for path in [*paths,mp]:out.write(path,str(Path(ROOT.name)/path.relative_to(ROOT)))
    with zipfile.ZipFile(args.output) as archive:
        bad=archive.testzip()
        if bad:raise RuntimeError('Corrupt ZIP member: '+bad)
    print(json.dumps({'zip':str(args.output),'files':len(paths)+1,'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
