"""Fictional goods/venues and explicit price/time assumptions, not local listings.
Each entry is an executable activity with distinct materials, budget or logistics.
No activity adds developmental points. Amounts are incremental discretionary costs.
"""
ACTS={}
def add(key,title,place,hours,cost,age=0,*,item=None,genre='play',stim=.4,agreement=False,bucket='care'):
 ACTS[key]=dict(title=title,place=place,hours=hours,cost=cost,min_age=age,item=item,genre=genre,stim=stim,agreement=agreement,bucket=bucket)
add('voice','顔を見て、ゆっくり話す','自宅の窓辺',.25,0,genre='communication',stim=.15)
add('floor','床に場所をつくって遊ぶ','自宅の敷物の上',.5,0,3,genre='movement')
add('book','絵本を一緒に開く','自宅の絵本の場所',.5,1200,2,item='book',genre='books')
add('toy','布のボールを転がす','自宅の敷物の上',.5,1600,4,item='toy')
add('music','小さな鈴を鳴らしてみる','自宅の居間',.5,900,3,item='bell',genre='music',stim=.6)
add('blocks','大人が積んだ積み木で遊ぶ','自宅の床',.75,2400,9,item='blocks',genre='construction')
add('mirror','鏡に一緒に映ってみる','自宅の居間',.25,0,2,genre='discovery')
add('cloth','布の陰から、いないいないばあ','自宅の居間',.25,0,4,genre='communication')
add('meal','いつもの食事を一緒に見守る','自宅の食卓',.5,0,6,genre='food',stim=.25)
add('park','近所の公園へ','近所の公園（架空の散歩先）',1.5,0,1,genre='outdoors',stim=.7,bucket='rest')
add('center','親子の部屋へ出かける','こもれび親子の部屋（架空）',2,300,3,genre='community',stim=.9,bucket='rest')
add('aquarium','水族館へ行ってみる','海色の水族館（架空）',5,4800,6,genre='leisure',stim=1.2,bucket='rest')
add('zoo','動物を見に行ってみる','丘の動物園（架空）',5,3200,8,genre='animals',stim=1.1,bucket='rest')
add('train','電車の見える場所へ','線路の見える散歩道（架空）',2,600,6,genre='discovery',stim=1.,bucket='rest')
add('leaves','季節の色を探して歩く','近所の並木道（架空）',1.5,0,3,genre='season',stim=.5,bucket='rest')
add('photo','今の姿を家族の写真に残す','自宅の窓辺',.75,0,genre='memory')
add('birthday','家族だけで誕生日を祝う','自宅の居間',2,2000,11,genre='anniversary',agreement=True,bucket='rest')
add('birthday_free','写真と歌で誕生日を祝う','自宅の居間',1,0,11,genre='anniversary',bucket='rest')
add('handover','自分が育児を引き受ける','自宅の居間',2,0,genre='family',agreement=True,bucket='rest')
add('visit','保育の見学先を訪ねる','見学用の親子室（架空）',2,500,genre='childcare',agreement=True,bucket='rest')
add('trip','一泊の家族旅行を計画する','みずうみの宿（架空）',16,28000,6,genre='travel',stim=1.4,agreement=True,bucket='rest')
add('submission','家族写真の展示企画へ応募する','自宅の写真を選ぶ場所',1,0,3,genre='challenge',agreement=True,bucket='rest')
ITEM_NAMES={'book':'『まると、てのひら』（架空の絵本）','toy':'赤い布のボール','bell':'黄色い持ち手の鈴','blocks':'木の四角い積み木'}
# Theme determines real candidate activities; the menu never exposes this whole table.
THEMES={'discover':('この子と、新しいこと', ['aquarium','music','mirror','cloth','zoo','train','blocks','book','toy']),
 'weekend':('今度の休日、どこで過ごそう',['trip','aquarium','zoo','center','leaves','park']),
 'remember':('今の姿を、残しておこう',['submission','photo','book'])}
