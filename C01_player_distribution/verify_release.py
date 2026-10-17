"""Inspect the SAVED distribution in a separate directory and start its launcher."""
import argparse,gzip,hashlib,json,os,shutil,sqlite3,subprocess,sys,time,urllib.error,urllib.request,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 archive=REPO/'artifacts/C01_PLAY_WINDOWS_X64.zip';record=json.loads((REPO/'artifacts/C01_PLAYER_DOWNLOAD.json').read_text());assert sha(archive)==record['sha256']
 target=Path('/workspace/c01_release_inspection');target.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist());z.extractall(target)
 root=target/'C01_Play';manifest=json.loads((root/'PLAYER_MANIFEST.json').read_text());assert sha(root/'PLAYER_MANIFEST.json')==record['manifest_sha256']
 for name,m in manifest['files'].items():
  p=root/name;assert p.stat().st_size==m['bytes'] and sha(p)==m['sha256'],name
 db=root/'app/JapanFamily/22_experience_c0/data/runtime_region.sqlite'
 with sqlite3.connect(f'file:{db}?mode=ro',uri=True) as c:
  integrity=c.execute('pragma integrity_check').fetchall();fk=c.execute('pragma foreign_key_check').fetchall();assert integrity==[('ok',)] and not fk
 log=(target/'launcher_test.log').open('w',encoding='utf-8')
 env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'}
 proc=subprocess.Popen([sys.executable,'-I','-X','utf8',str(root/'launch.py'),'--no-browser','--port','18791'],cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT)
 base='http://127.0.0.1:18791';checks={};v=None
 def call(path,body=None,header=True):
  data=None if body is None else json.dumps(body).encode();headers={'Content-Type':'application/json','X-C0-Client':'browser-v1'} if header else {'Content-Type':'application/json'}
  with OPENER.open(urllib.request.Request(base+path,data,headers),timeout=45) as r:return json.load(r)
 try:
  for _ in range(100):
   if proc.poll() is not None:raise AssertionError('launcher exited; inspect '+str(target/'launcher_test.log'))
   try:
    if call('/api/health')['version']=='C-0.1-P0.1':break
   except OSError:pass
   time.sleep(.15)
  else:raise AssertionError('launcher not ready')
  checks['extracted_launcher_and_portable_database_start']=True
  data=call('/api/start',{'seed':'independent-release','prefecture_code':'13','environment':'urban','child_name':'りつ','conditions':{'mother_age':30,'father_age':32,'birth_rank':1},'initial_cash_yen':5000000});sid=data['sid'];v=data['view']
  def command(name,**kwargs):return call('/api/command',{'sid':sid,'revision':v['revision'],'command':name,**kwargs})
  firstrev=v['revision'];v=command('advance')['view']
  try:call('/api/command',{'sid':sid,'revision':firstrev,'command':'advance'});raise AssertionError('stale command accepted')
  except urllib.error.HTTPError as e:assert e.code==409
  checks['stale_revision_rejected']=True
  old=json.dumps(v,sort_keys=True);fresh=call('/api/session?sid='+sid)['view'];assert json.dumps(fresh,sort_keys=True)==old;checks['reading_view_is_pure']=True
  for _ in range(100):
   if v['finished']:break
   event=v['event']
   if event:v=command('choose',event_id=event['id'],choice_id=event['options'][0]['id'])['view']
   else:v=command('advance')['view']
  assert v['finished'] and v['age_months']==24
  checks['extracted_pack_real_A_B_24_months']=True
  saved=command('save');loaded=call('/api/load',{'slot':saved['saved']['slot']});assert loaded['view']==v;checks['saved_pack_exact_reload']=True
  for path in ['/saves/'+saved['saved']['slot']+'.json.gz','/runtime/saves','/app/JapanFamily/data/region.sqlite']:
   try:call(path);raise AssertionError('private/static file exposure')
   except urllib.error.HTTPError as e:assert e.code==404
  try:call('/api/start',{},header=False);raise AssertionError('unguarded POST')
  except urllib.error.HTTPError as e:assert e.code==403
  checks['private_files_and_cross_origin_guard']=True
 finally:
  proc.send_signal(__import__('signal').SIGINT)
  try:proc.wait(timeout=15)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
  log.close()
 result={'version':'C-0.1-P0.1','archive':record,'zip_internal_CRC':'all_pass','all_manifest_SHA256':'all_pass','sqlite_integrity':integrity,'sqlite_foreign_key_errors':fk,'checks':checks,'independent_extraction_root':str(target),'native_Windows_execution_tested':False,'actual_platform':'Linux Python 3.12, pinned numpy/scipy; official Windows runtime and PE architecture preserved from verified baseline','ordinary_browser_evidence':'JapanFamily/23_experience_c01/reports/browser_verification.json'}
 (REPO/'artifacts/C01_RELEASE_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
