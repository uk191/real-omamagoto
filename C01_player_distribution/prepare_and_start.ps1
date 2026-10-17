param(
    [string]$ArchivePath = '',
    [string]$InstallBase = '',
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$ExpectedArchive = 'f09d9db8fde137ba687dccb4a68f89242d7d46a1806a85839b17813790fbce7d'
$ExpectedManifest = 'b8201ce92fa2306197784f4109d78f7ec1c8598b9a577f83ee7882c0d6d0a876'
$DownloadUrl = 'https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C01_P0_PLAY_WINDOWS_X64.zip'

function Same-Hash([string]$Path, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    return ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Expected)
}

function Valid-Game([string]$Root, [switch]$Full) {
    $manifestPath = Join-Path $Root 'PLAYER_MANIFEST.json'
    if (-not (Same-Hash $manifestPath $ExpectedManifest)) { return $false }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $critical = @('PLAY.cmd','launch.py','runtime/python/tools/python.exe',
        'app/JapanFamily/23_experience_c01/server.py',
        'app/JapanFamily/23_experience_c01/c01/experience.py',
        'app/JapanFamily/23_experience_c01/web/app.js',
        'app/JapanFamily/22_experience_c0/data/runtime_region.sqlite')
    foreach ($entry in $manifest.files.PSObject.Properties) {
        $path = Join-Path $Root $entry.Name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Write-Host ('不足しているファイル：' + $path)
            return $false
        }
        if ($Full -or ($critical -contains $entry.Name)) {
            if (-not (Same-Hash $path $entry.Value.sha256)) {
                Write-Host ('内容が一致しないファイル：' + $path)
                return $false
            }
        }
    }
    return $true
}

function Find-Archive {
    $folders = @()
    if ($env:C01_BOOTSTRAP) { $folders += Split-Path -Parent $env:C01_BOOTSTRAP }
    if ($env:USERPROFILE) { $folders += Join-Path $env:USERPROFILE 'Downloads' }
    if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
        # Includes Downloads folders moved by the user or redirected by Windows.
        try {
            $shell = New-Object -ComObject Shell.Application
            $downloads = $shell.Namespace('shell:Downloads')
            if ($null -ne $downloads) { $folders += $downloads.Self.Path }
        } catch { }
    }
    $folders += $InstallBase
    foreach ($folder in ($folders | Select-Object -Unique)) {
        if (-not $folder -or -not (Test-Path -LiteralPath $folder -PathType Container)) { continue }
        $files = Get-ChildItem -LiteralPath $folder -Filter 'C01_P0_PLAY_WINDOWS_X64*.zip' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
        foreach ($file in $files) {
            if (Same-Hash $file.FullName $ExpectedArchive) { return $file.FullName }
        }
    }
    return ''
}

try {
    if (-not $InstallBase) {
        $local = [Environment]::GetFolderPath('LocalApplicationData')
        if (-not $local) { throw 'Windowsの保存先を取得できませんでした。' }
        $InstallBase = Join-Path $local 'RealOmamagoto/C01'
    }
    $InstallBase = [IO.Path]::GetFullPath($InstallBase)
    New-Item -ItemType Directory -Path $InstallBase -Force | Out-Null
    $gameContainer = Join-Path $InstallBase 'game'
    $game = Join-Path $gameContainer 'C01_Play'
    Write-Host ''
    Write-Host '「まいにちの、あいだ。」C-0.1の起動準備' -ForegroundColor Green
    Write-Host '旧C-0を保管したまま、新しい体験版を別フォルダへ用意します。'

    if (-not (Valid-Game $game)) {
        if (-not $ArchivePath) { $ArchivePath = Find-Archive }
        if (-not $ArchivePath) {
            Write-Host 'ゲームZIPを取得しています。初回だけ約103MBをダウンロードします。'
            $ArchivePath = Join-Path $InstallBase 'C01_P0_PLAY_WINDOWS_X64.zip'
            $pending = Join-Path $InstallBase ('download-' + [Guid]::NewGuid().ToString('N') + '.zip')
            [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $DownloadUrl -OutFile $pending -UseBasicParsing
            if (-not (Same-Hash $pending $ExpectedArchive)) { throw '取得したZIPのハッシュが一致しません。ゲームは実行しませんでした。' }
            Move-Item -LiteralPath $pending -Destination $ArchivePath -Force
        }
        if (-not (Same-Hash $ArchivePath $ExpectedArchive)) { throw '選択されたゲームZIPが正式な配布物と一致しません。' }
        Write-Host ('使うZIP：' + $ArchivePath)
        Write-Host '必要な一式を自動で展開しています。画面を閉じずにお待ちください。'
        $stage = Join-Path $InstallBase ('prepare-' + [Guid]::NewGuid().ToString('N'))
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [IO.Compression.ZipFile]::ExtractToDirectory($ArchivePath, $stage)
        $preparedGame = Join-Path $stage 'C01_Play'
        Write-Host 'Python本体とゲームファイルを確認しています。'
        if (-not (Valid-Game $preparedGame -Full)) { throw '展開したファイルが不足しているか、ハッシュが一致しません。' }

        # Preserve all old data, and carry local save slots across a repair.
        $oldSaves = Join-Path $game 'saves'
        if (Test-Path -LiteralPath $oldSaves -PathType Container) {
            Copy-Item -LiteralPath $oldSaves -Destination (Join-Path $preparedGame 'saves') -Recurse
        }
        if (Test-Path -LiteralPath $gameContainer) {
            $backup = Join-Path $InstallBase ('backup-' + [Guid]::NewGuid().ToString('N'))
            Move-Item -LiteralPath $gameContainer -Destination $backup
            Write-Host ('以前のフォルダは保管しました：' + $backup)
        }
        Move-Item -LiteralPath $stage -Destination $gameContainer
    }

    Write-Host ('準備できました：' + $game)
    Write-Host '終了する前に、ゲーム画面で保存してください。'
    if ($PrepareOnly) {
        Write-Output ('C01_PREPARED=' + $game)
    } else {
        if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'この起動補助はWindows用です。' }
        # Use absolute paths; do not depend on the old PLAY.cmd working folder.
        $python = Join-Path $game 'runtime/python/tools/python.exe'
        $arguments = '-I -X utf8 "' + (Join-Path $game 'launch.py') + '"'
        Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $game
    }
    exit 0
} catch {
    Write-Host ''
    Write-Host ('起動準備で止まりました：' + $_.Exception.Message) -ForegroundColor Red
    Write-Host '表示された内容を、そのままチャットに送ってください。'
    exit 1
}
