"""Start the real server and collect process/cgroup resources without modifying it."""
import json, os, signal, subprocess, sys, time
from pathlib import Path
import psutil
role=sys.argv[1]
args=[sys.executable,'server.py','--host','0.0.0.0','--port','8765','--namespace','/tmp/capacity'] if role=='api' else [sys.executable,'-m','live','--host','0.0.0.0','--port','8770']
proc=subprocess.Popen(args,cwd='/app')
def stop(*_):
    proc.send_signal(signal.SIGTERM)
signal.signal(signal.SIGTERM,stop)
with open('/result/'+role+'-resources.jsonl','a',buffering=1) as out:
    while proc.poll() is None:
        group=[psutil.Process(proc.pid)]
        try: group+=group[0].children(recursive=True)
        except psutil.Error: pass
        cpu=rss=0
        for p in group:
            try:
                t=p.cpu_times(); cpu+=t.user+t.system; rss+=p.memory_info().rss
            except psutil.Error: pass
        stat={k:int(v) for k,v in (s.split() for s in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines())}
        out.write(json.dumps(dict(at=time.time(),mono=time.monotonic(),cpu_seconds=cpu,rss_bytes=rss,processes=len(group),cgroup=stat,memory_bytes=int(Path('/sys/fs/cgroup/memory.current').read_text()),memory_events=Path('/sys/fs/cgroup/memory.events').read_text()))+'\n')
        time.sleep(1)
sys.exit(proc.returncode)
