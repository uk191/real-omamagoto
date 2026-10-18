#!/usr/bin/env python3
"""Loopback player service; player projection and trusted state remain separate."""
import argparse,copy,json,re,secrets,sys,traceback,urllib.parse
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'22_experience_c0'))
from server import Handler as BaseHandler
from c0.bridge import make_engine
from c0.catalogue import PREFECTURES
sys.path.insert(0,str(ROOT))
from c31 import VERSION
from c31.model import Experience

class Application:
 def __init__(self,engine,save_dir):self.engine=engine;self.save_dir=Path(save_dir);self.save_dir.mkdir(parents=True,exist_ok=True);self.sessions={}
 def session(self,sid):
  if not isinstance(sid,str) or not re.fullmatch('[a-f0-9]{32}',sid) or sid not in self.sessions:raise LookupError('保存記録から再開するか、新しく始めてください。')
  return self.sessions[sid]
 def create(self,body):
  body=dict(body);body.setdefault('seed',secrets.token_hex(8));g=Experience.start(self.engine,**body);sid=secrets.token_hex(16);self.sessions[sid]=g;return sid,g
 def save(self,sid,elapsed_ms=0):
  g=self.session(sid)
  if type(elapsed_ms) not in [int,float] or not 0<=elapsed_ms<=3333:raise ValueError('進行時間を確認してください。')
  g.elapsed_ms=elapsed_ms;slot=secrets.token_hex(16);h=g.save(self.save_dir/(slot+'.json.gz'));meta={'slot':slot,'child_name':g.game.config['child_name'],'date':g.date,'age_months':g.game.core.elapsed_months,'version':VERSION,'sha256':h}
  (self.save_dir/(slot+'.meta.json')).write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8');return meta
 def load(self,slot):
  if not isinstance(slot,str) or not re.fullmatch('[a-f0-9]{32}',slot):raise ValueError('保存記録を選んでください。')
  g=Experience.load(self.save_dir/(slot+'.json.gz'),self.engine);sid=secrets.token_hex(16);self.sessions[sid]=g;return sid,g
 def command(self,sid,body):
  g=self.session(sid)
  if type(body.get('revision')) is not int or body['revision']!=g.revision:raise ValueError('別の操作で記録が更新されました。画面を再読込してください。')
  # Each input is an atomic candidate, including cost journal and native requests.
  obj=copy.copy(g);obj.__dict__.update(copy.deepcopy({k:v for k,v in g.__dict__.items() if k!='game'}));obj.game=g.game.clone();obj.game.core.a=copy.deepcopy(g.game.core.a)
  cmd=body.get('command')
  if cmd=='policy':obj.set_policy(body.get('policy'))
  elif cmd=='opportunity':obj.open_opportunity(body.get('theme','discover'))
  elif cmd=='choose':obj.choose(body.get('event_id'),body.get('choice_id'))
  elif cmd=='tick':
   if obj.running:obj.tick()
  elif cmd=='step':obj.tick()
  elif cmd=='clock':
   if type(body.get('running')) is not bool or body.get('speed') not in [.5,1,2,4]:raise ValueError('速度を選んでください。')
   obj.running=body['running'] and bool(obj.policy) and not obj.current_event and not obj.game.finished;obj.speed=body['speed'];obj.revision+=1
  else:raise ValueError('この操作は選べません。')
  self.sessions[sid]=obj;return obj

def serialized_request(fn):
 @wraps(fn)
 def wrapped(self,*args,**kwargs):
  return self.server.simulation_worker.submit(fn,self,*args,**kwargs).result()
 return wrapped

class Handler(BaseHandler):
 @serialized_request
 def do_GET(self):
  u=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(u.query)
  try:
   if u.path=='/api/health':return self.send(200,{'ok':True,'version':VERSION,'engine':'unchanged A3.0-0.2 + B-1.1'})
   if u.path=='/api/catalogue':return self.send(200,{'prefectures':[{'code':f'{i:02d}','name':n} for i,n in enumerate(PREFECTURES,1)]})
   if u.path=='/api/session':return self.send(200,{'view':self.app.session(q.get('sid',[''])[0]).view()})
   if u.path=='/api/saves':return self.send(200,{'saves':[json.loads(p.read_text(encoding='utf-8')) for p in sorted(self.app.save_dir.glob('*.meta.json'),key=lambda p:p.stat().st_mtime,reverse=True)]})
   static={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
   if u.path in static:
    name,mime=static[u.path];return self.send(200,(ROOT/'web'/name).read_bytes(),mime)
   return self.send(404,{'error':'このページはありません。'})
  except (ValueError,LookupError) as e:return self.send(422,{'error':str(e)})
  except Exception:traceback.print_exc();return self.send(500,{'error':'読み込めません。logs/server.logを確認してください。'})
 @serialized_request
 def do_POST(self):
  try:
   origin=self.headers.get('Origin')
   if self.headers.get('X-C0-Client')!='browser-v1' or (origin and urllib.parse.urlsplit(origin).netloc!=self.headers.get('Host')):return self.send(403,{'error':'ゲーム画面から操作してください。'})
   if self.headers.get_content_type()!='application/json':return self.send(415,{'error':'JSONで送信してください。'})
   length=int(self.headers.get('Content-Length',0))
   if not 0<length<=32768:raise ValueError('送信量を確認してください。')
   body=json.loads(self.rfile.read(length))
   if not isinstance(body,dict):raise ValueError('操作形式が正しくありません。')
   path=urllib.parse.urlsplit(self.path).path
   if path=='/api/start':sid,g=self.app.create(body);return self.send(200,{'sid':sid,'view':g.view()})
   if path=='/api/load':sid,g=self.app.load(body.get('slot'));return self.send(200,{'sid':sid,'view':g.view()})
   if path=='/api/save':return self.send(200,{'saved':self.app.save(body.get('sid'),body.get('elapsed_ms',0))})
   if path=='/api/command':g=self.app.command(body.get('sid'),body);return self.send(200,{'view':g.view()})
   return self.send(404,{'error':'この操作はありません。'})
  except (ValueError,TypeError,KeyError,LookupError) as e:return self.send(422,{'error':str(e)[:400]})
  except Exception:traceback.print_exc();return self.send(500,{'error':'操作を完了できません。logs/server.logを確認してください。'})

def main():
 p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1',choices=['127.0.0.1']);p.add_argument('--port',type=int,default=8788);p.add_argument('--save-dir',type=Path,default=ROOT/'runtime/saves');p.add_argument('--runtime-db',type=Path);a=p.parse_args()
 s=ThreadingHTTPServer((a.host,a.port),Handler);s.simulation_worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='C31Simulation');s.application=s.simulation_worker.submit(lambda:Application(make_engine(a.runtime_db),a.save_dir)).result();print(json.dumps({'ready':True,'port':s.server_port,'version':VERSION}),flush=True);s.serve_forever()
if __name__=='__main__':main()
