"""C31 runnable delta over immutable C3. No research DB duplication."""
import hashlib,json,zipfile,sys
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent;ROOT=REPO/'JapanFamily/27_experience_c31';HERE=Path(__file__).resolve().parent;OUT=REPO/'artifacts'
BASE=REPO.parent/'c31_baseline/C3_PLAY_WINDOWS_X64.zip'
if not BASE.exists():BASE=REPO.parent/'c31_baseline/C3_PLAY_WINDOWS_X64.zip'
BASE_SHA='dc5f4ce7a48355588954b5de9f72aea6c850bc96330d52121b2e97d4a53d555f'
LARGE={'sixteen_branches.json','varied_households.json'}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def eligible(p):return p.is_file() and not any(t in p.relative_to(ROOT).parts for t in ['runtime','__pycache__'])
def player():
 assert sha(BASE)==BASE_SHA
 out=OUT/'C31_PLAY_WINDOWS_X64.zip';files={};preserved=0
 with zipfile.ZipFile(BASE) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
  assert src.testzip() is None
  for info in src.infolist():
   rel=info.filename.removeprefix('C3_Play/')
   if info.is_dir() or not rel.startswith(('app/','runtime/')):continue
   h=hashlib.sha256()
   with src.open(info) as r,dst.open('C31_Play/'+rel,'w') as w:
    while b:=r.read(1048576):h.update(b);w.write(b)
   files[rel]={'bytes':info.file_size,'sha256':h.hexdigest()};preserved+=1
  def put(n,b):dst.writestr('C31_Play/'+n,b);files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
  for p in sorted(ROOT.rglob('*')):
   if eligible(p) and not any(t in p.relative_to(ROOT).parts for t in ['reports','inputs']):put('app/JapanFamily/27_experience_c31/'+p.relative_to(ROOT).as_posix(),p.read_bytes())
  for name in ['launch.py','PLAY.cmd','READ_ME_JA.txt']:put(name,(HERE/name).read_text().replace('\r\n','\n').replace('\n','\r\n').encode('utf8'))
  put('DISTRIBUTION_PROVENANCE.json',json.dumps({'version':'C-3.1-four-decisions-research','base_sha256':BASE_SHA,'unchanged_inherited_files':preserved,'A_B_coefficients_unchanged':True,'no_new_long_term_child_effects':True,'large_original_research_DB_not_restored_or_duplicated':True,'Windows_actual_execution_tested':False},indent=2).encode())
  manifest={'version':'C-3.1-four-decisions-research','files':files};b=json.dumps(manifest,ensure_ascii=False,indent=2).encode();dst.writestr('C31_Play/PLAYER_MANIFEST.json',b)
 assert out.stat().st_size<104857600
 record={'file':out.name,'bytes':out.stat().st_size,'sha256':sha(out),'manifest_sha256':hashlib.sha256(b).hexdigest(),'preserved_files':preserved,'base_sha256':BASE_SHA}
 (OUT/'C31_PLAYER_DOWNLOAD.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
def reports():
 code=OUT/'C31_CODE_AND_REPORTS.zip';data=OUT/'C31_COMPARISON_DATA.zip'
 with zipfile.ZipFile(code,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z,zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as d:
  for p in sorted(ROOT.rglob('*')):
   if eligible(p):(d if p.name in LARGE else z).write(p,p.relative_to(REPO))
  for p in sorted(HERE.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:z.write(p,p.relative_to(REPO))
 record=[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in [code,data]]
 (OUT/'C31_REPORT_DOWNLOADS.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
if __name__=='__main__':
 if '--reports-only' in sys.argv:reports()
 else:player()
