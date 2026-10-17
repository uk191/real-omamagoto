# まいにちの、あいだ。 C-2

普段は6つの方針から一つだけ選び、暮らしを自動で見守る体験版。重要な相談では時間が止まり、一つの問題と2〜3個の具体的な選択に集中します。選択後に実行結果を見て、自動進行へ戻ります。

Windowsは `C2_START.zip` をすべて展開して `START_C2.cmd` を開いてください。旧版のフォルダ選択は不要です。初回はSHA256で固定した本体を取得し、別のC2フォルダへ自動展開します。旧版と旧保存は残します。C2の保存はC2で再開してください。Windows実機の今回の検査と、Linux上のブラウザ・PowerShell検査は区別します。

1. 父親または母親を選び、家族を生成。
2. 続けたい生活方針を一つ選ぶ。これで自動進行が始まる。
3. 普段は新しい記録だけが届く。変化がない月のログを埋めるために事件を作らない。
4. 大きな相談が出たら選び、結果を確認して「暮らしに戻る」。
5. 終了前に保存。次回は保存した暮らしから再開。

## 開発・再現

Python3.12、numpy2.3.5、scipy1.17.0。既存A/B/C1を保ち、`25_experience_c2`だけを新しい層として追加した。旧研究の巨大DBを複製せず、固定されたC1実行パックから変更していないA/B核と地域SQLite射影を参照する。

```sh
python JapanFamily/25_experience_c2/server.py --port 8786
python JapanFamily/25_experience_c2/scripts/verify.py
python JapanFamily/25_experience_c2/scripts/browser.py
python -m unittest discover -s JapanFamily/22_experience_c0/tests -v
```

ブラウザ検査は起動済み8786サービス、Playwright1.62.0と既存 `/usr/bin/chromium` を使用。クラウドのlocalhostは外部プレイURLではない。Windows配布の起動補助は、C1でユーザーが起動できた方式を引き継ぐ。

`AUDIT_AND_FINANCE.md` は家計と旧接続の監査、`VARIABLE_TO_EXPERIENCE.md` は使った変数と未接続変数、`BUILD_REPORT.md` は結果・判定・未完成事項。全比較・分岐データは別の `C2_COMPARISON_DATA.zip`。軽量パックにはソース・説明・画面・検証要約を含める。

元の5GB超の全研究原本そのものは今回のクラウドにはなく、保存状態を今回の検査済みとしない。手元の旧実装・統計核は変更せず、過去の公開アーカイブも保持する。科学的な外部妥当性、現実の問題発生率、人間が感じる面白さは、内部テストの成功と別に評価する。
