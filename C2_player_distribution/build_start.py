import json,hashlib,zipfile,re
from pathlib import Path
REPO=Path(__file__).resolve().parent.parent;HERE=Path(__file__).resolve().parent;OUT=REPO/'artifacts'
r=json.loads((OUT/'C2_PLAYER_DOWNLOAD.json').read_text())
s=(HERE/'prepare_safe_start.ps1').read_text()
s=re.sub(r"\$ExpectedArchive = '[^']+'", "$ExpectedArchive = '"+r['sha256']+"'",s)
s=re.sub(r"\$ExpectedManifest = '[^']+'", "$ExpectedManifest = '"+r['manifest_sha256']+"'",s)
s=re.sub(r"\$DownloadUrl = '[^']+'", "$DownloadUrl = 'https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C2_PLAY_WINDOWS_X64.zip'",s)
(HERE/'prepare_safe_start.ps1').write_text(s)
old=(HERE/'START_C2.cmd').read_text();header=old.split('# C2_SAFE_POWERSHELL\n',1)[0]+'# C2_SAFE_POWERSHELL\n'
cmd=(header+s).replace('\r\n','\n').replace('\n','\r\n').encode('utf8');(HERE/'START_C2.cmd').write_bytes(cmd)
p=OUT/'C2_START.zip'
with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('START_C2.cmd',cmd);z.writestr('はじめに.txt',('ZIPをすべて展開し、START_C2.cmdを開いてください。\r\n初回は本体約103MBを取得・検証して、C2の別フォルダへ自動展開します。旧版のフォルダ選択は不要です。\r\n普段の生活方針を1つ選ぶと自動進行します。重要な相談では止まり、選んだ結果を見て再開できます。\r\n終了前に記録を保存。次回もSTART_C2.cmdから起動してください。\r\n旧C1と旧セーブは残ります。エラーはファイルに記録して開きます。\r\n').encode('utf-8-sig'))
r={'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'base_game':r}
(OUT/'C2_START_DOWNLOAD.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
