"""Small patch reuses the user's working native runtime and statistical DB."""
import hashlib,json,zipfile
from pathlib import Path
from build import REPO,ROOT,HERE,OUT,BASE,BASE_SHA,eligible,sha
PS=r'''$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $env:C1_UPDATE_FILE
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.FolderBrowserDialog
$picker.Description = 'Select your working game folder containing PLAY.cmd, runtime and app.'
$candidate = Join-Path $env:LOCALAPPDATA 'RealOmamagoto\C01\game\C01_Play'
if (Test-Path $candidate) { $picker.SelectedPath = $candidate }
if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { Write-Host 'Cancelled. No game files were changed.'; exit 0 }
$target = $picker.SelectedPath
$manifest = Get-Content -LiteralPath (Join-Path $scriptRoot 'UPGRADE_MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($entry in $manifest.dependencies.PSObject.Properties) {
    $path = Join-Path $target $entry.Name
    if (-not (Test-Path -LiteralPath $path)) { throw "Required original file is missing: $($entry.Name). Please select the folder containing PLAY.cmd and runtime." }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Original file has a different version: $($entry.Name). Use the full C1 pack; no files were changed." }
}
foreach ($entry in $manifest.files.PSObject.Properties) {
    $path = Join-Path (Join-Path $scriptRoot 'payload') $entry.Name
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Upgrade checksum mismatch: $($entry.Name)" }
}
# Preserve earlier C1 updates, without overwriting the working C01 or its saves.
$backup = Join-Path $target ('c1_backups\' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
foreach ($entry in $manifest.files.PSObject.Properties) {
    $dest = Join-Path $target $entry.Name
    if (Test-Path -LiteralPath $dest) {
        $saved = Join-Path $backup $entry.Name
        New-Item -ItemType Directory -Force -Path (Split-Path $saved) | Out-Null
        Copy-Item -LiteralPath $dest -Destination $saved -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
    Copy-Item -LiteralPath (Join-Path (Join-Path $scriptRoot 'payload') $entry.Name) -Destination $dest -Force
}
Write-Host 'C1 is installed. Original C01 and its saves are unchanged.'
Start-Process -FilePath (Join-Path $target 'PLAY_C1.cmd') -WorkingDirectory $target
'''
CMD=r'''@echo off
setlocal
set "C1_UPDATE_FILE=%~f0"
set "C1_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "C1_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%C1_PS%" -NoLogo -NoProfile -STA -Command "$raw = [IO.File]::ReadAllText($env:C1_UPDATE_FILE); $marker = '# C1_' + 'POWERSHELL_BEGIN'; $body = $raw.Substring($raw.IndexOf($marker) + $marker.Length); try { & ([ScriptBlock]::Create($body)) } catch { Write-Host $_ -ForegroundColor Red; exit 1 }"
set "C1_UPDATE_RESULT=%ERRORLEVEL%"
if not "%C1_UPDATE_RESULT%"=="0" (
 echo.
 echo Update failed. Keep the error above. The full C1 pack is also available.
 pause
)
exit /b %C1_UPDATE_RESULT%
# C1_POWERSHELL_BEGIN
'''

def build():
 assert sha(BASE)==BASE_SHA
 files={}
 for p in ROOT.rglob('*'):
  if eligible(p) and 'reports' not in p.relative_to(ROOT).parts:files['app/JapanFamily/24_experience_c1/'+p.relative_to(ROOT).as_posix()]=p.read_bytes()
 files['launch_c1.py']=(HERE/'launch.py').read_text().replace("BASE/'saves'","BASE/'saves_c1'").replace("BASE/'logs'","BASE/'logs_c1'").encode()
 files['PLAY_C1.cmd']=(HERE/'PLAY.cmd').read_text().replace('launch.py','launch_c1.py').replace('logs\\server.log','logs_c1\\server.log').replace('\n','\r\n').encode()
 dependencies={}
 with zipfile.ZipFile(BASE) as z:
  baseline=json.loads(z.read('C01_Play/PLAYER_MANIFEST.json'))['files']
  for name,rec in baseline.items():
   if name.startswith('app/') and (name.endswith('.py') or name.endswith(('.gz','.sqlite'))):dependencies[name]=rec['sha256']
 # Full native A/B source + kernels + DB are compared before writing any new file.
 manifest={'version':'C1','base_sha256':BASE_SHA,'dependencies':dependencies,'files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}
 out=OUT/'C1_UPGRADE.zip'
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,data in files.items():z.writestr('C1_Update/payload/'+name,data)
  z.writestr('C1_Update/UPDATE_C1.cmd',(CMD+PS).replace('\n','\r\n').encode('utf8'))
  z.writestr('C1_Update/UPGRADE_MANIFEST.json',json.dumps(manifest,indent=2).encode())
  z.writestr('C1_Update/はじめに.txt',('ZIPを「すべて展開」し、UPDATE_C1.cmdを開いてください。\r\nフォルダ選択で、現在プレイできているゲームのPLAY.cmd・runtime・appがあるフォルダを選びます。\r\n検証後、新しいPLAY_C1.cmdが追加されます。次回からはそれを開いてください。\r\n旧版・旧保存は残ります。C1の保存はsaves_c1です。\r\n原本の版が違う場合は更新せず停止します。その場合はC1の全体ZIPを別フォルダに展開してください。\r\n').encode('utf-8-sig'))
 with zipfile.ZipFile(out) as z:assert z.testzip() is None
 print(json.dumps({'file':out.name,'bytes':out.stat().st_size,'sha256':sha(out),'verified_dependencies':len(dependencies),'payload_files':len(files)}))
if __name__=='__main__':build()
