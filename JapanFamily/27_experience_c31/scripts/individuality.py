"""Only B child seed changes; native A family/resources remain matched."""
import sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from c31.model import Experience,digest
from c0.bridge import make_engine
E=make_engine();rows=[]
for seed in [111,222,333]:
 x=Experience.start(E,seed=4402,child_seed=seed,policy='stable',conditions={'father_age':32,'mother_age':30})
 while not x.current_event:x.tick()
 assert x.events[-1]['domain']=='B'
 x.choose(x.current_event,'broaden');c=x.case_ledger[-1]
 while x.month<6:
  if x.current_event:x.choose(x.current_event,x.events[-1]['choices'][0]['id'])
  else:x.tick()
 ids=x.case_effects(c)['experience_ids']
 rows.append({'child_seed':seed,'initial_A':digest(x.game.core.initial_a),'current_A_accounts':digest(x.game.core.a['accounts']),'choice':'broaden','experiences':[e for e in x.experiences if e['id'] in ids],'case_effects':x.case_effects(c)})
assert len({r['initial_A'] for r in rows})==len({r['current_A_accounts'] for r in rows})==1
assert len({digest([e['reaction_code'] for e in r['experiences']]) for r in rows})>1
(R/'reports/individuality.json').write_text(json.dumps({'children':rows,'matched_A':True,'observed_reactions_differ':True,'reaction_coefficients_external_validity':False,'not_a_personality_diagnosis':True},ensure_ascii=False,indent=2));print('MATCHED_CHILDREN_PASS')
