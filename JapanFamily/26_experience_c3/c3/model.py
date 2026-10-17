"""Low-load orchestration. No edits to inherited A/B or scientific coefficients.
Policies authorize own recurring actions, never control a partner's employment.
Facts are deduplicated by structured semantic keys before Japanese rendering.
"""
import copy,datetime as dt,gzip,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'24_experience_c1'))
from c1.experience import Previous,Game,restore_game,u,yen,LABELS,digest
from c01.experience import Experience as FamilyStart,cash_label
from c0.catalogue import PREFECTURES,EMPLOYMENT
from . import VERSION
EMPLOYMENT={**EMPLOYMENT,'working_care_constrained':'育児に合わせて実働を調整中','contract_no_paid_work':'雇用先はあるが実働・給与がない状態'}
POLICIES={
 'work':{'name':'仕事と収入','hint':'自分の通常勤務を希望。仕事の準備に月8時間を確保し、家では声かけ。収入増を保証しません。'},
 'time':{'name':'子どもとの時間','hint':'自分の勤務を8割で相談。月4回を目安に、家で過ごす時間を計画。実現後は給与が減る可能性。'},
 'play':{'name':'遊びと体験','hint':'月3,000円を上限に絵本・玩具と外出。支払い口座と予定枠が足りる範囲で実行。'},
 'stable':{'name':'安定した暮らし','hint':'今の働き方を保ち、家での声かけ・写真・食事などを中心に過ごす。'},
 'save':{'name':'貯蓄をつくる','hint':'直近の支払い2か月分を残し、余裕があれば月2万円まで定期性預貯金へ。運用益は追加しません。'},
 'social':{'name':'家族と交流','hint':'月1,500円までで親子の場所・公園へ。家族の分担も相談し、見送りも記録する。'},
}
from .catalogue import ACTS
from .scenes import build_scene,render_scene
class Experience:
 @classmethod
 def start(cls,engine,**settings):
  actor=settings.pop('role','father');policy=settings.pop('policy',None);neighborhood=settings.pop('neighborhood','city')
  if neighborhood not in ['city','suburban','rural']:raise ValueError('外出の生活設定を選んでください。')
  if actor not in ['father','mother'] or policy not in [None,*POLICIES]:raise ValueError('主人公と生活方針を選んでください。')
  allowed={'prefecture_code','seed','birth_date','conditions','child_name','father_name','mother_name','initial_cash_yen','child_seed','background'}
  if set(settings)-allowed:raise ValueError('指定できない開始条件です。')
  for k in ['father_name','mother_name','background']:
   if not isinstance(settings.get(k,''),str) or len(settings.get(k,''))>(600 if k=='background' else 24):raise ValueError('名前・経歴を確認してください。')
  cond=copy.deepcopy(settings.get('conditions') or {});cond.setdefault('partner_present',True)
  if actor=='father' and not cond['partner_present']:raise ValueError('同居する父親がいない家庭では母親を主人公に選んでください。')
  args={k:v for k,v in settings.items() if k in ['prefecture_code','seed','birth_date','conditions','child_name','initial_cash_yen']};args['conditions']=cond;args.setdefault('seed',0)
  old=FamilyStart.start(engine,**args);obj=cls();obj.game=old.game
  if settings.get('child_seed') is not None:obj.game=Game.start(engine,prefecture_code=args.get('prefecture_code','13'),seed=args['seed'],birth_date=args.get('birth_date','2026-10-01'),conditions=cond,child_name=args.get('child_name','はる'),child_seed=settings['child_seed'],research_scenario=obj.game.config['research_scenario'])
  if actor not in obj.game.core.a['parents']:raise ValueError('この家庭には選んだ主人公が同居していません。')
  obj.actor=actor;obj.partner=next((p for p in obj.game.core.a['parents'] if p!=actor),None);obj.settings=copy.deepcopy(settings);obj.settings['conditions']=cond
  obj.settings['neighborhood']=neighborhood
  obj.names={k:settings.get(k+'_name') or old.names[k] for k in obj.game.core.a['parents']}
  obj.revision=0;obj.phase=0;obj.running=False;obj.speed=1;obj.elapsed_ms=0;obj.policy=None;obj.policy_history=[];obj.month_prepared=-1
  obj.logs=[];obj.fact_ledger=[];obj.semantic_last={};obj.pending_facts=[];obj.suppressed=[];obj.tasks=[];obj.inventory={};obj.experiences=[];obj.finance=[];obj.time_used={};obj.requests=[];obj.events=[];obj.current_event=None;obj.last_event_month=0;obj.event_cooldown={};obj.months=[];obj.observed_signals={};obj.envelopes=[];obj.partner_history=[];obj.policy_operations=[]
  obj.initial_accounts=copy.deepcopy(obj.game.core.a['accounts']);obj.initial_trace=copy.deepcopy(obj.game.core.a['initial_family']['automatic_accounts']['trace'])
  obj.growth_moments=[];obj.administrative_facts=[];obj.scenes=[];obj.plans=[];obj.keepsakes=[];obj.interests={};obj.opportunity_month=-1;obj.scene_semantics={};obj.work_preference_override=None
  obj.npc_wish='quiet' if u(args['seed'],'C3partner')<.5 else 'outdoor'
  if policy:obj.set_policy(policy)
  return obj
 @property
 def date(self):return self.game.core.child._state['as_of_date']
 @property
 def month(self):return len(self.game.turns)
 def clone(self):
  obj=copy.copy(self);obj.__dict__.update(copy.deepcopy({k:v for k,v in self.__dict__.items() if k!='game'}));obj.game=self.game.clone();obj.game.core.a=copy.deepcopy(self.game.core.a);return obj
 def fact(self,key,title,text,refs,evidence,*,permanent=False,cooldown=6,links=None):
  if key.startswith(('saving-','pattern/','transfer/','envelope/','reserve-underfunded')):
   self.administrative_facts.append({'key':key,'date':self.date,'text':text,'source_refs':refs,'evidence':evidence});return
  if key.startswith('decision/'):
   title='仕事や暮らしの予定が動いた'
   # Keep exact native outcomes; remove repeated machine-facing observation footer.
   text=text.split(' 実働は週')[0].replace('の希望に返答。','が相談していた件について、')
  if key.startswith('observed-skill/'):
   name=self.game.config['child_name'];actor=self.names[self.actor];signal=key.split('/')[-1]
   moment=next((m for m in self.growth_moments if m.get('source_signal')==signal),None)
   if not moment:
    word='ぱぱ' if self.actor=='father' else 'まま'
    title='こちらを向いて、「'+word+'」' if signal=='uses_contextual_word' else '抱いて運んでいた場所を、自分の足で'
    text=(actor+'がそばで声をかけると、'+name+'はこちらを向いて「'+word+'」と言った。'+actor+'がもう一度顔を近づけて待つと、今度は口を動かすだけだった。今日は、その一度を覚えておく。' if signal=='uses_contextual_word' else actor+'が床の少し先で待っていると、'+name+'が支えなしに足を運んできた。'+actor+'は手を伸ばせる所にしゃがみ、近づいてくる姿をそのまま待っていた。')
    moment={'id':f'growth-{len(self.growth_moments):03d}','date':self.date,'period':self.month,'capacity_ref':'first_contextual_word' if signal=='uses_contextual_word' else 'walking_independently','source_signal':signal,'title':title,'text':text,'word':word if signal=='uses_contextual_word' else None,'source_refs':copy.deepcopy(refs),'evidence':'native_positive_caregiver_report_plus_C3_fictional_scene_and_lexeme','not_exact_onset_date':True}
    self.growth_moments.append(moment)
    self.keepsakes.append({'id':f'memory-{len(self.keepsakes):04d}','date':self.date,'title':title,'scene_id':None,'growth_id':moment['id'],'experience_id':None,'text':text,'item_id':None})
   title=moment['title'];text=moment['text'];refs=['C3.growth_moments/'+moment['id']];evidence=moment['evidence']
  rec={'id':f'fact-{len(self.fact_ledger):05d}','key':key,'title':title,'text':text,'date':self.date,'period':self.month,'phase':self.phase,'source_refs':refs,'evidence':evidence,'links':links or []};self.fact_ledger.append(copy.deepcopy(rec))
  if any(r['text']==text for r in self.logs+self.pending_facts):self.suppressed.append({'fact_id':rec['id'],'reason':'same_visible_scene_despite_different_latent_draw','key':key});return
  seen=self.semantic_last.get(key)
  if seen is not None and (permanent or self.month-seen<cooldown):self.suppressed.append({'fact_id':rec['id'],'reason':'known_semantic_fact','key':key});return
  # Same reaction recurring in the same place never becomes news just by rewording.
  self.semantic_last[key]=self.month;self.pending_facts.append(rec)
 def flush(self):
  occupied=sum(x.get('published_period',x['period'])==self.month for x in self.logs)
  while self.pending_facts and occupied<3:
   r=self.pending_facts.pop(0);r.update(published_date=self.date,published_phase=self.phase,published_period=self.month)
   # Explicitly update by ID. JSON cannot preserve Python shared-object identity.
   next(f for f in self.fact_ledger if f['id']==r['id']).update(copy.deepcopy(r))
   self.logs.append(copy.deepcopy(r));occupied+=1
 def budget(self):
  a=self.game.core.a;row=a.get('last_month');t=(row or {}).get('time',{}).get('parents',{}).get(self.actor)
  if t:care=t['active_care']*4;rest=t['rest']*4;basis='直近の週時間配分×4週を計画枠に使う仮定'
  else:
   p=a['parents'][self.actor];w=p['normal_weekly_hours'] if p['state']=='working' else 0;care=112;rest=max(0,168-56-w-5-28-14)*4;basis='初期の通常勤務からの計画枠（未校正）'
  return {'care':max(0,care-self.time_used.get('care',0)),'rest':max(0,rest-self.time_used.get('rest',0)),'used':copy.deepcopy(self.time_used),'basis':basis}
 def essential(self):
  row=self.game.core.a.get('last_month')
  return int((row['consumption']+row['rent']+(row.get('care_fee') or {}).get('cash_charge',0)) if row else self.game.core.a['base_consumption'])
 def held_cash(self):return sum(x['remaining_yen'] for x in self.envelopes if x['status']=='active')
 def transfer(self,kind,n,ref):
  assert self.game.core.forecast is None
  if type(n) is not int or n<0:raise ValueError('金額を確認してください。')
  from ledger import Ledger
  a=self.game.core.a;l=Ledger(a['accounts'],self.date)
  if kind=='expense':
   if a['accounts']['cash']<n:raise ValueError('支払い口座が足りないため実行していません。')
   l.expense_due('C3/'+ref,n,{'source':'C3_explicit_price_scenario','reference':ref});l.pay('L:AP:C3/'+ref,n)
  else:
   src,dst=('term','cash') if kind=='withdraw' else ('cash','term')
   if a['accounts'].get(src,0)<n:raise ValueError('振替元の残高が足りません。')
   l.transfer(src,dst,n)
  r={'id':f'finance-{len(self.finance):05d}','date':self.date,'period':self.month,'ref':ref,'kind':kind,'entries':copy.deepcopy(l.entries),'check':l.check()};self.finance.append(r);return r
 def own_request(self,kind,value=None,source=None):
  if any(a['type']==kind and a.get('person')==(self.actor if kind in ['request_hours','take_leave','request_return','job_search','accept_job_offer','reject_job_offer'] else None) for a in self.game.queue):return None
  who=self.actor if kind in ['request_hours','take_leave','request_return','job_search','accept_job_offer','reject_job_offer'] else None
  if source and source.startswith('policy/') and any(r.get('source')==source and r.get('kind')==kind and r.get('value')==value and r.get('policy_epoch')==len(self.policy_history) for r in self.requests):return None
  if self.budget()['rest']<.5:return None
  self.game.request(kind,person=who,value=value);self.time_used['rest']=self.time_used.get('rest',0)+.5
  r={'id':self.game.queue[-1]['id'],'date':self.date,'kind':kind,'value':value,'actor':self.actor,'source':source,'time_hours':.5,'policy_epoch':len(self.policy_history),'status':'requested','results':[]};self.requests.append(r);return r
 def set_policy(self,kind):
  if kind not in POLICIES:raise ValueError('生活方針を選んでください。')
  if self.game.finished:raise ValueError('24か月の体験は終了しています。')
  if kind!=self.policy:
   previous=self.policy;self.policy=kind;self.work_preference_override=None;self.policy_history.append({'date':self.date,'period':self.month,'from':previous,'to':kind})
   # Cancel only unexecuted policy tasks, not committed event choices.
   for t in self.tasks:
    if t['status']=='queued' and t['source']=='policy':t['status']='cancelled_policy_change'
   self.month_prepared=-1
  self.running=not bool(self.current_event);self.revision+=1
 def schedule(self,kind,source='policy',event_id=None):
  q=self.quote_activity(kind);q['kind']=kind
  if self.game.core.elapsed_months<q['min_age']:return None
  r={'id':f'task-{len(self.tasks):05d}','date_requested':self.date,'period':self.month,'kind':kind,'quote':q,'source':source,'event_id':event_id,'status':'queued'};self.tasks.append(r);return r
 def prepare_policy(self):
  if self.month_prepared==self.month or not self.policy:return
  self.month_prepared=self.month;a=self.game.core.a;p=a['parents'][self.actor];key=self.policy;age=self.game.core.elapsed_months
  if key in ['time','work'] and self.work_preference_override is None:
   ratio=.8 if key=='time' else 1.
   if p.get('employee_contract') and p['hours_ratio']!=ratio:self.own_request('request_hours',ratio,'policy/'+key)
   if key=='work' and p['state']=='nonemployed' and not p.get('job_search'):self.own_request('job_search',source='policy/work')
  if key=='work':
   hours=min(8,self.budget()['rest']);self.time_used['rest']=self.time_used.get('rest',0)+hours
   self.policy_operations.append({'period':self.month,'kind':'work_preparation_reserved','hours':hours,'evidence':'C3_time_allocation_scenario_no_extra_income'})
  if key=='save':
   amount=max(0,min(20000,a['accounts']['cash']-2*self.essential()-self.held_cash()))
   if amount:
    r=self.transfer('saving',amount,'policy-saving-'+str(self.month));self.policy_operations.append({'period':self.month,'kind':'saving','yen':amount,'finance_id':r['id']})
  # Deferred promises are executed before discretionary standing-policy activities.
  for plan in self.plans:
   if plan['status']=='planned' and self.month>=plan['due_period'] and self.date>=plan['due_date']:
    plan['status']='attempting';t=self.schedule(plan['kind'],'promise',plan['event_id']);plan['task_id']=t['id'] if t else None
    if t:t['plan_id']=plan['id']
    else:plan['status']='not_realized';plan['reason']='対象月齢の条件を満たさない'
  pools={'work':['voice','photo','mirror'], 'time':['floor','cloth','book','voice'], 'play':['book','toy','music','blocks','center','train','mirror'], 'stable':['voice','meal','photo','floor'], 'save':['voice','floor','leaves','photo'], 'social':['center','park','handover','cloth']}
  eligible=[k for k in pools[key] if age>=ACTS[k]['min_age'] and (k!='handover' or self.partner)]
  # History, not a new synonymous sentence, determines the next real activity.
  weights=[]
  for k in eligible:
   last=max((e['period'] for e in self.experiences if e['kind']==k),default=-4)
   count=sum(e['kind']==k for e in self.experiences)
   interest=self.interests.get(k,{}).get('observed_engagements',0)
   weights.append((min(5,self.month-last)+min(2,interest)*.15+u(self.settings.get('seed'),self.month,key,k),k))
  chosen=[k for _,k in sorted(weights,reverse=True)[:4 if key=='time' else 2 if key!='work' else 1]]
  if not chosen:chosen=['voice']
  if key=='time':chosen=(chosen*4)[:4]
  for k in chosen:self.schedule(k)

 def execute(self,t):
  from .catalogue import ITEM_NAMES
  q=t['quote'];kind=t['kind'];reason=None;actor=self.names[self.actor];child=self.game.config['child_name']
  if self.budget()[q['bucket']]<q['hours']:reason='仕事やほかの予定と重なり、使える時間を確保できなかった'
  cash=self.game.core.a['accounts']['cash'];limit=3000 if self.policy=='play' else 1500 if self.policy=='social' else cash
  spent=sum(r['paid_yen'] for r in self.experiences if r['period']==self.month and r['source']=='policy')
  if t['source']=='policy' and q['cost']>max(0,limit-spent):reason='今月、この過ごし方に使うと決めた予算を超える'
  if q['cost']>cash:reason='生活の支払い口座から費用を出せなかった'
  if q.get('agreement') and self.partner and kind in ['trip','submission']:
   if self.game.core.a['parents'][self.partner]['state']=='maternity' and kind=='trip':reason=self.names[self.partner]+'が、産後休業中の泊まりは見送りたいと伝えた'
   elif kind=='trip' and self.npc_wish=='quiet' and not any(e['kind']=='handover' for e in self.experiences):reason=self.names[self.partner]+'が、先に休める日を作りたいと伝えた'
   elif kind=='submission' and self.npc_wish=='quiet':reason=self.names[self.partner]+'が、子どもの写真は家族の中で残したいと伝えた'
  if kind=='handover' and not self.partner:reason='交代する同居の配偶者がいない'
  # Outdoor and overnight disruptions affect actual itinerary, not biological development.
  disruption=kind in ['trip','zoo','leaves'] and u(self.settings.get('seed'),'C3_weather',self.date,t['id'])<.13
  if disruption:reason='出発前に雨が強まり、屋外の予定を延期することにした'
  if reason:
   t.update(status='not_realized',reason=reason)
   if t.get('plan_id'):
    plan=next(p for p in self.plans if p['id']==t['plan_id']);plan.update(status='not_realized',reason=reason)
   if t['source']!='policy':
    self.fact('blocked/'+kind+'/'+str(self.month),'予定どおりにいかない日',actor+'の「'+q['title']+'」は、'+reason+'。支払いはせず、今月は見送った。',['C3.tasks/'+t['id']],'C3_resource_or_fictional_logistics',permanent=True)
   return t
  paid=self.transfer('expense',q['cost'],t['id']) if q['cost'] else None
  remaining=q['cost']
  for envelope in self.envelopes:
   used=min(remaining,envelope['remaining_yen']);envelope['remaining_yen']-=used;remaining-=used
   if not envelope['remaining_yen']:envelope['status']='used'
  item=None
  if q.get('item'):
   if q['item'] not in self.inventory:self.inventory[q['item']]={'id':'item-'+q['item'],'name':ITEM_NAMES[q['item']],'acquired':self.date,'source_task':t['id'],'cost_yen':q['cost']}
   item=self.inventory[q['item']]
  past=[e for e in self.experiences if e['kind']==kind];scene=build_scene(self,t,past,item)
  self.time_used[q['bucket']]=self.time_used.get(q['bucket'],0)+scene['actual_hours']
  exp={'id':f'experience-{len(self.experiences):05d}','task_id':t['id'],'scene_id':scene['id'],'period':self.month,'date':self.date,'age_days':scene['age_days'],'kind':kind,'place':q['place'],'participants':scene['participant_ids'],'item_id':scene['item_id'],'item_name':item['name'] if item else None,'prior_experience_id':past[-1]['id'] if past else None,'reaction':scene['beats'][-2 if past and scene['beats'][-1]['code']=='continuity' else -1]['text'],'short_observation':scene['short_observation'],'reaction_code':scene['reaction_code'],'hours':scene['actual_hours'],'paid_yen':q['cost'],'finance_id':paid['id'] if paid else None,'source':t['source'],'event_id':t['event_id'],'evidence':scene['research_status'],'long_term_effect':False}
  scene['experience_id']=exp['id'];self.scenes.append(scene);self.experiences.append(exp)
  t.update(status='done',experience_id=exp['id'],scene_id=scene['id'],paid_yen=q['cost'],hours=scene['actual_hours'])
  if t.get('plan_id'):next(p for p in self.plans if p['id']==t['plan_id']).update(status=scene['status'],experience_id=exp['id'])
  if kind=='handover':self.partner_history.append({'date':self.date,'period':self.month,'source_task':t['id'],'person':self.partner,'hours':2,'action':'ひとりで静かに休む' if self.npc_wish=='quiet' else '近所をひとりで歩く','evidence':'C3_NPC_schedule_assumption'})
  interest=self.interests.setdefault(kind,{'observed_engagements':0,'experience_ids':[]})
  interest['observed_engagements']+=int(scene['reaction_code'] in ['watch','reach']);interest['experience_ids'].append(exp['id'])
  if kind in ['photo','birthday','birthday_free','trip','aquarium','submission'] or not past or t['source']!='policy':
   self.keepsakes.append({'id':f'memory-{len(self.keepsakes):04d}','date':self.date,'title':q['title'],'scene_id':scene['id'],'experience_id':exp['id'],'text':render_scene(scene),'item_id':scene['item_id']})
  if kind=='submission':
   self.plans.append({'id':f'plan-{len(self.plans):04d}','kind':'submission_result','date':self.date,'due_date':self.date,'due_period':self.month+1,'event_id':t['event_id'],'status':'awaiting_result','source_scene_id':scene['id']})
  semantic=digest(scene['semantic_signature'])
  title={'book':'読むつもりが、めくる時間に' if scene['reaction_code']=='reach' else 'ひざの上の一冊','blocks':'積む人と、崩す人','aquarium':'水槽の前で、足が止まった','photo':'撮り直さなかった一枚','birthday':'小さな誕生日','birthday_free':'歌と、一枚の写真','trip':'いつもと違う窓','music':'音が止まった、そのあと','meal':'スプーンを待つ間','submission':'この一枚で、応募してみる'}.get(kind,q['title'])
  self.fact('scene/'+semantic,title,render_scene(scene),['C3.scenes/'+scene['id'],'C3.experiences/'+exp['id']]+(['C3.scenes/'+scene['prior_scene_id']] if scene['prior_scene_id'] else []),scene['research_status'],permanent=True,links=[t['event_id']] if t['event_id'] else [])
  return t

 def observe_new(self):
  self.game.observe('observe',observer=self.actor)
  reports=self.game.core.child.player_view(self.game.core.identity['person_links'][self.actor])['observations']
  # Only reported positive skills can produce attainment news, never latent thresholds.
  for signal,title in [('takes_independent_steps','ひとりで足を運ぶ姿'),('uses_contextual_word','場面に合う言葉')]:
   positives=[r for r in reports if r['behaviors'].get(signal)]
   if positives and signal not in self.observed_signals:
    self.observed_signals[signal]={'date':positives[0]['date'],'report_sha256':digest(positives[0])}
    self.fact('observed-skill/'+signal,'親の記録に初めて残ったこと',f'{self.names[self.actor]}の観察に、{self.game.config["child_name"]}の「{title}」が初めて残った。観察した場面の記録で、診断や正確な獲得日ではない。',['B.player_view/'+self.actor+'/'+signal],'B_report_model_not_diagnosis',permanent=True)
  # Additional caregiver scenes can reveal five inherited B capacities.
  # Existence of a latent capacity alone never makes it known to the player.
  capabilities=self.game.core.child._state['developmental_state']['milestones']
  opportunities=any(t['status']=='done' and t['period']==self.month for t in self.tasks)
  actor=self.names[self.actor];child=self.game.config['child_name']
  definitions={
   'head_control':('抱き方が、少し変わった',actor+'が縦に抱いているとき、'+child+'が自分で首を支えて顔を上げていた。'+actor+'は支える手を添えたまま、正面からその顔を見た。'),
   'rolling':('敷物の上で、向きが変わった',actor+'がそばに座っていると、'+child+'の体が横を向き、そのままころんと回った。さっきまで見ていた天井とは、違う方を向いている。'+actor+'は床の小物を遠ざけて、そばに座り直した。'),
   'sitting_unsupported':('両手が、空いた',actor+'が床でそばにいるとき、'+child+'は手で支えずに座っていた。両手を前に出せる姿を、今日は落ち着いて眺められた。'),
   'crawling':('待っている場所へ',actor+'が床の少し先で声をかけると、'+child+'が腹ばいで前へ進んできた。抱いて近づける代わりに、今日はその場所で待っていた。'),
   'standing_with_support':('つかまった手の、その先',actor+'がそばで見ていると、'+child+'が低い台に手をかけて立ち上がった。高さの変わった目線で辺りを見回す間、'+actor+'は手の届く所にいた。')}
  for skill,(title,text) in definitions.items():
   if opportunities and skill in capabilities and skill not in self.observed_signals and u(self.game.core.child._state['random_streams']['seed'],'C3_growth_opportunity',self.date,skill)<.65:
    moment={'id':f'growth-{len(self.growth_moments):03d}','date':self.date,'period':self.month,'capacity_ref':skill,'participant_ids':[self.game.core.identity['person_links'][self.actor],self.game.core.identity['index_global_person_id']],'title':title,'text':text,'source_refs':['B.developmental_state.milestones/'+skill],'evidence':'B11_report_proxy_capacity_plus_C3_unvalidated_observation_opportunity_0.65','not_exact_onset_date':True}
    self.growth_moments.append(moment);self.observed_signals[skill]={'date':self.date,'growth_id':moment['id']}
    self.fact('growth/'+skill,title,text,['C3.growth_moments/'+moment['id']],moment['evidence'],permanent=True)
    self.keepsakes.append({'id':f'memory-{len(self.keepsakes):04d}','date':self.date,'title':title,'scene_id':None,'growth_id':moment['id'],'experience_id':None,'text':text,'item_id':None})
    break
 def quote_activity(self,k):
  q=copy.deepcopy(ACTS[k])
  if q['bucket']=='rest' and k in ['park','center','aquarium','zoo','train','leaves','trip']:
   h,y={'city':(0,0),'suburban':(.5,300),'rural':(1.,600)}[self.settings.get('neighborhood','city')];q['hours']+=h;q['cost']+=y;q['transport_scenario']=self.settings.get('neighborhood','city')
  if q.get('item') in self.inventory:q['cost']=0
  if q['bucket']=='care' and self.budget()['care']<q['hours'] and self.budget()['rest']>=q['hours']:q['bucket']='rest'
  return q
 def quote_choice(self,kind,*,plan=False):
  probe=self.quote_activity(kind);q=probe;cost=q['cost']
  detail={'book':'この絵本を手元に置き、何度でも一緒に開ける。ページを読めるとは限らない。','toy':'布のボールが家の持ち物になる。その場で転がし、子どもの反応を見てみる。','music':'小さな鈴を一緒に鳴らす。音が止まったあとも、少し待ってみる。','blocks':'積み木を家に用意し、まず大人が積んでみる。子どもが同じように積めるとは限らない。','photo':'撮れた一枚をアルバムへ。きちんと正面を向いた写真になるとは限らない。','submission':'家族写真を一枚残して、架空の企画へ応募する。合意できなければ家族内に残す。','meal':'いつもの食事のそばに座る。急がせずに休みを入れる場面をつくる。','park':'お金をかける遠出の代わりに、近くで足を止めて過ごす。移動費は生活設定による。','voice':'新しい買い物をせず、抱っこしてゆっくり話しかける。','handover':'自分の時間を使い、配偶者がひとりで休む・散歩する時間をつくる。'}.get(kind,'この子と一緒に過ごす時間をつくる。興味を示すか、途中で休むかは、その日になってから。')
  return {'id':kind,'title':q['title'],'mode':'plan' if plan else 'activity','kind':kind,'value':None,'cost_yen':cost,'hours':q['hours'],'detail':('来月の予定にする。当日の時間・残高・家族の都合を確認し、実行できたときだけ支払う。' if plan else detail),'transfer_yen':0}
 def available(self,k):
  q=self.quote_activity(k);return self.game.core.elapsed_months>=q['min_age'] and (k!='handover' or bool(self.partner)) and self.game.core.a['accounts']['cash']>=(0 if q.get('item') in self.inventory else q['cost']) and self.budget()[q['bucket']]>=q['hours']
 def activity_options(self,kinds):return [self.quote_choice(k,plan=k in ['trip','aquarium','zoo']) for k in kinds if self.available(k)]
 def event_candidates(self):
  from .catalogue import THEMES
  age=self.game.core.elapsed_months;a=self.game.core.a;c=[];child=self.game.config['child_name']
  def add(kind,priority,title,background,kinds):
   opts=self.activity_options(kinds)
   if len(opts)>=2:c.append((kind,priority,title,background,opts))
  # Birthdays refer to the next actual birthday, not a fixed accomplishment.
  if 10<=age<=11 or 22<=age<=23:
   target=1 if age<12 else 2
   if not any(p.get('birthday_year')==target for p in self.plans):
    opts=self.activity_options(['birthday','birthday_free','photo'])
    for o in opts:
     if o['kind'] in ['birthday','birthday_free']:o['mode']='plan';o['birthday_year']=target;o['detail']='誕生日以降の最初の生活場面に実行する予定。お祝いの方法と費用が残る。'
    if len(opts)>=2:c.append(('birthday',95,'もうすぐ、'+str(target)+'歳',child+'の誕生日が近づいてきた。家の中で祝うのか、写真と歌を残すのか。大きく見せるより、この家族の一日にしたい。',opts))
  recent=self.scenes[-1] if self.scenes else None
  if recent and recent['reaction_code'] in ['watch','reach','unexpected']:
   kind=recent['kind'];opts=['music','book','toy','mirror'] if kind not in ['aquarium','zoo','trip','park'] else ['aquarium','zoo','train','park']
   add('interest',62,'さっきの顔を、もう一度見たい',next(b['text'] for b in reversed(recent['beats']) if b['code']!='continuity')+' 似たことをもう一度試すか、別のものを見せてみようか。',opts)
  trips=[e for e in self.experiences if e['kind'] in ['aquarium','zoo','trip']]
  old=next((e for e in reversed(trips) if self.month-e['period']>=4),None)
  if old and not any(p['kind']==old['kind'] and p['status']=='planned' for p in self.plans):add('revisit',76,'あの日の場所へ、もう一度',old['date'][:7]+'、'+old['place']+'では'+old['short_observation']+'。月日がたった今、同じ場所ではどんな顔を見せるだろう。',[old['kind'],'park','photo'])
  if age>=6:add('outing',60,'次の休日、少し遠くへ',self.names[self.actor]+'の今月の空き予定枠は'+str(round(self.budget()['rest'],1))+'時間。遠出には移動も休憩も必要だけれど、いつもと違う景色を一緒に見に行ける。',['aquarium','zoo','train','park'])
  add('gift',58,'この子に、何を用意しよう',child+'と過ごす家の時間。買うだけで気に入るとは限らない。手元の物で遊ぶ時間と、新しい道具を選ぶ時間を考える。',['blocks','music','book','toy','cloth','voice'])
  if age>=3:add('challenge',54,'家族の写真、外にも残してみる？','架空の「こもれび家族写真展」では、家族の日常写真を募っている。応募は無料、子どもの顔が展示される想定なので配偶者がいれば相談が必要。選考はゲーム内の抽選で、容姿・能力評価ではない。',['submission','photo','book'])
  if age>=6:add('food',50,'食卓で、一緒に待つ時間',child+'との食事は予定どおりにいかないこともある。今日は急がずそばで過ごすか、食後の遊びを用意しようか。具体的な献立・量・安全性はこのモデルでは判定しない。',['meal','book','voice'])
  season=int(self.date[5:7]);add('season',52,'窓の外の季節を、一緒に',('暑さを避けて短い外出にするか、家の中で過ごすか。' if season in [6,7,8] else '外の空気を感じる短い散歩か、家の中で過ごす休日か。')+' 施設名・気象・移動条件は架空の生活設定。',['leaves','center','park','photo'])
  if self.partner:add('family',49,'二人の休日を、少しずつ',self.names[self.partner]+'は'+('家で静かに休める時間がほしい、と話した。' if self.npc_wish=='quiet' else 'ひとりで外を歩く時間もほしい、と話した。')+' 自分が育児を引き受けるか、家で一緒に過ごすか。',['handover','book','voice'])
  # Actual native feasibility problems remain available, but cannot crowd out all joyful choices.
  p=a['parents'][self.actor];offer=p.get('job_offer')
  if offer:
   opts=[{'id':k,'title':title,'mode':'request','kind':req,'value':offer['id'],'cost_yen':0,'hours':.5,'detail':'自分宛ての仕事の提案への返答。実際の就業は次の月次処理で決まる。','transfer_yen':0} for k,title,req in [('accept','仕事の提案を受ける','accept_job_offer'),('reject','今回は断る','reject_job_offer')]]
   c.append(('job',90,'仕事の提案と、これからの暮らし',self.names[self.actor]+'宛てに通常年収'+yen(offer['normal_annual'])+'・週'+str(offer['normal_weekly_hours'])+'時間の提案がある。家で過ごす時間との兼ね合いも考えて返事をする。',opts))
  if self.month>=4 and p.get('employee_contract'):
   ratio=1. if p['hours_ratio']<1 else .8
   opts=[{'id':'hours','title':'自分の勤務を'+str(round(ratio*100))+'％で相談する','mode':'request','kind':'request_hours','value':ratio,'cost_yen':0,'hours':.5,'detail':'希望と実現を分ける。実働と給与が次月以降に変わる可能性がある。','transfer_yen':0},self.quote_choice('voice')]
   c.append(('work',44,'家にいる時間と、自分の仕事',self.names[self.actor]+'の直近の実働は週'+str(p.get('actual_weekly_hours',0))+'時間。今月は'+str(len([e for e in self.experiences if e['period']==self.month]))+'場面を子どもと過ごした。勤務を相談するか、今の働き方の中で時間を作るか。',opts))
  if a['accounts']['cash']<self.essential()*.4:
   opts=[self.quote_choice('voice')]
   term=a['accounts'].get('term',0)
   if term:opts.insert(0,{'id':'withdraw','title':'次の生活費を支払い口座へ戻す','mode':'withdraw','kind':min(term,max(10000,self.essential()-a['accounts']['cash'])),'value':None,'cost_yen':0,'hours':0,'detail':'定期性預貯金からの振替。新しい収入ではない。解約条件は未実装。','transfer_yen':min(term,max(10000,self.essential()-a['accounts']['cash']))})
   if len(opts)>=2:c.append(('money',84,'遊びの予定を立てる前に',f'支払い口座は{yen(a["accounts"]["cash"])}。直近の生活費参照額は{yen(self.essential())}。外出を増やす前に、口座を整えるか、今月は家で過ごすか。',opts))
  return [v for v in c if self.month-self.event_cooldown.get(v[0],-99)>=(8 if v[0] in ['work','money','family'] else 5) and all(not (o['mode']=='request' and any(q['type']==o['kind'] for q in self.game.queue)) for o in v[4])]
 def publish_event(self,c,*,voluntary=False):
  if self.current_event or self.game.finished:return
  e={'id':f'event-{len(self.events):04d}','kind':c[0],'title':c[2],'background':c[3],'date':self.date,'period':self.month,'participants':[self.names[self.actor],self.game.config['child_name']],'why_now':'今の月齢・実際の予定枠・使える口座・これまでの出来事から選べることです。結果は選択後に決まります。','choices':copy.deepcopy(c[4][:3]),'source_refs':['A.completed.accounts','A.completed.parents/'+self.actor,'C3.scenes','C3.plans','B.actual_age_days'],'status':'waiting','evidence':'C3_contextual_game_opportunity_not_empirical_frequency','voluntary':voluntary}
  self.events.append(e);self.current_event=e['id'];self.last_event_month=self.month;self.event_cooldown[c[0]]=self.month;self.running=False
 def maybe_event(self):
  # Resolve an application later, even if it was not selected. No attractive-child advantage.
  for p in self.plans:
   if p['status']=='awaiting_result' and self.month>=p['due_period']:
    selected=u(self.settings.get('seed'),'C3_photo_selection',p['id'])<.35;p['status']='selected' if selected else 'not_selected';p['result_date']=self.date
    text=('家族写真展に、一枚を飾ってもらえることになった。' if selected else '家族写真展から、今回は展示に選ばれなかったと連絡が来た。')+'応募した写真は、家族のアルバムにも残っている。'
    self.fact('project/'+p['id'],'あの一枚の、その後',text,['C3.plans/'+p['id'],'C3.scenes/'+p['source_scene_id']],'fictional_lottery_no_ability_effect',permanent=True)
    self.keepsakes.append({'id':f'memory-{len(self.keepsakes):04d}','date':self.date,'title':'家族写真展の結果','scene_id':p['source_scene_id'],'experience_id':None,'text':text,'item_id':None})
  if self.current_event or self.game.finished:return
  gap=2+int(u(self.settings.get('seed'),self.last_event_month,'C3_spacing')>.6)
  if self.month-self.last_event_month<gap:return
  c=self.event_candidates()
  if not c:return
  # Category diversity is about distinct decisions, not rotating phrases.
  recent=[e['kind'] for e in self.events[-3:]]
  c=max(c,key=lambda v:v[1]-(22 if v[0] in recent else 0)+u(self.settings.get('seed'),self.month,v[0])*17)
  self.publish_event(c)
 def open_opportunity(self,theme='discover'):
  from .catalogue import THEMES
  if theme not in THEMES:raise ValueError('どんな楽しみを考えるか選んでください。')
  if self.current_event:raise ValueError('先に、いまの出来事への返事をしてください。')
  if self.opportunity_month==self.month:raise ValueError('今月の楽しみは選びました。次の月にも考えられます。')
  if not self.policy or self.game.finished:raise ValueError('生活方針を選んで、体験中に使ってください。')
  title,kinds=THEMES[theme];opts=self.activity_options(kinds)
  # At birth, offer a photo or quiet face-to-face time rather than unsuitable trips.
  if len(opts)<2:opts=self.activity_options(['photo','voice'])
  self.publish_event(('initiative',0,title,'自分から、次に一緒にしてみたいことを考える。遠出は来月の予定に、家の遊びは今の時間に。手元の残高と時間で実行できる候補を表示しています。',opts),voluntary=True)
  self.opportunity_month=self.month;self.revision+=1
 def choose(self,event_id,choice_id):
  if self.current_event!=event_id:raise ValueError('現在の判断を選んでください。')
  event=next(e for e in self.events if e['id']==event_id);choice=next((c for c in event['choices'] if c['id']==choice_id),None)
  if not choice:raise ValueError('この判断の選択肢を選んでください。')
  before={'accounts':copy.deepcopy(self.game.core.a['accounts']),'time':self.budget(),'experience_count':len(self.experiences),'queue':copy.deepcopy(self.game.queue)};result={}
  mode=choice['mode'];kind=choice['kind']
  if mode=='plan':
   due_period=self.month+1;due_date=self.date
   if choice.get('birthday_year'):
    birth=dt.date.fromisoformat(self.game.config['birth_date']);due_date=birth.replace(year=birth.year+choice['birthday_year']).isoformat()
   result={'id':f'plan-{len(self.plans):04d}','date':self.date,'kind':kind,'due_period':due_period,'due_date':due_date,'event_id':event_id,'status':'planned','birthday_year':choice.get('birthday_year'),'quoted_yen':choice['cost_yen'],'quoted_hours':choice['hours']}
   self.plans.append(result)
   self.fact('promise/'+result['id'],'次の楽しみができた',self.names[self.actor]+'は「'+choice['title']+'」を予定にした。'+('誕生日が来てから、一緒に過ごす。' if choice.get('birthday_year') else '来月、家族の都合と費用を確かめて出かける。'),['C3.plans/'+result['id']],'C3_explicit_future_plan',permanent=True)
  elif mode=='activity':
   t=self.schedule(kind,'event',event_id)
   if not t:raise ValueError('この月齢では実行できません。')
   result=self.execute(t)
  elif mode=='request':
   r=self.own_request(kind,choice['value'],event_id)
   if r:
    result=r
    if kind=='request_hours':self.work_preference_override=choice['value']
   else:result={'status':'not_realized','reason':'同じ希望をすでに送ったか、相談に使う予定枠が足りない'}
  elif mode in ['withdraw','saving']:result=self.transfer(mode,kind,event_id)
  elif mode=='envelope':
   if self.game.core.a['accounts']['cash']-self.held_cash()<kind:raise ValueError('この額を確保する残高がありません。')
   result={'id':f'envelope-{len(self.envelopes)}','remaining_yen':kind,'status':'active','source_event':event_id,'purpose':'次回の有料活動'};self.envelopes.append(result)
  event.update(status='chosen',chosen=choice_id,result=copy.deepcopy(result),before=before,after={'accounts':copy.deepcopy(self.game.core.a['accounts']),'time':self.budget(),'experience_count':len(self.experiences),'queue':copy.deepcopy(self.game.queue)})
  self.current_event=None
  if mode in ['withdraw','saving']:
   term=self.game.core.a['accounts'].get('term',0);cash=self.game.core.a['accounts']['cash']
   self.fact('transfer/'+mode+'/'+digest([kind,term,cash]),'口座を動かして備えた',f'{self.names[self.actor]}は「{choice["title"]}」として{yen(kind)}を移した。支払い口座は{yen(before["accounts"]["cash"])}から{yen(cash)}へ、定期性預貯金は{yen(term)}になった。純資産は増えていない。',['C3.events/'+event_id,'C3.finance/'+result['id']],'actual_asset_transfer',permanent=True,links=[event_id])
  elif mode=='envelope':
   self.fact('envelope/'+str(self.held_cash()),'次に使うお金を分けた',f'{self.names[self.actor]}は活動費として{yen(kind)}を取り置き、取り置きの合計は{yen(self.held_cash())}になった。預金残高や純資産は変わらず、ほかの任意の振替に回せる額が減る。',['C3.events/'+event_id,'C3.envelopes'],'explicit_budget_commitment',permanent=True,links=[event_id])
  elif mode=='request' and result.get('status')=='requested':
   p=self.game.core.a['parents'][self.actor];context=[kind,choice['value'],p['state'],p['hours_ratio'],self.game.core.a['care']['status']]
   self.fact('request/'+digest(context),'希望を伝えた場面',f'{self.names[self.actor]}は「{choice["title"]}」の手続きに0.5時間を使った。いまの実働は週{p.get("actual_weekly_hours",0):g}時間で、まだ結果ではない。',['C3.requests/'+result['id']],'requested_action_not_outcome',permanent=True,links=[event_id])
  self.flush();self.running=not self.game.finished;self.revision+=1
 def financial_view(self):
  a=self.game.core.a;period=self.game.core.a_periods[-1] if self.game.core.a_periods and (not self.months or self.months[-1].get('native_period_completed',True)) else None;row=a.get('last_month') if period else None
  tx=copy.deepcopy(period['A_transactions']) if period else []
  pidx=self.month-1
  extra=[f for f in self.finance if f['period']==pidx] if period else []
  rows=[]
  for t in tx:
   delta=t['deltas'].get('cash',0)
   if delta:rows.append({'event_id':t['event_id'],'label':('保育料（自治体の実額未確認・参照シナリオ）' if 'childcare' in ' '.join(t['deltas']) and row and (row.get('care_fee') or {}).get('actual_local_fee_identified') is False else cash_label(t)),'cash_delta':delta,'kind':t['kind'],'source':'A.completed.transactions','deltas':t['deltas']})
  for f in extra:
   for e in f['entries']:
    delta=e['deltas'].get('cash',0)
    if delta:rows.append({'event_id':f['id']+'/'+e['event_id'],'label':('活動の支払い：'+ACTS[next((t['kind'] for t in self.tasks if t['id']==f['ref']),'voice')]['title']) if f['kind']=='expense' else '支払い口座→定期性預貯金' if f['kind']=='saving' else '定期性預貯金→支払い口座','cash_delta':delta,'kind':'C3_'+f['kind'],'source':'C3.finance/'+f['id'],'deltas':e['deltas']})
  current=sum(e['deltas'].get('cash',0) for f in self.finance if f['period']==self.month for e in f['entries'])
  opening=self.initial_accounts['cash'] if not self.months else self.months[-1]['opening_cash']
  closing_before_current=a['accounts']['cash']-current
  balance_residual=closing_before_current-opening-sum(r['cash_delta'] for r in rows) if period else None
  recognized_expense=(row or {}).get('ledger',{}).get('recognized_expense')
  # Full accrual/cash distinction comes from real journal, not extrapolated income.
  due_income=sum(sum(v for k,v in t['deltas'].items() if k.startswith('AR:') and v>0) for t in tx if t['kind'] in ['income','gross_salary_earned','wage_earned'])
  return {'cash':a['accounts']['cash'],'accounts':copy.deepcopy(a['accounts']),'account_rows':[{'key':k,'label':LABELS.get(k,('給与の入金待ち' if 'payroll' in k else '給付・精算等の入金待ち') if k.startswith('AR:') else ('社会保険の未払い' if 'social' in k else '税の未払い' if 'tax' in k else '出産費用の未払い' if 'birth' in k else '生活費等の未払い') if k.startswith('L:AP:') else 'その他の残高'),'value':v} for k,v in sorted(a['accounts'].items())],'opening_cash':opening,'closing_cash':closing_before_current,'rows':rows,'cash_identity_residual':balance_residual,'current_C3_cash_delta':current,'period':period['start'] if period else None,'consumption_items':(row or {}).get('budget_detail',{}).get('items',[]),'monthly_reference_need':self.essential(),'reserved_cash':self.held_cash(),'normal_annual_total':sum(p['normal_annual'] for p in a['parents'].values()),'wages_gross_earned':(row or {}).get('actual_earned_gross'),'recognized_expense':recognized_expense,'receivables':{k:v for k,v in a['accounts'].items() if k.startswith('AR:') and v},'unpaid':{k:v for k,v in a['accounts'].items() if k.startswith('L:AP:') and v},'ownership':'世帯の通貨性預貯金。主人公個人の持分は未識別。','initial_source':'2024年・住宅ローン有無×可処分所得帯×参照世帯規模の資産統計。親の年齢・職業と資産の同時分布、出生家庭への移送は未確認。','initial_explicit_scenario':self.settings.get('initial_cash_yen') is not None,'net_worth':sum(v if not k.startswith('L:') else -v for k,v in a['accounts'].items())}
 def tick(self):
  if self.current_event or not self.policy or self.game.finished:return
  self.phase+=1;self.elapsed_ms=0
  if self.phase==1:
   self.prepare_policy();queued=[t for t in self.tasks if t['status']=='queued'];n=max(1,math.ceil(len(queued)/2))
   for t in queued[:n]:self.execute(t)
   self.observe_new();self.flush()
  elif self.phase==2:
   for t in [t for t in self.tasks if t['status']=='queued']:self.execute(t)
   self.flush();self.maybe_event()
  else:
   opening=self.months[-1]['closing_cash'] if self.months else self.initial_accounts['cash'];old_period=self.month
   old_completed=len(self.game.core.a_periods);self.game.advance(reviewed=True,observer=self.actor);self.phase=0
   decisions=self.game.turns[-1]['decisions']
   for d in decisions:
    req=next((r for r in self.requests if r['id']==d.get('request_id')),None)
    if req:req['results'].append(copy.deepcopy(d));req['status']='answered'
    self.fact('decision/'+digest([d['kind'],d.get('requested_value'),d['outcome'],[self.game.core.a['parents'][self.actor]['state'],self.game.core.a['parents'][self.actor].get('actual_weekly_hours',0)],self.game.core.a['care']['status']]),'希望への返答が届いた',self.names[self.actor]+'の希望に返答。'+d['text']+f' 実働は週{self.game.core.a["parents"][self.actor].get("actual_weekly_hours",0):g}時間、保育は「{self.game.view(self.actor)["household"]["care"]["status"]}」。',['A.completed.decisions/'+str(d['request_id'])],'native_A_unvalidated_feasibility',permanent=True,links=[req['source']] if req and req['source'] and req['source'].startswith('event-') else [])
   old=self.months[-1]['parents'] if self.months else None;now={k:{'state':p['state'],'hours':p.get('actual_weekly_hours',0),'ratio':p['hours_ratio']} for k,p in sorted(self.game.core.a['parents'].items())}
   if old:
    for k,p in now.items():
     if p['state']!=old[k]['state'] or abs(p['hours']-old[k]['hours'])>=4:
      self.fact('work/'+k+'/'+p['state']+'/'+str(p['hours']),'働き方の実際が変わった',(f'{self.names[k]}は「{EMPLOYMENT.get(old[k]["state"],old[k]["state"])}」から「{EMPLOYMENT.get(p["state"],p["state"])}」へ移った。今の実働は週{p["hours"]:g}時間。' if old[k]['hours']==p['hours'] else f'{self.names[k]}の実働は、週{old[k]["hours"]:g}時間から{p["hours"]:g}時間へ変わった。今は「{EMPLOYMENT.get(p["state"],p["state"])}」で過ごしている。'),['A.completed.parents/'+k],'native_A_unverified_employment',permanent=True)
   self.months.append({'date':self.date,'period':self.month,'opening_cash':opening,'closing_cash':self.game.core.a['accounts']['cash'],'parents':now,'native_period_completed':len(self.game.core.a_periods)>old_completed,'unresolved_A_decisions':copy.deepcopy(self.game.core.a.get('pending_decisions',[])),'policy':self.policy,'time_used':copy.deepcopy(self.time_used),'task_ids':[t['id'] for t in self.tasks if t['period']==old_period]})
   # Observe only native reports made available after this real completed period.
   reports=self.game.core.child.player_view(self.game.core.identity['person_links'][self.actor])['observations']
   for signal,title in [('takes_independent_steps','ひとりで足を運ぶ姿'),('uses_contextual_word','場面に合う言葉')]:
    found=next((r for r in reports if r['behaviors'].get(signal)),None)
    if found and signal not in self.observed_signals:
     self.observed_signals[signal]={'date':found['date'],'report_sha256':digest(found)};self.fact('observed-skill/'+signal,'初めて記録できた姿',f'{self.names[self.actor]}は、{self.game.config["child_name"]}の「{title}」を記録した。実際に観察できた場面で、正確な獲得日の判定ではない。',['B.player_view/'+self.actor+'/'+signal],'B_uncalibrated_report_measurement',permanent=True)
   while self.held_cash()>self.game.core.a['accounts']['cash']:
    envelope=next((e for e in reversed(self.envelopes) if e['remaining_yen']),None)
    gap=self.held_cash()-self.game.core.a['accounts']['cash'];envelope['remaining_yen']=max(0,envelope['remaining_yen']-gap)
    if not envelope['remaining_yen']:envelope['status']='underfunded_by_monthly_cashflow'
    self.fact('reserve-underfunded','取り置きも見直す',f'月次の入出金後、口座残高に合わせて活動費の取り置きを減らした。法的に保護された別口座ではなく、家計内の目的別メモとして扱う。',['A.completed.transactions','C3.envelopes'],'cash_budget_reconciliation',cooldown=6)
   self.time_used={};self.flush();self.maybe_event()
   if self.game.finished:self.running=False
  self.revision+=1;self.game.core.assert_consistent()
 def view(self):
  v=self.game.view(self.actor);a=self.game.core.a;people={p['person_id']:p for p in a['persons']};parents=[]
  for k,p in sorted(a['parents'].items(),key=lambda pair:(pair[0]!=self.actor,pair[0])):parents.append({'role':k,'name':self.names[k],'age':people[k]['age_years'],'education':people[k]['attributes'].get('education'),'occupation':people[k]['attributes'].get('occupation'),'usual_annual':p['normal_annual'],'state':EMPLOYMENT.get(p['state'],'就業の調整中'),'hours':p.get('actual_weekly_hours'),'is_player':k==self.actor})
  event=next((e for e in self.events if e['id']==self.current_event),None)
  public_event={k:copy.deepcopy(event[k]) for k in ['id','kind','title','background','date','participants','why_now','choices','evidence','source_refs']} if event else None
  recent=self.logs[-1] if self.logs else None
  return {'version':VERSION,'revision':self.revision,'date':self.date,'age_months':v['age_months'],'age_days':v['age_days'],'phase':self.phase,'running':self.running,'speed':self.speed,'elapsed_ms':self.elapsed_ms,'finished':self.game.finished,'actor':self.actor,'player_name':self.names[self.actor],'child_name':v['child_name'],'location':PREFECTURES[int(a['household']['prefecture_code'])-1]+v['household']['municipality'],'parents':parents,'policy':self.policy,'work_preference_override':self.work_preference_override,'policies':POLICIES,'logs':copy.deepcopy(self.logs[-75:]),'latest_child':next((x for x in reversed(self.logs) if x['key'].startswith(('scene/','observed-skill/','growth/'))),None),'event':public_event,'past_events':[{'id':e['id'],'title':e['title'],'choice':e.get('chosen'),'status':e['status'],'date':e['date'],'result':{k:e.get('result',{}).get(k) for k in ['status','reason','kind','id','paid_yen','hours']}} for e in self.events[-6:]],'last_choice_result':self.choice_result(),'money':self.financial_view(),'time':self.budget(),'inventory':copy.deepcopy(self.inventory),'care':v['household']['care'],'reports':v['child'],'album':copy.deepcopy(self.keepsakes),'plans':[{'id':p['id'],'title':ACTS.get(p['kind'],{}).get('title','家族写真展の返事'),'status':p['status'],'date':p['date'],'due_period':p['due_period'],'reason':p.get('reason')} for p in self.plans],'child_glimpse':(next((l['text'] for l in reversed(self.logs) if l['key'].startswith(('scene/','observed-skill/','growth/'))),None) if self.logs and self.logs[-1]['key'].startswith(('growth/','observed-skill/')) else next((b['text'] for scene in reversed(self.scenes) for b in scene['beats'][1:2]),None)),'neighborhood':self.settings.get('neighborhood','city'),'scene_count':len(self.scenes),'initiative_available':self.opportunity_month!=self.month and not self.game.finished and bool(self.policy) and not self.current_event,'portrait':[{'signal':c['signal'],'text':c['text'],'sources':c['sources']} for c in v['child']['cards'] if c['sampled'] and c['present']][:3],'limits':'活動の反応と配偶者の合意は未校正の体験シナリオ。長期能力・愛着への追加効果はなし。家計・就業・保育はA研究版の未検証部分を継承。'}
 def choice_result(self):
  e=next((e for e in reversed(self.events) if e['status']=='chosen'),None)
  if not e:return None
  c=next(c for c in e['choices'] if c['id']==e['chosen']);r=e['result']
  request=next((q for q in self.requests if q['id']==r.get('id')),None)
  return {'event_id':e['id'],'title':c['title'],'status':r.get('status','executed'),'reason':r.get('reason'),'observed_reaction':next((x['reaction'] for x in self.experiences if x['id']==r.get('experience_id')),None),'scene_text':next((render_scene(q) for q in self.scenes if q['id']==r.get('scene_id')),None),'plan':copy.deepcopy(next((p for p in self.plans if p['id']==r.get('id')),None)),'counterparty':next((self.names.get(x['person'],'家族')+'は「'+x['action']+'」予定を実行した。' for x in reversed(self.partner_history) if x['source_task']==r.get('id')),None),'cash_delta':e['after']['accounts']['cash']-e['before']['accounts']['cash'],'new_experiences':e['after']['experience_count']-e['before']['experience_count'],'time_hours':r.get('hours',r.get('time_hours',0)),'native_results':copy.deepcopy(request['results']) if request else [],'followup':'希望を送ったところです。次の月次処理で結果を確認します。' if request and not request['results'] else '予定に残りました。当日、仕事・時間・口座・家族の都合をもう一度確かめます。' if r.get('status')=='planned' else 'この日の場面は、暮らしの記録に残りました。','evidence':e['evidence']}
 def snapshot(self):return {'version':VERSION,'state':copy.deepcopy({k:v for k,v in self.__dict__.items() if k!='game'}),'native':self.game.snapshot()}
 def save(self,path):
  p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);body=self.snapshot();tmp=p.with_suffix('.tmp')
  with gzip.open(tmp,'wt',encoding='utf8') as f:json.dump({'payload':body,'sha256':digest(body)},f,ensure_ascii=False,sort_keys=True,allow_nan=False)
  tmp.replace(p);return digest(body)
 @classmethod
 def load(cls,path,engine):
  with gzip.open(path,'rt',encoding='utf8') as f:env=json.load(f)
  b=env['payload']
  if b['version']!=VERSION or digest(b)!=env['sha256']:raise ValueError('保存記録の版・ハッシュが一致しません。')
  obj=cls();obj.__dict__.update(b['state']);obj.game=restore_game(b['native'],engine);return obj
