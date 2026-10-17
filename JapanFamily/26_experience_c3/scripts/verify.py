"""Play-path verification: 10 native A/B households, meaningful branches, facts.
This is developer scenario inspection, not human enjoyment validation.
"""
import copy,json,tempfile,sys,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from c3.model import Experience,POLICIES,ACTS,restore_game,digest
from c3.scenes import render_scene
from c0.bridge import make_engine
E=make_engine();OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)
def new(**kw):return Experience.start(E,**kw)
def restore(snapshot):
 x=Experience();x.__dict__.update(copy.deepcopy(snapshot['state']));x.game=restore_game(snapshot['native'],E);return x
def advance(x,n=1,index=0):
 goal=x.month+n
 for _ in range(500):
  if x.game.finished or x.month>=goal:return x
  if x.current_event:
   e=x.events[-1];x.choose(e['id'],e['choices'][index%len(e['choices'])]['id'])
  else:x.tick()
 raise AssertionError('Progress stalled')
def biology(x):return digest({k:x.game.core.child._state[k] for k in ['physical_health','latent_state','emotion_regulation','developmental_state','sleep']})
def effects(x):return {'accounts':copy.deepcopy(x.game.core.a['accounts']),'time':copy.deepcopy(x.time_used),'experience_kinds':[e['kind'] for e in x.experiences],'plans':copy.deepcopy(x.plans),'inventory':copy.deepcopy(x.inventory),'requests':copy.deepcopy(x.requests)}
configs=[]
for i,(pref,role,policy,setting,cash) in enumerate([('13','father','play','city',3000000),('27','mother','time','suburban',500000),('01','father','social','rural',2000000),('47','mother','stable','rural',300000),('23','father','save','suburban',1200000),('40','mother','work','city',5000000),('26','father','stable','city',80000),('20','mother','play','rural',3500000),('04','father','time','suburban',800000),('37','mother','social','rural',1000000)]):
 cond={'mother_age':27+i%9,'father_age':29+i%11}
 if i in [3,7]:cond={'mother_age':28+i%6,'partner_present':False}
 if i in [0,5]:cond.update(father_income_yen=8000000,mother_income_yen=4000000)
 if i in [3,6]:cond.update(mother_income_yen=1200000)
 configs.append(dict(seed=3300+i,prefecture_code=pref,role=role,policy=policy,neighborhood=setting,initial_cash_yen=cash,conditions=cond,birth_date='2026-10-17' if i==7 else '2026-10-01',child_name=['はる','ゆい','そら','あお','りつ','ひな','かい','なぎ','めい','れん'][i]))
families=[];branches=[];metrics=[];seen=set()
for i,cfg in enumerate(configs):
 x=new(**cfg);initial=digest(x.game.core.initial_a);checks=0
 while not x.game.finished:
  if x.current_event:
   e=x.events[-1]
   if e['kind'] not in seen or i<3 and len([b for b in branches if b['family']==i])<2:
    seen.add(e['kind']);snap=x.snapshot();outcomes=[]
    for c in e['choices']:
     b=restore(snap);b.choose(e['id'],c['id']);now=effects(b);advance(b,3,index=i)
     outcomes.append({'choice':c,'immediate':now,'three_months_later':effects(b),'biology':biology(b),'logs':b.logs[-9:]})
    assert len({digest(o['immediate']) for o in outcomes})==len(outcomes),(i,e['kind'],'dummy choice')
    assert len({o['biology'] for o in outcomes})==1,(i,e['kind'],'new untested biological effect')
    branches.append({'family':i,'event':e,'outcomes':outcomes})
   c=e['choices'][(i+x.month)%len(e['choices'])];x.choose(e['id'],c['id'])
  else:x.tick()
  assert x.financial_view()['cash_identity_residual'] in [0,None]
  assert x.view()['money']['cash']==x.game.core.a['accounts']['cash'];checks+=1
 assert x.game.core.elapsed_months==24 and digest(x.game.core.initial_a)==initial
 assert all(f['check']['cash_identity_residual']==f['check']['net_worth_identity_residual']==0 for f in x.finance)
 assert all(sum(l.get('published_period',l['period'])==m for l in x.logs)<=3 for m in range(x.month+1))
 for scene in x.scenes:
  assert render_scene(scene)==''.join(b['text'] for b in scene['beats'])
  assert scene['age_days']>=ACTS[scene['kind']]['min_age']*28 # actual date month thresholds stronger in schedule
  assert any(e['scene_id']==scene['id'] for e in x.experiences)
  if scene['item_id']:assert scene['item_id'] in [v['id'] for v in x.inventory.values()]
  if scene['prior_scene_id']:assert int(scene['prior_scene_id'].split('-')[1])<int(scene['id'].split('-')[1])
 assert all(l['source_refs'] for l in x.logs)
 assert all(m['capacity_ref'] in x.game.core.child._state['developmental_state']['milestones'] for m in x.growth_moments)
 assert len({m['capacity_ref'] for m in x.growth_moments})==len(x.growth_moments)
 texts=[l['text'] for l in x.logs];dups=len(texts)-len(set(texts));assert dups==0,(i,'exact narrative repetition')
 prohibited=['回の記録のうち','交流経験が記録','口座間の資金移動','希望への返答が届いた']
 assert not any(p in l['text'] for p in prohibited for l in x.logs)
 intervals=[b['period']-a['period'] for a,b in zip(x.events,x.events[1:])]
 cat=collections.Counter(e['kind'] for e in x.events);child=sum(l['key'].startswith(('scene/','observed-skill/','growth/','promise/','project/')) for l in x.logs)
 m={'family':i,'age_months':24,'turns':x.month,'events':len(x.events),'categories':dict(cat),'mean_interval':sum(intervals)/len(intervals) if intervals else None,'scenes':len(x.scenes),'genres':sorted(set(s['genre'] for s in x.scenes)),'logs':len(x.logs),'child_or_memory_log_share':child/len(x.logs),'duplicate_texts':dups,'memories':len(x.keepsakes),'cash_checks':checks,'reaction_distribution':dict(collections.Counter(s['reaction_code'] for s in x.scenes))}
 metrics.append(m);families.append({'config':cfg,'final_view':x.view(),'scenes':x.scenes,'events':x.events,'plans':x.plans,'finance':x.finance,'growth_moments':x.growth_moments,'months':x.months,'requests':x.requests,'asset_source':x.initial_trace,'metrics':m})
 (OUT/f'family{i+1:02d}_player_record.md').write_text('# '+cfg['child_name']+'と過ごした24か月\n\n'+'\n\n'.join('### '+l['date']+'｜'+l['title']+'\n\n'+l['text'] for l in x.logs),encoding='utf8')
 print('family',i,m,flush=True)
# Equal child trajectories across all six policies; actual spending/time/context differs.
policies=[]
for policy in POLICIES:
 x=new(seed=3399,initial_cash_yen=5000000,policy=policy);advance(x,24,index=1)
 policies.append({'policy':policy,'effects':effects(x),'biology':biology(x)})
assert len({p['biology'] for p in policies})==1
assert len({digest(p['effects']) for p in policies})==6
# Individuality: only child seed changes; all start A accounts match.
children=[]
for seed in [111,222,333]:
 x=new(seed=3300,child_seed=seed,initial_cash_yen=5000000,policy='stable');a=digest(x.game.core.a['accounts'])
 for _ in range(10):
  t=x.schedule('voice','comparison');x.execute(t)
 children.append({'child_seed':seed,'initial_A':a,'reactions':[e['reaction_code'] for e in x.experiences]})
assert len({c['initial_A'] for c in children})==1
assert len({digest(c['reactions']) for c in children})>1
# Persistence: event, phase clock, deferred plan, private ledger all restored.
x=new(seed=3300,policy='play',initial_cash_yen=5000000);advance(x,7)
if x.current_event:e=x.events[-1];x.choose(e['id'],e['choices'][-1]['id'])
x.open_opportunity('weekend');e=x.events[-1];x.choose(e['id'],e['choices'][0]['id']);x.elapsed_ms=1234
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'save.gz';x.save(p);y=Experience.load(p,E);assert x.snapshot()==y.snapshot()
 before=digest(x.snapshot())
 for _ in range(10):x.view()
 assert digest(x.snapshot())==before
 advance(x,5,index=1);advance(y,5,index=1);assert x.snapshot()==y.snapshot()
# No explicit intervention needed beyond a standing default.
x=new(seed=3304,policy='stable',initial_cash_yen=1000000);advance(x,24);assert len(x.scenes)>20
report={'checks':{'ten_families_24months':True,'meaningful_choice_branches':True,'native_cash_identity':True,'no_added_biological_causality':True,'policy_allocations_differ':True,'child_seed_changes_observed_reactions':True,'same_seed_save_resume':True,'view_no_random_consumption':True,'midmonth_birth_exact_24mo':True,'no_identical_log_texts':True,'no_explicit_action_required':True,'canonical_scene_before_prose':True},'families':metrics,'individuality':children,'branch_events':len(branches),'event_categories':sorted(seen),'human_fun_test':False,'Windows_native_test':False,'external_causal_validation':False}
for name,body in [('verification.json',report),('families_24mo.json',families),('choice_comparisons.json',branches),('policy_comparisons.json',policies)]:
 (OUT/name).write_text(json.dumps(body,ensure_ascii=False,indent=2),encoding='utf8')
print('C3_VERIFICATION_PASS',flush=True)
