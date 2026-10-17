# まいにちの、あいだ。 C-1

父親として予定を立て、子どもとの活動を実行し、家族と相談して数か月の結果を確かめる体験版。24か月進行を保持した独立した表示・意思決定層です。A/Bの既存ファイルは変更していません。

## 遊び方

Windowsで現在C-0.1が動いている場合は `C1_UPGRADE.zip` をすべて展開し、`UPDATE_C1.cmd` を開きます。フォルダ選択では **現在のPLAY.cmd・runtime・appがあるフォルダ** を選んでください。原本のハッシュを確認した後、`PLAY_C1.cmd` が追加され、C-1を起動します。旧PLAY.cmdと旧セーブは保持します。C-1の保存先は `saves_c1` です。版が合わない場合は何も書き込まず停止します。

単独の配布物は `C1_PLAY_WINDOWS_X64.zip`。別フォルダへすべて展開し、`C1_Play/PLAY.cmd` を開きます。保存先はこのフォルダの `saves`。過去版のセーブは過去版で引き続き使い、C-1への自動変換は行いません。

1. 名前・地域などを指定し、生成された人物・世帯口座を確認する。
2. 抱っこ・絵本・公園等の予定を入れ、「暮らしを進める」。標準約10秒/月で3段階に進む。
3. 「来月以降も毎月1回」にすると次月の予定が残る。実行前に取り消せる。
4. 妻との分担や旅行は合意が必要。仕事や保育は希望を出してからAモデルの結果を待つ。
5. 終了前に「記録を保存」。次回の開始画面から再開する。

費用が足りなければ実行せず理由を残します。定期性預貯金から支払い口座への振替も可能ですが、銀行の解約条件・手数料は未実装のシナリオです。追加活動で子どもの能力や愛着が上がることはありません。

## 開発環境

既存チェックアウトを使用し、旧資産を削除・上書きする再構築は避けてください。Python 3.12、numpy 2.3.5、scipy 1.17.0。巨大な研究DBは不要で、旧配布の損失のない地域SQL射影 `22_experience_c0/data/runtime_region.sqlite` を使用できます。

```sh
python JapanFamily/24_experience_c1/server.py --port 8784
python JapanFamily/24_experience_c1/scripts/verify.py
python JapanFamily/24_experience_c1/scripts/browser.py
python -m unittest discover -s JapanFamily/22_experience_c0/tests -v
```

ブラウザ検査は起動済み8784サービス、Playwright、`/usr/bin/chromium`を使用。開発者によるシナリオ検査であり、実ユーザーの面白さ評価ではありません。クラウドのオンボーディング画面には外向けプレビュー機能がないため、公開プレイURLは提供していません。

## 再構築

`C1_player_distribution/restore_environment.py` は公表済みC-0.1の固定コミット・SHA256を確認して不足ファイルだけ復元します。新C-1を含む軽量コードパックを展開した上で実行してください。既存ファイルが異なる場合は自動上書きしません。

```sh
python C1_player_distribution/restore_environment.py
python C1_player_distribution/build_upgrade.py
python C1_player_distribution/build.py
python C1_player_distribution/verify_release.py
```

`artifacts/C1_SHA256SUMS.txt` と `C1_RELEASE_VERIFICATION.json` を照合してください。旧5GB研究履歴を毎回複製しません。配布用統計核と旧実装は固定された旧パックを参照します。元の研究原資料・巨大DBそのものはこの新しいクラウド作業場所には復元しておらず、その保存状態を今回の検証済み事項とはしません。
