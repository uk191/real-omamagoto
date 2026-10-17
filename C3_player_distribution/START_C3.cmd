@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
set "C3_SAFE_START=%~f0"
set "C3_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "C3_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
echo Preparing C-3. No folder selection is required. Please keep this window open.
"%C3_PS%" -NoLogo -NoProfile -Command "$raw=[IO.File]::ReadAllText($env:C3_SAFE_START,[Text.Encoding]::UTF8);$marker='#'+' C3_SAFE_POWERSHELL';$index=$raw.IndexOf($marker);if($index -lt 0){throw 'Missing start code'}; & ([ScriptBlock]::Create($raw.Substring($index+$marker.Length)))"
set "C3_START_RESULT=%ERRORLEVEL%"
if not "%C3_START_RESULT%"=="0" (
 echo.
 echo Startup failed. Keep this message and the error record open.
 pause
)
exit /b %C3_START_RESULT%
# C3_SAFE_POWERSHELL
param(
    [string]$ArchivePath = '',
    [string]$InstallBase = '',
    [switch]$PrepareOnly,
    [switch]$DefineOnly
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$ExpectedArchive = 'dc5f4ce7a48355588954b5de9f72aea6c850bc96330d52121b2e97d4a53d555f'
$ExpectedManifest = '6250ca8120ee3228eab891ab5fa967e9c82adc93932fb6a5bb04bc0f4de3ce82'
$DownloadUrl = 'https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C3_PLAY_WINDOWS_X64.zip'
$script:LogFile = ''

function Write-Step([string]$Message) {
    Write-Host $Message
    if ($script:LogFile) {
        [IO.File]::AppendAllText($script:LogFile, ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + $Message + [Environment]::NewLine), [Text.Encoding]::UTF8)
    }
}
function Same-Hash([string]$Path, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    return ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Expected)
}
function Valid-Game([string]$Root) {
    $manifestPath = Join-Path $Root 'PLAYER_MANIFEST.json'
    if (-not (Same-Hash $manifestPath $ExpectedManifest)) { return $false }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($entry in $manifest.files.PSObject.Properties) {
        if (-not (Same-Hash (Join-Path $Root $entry.Name) $entry.Value.sha256)) {
            Write-Step ('確認が必要なファイル：' + $entry.Name)
            return $false
        }
    }
    return $true
}
function Find-Archive {
    $folders = @($InstallBase)
    if ($env:C3_SAFE_START) { $folders += Split-Path -Parent $env:C3_SAFE_START }
    if ($env:USERPROFILE) { $folders += Join-Path $env:USERPROFILE 'Downloads' }
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        try {
            $shell = New-Object -ComObject Shell.Application
            $downloads = $shell.Namespace('shell:Downloads')
            if ($null -ne $downloads) { $folders += $downloads.Self.Path }
        } catch { }
    }
    foreach ($folder in ($folders | Select-Object -Unique)) {
        if (-not $folder -or -not (Test-Path -LiteralPath $folder -PathType Container)) { continue }
        foreach ($file in (Get-ChildItem -LiteralPath $folder -Filter 'C3_PLAY_WINDOWS_X64*.zip' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10)) {
            if (Same-Hash $file.FullName $ExpectedArchive) { return $file.FullName }
        }
    }
    return ''
}
function Run-Captured([string]$Program, [string]$Arguments, [string]$WorkingDirectory, [string]$Prefix, [switch]$EchoOutput) {
    $stdoutPath = $Prefix + '.stdout.txt'
    $stderrPath = $Prefix + '.stderr.txt'
    # Files, rather than redirected pipes, avoid deadlock on a long traceback.
    $childProcess = Start-Process -FilePath $Program -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -NoNewWindow -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    $processHandle = $childProcess.Handle
    $outputOffset = 0
    do {
        $ended = $childProcess.WaitForExit(250)
        if ($EchoOutput -and (Test-Path -LiteralPath $stdoutPath)) {
            $outputText = [IO.File]::ReadAllText($stdoutPath, [Text.Encoding]::UTF8)
            if ($outputText.Length -gt $outputOffset) {
                Write-Host -NoNewline $outputText.Substring($outputOffset)
                $outputOffset = $outputText.Length
            }
        }
    } while (-not $ended)
    $childProcess.WaitForExit()
    $exitNumber = $childProcess.ExitCode
    if ($null -eq $exitNumber) { throw '起動したプロセスの終了状態を取得できませんでした。' }
    if ($exitNumber -ne 0) {
        $hex = '0x{0:X8}' -f [int]$exitNumber
        throw ('実行に失敗しました。終了コード ' + $exitNumber + ' (' + $hex + ')' + [Environment]::NewLine + '詳しい内容：' + $stderrPath + [Environment]::NewLine + '出力記録：' + $stdoutPath)
    }
}
if ($DefineOnly) { return }

try {
    if (-not $InstallBase) {
        $localFolder = [Environment]::GetFolderPath('LocalApplicationData')
        if (-not $localFolder) { throw 'Windowsの保存先を取得できませんでした。' }
        $InstallBase = Join-Path $localFolder 'RealOmamagoto/C3'
    }
    $InstallBase = [IO.Path]::GetFullPath($InstallBase)
    New-Item -ItemType Directory -Path $InstallBase -Force | Out-Null
    $logDirectory = Join-Path $InstallBase 'startup_logs'
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    $runTag = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,8)
    $script:LogFile = Join-Path $logDirectory ($runTag + '.log')
    Write-Step '「まいにちの、あいだ。」C-3の起動準備'
    Write-Step '旧ゲームのフォルダ選択は不要です。旧版とセーブを残し、C-3を別の場所へ用意します。'
    $container = Join-Path $InstallBase 'game'
    $game = Join-Path $container 'C3_Play'
    if (-not (Valid-Game $game)) {
        if (-not $ArchivePath) { $ArchivePath = Find-Archive }
        if (-not $ArchivePath) {
            Write-Step '初回の本体約103MBを取得しています。画面を閉じずにお待ちください。'
            $pending = Join-Path $InstallBase ('download-' + [Guid]::NewGuid().ToString('N') + '.zip')
            [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $DownloadUrl -OutFile $pending -UseBasicParsing -TimeoutSec 180
            if (-not (Same-Hash $pending $ExpectedArchive)) { throw '取得したZIPのSHA256が一致しません。実行せず停止しました。' }
            $ArchivePath = Join-Path $InstallBase 'C3_PLAY_WINDOWS_X64-pinned.zip'
            Move-Item -LiteralPath $pending -Destination $ArchivePath -Force
        }
        if (-not (Same-Hash $ArchivePath $ExpectedArchive)) { throw 'ゲームZIPのSHA256が正式配布物と一致しません。実行せず停止しました。' }
        Write-Step 'ZIPを検証できました。展開後の全ファイルも確認します。'
        $stage = Join-Path $InstallBase ('prepare-' + [Guid]::NewGuid().ToString('N'))
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath, $stage)
        $prepared = Join-Path $stage 'C3_Play'
        if (-not (Valid-Game $prepared)) { throw '展開したゲームのファイルが一致しません。現在のゲームは置き換えていません。' }
        $oldSaves = Join-Path $game 'saves'
        if (Test-Path -LiteralPath $oldSaves -PathType Container) {
            Copy-Item -LiteralPath $oldSaves -Destination (Join-Path $prepared 'saves') -Recurse
        }
        if (Test-Path -LiteralPath $container) {
            $backup = Join-Path $InstallBase ('backup-' + $runTag)
            Move-Item -LiteralPath $container -Destination $backup
            Write-Step ('以前のC-3を保管しました：' + $backup)
        }
        Move-Item -LiteralPath $stage -Destination $container
    }
    Write-Step ('準備できました：' + $game)
    Write-Step ('起動記録：' + $script:LogFile)
    if ($PrepareOnly) { Write-Output ('C3_PREPARED=' + $game); exit 0 }
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'ゲームの起動はWindows用です。展開検査とは区別しています。' }
    $python = Join-Path $game 'runtime/python/tools/python.exe'
    $probeArguments = '-I -X utf8 -c "import sys,sqlite3,ssl,numpy,scipy; from scipy.special import ndtr; assert numpy.__version__==''2.3.5'' and scipy.__version__==''1.17.0''; assert float(ndtr(0))==0.5; print(sys.version); print(''runtime OK'')"'
    Write-Step '同梱Pythonと必要なライブラリを確認しています。'
    Run-Captured $python $probeArguments $game (Join-Path $logDirectory ($runTag + '-runtime'))
    Write-Step 'ブラウザを開きます。このウィンドウはプレイ中そのままにしてください。終了前にゲーム画面で保存してください。'
    Run-Captured $python ('-I -X utf8 "' + (Join-Path $game 'launch.py') + '"') $game (Join-Path $logDirectory ($runTag + '-game')) -EchoOutput
    Write-Step 'ゲームを終了しました。保存記録は次回も残ります。'
    exit 0
} catch {
    $failure = '起動準備で止まりました：' + $_.Exception.Message
    Write-Host ''; Write-Host $failure -ForegroundColor Red
    $details = $failure + [Environment]::NewLine + [Environment]::NewLine + ($_ | Format-List * -Force | Out-String) + [Environment]::NewLine + '旧ゲーム・旧セーブは削除していません。'
    $errorPath = ''
    try {
        if ($InstallBase -and (Test-Path -LiteralPath $InstallBase)) {
            $errorPath = Join-Path $InstallBase 'startup-error.txt'
            [IO.File]::WriteAllText($errorPath,$details,[Text.Encoding]::UTF8)
            Write-Host ('エラー内容を保存しました：' + $errorPath)
            if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
                Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/notepad.exe') -ArgumentList ('"' + $errorPath + '"')
            }
        }
    } catch { Write-Host 'エラー記録の保存に失敗しました。上の表示をそのまま残してください。' }
    Write-Host '開いたエラー記録の内容をチャットに送ってください。自動送信は行いません。'
    exit 1
}
