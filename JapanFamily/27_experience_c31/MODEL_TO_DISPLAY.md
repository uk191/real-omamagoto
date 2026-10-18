# 状態と表示・効果の対応

| 表示・処理 | 正式な記録 | 根拠・制約 |
|---|---|---|
| 家族・主人公・職業・通常所得 | 継承A persons/parents、identity | A13/A16/A18統計核と推定結合。学歴等は条件付き生成 |
| 相談の背景 | decision_context_facts | その時点の確定口座・時間・就業・観察。将来のforecastは出さない |
| 四択の価値・引受けること | design.py recipes | ゲーム設計。正解・優劣点数を設けない |
| 選択 | case_ledger | domain/choice/date/before/after/commitment IDs/親case ID |
| 時間・予定・中止理由 | commitments、既存tasks/time_used | 実行時に資金・時間・月齢・合意を再確認。実行後は実時間、未実行は予定と表示 |
| 支出・口座振替 | C3 finance / native Ledger と A月次口座 | 均衡仕訳。預金振替を消費と混同しない。将来費用はまだ引かない |
| 行動の場面と短期反応 | 既存scenes/experiences | 年齢・潜在特性・疲労等を用いる未校正のC3表現。新しい長期B効果なし |
| 二つの物から待つ | agency_trials + 実際のtask | 非検証の安全な遊びのゲーム用選択モデル。性格診断にはしない |
| 家族の記録・後続相談 | keepsakes / source_case_id / experience_ids | 実際に残った経験・物・未実現理由を参照。乳児の自伝的記憶を主張しない |
| 仕事・支出・支援希望と返答 | native requests/results、A completed.decisions | 本人の希望と実現を分離。相手の勤務を直接操作しない。Aの外部未検証性を継承 |
| 名前付き・匿名の企画 | project_entries | 架空、年齢能力審査なし、抽選0.35はゲーム仮定。家族公開の合意もC3から継承する仮定 |
| 旅費メモ | purpose_funds + term | 同じ定期性預金の目的メモ、保護された別口座ではない。残高低下なら減額 |
| 行動の翌月持越し | due_periodと保存されたoperation | 元のモデルの乱数を追加消費しない。決定論的な別ハッシュ乱数を利用 |

プレイヤーAPIは観察・実行結果だけを返し、内部latent_state・将来の能力時期・forecastを返さない。テスト／研究用snapshotとプレイヤーviewは分離。重要な文章のsource_refsは保存した事実・経験・相談・応募結果を指す。物語のための生成AIや外部文章生成は使っていない。

追加したものは時間・費用・経験・関係者の行動・記録・次の相談条件であり、IQ・愛着・人格の増減係数は存在しない。環境を変えてもBの生物学的発達が同じであることを16分岐で検査する。これは因果効果を見つけた結果ではなく、未識別効果を導入しない実装上の約束である。
