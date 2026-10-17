"""Whole-path audit: genuine choices/policies, cash reconciliation, semantic news."""
import copy,json,sys,tempfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from c2.model import Experience,POLICIES
from c0.bridge import make_engine,digest
E=make_engine();OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)
checks={};families=[];branches=[];policy_runs=[]
def new(**kw):return Experience.start(E,**kw)
def load_snapshot(body):
 from c2.model import restore_game
 x=Experience();x.__dict__.update(copy.deepcopy(body['state']));x.game=restore_game(body['native'],E);return x
def advance(x,turns=1,index=0):
 count=0
 for _ in range(300):
  if x.game.finished or count>=turns:return
  before=x.month
  if x.current_event:
   event=x.events[-1];x.choose(event['id'],event['choices'][min(index,len(event['choices'])-1)]['id'])
  else:x.tick()
  count+=x.month-before
 raise AssertionError('No progress')
def bio(x):return {k:x.game.core.child._state[k] for k in ['physical_health','latent_state','emotion_regulation','developmental_state','sleep']}
configs=[
 dict(seed=1301,prefecture_code='13',conditions={'mother_age':30,'father_age':32}),
 dict(seed=1302,prefecture_code='27',conditions={'mother_age':27,'father_age':29},initial_cash_yen=600000),
 dict(seed=1303,prefecture_code='01',conditions={'mother_age':39,'father_age':43},initial_cash_yen=3000000),
 dict(seed=1304,prefecture_code='47',role='mother',conditions={'mother_age':28,'partner_present':False},initial_cash_yen=300000),
 dict(seed=1305,prefecture_code='23',role='mother',conditions={'mother_age':34,'father_age':36,'birth_rank':2},initial_cash_yen=1500000),
]
for j,cfg in enumerate(configs):
 x=new(**cfg,policy=list(POLICIES)[j%6]);initial=x.snapshot();before=copy.deepcopy(x.game.core.initial_a);captured=set();cashchecks=[]
 while not x.game.finished:
  if x.current_event:
   event=x.events[-1]
   if event['kind'] not in captured:
    captured.add(event['kind']);base=x.snapshot();outcomes=[]
    for choice in event['choices']:
     b=load_snapshot(base);b.choose(event['id'],choice['id']);immediate=b.snapshot();advance(b,3,index=0)
     outcomes.append({'choice':choice,'immediate':{'accounts':immediate['native']['core']['a']['accounts'],'time':immediate['state']['time_used'],'experiences':len(immediate['state']['experiences']),'experience_semantics':[{k:e[k] for k in ['kind','place','item_id','hours','paid_yen']} for e in immediate['state']['experiences'][-2:]],'requests':immediate['state']['requests'],'envelopes':immediate['state']['envelopes']},'after_three_months':{'view':b.view(),'last_events':b.events[-3:],'months':b.months[-3:]},'biology':digest(bio(b))})
    fingerprints=[digest(o['immediate']) for o in outcomes]
    assert len(set(fingerprints))==len(fingerprints),(event['kind'],'dummy branch')
    # Environment-to-child biology remains disabled: all branches share B trajectory.
    assert len({o['biology'] for o in outcomes})==1,(event['kind'],'biological causal leak')
    branches.append({'family':j,'event':event,'outcomes':outcomes})
   choice=event['choices'][j%len(event['choices'])];x.choose(event['id'],choice['id'])
  else:x.tick()
  f=x.financial_view()
  if f['cash_identity_residual'] is not None:assert f['cash_identity_residual']==0,(j,x.month,x.phase,f['cash_identity_residual'])
  assert x.view()['money']['cash']==x.game.core.a['accounts']['cash']
  cashchecks.append(f['cash_identity_residual'])
 assert x.game.core.initial_a==before
 assert all(v['check']['cash_identity_residual']==v['check']['net_worth_identity_residual']==0 for v in x.finance)
 assert len({l['key'] for l in x.logs if l['key'].startswith('experience/')})==len([l for l in x.logs if l['key'].startswith('experience/')])
 assert all(sum(l.get('published_period',l['period'])==m for l in x.logs)<=3 for m in range(x.month+1))
 # Verify that every narrative experience references a real performed task and item.
 for r in x.experiences:
  assert any(t['id']==r['task_id'] and t['status']=='done' for t in x.tasks)
  if r['item_id']:assert any(i['id']==r['item_id'] for i in x.inventory.values())
 intervals=[b['period']-a['period'] for a,b in zip(x.events,x.events[1:])]
 families.append({'configuration':cfg,'initial':initial,'final_view':x.view(),'events':x.events,'experiences':x.experiences,'finance':x.finance,'requests':x.requests,'policy_operations':x.policy_operations,'months':x.months,'initial_asset_trace':x.initial_trace,'audit':{'event_count':len(x.events),'mean_event_interval':sum(intervals)/len(intervals) if intervals else None,'intervals':intervals,'published_logs':len(x.logs),'fact_candidates':len(x.fact_ledger),'suppressed':len(x.suppressed),'semantic_duplicate_experience_logs':0,'cash_checks':len(cashchecks)}})
 print('family',j,'age',x.game.core.elapsed_months,'events',len(x.events),'logs',len(x.logs),'gap',families[-1]['audit']['mean_event_interval'],flush=True)
checks.update(five_families_24mo=True,all_event_choice_branches_have_state_differences=True,no_added_long_term_child_effect=True,integer_cash_and_net_worth_identities=True,player_money_matches_engine=True,semantic_experience_duplicates_suppressed=True,at_most_three_new_logs_per_month=True)
for policy in POLICIES:
 x=new(seed=1301,initial_cash_yen=5000000,conditions={'father_age':32,'mother_age':30},policy=policy);advance(x,24,index=1)
 policy_runs.append({'policy':policy,'biological_hash':digest(bio(x)),'cash':x.game.core.a['accounts']['cash'],'term':x.game.core.a['accounts']['term'],'time_total':sum(sum(m['time_used'].values()) for m in x.months),'experience_count':len(x.experiences),'contexts':sorted(set(e['kind'] for e in x.experiences)),'native_hours_ratio':x.game.core.a['parents']['father']['hours_ratio'],'policy_operations':x.policy_operations,'logs':x.logs})
assert len({p['biological_hash'] for p in policy_runs})==1
assert len({digest([p['cash'],p['term'],p['time_total'],p['experience_count'],p['contexts']]) for p in policy_runs})==6
checks['six_persistent_policies_distinct_real_allocation']=True
# Same model, same inputs, same decisions; persistence at a waiting event.
a=new(seed=1301,policy='stable');advance(a,2)
for _ in range(8):
 if a.current_event:break
 a.tick()
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'save.gz';a.save(p);b=Experience.load(p,E);assert a.snapshot()==b.snapshot()
 for _ in range(5):a.view();b.view()
 assert a.snapshot()==b.snapshot()
 advance(a,4);advance(b,4);assert a.snapshot()==b.snapshot()
checks['saved_event_resume_seed_and_view_purity']=True
# A mid-month birth retains the native final partial accounting distinction.
x=new(seed=1304,birth_date='2026-10-17',policy='stable');advance(x,25)
assert x.game.finished and x.date=='2028-10-17';assert x.month==25
checks['midmonth_birth_24month_limit']=True
summary={'checks':checks,'family_metrics':[f['audit'] for f in families],'policies':policy_runs,'branch_events':len(branches),'actual_user_study':False,'scientific_external_validation':False}
for name,body in [('verification.json',summary),('families_24mo.json',families),('event_branch_comparisons.json',branches)]:
 (OUT/name).write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf8')
print('C2_VERIFICATION_PASS',flush=True)
