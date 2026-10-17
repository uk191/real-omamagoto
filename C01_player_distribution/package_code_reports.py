"""Small standalone source/report pack; original statistical DB stays separate."""
import hashlib,json,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent;ART=REPO/'artifacts'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
files=[]
for folder in ['JapanFamily/23_experience_c01','C01_player_distribution']:
 for p in sorted((REPO/folder).rglob('*')):
  if p.is_file() and not any(x in p.relative_to(REPO/folder).parts for x in ['runtime','__pycache__']):files.append(p)
files.append(REPO/'C0_player_distribution/prepare_and_start.ps1')
for name in ['C01_PLAYER_DOWNLOAD.json','C01_START_HELPER.json','C01_RELEASE_VERIFICATION.json','C01_START_HELPER_VERIFICATION.json']:
 files.append(ART/name)
manifest={'version':'C-0.1-P0.1','base_archive_sha256':'216e260e125d00c7c4f5358d5d70551eec4a211cc470b0678511ff19adcf8649','files':{p.relative_to(REPO).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}}
out=ART/'C01_P0B_CODE_AND_REPORTS.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(REPO).as_posix())
 z.writestr('C01_CODE_AND_REPORTS_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for name,r in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==r['sha256']
record={'filename':out.name,'bytes':out.stat().st_size,'sha256':sha(out),'files':len(files)+1}
(ART/'C01_CODE_AND_REPORTS.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
records=[]
for name in ['C01_P0B_PLAY_WINDOWS_X64.zip','C01_P0B_START_HELPER.zip','C01_P0B_CODE_AND_REPORTS.zip','C01_RELEASE_VERIFICATION.json','C01_START_HELPER_VERIFICATION.json']:
 p=ART/name;records.append({'filename':name,'bytes':p.stat().st_size,'sha256':sha(p)})
(ART/'C01_SHA256SUMS.txt').write_text(''.join(r['sha256']+'  '+r['filename']+'\n' for r in records))
(ART/'C01_DELIVERY.json').write_text(json.dumps({'version':'C-0.1-P0.1','artifacts':records},indent=2))
