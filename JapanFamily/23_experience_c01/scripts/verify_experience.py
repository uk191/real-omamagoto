"""Executable integration checks, using the real A/B engines, never mock results."""
import copy, gzip, hashlib,json,sys,tempfile,time,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from c01.experience import Experience,digest
from c0.bridge import make_engine
from c0.game import Game
OUT=ROOT/'reports';OUT.mkdir(exist_ok=True)
engine=make_engine();checks={};failures=[]
def check(name,fn):
 try:
  result=fn();assert result is not False;checks[name]='passed';print('PASS',name,flush=True)
 except Exception as e:checks[name]='failed';failures.append({'check':name,'error':repr(e)});print('FAIL',name,repr(e),flush=True)

def start(seed='p0-verify',**kw):return Experience.start(engine,seed=seed,child_name='はる',**kw)
def settle(e,policy='normal'):
 for _ in range(25):
  event=e.event()
  if not event:return
  choice=event['options'][0]
  if event['id'].startswith('budget/'):
   choice=next(x for x in event['options'] if x['id']==policy)
  e.choose(event['id'],choice['id'])
 raise AssertionError('endless decision loop')

base=start();check('start_auto_10_seconds',lambda:base.playback=={'running':True,'speed':1,'remaining_ms':10000})
h=digest(base.game.core.payload());[base.view() for _ in range(10)];check('view_does_not_consume_randomness',lambda:digest(base.game.core.payload())==h)
base.advance();check('first_month_pauses_for_real_decision',lambda:base.event()['id']=='allowance' and not base.playback['running'])
try:base.advance();blocked=False
except ValueError:blocked=True
check('cannot_skip_unreviewed_event',lambda:blocked)
base.choose('allowance','apply');check('choice_is_native_request_not_guaranteed_result',lambda:base.game.queue[0]['type']=='apply_child_allowance' and not any(c['kind']=='child_application' for c in base.game.core.a['claims']))
settle(base);base.advance();check('native_claim_submitted_next_month',lambda:any(c['kind']=='child_application' for c in base.game.core.a['claims']))
check('money_flow_reconciles',lambda:base.history[-1]['cash_delta_yen']==base.history[-1]['cash_in_yen']-base.history[-1]['cash_out_yen']+base.history[-1]['asset_transfer_yen']+base.history[-1]['borrowing_yen'])
with tempfile.TemporaryDirectory() as t:
 settle(base);path=Path(t)/'save.gz';base.set_playback(True,4,4321);base.save(path);restored=Experience.load(path,engine)
 check('save_load_exact_state_and_timer',lambda:restored.view()==base.view() and digest(restored.game.core.payload())==digest(base.game.core.payload()))
 settle(base);settle(restored);base.advance();restored.advance()
 check('save_replay_next_month_exact',lambda:restored.view()==base.view())
 data=bytearray(path.read_bytes());data[len(data)//2]^=1;path.write_bytes(data)
 try:Experience.load(path,engine);caught=False
 except Exception:caught=True
 check('damaged_save_rejected',lambda:caught)

# Identical native scenario, actions and seeds remain identical in inherited C0.
x=start('native-compatible');old=Game.start(engine,seed='native-compatible')
for _ in range(4):
 while x.event():
  event=x.event();x.choose(event['id'],'later')
 old.advance(reviewed=bool(old.core.a.get('pending_decisions')));x.advance()
check('unchanged_native_A_B_results',lambda:digest(x.game.core.payload())==digest(old.core.payload()))

families=[('tokyo',dict(prefecture_code='13',environment='urban',conditions={'mother_age':30,'father_age':32,'birth_rank':1,'household_income_yen':6000000})),
 ('single',dict(prefecture_code='01',conditions={'mother_age':25,'partner_present':False,'legal_status':'nonmarital','birth_rank':1})),
 ('rural',dict(prefecture_code='01',environment='rural',conditions={'mother_age':30})),
 ('suburban',dict(prefecture_code='12',environment='suburban',conditions={'birth_rank':1})),
 ('jobs',dict(prefecture_code='27',conditions={'mother_employed':True,'father_employed':True,'mother_occupation':'03','mother_education':'4'})),
 ('lowcash',dict(prefecture_code='40',initial_cash_yen=0,conditions={'mother_age':24,'birth_rank':1})),
 ('highcash',dict(prefecture_code='14',initial_cash_yen=10000000,conditions={'mother_age':35,'birth_rank':2})),
 ('siblings',dict(prefecture_code='47',conditions={'birth_rank':3})),
 ('regional',dict(prefecture_code='20',conditions={'mother_age':29})),
 ('midmonth',dict(prefecture_code='23',birth_date='2026-10-17',conditions={'mother_age':31,'birth_rank':1}))]
results=[]
for label,settings in families:
 e=start('c01-family-'+label,**settings);choices=0
 for key,val in settings.get('conditions',{}).items():
  if key.endswith('_age'):
   who=key.split('_')[0];person=next(p for p in e.game.core.a['persons'] if p['person_id']==who);assert person['age_years']==val
  if key.endswith('_education') or key.endswith('_occupation'):
   who,field=key.split('_');p=next(p for p in e.game.core.a['persons'] if p['person_id']==who)['attributes'];assert p[{'education':'education_coarse','occupation':'occupation_code'}[field]]==val
 if settings.get('environment'):assert e.view()['environment']['class']==settings['environment']
 while not e.game.finished:
  settle(e);before=len(e.logs);e.advance();assert 1<=len(e.logs)-before<=3
  e.game.core.assert_consistent();row=e.game.core.a.get('last_month')
  if row:assert row['ledger']['cash_identity_residual']==row['ledger']['net_worth_identity_residual']==0
 eview=e.view();assert eview['age_months']==24
 reports=e.game.core.child.player_view(e.game.core.identity['person_links']['mother'])['observations'];known={digest(r):r for r in reports}
 for log in e.logs:
  for ref in log['source_refs']:
   if isinstance(ref,dict) and 'report_sha256' in ref:assert known[ref['report_sha256']]['behaviors'][ref['signal']] is True
 with gzip.open(OUT/(label+'_player_history.json.gz'),'wt',encoding='utf-8') as f:json.dump(eview,f,ensure_ascii=False)
 result={'family':label,'date':eview['date'],'calendar_turns':e.month,'logs':len(e.logs),'choices':len(e.choices),'cash_yen':eview['metrics']['cash_yen'],'environment':eview['environment'],'household_id':eview['household']['household_id']}
 results.append(result);print('FAMILY',label,e.month,len(e.logs),flush=True)
check('ten_families_24_months_ids_ledger_logs_provenance',lambda:len(results)==10)

comparisons=[]
for label in ['branch-a','branch-b','branch-c']:
 setting=dict(prefecture_code='13',conditions={'mother_age':30,'father_age':32,'birth_rank':1},initial_cash_yen=5000000)
 branches=[]
 for policy in ['trim','room']:
  e=start(label,**setting)
  while not e.game.finished:settle(e,policy);e.advance()
  branches.append(e)
 a,b=branches
 assert a.game.core.a['accounts']!=b.game.core.a['accounts']
 # Spending changes do not secretly increase hidden child skills.
 child_equal=digest(a.game.core.child._state)==digest(b.game.core.child._state)
 comparisons.append({'family':label,'trim_final_cash':a.history[-1]['cash_yen'],'room_final_cash':b.history[-1]['cash_yen'],'cash_difference_yen':a.history[-1]['cash_yen']-b.history[-1]['cash_yen'],'unpaid_difference_yen':a.history[-1]['unpaid_yen']-b.history[-1]['unpaid_yen'],'recognized_expense_difference_yen':sum(x['recognized_expense_yen'] or 0 for x in a.history)-sum(x['recognized_expense_yen'] or 0 for x in b.history),'child_internal_equal':child_equal,
 'native_effect':'set_spending changes A consumption / cash / liabilities; no identified child causal effect'})
with gzip.open(OUT/'decision_comparison_paths.json.gz','wt',encoding='utf-8') as f:json.dump([b.view() for b in branches],f,ensure_ascii=False)
check('three_policy_branches_change_real_household_state',lambda:all(x['cash_difference_yen']!=0 or x['unpaid_difference_yen']!=0 or x['recognized_expense_difference_yen']!=0 for x in comparisons))
# Scan player payload recursively for scientific state keys (not explanatory prose).
forbidden={'latent_state','initial_dispositions','developmental_state','transition_parameters','random_streams','birth_conditions'}
def keys(x):
 if isinstance(x,dict):
  for k,v in x.items():yield k;yield from keys(v)
 elif isinstance(x,list):
  for v in x:yield from keys(v)
check('no_hidden_child_state_in_player_API',lambda:not forbidden.intersection(keys(e.view())))
(OUT/'integration_verification.json').write_text(json.dumps({'version':'C-0.1-P0.1','checks':checks,'failures':failures,'families':results,'decision_comparisons':comparisons,'test_kind':'developer integration scenarios; not human play evaluation'},ensure_ascii=False,indent=2),encoding='utf-8')
assert not failures,failures
