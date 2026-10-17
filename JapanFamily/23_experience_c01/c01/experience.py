"""Deterministic player projection, contextual decisions and save wrapper.
No updates of biological traits, scientific coefficients or A accounting rules.
"""
import copy, datetime as dt, gzip, json, os, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent/'22_experience_c0'))
from c0.game import Game
from c0.bridge import digest
from c0.catalogue import PARENT, ACTIONS, OUTCOME, PREFECTURES
from . import VERSION

ENVIRONMENTS = {'urban':'都市部（市町村人口密度4,000人/km²以上）',
                'suburban':'郊外・地方都市（300〜4,000人/km²未満）',
                'rural':'低密度地域（300人/km²未満）'}
CONDITIONS = {'mother_age','father_age','mother_employed','father_employed','mother_education',
              'father_education','mother_occupation','father_occupation','mother_income_yen',
              'father_income_yen','household_income_yen','partner_present','legal_status','birth_rank','tenure','municipality_code'}

def density_class(region):
    value = next((x['value'] for x in region.get('authority_metrics',[]) if x['variable_id']=='X_DENSITY_CENSUS' and x['value'] is not None), None)
    return (None if value is None else 'urban' if value>=4000 else 'suburban' if value>=300 else 'rural'), value

def option(key,label,description,kind=None,person=None,value=None):
    return dict(id=key,label=label,description=description,kind=kind,person=person,value=value)

def money(n): return f'{int(n):,}円'

def cash_label(t):
    kind=t['kind'];joined=' '.join(t['deltas'])
    if kind=='payroll_net_receipt':return '給与の振込（'+PARENT.get(t.get('metadata',{}).get('person'),'親')+'）'
    if kind=='asset_transfer':return '資産から現金への振替'
    if kind=='authorized_borrow':return '借入による入金'
    labels=[('child_allowance','児童手当'),('parental','育児休業給付'),('maternity','出産手当金'),
            ('support','給付金'),('consumption','生活費'),('birth_invoice','出産費用'),('rent','家賃'),
            ('resident_tax','住民税'),('withheld','源泉所得税'),('social','社会保険料'),
            ('pension','年金保険料'),('commute','通勤費'),('care_fee','保育料'),('nursery','保育料'),
            ('interest','借入の利息'),('mortgage','住宅ローン元本'),('other_debt','借入金元本'),('tax_refund','税精算の還付')]
    for token,label in labels:
        if token in joined:return label
    return 'その他の入金' if t['deltas'].get('cash',0)>0 else 'その他の支払い'

class Experience:
    @classmethod
    def start(cls, engine, **settings):
        allowed={'prefecture_code','seed','birth_date','conditions','child_name','environment','initial_cash_yen'}
        if set(settings)-allowed: raise ValueError('対応していない開始条件です。')
        pref=settings.get('prefecture_code','13')
        if pref not in [f'{i:02d}' for i in range(1,48)]:raise ValueError('都道府県を選んでください。')
        conditions=settings.get('conditions') or {}
        if not isinstance(conditions,dict) or set(conditions)-CONDITIONS: raise ValueError('対応していない家庭条件です。')
        seed=settings.get('seed')
        if type(seed) not in [str,int] or len(str(seed))>80:raise ValueError('記録コードは80文字以内です。')
        environment=settings.get('environment','any')
        if environment not in {'any',*ENVIRONMENTS}:raise ValueError('居住環境を選んでください。')
        birth=settings.get('birth_date','2026-10-01')
        if not isinstance(birth,str) or not dt.date(2026,8,1)<=dt.date.fromisoformat(birth)<=dt.date(2026,11,30):raise ValueError('現行の家庭モデルで開始できる出生日は2026年8月1日〜11月30日です。')
        cash=settings.get('initial_cash_yen')
        if cash is not None and (type(cash) is not int or not 0<=cash<=1_000_000_000):raise ValueError('開始時現金は0〜10億円です。')
        scenario={} if cash is None else {'initial_cash_override':cash}
        game=None
        # Native, complete conditional families are accepted/rejected, never edited
        # to simulate a different residential context. No B internal traits filter.
        for attempt in range(48 if environment!='any' else 1):
            candidate_seed=seed if attempt==0 else f'{seed}/residential/{attempt}'
            try:
                candidate=Game.start(engine,prefecture_code=pref,seed=candidate_seed,birth_date=birth,
                                     conditions=conditions,child_name=settings.get('child_name','はる'),research_scenario=scenario)
            except ValueError as e:
                if type(e).__name__ in ['ConditionSupportError','InitialConditionError']:
                    raise ValueError('指定条件の組合せを現在の統計モデルでは生成できませんでした。条件を減らすか「おまかせ」を増やしてください。この家庭が現実に存在しないという意味ではありません。') from e
                raise
            category,_=density_class(candidate.core.a.get('region_context') or {})
            if environment=='any' or category==environment:
                game=candidate;break
        if game is None: raise ValueError('この地域・条件の組合せを48回の生成で確認できませんでした。居住環境を「おまかせ」にするか条件を減らしてください。存在しない家庭という意味ではありません。')
        obj=cls();obj.game=game;obj.settings=copy.deepcopy(settings);obj.accepted_attempt=attempt
        obj.revision=0;obj.logs=[];obj.history=[];obj.choices=[];obj.snoozed={};obj.resolved={}
        obj.playback={'running':True,'speed':1,'remaining_ms':10000};obj.acknowledgements=[]
        obj.names={'mother':['みさき','あかり','さき','まどか'][int(digest([seed,'mother'])[:6],16)%4],
                   'father':['そうた','ゆうた','なおき','けんた'][int(digest([seed,'father'])[:6],16)%4]}
        obj.initial_cash=game.core.a['accounts'].get('cash',0)
        obj.add_log(birth,'はじまり',f'{PREFECTURES[int(pref)-1]}{game.view()["household"]["municipality"]}で、{game.config["child_name"]}との暮らしが始まった。日々の生活は自動で進み、相談が必要になると時間が止まる。',
                    ['A.completed.household','B.child_identity'], 'simulated_state',[])
        obj.history.append(obj.metrics());return obj

    @property
    def month(self):return len(self.game.turns)

    def add_log(self,date,category,text,refs,evidence,staging):
        self.logs.append({'id':f'life-{len(self.logs):04d}','date':date,'month':self.month,'category':category,
                          'text':text,'source_refs':refs,'evidence':evidence,'fictional_staging':staging})

    def metrics(self):
        a=self.game.core.a;row=a.get('last_month');tx=[]
        completed=len(self.game.core.a_periods)
        if getattr(self,'history',[]) and completed==self.history[-1].get('completed_periods',0):row=None
        if row and self.game.core.a_periods:tx=self.game.core.a_periods[-1]['A_transactions']
        # Gross receipts and payments are actual cash movements, excluding asset
        # transfers and borrowing, which remain separately identified.
        incoming=sum(max(0,t['deltas'].get('cash',0)) for t in tx if t['kind'] not in ['asset_transfer','authorized_borrow'])
        outgoing=-sum(min(0,t['deltas'].get('cash',0)) for t in tx if t['kind']!='asset_transfer')
        transfers=sum(t['deltas'].get('cash',0) for t in tx if t['kind']=='asset_transfer')
        cash=a['accounts'].get('cash',0)
        old=self.history[-1]['cash_yen'] if getattr(self,'history',[]) else cash
        return {'date':self.game.core.child._state['as_of_date'],'month':self.month,'completed_periods':completed,'cash_yen':cash,
                'cash_delta_yen':cash-old,'cash_in_yen':incoming if row else None,'cash_out_yen':outgoing if row else None,
                'asset_transfer_yen':transfers,'borrowing_yen':sum(max(0,t['deltas'].get('cash',0)) for t in tx if t['kind']=='authorized_borrow'),'recognized_income_yen':row['ledger']['recognized_income'] if row else None,
                'recognized_expense_yen':row['ledger']['recognized_expense'] if row else None,
                'term_yen':a['accounts'].get('term',0),'securities_yen':a['accounts'].get('securities',0),
                'unpaid_yen':(row['ledger']['unpaid_due']+row['ledger']['unpaid_principal_due']) if row else 0,
                'consumption_yen':row['consumption'] if row else None,'rent_yen':row['rent'] if row else None,
                'spending_factor':a['spending_factor'],
                'cash_trace':[{'id':t['event_id'],'kind':t['kind'],'label':cash_label(t),'delta_yen':t['deltas'].get('cash',0),'accounts':list(t['deltas'])} for t in tx if t['deltas'].get('cash')],
                'source_ref':'A.completed.A_transactions + accounts; asset transfers distinguished'}

    def event(self):
        if self.game.finished:return None
        a=self.game.core.a;n=a['elapsed_months'];v=self.game.view();parents=a['parents']
        candidates=[]
        def event(key,title,text,options,refs):
            candidates.append(dict(id=key,title=title,text=text,options=options,source_refs=refs,
                                   evidence='native_household_scenario',resolves_at='次の暦月決算。申請や採用にはさらに時間がかかる場合があります。'))
        for who,p in parents.items():
            if p.get('job_offer'):
                o=p['job_offer'];event('offer/'+o['id'],'仕事の提案が届いた',f'{self.names[who]}に年収目安{money(o["normal_annual"])}・週{o["normal_weekly_hours"]:g}時間の提案。受諾するか、見送るかを決めたい。',[
                    option('accept','この提案を受ける','勤務条件と以後の収入の計算へ反映。保育との両立は別途確認。','accept_job_offer',who,o['id']),
                    option('reject','今回は見送る','今ある仕事の提案を辞退する。','reject_job_offer',who,o['id'])],['A.parents.'+who+'.job_offer'])
        for flag in a.get('pending_decisions',[]):
            kind=flag['type'];key='native/'+kind
            if kind=='cash_shortage':
                # Escalations reopen even if the previous shortage was deferred.
                band=int(flag.get('amount',0)//500000);key+=f'/{band}'
                opts=[option('trim','調整できる生活費を抑える','調整できる生活費の予算を基準から20%抑える。家賃や返済はそのまま。','set_spending',value=.8)]
                if a['accounts'].get('term',0)>0:opts.append(option('term','定期性預金も支払いに使う','不足時に定期性預金から現金へ移す。収入ではない。','set_liquidity_policy',value='use_term'))
                if a['accounts'].get('securities',0)>0:opts.append(option('assets','有価証券も支払いに使う','不足時の資産振替。運用益や将来の値上がりは計算しない。','set_liquidity_policy',value='use_securities'))
                event(key,'今月の支払いが足りない',f'期限が来た支払いのうち{money(flag.get("amount",0))}が未払い。生活費を見直すか、支払いに使う資産を相談したい。',opts,['A.pending_decisions','A.accounts'])
            elif kind in ['care_work_conflict','care_eligibility_review']:
                opts=self.care_options(a)
                event(key,'仕事の時間をどうつなぐ？','働く時間に対して、利用できる保育枠や利用条件がそろっていない。希望するだけでは復職・入園は確定しない。',opts,['A.pending_decisions','A.care'])
            elif kind=='leave_plan_exceeds_evidenced_entitlement':
                opts=[option('support','身近な人へ支援を相談する','支援できる人がいるか、モデル内で返答を確認する。','request_relative_support')]
                opts+=self.return_options(a)
                event(key,'休業を続ける条件を確認したい','希望する休業期間の根拠が未確認。雇用先との関係が続いても、給与が出るとは限らない。',opts,['A.pending_decisions','A.parents'])
        if n>=1 and not any(c['kind']=='child_application' for c in a['claims']):
            event('allowance','児童手当の手続きをどうする？','出生後の手続きがまだ記録されていない。提出、承認、入金は別々に進む。実際の自治体での期限や資格を保証するものではない。',[
                option('apply','手続きを出す','申請を登録。承認を経て、支払月に入金する。','apply_child_allowance')],['A.claims'])
        if n>=3 and n%6==3 and a['care']['status']!='enrolled':
            event(f'care/{n}','これからの仕事と預け先',f'{self.game.config["child_name"]}との生活が続くなか、家族の時間をどう組み立てるか。今の保育は「{v["household"]["care"]["status"]}」。',self.care_options(a)+self.return_options(a),['A.parents','A.care'])
        if n>=6 and n%6==0:
            event(f'budget/{n}','家計を一度、見直そう',f'いまの現金残高は{money(a["accounts"].get("cash",0))}。食費・日用品など調整できる部分について、次の方針を決める。',[
                option('trim','少し抑えて暮らす','調整できる生活費の予算を基準から20%抑える。','set_spending',value=.8),
                option('normal','通常の予算にする','予算を基準に戻す。物価や家族の条件は別途反映。','set_spending',value=1.0),
                option('room','生活費に少し余裕を持たせる','調整できる生活費の予算を基準から15%増やす。能力や愛着への加点はない。','set_spending',value=1.15)],['A.spending_factor','A.accounts'])
        if n in [2,8,14,20]:
            cards=v['child']['cards'];sig=next((c for c in cards if c['signal']=='crying' and c['present']),None)
            if sig:
                event(f'child/{n}',f'{self.game.config["child_name"]}のそばで','泣いている様子が、今月の観察に残った。原因はこの記録だけではわからない。少し時間をとって関わってみる？',[
                    option('comfort','なだめながら、様子を見る','その場の反応を追加で観察する。長期の能力・愛着の効果は計算しない。','child:offer_comfort'),
                    option('watch','そばで見守って記録する','観察できた反応を記録する。','child:observe')],['B.player_view.observations'])
        for e in candidates:
            if self.resolved.get(e['id']) or self.snoozed.get(e['id'],-1)>n:continue
            e['options']=[o for o in e['options'] if not any(q['type']==o['kind'] and q.get('person')==o['person'] for q in self.game.queue)]
            if not e['options']:continue
            e['options'].append(option('later','いまは方針を変えず、続ける','判断を3か月保留する。未払い・保育不足などの条件は解消されない。'))
            return e
        return None

    def care_options(self,a):
        opts=[];care=a['care']
        if (care['application'] is None or care['status'] in ['rejected','not_admitted','needs_eligibility_review']) and any(p.get('contract_active') or p.get('job_search') for p in a['parents'].values()):
            opts.append(option('care','保育を申し込む','就業などの利用条件を確認して申請。入園の可否は別途判定。','apply_childcare'))
        if not care['relative_requested']:opts.append(option('support','身近な人へ支援を相談する','支援が可能か返答を受ける。希望通りとは限らない。','request_relative_support'))
        for who,p in a['parents'].items():
            if not p.get('contract_active') and not p.get('job_search'):
                opts.append(option('search-'+who,f'{PARENT[who]}が仕事を探す','求職を開始。提案が届くか、採用条件は未確定。','job_search',who))
        return opts

    def return_options(self,a):
        opts=[]
        for who,p in a['parents'].items():
            if p.get('contract_active'):
                opts.append(option('hours-'+who,f'{PARENT[who]}の時短勤務を相談','通常の75%の勤務時間を希望。雇用先の返答を経て反映。','request_hours',who,.75))
                if p.get('leave_requested') or p['state'] in ['maternity','parental_leave','job_attached_zero_work_unpaid']:
                    opts.append(option('return-'+who,f'{PARENT[who]}の復職を相談','次期からの復職を希望。保育や休業条件によって実働は別途決まる。','request_return',who,min(24,a['elapsed_months']+1)))
        return opts

    def choose(self,event_id,choice_id):
        e=self.event()
        if not e or event_id!=e['id']:raise ValueError('この相談は更新されています。最新の画面を確認してください。')
        o=next((o for o in e['options'] if o['id']==choice_id),None)
        if not o:raise ValueError('この場面では選べません。')
        before=digest(self.game.core.payload());native=None
        if o['kind'] and o['kind'].startswith('child:'):
            self.game.observe(o['kind'].split(':')[1]);self.resolved[e['id']]=True
            self.child_scene(interaction=True)
        elif o['kind']:
            self.game.request(o['kind'],person=o['person'],value=o['value']);native=copy.deepcopy(self.game.queue[-1]);self.resolved[e['id']]=True
        else:self.snoozed[e['id']]=self.game.core.a['elapsed_months']+3
        # Persistent native problems should recur, not permanently disappear.
        if e['id'].startswith('native/'):
            self.resolved.pop(e['id'],None);self.snoozed[e['id']]=self.game.core.a['elapsed_months']+3
        self.choices.append({'date':self.game.view()['date'],'event_id':e['id'],'choice_id':o['id'],'label':o['label'],
                             'description':o['description'],'native_request':native,'before_sha256':before,
                             'after_sha256':digest(self.game.core.payload()),'evidence':e['evidence']})
        self.playback['remaining_ms']=10000
        self.playback['running']=False
        self.revision+=1

    def child_scene(self,interaction=False):
        v=self.game.view();reports=v['child']['observations'];name=v['child_name'];month=self.month
        positives=[(i,r,k) for i,r in enumerate(reports) for k,value in r['behaviors'].items() if value]
        first_walk=any('足を運ぶ' in n for n in v['child']['notices']);first_word=any('ことば' in n for n in v['child']['notices'])
        if first_walk:positives=[x for x in positives if x[2]=='takes_independent_steps'] or positives
        elif first_word:positives=[x for x in positives if x[2]=='uses_contextual_word'] or positives
        if positives:
            pick=positives[int(digest([self.game.config['seed'],month,'interaction' if interaction else 'scene'])[:8],16)%len(positives)]
            i,r,k=pick;parent=self.names['mother']
            templates={
                'crying':f'昼下がりの居間。{name}の泣き声が聞こえ、{parent}がそばで様子を見た。何を伝えたいのか、この場面だけではまだわからない。',
                'settles_after_comfort':f'居間で{name}をなだめていた{parent}。しばらくすると、落ち着く様子が見られた。いつも同じようになるかは、また別の日に。',
                'orients_to_unfamiliar_object':f'午前中、居間に赤い布を置くと、{name}がそちらへ注意を向けた。{parent}は少し離れて、その様子を見ていた。',
                'looks_toward_voice':f'夕方、居間で{parent}が声をかけた。{name}の視線が、声のした方へ向いた。',
                'difficulty_settling':f'夜、部屋を静かにして過ごす。{name}には落ち着きにくい様子があり、{parent}はそばで見守った。今夜も、そばでゆっくり過ごす。',
                'takes_independent_steps':f'居間で{name}がひとりで足を運ぶ姿を、{parent}が見つけた。そばから見ていたこの場面が、家の記録に残った。',
                'uses_contextual_word':f'午後、{name}と居間で過ごしていた{parent}。その場に合うことばが聞かれ、今日の記録に書き留めた。',
                'sustains_object_attention':f'窓辺の光が揺れる居間。{name}は目の前の物へ、しばらく注意を向け続けていた。{parent}もそばで、その間を過ごした。',
                'withdraws_from_intense_stimulus':f'居間で強い刺激に触れたとき、{name}が身を引く様子を見せた。{parent}は反応を書き留めた。何が嫌だったのかは、決めつけずにおく。',
                'explores_available_space':f'午前中の居間で、{name}が周りの空間を探索する様子を見せた。{parent}は動きや視線を追っていた。'}
            text=templates.get(k,f'{name}と過ごした場面が、今月の記録に残った。')
            self.add_log(r['date'],'ふたりの時間' if interaction else '子ども',text,
                [{'path':'B.player_view.observations','report_sha256':digest(r),'signal':k,'observed_value':True}],
                'uncalibrated_observed_behavior_with_fictional_staging',['親の呼び名','時刻・居間・小物・周囲の描写。発達・因果効果の追加なし'])
        else:
            self.add_log(v['date'],'子ども',f'{name}と過ごす日々。今月は、具体的な反応を書き留められた場面がなかった。見えていない時間のことまでは、決めつけずにおく。',['B.player_view.observations'],'missing_observation',[])

    def advance(self):
        if self.event():raise ValueError('相談の選択肢を選んでから、再開してください。')
        obj=copy.copy(self);obj.game=self.game.clone()
        for key in ['logs','history','choices','snoozed','resolved','playback','acknowledgements']:setattr(obj,key,copy.deepcopy(getattr(self,key)))
        pending=copy.deepcopy(obj.game.core.a.get('pending_decisions',[]))
        if pending:obj.acknowledgements.append({'date':obj.game.view()['date'],'flags':pending,'policy':'explicit_contextual_choice_or_3_month_deferral'})
        obj.game.advance(reviewed=bool(pending));obj.child_scene()
        m=obj.metrics();obj.history.append(m)
        v=obj.game.view();a=obj.game.core.a;row=a.get('last_month') if m['cash_in_yen'] is not None else None
        if row:
            text=f'月末、{obj.names["mother"]}が家計の記録を開く。入金は{money(m["cash_in_yen"]) }、支払いは{money(m["cash_out_yen"])}。現金残高は前期より{money(abs(m["cash_delta_yen"]))}{"増えた" if m["cash_delta_yen"]>=0 else "減った"}。'
            if m['asset_transfer_yen']:text+=f'資産から現金への振替は{money(m["asset_transfer_yen"])}。'
            if m['unpaid_yen']:text+=f'期限の来た未払いが{money(m["unpaid_yen"])}残っている。'
            obj.add_log((dt.date.fromisoformat(a['month'])-dt.timedelta(days=1)).isoformat(),'暮らしとお金',text,['A.completed.A_transactions','A.completed.accounts'],'unvalidated_household_cashflow',['月末に家計を開く場面・親の呼び名'])
        decisions=v['decisions']
        if decisions:
            text=' / '.join(d['text'] for d in decisions)
            obj.add_log(v['date'],'選んだことの返答',text,[d['source_ref'] for d in decisions],'native_action_feasibility_scenario',[])
        elif obj.game.core.a_periods and row:
            prev_care=self.game.core.a['care']['status']
            changes=[]
            if a['care']['status']!=prev_care:changes.append('保育の状況が「'+v['household']['care']['status']+'」に変わった。')
            for who,p in a['parents'].items():
                old=self.game.core.a['parents'].get(who,{})
                if p['state']!=old.get('state'):changes.append(f'{obj.names[who]}の仕事は「'+next(x['status'] for x in v['household']['parents'] if x['id']==who)+'」になった。')
            if changes:obj.add_log(v['date'],'生活の変化',' '.join(changes),['A.completed.parents','A.completed.care'],'unverified_employment_and_care_scenario',[])
        obj.playback['remaining_ms']=10000
        if obj.event() or obj.game.finished:obj.playback['running']=False
        obj.revision+=1;self.__dict__.update(obj.__dict__)

    def view(self):
        v=self.game.view();a=self.game.core.a
        parents=[]
        for p in v['household']['parents']:
            native=next(x for x in a['persons'] if x['person_id']==p['id']);attr=native.get('attributes') or {}
            parents.append({**p,'given_name':self.names[p['id']],'age_years':native.get('age_years'),
                'education':attr.get('education'),'education_coarse':attr.get('education_coarse'),
                'occupation':attr.get('occupation'),'occupation_code':attr.get('occupation_code'),
                'employment_type':a['parents'][p['id']].get('employment_type')})
        env,density=density_class(a.get('region_context') or {})
        return {'version':VERSION,'revision':self.revision,'date':v['date'],'birth_date':v['birth_date'],
                'age_months':v['age_months'],'age_days':v['age_days'],'finished':v['finished'],
                'child_name':v['child_name'],'parents':parents,
                'household':v['household'],'environment':{'class':env,'label':ENVIRONMENTS.get(env,'分類不明'),'density':density},
                'logs':copy.deepcopy(self.logs),'metrics':copy.deepcopy(self.history[-1]),'history':copy.deepcopy(self.history),
                'event':self.event(),'choices':copy.deepcopy(self.choices),'queue':v['queued_requests'],
                'child':{'notices':v['child']['notices'],'measurements':v['child']['measurements'],
                         'observed_growth':[{'date':r['end'],'notices':r['child']['notices']} for r in v['album'] if r['child']['notices']]},
                'playback':copy.deepcopy(self.playback),'limits':v['limits'],'observe_used':'mother/observe' in self.game.child_actions_this_turn,
                'setup':{'conditions':copy.deepcopy(self.settings.get('conditions',{})),'accepted_attempt':self.accepted_attempt,
                         'initial_cash_user_override':self.settings.get('initial_cash_yen')}}

    def set_playback(self,running,speed,remaining_ms):
        if type(running) is not bool or speed not in [.5,1,2,4] or type(remaining_ms) not in [int,float] or not 0<=remaining_ms<=10000:raise ValueError('進行設定が正しくありません。')
        if running and (self.event() or self.game.finished):raise ValueError('相談を選んでから再開してください。')
        self.playback={'running':running,'speed':speed,'remaining_ms':remaining_ms};self.revision+=1

    def save(self,path):
        body={key:copy.deepcopy(value) for key,value in self.__dict__.items() if key!='game'}
        body.update(version=VERSION,game=self.game.snapshot());env={'payload':body,'sha256':digest(body)}
        p=Path(path);tmp=p.with_suffix('.tmp');p.parent.mkdir(parents=True,exist_ok=True)
        with gzip.open(tmp,'wt',encoding='utf-8') as f:json.dump(env,f,ensure_ascii=False,sort_keys=True,allow_nan=False)
        os.chmod(tmp,0o600);tmp.replace(p);return env['sha256']

    @classmethod
    def load(cls,path,engine):
        with gzip.open(path,'rt',encoding='utf-8') as f:env=json.load(f)
        b=env['payload']
        if b.get('version')!=VERSION or digest(b)!=env['sha256']:raise ValueError('記録の版・ハッシュが一致しません。旧C-0の保存記録は旧版で開いてください。')
        old=b.pop('game');b.pop('version')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'game.gz'
            with gzip.open(p,'wt',encoding='utf-8') as f:json.dump({'payload':old,'sha256':digest(old)},f,ensure_ascii=False)
            game=Game.load(p,engine)
        obj=cls();obj.__dict__.update(b);obj.game=game;return obj
