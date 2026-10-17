# 再構築・保全・配布

通常のプレイヤーは `C01_P0_START_HELPER.zip` だけを取得します。本書は開発再開用です。

## 原本

旧A/B・C-0原本は元のワークスペースと旧リリースZIPに残しています。巨大な正式統合研究DB・原資料を、この体験版の版ごとに複製する構造にはしていません。プレイ用には、以前に同値性を検査した約327MBの読み取り専用地域DB射影と元の統計核を利用します。

- 旧プレイ用 `C0_PLAY_WINDOWS_X64.zip`：SHA256 `216e260e125d00c7c4f5358d5d70551eec4a211cc470b0678511ff19adcf8649`
- 旧コード原本 `C0_CODE_AND_REPORTS.zip` と旧 `22_experience_c0` を保持。
- 公開原本：https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C0_PLAY_WINDOWS_X64.zip
- 今回の実装差分：`JapanFamily/23_experience_c01` と `C01_player_distribution`。
- 読み取り専用DB SHA256：`2b15f9c621163c40270b32c224c104f7d01a74e06362c325e7be3b0aad4b9ba5`。

## 開発再開

既存ワークスペースでは、READMEの `scripts/start.sh` で再開します。研究原本やDBを再構築・上書きしないでください。

軽量パックだけを取得した場合は、同じルートへ元のプレイ用ZIPを `artifacts/C0_PLAY_WINDOWS_X64.zip` として配置します。C01パックのコード・資料は、同じ相対配置で展開してください。WindowsのPython・numpy・scipyは、検証済み旧プレイ用ZIP内にあり、ゲームを遊ぶためにpipを実行する必要はありません。

Python 3.12の開発環境で：

```sh
python C01_player_distribution/build_player_pack.py
python C01_player_distribution/build_start_helper.py
python C01_player_distribution/verify_release.py
```

本体ビルドは旧ZIPのSHA256とCRCを検査し、A/Bと同梱Pythonをバイト単位で保持したまま新しい体験層を追加します。旧プレイ履歴・スクリーンショットの再重複を避け、100MiB未満に収めています。`build_start_helper.py` の旧起動補助ソース依存も軽量パックへ同梱しています。

新しい本体ZIPを作り直した場合は、その新しいハッシュを参照する起動補助も必ず作り直してください。既存ハッシュ値を検査通過のためだけに手動で変更しないでください。

`verify_release.py` は作業環境向けの別展開先 `/workspace/c01_release_inspection` を使い、全ファイル・SQLite・実際の起動・24か月・保存復元を検査します。Windowsのネイティブ実機試験とは別です。起動補助のPowerShell検査もLinux PowerShellであり、Windows実機を実行したことにはしません。

## 成果物の対応

- `C01_P0_PLAY_WINDOWS_X64.zip`：実行に必要なコード・地域DB射影・Python同梱。約103MB。
- `C01_P0_START_HELPER.zip`：自動取得・検証・展開・起動の1ファイル。約4KB。
- `C01_P0_CODE_AND_REPORTS.zip`：ソース、実装報告、画面、10家庭の観測履歴と比較結果。巨大DBとPythonは含めません。
- `C01_RELEASE_VERIFICATION.json` / `C01_START_HELPER_VERIFICATION.json`：保存済み配布物・起動補助の独立検査。
- `C01_SHA256SUMS.txt`：別ファイルとして配布物を照合。

旧C-0と新C-0.1は別インストール先です。旧保存を誤った版で読み込んで無理に変換しません。新しい版の保存は相談・保留・ログ・再生速度・タイマー残時間を含みます。
