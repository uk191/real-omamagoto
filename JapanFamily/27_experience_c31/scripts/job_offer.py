"""Native job offers must remain actionable inside the four-choice C structure."""
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from c31.model import Experience
from c0.bridge import make_engine
E=make_engine();result=None
for seed in [5501,5502,5503,5504]:
 x=Experience.start(E,seed=seed,role='mother',policy='work',conditions={'mother_age':28,'father_age':30,'mother_employed':False})
 while x.month<10:
  if x.current_event:
   e=x.events[-1]
   offer=x.game.core.a['parents'][x.actor].get('job_offer')
   if e.get('domain')=='C' and offer:
    outcomes=[]
    for c in e['choices']:
     b=x.clone();b.choose(e['id'],c['id']);case=b.case_ledger[-1]
     while b.month<x.month+1:
      if b.current_event:b.choose(b.current_event,b.events[-1]['choices'][0]['id'])
      else:b.tick()
     outcomes.append({'choice':c['id'],'effects':b.case_effects(case),'state':b.context()})
    result={'seed':seed,'offer':offer,'event':e,'outcomes':outcomes};break
   x.choose(e['id'],e['choices'][0]['id'])
  else:x.tick()
 if result:break
assert result,'No observed native offer in fixture support'
assert result['outcomes'][0]['effects']['native_results']
(R/'reports/native_job_offer.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('NATIVE_JOB_OFFER_FOUR_CHOICES_PASS',seed)
