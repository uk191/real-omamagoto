"""Render saved outcomes; do not invent narrative facts or causal explanations."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'reports'
rows=json.loads((O/'sixteen_branches.json').read_text());text=['# 四つの相談・全16分岐の状態比較','', '各領域は同一チェックポイント・同一家庭・同一seedから四分岐。主比較はseed4402、父32歳・母30歳、所得・初期口座の指定なし。前提は架空の街中移動条件。数値は保存された実行結果で、人口推定・効用点・因果効果の推定ではない。','', '支出は実際の活動費、時間は実際に使った時間。預金振替は消費から分離する。三か月後の当月初めの処理まで進め、二か月後の相談の次の実行も含めて検査する。主選択の集計と後続選択の集計は別。']
axes={'A':'一回の遠出／近所の反復／将来の余裕／家族の休み。移動の新しさと、複数回付き合う時間、預金、支え合いが競合する。','B':'一つを深める／幅を広げる／子が向かった方で待つ／親とのやりとり。親が環境を作る方針が異なり、道具の購入や関わりの回数・待つ時間も違う。','C':'仕事の見通し／いま家で過ごす／消費を調整する／支援を整える。同じ親の時間を何へ使うかを選ぶ。現実の依頼の実現確率は未校正。','D':'公開で挑戦／家族内に残す／匿名で参加／応募せず訪問。参加とプライバシーの対立を、その家族が取る行動として扱う。'}
for b in rows:
 text+=['','## '+b['domain']+'｜'+b['event']['title'],'',axes[b['domain']],'',b['event']['background'],'','| 選択・価値 | 直後：支出／時間／残予定 | 一か月後：主選択の累計 | 三か月後：主選択の累計 |','|---|---|---|---|']
 for o in b['outcomes']:
  c=o['choice'];n=o['immediate']['effects'];one=o['one_month']['effects'];t=o['three_months']['effects']
  text.append('| '+c['title']+'（'+c['value_axis']+'） | '+f'{n["expenses_yen"]:,}円／{n["hours_used"]:g}h／{n["planned_operations"]}件 | {one["expenses_yen"]:,}円／{one["hours_used"]:g}h | {t["expenses_yen"]:,}円／{t["hours_used"]:g}h'+' |')
 for o in b['outcomes']:
  c=o['choice'];f=o['three_months']['effects'];a=o['followup_result'];af=a['effects']
  text+=['','### '+c['title'],'','大切にすること：'+c['gain']+'。引き受けること：'+c['forgo']+'。','',f'主選択の直接の支払い口座差額 {f["cash_delta_direct"]:+,}円、定期性預金差額 {f["term_delta_direct"]:+,}円。経験 '+', '.join(e['kind'] for e in o['three_months']['experiences'])+'。']
  if f['native_results']:text+=['','既存Aモデルの返答：'+'／'.join(r['text'] for r in f['native_results'])]
  if f['projects']:text+=['','企画結果：'+'、'.join(p['format']+'='+p['status'] for p in f['projects'])+'。ゲーム内の抽選であり、子どもの容姿・能力の評価ではない。']
  if f['observed_reactions']:text+=['','実際の場面：'+f['observed_reactions'][-1]['text']]
  text+=['','二か月後に出た相談：'+o['followup']['background'],'','検査で選んだ後続選択：'+o['followup']['chosen']+f'。その実支出 {af["expenses_yen"]:,}円、実時間 {af["hours_used"]:g}h。'+('／'.join(r['text'] for r in af['observed_reactions']) or '新しい外出に限らず、実際の手続き・記録を残す操作。')]
  if f['unrealized'] or af['unrealized']:text+=['','実現しなかった理由：'+str(f['unrealized']+af['unrealized'])]
 text+=['','この四分岐は、識別子・タイトルを除外した支出・振替・時間・経験種別・申請・応募形式等の組で全て異なる。主選択後のB身体・潜在状態・調整・発達・睡眠の比較ハッシュは四分岐で一致する。']
text+=['','## 家庭条件・個体差・未検証事項','','追加5家庭では北海道・大阪・沖縄・長野・福岡、父母の年齢・学歴・都市／郊外／移動費条件、単親、月途中出生を含め24か月を確認した。給料・預金は手入力していない。時間がなければ候補を延期し、費用・合意・当日の天候シナリオで未実現になった場合は理由を保存する。47都道府県全体や全低資産家庭の今回の網羅試験ではない。','','同じA家庭で子どものseedのみ111/222/333に変更し、同じB領域の選択を実行した。初期Aと比較時A口座は一致し、観察された反応列は異なった（reports/individuality.json）。気質・注意等は反応に用いられるが、その反応式は未校正のゲーム仮定。違いが出ることは現実の乳児行動の外部妥当性を意味しない。','','未検証：選択の人口中の発生頻度、反応式、合意・天候・応募抽選、移動条件・価格、仕事や保育の実現確率、資産同時分布。新しい長期発達効果は未実装。旅行や絵本で能力・人格を上げる処理はない。四択に主観的な迷いや納得が生まれるかは、ユーザーのプレイで評価する。']
(R/'SIXTEEN_BRANCHES.md').write_text('\n'.join(text)+'\n')
