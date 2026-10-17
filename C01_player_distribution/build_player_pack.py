"""Build a stand-alone Windows C01 pack from the verified preserved C0 pack.
Only the player layer / launcher change; A/B and runtime bytes are copied exactly.
"""
import hashlib,json,shutil,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent;SOURCE=Path(__file__).resolve().parent
ROOT=REPO/'JapanFamily/23_experience_c01';ART=REPO/'artifacts'
BASE_SHA='216e260e125d00c7c4f5358d5d70551eec4a211cc470b0678511ff19adcf8649'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def build():
 base=ART/'C0_PLAY_WINDOWS_X64.zip';assert sha(base)==BASE_SHA
 out=ART/'C01_P0_PLAY_WINDOWS_X64.zip';files={}
 def write(z,name,data):
  z.writestr('C01_Play/'+name,data);files[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 with zipfile.ZipFile(base) as src,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
  assert src.testzip() is None
  for info in src.infolist():
   assert info.filename.startswith('C0_Play/') and '..' not in Path(info.filename).parts
   name=info.filename[len('C0_Play/'):]
   if info.is_dir() or name in ['PLAYER_MANIFEST.json','DISTRIBUTION_PROVENANCE.json','launch.py','PLAY.cmd','READ_ME_JA.txt']:continue
   # Original reports and play histories remain in the preserved C0 archives;
   # they are not duplicated into the new executable pack.
   if name.startswith('app/JapanFamily/22_experience_c0/results/'):continue
   h=hashlib.sha256()
   with src.open(info) as r,dst.open('C01_Play/'+name,'w') as w:
    while data:=r.read(1024*1024):h.update(data);w.write(data)
   files[name]={'bytes':info.file_size,'sha256':h.hexdigest()}
  for p in sorted(ROOT.rglob('*')):
   rel=p.relative_to(ROOT)
   if not p.is_file() or any(x in rel.parts for x in ['__pycache__','runtime','screenshots']):continue
   write(dst,'app/JapanFamily/23_experience_c01/'+rel.as_posix(),p.read_bytes())
  for name in ['launch.py','PLAY.cmd','READ_ME_JA.txt']:
   data=(SOURCE/name).read_text(encoding='utf-8').replace('\r\n','\n').replace('\n','\r\n').encode('utf-8')
   if name.endswith('.txt'):data=b'\xef\xbb\xbf'+data
   write(dst,name,data)
  provenance=json.loads(src.read('C0_Play/DISTRIBUTION_PROVENANCE.json'))
  provenance.update(player_version='C-0.1-P0.1',base_archive_sha256=BASE_SHA,
                    scientific_A_B_code_unchanged=True,player_layer_rewritten=True,
                    old_C0_and_all_research_assets_preserved_in_workspace=True,
                    windows_machine_execution_tested=False)
  write(dst,'DISTRIBUTION_PROVENANCE.json',json.dumps(provenance,ensure_ascii=False,indent=2).encode())
  manifest={'package':'C01_PLAY_WINDOWS_X64','version':'C-0.1-P0.1','files':files,'base_archive_sha256':BASE_SHA}
  manifest_data=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
  dst.writestr('C01_Play/PLAYER_MANIFEST.json',manifest_data)
 with zipfile.ZipFile(out) as z:assert z.testzip() is None
 assert out.stat().st_size<104857600,'Exceeds GitHub 100MiB blob limit'
 record={'filename':out.name,'bytes':out.stat().st_size,'sha256':sha(out),'manifest_sha256':hashlib.sha256(manifest_data).hexdigest(),'files':len(files)+1,'uncompressed_bytes':sum(r['bytes'] for r in files.values())+len(manifest_data)}
 (ART/'C01_PLAYER_DOWNLOAD.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
if __name__=='__main__':build()
