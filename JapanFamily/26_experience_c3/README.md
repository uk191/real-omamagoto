# まいにちの、あいだ。C-3

子どもとの経験を選び、当日の思いがけない反応と、その後につながる家族の記録を見守る体験版。

Windowsでは公開の `C3_START.zip` をすべて展開し、`START_C3.cmd` を開く。旧フォルダの選択やPythonの個別導入は不要。旧C1/C2を上書きしない。C3は新しい家庭から始める。旧セーブの変換は行わない。

開発環境は既存チェックアウトを使う。ユーザーの指定なしにworktreeを作らない。Python3.12、numpy2.3.5、scipy1.17.0。ブラウザ検査はPlaywright1.62.0と/usr/bin/chromium。新しい環境で旧実行資産が欠ける場合は `python C3_player_distribution/restore_environment.py`（SHA検証済み旧C1公開パックの不足ファイルだけを復元）。巨大研究DBは複製しない。

```sh
cd /workspace/real-omamagoto
python JapanFamily/26_experience_c3/server.py --port 8787
```

ループバック専用のサービス。クラウドのこのUIから外部向けプレビューURLは作れない。Windowsの起動パックがプレイヤー向け入口。

家庭を始めて方針を一つ選ぶと、約10秒で1か月が進む。重要な機会は自動停止。普段は見守ってよく、自分から考えたいときだけ「次の楽しみを考える」。遠出は翌月に持ち越す。終わる前に「記録を保存」。再起動後は開始画面の保存記録から再開できる。アルバムには実際の場面だけが残る。

再構築・検証：

```sh
python JapanFamily/26_experience_c3/scripts/verify.py
python JapanFamily/26_experience_c3/scripts/check_connections.py
python JapanFamily/26_experience_c3/scripts/browser.py
python JapanFamily/26_experience_c3/scripts/life_chains.py
python JapanFamily/26_experience_c3/scripts/report.py
python JapanFamily/26_experience_c3/scripts/report_chains.py
python C3_player_distribution/build.py
python C3_player_distribution/build_start.py
python C3_player_distribution/verify_start.py
python C3_player_distribution/build.py --reports-only
python C3_player_distribution/verify_release.py
```

`build.py` は公開C2本体 SHA 36f46f32a26cc001891e8c476b2eafe17ca04615f26ba4630c3fc91f8f82c967 をartifactsまたは/workspace/c3_baselineで必要とする。コード・資料パックには旧DBを重複収録せず、旧公開資産をハッシュで参照する。比較全履歴は別ZIP。

追加の場面はゲーム用シナリオ。A/Bの統計モデルや確率係数は変更せず、子どもの能力や愛着への長期効果は加算しない。詳しくは AUDIT_AND_DESIGN.md と BUILD_REPORT.md。
