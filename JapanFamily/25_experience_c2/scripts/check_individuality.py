import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from c2.model import Experience
from c0.bridge import make_engine,digest
E=make_engine();records=[]
for child_seed in [111,222]:
 x=Experience.start(E,seed=1301,child_seed=child_seed,policy='play',initial_cash_yen=3000000,conditions={'father_age':32,'mother_age':30})
 while x.month<12:
  if x.current_event:
   e=x.events[-1];x.choose(e['id'],e['choices'][-1]['id'])
  else:x.tick()
 records.append({'child_seed':child_seed,'household_id':x.game.core.identity['household_id'],'run_id':x.game.core.identity['run_id'],'accounts':x.game.core.a['accounts'],'B_core_hash':digest(x.game.core.child._state['latent_state']),'reaction_codes':[e['reaction_code'] for e in x.experiences],'observed_logs':x.logs,'experience_count':len(x.experiences)})
assert records[0]['household_id']==records[1]['household_id'] and records[0]['accounts']==records[1]['accounts']
assert records[0]['B_core_hash']!=records[1]['B_core_hash'] and records[0]['reaction_codes']!=records[1]['reaction_codes']
(ROOT/'reports/individuality.json').write_text(json.dumps(records,ensure_ascii=False,indent=2));print('C2_DIFFERENT_CHILDREN_SAME_HOUSEHOLD_PASS')
