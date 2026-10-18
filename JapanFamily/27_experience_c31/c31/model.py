"""C3.1: four consequential decisions, inheriting unchanged C3/A/B engines.
All extra effects are game-world resources, observations and commitments.
"""
import copy,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'26_experience_c3'))
from c3.model import Experience as Base,restore_game,digest,u,yen,EMPLOYMENT
from c3 import VERSION as BASE_VERSION
from . import VERSION
from .design import MAIN_AGES,LABELS,main_choices,followup_choices

class Experience(Base):
 @classmethod
 def start(cls,engine,**settings):
  policy=settings.pop('policy',None);x=super().start(engine,policy=None,**settings);x.init_decisions()
  if policy:x.set_policy(policy)
  return x
 def init_decisions(self):
  self.case_ledger=[];self.commitments=[];self.purpose_funds=[];self.project_entries=[];self.agency_trials=[];self.main_seen=[];self.decision_context_facts=[];self.handled_job_offers=[]
 def snapshot(self):
  body=super().snapshot();body['version']=VERSION;return body
 @classmethod
 def load(cls,path,engine):
  with gzip.open(path,'rt',encoding='utf8') as f:envelope=json.load(f)
  body=envelope['payload']
  if body['version'] not in [VERSION,BASE_VERSION] or digest(body)!=envelope['sha256']:raise ValueError('保存記録の版・ハッシュが一致しません。')
  x=cls();x.__dict__.update(body['state']);x.game=restore_game(body['native'],engine)
  if body['version']==BASE_VERSION:x.init_decisions()
  if not hasattr(x,'handled_job_offers'):x.handled_job_offers=[]
  return x
 def context(self):
  a=self.game.core.a;p=a['parents'][self.actor];row=a.get('last_month') or {}
  return {'date':self.date,'age_months':self.game.core.elapsed_months,'cash':a['accounts']['cash'],'term':a['accounts'].get('term',0),'spending_factor':a['spending_factor'],'parent_state':p['state'],'actual_weekly_hours':p.get('actual_weekly_hours',0),'usual_annual':p['normal_annual'],'hours_ratio':p['hours_ratio'],'care':a['care']['status'],'actual_gross_earned':row.get('actual_earned_gross'),'time':copy.deepcopy(self.budget()),'experience_ids':[e['id'] for e in self.experiences],'inventory_ids':[v['id'] for v in self.inventory.values()],'native_queue':copy.deepcopy(self.game.queue),'job_offer':copy.deepcopy(p.get('job_offer'))}
 def quote_operation(self,op):
  kind=op['op'];q={'cost_yen':0,'transfer_yen':0,'hours':0,'bucket':'rest','when':op.get('when',0),'minimum_age':0}
  if kind=='activity':
   a=self.quote_activity(op['kind']);q.update(cost_yen=a['cost'],hours=a['hours'],bucket=a['bucket'],minimum_age=a['min_age'])
  elif kind=='request':q['hours']=.5
  elif kind in ['entry','private_album','work_time']:q['hours']=op['hours']
  elif kind=='agency':q.update(hours=1,bucket='care')
  elif kind=='saving':q['transfer_yen']=op['yen']
  return q
 def quote_options(self,options):
  public=[]
  for c in options:
   c=copy.deepcopy(c);quotes=[self.quote_operation(o) for o in c['ops']]
   # Estimate future material reuse after planned first purchases.
   virtual=set(self.inventory);total=0
   for op,q in zip(c['ops'],quotes):
    if op['op']=='activity':
     item=self.quote_activity(op['kind']).get('item')
     if item in virtual:q['cost_yen']=0
     if item:virtual.add(item)
    total+=q['cost_yen']
   immediate=sum(q['cost_yen'] for q in quotes if not q['when']);hours=sum(q['hours'] for q in quotes);transfers=sum(q['transfer_yen'] for q in quotes)
   reason=None
   if immediate+sum(q['transfer_yen'] for q in quotes if not q['when'])>self.game.core.a['accounts']['cash']:reason='今の支払い口座では、最初の支出・振替ができない'
   for bucket in ['care','rest']:
    need=sum(q['hours'] for q in quotes if q['bucket']==bucket and not q['when'])
    if need>self.budget()[bucket]:reason='今月の'+('育児' if bucket=='care' else '余暇・手続き')+'の枠が足りない'
   c.update(cost_yen=immediate,planned_cost_yen=total-immediate,hours=hours,transfer_yen=transfers,detail=c['gain']+'／'+c['forgo'],disabled=bool(reason),disabled_reason=reason,quotes=quotes)
   public.append(c)
  return public
 def background(self,code,parent_case=None):
  ctx=self.context();child=self.game.config['child_name'];actor=self.names[self.actor]
  if parent_case:
   effects=self.case_effects(parent_case);exps=[e for e in self.experiences if e['id'] in effects['experience_ids']]
   first='前に選んだのは「'+parent_case['choice_title']+'」。'
   if exps:
    last=exps[-1];first+=last['date'][:7]+'、'+last['place']+'では「'+last['short_observation']+'」という場面が残った。'
   failures=[o.get('reason') for o in self.commitments if o['case_id']==parent_case['id'] and o['status']=='not_realized']
   if failures:first+=' 実現しなかった予定もある：'+failures[0]+'。'
   if code=='C':first+=f' 直近の実働は週{ctx["actual_weekly_hours"]:g}時間、今の勤務希望は{ctx["hours_ratio"]*100:g}％。給与の発生と入金を分けて確かめる。'
   projects=[p for p in self.project_entries if p['case_id']==parent_case['id']]
   if projects:first+=' 企画は「'+{'selected':'展示に選ばれた','not_selected':'今回は展示に選ばれなかった','declined':'公開の合意ができず応募を見送った','awaiting_result':'まだ結果を待っている'}.get(projects[-1]['status'],projects[-1]['status'])+'」。'
   funds=[f for f in self.purpose_funds if f['case_id']==parent_case['id']]
   if funds:first+=' 旅費の目的メモとして残る額は'+yen(sum(f['remaining_yen'] for f in funds))+'。'
   return first+' この続きは、どう過ごそうか。'
  recent=self.scenes[-1] if self.scenes else None
  observed=(recent['date'][:7]+'、'+recent['place']+'で'+child+'は「'+recent['short_observation']+'」。') if recent else child+'との暮らしの予定を考える。'
  facts=f'支払い口座は{yen(ctx["cash"])}、今月の余暇・手続きの枠はあと{ctx["time"]["rest"]:g}時間。'
  if code=='A':return observed+' 休日に少し遠くへ行く話が出た。一回の遠出に使うか、近場で何度も過ごすか、それとも今は別のことを優先するか。'+facts
  if code=='B':return observed+' 一度の反応で「好き」とは決められない。次にこの子の前へ何を置くか、どのように待つかを考える。'+facts
  if code=='C':
   offer=ctx['job_offer'];partner=(' 家では'+self.names[self.partner]+'は「'+EMPLOYMENT.get(self.game.core.a['parents'][self.partner]['state'],'就業を調整中')+'」、保育は「'+self.game.view(self.actor)['household']['care']['status']+'」。') if self.partner else ' 自分が主に家の予定を組み、保育や支援も確かめる必要がある。'
   trigger=(actor+'宛てに、通常年収'+yen(offer['normal_annual'])+'・週'+str(offer['normal_weekly_hours'])+'時間の仕事の提案が届いた。希望だけで就業が決まるわけではない。' if offer else actor+'は来月の勤務希望を出す前に、家で使う時間と生活費を並べてみた。')
   return trigger+f' 今は「{EMPLOYMENT.get(ctx["parent_state"],"就業を調整中")}」、直近の実働は週{ctx["actual_weekly_hours"]:g}時間、通常年収は{yen(ctx["usual_annual"])}。'+partner+observed+' 仕事の準備にも、家で待つ時間にも同じ自分の時間を使う。'+facts

  return '架空の「こもれび親子の部屋」で、家族の日常写真を飾る企画がある。参加費は不要、展示枠はゲーム内の抽選で、子どもの容姿や能力の評価ではない。公開写真は家族名付き、匿名作品なら顔と名前を出さずに参加できる。写真を家族内に残す、応募せず会場へ行く、という選び方もある。'+facts
 def offer_main(self,code):return self.offer_decision(code)
 def offer_decision(self,code,parent_case=None):
  if self.current_event or self.game.finished:return False
  options=self.quote_options(followup_choices(self,parent_case) if parent_case else main_choices(self,code))
  # Four meaningful alternatives are required. Infeasible contexts are deferred,
  # never padded with empty "do nothing" options.
  if len(options)!=4 or any(c['disabled'] for c in options):return False
  eid=f'event-{len(self.events):04d}';context=self.context();text=self.background(code,parent_case)
  record={'id':f'decision-context-{len(self.decision_context_facts):03d}','date':self.date,'domain':code,'context':context,'text':text,'source_scene_ids':[s['id'] for s in self.scenes[-2:]],'source_case_id':parent_case['id'] if parent_case else None,'evidence':'C31_contextual_game_situation_not_real_employer_or_institution_notice'}
  self.decision_context_facts.append(record)
  e={'id':eid,'kind':'decision_'+code,'domain':code,'title':('あの選択から、二か月' if parent_case else LABELS[code]),'background':text,'date':self.date,'period':self.month,'participants':[self.names[self.actor],self.game.config['child_name']]+([self.names[self.partner]] if self.partner else []),'why_now':'前の選択の結果と、今の家族の条件を確認するため。' if parent_case else '実際の月齢・観察・口座・時間から、四つの選び方を考えられるため。','choices':options,'source_refs':['C31.decision_context_facts/'+record['id']],'status':'waiting','evidence':'C31_game_scenario; native_A_feasibility_unvalidated; no_added_B_long_term_effect','parent_case_id':parent_case['id'] if parent_case else None,'voluntary':False}
  self.events.append(e);self.current_event=eid;self.last_event_month=self.month;self.running=False
  if parent_case:parent_case['followup_event_id']=eid
  else:self.main_seen.append(code)
  offer=self.game.core.a['parents'][self.actor].get('job_offer')
  if code=='C' and offer and offer['id'] not in self.handled_job_offers:self.handled_job_offers.append(offer['id'])
  return True
 def maybe_event(self):
  # Preserve the original voluntary C3 photo-project resolution, but replace only
  # its forced-choice selector with the four new structures.
  for p in self.plans:
   if p['status']=='awaiting_result' and self.month>=p['due_period']:
    selected=u(self.settings.get('seed'),'C3_photo_selection',p['id'])<.35;p['status']='selected' if selected else 'not_selected';p['result_date']=self.date
    text=('家族写真展に、一枚を飾ってもらえることになった。' if selected else '家族写真展から、今回は展示に選ばれなかったと連絡が来た。')+'応募した写真は、家族のアルバムにも残っている。'
    self.fact('project/'+p['id'],'あの一枚の、その後',text,['C3.plans/'+p['id'],'C3.scenes/'+p['source_scene_id']],'fictional_lottery_no_ability_effect',permanent=True)
    self.keepsakes.append({'id':f'memory-{len(self.keepsakes):04d}','date':self.date,'title':'家族写真展の結果','scene_id':p['source_scene_id'],'experience_id':None,'text':text,'item_id':None})
  self.refresh_outcomes()
  if self.current_event or self.game.finished:return
  if self.month-self.last_event_month<2:return
  offer=self.game.core.a['parents'][self.actor].get('job_offer')
  if offer and offer['id'] not in self.handled_job_offers:
   prior=next((c for c in reversed(self.case_ledger) if c['domain']=='C'),None)
   if self.offer_decision('C',prior):return
  due=next((c for c in self.case_ledger if c['stage']=='main' and not c.get('followup_event_id') and self.month>=c['followup_due_period']),None)
  if due and self.offer_decision(due['domain'],due):return
  for code,age in MAIN_AGES.items():
   if code not in self.main_seen and self.game.core.elapsed_months>=age:
    if self.offer_decision(code):return
 def choose(self,event_id,choice_id):
  e=next((e for e in self.events if e['id']==event_id),None)
  if not e or 'domain' not in e:return super().choose(event_id,choice_id)
  if self.current_event!=event_id:raise ValueError('現在の相談を選んでください。')
  c=next((c for c in e['choices'] if c['id']==choice_id),None)
  if c is None or c.get('disabled'):raise ValueError('実行できる選択肢を選んでください。')
  cid=f'case-{len(self.case_ledger):04d}';record={'id':cid,'event_id':event_id,'domain':e['domain'],'stage':'followup' if e.get('parent_case_id') else 'main','parent_case_id':e.get('parent_case_id'),'choice_id':c['id'],'choice_title':c['title'],'value_axis':c['value_axis'],'gain':c['gain'],'forgo':c['forgo'],'date':self.date,'period':self.month,'before':self.context(),'followup_due_period':self.month+2,'followup_event_id':None,'commitment_ids':[],'evidence':e['evidence']}
  self.case_ledger.append(record)
  for op in c['ops']:
   entry={'id':f'commitment-{len(self.commitments):04d}','case_id':cid,'event_id':event_id,'requested_date':self.date,'due_period':self.month+op.get('when',0),'operation':copy.deepcopy(op),'status':'planned','quote':self.quote_operation(op)}
   self.commitments.append(entry);record['commitment_ids'].append(entry['id'])
   if entry['due_period']==self.month:self.run_commitment(entry)
  record['after_choice']=self.context();e.update(status='chosen',chosen=choice_id,case_id=cid,result={'status':'committed','case_id':cid},before=record['before'],after=record['after_choice'])
  self.fact('decision-choice/'+cid,'この家族で、選んだこと',self.names[self.actor]+'は「'+c['title']+'」を選んだ。'+c['gain']+'。一方で、'+c['forgo']+'。',['C31.case_ledger/'+cid],'C31_committed_choice_not_a_promised_outcome',permanent=True)
  self.current_event=None;self.refresh_outcomes();self.flush();self.running=not self.game.finished;self.revision+=1
 def prepare_policy(self):
  for op in self.commitments:
   if op['status']=='planned' and op['due_period']<=self.month:self.run_commitment(op)
  super().prepare_policy()
  self.refresh_outcomes()
 def run_commitment(self,r):
  op=r['operation'];kind=op['op'];before=self.context();r['executed_date']=self.date;r['status']='executing';r['experience_ids']=[];r['task_ids']=[];r['finance_ids']=[];r['native_request_ids']=[];r['project_ids']=[]
  try:
   if kind in ['activity','agency']:
    chosen=op.get('kind')
    if kind=='agency':
     candidates=[k for k,item in [('book','book'),('music','bell'),('toy','toy'),('blocks','blocks')] if item in self.inventory]
     candidates=(candidates+['cloth','voice'])[:2]
     s=self.game.core.child._state;t=s['latent_state'];weight=.5+.1*max(-1,min(1,t['exploration']))
     chosen=candidates[0] if u(s['random_streams']['seed'],'C31_agency',self.date,r['id'])<weight else candidates[1]
     trial={'id':f'choice-trial-{len(self.agency_trials):03d}','date':self.date,'case_id':r['case_id'],'offered':candidates,'chosen':chosen,'waiting_hours':1,'evidence':'C31_unvalidated_safe_play_choice_scenario'};self.agency_trials.append(trial);r['agency_id']=trial['id']
    task=self.schedule(chosen,'decision',r['event_id'])
    if not task:raise ValueError('この月齢ではまだ予定できない遊び')
    if kind=='agency':task['quote']['hours']=1
    self.execute(task);r['task_ids'].append(task['id'])
    if task['status']!='done':raise ValueError(task['reason'])
    r['experience_ids'].append(task['experience_id'])
    if self.experiences[-1]['finance_id']:r['finance_ids'].append(self.experiences[-1]['finance_id'])
   elif kind=='request':
    request=self.own_request(op['kind'],op.get('value'),r['event_id'])
    if not request:raise ValueError('同じ希望をすでに送ったか、手続きの時間を確保できなかった')
    r['native_request_ids'].append(request['id'])
    if op['kind']=='request_hours':self.work_preference_override=op.get('value')
   elif kind=='saving':
    f=self.transfer('saving',op['yen'],r['id']);r['finance_ids'].append(f['id'])
    goal={'id':f'fund-{len(self.purpose_funds):03d}','case_id':r['case_id'],'purpose':op['purpose'],'contributed_yen':op['yen'],'remaining_yen':op['yen'],'date':self.date,'evidence':'purpose_memo_within_existing_term_deposit_not_a_protected_account'};self.purpose_funds.append(goal);r['fund_id']=goal['id']
   elif kind=='spend_fund':
    f=next(f for f in self.purpose_funds if f['id']==op['fund_id']);amount=min(f['remaining_yen'],self.game.core.a['accounts'].get('term',0))
    if not amount:raise ValueError('旅費用の預金メモを今の残高で賄えなかった')
    tx=self.transfer('withdraw',amount,r['id']);r['finance_ids'].append(tx['id']);f['remaining_yen']-=amount
   elif kind in ['private_album','entry','work_time']:
    hours=op['hours']
    if self.budget()['rest']<hours:raise ValueError('自分の余暇・手続きの時間を確保できなかった')
    self.time_used['rest']=self.time_used.get('rest',0)+hours
    if kind=='entry':
     fmt=op['format'];declined=fmt=='named_portrait' and self.partner and self.npc_wish=='quiet'
     item=next(iter(self.inventory.values()),None)
     entry={'id':f'entry-{len(self.project_entries):03d}','case_id':r['case_id'],'date':self.date,'format':fmt,'audience':'family_name_and_portrait' if fmt=='named_portrait' else 'anonymous_object_only','artifact':'家族の写真' if fmt=='named_portrait' else (item['name'] if item else '手持ちの布')+'を題材にした親の作品','status':'declined' if declined else 'awaiting_result','due_period':self.month+1,'reason':self.names[self.partner]+'は写真を家族内に残したいと伝え、公開に合意しなかった' if declined else None,'evidence':'fictional_exhibition_and_consent; appearance_independent_game_lottery'}
     self.project_entries.append(entry);r['project_ids'].append(entry['id'])
     if declined:r['status']='not_realized';r['reason']=entry['reason']
    elif kind=='private_album':
     case=next(c for c in self.case_ledger if c['id']==r['case_id']);source=case.get('parent_case_id') or case['id'];linked=[e for e in self.experiences if e['event_id']==next(c['event_id'] for c in self.case_ledger if c['id']==source)]
     text=self.names[self.actor]+'は、'+(linked[-1]['date'][:7]+'に'+linked[-1]['place']+'で過ごした記録' if linked else 'これまでの家族の記録')+'を見返す時間を取った。新しい場所へ急がず、残っている一場面を手元に置いて過ごした。'
     memory={'id':f'memory-{len(self.keepsakes):04d}','date':self.date,'title':'あの日を、家で見返す','scene_id':linked[-1]['scene_id'] if linked else None,'experience_id':linked[-1]['id'] if linked else None,'text':text,'item_id':None,'case_id':r['case_id']};self.keepsakes.append(memory)
     self.fact('reflection/'+r['id'],memory['title'],text,['C31.commitments/'+r['id']],'C31_actual_reflection_time',permanent=True)
    else:self.policy_operations.append({'period':self.month,'kind':'decision_work_preparation','hours':hours,'case_id':r['case_id'],'evidence':'reserved_time_no_extra_income'})
   else:raise ValueError('対応していない約束')
   if r['status']=='executing':r['status']='done'
  except ValueError as err:r['status']='not_realized';r['reason']=str(err)
  after=self.context();r['cash_delta']=after['cash']-before['cash'];r['term_delta']=after['term']-before['term'];r['hours_used']=sum(after['time']['used'].values())-sum(before['time']['used'].values());r['participants']=[self.game.core.identity['person_links'][self.actor]]
  if r['experience_ids']:r['participants'].append(self.game.core.identity['index_global_person_id'])
  if kind=='activity' and op.get('kind') in ['trip','handover'] and self.partner:r['participants'].append(self.game.core.identity['person_links'][self.partner])
  if r['status']=='not_realized':self.fact('unrealized/'+r['id'],'選んだあと、予定を変えた',self.names[self.actor]+'の予定は「'+r['reason']+'」ため、予定どおりには実行しなかった。',['C31.commitments/'+r['id']],'C31_unrealized_commitment',permanent=True)
 def refresh_outcomes(self):
  for p in self.project_entries:
   if p['status']=='awaiting_result' and self.month>=p['due_period']:
    selected=u(self.settings.get('seed'),'C31_exhibition',p['id'])<.35;p['status']='selected' if selected else 'not_selected';p['result_date']=self.date
    text=('架空の家族写真展に、'+('家族の写真' if p['format']=='named_portrait' else '顔や名前を出さない作品')+'が選ばれた。' if selected else '架空の家族写真展から、今回は展示に選ばれなかったと連絡が来た。')+'親が用意したものと、その日の家族の記録は手元に残っている。'
    self.fact('exhibition/'+p['id'],'用意した一枚の、その後',text,['C31.project_entries/'+p['id']],'fictional_lottery_not_child_ability_or_appearance',permanent=True)
    self.keepsakes.append({'id':f'memory-{len(self.keepsakes):04d}','date':self.date,'title':'用意した一枚の、その後','scene_id':None,'experience_id':None,'text':text,'item_id':None,'case_id':p['case_id']})
  available=self.game.core.a['accounts'].get('term',0)
  for f in self.purpose_funds:
   f['remaining_yen']=min(f['remaining_yen'],available);available-=f['remaining_yen']
 def case_effects(self,case):
  ops=[r for r in self.commitments if r['case_id']==case['id']];ids=[i for r in ops for i in r.get('experience_ids',[])];exps=[e for e in self.experiences if e['id'] in ids];reqs=[q for q in self.requests if q['id'] in [i for r in ops for i in r.get('native_request_ids',[])]]
  return {'experience_ids':ids,'expenses_yen':sum(e['paid_yen'] for e in exps),'cash_delta_direct':sum(r.get('cash_delta',0) for r in ops),'term_delta_direct':sum(r.get('term_delta',0) for r in ops),'hours_used':sum(r.get('hours_used',0) for r in ops),'planned_operations':sum(r['status']=='planned' for r in ops),'done_operations':sum(r['status']=='done' for r in ops),'unrealized':[{'id':r['id'],'reason':r.get('reason')} for r in ops if r['status']=='not_realized'],'native_results':[a for q in reqs for a in q['results']],'projects':copy.deepcopy([p for p in self.project_entries if p['case_id']==case['id']]),'funds':copy.deepcopy([f for f in self.purpose_funds if f['case_id']==case['id']]),'observed_reactions':[{'experience_id':e['id'],'date':e['date'],'place':e['place'],'text':e['reaction']} for e in exps],'memory_ids':[m['id'] for m in self.keepsakes if m.get('case_id')==case['id'] or m.get('experience_id') in ids]}
 def choice_result(self):
  e=next((e for e in reversed(self.events) if e['status']=='chosen'),None)
  if not e or not e.get('case_id'):return super().choice_result()
  c=next(c for c in self.case_ledger if c['id']==e['case_id']);f=self.case_effects(c)
  return {'event_id':e['id'],'case_id':c['id'],'title':c['choice_title'],'status':'partial' if f['unrealized'] else 'committed','reason':f['unrealized'][0]['reason'] if f['unrealized'] else None,'scene_text':f['observed_reactions'][0]['text'] if f['observed_reactions'] else None,'cash_delta':f['cash_delta_direct'],'new_experiences':len(f['experience_ids']),'time_hours':f['hours_used'],'plan':{'remaining':f['planned_operations']} if f['planned_operations'] else None,'native_results':f['native_results'],'counterparty':None,'followup':f'実支出は{yen(f["expenses_yen"])}、使った時間は{f["hours_used"]:g}時間。'+(f'あと{f["planned_operations"]}件はこれから実行する予定。' if f['planned_operations'] else 'その後の家族の様子も記録していく。'),'value_axis':c['value_axis'],'gain':c['gain'],'forgo':c['forgo'],'effects':f,'evidence':c['evidence']}
 def view(self):
  v=super().view();v['version']=VERSION
  if v['event'] and v['event']['kind'].startswith('decision_'):
   source=next(e for e in self.events if e['id']==self.current_event);v['event'].update(domain=source['domain'],parent_case_id=source.get('parent_case_id'))
   v['event']['choices']=[{k:c.get(k) for k in ['id','title','value_axis','gain','forgo','cost_yen','planned_cost_yen','hours','transfer_yen','detail','disabled','disabled_reason']} for c in v['event']['choices']]
  v['decisions']=[{'id':c['id'],'date':c['date'],'title':c['choice_title'],'domain':c['domain'],'stage':c['stage'],'effects':self.case_effects(c)} for c in self.case_ledger[-8:]]
  v['initial_generation']={'native_model':self.game.core.a['model_version'],'income_generated_from_conditions':not any(k.endswith('income_yen') for k in self.settings.get('conditions',{})),'asset_age_joint_validated':False,'deposits':self.initial_accounts['cash']+self.initial_accounts.get('term',0),'initial_cash':self.initial_accounts['cash'],'initial_term':self.initial_accounts.get('term',0),'note':'初期預金は全世代の統計を移送した推定で、親の年齢との同時分布は未校正です。本人の貯蓄経緯を再現した金額ではありません。'}
  return v
