"""Shared contract, run first against immutable C3 and then the update."""
import sys,json,tempfile,copy,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];P=R.parent
sys.path.insert(0,str(P/'26_experience_c3'))
from c3.model import Experience as Baseline
from c0.bridge import make_engine,digest

def contract(cls):
 engine=make_engine();x=cls.start(engine,seed=4401,prefecture_code='13',conditions={'father_age':23,'mother_age':22},role='father',policy='play')
 assert x.actor=='father' and len(x.game.core.identity['person_links'])>=2
 identity=copy.deepcopy(x.game.core.identity);initial=digest(x.game.core.initial_a)
 result={'generation_and_father':True,'A_B_identity':identity};timeline=[];events=0
 # Pure inspection must not consume randomness or alter state.
 snapshot=digest(x.snapshot());x.view();x.view();assert snapshot==digest(x.snapshot())
 x.tick();assert x.phase==1;assert x.logs and x.month==0
 # Core clock state can pause and change speed; browser verifies the actual timer.
 x.running=False;x.speed=4;x.elapsed_ms=1500
 with tempfile.TemporaryDirectory() as t:
  p=Path(t)/'save.gz';x.save(p);y=cls.load(p,engine);assert x.snapshot()==y.snapshot()
  for obj in [x,y]:
   obj.running=True
   while not obj.game.finished:
    if obj.current_event:
     assert not obj.running
     e=obj.events[-1];c=next((c for c in e['choices'] if not c.get('disabled')),None);assert c
     obj.choose(e['id'],c['id']);assert obj.running or obj.game.finished
    else:obj.tick()
    assert obj.financial_view()['cash_identity_residual'] in [0,None]
   obj.game.core.assert_consistent()
  assert x.snapshot()==y.snapshot()
 assert x.game.core.elapsed_months==24 and x.game.core.identity==identity and digest(x.game.core.initial_a)==initial
 assert all(l.get('published_date',l['date'])<=x.date for l in x.logs)
 assert [l.get('published_period',l['period']) for l in x.logs]==sorted(l.get('published_period',l['period']) for l in x.logs)
 assert x.view()['money']['cash']==x.game.core.a['accounts']['cash']
 assert len(x.experiences)>0 and x.game.core.child._state['age_days']>700
 result.update(auto_pause_and_resume=True,month24=True,clock_and_speed_saved=True,save_and_replay_exact=True,log_publication_order=True,native_account_identity=True,child_and_family_updates=True,view_pure=True,unchanged_initial_family=True,events=len(x.events))
 return result
if __name__=='__main__':
 name=sys.argv[1] if len(sys.argv)>1 else 'baseline'
 if name=='baseline':cls=Baseline
 else:
  sys.path.insert(0,str(R));from c31.model import Experience;cls=Experience
 r=contract(cls);(R/'reports'/('regression_'+name+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2));print(name,'REGRESSION_PASS',r)
