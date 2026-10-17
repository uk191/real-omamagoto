"""Build the pinned one-file C01 Windows automatic preparer."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
record=json.loads((REPO/'artifacts/C01_PLAYER_DOWNLOAD.json').read_text())
body=(REPO/'C0_player_distribution/prepare_and_start.ps1').read_text(encoding='utf-8')
body=body.replace('216e260e125d00c7c4f5358d5d70551eec4a211cc470b0678511ff19adcf8649',record['sha256'])
body=body.replace('e82a1b5162e313e2eb2eaa16c7a2f23ad5858471974fa36ff667f2aa71a7ebeb',record['manifest_sha256'])
body=body.replace('C0_PLAY_WINDOWS_X64','C01_PLAY_WINDOWS_X64').replace('C0_Play','C01_Play').replace('C0_BOOTSTRAP','C01_BOOTSTRAP').replace('RealOmamagoto/C0','RealOmamagoto/C01').replace('C-0の起動準備','C-0.1の起動準備').replace('C0_PREPARED=','C01_PREPARED=')
body=body.replace("'app/JapanFamily/22_experience_c0/server.py',","'app/JapanFamily/23_experience_c01/server.py',\n        'app/JapanFamily/23_experience_c01/c01/experience.py',\n        'app/JapanFamily/23_experience_c01/web/app.js',")
body=body.replace('ゲームの計算モデルや設定は変更しません。','旧C-0を保管したまま、新しい体験版を別フォルダへ用意します。')
body=body.replace('初回だけ約105MB','初回だけ約103MB')
(ROOT/'prepare_and_start.ps1').write_text(body,encoding='utf-8')
header='''@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
set "C01_BOOTSTRAP=%~f0"
echo Preparing C-0.1... Please keep this window open.
powershell.exe -NoLogo -NoProfile -Command "$t=[IO.File]::ReadAllText($env:C01_BOOTSTRAP,[Text.Encoding]::UTF8);$m='#'+' C01_POWERSHELL';$i=$t.IndexOf($m);if($i -lt 0){throw 'Missing setup code'};& ([scriptblock]::Create($t.Substring($i+$m.Length)))"
set "C01_RESULT=%ERRORLEVEL%"
if not "%C01_RESULT%"=="0" pause
exit /b %C01_RESULT%
# C01_POWERSHELL
'''
cmd=ROOT/'START_C01.cmd';cmd.write_bytes((header+body).replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
readme='''「まいにちの、あいだ。」C-0.1 P0 起動用\n\nSTART_C01.cmdをダブルクリックしてください。\nこの小さなZIPの中から直接開けます。\n初回は本体約103MBを取得し、SHA256と展開後の全ファイルを確認します。\nPythonのインストールや実行ポリシーの設定変更は不要です。\n\n開始すると10秒で1か月。相談で止まり、選択後に再開します。\n終了前に右上「保存」。次回は「保存した記録から」。\n\n保存先はローカルアプリデータ内のRealOmamagoto/C01/game/C01_Playです。\n旧C-0のインストール・セーブは上書きしません。旧記録は旧版で開いてください。\nWindows 10/11 x64用。ゲームの本格的な実ユーザー評価は、これから行います。\n'''
archive=REPO/'artifacts/C01_START_HELPER.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 z.write(cmd,'START_C01.cmd');z.writestr('READ_ME.txt',b'\xef\xbb\xbf'+readme.replace('\n','\r\n').encode('utf-8'))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
h=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest();r={'filename':archive.name,'bytes':archive.stat().st_size,'sha256':h,'cmd_sha256':hashlib.file_digest(cmd.open('rb'),'sha256').hexdigest(),'base_game':record}
(REPO/'artifacts/C01_START_HELPER.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
