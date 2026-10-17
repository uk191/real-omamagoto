"""Canonical game-world scene -> Japanese presentation. No hidden-state narration.
Sampling has its own keyed stream and never consumes A/B random streams.
The scene is saved before prose. Verbs, incidental facts and dialogue are stored,
not invented on render. Coefficients are game assumptions, not measured effects.
"""
import math
from .catalogue import ACTS

def build_scene(x,task,prior,item):
 from c1.experience import u
 q=task['quote'];item=item or {'name':'手元の遊び道具','id':None};kind=task['kind'];s=x.game.core.child._state;t=s['latent_state'];age=s['age_days']/30.4375
 seed=s['random_streams']['seed'];draw=lambda tag:u(seed,'C3_scene',x.date,task['id'],tag)
 familiar=min(1,len(prior)/5);fat=s['emotion_regulation']['fatigue'];stim=q['stim'];old=prior[-1] if prior else None
 # Latent scores influence the odds, never determine a reaction or diagnose a child.
 weights={'watch':math.exp(.25*t['attention_persistence']+.2*t['attention_orientation']),
 'reach':math.exp(.3*t['exploration']+.2*t['activity']+min(age,18)/25) if age>=6 else 0,
 'people':math.exp(.3*t['social_orientation']+.15*t['approach']),
 'withdraw':math.exp(-.7+.3*t['reactivity']+.35*t['sensory_sensitivity']+stim-.4*familiar),
 'sleepy':math.exp(-1.2+1.2*fat),
 'unexpected':math.exp(-.2+.2*t['exploration'])}
 z=draw('reaction')*sum(weights.values());reaction='watch'
 for k,w in weights.items():
  z-=w
  if z<=0:reaction=k;break
 # New attention targets are canonical state, not synonymous sentences.
 targets={'aquarium':['銀色の魚の群れ','青く揺れる水槽の明かり','行き交う人の足元'],
 'zoo':['木の上の小さな動物','足元の砂利','動物の囲いの影'],
 'park':['風で動く枝','ベンチの影','通り過ぎるベビーカー'],
 'leaves':['並木の葉','道に落ちた葉の影','風に揺れる枝'],
 'train':['通り過ぎる電車','踏切の明かり','見送る人の手'],
 'center':['転がる大きなボール','入口に並んだ靴','部屋の大人たち'],
 'trip':['宿の窓から見える水面','見慣れないカーテン','部屋の照明']}
 targetlist=targets.get(kind,[item['name'] if item else '目の前の大人の顔'])
 target=targetlist[int(draw('target')*len(targetlist))%len(targetlist)]
 actor=x.names[x.actor];child=x.game.config['child_name'];other=x.names.get(x.partner)
 participants=[x.game.core.identity['person_links'][x.actor],x.game.core.identity['index_global_person_id']]
 names=[actor,child]
 if kind in ['trip','birthday','birthday_free','handover'] and other:
  participants.append(x.game.core.identity['person_links'][x.partner]);names.append(other)
 scene={'id':f'scene-{len(x.scenes):05d}','date':x.date,'period':x.month,'task_id':task['id'],'experience_id':None,'kind':kind,'genre':q['genre'],'place':q['place'],'participant_ids':participants,'participant_names':names,'age_days':s['age_days'],'stage':0 if age<3 else 1 if age<6 else 2 if age<12 else 3 if age<18 else 4,'item_id':item['id'] if item else None,'target':target,'reaction_code':reaction,'prior_scene_id':old.get('scene_id') if old else None,'beats':[],'paid_yen':q['cost'],'actual_hours':q['hours'],'status':'completed','research_status':'C3_uncalibrated_game_world_scenario','long_term_effect':False,'transport_scenario':q.get('transport_scenario'),'season_month':int(x.date[5:7]),'source_refs':['C3.tasks/'+task['id'],'B.age_days','B.latent_state (trusted reaction calculation only)','B.emotion_regulation (trusted reaction calculation only)']}
 def beat(code,text):scene['beats'].append({'code':code,'text':text})
 # Every sentence below becomes a canonical, saved world fact before rendering.
 if kind in targets:
  beat('arrival',f'{actor}は{child}と、{q["place"]}へ出かけた。')
  if reaction=='withdraw':
   beat('overwhelmed',f'{child}は周りを見回したあと、{actor}の服をぎゅっと握って泣き出した。予定していた場所を全部は回らず、人の少ない所で休んでから帰ることにした。' if age>=6 else f'{child}が泣き始めたので、{actor}は人の少ない所へ移った。今日は短い外出で切り上げた。');scene['status']='early_return';scene['actual_hours']=min(q['hours'],max(1,q['hours']*.6))
  elif reaction=='sleepy':beat('nap',f'着いたころ、{child}のまぶたが重くなった。{actor}は立ち止まって休むことにした。楽しみにしていた景色は、今日は大人の方が長く眺めていた。');scene['status']='rested'
  elif reaction=='people':beat('social_focus',f'{child}が顔を向けていたのは、{target}より、そばにいた人の方だった。{actor}が景色を見せようと向きを変えると、また人のいる方へ顔を戻した。')
  elif reaction=='reach':beat('reach_target',f'{child}は{target}を見つけて手を伸ばした。{actor}はその方向で足を止めた。次の場所へ進もうとすると、もう一度そちらへ手が伸びた。')
  elif reaction=='unexpected':
   alternative=targetlist[-1];scene['target']=alternative
   beat('unexpected_target',f'{actor}が見せたかったものの横で、{child}は{alternative}をじっと見ていた。予定とは少し違う所で、いちばん長い寄り道になった。')
  else:beat('watch_target',f'{child}は{target}の方へ顔を向け、しばらくそのまま眺めていた。{actor}も急がず、隣で同じものを見て過ごした。')
 elif kind=='book':
  beat('open_book',f'{actor}は{q["place"]}で、{item["name"]}を膝の上に開いた。')
  if reaction=='reach':beat('page',f'{child}の手が次のページにかかった。{actor}が続きを読もうとすると、開いたばかりのページがまた閉じた。今日は同じページを何度も開くことになった。')
  elif reaction=='unexpected':beat('back_cover',f'{child}が長く見ていたのは、お話の続きより裏表紙だった。{actor}は本を裏返して、その絵を一緒に眺めた。')
  else:beat('book_response',{'watch':f'{child}は丸い絵へ顔を向けた。{actor}はそこで読むのを止め、同じ絵をもう少し見せていた。','people':f'{child}は本より、読んでいる{actor}の口元を見ていた。声を止めると、顔を見たまま待っていた。','withdraw':f'{child}が泣き始めたので、{actor}は読みかけに指を挟んで本を閉じた。続きは、また別の日にすることにした。','sleepy':f'{child}の目が閉じかけた。{actor}は本を閉じ、声を落とした。最後まで読まない日もある。'}[reaction])
 elif kind in ['toy','blocks','music','cloth','mirror','floor','voice']:
  setup={'toy':f'{actor}は{item["name"]}を、敷物の上でゆっくり転がした。','blocks':f'{actor}が{item["name"]}を三つ重ねた。','music':f'{actor}は{item["name"]}を一度だけ、そっと鳴らした。','cloth':f'{actor}が手持ちの布で顔を隠し、少し待ってから顔を出した。','mirror':f'{actor}は{child}を抱き、鏡の前で横に並んだ。','floor':f'{actor}は床の小物を片づけ、{child}のそばに腰を下ろした。','voice':f'{actor}は窓辺で{child}を抱き、顔を見ながらゆっくり話しかけた。'}
  beat('invitation',setup[kind])
  specifics={('blocks','reach'):f'{child}の手が積み木に触れ、三つともころんと倒れた。{actor}が積み直すと、また手が伸びる。作る係と崩す係が、いつの間にか決まっていた。',('toy','reach'):f'{child}がボールへ手を伸ばすと、指先が当たって向こうへ転がった。{actor}が取りに行き、戻すと、もう一度。遊んでいるうちに、大人の往復が増えていった。',('music','unexpected'):f'音が止まったあと、{child}は鈴より{actor}の手元を見ていた。もう一度鳴らす前から、同じ場所へ顔を向けて待った。',('mirror','unexpected'):f'{actor}が横に動くと、鏡の中でも二人が動いた。{child}は鏡の方を見たあと、抱いている腕の方へ顔を戻した。'}
  generic={'watch':f'{child}は目の前の動きをしばらく見つめた。{actor}も同じ速さで、もう一度だけ繰り返した。','reach':f'{child}の手が目の前へ伸びた。{actor}は届く場所へ手を寄せ、つかもうとする様子を待っていた。','people':f'{child}は道具より{actor}の顔を見ていた。{actor}が顔を近づけると、その方へ視線が戻った。','withdraw':f'{child}の顔がくしゃっとなり、泣き声に変わった。{actor}は遊びをやめ、抱き直して静かに待った。','sleepy':f'{child}のまぶたがゆっくり閉じかけた。{actor}は遊びの途中で手を止め、声を小さくした。','unexpected':f'{actor}が動きを止めたあとも、{child}は同じ所を見ていた。間を置いて同じことをすると、またそちらへ顔が向いた。'}
  beat('play_'+reaction,specifics.get((kind,reaction),generic[reaction]))
 elif kind=='meal':
  beat('meal_setup',f'いつもの食事の時間、{actor}は{child}のそばに座った。')
  beat('meal_'+reaction, f'{child}は差し出されたスプーンより、その持ち手へ手を伸ばした。{actor}は急がず、いったん手を止めた。' if reaction in ['reach','unexpected'] else f'{child}は途中で顔をそむけた。{actor}はひと口を急がせず、休みを入れた。' if reaction in ['withdraw','sleepy'] else f'{child}は{actor}がスプーンを動かす方を見ていた。次のひと口の前に、少しだけ二人の間が空いた。')
 elif kind in ['birthday','birthday_free']:
  years=max(1,round(age/12));scene['birthday_year']=years
  beat('birthday_setup',f'{actor}は{child}の{years}歳の誕生日に、自宅で'+('小さな飾りを用意した。' if kind=='birthday' else '写真を撮り、歌をうたった。'))
  beat('birthday_'+reaction, f'写真を撮ろうとすると、{child}はカメラの方へ手を伸ばした。撮れたのは、近づいてきた手の大きな一枚だった。' if reaction in ['reach','unexpected'] else f'歌の途中、{child}は{actor}の顔をじっと見ていた。歌い終わってからも、もう少しそのままで過ごした。' if reaction in ['watch','people'] else f'{child}は途中で眠そうになった。予定を短くして、写真を一枚だけ残した。')
 elif kind in ['photo','submission']:
  beat('photo_setup',f'{actor}は窓辺で{child}の写真を撮ろうとした。')
  beat('photo_'+reaction, f'カメラを構えた瞬間、{child}はそっぽを向いた。撮れた写真には横顔が残った。向き直るのを待った時間も、今日の撮影の一部になった。' if reaction in ['unexpected','people'] else f'{child}が目の前へ手を伸ばし、画面いっぱいに指が写った。きちんとした一枚とは違うけれど、その写真を消さずに残した。' if reaction=='reach' else f'大きなあくびが写った。{actor}は撮り直すのをやめ、この一枚を家族のアルバムに残した。' if reaction in ['sleepy','withdraw'] else f'{child}は窓の方を見ていた。その横顔を一枚、家族のアルバムに残した。')
 elif kind=='handover':
  beat('handover',f'{actor}は2時間、{child}と家で過ごした。'+(f'{other}はその間、'+('ひとりで静かに休んだ。' if x.npc_wish=='quiet' else '近所をひとりで歩いた。') if other else '今日は自分と子どもの時間にした。'))
  beat('daily_response',f'{child}が眠そうにしたので、途中からは遊びをやめて静かに過ごした。' if reaction in ['withdraw','sleepy'] else f'{child}は声をかける{actor}の方へ顔を向けた。今日は次の予定を入れず、そのまま家で過ごした。')
 elif kind=='visit':beat('visit',f'{actor}は{child}と{q["place"]}へ出かけ、部屋の様子を見て帰った。見学と入園は別なので、申し込みはまだ済んでいない。')
 # Derive novelty from observable facts, not latent response labels or changing dates.
 generic={'watch':'じっと見ていた','reach':'手を伸ばした','people':'そばの人を見ていた','withdraw':'泣いて途中で帰った' if kind in targets else '泣いて遊びを切り上げた','sleepy':'眠そうになって休んだ','unexpected':'動きを止めたあとも、同じ所を見ていた'}
 short=generic[reaction]
 if kind in targets and reaction=='unexpected':short=scene['target']+'を見ていた'
 if kind=='mirror' and reaction=='unexpected':short='鏡と抱いている腕を見比べていた'
 if kind=='book' and reaction=='unexpected':short='裏表紙を長く見ていた'
 if kind=='book' and reaction=='reach':short='ページに手をかけていた'
 if kind=='blocks' and reaction=='reach':short='大人が積んだ積み木を倒していた'
 if kind=='meal':short='スプーンの持ち手へ手を伸ばした' if reaction in ['reach','unexpected'] else '食事の途中に休みを入れた' if reaction in ['withdraw','sleepy'] else 'スプーンの動きを見ていた'
 if kind=='handover':short='眠そうにして静かに過ごした' if reaction in ['withdraw','sleepy'] else '声をかける大人の方を見ていた'
 if kind in ['photo','submission']:short='手が大きく写った写真を残した' if reaction=='reach' else 'あくびが写った写真を残した' if reaction in ['withdraw','sleepy'] else '横顔の写真を残した'
 scene['short_observation']=short
 scene['semantic_signature']=[kind,[b['text'] for b in scene['beats']]]
 if old and old.get('scene_id'):
  scene['source_refs'].append('C3.scenes/'+old['scene_id'])
  # Repetition becomes news only when an observable difference follows a real gap/choice.
  if old.get('short_observation')!=short and (x.month-old['period']>=3 or task['source']!='policy'):
   beat('continuity',f'{old["date"][:7]}に同じことをしたときは、{old.get("short_observation","別の姿があった")}。')
 return scene

def render_scene(scene):
 # No sampling, no latent state, no additional dialogue or physical achievements.
 return ''.join(b['text'] for b in scene['beats'])
