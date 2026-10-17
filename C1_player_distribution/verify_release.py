"""Verify saved archives and execute the restored copy in an independent process."""
import hashlib,json,os,sqlite3,subprocess,sys,tempfile,zipfile
from pathlib import Path
from build import REPO,OUT,BASE,sha

def verify():
 archives=[OUT/n for n in ['C1_PLAY_WINDOWS_X64.zip','C1_CODE_AND_REPORTS.zip','C1_UPGRADE.zip']]
 checks={};archive_records=[]
 for p in archives:
  with zipfile.ZipFile(p) as z:assert z.testzip() is None
  archive_records.append({'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'crc_ok':True})
 checks['three_archives_CRC']=True
 with tempfile.TemporaryDirectory(prefix='c1-independent-') as tmp:
  root=Path(tmp)
  with zipfile.ZipFile(archives[0]) as z:
   for n in z.namelist():assert '..' not in Path(n).parts and not Path(n).is_absolute()
   z.extractall(root)
  play=root/'C1_Play';manifest=json.loads((play/'PLAYER_MANIFEST.json').read_text())
  for rel,record in manifest['files'].items():assert (play/rel).stat().st_size==record['bytes'] and sha(play/rel)==record['sha256'],rel
  checks['all_manifest_hashes_after_extraction']=len(manifest['files'])
  with zipfile.ZipFile(BASE) as old:
   original=json.loads(old.read('C01_Play/PLAYER_MANIFEST.json'))['files'];n=0
   for rel,rec in original.items():
    if rel.startswith(('runtime/','app/')):assert sha(play/rel)==rec['sha256'],rel;n+=1
  checks['preserved_native_and_runtime_files']=n
  db=play/'app/JapanFamily/22_experience_c0/data/runtime_region.sqlite';connection=sqlite3.connect(f'file:{db}?mode=ro',uri=True)
  assert connection.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
  assert connection.execute('PRAGMA foreign_key_check').fetchall()==[];connection.close();checks['SQLite_integrity_foreign_keys']=True
  # Reconstruct the small upgrade solely using its manifest, proving identical new files.
  with zipfile.ZipFile(archives[2]) as z:
   m=json.loads(z.read('C1_Update/UPGRADE_MANIFEST.json'))
   for rel,h in m['dependencies'].items():assert sha(play/rel)==h
   for rel,h in m['files'].items():assert hashlib.sha256(z.read('C1_Update/payload/'+rel)).hexdigest()==h
   for rel,h in m['files'].items():
    if rel.startswith('app/'):assert sha(play/rel)==h
   checks['upgrade_dependencies_and_payload']=True
   hybrid=z.read('C1_Update/UPDATE_C1.cmd').decode('utf8');assert hybrid.count('# C1_POWERSHELL_BEGIN')==1 and '-ExecutionPolicy' not in hybrid
   checks['upgrade_no_policy_changes']=True
  source=r'''
import json,sys,tempfile
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'app/JapanFamily/24_experience_c1'))
from c1.experience import Experience
from c0.bridge import make_engine,digest
from c0.game import Game
E=make_engine();old=Game.start(E,seed=1301,conditions={'father_age':32,'mother_age':30});old.advance(reviewed=True,observer='father');assert old.core.assert_consistent()
x=Experience.start(E,seed=1301,initial_cash_yen=8000000,conditions={'father_age':32,'mother_age':30})
x.plan('voice',repeat=True)
for i in range(6):x.tick()
x.plan('book');x.tick();x.tick();assert x.inventory['book']
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'save.gz';x.save(p);y=Experience.load(p,E);assert x.snapshot()==y.snapshot()
 x.tick();y.tick();assert x.snapshot()==y.snapshot()
 truth=digest(x.snapshot());v=x.view();assert truth==digest(x.snapshot())
 assert not any(k in json.dumps(v) for k in ['latent_state','frailty','prob_distress','random_streams','transition_parameters','forecast_transactions'])
while not x.game.finished:x.tick()
assert x.date=='2028-10-01' and x.game.core.assert_consistent()
print(json.dumps({'old_API':True,'C1_generation_cost_time_resume_seed':True,'parent_projection_no_latent_state':True,'C1_24months':True,'external_expense_checks':[f['check'] for f in x.finance]}))
'''
  run=subprocess.run([sys.executable,'-I','-X','utf8','-c',source,str(play)],cwd=root,capture_output=True,text=True,timeout=150)
  if run.returncode:raise RuntimeError(run.stderr)
  checks['independent_python_process']=json.loads(run.stdout)
  # The standalone launcher must select C1, retain exact original runtime dependencies.
  launch=(play/'launch.py').read_text();assert '24_experience_c1' in launch and "VERSION = 'C-1.0-experience-research'" in launch
  checks['launcher_target']=True
 results={'archives':archive_records,'checks':checks,'saved_zip_independent_reextraction':True,'platform_executed':'Linux x64 Python3.12 and Chromium','windows_machine_execution_tested':False,'windows_upgrade_installer_executed':False,'scientific_external_validation':False,'actual_human_playtest':False}
 (OUT/'C1_RELEASE_VERIFICATION.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'C1_SHA256SUMS.txt').write_text('\n'.join(f'{x["sha256"]}  {x["name"]}' for x in archive_records)+'\n')
 print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__':verify()
