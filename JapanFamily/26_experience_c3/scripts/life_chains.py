"""Three targeted 6-12 month play paths: plan, consent, trip, later revisit.
Fixtures explicitly use a cash scenario; they are not population inference.
"""
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from c3.model import Experience,digest
from c0.bridge import make_engine
E=make_engine();rows=[]
def advance(x,n,index=0):
 goal=x.month+n
 while x.month<goal and not x.game.finished:
  if x.current_event:
   e=x.events[-1];x.choose(e['id'],e['choices'][index%len(e['choices'])]['id'])
  else:x.tick()
for i,(seed,pref,role) in enumerate([(3300,'13','father'),(3301,'27','mother'),(3302,'01','father')]):
 x=Experience.start(E,seed=seed,prefecture_code=pref,role=role,policy='play',initial_cash_yen=10000000,conditions={'mother_age':30,'father_age':32})
 advance(x,6)
 if x.current_event:e=x.events[-1];x.choose(e['id'],e['choices'][-1]['id'])
 # A real prior sharing choice, when needed, can change spouse's travel agreement.
 care=x.schedule('handover','focused_play');x.execute(care)
 before=x.snapshot();x.open_opportunity('weekend');e=x.events[-1];choice=next((c for c in e['choices'] if c['kind']=='trip'),None)
 assert choice,'Travel should be available in this explicit fixture'
 x.choose(e['id'],choice['id']);plan=x.plans[-1];pid=plan['id'];after_choice={'money':x.view()['money']['cash'],'plan':dict(plan),'view':x.view()}
 advance(x,1);after_month={'plans':x.plans,'experiences':x.experiences[-5:],'view':x.view()}
 advance(x,5);after_six={'plans':x.plans,'experiences':x.experiences[-10:],'view':x.view()}
 target=next(p for p in x.plans if p['id']==pid);assert target['status'] in ['completed','early_return','rested','not_realized']
 if target['status']!='not_realized':
  exp=next(z for z in x.experiences if z['id']==target['experience_id']);assert exp['paid_yen']==28000
  assert any(m['experience_id']==exp['id'] for m in x.keepsakes)
 rows.append({'family':i,'seed':seed,'pref':pref,'role':role,'cash_fixture_yen':10000000,'before':{'cash':before['native']['core']['a']['accounts']['cash'],'handover_task':care},'after_choice':after_choice,'one_month_later':after_month,'six_months_later':after_six,'target_plan_status':target['status']})
 print('travel',i,target['status'],flush=True)
assert any(r['target_plan_status']!='not_realized' for r in rows)
(R/'reports/life_chains.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print('C3_LIFE_CHAINS_PASS')
