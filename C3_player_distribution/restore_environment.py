"""Restore required unchanged scientific kernels from an immutable public pack.
Only missing app files are written; conflicts are reported, never overwritten.
"""
import hashlib,os,sys,tempfile,urllib.request,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent
CACHE=REPO.parent/'c2_baseline';NAME='C1_PLAY_WINDOWS_X64.zip'
SHA='4f65d84579be58767f51b4b67cd71c2364273225882961602671968a886761b5'
URL='https://github.com/uk191/real-omamagoto/raw/d3317e50a7a2ea2f74a72b1f4843248e6c34ce4e/player-download/'+NAME
def sha(path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def restore():
 CACHE.mkdir(exist_ok=True);archive=CACHE/NAME
 if not archive.exists():
  tmp=archive.with_suffix('.download')
  with urllib.request.urlopen(URL,timeout=120) as src,open(tmp,'wb') as dst:
   while b:=src.read(1048576):dst.write(b)
  if sha(tmp)!=SHA:tmp.unlink();raise ValueError('Baseline SHA256 mismatch')
  tmp.replace(archive)
 if sha(archive)!=SHA:raise ValueError('Baseline SHA256 mismatch')
 writes=0
 with zipfile.ZipFile(archive) as z:
  if z.testzip():raise ValueError('Baseline CRC mismatch')
  # Verify the complete set before any write, so an old modified source is retained.
  entries=[]
  for info in z.infolist():
   if info.is_dir() or not info.filename.startswith('C1_Play/app/'):continue
   rel=Path(info.filename.removeprefix('C1_Play/app/'))
   if any(part in rel.parts for part in ['reports','results','screenshots','runtime','__pycache__']):continue
   if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe archive path')
   dest=REPO/rel
   if dest.exists():
    with z.open(info) as f:expected=hashlib.file_digest(f,'sha256').hexdigest()
    if sha(dest)!=expected and (rel.suffix=='.py' or 'data' in rel.parts):raise ValueError(f'Existing file differs; preserve it and resolve manually: {rel}')
   else:entries.append((info,dest))
  for info,dest in entries:
   dest.parent.mkdir(parents=True,exist_ok=True)
   with z.open(info) as src,open(dest,'wb') as dst:
    while b:=src.read(1048576):dst.write(b)
   writes+=1
 print(f'Baseline SHA/CRC verified; restored {writes} missing files. Old files retained.')
if __name__=='__main__':restore()
