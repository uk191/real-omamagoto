"""Targeted agency/continuity/invariance checks and actual scenario records."""
import copy,json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from c1.experience import Experience,restore_game
from c0.bridge import make_engine,digest
E=make_engine();OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)
def new(seed=1301,**kwargs):return Experience.start(E,seed=seed,child_name='はる',initial_cash_yen=8000000,conditions={'father_age':32,'mother_age':30},**kwargs)
def months(x,n):
 for _ in range(n*3):x.tick()
def biology(x):
 s=x.game.core.child._state
 return {k:s[k] for k in ['latent_state','physical_health','developmental_state','emotion_regulation','sleep','growth_process']}
checks={};records=[]
x=new();original=x.game.core.initial_a['accounts'].copy();months(x,6)
x.plan('book');x.plan('park');x.plan('handover');x.tick();cost=x.plans[0]['actual_cost'];assert cost==1200 and 'book' in x.inventory
assert x.time_used['care']==.5
assert x.game.core.initial_a['accounts']==original
x.tick();assert x.npc['monthly_rest_received']==2
for f in x.finance:assert f['check']['net_worth_identity_residual']==f['check']['cash_identity_residual']==0
x.tick();x.plan('book');x.tick();assert x.plans[-1]['actual_cost']==0
assert x.experiences[-1]['previous_experience_id']==x.experiences[0]['id']
checks['real_cost_time_purchase_reuse_familiarity']=True
r=new();r.plan('voice',repeat=True);months(r,2)
assert len(r.experiences)==2 and len(r.plans)==3
r.cancel(r.plans[-1]['id']);months(r,1);assert len(r.experiences)==2
before=copy.deepcopy(r.game.core.a['accounts']);r.request('save_money',100);r.request('withdraw_money',100);assert r.game.core.a['accounts']==before
checks['recurring_plan_cancel_and_asset_transfer']=True
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'save.gz';x.save(p);y=Experience.load(p,E)
 assert x.snapshot()==y.snapshot();before=digest(x.snapshot())
 for _ in range(10):x.view()
 assert before==digest(x.snapshot())
 for _ in range(5):x.tick();y.tick()
 assert x.snapshot()==y.snapshot()
 env=json.loads(__import__('gzip').open(p,'rt',encoding='utf8').read());env['payload']['state']['phase']=2
 with __import__('gzip').open(p,'wt',encoding='utf8') as f:json.dump(env,f)
 try:Experience.load(p,E);raise AssertionError('tamper accepted')
 except ValueError:pass
checks['save_phase_resume_seed_view_purity_tamper']=True
# Time and liquidity rejection leave biological and money states untouched.
z=Experience.start(E,seed=1301,initial_cash_yen=0,child_name='はる',conditions={'father_age':32,'mother_age':30})
months(z,2);z.game.core.a['accounts']['cash']=0 # explicit test fixture, never a game operation
before=copy.deepcopy(z.game.core.a['accounts']);z.plan('book');z.tick();assert z.plans[-1]['status']=='deferred' and z.game.core.a['accounts']==before
checks['insufficient_cash_no_free_item_no_charge']=True
for seed,pref,age in [(1301,'13',0),(1302,'27',6),(1303,'01',12)]:
 s=Experience.start(E,seed=seed,prefecture_code=pref,child_name='はる',initial_cash_yen=8000000,conditions={'father_age':32,'mother_age':30})
 months(s,age);base=s.snapshot();control=Experience.load if False else None
 # Clone the exact initial household + child without resampling.
 def branch():
  obj=Experience();obj.__dict__.update(copy.deepcopy(base['state']));obj.game=restore_game(base['native'],E);return obj
 a=branch();b=branch();before_view=a.view()
 for m in range(6):
  kind='voice' if a.game.core.elapsed_months<2 else 'book'
  a.plan(kind)
  if a.game.core.elapsed_months>=1:a.plan('park')
  if m==0:a.request('shorter');a.plan('handover')
  if m==1:a.request('nursery')
  months(a,1);months(b,1)
 assert biology(a)==biology(b),'C1 activities or choices leaked into biological B model'
 assert a.game.core.a['parents']['father']['hours_ratio']==.8
 rec={'seed':seed,'pref':pref,'start_age':age,'before':before_view,'after':a.view(),'control_after':b.view(),'native_father_with_choice':a.game.core.a['parents']['father'],'native_father_control':b.game.core.a['parents']['father'],'months':a.months[-6:],'plans':a.plans,'experiences':a.experiences,'decisions':a.agreements,'finance':a.finance,'biological_effect_disabled':True}
 records.append(rec)
checks['three_families_three_ages_six_month_branches']=True
# 24-month path and actual calendar/birth-day consistency.
x=new(seed=1304,birth_date='2026-10-17');months(x,25)
assert x.game.finished and x.date=='2028-10-17';x.game.core.assert_consistent()
assert x.game.core.child._state['age_days']==731
checks['midmonth_birth_24months_25calendar_turns']=True
# Different child under the same household, equal plan sequence.
a=new(seed=1301,child_seed=111);b=new(seed=1301,child_seed=222);assert a.game.core.identity['household_id']==b.game.core.identity['household_id']
for _ in range(12):
 a.plan('voice');b.plan('voice');months(a,1);months(b,1)
assert [r['observed_reaction'] for r in a.experiences]!=[r['observed_reaction'] for r in b.experiences]
assert biology(a)!=biology(b)
checks['same_household_different_children_real_B_and_reactions']=True
checks['log_count_at_most_three_per_month']=all(sum(l['period']==m and l['phase']!=0 for l in a.logs)<=2 for m in range(12))
(OUT/'scenario_comparisons.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'verification.json').write_text(json.dumps({'checks':checks,'scope':'developer scenario inspection; not human playtest nor external scientific calibration','passed':all(checks.values())},ensure_ascii=False,indent=2))
print(json.dumps(checks,ensure_ascii=False))
