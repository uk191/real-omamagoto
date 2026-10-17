# 「まいにちの、あいだ。」C-0.1 P0 再設計版

実プレイの評価を受け、自動進行・一画面・生活ログ・状況別の選択を実装した版です。

**[起動用ZIPをダウンロード](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C01_P0B_START_HELPER.zip)**（約4KB）。中の **START_C01.cmd** を開くと、本体約103MBを取得・検証・展開してブラウザを開きます。Pythonを入れる必要はありません。初回取得後はネット接続なしで遊べます。

1. 家庭条件を設定して「この家族の暮らしを始める」。
2. 通常は10秒で1か月。0.5/1/2/4倍速、一時停止、手動月送りができます。
3. 相談で止まったら選択し、「この方針で自動進行を再開」。
4. 終了前に右上の「保存」。次回は「保存した記録から」。

旧C-0とは別フォルダへ入ります。旧版の保存記録は旧版で開いてください。Windows 10/11 x64用。OSから発行元確認や組織ポリシーによる制限が出る場合、セキュリティ設定の無効化は必要ありません。起動で止まる場合は表示を確認してください。

通常プレイにタブ切替は不要。中央が自動更新ログ、左が家族・勤務時間・気づいた成長、右が相談と入出金・残高です。児童手当、保育、復職・時短、求職、身近な人の支援、生活費、支払いに使う資産を状況に応じて選べます。希望の受付と実現は別で、実際のA/Bエンジンが結果を計算します。

[画面例](https://github.com/uk191/real-omamagoto/blob/c0-player-download/JapanFamily/23_experience_c01/reports/screenshots/month_12.png) ／ [実装報告](https://github.com/uk191/real-omamagoto/blob/c0-player-download/JapanFamily/23_experience_c01/BUILD_REPORT.md) ／ [実行手順](https://github.com/uk191/real-omamagoto/blob/c0-player-download/JapanFamily/23_experience_c01/README.md)

## その他の取得物

- [本体ZIP・約103MB](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C01_P0B_PLAY_WINDOWS_X64.zip)：全体を展開してPLAY.cmdから起動する方法。
- [コード・資料・画面・履歴・約1.65MB](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C01_P0B_CODE_AND_REPORTS.zip)
- [保存後の独立検証](https://github.com/uk191/real-omamagoto/blob/c0-player-download/player-download/C01_RELEASE_VERIFICATION.json) ／ [起動補助の検証](https://github.com/uk191/real-omamagoto/blob/c0-player-download/player-download/C01_START_HELPER_VERIFICATION.json) ／ [SHA256](https://github.com/uk191/real-omamagoto/blob/c0-player-download/player-download/C01_SHA256SUMS.txt)

A/Bの科学モデル・旧C-0を保持しています。開発者のブラウザ検査で設定、実時間進行、選択、保存・再開、24か月を通過。10家庭の実エンジン進行と3家庭の方針比較、旧13テストも確認しました。Windowsネイティブ実機は未検査です。これらは人間による面白さ評価や外部科学的妥当性の証明ではありません。

親の呼び名・時刻・居間・小物などは演出です。行動は親の観察情報、家計は確定した取引に追跡できます。気質・行動・就業・保育・家計には未校正・未識別部分があります。能力や愛着へ架空の加点はしません。健康・離乳食・投資・転居などの新しいモデルは今回追加していません。

[旧C-0の本体](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C0_PLAY_WINDOWS_X64.zip)と[旧起動補助](https://github.com/uk191/real-omamagoto/raw/refs/heads/c0-player-download/player-download/C0_START_HELPER.zip)は保管しています。
