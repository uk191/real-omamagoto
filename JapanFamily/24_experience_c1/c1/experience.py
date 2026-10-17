"""Father's agency layer. Native A/B source is unchanged.
C1 expenses/transfers are native balanced Ledger transactions between A periods.
Acute activity/familiarity responses are explicitly uncalibrated scenarios; they
never feed B development, attachment, physical health or future ability.
"""
import copy,datetime as dt,gzip,json,math,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'23_experience_c01'))
from c01.experience import Experience as Previous
from c0.game import Game
from c0.bridge import digest
from c0.catalogue import PREFECTURES
from . import VERSION

# Prices/durations are game offers, not estimates of national market prices.
CATALOGUE={
 'voice':dict(title='抱っこして、声をかける',place='自宅',hours=.25,cost=0,min_age=0,care=True,group='子と過ごす',context='voice'),
 'book':dict(title='絵本を一緒に開く',place='自宅',hours=.5,cost=1200,min_age=2,care=True,group='子と過ごす',context='book',item='book'),
 'toy':dict(title='手に取りやすい玩具で遊ぶ',place='自宅',hours=.5,cost=1600,min_age=4,care=True,group='子と過ごす',context='toy',item='toy'),
 'floor':dict(title='床の安全な場所で一緒に遊ぶ',place='自宅',hours=.5,cost=0,min_age=3,care=True,group='子と過ごす',context='floor'),
 'park':dict(title='近所の公園に出かける',place='近所の公園',hours=1.5,cost=0,min_age=1,care=False,group='外に出る',context='park'),
 'center':dict(title='親子向けのひろばへ出かける',place='地域の親子ひろば（仮の施設）',hours=2,cost=300,min_age=3,care=False,group='外に出る',context='center'),
 'trip':dict(title='家族で一泊の旅行を相談する',place='近隣の宿泊先（仮の旅行商品）',hours=16,cost=28000,min_age=6,care=False,agreement=True,group='家族と相談',context='trip'),
 'handover':dict(title='週末に2時間、育児を引き受ける',place='自宅',hours=2,cost=0,min_age=0,care=False,agreement=True,group='家族と相談',context='handover'),
 'nursery_visit':dict(title='保育園見学の予定を相談する',place='保育施設（仮の見学枠）',hours=2,cost=500,min_age=0,care=False,agreement=True,group='家族と相談',context='nursery_visit'),
}
LABELS={'cash':'通貨性預貯金（世帯・支払い口座）','term':'定期性預貯金（世帯）','securities':'有価証券（世帯）','insurance_reserve':'保険準備金','other_financial':'その他金融資産','other_property':'その他不動産等','home':'現在の持家評価','L:mortgage':'住宅・土地の借入','L:other_debt':'その他借入'}
def u(*parts):return int(digest(parts)[:13],16)/float(16**13)
def yen(n):return f'{int(n):,}円'

def restore_game(body,engine):
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp)/'native.gz'
  with gzip.open(p,'wt',encoding='utf-8') as f:json.dump({'payload':body,'sha256':digest(body)},f,ensure_ascii=False)
  return Game.load(p,engine)

class Experience:
 @classmethod
 def start(cls,engine,**settings):
  allowed={'prefecture_code','seed','birth_date','conditions','child_name','father_name','mother_name','background','initial_cash_yen','child_seed'}
  if set(settings)-allowed:raise ValueError('開始条件を確認してください。')
  for k in ['father_name','mother_name','background']:
   if not isinstance(settings.get(k,''),str) or len(settings.get(k,''))> (600 if k=='background' else 24):raise ValueError('名前または経歴が長すぎます。')
  cond=copy.deepcopy(settings.get('conditions') or {});cond['partner_present']=True
  legacy={k:v for k,v in settings.items() if k in {'prefecture_code','seed','birth_date','conditions','child_name','initial_cash_yen'}};legacy['conditions']=cond
  legacy.setdefault('seed',0)
  old=Previous.start(engine,**legacy)
  obj=cls();obj.game=old.game;obj.settings=copy.deepcopy(settings)
  if settings.get('child_seed') is not None:
   # Same A household; a separately identified child stream, never mutate a child after generation.
   obj.game=Game.start(engine,prefecture_code=legacy.get('prefecture_code','13'),seed=legacy['seed'],birth_date=legacy.get('birth_date','2026-10-01'),conditions=cond,child_name=legacy.get('child_name','はる'),child_seed=settings['child_seed'],research_scenario=obj.game.config['research_scenario'])
  if not {'father','mother'}<=set(obj.game.core.a['parents']):raise ValueError('C-1は父親と配偶者が同居する家庭を対象にしています。')
  obj.names={'father':settings.get('father_name') or old.names['father'],'mother':settings.get('mother_name') or old.names['mother']}
  obj.revision=0;obj.phase=0;obj.running=False;obj.speed=1;obj.logs=[];obj.plans=[];obj.inventory={};obj.experiences=[];obj.wife_actions=[];obj.finance=[];obj.time_used={};obj.months=[];obj.agreements=[];obj.alert=None
  obj.initial_accounts=copy.deepcopy(obj.game.core.a['accounts']);obj.initial_family=copy.deepcopy(obj.game.core.a['initial_family'])
  obj.npc={'wish':'quiet_weekend' if u(legacy['seed'],'wife_wish')<.5 else 'shared_outing','monthly_rest_received':0}
  obj.intro=f'{obj.names["father"]}として、{legacy.get("child_name","はる")}との暮らしを始める。経歴のうち、統計から分からない過去は未設定のままです。'
  return obj
 @property
 def date(self):return self.game.core.child._state['as_of_date']
 @property
 def month(self):return len(self.game.turns)
 def emit(self,title,text,refs,kind='C1_game_scenario',links=None):
  self.logs.append({'id':f'life-{len(self.logs):05d}','date':self.date,'period':self.month,'phase':self.phase,'title':title,'text':text,'source_refs':refs,'evidence':kind,'links':links or []})
 def context(self):
  h=self.game.view('father')['household'];a=self.game.core.a;p=a['parents']['father']
  return f'{self.names["father"]}は{next(p['status'] for p in h['parents'] if p['id']=='father')}。支払い口座は{yen(a["accounts"]["cash"])}。保育は「{h["care"]["status"]}」。勤務の希望は職場の結果が出るまで未確定です。'
 def quote(self,kind):
  q=copy.deepcopy(CATALOGUE[kind]);q['kind']=kind
  if q.get('item') in self.inventory:q['cost']=0;q['title']+='（家にあるもの）'
  age=self.game.core.elapsed_months;q['available']=age>=q['min_age'] and not self.game.finished
  q['reason']=f'生後{q["min_age"]}か月からの体験枠' if not q['available'] else ('家族の合意を確認してから予定に入れます。' if q.get('agreement') else '今月の予定に入れ、暮らしの進行中に実行します。')
  q['cost_basis']='C1価格・時間シナリオ。実在する商品・施設の調査値ではありません。'
  return q
 def budget(self):
  a=self.game.core.a;row=a.get('last_month');p=a['parents']['father'];time=(row or {}).get('time',{}).get('parents',{}).get('father')
  if time:care=time['active_care']*4;rest=time['rest']*4;basis='前月のA時間配分×4週を今月の計画枠に使う仮定'
  else:
   work=p['normal_weekly_hours'] if p['state']=='working' else 0
   care=28*4;rest=max(0,168-56-work-5-28-14)*4;basis='開始時の通常勤務から作る4週間の計画枠（未校正）'
  return {'care':max(0,care-self.time_used.get('care',0)),'rest':max(0,rest-self.time_used.get('rest',0)),'basis':basis,'used':copy.deepcopy(self.time_used),'wife_rest_hours':self.npc['monthly_rest_received']}
 def plan(self,kind,repeat=False):
  if self.game.finished:raise ValueError('24か月の記録を終えています。')
  if type(repeat) is not bool:raise ValueError('繰り返しの指定を確認してください。')
  if kind not in CATALOGUE:raise ValueError('選べる予定を指定してください。')
  q=self.quote(kind)
  if not q['available']:raise ValueError(q['reason'])
  if len([p for p in self.plans if p['status']=='queued'])>=3:raise ValueError('今月に予約できる予定は3件です。実行後に追加できます。')
  if any(p['kind']==kind and p['period']==self.month and p['status'] in ['queued','done'] for p in self.plans):raise ValueError('同じ活動は今月1回です。来月また予定できます。')
  rec={'id':f'plan-{len(self.plans):04d}','period':self.month,'date_requested':self.date,'kind':kind,'quote':q,'status':'queued','background':self.context(),'outcome':None,'linked_experience':None,'repeat':repeat}
  if q.get('agreement'):
   # A distinct NPC response, driven by her stated wishes and resource constraints.
   rest=self.budget()['rest'];cash=self.game.core.a['accounts']['cash'];mother=self.game.core.a['parents']['mother'];reasons=[]
   if q['cost']>cash:reasons.append('今の支払い口座から旅費や費用を出せない')
   if q['hours']>rest:reasons.append('今月の予定枠を確保できない')
   if kind=='trip' and mother['state']=='maternity':reasons.append('産後休業中は泊まりの予定を見送りたい')
   if kind=='trip' and self.npc['wish']=='quiet_weekend' and not self.agreements:reasons.append('先に家で休める時間を相談したい')
   if reasons:
    rec['status']='declined';rec['outcome']=f'{self.names["mother"]}「'+ '。'.join(reasons)+'。今回は見送ろう」'
   else:
    rec['outcome']=f'{self.names["mother"]}「'+ ('その間は自分の用事を済ませたい。お願いね' if kind=='handover' else '費用と時間を確認したよ。この予定で進めよう')+'」'
    self.agreements.append({'plan_id':rec['id'],'date':self.date,'kind':kind,'status':'agreed','rule':'unvalidated_NPC_schedule_scenario'})
   rec['agreement_basis']='配偶者の発言・合意はC1の人物シナリオ。実在する親の心理の予測ではない。'
  self.plans.append(rec);self.revision+=1;return rec
 def cancel(self,id):
  p=next((p for p in self.plans if p['id']==id),None)
  if not p or p['status']!='queued':raise ValueError('まだ実行していない予定だけ取り消せます。')
  p.update(status='cancelled',repeat=False,outcome='実行前に取り消した。費用・時間は使っていない。繰り返し予定も止めた。');self.revision+=1
 def transact(self,kind,n,ref):
  # No forecast exists during C1 phases; edits are explicit balanced interperiod transactions.
  assert self.game.core.forecast is None
  from ledger import Ledger
  a=self.game.core.a;l=Ledger(a['accounts'],self.date)
  if kind=='expense':
   if a['accounts']['cash']<n:raise ValueError('支払い口座の残高が足りません。定期預金等を自動で使うことはしません。')
   l.expense_due('C1/'+ref,n,{'source':'C1_price_scenario','plan_id':ref});l.pay('L:AP:C1/'+ref,n)
  else:
   source,target=('term','cash') if kind=='withdraw' else ('cash','term')
   if a['accounts'].get(source,0)<n:raise ValueError('振替元の残高が足りません。')
   l.transfer(source,target,n)
  rec={'id':f'finance-{len(self.finance):04d}','date':self.date,'period':self.month,'ref':ref,'kind':kind,'entries':copy.deepcopy(l.entries),'check':l.check()};self.finance.append(rec);return rec
 def react(self,plan):
  s=self.game.core.child._state;kind=plan['kind'];q=plan['quote'];t=s['latent_state'];e=s['emotion_regulation'];age=s['age_days']/30.4375
  past=[x for x in self.experiences if x['context']==q['context']];recent=past[-1] if past else None
  # Memory is exposure/familiarity bookkeeping, never autobiographical recall.
  familiarity=math.exp(-max(0,(dt.date.fromisoformat(self.date)-dt.date.fromisoformat(recent['date'])).days)/90) if recent else 0
  stimulation={'voice':.15,'book':.35,'toy':.5,'floor':.5,'park':.8,'center':1.1,'trip':1.4,'handover':.2,'nursery_visit':1.0}[kind]
  load=-1.5+.45*t['reactivity']+.4*t['sensory_sensitivity']+.8*e['fatigue']+stimulation-.5*familiarity
  engagement=-.25+.35*t['attention_orientation']+.35*t['approach']+.25*t['exploration']+min(age,18)*.035+.3*familiarity
  prob_distress=1/(1+math.exp(-load));prob_engage=1/(1+math.exp(-engagement));key=[self.settings.get('seed',0),s['random_streams']['seed'],self.date,plan['id'],kind]
  stopped=u(*key,'stop')<prob_distress
  engaged=u(*key,'engage')<prob_engage
  # A father sees only the sampled behaviour, never these probabilities/traits.
  if stopped:reaction='途中で泣き出したため、いったん切り上げて静かな場所で過ごした。'
  elif kind=='voice':reaction='声をかけると、顔の方へ視線を向けた。' if engaged else '抱っこの中でしばらく周囲を見ていた。'
  elif kind=='book':reaction=('ページに手を伸ばした。' if age>=6 else '開いたページへ視線を向けた。') if engaged else '絵本より、そばの人の方を見ていた。'
  elif kind in ['floor','toy']:reaction=('手を伸ばして触れた。' if age>=5 else '近くの物を目で追った。') if engaged else 'しばらく見た後、別の方へ顔を向けた。'
  else:reaction='周りの音や人の方へ何度か視線を向けた。' if engaged else '抱っこの中で周囲を見た後、顔を寄せていた。'
  eid=f'experience-{len(self.experiences):05d}';record={'id':eid,'date':self.date,'age_days':s['age_days'],'plan_id':plan['id'],'context':q['context'],'place':q['place'],'participants':[self.game.core.identity['person_links']['father'],self.game.core.identity['index_global_person_id']]+([self.game.core.identity['person_links']['mother']] if q.get('agreement') and kind!='handover' else []),'previous_experience_id':recent['id'] if recent else None,'exposure_count':len(past)+1,'observed_reaction':reaction,'ended_early':stopped,'engaged':engaged,'research_only':{'familiarity':familiarity,'prob_distress':prob_distress,'prob_engage':prob_engage,'trait_source':'B.latent_state','state_source':'B.emotion_regulation'},'evidence':'C1_unvalidated_acute_context_scenario','long_term_development_effect':False,'parent_knows':True}
  self.experiences.append(record);return record
 def execute(self,p):
  q=self.quote(p['kind']);p['quote_at_execution']=q;bucket='care' if q['care'] else 'rest'
  try:
   if self.budget()[bucket]<q['hours']:raise ValueError('今月に確保した時間枠が足りず、延期した。')
   tx=self.transact('expense',q['cost'],p['id']) if q['cost'] else None
   self.time_used[bucket]=self.time_used.get(bucket,0)+q['hours']
   if q.get('item'):self.inventory[q['item']]={'acquired':self.date,'plan_id':p['id']}
   if p['kind']=='handover':
    self.npc['monthly_rest_received']+=q['hours']
    self.wife_actions.append({'id':f'wife-{len(self.wife_actions):04d}','date':self.date,'period':self.month,'source_plan_id':p['id'],'person_id':self.game.core.identity['person_links']['mother'],'activity':'家の中でひとりで休む' if self.npc['wish']=='quiet_weekend' else '近所をひとりで散歩する','hours':q['hours'],'time_source':'father takes over two hours of existing maternal childcare; total awake supervision unchanged','evidence':'C1_independent_NPC_schedule_scenario'})
   reaction=self.react(p);p.update(status='done',executed_date=self.date,linked_experience=reaction['id'],finance_id=tx['id'] if tx else None,actual_cost=q['cost'],actual_hours=q['hours'],time_bucket=bucket,outcome=reaction['observed_reaction'])
   return f'{self.names["father"]}は{self.game.config["child_name"]}と{q["place"]}で「{q["title"]}」。{reaction["observed_reaction"]}'+(f'以前の同じ場所・活動から{reaction["exposure_count"]}回目の記録。' if reaction['previous_experience_id'] else '')+(f' {self.names["mother"]}は、その間「{self.wife_actions[-1]["activity"]}」予定を実行した。' if p['kind']=='handover' else '')+f' 費用{yen(q["cost"])}、予定枠{q["hours"]}時間。'
  except ValueError as ex:p.update(status='deferred',outcome=str(ex));return f'「{q["title"]}」は実行できなかった。{ex}'
 def request(self,kind,value=None):
  if self.game.finished:raise ValueError('24か月の体験を終えています。')
  allowed={'shorter','normal_hours','leave','return','job_search','nursery','allowance','support','spending','save_money','withdraw_money','wife_return','accept_offer','reject_offer'}
  if kind not in allowed:raise ValueError('選べない相談です。')
  bg=self.context();record={'id':f'decision-{len(self.agreements):04d}','date':self.date,'period':self.month,'kind':kind,'background':bg,'status':'requested','evidence':'native_A_unvalidated_household_scenario'}
  if kind in ['save_money','withdraw_money']:
   if type(value) is not int or not 1<=value<=10000000:raise ValueError('振替額を1〜1000万円で指定してください。')
   record['finance']=self.transact('withdraw' if kind=='withdraw_money' else 'saving',value,record['id']);record['status']='done';record['message']=(f'定期性預貯金から支払い口座へ{yen(value)}を振り替えた。' if kind=='withdraw_money' else f'支払い口座から定期性預貯金へ{yen(value)}を振り替えた。')+'世帯の純資産は変わらない。解約条件・手数料は未実装の振替シナリオ。'
  elif kind=='wife_return':
   # Wife owns her employment. She states a counterproposal rather than being controlled.
   m=self.game.core.a['parents']['mother'];record['status']='counterproposal';record['message']=f'{self.names["mother"]}「仕事の復帰は私も決めたい。まず保育の申請状況と、あなたの分担を確認しよう」'
   if self.game.core.a['care'].get('application') and self.npc['monthly_rest_received']>=2:
    n=self.game.core.a['elapsed_months']+2
    self.game.request('request_return',person='mother',value=min(24,n));record['status']='agreed_requested';record['message']=f'{self.names["mother"]}「まず{n}か月時点での復帰を相談してみる」';record['native_action_id']=self.game.queue[-1]['id']
  else:
   mapping={'shorter':('request_hours','father',.8),'normal_hours':('request_hours','father',1.),'leave':('take_leave','father',None),'return':('request_return','father',min(24,self.game.core.a['elapsed_months']+1)),'job_search':('job_search','father',None),'nursery':('apply_childcare',None,None),'allowance':('apply_child_allowance',None,None),'support':('request_relative_support',None,None),'spending':('set_spending',None,.9)}
   if kind in ['accept_offer','reject_offer']:
    offer=self.game.core.a['parents']['father'].get('job_offer')
    if not offer:raise ValueError('届いている仕事の提案はありません。')
    mapped=('accept_job_offer' if kind=='accept_offer' else 'reject_job_offer','father',offer['id'])
   else:mapped=mapping[kind]
   if kind in ['nursery','spending']:
    record['spouse_statement']=f'{self.names["mother"]}「'+('申請しても入園はまだ決まらないね。結果を待とう' if kind=='nursery' else '生活費を1割抑える方針だね。必要な支払いは残そう')+'」'
    record['agreement_rule']='C1 explicit cooperative discussion scenario'
   self.game.request(mapped[0],person=mapped[1],value=mapped[2]);record['native_action_id']=self.game.queue[-1]['id'];record['message']='希望を伝えた。次の月次処理で、実現したことと実現しなかった理由を確認する。'
  self.agreements.append(record);self.revision+=1;return record
 def tick(self):
  if self.game.finished:return
  self.phase+=1;self.elapsed_ms=0
  if self.phase in [1,2]:
   queued=[p for p in self.plans if p['status']=='queued'];limit=1 if self.phase==1 else 3
   selected=queued[:limit];texts=[self.execute(p) for p in selected]
   if texts:self.emit('子と過ごした時間' if self.phase==1 else '暮らしの予定','\n'.join(texts),['C1.plans/'+p['id'] for p in selected],links=[p.get('linked_experience') for p in selected if p.get('linked_experience')])
   elif self.phase==1:
    # Native father-observation only; no new health/trait effects.
    self.game.observe('observe',observer='father');cards=self.game.view('father')['child']['cards'];seen=next((c for c in cards if c['sampled'] and c['present']),None)
    self.emit('何も予定のない日も',f'{self.names["father"]}は自宅で{self.game.config["child_name"]}の様子を見た。'+(seen['text'] if seen else 'この場面では、はっきりした変化を記録できなかった。'),['B.father_observations'],'B_uncalibrated_observation')
   # At most three life entries per period, no invented obligatory dramatic event.
  else:
   before=copy.deepcopy(self.game.core.a['accounts']);self.game.advance(reviewed=True,observer='father');self.phase=0
   turn=self.game.turns[-1];h=self.game.view('father')['household'];dec=turn['decisions'];bits=[]
   for d in dec:
    related=next((a for a in self.agreements if a.get('native_action_id')==d.get('request_id')),None)
    if related:related.setdefault('results',[]).append(copy.deepcopy(d))
    bits.append(d['text'])
   if not bits:
    f=next(p for p in h['parents'] if p['id']=='father');bits.append(f'{self.names["father"]}は「{f["status"]}」。実働は'+(f'週{f["weekly_hours"]:g}時間。' if f['weekly_hours'] is not None else '未記録。'))
   bits.append(f'支払い口座は{yen(before["cash"])}から{yen(self.game.core.a["accounts"]["cash"])}へ。')
   notices=self.game.view('father')['child'].get('notices',[])
   if notices:bits.append(notices[0] if isinstance(notices[0],str) else notices[0]['text'])
   self.emit('ひと月が過ぎて',' '.join(bits),['A.completed.periods/'+str(len(self.game.core.a_periods)-1),'B.father_observations'],'native_AB_research_model')
   self.months.append({'date':self.date,'period':self.month,'household':h,'C1_finance_ids':[x['id'] for x in self.finance if x['period']==self.month-1],'time_used':copy.deepcopy(self.time_used),'wife_rest_hours':self.npc['monthly_rest_received'],'native_decisions':copy.deepcopy(dec)})
   self.time_used={};self.npc['monthly_rest_received']=0
   if not self.game.finished:
    for p in list(self.plans):
     if p['period']==self.month-1 and p.get('repeat') and p['status'] in ['done','deferred']:
      self.plan(p['kind'],repeat=True)
   critical=[p for p in self.game.view('father')['pauses'] if p.get('kind') in ['cash_shortage','care_work_conflict','job_offer_proposed']]
   offer=self.game.core.a['parents']['father'].get('job_offer')
   if critical or offer:self.running=False;self.alert='仕事・保育・支払いについて確認したい記録があります。暮らしの相談欄を確認してください。'
   if self.game.finished:self.running=False
  self.revision+=1;self.game.core.assert_consistent()
 def wife_statement(self):
  p=self.game.core.a['parents']['mother'];recent=[x for x in self.wife_actions if self.month-1<=x['period']<=self.month]
  if recent:return f'この前は{recent[-1]["hours"]:g}時間、育児を代わってくれたね。次の予定も分担を相談したい。'
  if p.get('actual_weekly_hours',0)>0:return f'今は週{p["actual_weekly_hours"]:g}時間働いているから、予定は分担を確認してから決めたい。'
  if self.game.core.a['care'].get('application'):return '保育の申請は出したね。まだ希望と実現したことを分けて考えよう。'
  return '今月は家で休める時間もほしいな。' if self.npc['wish']=='quiet_weekend' else '無理のない範囲で、一緒に外に出る予定も考えたいな。'
 def view(self):
  v=self.game.view('father');a=self.game.core.a;people={p['person_id']:p for p in a['persons']};profiles={}
  for role in ['father','mother']:
   p=people[role];at=p['attributes'];job=a['parents'][role]
   profiles[role]={'name':self.names[role],'age':p['age_years'],'education':at.get('education'),'occupation':at.get('occupation'),'industry':job.get('industry'),'usual_annual':job['normal_annual'],'usual_hours':job['normal_weekly_hours'],'status':next(x['status'] for x in v['household']['parents'] if x['id']==role),'actual_hours':job.get('actual_weekly_hours'),'id':self.game.core.identity['person_links'][role]}
  cash=a['accounts']['cash'];last=self.months[-1]['household']['budget'] if self.months else None
  tx=self.game.core.a_periods[-1]['A_transactions'] if self.game.core.a_periods else []
  flows={'received':sum(max(0,t['deltas'].get('cash',0)) for t in tx if t['kind'] not in ['asset_transfer','authorized_borrow']),'paid':-sum(min(0,t['deltas'].get('cash',0)) for t in tx if t['kind']!='asset_transfer'),'extra_C1_paid':sum(-min(0,e['deltas'].get('cash',0)) for f in self.finance if f['period']==self.month for e in f['entries'] if f['kind']=='expense'),'period':self.game.core.a_periods[-1]['start'] if self.game.core.a_periods else None}
  flows['paid']+=sum(-min(0,e['deltas'].get('cash',0)) for f in self.finance if f['period']==self.month-1 and f['kind']=='expense' for e in f['entries'])
  # Whitelist: no core state, trait probabilities, hidden wife's policy, private forecasts.
  return {'version':VERSION,'revision':self.revision,'date':self.date,'age_months':v['age_months'],'age_days':v['age_days'],'phase':self.phase,'finished':self.game.finished,'running':self.running,'speed':self.speed,'child_name':v['child_name'],'location':PREFECTURES[int(a['household']['prefecture_code'])-1]+v['household']['municipality'],'profiles':profiles,'background':self.settings.get('background') or '過去の勤務先・貯蓄の経緯は未設定。現在の学歴・職業・通常所得は統計を参照して生成しています。','intro':self.intro,'wife_statement':self.wife_statement(),'wife_recent_actions':copy.deepcopy(self.wife_actions[-3:]),'assets':{'cash':cash,'opening':self.initial_accounts,'current':{LABELS.get(k,k):val for k,val in a['accounts'].items() if k in LABELS},'net_worth':sum(val if not k.startswith('L:') else -val for k,val in a['accounts'].items()),'ownership':'世帯の残高。夫婦それぞれの所有持分は資料から識別できず、父親個人の財産とは表示しません。','basis':'2024年の住宅ローン有無・可処分所得帯・世帯規模別の資産統計を移送。親の年齢との同時分布、資産間の相関、2026年出生家庭への適合は未確認。','explicit_cash_scenario':self.settings.get('initial_cash_yen') is not None,'last_budget':last,'cash_flows':flows},'budget_time':self.budget(),'care':v['household']['care'],'native_pauses':v['pauses'],'child':v['child'],'catalogue':[self.quote(k) for k in CATALOGUE],'plans':copy.deepcopy(self.plans[-12:]),'inventory':copy.deepcopy(self.inventory),'logs':copy.deepcopy(self.logs[-90:]),'decisions':copy.deepcopy(self.agreements[-12:]),'queued_native':v['queued_requests'],'alert':self.alert,'experience_count':len(self.experiences),'recent_experiences':[{k:x[k] for k in ['id','date','context','place','previous_experience_id','observed_reaction','evidence']} for x in self.experiences[-4:]],'elapsed_ms':getattr(self,'elapsed_ms',0),'limits':'遊び・外出の短期反応と配偶者の会話は未校正の体験シナリオ。能力・愛着への長期効果は計算しません。就業・保育・家計にはA研究版の未検証経路が残ります。','actions_context':self.context()}
 def snapshot(self):return {'version':VERSION,'native':self.game.snapshot(),'state':copy.deepcopy({k:v for k,v in self.__dict__.items() if k!='game'})}
 def save(self,path):
  p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);body=self.snapshot();env={'payload':body,'sha256':digest(body)};tmp=p.with_suffix('.tmp')
  with gzip.open(tmp,'wt',encoding='utf-8') as f:json.dump(env,f,ensure_ascii=False,sort_keys=True,allow_nan=False)
  tmp.replace(p);return env['sha256']
 @classmethod
 def load(cls,path,engine):
  with gzip.open(path,'rt',encoding='utf-8') as f:env=json.load(f)
  body=env['payload']
  if body['version']!=VERSION or digest(body)!=env['sha256']:raise ValueError('保存記録の版・ハッシュが一致しません。')
  obj=cls();obj.__dict__.update(body['state']);obj.game=restore_game(body['native'],engine);return obj
