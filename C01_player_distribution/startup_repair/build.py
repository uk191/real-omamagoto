from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
header=r'''@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
set "C01_DIAG_BOOTSTRAP=%~f0"
set "C01_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "C01_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
echo Checking C-0.1 startup. Please keep this window open.
"%C01_PS%" -NoLogo -NoProfile -Command "$t=[IO.File]::ReadAllText($env:C01_DIAG_BOOTSTRAP,[Text.Encoding]::UTF8);$m='#'+' C01_DIAGNOSTIC_BODY';$i=$t.IndexOf($m);if($i -lt 0){throw 'Missing diagnostic code'};& ([scriptblock]::Create($t.Substring($i+$m.Length)))"
set "C01_DIAG_RESULT=%ERRORLEVEL%"
echo.
echo PowerShell exit status: %C01_DIAG_RESULT%
echo Press any key to close this window after reading the result.
pause >nul
exit /b %C01_DIAG_RESULT%
# C01_DIAGNOSTIC_BODY
'''
p=ROOT/'CHECK_AND_PLAY.cmd';p.write_bytes((header+(ROOT/'check_and_play.ps1').read_text()).replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
out=REPO/'artifacts/C01_CHECK_AND_PLAY.zip'
readme='''C-0.1 起動確認\n\nCHECK_AND_PLAY.cmdを開いてください。\n通常の自動展開先にあるゲームを確認し、起動できればそのまま開きます。\n本体の再取得、再インストール、セーブの変更はしません。\n\n失敗した場合は、Python本体・標準DLL・NumPy/SciPyのどこで止まったか、\n終了コードとともにログへ残し、メモ帳で開きます。\nログ内容は自動送信しません。チャットへ貼り付けてください。\nWindowsのエラーダイアログが出た場合はコードを控え、OKで閉じてください。\n\nこの補助だけでWindows側の原因が解消するとは断定していません。\nゲームロジック、統計モデル、Windowsの設定は変更しません。\n'''
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:z.write(p,p.name);z.writestr('READ_ME.txt',b'\xef\xbb\xbf'+readme.encode('utf-8'))
with zipfile.ZipFile(out) as z:assert z.testzip() is None
record={'filename':out.name,'bytes':out.stat().st_size,'sha256':hashlib.file_digest(out.open('rb'),'sha256').hexdigest()}
(REPO/'artifacts/C01_CHECK_AND_PLAY.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
