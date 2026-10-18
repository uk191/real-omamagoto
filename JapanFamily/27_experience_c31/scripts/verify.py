"""Native checkpoints, 16 forks, real 1/3-month outcomes, varied contexts."""
import sys,json,copy,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from c31.model import Experience,digest
from c0.bridge import make_engine
E=make_engine();OUT=R/'reports'
def new(**cfg):return Experience.start(E,policy='stable',**cfg)
def resolve(x,index=0):
 e=x.events[-1];x.choose(e['id'],e['choices'][index%4]['id'])
def advance(x,target,index=0):
 while x.month<target and not x.game.finished:
  if x.current_event:resolve(x,index)
  else:x.tick()
 return x
def biological(x):return digest({k:x.game.core.child._state[k] for k in ['physical_health','latent_state','emotion_regulation','developmental_state','sleep']})
def direct(x,c):
 f=x.case_effects(c);ex=[e for e in x.experiences if e['id'] in f['experience_ids']]
 # Ignore event/choice/text IDs when asserting meaningful differences.
 signature={'expenses':f['expenses_yen'],'cash':f['cash_delta_direct'],'term':f['term_delta_direct'],'hours':f['hours_used'],'kinds':[e['kind'] for e in ex],'requests':[(q['kind'],q['value']) for q in x.requests if q['source']==c['event_id']],'projects':[(p['format'],p['status']) for p in f['projects']],'agency':[(t['offered'],t['chosen']) for t in x.agency_trials if t['case_id']==c['id']]}
 return {'effects':f,'signature':signature,'state':x.context(),'experiences':copy.deepcopy(ex),'operations':copy.deepcopy([o for o in x.commitments if o['case_id']==c['id']]),'biology':biological(x)}
branches=[];fixtures=[]
x=new(seed=4402,prefecture_code='13',conditions={'father_age':32,'mother_age':30})
while not x.game.finished:
 if not x.current_event:x.tick();continue
 e=copy.deepcopy(x.events[-1]);code=e['domain']
 if not e.get('parent_case_id'):
  checkpoint=x.clone();out=[]
  for i,c in enumerate(e['choices']):
   b=checkpoint.clone();b.choose(e['id'],c['id']);case=b.case_ledger[-1];now=direct(b,case);start=b.month
   # Save/resume including pending operations: exact result in both paths.
   with tempfile.TemporaryDirectory() as t:
    p=Path(t)/'save.gz';b.save(p);again=Experience.load(p,E);assert b.snapshot()==again.snapshot()
    advance(b,start+1);advance(again,start+1);assert b.snapshot()==again.snapshot()
   one=direct(b,case);advance(b,start+3)
   if not b.current_event and not b.game.finished and b.phase==0:b.tick()
   three=direct(b,case)
   follow=next(z for z in b.events if z.get('parent_case_id')==case['id'])
   assert follow['background']!=e['background'] and follow['source_refs']
   assert not any(op['status']=='planned' and op['due_period']<b.month for op in b.commitments)
   assert all(b.financial_view()['cash_identity_residual'] in [0,None] for _ in [0])
   out.append({'choice':c,'immediate':now,'one_month':one,'three_months':three,'followup':copy.deepcopy(follow),'followup_result':direct(b,next(c for c in b.case_ledger if c['id']==follow['case_id'])),'last_logs':copy.deepcopy(b.logs[-9:])})
  assert len({digest(o['three_months']['signature']) for o in out})==4,(code,'dummy consequence')
  assert len({o['three_months']['biology'] for o in out})==1,(code,'invented biological effect')
  assert len({o['followup']['background'] for o in out})==4,(code,'no conditional followup')
  branches.append({'domain':code,'checkpoint':checkpoint.context(),'event':e,'outcomes':out})
 resolve(x)
assert len(branches)==4 and len(x.events)==8
# Other actual households: no manual income/cash, including single parent/midmonth.
for i,cfg in enumerate([
 dict(seed=11,prefecture_code='01',conditions={'father_age':23,'mother_age':22},neighborhood='rural'),
 dict(seed=12,prefecture_code='27',conditions={'father_age':41,'mother_age':38},neighborhood='suburban'),
 dict(seed=13,prefecture_code='47',conditions={'mother_age':25,'partner_present':False},role='mother'),
 dict(seed=14,prefecture_code='20',conditions={'father_age':35,'mother_age':31},birth_date='2026-10-17'),
 dict(seed=15,prefecture_code='40',conditions={'father_age':29,'mother_age':27,'father_education':'4','mother_education':'2'})]):
 b=new(**cfg);initial=digest(b.game.core.initial_a)
 advance(b,25,index=i%4)
 assert b.game.core.elapsed_months==24 and digest(b.game.core.initial_a)==initial
 assert set(b.main_seen)==set('ABCD'),(cfg,b.main_seen)
 assert all(len(e['choices'])==4 for e in b.events)
 assert all(r['check']['cash_identity_residual']==r['check']['net_worth_identity_residual']==0 for r in b.finance)
 b.game.core.assert_consistent()
 fixtures.append({'settings':cfg,'events':b.events,'cases':b.case_ledger,'operations':b.commitments,'effects':[b.case_effects(c) for c in b.case_ledger],'final_view':b.view()})
 (OUT/f'family_{i+1}_player_log.md').write_text('# '+str(cfg['seed'])+' の24か月\n\n'+'\n\n'.join(l['date']+'｜'+l['title']+'\n\n'+l['text'] for l in b.logs),encoding='utf8')
# Existing C3 saved games import without mutation to original.
from c3.model import Experience as Old
old=Old.start(E,seed=77,policy='stable');advance(old,2)
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'old.gz';old.save(p);h=p.read_bytes();m=Experience.load(p,E);assert p.read_bytes()==h
 assert m.game.core.a==old.game.core.a and m.game.core.child._state==old.game.core.child._state
 advance(m,24);assert m.game.finished
# Inspection purity after real pending decisions and after completion.
h=digest(x.snapshot());x.view();x.view();assert h==digest(x.snapshot())
(OUT/'sixteen_branches.json').write_text(json.dumps(branches,ensure_ascii=False,indent=2))
(OUT/'varied_households.json').write_text(json.dumps(fixtures,ensure_ascii=False,indent=2))
r={'sixteen_branches':len(branches)*4,'distinct_real_outcomes_each':True,'followup_context_depends_on_choice':True,'no_added_B_biology_effect':True,'pending_save_resume_exact':True,'additional_native_households_24mo':len(fixtures),'midmonth_birth':True,'C3_save_import':True,'view_pure':True,'A_B_originals_unchanged':True,'human_fun_test':False,'Windows_native_test':False}
(OUT/'verification.json').write_text(json.dumps(r,indent=2));print('C31_VERIFICATION_PASS',r)
