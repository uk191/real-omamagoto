import sys,json,gzip,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R.parent/'26_experience_c3'))
from c3.model import Experience
from c0.bridge import make_engine
E=make_engine();rows=[]
for seed in range(24):
 x=Experience.start(E,seed=seed,prefecture_code='13',conditions={'father_age':23,'mother_age':22})
 a=x.game.core.a;people={p['person_id']:p for p in a['persons']};acc=a['accounts']
 rows.append({'seed':seed,'accounts':acc,'deposits':acc['cash']+acc.get('term',0),'normal_annual':{p:q['normal_annual'] for p,q in a['parents'].items()},'parents':{p:people[p] for p in a['parents']},'housing':a['housing'],'asset_trace':x.initial_trace,'config':x.game.config,'automatic_source':a['initial_family']['provenance'].get('automatic')})
# Conditioning through the native API, including the maternal pregnancy phase.
ed=[]
for coarse in ['1','2','3','4']:
 for seed in range(3):
  try:
   x=Experience.start(E,seed='education-'+coarse+'-'+str(seed),conditions={'father_age':23,'mother_age':22,'father_education':coarse,'mother_education':coarse})
   people={p['person_id']:p for p in x.game.core.a['persons']}
   for p in ['father','mother']:assert people[p]['attributes']['education_coarse']==coarse
   ed.append({'education':coarse,'seed':seed,'parents':{p:people[p]['attributes'] for p in ['father','mother']},'annual':{p:q['normal_annual'] for p,q in x.game.core.a['parents'].items()},'success':True})
  except ValueError as err:ed.append({'education':coarse,'seed':seed,'success':False,'reason':str(err)})
report={'young_parent_examples':rows,'over_10million_deposit_examples':[r['seed'] for r in rows if r['deposits']>10000000],'education_conditioning':ed,'asset_age_direct_conditioning':False,'arbitrary_cap_added':False,'not_a_population_validation':True,'original_user_seed_unknown':True}
(R/'reports/initial_assets_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('over10m',report['over_10million_deposit_examples']);print('education',[(r['education'],r['success']) for r in ed])
