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
POLICIES={
 'work':{'name':'仕事と収入','hint':'自分の通常勤務を希望。仕事の準備に月8時間を確保し、家では声かけ。収入増を保証しません。'},
 'time':{'name':'子どもとの時間','hint':'自分の勤務を8割で相談。月4回、家で一緒に過ごす枠を確保。実現後は給与が減る可能性。'},
 'play':{'name':'遊びと体験','hint':'月3,000円を上限に絵本・玩具と外出。支払い口座と予定枠が足りる範囲で実行。'},
 'stable':{'name':'安定した暮らし','hint':'今の働き方を保ち、家での活動を中心に。直近の支払い額を目安に口座を残す。'},
 'save':{'name':'貯蓄をつくる','hint':'直近の支払い2か月分を残し、余裕があれば月2万円まで定期性預貯金へ。運用益は追加しません。'},
 'social':{'name':'家族と交流','hint':'親子ひろばと家族の分担を優先。配偶者には都度相談し、断られた場合も経過を残します。'},
}
ACTS={
 'voice':dict(title='抱っこで声をかける',place='自宅',hours=.25,cost=0,min_age=0,bucket='care'),
 'floor':dict(title='床に敷いたマットで遊ぶ',place='自宅',hours=.5,cost=0,min_age=3,bucket='care'),
 'book':dict(title='絵本を一緒に開く',place='自宅',hours=.5,cost=1200,min_age=2,bucket='care',item='book'),
 'toy':dict(title='布のボールで遊ぶ',place='自宅',hours=.5,cost=1600,min_age=4,bucket='care',item='toy'),
 'park':dict(title='公園のベンチで過ごす',place='近所の公園',hours=1.5,cost=0,min_age=1,bucket='rest'),
 'center':dict(title='親子ひろばへ出かける',place='地域の親子ひろば（体験用の施設）',hours=2,cost=300,min_age=3,bucket='rest'),
 'handover':dict(title='2時間の育児を引き受ける',place='自宅',hours=2,cost=0,min_age=0,bucket='rest',agreement=True),
 'visit':dict(title='保育園の見学枠を訪ねる',place='保育施設（体験用の見学枠）',hours=2,cost=500,min_age=0,bucket='rest',agreement=True),
 'trip':dict(title='家族で一泊の旅行に出る',place='近隣の宿泊先（体験用の商品）',hours=16,cost=28000,min_age=6,bucket='rest',agreement=True),
}
class Experience:
 @classmethod
 def start(cls,engine,**settings):
  actor=settings.pop('role','father');policy=settings.pop('policy',None)
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
  obj.names={k:settings.get(k+'_name') or old.names[k] for k in obj.game.core.a['parents']}
  obj.revision=0;obj.phase=0;obj.running=False;obj.speed=1;obj.elapsed_ms=0;obj.policy=None;obj.policy_history=[];obj.month_prepared=-1
  obj.logs=[];obj.fact_ledger=[];obj.semantic_last={};obj.pending_facts=[];obj.suppressed=[];obj.tasks=[];obj.inventory={};obj.experiences=[];obj.finance=[];obj.time_used={};obj.requests=[];obj.events=[];obj.current_event=None;obj.last_event_month=0;obj.event_cooldown={};obj.months=[];obj.observed_signals={};obj.envelopes=[];obj.partner_history=[];obj.policy_operations=[]
  obj.initial_accounts=copy.deepcopy(obj.game.core.a['accounts']);obj.initial_trace=copy.deepcopy(obj.game.core.a['initial_family']['automatic_accounts']['trace'])
  obj.work_preference_override=None
  obj.npc_wish='quiet' if u(args['seed'],'C2partner')<.5 else 'outdoor'
  if policy:obj.set_policy(policy)
  return obj
 @property
 def date(self):return self.game.core.child._state['as_of_date']
 @property
 def month(self):return len(self.game.turns)
 def clone(self):
  obj=copy.copy(self);obj.__dict__.update(copy.deepcopy({k:v for k,v in self.__dict__.items() if k!='game'}));obj.game=self.game.clone();obj.game.core.a=copy.deepcopy(self.game.core.a);return obj
 def fact(self,key,title,text,refs,evidence,*,permanent=False,cooldown=6,links=None):
  rec={'id':f'fact-{len(self.fact_ledger):05d}','key':key,'title':title,'text':text,'date':self.date,'period':self.month,'phase':self.phase,'source_refs':refs,'evidence':evidence,'links':links or []};self.fact_ledger.append(rec)
  seen=self.semantic_last.get(key)
  if seen is not None and (permanent or self.month-seen<cooldown):self.suppressed.append({'fact_id':rec['id'],'reason':'known_semantic_fact','key':key});return
  # Same reaction recurring in the same place never becomes news just by rewording.
  self.semantic_last[key]=self.month;self.pending_facts.append(rec)
 def flush(self):
  occupied=sum(x.get('published_period',x['period'])==self.month for x in self.logs)
  while self.pending_facts and occupied<3:
   r=self.pending_facts.pop(0);r['published_date']=self.date;r['published_phase']=self.phase;r['published_period']=self.month;self.logs.append(r);occupied+=1
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
   l.expense_due('C2/'+ref,n,{'source':'C2_explicit_price_scenario','reference':ref});l.pay('L:AP:C2/'+ref,n)
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
  q=copy.deepcopy(ACTS[kind]);q['kind']=kind
  if self.game.core.elapsed_months<q['min_age']:return None
  if q.get('item') in self.inventory:q['cost']=0
  r={'id':f'task-{len(self.tasks):05d}','date_requested':self.date,'period':self.month,'kind':kind,'quote':q,'source':source,'event_id':event_id,'status':'queued'};self.tasks.append(r);return r
 def prepare_policy(self):
  if self.month_prepared==self.month or not self.policy:return
  self.month_prepared=self.month;a=self.game.core.a;p=a['parents'][self.actor];key=self.policy
  if key in ['time','work'] and self.work_preference_override is None:
   ratio=.8 if key=='time' else 1.
   if p.get('employee_contract') and p['hours_ratio']!=ratio:self.own_request('request_hours',ratio,'policy/'+key)
   if key=='work' and p['state']=='nonemployed' and not p.get('job_search'):self.own_request('job_search',source='policy/work')
  if key=='work':
   hours=min(8,self.budget()['rest']);self.time_used['rest']=self.time_used.get('rest',0)+hours
   self.policy_operations.append({'period':self.month,'kind':'work_preparation_reserved','hours':hours,'evidence':'C2_time_allocation_scenario_no_extra_income'})
  if key=='save':
   amount=max(0,min(20000,a['accounts']['cash']-2*self.essential()-self.held_cash()))
   if amount:
    r=self.transfer('saving',amount,'policy-saving-'+str(self.month));self.policy_operations.append({'period':self.month,'kind':'saving','yen':amount,'finance_id':r['id']})
    self.fact('saving-start','支払い口座と分けて残す',f'{self.names[self.actor]}は、直近の生活費2か月分を口座に残した上で{yen(amount)}を定期性預貯金へ移した。世帯の純資産は増えていない。',['C2.finance/'+r['id']],'explicit_asset_transfer',permanent=True)
  age=self.game.core.elapsed_months
  choices={'work':['voice'],'time':['floor' if age>=3 else 'voice']*4,'play':['book' if age>=2 else 'voice','toy' if age>=4 else 'voice','center' if age>=3 else 'park' if age>=1 else 'voice'],'stable':['voice','floor' if age>=3 else 'voice'],'save':['voice'],'social':['center' if age>=3 else 'voice','handover' if self.partner else 'park' if age>=1 else 'voice']}
  for k in choices[key]:self.schedule(k)
 def execute(self,t):
  q=t['quote'];actor=self.names[self.actor];child=self.game.config['child_name'];partner=self.names.get(self.partner);bucket=q['bucket'];reason=None
  if self.budget()[bucket]<q['hours']:reason='今月の予定枠が足りない'
  cash=self.game.core.a['accounts']['cash'];limit=3000 if self.policy=='play' else 500 if self.policy=='social' else cash
  spent=sum(r.get('paid_yen',0) for r in self.experiences if r['period']==self.month and r['source']=='policy')
  if t['source']=='policy' and (q['cost']>max(0,limit-spent) or q['cost']>cash):reason='この方針の予算枠・残しておくお金を超える'
  if q['cost']>cash:reason='支払い口座の残高が足りない'
  if q.get('agreement') and self.partner:
   if t['kind']=='trip' and self.game.core.a['parents'][self.partner]['state']=='maternity':reason='配偶者から、産後休業中の泊まりは見送りたいとの返答'
   elif t['kind']=='trip' and self.npc_wish=='quiet' and not any(r['kind']=='handover' and r['status']=='done' for r in self.tasks):reason='配偶者から、先に家で休める分担を相談したいとの返答'
  if t['kind']=='handover' and not self.partner:reason='この家庭には交代する同居の配偶者がいない'
  if reason:
   t.update(status='not_realized',reason=reason)
   if t['source']!='policy' or self.semantic_last.get('blocked/'+t['kind']) is None:self.fact('blocked/'+t['kind'],'予定を見直した',f'{actor}の「{q["title"]}」は、{reason}ため実行しなかった。費用は発生していない。',['C2.tasks/'+t['id']],'resource_or_NPC_scenario',cooldown=12,links=[t['event_id']] if t['event_id'] else [])
   return t
  paid=self.transfer('expense',q['cost'],t['id']) if q['cost'] else None
  remaining_cost=q['cost']
  for envelope in self.envelopes:
   used=min(remaining_cost,envelope['remaining_yen']);envelope['remaining_yen']-=used;remaining_cost-=used
   if not envelope['remaining_yen']:envelope['status']='used'
  self.time_used[bucket]=self.time_used.get(bucket,0)+q['hours']
  item=None
  if q.get('item'):
   name={'book':'「まると、てのひら」（架空の絵本）','toy':'赤い布のボール'}[q['item']]
   if q['item'] not in self.inventory:self.inventory[q['item']]={'id':'item-'+q['item'],'name':name,'acquired':self.date,'source_task':t['id'],'cost_yen':q['cost']}
   item=self.inventory[q['item']]
  # Inherited C1 acute response computation, generalised only for context/actor.
  s=self.game.core.child._state;traits=s['latent_state'];short=s['emotion_regulation'];age=s['age_days']/30.4375
  past=[e for e in self.experiences if e['kind']==t['kind']];old=past[-1] if past else None
  familiarity=math.exp(-(dt.date.fromisoformat(self.date)-dt.date.fromisoformat(old['date'])).days/90) if old else 0
  stim={'voice':.15,'floor':.5,'book':.35,'toy':.5,'park':.8,'center':1.1,'handover':.2,'visit':1.,'trip':1.4}[t['kind']]
  load=-1.5+.45*traits['reactivity']+.4*traits['sensory_sensitivity']+.8*short['fatigue']+stim-.5*familiarity
  engage=-.25+.35*traits['attention_orientation']+.35*traits['approach']+.25*traits['exploration']+min(age,18)*.035+.3*familiarity
  seed=s['random_streams']['seed'];stopped=u(seed,self.date,t['id'],'cry')<1/(1+math.exp(-load));interested=u(seed,self.date,t['id'],'look')<1/(1+math.exp(-engage))
  reaction='途中で泣き出したため、活動を切り上げて静かな所で過ごした。' if stopped else ('開いたページに手を伸ばした。' if age>=6 else '開いたページへ顔を向けた。') if t['kind']=='book' and interested else '赤い布のボールへ手を伸ばした。' if t['kind']=='toy' and interested else '声の方へ顔を向けた。' if t['kind']=='voice' and interested else '周りの音の方へ顔を向けた。' if interested else 'しばらく見たあと、そばの大人へ顔を寄せた。'
  outcome='crying' if stopped else 'engaged_reaching' if interested and t['kind'] in ['book','toy'] and age>=6 else 'engaged' if interested else 'looking_away'
  r={'id':f'experience-{len(self.experiences):05d}','task_id':t['id'],'period':self.month,'date':self.date,'age_days':s['age_days'],'kind':t['kind'],'place':q['place'],'participants':[self.game.core.identity['person_links'][self.actor],self.game.core.identity['index_global_person_id']],'item_id':item['id'] if item else None,'item_name':item['name'] if item else None,'prior_experience_id':old['id'] if old else None,'reaction':reaction,'reaction_code':outcome,'hours':q['hours'],'paid_yen':q['cost'],'finance_id':paid['id'] if paid else None,'source':t['source'],'event_id':t['event_id'],'evidence':'inherited_C1_uncalibrated_acute_scenario','long_term_effect':False}
  self.experiences.append(r);t.update(status='done',experience_id=r['id'],paid_yen=q['cost'],hours=q['hours'])
  window=(past+[r])[-4:]
  if len(window)>=3 and sum(e['reaction_code']==outcome for e in window)>=3:
   self.fact('pattern/'+t['kind']+'/'+outcome,'繰り返して、気づいたこと',f'{actor}と{child}の'+(item['name'] if item else q['title'])+f'の直近{len(window)}回の記録のうち、'+str(sum(e['reaction_code']==outcome for e in window))+'回で「'+reaction+'」という反応が残った。この場面での記録で、性格や好みの診断ではない。',['C2.experiences/'+e['id'] for e in window],'repeated_observed_scenario_pattern',permanent=True)
  if t['kind']=='handover':
   rel={'date':self.date,'period':self.month,'source_task':t['id'],'person':self.partner,'hours':2,'action':'自宅でひとりで休む' if self.npc_wish=='quiet' else '近所をひとりで散歩する','evidence':'NPC_schedule_scenario'};self.partner_history.append(rel)
  text=f'{actor}は{child}と{q["place"]}で'+(item['name']+'を使った。' if item else '「'+q['title']+'」時間を取った。')+reaction
  if old and old['reaction_code']!=outcome:text+='前回の同じ活動とは違う反応が記録された。'
  if t['kind']=='handover':text+=f'{partner}はその2時間、「{self.partner_history[-1]["action"]}」予定を実行した。'
  refs=['C2.experiences/'+r['id'],'C2.tasks/'+t['id']]+(['C2.inventory/'+item['id']] if item else [])
  self.fact('experience/'+t['kind']+'/'+outcome,'いつもと違う発見' if old else '一緒に過ごした場面',text,refs,r['evidence'],permanent=True,links=[t['event_id']] if t['event_id'] else [])
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
 def event_candidates(self):
  a=self.game.core.a;p=a['parents'][self.actor];age=self.game.core.elapsed_months;cash=a['accounts']['cash'];choices=[]
  pending_kinds={d['type'] for d in a.get('pending_decisions',[])}
  offer=p.get('job_offer')
  if offer:choices.append(('job',100,'仕事の提案が届いた',f'通常年収{yen(offer["normal_annual"])}、週{offer["normal_weekly_hours"]}時間の提案。受けても就業の実現はAモデルの判定を待つ。',[('accept','この提案を受ける','request','accept_job_offer',offer['id']),('reject','今回は見送る','request','reject_job_offer',offer['id'])]))
  if (cash<self.essential()*.6 or 'cash_shortage' in pending_kinds) and self.event_cooldown.get('money',-99)<=self.month-3:
   options=[]
   if a['accounts'].get('term',0)>0:options.append(('withdraw','定期性預貯金から支払い口座へ','withdraw',min(a['accounts']['term'],max(10000,self.essential()-cash)),None))
   if a['spending_factor']>.9:options.append(('reduce','今後の通常消費を1割抑える','request','set_spending',.9))
   if not any(r['kind']=='apply_child_allowance' for r in self.requests):options.append(('allowance','児童手当の申請を進める','request','apply_child_allowance',None))
   else:options.append(('search','自分の仕事探しを進める','request','job_search',None))
   choices.append(('money',90,'次の支払いをどう備えるか',f'支払い口座は{yen(cash)}。直近の通常消費・家賃・保育料は月{yen(self.essential())}。これは過去・初期の参照額で、来月の確定予測ではない。',options))
  if (p.get('actual_weekly_hours',0)>28 or p['state'] in ['leave','maternity'] or 'care_work_conflict' in pending_kinds) and self.month>=2:
   options=[]
   if p.get('employee_contract') and p['hours_ratio']!=.8:options.append(('hours','自分の勤務を8割で相談','request','request_hours',.8))
   if not a['care'].get('application'):options.append(('nursery','保育の利用を申請する','request','apply_childcare',None))
   options.append(('home','自宅で子どもと過ごす枠をつくる','activity','floor' if age>=3 else 'voice',None))
   choices.append(('balance',55,'仕事と子どもの時間を見直す',f'{self.names[self.actor]}は{EMPLOYMENT.get(p["state"],p["state"])}。実働週{p.get("actual_weekly_hours",0):g}時間。配偶者の仕事を代わりに変更せず、自分の働き方や保育を相談する。',options))
  if age>=3 and (not a['care'].get('application') or a['care']['status']=='needs_eligibility_review'):
   choices.append(('care',60,'保育を調べる、その次は',f'今は保育を「{a["care"]["status"]}」で進行している。見学、申請、親族への相談は別の手続きで、入園や支援は保証されない。',[('apply','利用を申請する','request','apply_childcare',None),('visit','見学の枠を訪ねる','activity','visit',None),('relative','親族へ支援を頼む','request','request_relative_support',None)]))
  if age>=2:
   options=[('book','絵本を一緒に開く','activity','book',None),('free','家にある場所で遊ぶ','activity','floor' if age>=3 else 'voice',None)]
   if age>=4:options.append(('toy','布のボールで遊ぶ','activity','toy',None))
   choices.append(('play',45,'この子と、次に何をしてみよう',f'{self.game.config["child_name"]}は生後{age}か月。これまでの予定の経験は{len(self.experiences)}件。手元の物や初めての活動を選ぶ。好みや能力を断定する選択ではない。',options))
  if age>=6 and self.partner and self.budget()['rest']>=16 and cash>=28000 and any(e['kind'] in ['park','center'] for e in self.experiences):
   choices.append(('weekend',50,'家族の休日を相談する',f'外出の経験が増えた。支払い口座{yen(cash)}、今月の予定枠{self.budget()["rest"]:g}時間。泊まりには配偶者の合意も必要。',[('trip','一泊の旅行を相談する','activity','trip',None),('park','近所の公園で過ごす','activity','park',None),('handover','育児を交代して配偶者の時間をつくる','activity','handover',None)]))
  if self.partner and self.month>=2 and self.budget()['rest']>=2:
   choices.append(('family',48,'それぞれの休める時間を相談する',f'{self.names[self.partner]}には自分の予定もある。こちらが育児を引き受けるか、外の支援を頼むか、今月の過ごし方を話す。',[('handover','2時間の育児を引き受ける','activity','handover',None),('relative','親族へ支援を依頼する','request','request_relative_support',None),('home','子どもと家で過ごす','activity','voice',None)]))
  if cash>2*self.essential()+20000:
   choices.append(('reserve',40,'余裕のあるお金の置き場所',f'支払い口座には直近の通常支払い2か月分を超える残高がある。世帯の純資産を増やす選択ではなく、流動性と使い道を分ける。',[('save','2万円を定期性預貯金へ','saving',20000,None),('envelope','5千円を次の活動費に残す','envelope',5000,None),('book','手元の絵本で過ごす' if 'book' in self.inventory else '絵本を用意する','activity','book' if age>=2 else 'voice',None)]))
  return [c for c in choices if len(c[4])>=2 and self.month-self.event_cooldown.get(c[0],-99)>= (3 if c[0] in ['money','job'] else 6)]
 def maybe_event(self):
  a=self.game.core.a
  if self.current_event or self.game.finished:return
  candidates=self.event_candidates();urgent=[c for c in candidates if c[1]>=90]
  if not urgent and self.month-self.last_event_month<2+int(u(self.settings.get('seed'),self.last_event_month,'spacing')>.55):return
  candidates=urgent or candidates
  if not candidates:return
  # Household/child history changes eligible candidates, seed only breaks priority ties.
  c=max(candidates,key=lambda c:c[1]+u(self.settings.get('seed'),self.month,c[0])*12)
  event={'id':f'event-{len(self.events):04d}','kind':c[0],'title':c[2],'background':c[3],'date':self.date,'period':self.month,'participants':[self.names[self.actor]]+([self.names[self.partner]] if self.partner else []),'why_now':{'money':'口座が直近の支払い参照額に対して少ないか、期限が来た未払があるため。','balance':'勤務・休業の状況や、育児による実働の調整が必要な条件に合うため。','care':'生後3か月以降で保育が未申請か、利用条件の再確認が必要なため。','play':'月齢に合う活動と、持ち物・経験を見直せるため。','family':'今月、交代に使える2時間を確保できるため。','weekend':'外出の経験があり、旅行に使える費用と時間枠の条件を満たすため。','reserve':'直近の支払い参照額2か月分を超える残高があるため。','job':'本人宛ての仕事の提案が実際に届いているため。'}[c[0]]+' 将来の結果はまだ計算していない。','choices':[],'source_refs':['A.completed.parents/'+self.actor,'A.completed.care','A.completed.accounts','C2.experience_ledger'],'status':'waiting','evidence':'C2_contextual_game_scenario_with_native_actions'}
  event['background']+=f' 世帯は{len([p for p in a["persons"] if p.get("co_resident")])}人。{self.names[self.actor]}の直近の実働は週{a["parents"][self.actor].get("actual_weekly_hours",0):g}時間、今月の空き予定枠は{self.budget()["rest"]:g}時間。'
  event['participants'].append(self.game.config['child_name'])
  for id,title,mode,kind,value in c[4]:
   if mode=='activity':
    q=copy.deepcopy(ACTS[kind]);cost=0 if q.get('item') in self.inventory else q['cost'];hours=q['hours'];detail='時間と費用を使う。反応は未校正の短期シナリオ。能力の長期効果は計算しない。'
   elif mode=='request':cost=0;hours=.5;detail='希望を伝える手続き。職場・自治体等の結果は次の月次処理を待つ。給与の入金はさらに遅れる場合がある。'
   else:cost=0;hours=0;detail='預金振替・目的別の確保。純資産は増えない。定期預金の解約条件・手数料は未実装。'
   if mode=='activity':
    detail={'book':'同じ絵本を繰り返し使える。初回のみ購入。能力の長期効果は加算せず、その場の反応を記録。','toy':'布のボールを持ち物に加え、その後も使える。興味を示すかは保証されない。','handover':'自分の休日等の枠を2時間使い、配偶者の既存の育児を代わる。合意できなければ実行しない。','trip':'旅先の経験を家族で共有する。配偶者の合意が必要で、断られた場合は未実行・未請求。','park':'費用をかけず、外出に時間を使う。刺激への反応は未校正の場面シナリオ。','visit':'見学枠を訪ねた記録が残る。申請や入園の成功率は加算しない。','floor':'既存の育児時間の一部を、家で一緒に過ごす枠へ。追加の購入はしない。','voice':'既存の育児時間の一部で抱っこして話す。配偶者の仕事は変更しない。'} .get(kind,detail)
   elif mode=='request' and kind=='request_hours':detail='自分の勤務を8割で相談する。実働に反映されれば時間が増える一方、給与が減る可能性。給与の発生と振込には時間差がある。'
   if mode=='request' and any(a['type']==kind for a in self.game.queue):continue
   if mode=='request' and self.budget()['rest']<hours:continue
   if mode=='activity' and (self.game.core.elapsed_months<q['min_age'] or self.budget()[q['bucket']]<hours or self.game.core.a['accounts']['cash']<cost):continue
   event['choices'].append({'id':id,'title':title,'mode':mode,'kind':kind,'value':value,'cost_yen':cost,'hours':hours,'detail':detail,'transfer_yen':kind if mode in ['withdraw','saving','envelope'] else 0})
  if len(event['choices'])<2:return
  self.events.append(event);self.current_event=event['id'];self.last_event_month=self.month;self.event_cooldown[c[0]]=self.month;self.running=False
 def choose(self,event_id,choice_id):
  if self.current_event!=event_id:raise ValueError('現在の判断を選んでください。')
  event=next(e for e in self.events if e['id']==event_id);choice=next((c for c in event['choices'] if c['id']==choice_id),None)
  if not choice:raise ValueError('この判断の選択肢を選んでください。')
  before={'accounts':copy.deepcopy(self.game.core.a['accounts']),'time':self.budget(),'experience_count':len(self.experiences),'queue':copy.deepcopy(self.game.queue)};result={}
  mode=choice['mode'];kind=choice['kind']
  if mode=='activity':
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
   self.fact('transfer/'+mode+'/'+digest([kind,term,cash]),'口座を動かして備えた',f'{self.names[self.actor]}は「{choice["title"]}」として{yen(kind)}を移した。支払い口座は{yen(before["accounts"]["cash"])}から{yen(cash)}へ、定期性預貯金は{yen(term)}になった。純資産は増えていない。',['C2.events/'+event_id,'C2.finance/'+result['id']],'actual_asset_transfer',permanent=True,links=[event_id])
  elif mode=='envelope':
   self.fact('envelope/'+str(self.held_cash()),'次に使うお金を分けた',f'{self.names[self.actor]}は活動費として{yen(kind)}を取り置き、取り置きの合計は{yen(self.held_cash())}になった。預金残高や純資産は変わらず、ほかの任意の振替に回せる額が減る。',['C2.events/'+event_id,'C2.envelopes'],'explicit_budget_commitment',permanent=True,links=[event_id])
  elif mode=='request' and result.get('status')=='requested':
   p=self.game.core.a['parents'][self.actor];context=[kind,choice['value'],p['state'],p['hours_ratio'],self.game.core.a['care']['status']]
   self.fact('request/'+digest(context),'希望を伝えた場面',f'{self.names[self.actor]}は「{choice["title"]}」の手続きに0.5時間を使った。いまの実働は週{p.get("actual_weekly_hours",0):g}時間で、まだ結果ではない。',['C2.requests/'+result['id']],'requested_action_not_outcome',permanent=True,links=[event_id])
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
    if delta:rows.append({'event_id':f['id']+'/'+e['event_id'],'label':('活動の支払い：'+ACTS[next((t['kind'] for t in self.tasks if t['id']==f['ref']),'voice')]['title']) if f['kind']=='expense' else '支払い口座→定期性預貯金' if f['kind']=='saving' else '定期性預貯金→支払い口座','cash_delta':delta,'kind':'C2_'+f['kind'],'source':'C2.finance/'+f['id'],'deltas':e['deltas']})
  current=sum(e['deltas'].get('cash',0) for f in self.finance if f['period']==self.month for e in f['entries'])
  opening=self.initial_accounts['cash'] if not self.months else self.months[-1]['opening_cash']
  closing_before_current=a['accounts']['cash']-current
  balance_residual=closing_before_current-opening-sum(r['cash_delta'] for r in rows) if period else None
  recognized_expense=(row or {}).get('ledger',{}).get('recognized_expense')
  # Full accrual/cash distinction comes from real journal, not extrapolated income.
  due_income=sum(sum(v for k,v in t['deltas'].items() if k.startswith('AR:') and v>0) for t in tx if t['kind'] in ['income','gross_salary_earned','wage_earned'])
  return {'cash':a['accounts']['cash'],'accounts':copy.deepcopy(a['accounts']),'account_rows':[{'key':k,'label':LABELS.get(k,('給与の入金待ち' if 'payroll' in k else '給付・精算等の入金待ち') if k.startswith('AR:') else ('社会保険の未払い' if 'social' in k else '税の未払い' if 'tax' in k else '出産費用の未払い' if 'birth' in k else '生活費等の未払い') if k.startswith('L:AP:') else 'その他の残高'),'value':v} for k,v in a['accounts'].items()],'opening_cash':opening,'closing_cash':closing_before_current,'rows':rows,'cash_identity_residual':balance_residual,'current_C2_cash_delta':current,'period':period['start'] if period else None,'consumption_items':(row or {}).get('budget_detail',{}).get('items',[]),'monthly_reference_need':self.essential(),'reserved_cash':self.held_cash(),'normal_annual_total':sum(p['normal_annual'] for p in a['parents'].values()),'wages_gross_earned':(row or {}).get('actual_earned_gross'),'recognized_expense':recognized_expense,'receivables':{k:v for k,v in a['accounts'].items() if k.startswith('AR:') and v},'unpaid':{k:v for k,v in a['accounts'].items() if k.startswith('L:AP:') and v},'ownership':'世帯の通貨性預貯金。主人公個人の持分は未識別。','initial_source':'2024年・住宅ローン有無×可処分所得帯×参照世帯規模の資産統計。親の年齢・職業と資産の同時分布、出生家庭への移送は未確認。','initial_explicit_scenario':self.settings.get('initial_cash_yen') is not None,'net_worth':sum(v if not k.startswith('L:') else -v for k,v in a['accounts'].items())}
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
   old=self.months[-1]['parents'] if self.months else None;now={k:{'state':p['state'],'hours':p.get('actual_weekly_hours',0),'ratio':p['hours_ratio']} for k,p in self.game.core.a['parents'].items()}
   if old:
    for k,p in now.items():
     if p['state']!=old[k]['state'] or abs(p['hours']-old[k]['hours'])>=4:
      self.fact('work/'+k+'/'+p['state']+'/'+str(p['hours']),'働き方の実際が変わった',f'{self.names[k]}の実働は週{old[k]["hours"]:g}時間から{p["hours"]:g}時間へ。今は「{EMPLOYMENT.get(p["state"],p["state"])}」。給与の振込とは時期を分けて確認する。',['A.completed.parents/'+k],'native_A_unverified_employment',permanent=True)
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
    self.fact('reserve-underfunded','取り置きも見直す',f'月次の入出金後、口座残高に合わせて活動費の取り置きを減らした。法的に保護された別口座ではなく、家計内の目的別メモとして扱う。',['A.completed.transactions','C2.envelopes'],'cash_budget_reconciliation',cooldown=6)
   self.time_used={};self.flush();self.maybe_event()
   if self.game.finished:self.running=False
  self.revision+=1;self.game.core.assert_consistent()
 def view(self):
  v=self.game.view(self.actor);a=self.game.core.a;people={p['person_id']:p for p in a['persons']};parents=[]
  for k,p in a['parents'].items():parents.append({'role':k,'name':self.names[k],'age':people[k]['age_years'],'education':people[k]['attributes'].get('education'),'occupation':people[k]['attributes'].get('occupation'),'usual_annual':p['normal_annual'],'state':next(q['status'] for q in v['household']['parents'] if q['id']==k),'hours':p.get('actual_weekly_hours'),'is_player':k==self.actor})
  event=next((e for e in self.events if e['id']==self.current_event),None)
  public_event={k:copy.deepcopy(event[k]) for k in ['id','kind','title','background','date','participants','why_now','choices','evidence','source_refs']} if event else None
  recent=self.logs[-1] if self.logs else None
  return {'version':VERSION,'revision':self.revision,'date':self.date,'age_months':v['age_months'],'age_days':v['age_days'],'phase':self.phase,'running':self.running,'speed':self.speed,'elapsed_ms':self.elapsed_ms,'finished':self.game.finished,'actor':self.actor,'player_name':self.names[self.actor],'child_name':v['child_name'],'location':PREFECTURES[int(a['household']['prefecture_code'])-1]+v['household']['municipality'],'parents':parents,'policy':self.policy,'work_preference_override':self.work_preference_override,'policies':POLICIES,'logs':copy.deepcopy(self.logs[-75:]),'latest_child':next((x for x in reversed(self.logs) if x['key'].startswith(('experience/','observed-skill/'))),None),'event':public_event,'past_events':[{'id':e['id'],'title':e['title'],'choice':e.get('chosen'),'status':e['status'],'date':e['date'],'result':{k:e.get('result',{}).get(k) for k in ['status','reason','kind','id','paid_yen','hours']}} for e in self.events[-6:]],'last_choice_result':self.choice_result(),'money':self.financial_view(),'time':self.budget(),'inventory':copy.deepcopy(self.inventory),'care':v['household']['care'],'reports':v['child'],'portrait':[{'signal':c['signal'],'text':c['text'],'sources':c['sources']} for c in v['child']['cards'] if c['sampled'] and c['present']][:3],'limits':'活動の反応と配偶者の合意は未校正の体験シナリオ。長期能力・愛着への追加効果はなし。家計・就業・保育はA研究版の未検証部分を継承。'}
 def choice_result(self):
  e=next((e for e in reversed(self.events) if e['status']=='chosen'),None)
  if not e:return None
  c=next(c for c in e['choices'] if c['id']==e['chosen']);r=e['result']
  request=next((q for q in self.requests if q['id']==r.get('id')),None)
  return {'event_id':e['id'],'title':c['title'],'status':r.get('status','executed'),'reason':r.get('reason'),'observed_reaction':next((x['reaction'] for x in self.experiences if x['id']==r.get('experience_id')),None),'counterparty':next((self.names.get(x['person'],'家族')+'は「'+x['action']+'」予定を実行した。' for x in reversed(self.partner_history) if x['source_task']==r.get('id')),None),'cash_delta':e['after']['accounts']['cash']-e['before']['accounts']['cash'],'new_experiences':e['after']['experience_count']-e['before']['experience_count'],'time_hours':r.get('hours',r.get('time_hours',0)),'native_results':copy.deepcopy(request['results']) if request else [],'followup':'希望を送ったところです。次の月次処理で結果を確認します。' if request and not request['results'] else '実際に動いた口座・予定枠・経験を記録しています。','evidence':e['evidence']}
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
