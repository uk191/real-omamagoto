"""C2 runnable delta over immutable C1. No research DB duplication."""
import hashlib,json,zipfile,sys
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent;ROOT=REPO/'JapanFamily/25_experience_c2';HERE=Path(__file__).resolve().parent;OUT=REPO/'artifacts'
BASE=REPO/'artifacts/C1_PLAY_WINDOWS_X64.zip'
if not BASE.exists():BASE=REPO.parent/'c2_baseline/C1_PLAY_WINDOWS_X64.zip'
BASE_SHA='4f65d84579be58767f51b4b67cd71c2364273225882961602671968a886761b5'
LARGE={'families_24mo.json','event_branch_comparisons.json'}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def eligible(p):return p.is_file() and not any(t in p.relative_to(ROOT).parts for t in ['runtime','__pycache__'])
def player():
 assert sha(BASE)==BASE_SHA
 out=OUT/'C2_PLAY_WINDOWS_X64.zip';files={};preserved=0
 with zipfile.ZipFile(BASE) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
  assert src.testzip() is None
  for info in src.infolist():
   rel=info.filename.removeprefix('C1_Play/')
   if info.is_dir() or not rel.startswith(('app/','runtime/')):continue
   h=hashlib.sha256()
   with src.open(info) as r,dst.open('C2_Play/'+rel,'w') as w:
    while b:=r.read(1048576):h.update(b);w.write(b)
   files[rel]={'bytes':info.file_size,'sha256':h.hexdigest()};preserved+=1
  def put(n,b):dst.writestr('C2_Play/'+n,b);files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
  for p in sorted(ROOT.rglob('*')):
   if eligible(p) and not any(t in p.relative_to(ROOT).parts for t in ['reports','inputs']):put('app/JapanFamily/25_experience_c2/'+p.relative_to(ROOT).as_posix(),p.read_bytes())
  for name in ['launch.py','PLAY.cmd','READ_ME_JA.txt']:put(name,(HERE/name).read_text().replace('\r\n','\n').replace('\n','\r\n').encode('utf8'))
  put('DISTRIBUTION_PROVENANCE.json',json.dumps({'version':'C-2.0-low-load-research','base_sha256':BASE_SHA,'unchanged_inherited_files':preserved,'A_B_coefficients_unchanged':True,'no_new_long_term_child_effects':True,'large_original_research_DB_not_restored_or_duplicated':True,'Windows_actual_execution_tested':False},indent=2).encode())
  manifest={'version':'C-2.0-low-load-research','files':files};b=json.dumps(manifest,ensure_ascii=False,indent=2).encode();dst.writestr('C2_Play/PLAYER_MANIFEST.json',b)
 assert out.stat().st_size<104857600
 record={'file':out.name,'bytes':out.stat().st_size,'sha256':sha(out),'manifest_sha256':hashlib.sha256(b).hexdigest(),'preserved_files':preserved,'base_sha256':BASE_SHA}
 (OUT/'C2_PLAYER_DOWNLOAD.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
def reports():
 code=OUT/'C2_CODE_AND_REPORTS.zip';data=OUT/'C2_COMPARISON_DATA.zip'
 with zipfile.ZipFile(code,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z,zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as d:
  for p in sorted(ROOT.rglob('*')):
   if eligible(p):(d if p.name in LARGE else z).write(p,p.relative_to(REPO))
  for p in sorted(HERE.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:z.write(p,p.relative_to(REPO))
 record=[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in [code,data]]
 (OUT/'C2_REPORT_DOWNLOADS.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':
 if '--reports-only' in sys.argv:reports()
 else:player()
