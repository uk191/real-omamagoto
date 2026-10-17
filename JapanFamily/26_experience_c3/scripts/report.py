"""Summarize executed records; never label developer inspection a human study."""
import json,collections
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'reports'
v=json.loads((O/'verification.json').read_text());families=json.loads((O/'families_24mo.json').read_text());branches=json.loads((O/'choice_comparisons.json').read_text())
rows=['|家庭|地域・視点・方針|場面|主ログ|アルバム|イベント|平均間隔（月）|','|---|---|---:|---:|---:|---:|---:|']
for f,m in zip(families,v['families']):
 c=f['config'];rows.append(f"|{m['family']+1}|{c['prefecture_code']}・{c['role']}・{c['policy']}|{m['scenes']}|{m['logs']}|{m['memories']}|{m['events']}|{m['mean_interval']:.2f}|")
mechanisms=set()
for f in families:
 for s in f['scenes']:mechanisms.add((s['kind'],s['status'],tuple(b['code'] for b in s['beats'] if b['code'] not in ['arrival','continuity']),bool(s['paid_yen'])))
metrics={'total_scene_records':sum(m['scenes'] for m in v['families']),'published_logs':sum(m['logs'] for m in v['families']),'actual_genres':sorted(set(s['genre'] for f in families for s in f['scenes'])),'executed_kinds':sorted(set(s['kind'] for f in families for s in f['scenes'])),'observed_mechanical_profiles':len(mechanisms),'event_categories':v['event_categories'],'branch_cases':len(branches),'same_visible_text_duplicate_count':sum(m['duplicate_texts'] for m in v['families']),'child_log_share_range':[min(m['child_or_memory_log_share'] for m in v['families']),max(m['child_or_memory_log_share'] for m in v['families'])],'not_independent_story_count':True}
(O/'diversity.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
# Focused editorial samples from actual generated records, not invented episodes.
review=['# 生成記録の編集的レビュー（開発者による点検）','\n実ユーザーテストではない。以下は保存した履歴の抜粋と、その読み取り。文章がすべて自然で面白いという判定ではない。']
for j in [0,2,5]:
 f=families[j];logs=f['final_view']['logs'];start='2027-03';end='2027-08'
 review.append(f"\n## 家庭{j+1}：生後5〜10か月の場面\n")
 for l in logs:
  if start<=l['date'][:7]<=end:review.append('### '+l['date']+'｜'+l['title']+'\n\n'+l['text']+'\n\n根拠：'+', '.join(l['source_refs']))
 review.append('\n点検：実行済みの物品・場所・反応のみを本文に採用。成長の節目は観察と獲得を区別する。泣いた外出を失敗点にせず、切り上げた行程を残す。定型の「前回とは違う顔」を連続させる表現は削除した。家計・就業の数値説明は必要な変化と詳細画面へ絞った。')
review.append('\n## 残る文章上の問題\n\n顔を向ける・見つめる等の基礎的な仕草は共通化しており、意味的に似た文章は残る。個人固有の癖・会話・対象への長い関心はまだ薄い。「機械的な本文がすべて解消した」とは評価しない。今後は利用者が覚えていた場面と読み飛ばした場面を確認する。')
(O/'EDITORIAL_REVIEW.md').write_text('\n\n'.join(review),encoding='utf8')
report=f'''# C-3 構築報告｜子どもとの経験から、家族の次へ

2026-10-18（日本時間）。従来のC-2を残し、26_experience_c3に独立実装。体験の入口は公開する C3_START.zip → START_C3.cmd。旧C1/C2のフォルダ・セーブを上書きしない。C3では新しい家庭から始める。

## 今できること

父親・母親として正式な家庭生成APIから開始。少数の生活方針で約10秒/月の自動進行を続け、贈り物、外出、写真、誕生日などで立ち止まる。任意の「次の楽しみ」から自分でも計画できる。選ぶと費用・時間・所有物・予定・子どもの短期反応・履歴が変わる。遠出は翌月に実現可否を再評価する。短く帰った日、応募が断られた／抽選に選ばれなかった日も、消えずに家族の記録になる。以前訪れた場所から再訪の機会を作る。

既存7能力のうち歩行・言語はBの養育者報告、他5能力は獲得済み代理状態とC3の観察機会を組み合わせて、親が見た場面にする。言語の陽性報告に具体的な短い呼びかけを添える場合は、その語彙とやりとりをC3の創作場面として先に保存する。Bが語彙内容を予測しているとは扱わない。潜在特性や予定獲得日は表示しない。能力・愛着・知能の加点は一切追加しない。

## 実行結果

{chr(10).join(rows)}

10家庭すべて24か月、月途中出生1家庭は25暦ターンで正確な24か月誕生日まで進行。場面記録{metrics['total_scene_records']}件、公開主ログ{metrics['published_logs']}件。これは同数の独立した物語を意味しない。実行ジャンルは{len(metrics['actual_genres'])}、イベントカテゴリは{len(metrics['event_categories'])}、分岐比較は{len(branches)}イベント。主ログの子ども・経験・記憶関連比率は{metrics['child_log_share_range'][0]:.1%}〜{metrics['child_log_share_range'][1]:.1%}。主ログの完全同文重複は0。意味の似た基礎反応まで0としたわけではない。

さらに3家庭で、本人から一泊の予定を提案し、翌月の実行と6か月後までの追跡を行った。2家庭は旅行を実施し、1家庭は子どもが泣いて早めに帰った。28,000円の費用、滞在時間、アルバムが実際に更新された。初期口座1,000万円の明示テスト条件で、典型的な出生家庭という意味ではない（reports/LIFE_CHAINS.md）。

各比較では、同じ開始状態から全選択肢を実行し、直後と3か月後の口座・時間・物品・経験・予定・希望の結果を保存した。全分岐で実際の状態が異なり、Bの生物学的軌跡への未検証効果は入らない。同一家庭に子どもseedだけを変えた3例では、Aの初期口座が一致し、反応列が異なる。6方針の割当も実際に異なる。

月内3段階の自動進行・重要場面停止・任意の計画・アルバム・保存再開・24か月・スマートフォン幅を実ブラウザで検査し、画面を保存する。ブラウザの最終結果はreports/browser.json。旧C0の既存13テストは通過。保存後の独立ZIP・SQLite・旧新API検査は別ファイル C3_RELEASE_VERIFICATION.json。Windowsネイティブ実行と本人による面白さ評価は未実施で、Linux検査とは区別する。

## 検査中に修正した問題

- 年齢帯だけが変わり、見える出来事が同じでも新しい文として出る問題。観測可能な情景の署名で抑え、過去の日付だけの違いを新規性と数えない。
- 同じ予定の宣言文が繰り返される問題。予定は履歴に残し、同じ本文は主ログへ重複掲載しない。
- 郊外・移動の長い設定で、交流の予算が移動費にも満たない問題。交流方針の上限と見積り・支払を揃えた。
- 予定枠の育児がゼロでも自分の休息枠が空いている場合、家での短い関わりを計画できない問題。実在する休息枠を消費して実行できるようにした。
- 保存前は同じPythonオブジェクトを参照していた保留ログと事実台帳が、JSON復元後に分離し、公開日時の内部記録に差が出る問題。参照の共有に依存せずIDで更新するよう修正し、保留場面と翌月予定を含む保存・5か月後の完全一致を確認した。
- ブラウザが先に開く未使用接続で旧単一接続サーバーが待ち続ける問題を、同じ接続条件で再現した。接続受付をThreadingHTTPServerへ分離し、SQLite接続の作成と全シミュレーション処理は同一の専用ワーカーで順番に行う。A/Bのコードや乱数順序は変更しない。3本の未使用接続を開いたまま6件の並行ヘルス要求、家庭生成、月次処理、保存再開、古いrevisionの拒否を検査した（reports/connections.json）。
- 0→0時間の状態変化を数値中心で書く文、英語の就業コード、観察回数の集計文を主画面から除いた。続きの同じ締め文を毎回足す表現も削除した。

## 体験としての評価

**現在どこまで成立したか。** 生活費・本人の働き方を背景に、子どもへ何を見せるかを選び、その子の期待どおりでない反応と、後日に続く予定・思い出を見守る循環は動く。家計の操作だけで進める構造からは離れた。面白さ自体は本人の再プレイで判断する。

**実際に今できていること。** 10家庭の記録に、積み木を大人が積んで子どもが倒す場面、動物より足元に手を伸ばす外出、横顔やあくびの写真を残す場面、以前の外出先の再提案、誕生日の予定と実行がある。いずれも実際の履歴を参照している。全文はfamily01〜10_player_record.md、重点期間の抜粋と指摘はEDITORIAL_REVIEW.md。

**何が足りないか。** 短期反応は仮定が多く、同じ動作の共通表現は残る。独自の関心の持続、配偶者の多面的な希望、食事・健康・地域アクセスの実証接続は弱い。プレイヤーの操作の種類を増やすより、印象に残った場面と読み飛ばした場面の確認、行動生成の深化を優先する。

**2〜6歳の前に何を直すか。** 本人のフィードバックに基づく発見・予定・反応の質と頻度、反応モデルと観察機会の外部校正、実在施設・交通の接続、資産・雇用の未検証経路を優先する。データ件数だけを理由に年齢を広げない。

## 保全・根拠・未完成

A/Bと旧C系統を改変せず、ハッシュで継承する。巨大原資料DBはこの環境で新規に復元・再検証しておらず、旧公開資産を参照する。コード・画面・小規模記録と比較全履歴を別パックにする。再構築はREADME.md、監査・利用変数・統計と仮定の境界・未実装範囲はAUDIT_AND_DESIGN.mdを参照。

全22活動を別々の物語22種類、557場面を557種類の独立イベント、あるいは数千種類の場面を完成したとは数えない。一般化できる場面構造を実装し、今回実際に通過した範囲を保存した研究体験版である。
'''
(R/'BUILD_REPORT.md').write_text(report,encoding='utf8');print(json.dumps(metrics,ensure_ascii=False))
