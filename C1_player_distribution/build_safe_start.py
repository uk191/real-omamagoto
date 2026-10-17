"""Single-file bootstrap, no old-folder chooser, pinned previously verified C1."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
header=r'''@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
set "C1_SAFE_START=%~f0"
set "C1_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "C1_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
echo Preparing C-1. No folder selection is required. Please keep this window open.
"%C1_PS%" -NoLogo -NoProfile -Command "$raw=[IO.File]::ReadAllText($env:C1_SAFE_START,[Text.Encoding]::UTF8);$marker='#'+' C1_SAFE_POWERSHELL';$index=$raw.IndexOf($marker);if($index -lt 0){throw 'Missing start code'}; & ([ScriptBlock]::Create($raw.Substring($index+$marker.Length)))"
set "C1_START_RESULT=%ERRORLEVEL%"
if not "%C1_START_RESULT%"=="0" (
 echo.
 echo Startup failed. Keep this message and the error record open.
 pause
)
exit /b %C1_START_RESULT%
# C1_SAFE_POWERSHELL
'''
body=(ROOT/'prepare_safe_start.ps1').read_text(encoding='utf8')
cmd=(header+body).replace('\r\n','\n').replace('\n','\r\n').encode('utf8')
(ROOT/'START_C1.cmd').write_bytes(cmd)
readme='''まいにちの、あいだ。 C-1 起動用\r\n\r\nZIPを「すべて展開」して、START_C1.cmdをダブルクリックしてください。\r\n旧ゲームのフォルダを選ぶ必要はありません。\r\n初回だけ本体約103MBを取得し、SHA256と展開後の全ファイルを検証します。\r\n既に正式なC1_PLAY_WINDOWS_X64.zipがダウンロードフォルダ等にあれば再利用します。\r\n\r\nゲームと保存先：ローカルアプリデータ内のRealOmamagoto/C1/game/C1_Play\r\n終了前にゲーム画面の「記録を保存」。次回もSTART_C1.cmdから開きます。\r\n旧ゲームと旧セーブはそのまま残します。旧C-0.1の記録は旧版で開いてください。\r\n\r\nエラーが出た場合は内容をファイルに保存し、メモ帳で開きます。その内容をチャットへ送ってください。\r\n自動送信しません。Windowsの実行ポリシー変更や管理者起動は不要です。\r\nWindows x64用。Windows実機での今回の起動確認は未実施です。\r\n'''
archive=REPO/'artifacts/C1_SAFE_START.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('START_C1.cmd',cmd);z.writestr('はじめに.txt',readme.encode('utf-8-sig'))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
r={'file':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'cmd_sha256':hashlib.sha256(cmd).hexdigest(),'game_sha256':'4f65d84579be58767f51b4b67cd71c2364273225882961602671968a886761b5','no_folder_chooser':True,'simulation_code_changed':False}
(REPO/'artifacts/C1_SAFE_START_DOWNLOAD.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
