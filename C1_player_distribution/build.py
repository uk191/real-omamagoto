"""Content-addressed upgrade: old app/runtime bytes preserved; new player layer added."""
import hashlib,json,zipfile,sys
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent;ROOT=REPO/'JapanFamily/24_experience_c1';HERE=Path(__file__).resolve().parent;OUT=REPO/'artifacts'
BASE=REPO.parent/'c1_baseline/C01_P0B_PLAY_WINDOWS_X64.zip';BASE_SHA='a8ee71e0a38f3719f4a1603bfa8495532010e6a4ee34bcfd37a24e157133f97d'
def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def eligible(p):return p.is_file() and not any(x in ['__pycache__','runtime'] for x in p.relative_to(ROOT).parts)
def build():
 assert sha(BASE)==BASE_SHA
 out=OUT/'C1_PLAY_WINDOWS_X64.zip';files={};unchanged=0
 with zipfile.ZipFile(BASE) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
  assert src.testzip() is None
  for info in src.infolist():
   rel=info.filename.removeprefix('C01_Play/')
   if info.is_dir() or not rel.startswith(('runtime/','app/')):continue
   h=hashlib.sha256()
   with src.open(info) as r,dst.open('C1_Play/'+rel,'w') as w:
    while data:=r.read(1048576):h.update(data);w.write(data)
   files[rel]={'bytes':info.file_size,'sha256':h.hexdigest()};unchanged+=1
  def put(rel,data):
   dst.writestr('C1_Play/'+rel,data);files[rel]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
  for p in sorted(ROOT.rglob('*')):
   if not eligible(p) or 'reports' in p.relative_to(ROOT).parts:continue
   put('app/JapanFamily/24_experience_c1/'+p.relative_to(ROOT).as_posix(),p.read_bytes())
  for name in ['launch.py','PLAY.cmd','READ_ME_JA.txt']:
   data=(HERE/name).read_text().replace('\r\n','\n').replace('\n','\r\n').encode('utf8')
   if name.endswith('.txt'):data=b'\xef\xbb\xbf'+data
   put(name,data)
  provenance={'version':'C-1.0-experience-research','base_sha256':BASE_SHA,'unchanged_base_files':unchanged,'old_scientific_A_B_and_runtime_unchanged':True,'research_raw_DB_not_duplicated':True,'C1_expense_ledger':'balanced interperiod native Ledger entries; no native rules edited','acute_reaction_coefficients':'explicit uncalibrated C1 scenario; no B developmental effects','windows_actual_machine_tested':False}
  put('DISTRIBUTION_PROVENANCE.json',json.dumps(provenance,ensure_ascii=False,indent=2).encode())
  manifest={'version':provenance['version'],'files':files};dst.writestr('C1_Play/PLAYER_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())
 assert out.stat().st_size<104857600
 with zipfile.ZipFile(out) as z:assert z.testzip() is None
 code=OUT/'C1_CODE_AND_REPORTS.zip'
 with zipfile.ZipFile(code,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(ROOT.rglob('*')):
   if eligible(p):z.write(p,p.relative_to(REPO))
  for p in sorted(HERE.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:z.write(p,p.relative_to(REPO))
 result={'player':{'name':out.name,'bytes':out.stat().st_size,'sha256':sha(out)},'code_reports':{'name':code.name,'bytes':code.stat().st_size,'sha256':sha(code)},'base_archive':BASE.name,'base_sha256':BASE_SHA,'preserved_files':unchanged}
 (OUT/'C1_DOWNLOADS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(OUT/'C1_SHA256SUMS.txt').write_text('\n'.join(f'{sha(p)}  {p.name}' for p in [out,code])+'\n');print(json.dumps(result,ensure_ascii=False))
def reports_only():
 code=OUT/'C1_CODE_AND_REPORTS.zip'
 with zipfile.ZipFile(code,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(ROOT.rglob('*')):
   if eligible(p):z.write(p,p.relative_to(REPO))
  for p in sorted(HERE.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:z.write(p,p.relative_to(REPO))
 result=json.loads((OUT/'C1_DOWNLOADS.json').read_text());result['code_reports']={'name':code.name,'bytes':code.stat().st_size,'sha256':sha(code)}
 (OUT/'C1_DOWNLOADS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['code_reports']))
if __name__=='__main__':
 if '--reports-only' in sys.argv:reports_only()
 else:build()
