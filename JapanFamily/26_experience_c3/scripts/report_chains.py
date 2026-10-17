import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];rows=json.loads((R/'reports/life_chains.json').read_text())
s=['# 親から立てた一泊の予定｜3家庭の追跡','\nこれは開発者による条件比較。初期口座1,000万円を明示したテスト家庭で、全国の典型像ではない。']
for row in rows:
 e=row['after_choice']['plan'];p=next(p for p in row['six_months_later']['plans'] if p['id']==e['id']);observed=next((x for x in row['six_months_later']['experiences'] if x.get('id')==p.get('experience_id')),None)
 # The chosen trip may be earlier than the last ten activities; pull the persisted album.
 memories=[m for m in row['six_months_later']['view']['album'] if m['experience_id']==p.get('experience_id')]
 s += [f"\n## 家庭{row['family']+1}｜{row['pref']}・{row['role']}",f"選択前の支払い口座：{row['before']['cash']:,}円。自分が育児を引き受ける時間を実行してから、一泊の旅行を提案した。",f"選択直後：{e['status']}。予定を保存しただけで、まだ費用は支払わない。実行月に時間・残高・配偶者の意向を再評価する。",f"翌月の結果：{p['status']}。",'\n'.join(m['text'] for m in memories),f"6か月後：家族のアルバムに{len(memories)}件の当日の記録が残っている。近況・後続の判断はlife_chains.jsonのsix_months_laterを参照。"]
s+=['\n3家庭で、通常の旅行実施2例と、泣いて早めに帰った1例を確認。28,000円の追加仕訳が記録され、早帰りでも入場・宿泊費を架空に返金しない。原資、費用、合意・反応・天候は明示されたゲームシナリオ。旅行による能力・愛着の加点はない。']
(R/'reports/LIFE_CHAINS.md').write_text('\n\n'.join(s),encoding='utf8')
