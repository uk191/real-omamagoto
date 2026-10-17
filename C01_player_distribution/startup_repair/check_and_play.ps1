param(
    [string]$GameRoot = '',
    [switch]$SelfTest,
    [string]$ProbePython = ''
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$script:LogPath = ''
function Log([string]$Message) {
    Write-Host $Message
    if ($script:LogPath) { [IO.File]::AppendAllText($script:LogPath, $Message + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false))) }
}
function Status-Code([long]$Value) {
    $unsigned = $Value -band 4294967295L
    return ('0x{0:X8}' -f $unsigned)
}
function Run-Probe([string]$Executable, [string]$Code, [string]$Name, [string]$Directory, [switch]$Compact) {
    Log ('確認中：' + $Name)
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $Executable
    $info.Arguments = '-I -X utf8 -c "' + $Code.Replace('"','\"') + '"'
    $info.WorkingDirectory = $Directory
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
    $info.StandardErrorEncoding = New-Object Text.UTF8Encoding($false)
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $info
    try {
        [void]$process.Start()
        $outputTask = $process.StandardOutput.ReadToEndAsync()
        $errorTask = $process.StandardError.ReadToEndAsync()
        # Drain both pipes concurrently, including long NumPy import errors.
        if (-not $process.WaitForExit(60000)) {
            $process.Kill(); $process.WaitForExit()
            Log ('TIMEOUT: ' + $Name)
            return @{OK=$false; Stage=$Name; Exit='timeout'}
        }
        $output = $outputTask.Result
        $errorText = $errorTask.Result
        if ($Compact) { Log ('Captured stdout=' + $output.Length + ', stderr=' + $errorText.Length) }
        else {
            if ($output) { Log $output.TrimEnd() }
            if ($errorText) { Log $errorText.TrimEnd() }
        }
        $exitValue = $process.ExitCode
        $hex = Status-Code $exitValue
        Log ('終了コード：' + $exitValue + ' / ' + $hex)
        return @{OK=($exitValue -eq 0); Stage=$Name; Exit=$hex; OutputChars=$output.Length; ErrorChars=$errorText.Length}
    } catch {
        $native = $_.Exception
        if ($native.InnerException) { $native = $native.InnerException }
        Log ('起動そのものに失敗：' + $native.Message)
        if ($native -is [ComponentModel.Win32Exception]) { Log ('Win32Error=' + $native.NativeErrorCode) }
        return @{OK=$false; Stage=$Name; Exit=$native.Message}
    } finally { $process.Dispose() }
}
function Explain([string]$Code) {
    switch ($Code) {
        '0xC000007B' { Log 'Windowsが実行ファイルまたはDLLの形式を読み込めていません。これだけでは、どのDLLかは確定できません。' }
        '0xC0000135' { Log '起動に必要なDLLが見つからない状態です。ログのファイル検査と合わせて確認します。' }
        '0xC0000142' { Log 'DLLの初期化に失敗しています。失敗した確認段階をログに残しました。' }
        '0xC000001D' { Log 'CPU命令の実行に失敗しています。NumPy/SciPyの段階か、Python本体の段階かをログで確認します。' }
        '0xC0000022' { Log 'Windowsがアクセスを拒否しています。ファイル不足と断定せず、制限された対象を確認します。' }
        default { Log 'このコードだけでは原因を確定できません。表示とログを確認します。' }
    }
}
try {
    if ($SelfTest) {
        if (-not $ProbePython) { throw 'SelfTest requires ProbePython' }
        $positive = Run-Probe $ProbePython "import sys; print('probe output'); sys.stderr.write('probe stderr\n')" 'test success' ([IO.Path]::GetTempPath())
        $negative = Run-Probe $ProbePython 'import sys; sys.exit(37)' 'test failure' ([IO.Path]::GetTempPath())
        $large = Run-Probe $ProbePython "import sys; sys.stdout.write('x'*100000); sys.stderr.write('y'*100000)" 'large dual pipe output' ([IO.Path]::GetTempPath()) -Compact
        if (-not $large.OK -or $large.OutputChars -ne 100000 -or $large.ErrorChars -ne 100000) { throw 'Concurrent pipe capture failed' }
        if (-not $positive.OK -or $negative.OK -or $negative.Exit -ne '0x00000025' -or (Status-Code -1073741701) -ne '0xC000007B') { throw 'Process diagnostics self-test failed' }
        Write-Host 'PROCESS_PROBE_SELF_TEST_PASS'
        exit 0
    }
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'この起動補助はWindows用です。' }
    if (-not $GameRoot) {
        $local = [Environment]::GetFolderPath('LocalApplicationData')
        $GameRoot = Join-Path $local 'RealOmamagoto/C01/game/C01_Play'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $GameRoot 'PLAYER_MANIFEST.json') -PathType Leaf)) {
        $adjacent = ''
        if ($env:C01_DIAG_BOOTSTRAP) { $adjacent = Split-Path -Parent $env:C01_DIAG_BOOTSTRAP }
        if ($adjacent -and (Test-Path -LiteralPath (Join-Path $adjacent 'PLAYER_MANIFEST.json') -PathType Leaf)) {
            $GameRoot = $adjacent
        } else {
            Write-Host 'ゲームの場所を選択してください。PLAY.cmdがあるC01_Playフォルダです。'
            Add-Type -AssemblyName System.Windows.Forms
            $picker = New-Object Windows.Forms.FolderBrowserDialog
            $picker.Description = 'PLAY.cmdとapp、runtimeがあるC01_Playフォルダを選択してください。'
            $picker.ShowNewFolderButton = $false
            try {
                if ($picker.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { throw 'フォルダ選択をキャンセルしました。ファイルは変更していません。' }
                $GameRoot = $picker.SelectedPath
            } finally { $picker.Dispose() }
        }
    }
    $GameRoot = [IO.Path]::GetFullPath($GameRoot)
    $logDir = Join-Path $GameRoot 'logs'
    if (-not (Test-Path -LiteralPath $GameRoot -PathType Container)) { throw '自動展開したC-0.1が見つかりません。今回どのファイルを開いたか、チャットで教えてください。' }
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $script:LogPath = Join-Path $logDir ('startup-diagnostic-' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss') + '.txt')
    Log 'C-0.1 起動確認・起動補助'
    Log ('日時：' + [DateTime]::Now.ToString('s'))
    Log ('Windows：' + [Environment]::OSVersion.VersionString)
    Log ('64bit OS：' + [Environment]::Is64BitOperatingSystem + ' / 64bit 起動補助：' + [Environment]::Is64BitProcess)
    Log ('Processor architecture：' + $env:PROCESSOR_ARCHITECTURE + ' / ' + $env:PROCESSOR_ARCHITEW6432)
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        Log ('OS詳細：' + $os.Caption + ' / ' + $os.Version + ' / ' + $os.OSArchitecture)
        $cpu = Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1
        Log ('CPU：' + $cpu.Name + ' / Architecture=' + $cpu.Architecture)
    } catch { Log 'CPU詳細は取得できませんでした。' }
    if (-not [Environment]::Is64BitOperatingSystem) { throw '現在の配布物はx64用で、この32bit Windowsでは起動できません。' }
    # Trust only manifests from already released, checksum-verified packs.
    $known = @('c6949d4bc997acaf7eb984ea8ae5e27f5dec0226cd03d3b4c866495d26dc24b9',
        'b8201ce92fa2306197784f4109d78f7ec1c8598b9a577f83ee7882c0d6d0a876',
        '676dee89d20b642e226a9d823e0c3d34aca329fc942e8fa507f50690e505fd35')
    $manifestPath = Join-Path $GameRoot 'PLAYER_MANIFEST.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'PLAYER_MANIFEST.jsonがありません。全体が展開された場所か確認が必要です。' }
    $manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($known -notcontains $manifestHash) { throw '確認できる配布版とマニフェストが一致しません。ファイルは変更していません。' }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $count = 0
    foreach ($entry in $manifest.files.PSObject.Properties) {
        if ($entry.Name -match '^runtime/.*\.(exe|dll|pyd)$' -or $entry.Name -eq 'launch.py') {
            $file = Join-Path $GameRoot $entry.Name
            if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw ('不足：' + $entry.Name) }
            $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actual -ne $entry.Value.sha256) { throw ('内容が不一致：' + $entry.Name) }
            $count++
        }
    }
    Log ('同梱実行ファイル・DLL等のハッシュ確認：' + $count + 'ファイル一致')
    $python = Join-Path $GameRoot 'runtime/python/tools/python.exe'
    $probes = @(
        @('Python本体', 'import sys,struct; print(sys.version); print(struct.calcsize(''P'')*8)'),
        @('標準DLL・SQLite', 'import sqlite3,ssl; print(sqlite3.sqlite_version); print(ssl.OPENSSL_VERSION)'),
        @('NumPy・SciPy', 'import numpy,scipy; from scipy.special import ndtr; print(numpy.__version__,scipy.__version__,float(ndtr(0))); assert numpy.__version__==''2.3.5'' and scipy.__version__==''1.17.0'' and float(ndtr(0))==0.5')
    )
    foreach ($probe in $probes) {
        $result = Run-Probe $python $probe[1] $probe[0] $GameRoot
        if (-not $result.OK) { Explain $result.Exit; throw ('止まった段階：' + $result.Stage + ' / ' + $result.Exit) }
    }
    Log '確認を通過しました。ゲームを起動します。'
    $arguments = '-I -X utf8 "' + (Join-Path $GameRoot 'launch.py') + '"'
    $gameProcess = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $GameRoot -PassThru -Wait
    $gameProcess.WaitForExit()
    $gameProcess.Refresh()
    $exitValue = $gameProcess.ExitCode
    if ($null -eq $exitValue) { throw 'ゲーム終了コードを取得できませんでした。Windowsのエラー表示とlogs/server.logを確認します。' }
    Log ('ゲーム終了コード：' + $exitValue + ' / ' + (Status-Code $exitValue))
    if ($exitValue -ne 0) { Explain (Status-Code $exitValue); throw 'ゲームがエラーで終了しました。logs/server.logも残っています。' }
    Log 'ゲームを終了しました。保存済みの記録はそのままです。'
    exit 0
} catch {
    Log ('起動確認で止まりました：' + $_.Exception.Message)
    if ($script:LogPath) {
        Log ('確認ログ：' + $script:LogPath)
        Log 'ログをメモ帳で開きます。内容をチャットへ貼り付けてください。自動送信はしません。'
        try { Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/notepad.exe') -ArgumentList ('"' + $script:LogPath + '"') } catch { }
    }
    exit 1
}
