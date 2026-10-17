# C-0 Windows player download

## PLAYで「Bundled Python is missing」と出た場合

[起動補助ZIPをダウンロード（約4KB）](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C0_START_HELPER.zip)

小さいZIPを開き、中の **START_C0.cmd** を実行してください。この起動補助は単独で動くため、ZIPの中から開いても構いません。

既にダウンロードした `C0_PLAY_WINDOWS_X64.zip` がDownloads等にあれば再利用します。見つからない場合は、同じ正式ZIPを自動で取得します。SHA256を確認して一式を短い専用フォルダへ自動展開し、Pythonの場所を検査してから起動します。PythonやPowerShellの設定変更は不要です。

終了前にゲーム内で保存してください。次回もSTART_C0.cmdから起動できます。自動展開先に保存したデータは修復時にも引き継ぎ、旧フォルダも保管します。手動で展開した別の場所のsavesフォルダは自動移動しません。

起動補助の展開・欠落復旧・セーブ保全・単独cmd内のPowerShell処理はLinux上のPowerShell 7.4.7で検査しました。Windows実機の実行は未検証です。既存ゲームと統計モデルは変更していません。

## Original full package

[Full Windows x64 package](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C0_PLAY_WINDOWS_X64.zip)

Windows 10/11 x64 only. Python and required libraries are bundled.

Full ZIP SHA256: `216e260e125d00c7c4f5358d5d70551eec4a211cc470b0678511ff19adcf8649`
