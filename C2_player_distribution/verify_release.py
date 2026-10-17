import hashlib,json,sqlite3,subprocess,sys,tempfile,zipfile
from pathlib import Path
from build import BASE,BASE_SHA,OUT,sha

def verify():
 records=[];checks={}
 for name in ['C2_PLAY_WINDOWS_X64.zip','C2_CODE_AND_REPORTS.zip','C2_COMPARISON_DATA.zip','C2_START.zip']:
  p=OUT/name
  with zipfile.ZipFile(p) as z:assert z.testzip() is None
  records.append({'file':name,'bytes':p.stat().st_size,'sha256':sha(p),'CRC':True})
 with tempfile.TemporaryDirectory(prefix='c2-release-') as t:
  root=Path(t)
  with zipfile.ZipFile(OUT/'C2_PLAY_WINDOWS_X64.zip') as z:z.extractall(root)
  play=root/'C2_Play';manifest=json.loads((play/'PLAYER_MANIFEST.json').read_text())
  for n,r in manifest['files'].items():assert sha(play/n)==r['sha256'] and (play/n).stat().st_size==r['bytes']
  checks['all_extracted_manifest_files']=len(manifest['files'])
  assert sha(BASE)==BASE_SHA
  with zipfile.ZipFile(BASE) as old:
   m=json.loads(old.read('C1_Play/PLAYER_MANIFEST.json'));count=0
   for n,r in m['files'].items():
    if n.startswith(('runtime/','app/')):assert sha(play/n)==r['sha256'];count+=1
  checks['unchanged_inherited_files']=count
  db=play/'app/JapanFamily/22_experience_c0/data/runtime_region.sqlite';c=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
  assert c.execute('pragma integrity_check').fetchall()==[('ok',)] and c.execute('pragma foreign_key_check').fetchall()==[];c.close();checks['SQLite_integrity_and_foreign_keys']=True
  code=r'''
import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'app/JapanFamily/25_experience_c2'))
from c2.model import Experience
from c0.bridge import make_engine,digest
from c0.game import Game
E=make_engine();old=Game.start(E,seed=1301);old.advance(reviewed=True);assert old.core.assert_consistent()
x=Experience.start(E,seed=1301,policy='stable',conditions={'father_age':32,'mother_age':30})
for _ in range(20):
 if x.current_event:break
 x.tick()
assert x.current_event and not x.running
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'save.gz';x.save(p);y=Experience.load(p,E);assert x.snapshot()==y.snapshot()
 for obj in [x,y]:
  e=obj.events[-1];obj.choose(e['id'],e['choices'][0]['id']);obj.tick()
 assert x.snapshot()==y.snapshot()
while not x.game.finished:
 if x.current_event:
  e=x.events[-1];x.choose(e['id'],e['choices'][0]['id'])
 else:x.tick()
 assert x.financial_view()['cash_identity_residual'] in [0,None]
before=digest(x.snapshot());v=x.view();assert digest(x.snapshot())==before
for key in ['latent_state','random_streams','frailty','prob_distress','forecast_transactions']:
 assert key not in json.dumps(v)
assert x.date=='2028-10-01'
print(json.dumps({'old_API':True,'C2_24months':True,'save_at_event_and_resume':True,'seed_reproducibility':True,'player_projection_no_hidden_state':True,'cash_reconciliation':True}))
'''
  r=subprocess.run([sys.executable,'-I','-X','utf8','-c',code,str(play)],cwd=root,text=True,capture_output=True,timeout=150)
  if r.returncode:raise RuntimeError(r.stderr)
  checks['independent_restored_process']=json.loads(r.stdout)
 result={'archives':records,'checks':checks,'Windows_native_execution_tested':False,'human_user_test':False,'scientific_external_validity_claimed':False,'new_saved_zip_reextracted':True}
 (OUT/'C2_RELEASE_VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 (OUT/'C2_SHA256SUMS.txt').write_text('\n'.join(r['sha256']+'  '+r['file'] for r in records)+'\n');print(json.dumps(result))
if __name__=='__main__':verify()
