# C-3.1｜四つの相談と、その後

既存C3/A/Bを変更せず、強制選択を四つの相談構造へ置き換えた体験検証版。

Windows：[起動パック](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C31_START.zip) をすべて展開し、`START_C31.cmd` を開く。初回は約103MBの本体を検証して別フォルダへ用意する。Pythonの別途インストール・旧フォルダ選択は不要。旧版と旧セーブは残る。

年齢・学歴・地域を指定して開始し、生活方針を一つ選ぶ。通常は約10秒で一か月進む。重要な四択で止まり、結果を見て「暮らしに戻る」で再開する。Bは4か月、Aは8か月、Cは12か月、Dは16か月頃。約二か月後に実際の結果を踏まえた相談が出る。時間・資金によって延期する場合がある。面白さの評価を早く行う場合は速度を4倍にできる。通常の画面だけで24か月と保存・再開まで操作できる。

ローカル開発：Python3.12、`numpy==2.3.5 scipy==1.17.0` を用意し、`python C31_player_distribution/restore_environment.py` でハッシュ固定の不足旧資産だけを復元する。その後 `python JapanFamily/27_experience_c31/server.py --port 8788`。ローカルブラウザで `http://127.0.0.1:8788` を開く。このURLは起動した本人のPC用で、公開プレビューではない。

詳細は `EVENT_DESIGN.md`、`SIXTEEN_BRANCHES.md`、`INITIAL_ASSETS_AUDIT.md`、`BUILD_REPORT.md`、`MODEL_TO_DISPLAY.md`。比較全データは別の `C31_COMPARISON_DATA.zip` に保存する。

## 再検証

```sh
python JapanFamily/27_experience_c31/scripts/regression.py baseline
python JapanFamily/27_experience_c31/scripts/regression.py updated
python JapanFamily/27_experience_c31/scripts/audit_assets.py
python JapanFamily/27_experience_c31/scripts/verify.py
python JapanFamily/27_experience_c31/scripts/individuality.py
python -m unittest discover -s JapanFamily/22_experience_c0/tests -v
```

8787で旧C3、8788で新C31のサービスをそれぞれ起動してから `scripts/browser.py --baseline` と `scripts/browser.py` を実行する。Playwright1.62.0と `/usr/bin/chromium` を使う。自動検査の保存先は普段のセーブと分ける。

旧C3の保存は、元の `.json.gz` と同名 `.meta.json` を新しい `saves` フォルダへ**コピー**し再起動すると読める。既往の選択はそのまま保ち、本版の相談は読込以降の月齢から始まる。新旧の出来事が混在し得るため、四つの相談の評価には新規家庭を推奨する。旧ファイルの移動・上書きは不要。

Windows起動先は `%LOCALAPPDATA%/RealOmamagoto/C31/game/C31_Play`。セーブはその下の `saves`。終了前に画面の「記録を保存」を押す。エラー時は `%LOCALAPPDATA%/RealOmamagoto/C31/startup-error.txt` または `logs/server.log` を確認する。本版はWindows実機では未検証。
