#!/usr/bin/env python3
"""Run standard-library tests and write an actual result report."""
from pathlib import Path
import datetime,io,json,os,platform,subprocess,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
class RecordedResult(unittest.TextTestResult):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.ids=[]
    def addSuccess(self,test):super().addSuccess(test);self.ids.append(test.id())
def main():
    if not (os.environ.get('TEST_DATABASE_URL') or '').startswith(('postgresql://','postgres://')):
        sys.exit('Set TEST_DATABASE_URL to a disposable PostgreSQL database before running tests.')
    os.environ.pop('DATABASE_URL',None)
    start=time.perf_counter();log=io.StringIO();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT))
    result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
    art=ROOT/'artifacts';art.mkdir(exist_ok=True)
    (art/'python-tests.log').write_text(log.getvalue(),encoding='utf-8')
    report={'run_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'tests_run':result.testsRun,'passed':len(result.ids),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'seconds':round(time.perf_counter()-start,3),'passed_tests':result.ids,'live_llm_tested':False}
    report['skipped_tests']=[{'test':test.id(),'reason':reason} for test,reason in result.skipped]
    (art/'python-test-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(log.getvalue()[-5000:] if not result.wasSuccessful() else f"PASS: {result.testsRun} tests ({report['passed']} passed, {report['skipped']} skipped) · {report['seconds']}s. Report: artifacts/python-test-report.json")
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
