"""Four authored decision structures. Recipes are stateful operations, not prose.
No universal virtue ranking; costs/time and deferred commitments make each distinct.
"""
EDUCATION={'1':'小学・中学','2':'高校・旧制中学','3':'専門学校・短大・高専','4':'大学・大学院'}
MAIN_AGES={'B':4,'A':8,'C':12,'D':16}
LABELS={'A':'初めての遠出','B':'手が伸びた、その先','C':'来月の勤務と、家で過ごす時間','D':'家族の一枚を、外へ出す？'}

def activity(kind,when=0):return {'op':'activity','kind':kind,'when':when}
def request(kind,value=None,when=0):return {'op':'request','kind':kind,'value':value,'when':when}
def choice(id,title,value,gain,forgo,ops):return dict(id=id,title=title,value_axis=value,gain=gain,forgo=forgo,ops=ops)

def main_choices(x,code):
 age=x.game.core.elapsed_months;p=x.game.core.a['parents'][x.actor];cash=x.game.core.a['accounts']['cash'];owned=x.inventory
 if code=='A':
  # The scale changes with actual means, preserving a real novel/familiar contrast.
  far=next((k for k in ['trip','aquarium','zoo','center'] if x.available(k)), 'park')
  once=[activity(far,1)]
  if far=='trip' and x.partner and x.npc_wish=='quiet' and not any(e['kind']=='handover' for e in x.experiences):once.insert(0,activity('handover'))
  saving=min(28000,max(0,cash//8))
  stable=[{'op':'saving','yen':saving,'purpose':'次の遠出','when':0},activity('photo',1)] if saving else [request('set_spending',.9),activity('photo',1)]
  family=[activity('handover'),activity('book' if 'book'in owned else 'voice',1)] if x.partner else [request('request_relative_support'),activity('photo',1)]
  return [choice('once','今の家族で、少し遠くへ行く','今しかない一回','一度の遠出を予定にし、当日の姿を残す'+('。出発前に交代して休む日も取る' if len(once)>1 else ''),'移動と費用を使う。疲れて早く帰る日もある',once),
   choice('near','近所に、何度も通う時間をつくる','日々の積み重ね','近い場所へ今月と来月、短く2回ずつ出かける','親の時間を複数回使う。遠出は見送る',[activity('park',0),activity('park',0),activity('park',1),activity('park',1)]),
   choice('reserve','遠出は急がず、次に使うお金を残す','将来の余裕','旅費用の預金メモと家での写真を残す','今の月齢での遠出の機会は見送る',stable),
   choice('rest','まず、家族が休める休日にする','支え合って続ける','自分が引き受ける時間をつくる' if x.partner else '外の支援へ相談し、家でも記録を残す','自分の自由時間を使う。遠出は今回しない',family)]
 if code=='B':
  last=x.scenes[-1] if x.scenes else None
  focus=(last['kind'] if last and last['kind'] in ['music','toy','book','cloth','floor','mirror'] else next((k for k in ['book','toy','music'] if k in ['book' if 'book'in owned else None,'toy' if 'toy'in owned else None,'music' if 'bell'in owned else None]),'cloth'))
  alternatives=[k for k in ['blocks' if age>=9 else 'music','book','toy','mirror'] if k!=focus and x.game.core.elapsed_months>=x.quote_activity(k)['min_age']]
  contrast=next((k for k in alternatives if x.quote_activity(k)['cost']>0),alternatives[0])
  return [choice('deepen','あの遊びを、もう少し続けてみる','一つを深める','同じ物と遊びを、今月と来月に2回ずつ','別の遊びの時間は少なくなる。気に入る保証はない',[activity(focus),activity(focus),activity(focus,1),activity(focus,1)]),
   choice('broaden','違うものも、一つ見せてみる','関心の幅を広げる','別の道具・刺激を用意し、来月も使う','新しい買い物と時間を使う。見向きもしないかもしれない',[activity(contrast),activity(contrast,1)]),
   choice('agency','今日は、こちらで決めすぎない','子どもの選び方を見る','手元にある二つから向かった方と、そこでの反応を残す','親の予定どおりには進めず、待つ時間を使う',[{'op':'agency','when':0},{'op':'agency','when':1}]),
   choice('together','道具を増やさず、やりとりに付き合う','一緒に過ごすこと','顔を見て話す・布で遊ぶ時間を別の日にも取る','購入の新しさはない。自分が繰り返し付き合う',[activity('voice'),activity('cloth'),activity('voice',1),activity('cloth',1)])]
 if code=='C':
  employed=p.get('employee_contract');leave=p['state'] in ['leave','maternity'];search=not employed;offer=p.get('job_offer')
  work=request('accept_job_offer',offer['id']) if offer else request('job_search') if search else request('request_return') if leave else request('request_hours',1.)
  timeops=[activity('floor' if age>=3 else 'voice'),activity('photo',1)]
  if employed:timeops.insert(0,request('request_hours',.8))
  else:timeops.append(activity('floor',1))
  if offer:timeops.insert(0,request('reject_job_offer',offer['id']))
  support=request('apply_childcare') if not x.game.core.a['care'].get('application') else request('request_relative_support')
  return [choice('work','届いた仕事の提案を、受けると返事する' if offer else '通常勤務に向けて相談し、準備に時間を取る' if employed else '仕事を探す時間を、予定に入れる','仕事を手放さない','届いた提案に返事をし、仕事の準備に時間を取る' if offer else '本人の勤務・復職・仕事探しの希望を出し、準備の時間を取る','家のために使えた時間を月4時間、2か月使う。収入増は保証されない',[work,{'op':'work_time','hours':4,'when':0},{'op':'work_time','hours':4,'when':1}]),
   choice('time','家で過ごす時間を、先に確保する','今の子どもとの時間','勤務を8割で相談し、家で過ごす枠を実行する' if employed else '仕事探しを急がず、家で過ごす枠を実行する','減収・機会を見送る可能性がある。勤務変更には結果待ちがある',timeops),
   choice('budget','働き方は保ち、支出の方を見直す','生活の安定','通常消費を1割抑える希望を出し、家での活動を残す','使える物やサービスを減らす選択。収入を増やす計算ではない',([request('reject_job_offer',offer['id'])] if offer else [])+[request('set_spending',.9),activity('voice',1)]),
   choice('support','一人で抱えず、支援を整える方へ動く','続けられる分担','保育や親族支援へ相談し、手続きと家の予定を進める','利用できるか・費用はいくらかはまだ確定しない'+('。仕事の返事を待つ間に提案の期限を過ぎる可能性がある' if offer else ''),[support,activity('handover' if x.partner else 'photo',1)])]
 if code=='D':
  return [choice('public','公開することも含めて、応募を相談する','外へ出す挑戦','家族の一枚で架空の展示企画に応募する','家族の合意が必要。落選や見送りもある',[activity('photo'),{'op':'entry','format':'named_portrait','hours':1,'when':0}]),
   choice('private','この一枚は、家族だけのものにする','家族内の記憶','写真を外へ出さず、家族内で見返す予定を残す','外の企画への参加は見送る',[activity('photo'),{'op':'private_album','hours':1,'when':1}]),
   choice('anonymous','顔や名前を出さない作品で参加する','匿名性を守る工夫','親が手元の物を題材に、匿名の作品を作って応募する','制作に長く時間を使う。家族名や顔は紹介されない',[activity('photo'),{'op':'entry','format':'anonymous_object','hours':2.5,'when':0}]),
   choice('visit','応募せず、親子で会場へ行ってみる','結果より、その場の経験','架空の親子室へ出かけ、展示のある場所で過ごす','移動と費用を使う。自分たちの作品は展示しない',[activity('center',1)])]
 raise ValueError(code)

def followup_choices(x,case):
 code=case['domain'];experiences=[e for e in x.experiences if e['id'] in x.case_effects(case)['experience_ids']]
 last=experiences[-1] if experiences else None
 if code=='A':
  repeat=last['kind'] if last else 'park'
  if case['choice_id']=='once':repeat=next((r['operation']['kind'] for r in x.commitments if r['case_id']==case['id'] and r['operation']['op']=='activity' and r['operation']['kind']!='handover'),repeat)
  fund=next((f for f in x.purpose_funds if f['case_id']==case['id'] and f['remaining_yen']>0),None)
  option1=[{'op':'spend_fund','fund_id':fund['id'],'when':0},activity('aquarium' if fund['remaining_yen']>=x.quote_activity('aquarium')['cost'] else 'park',1)] if fund else [activity(repeat,1)]
  return [choice('return','残した経験や旅費を、次の一回につなぐ','続けてみる','前に選んだ行き先・旅費を使う予定にする','もう一度、時間や費用を使う',option1),choice('home','あの日を、家で見返す','思い出を味わう','家に残った記録を見返す時間を取る','新しい外出は足さない',[{'op':'private_album','hours':1,'when':0}]),choice('later','次は急がず、家計を優先する','余裕を守る','今月も通常消費を見直す希望を出す','新しい遠出は見送る',[request('set_spending',.9)]),choice('family','今度は、家族の休める時間をつくる','交代して続ける','前回とは別に分担や支援の相談を実行する','自分の自由時間や手続きの時間を使う',[activity('handover')] if x.partner else [request('request_relative_support')])]
 if code=='B':
  opts=main_choices(x,'B');opts[0]['title']='前に過ごした遊びを、もう一度' 
  # Persist the actual earlier choice of object, not the unrelated most recent policy scene.
  if last:opts[0]['ops']=[activity(last['kind']),activity(last['kind'],1)]
  return opts
 if code=='C':return main_choices(x,'C')
 if code=='D':
  return [choice('see','企画のその後を、親子で見に行く','会場の経験','実際の応募結果を踏まえて親子室を訪ねる','時間と移動費を使う',[activity('center',1)]),choice('keep','残った一枚を、家族の中で見返す','今ある記憶','新たに公開せず、残った記録を見る時間を取る','新しい応募はしない',[{'op':'private_album','hours':1,'when':0}]),choice('new','今度は、別の日の一枚を残す','今の姿を記録する','新しい日の写真を撮る','前の写真を撮り直すわけではない',[activity('photo')]),choice('ordinary','企画を離れて、いつもの遊びへ戻る','日常を大切にする','家にある物で親子の時間を取る','応募や展示との接点はここで区切る',[activity('cloth'),activity('voice',1)])]
