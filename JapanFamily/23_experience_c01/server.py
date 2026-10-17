#!/usr/bin/env python3
"""Loopback-only player server. Scientific truth and save files are not served."""
import argparse,json,re,secrets,sys,traceback,urllib.parse
from pathlib import Path
from http.server import HTTPServer
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'22_experience_c0'))
from server import Handler as BaseHandler
# This file is executed as __main__; the imported server is the old C0 module.
from c0.bridge import make_engine
from c0.catalogue import PREFECTURES
sys.path.insert(0,str(ROOT))
from c01 import VERSION
from c01.experience import Experience,ENVIRONMENTS

class Application:
    def __init__(self,engine,save_dir):
        self.engine=engine;self.save_dir=Path(save_dir);self.save_dir.mkdir(parents=True,exist_ok=True);self.sessions={}
    def session(self,sid):
        if not isinstance(sid,str) or not re.fullmatch('[a-f0-9]{32}',sid) or sid not in self.sessions:raise LookupError('保存記録から再開するか、新しく始めてください。')
        return self.sessions[sid]
    def create(self,payload):
        body=dict(payload);body['seed']=body.get('seed') or secrets.token_hex(8)
        game=Experience.start(self.engine,**body);sid=secrets.token_hex(16);self.sessions[sid]=game;return sid,game
    def save(self,sid):
        game=self.session(sid);slot=secrets.token_hex(16);h=game.save(self.save_dir/(slot+'.json.gz'));v=game.view()
        meta={'slot':slot,'child_name':v['child_name'],'date':v['date'],'age_months':v['age_months'],'version':VERSION,'payload_sha256':h}
        (self.save_dir/(slot+'.meta.json')).write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8');return meta
    def load(self,slot):
        if not isinstance(slot,str) or not re.fullmatch('[a-f0-9]{32}',slot):raise ValueError('保存記録を指定してください。')
        game=Experience.load(self.save_dir/(slot+'.json.gz'),self.engine);sid=secrets.token_hex(16);self.sessions[sid]=game;return sid,game

class Handler(BaseHandler):
    server_version='C01-local'
    def do_GET(self):
        url=urllib.parse.urlsplit(self.path);q=urllib.parse.parse_qs(url.query)
        try:
            if url.path=='/api/health':return self.send(200,{'ok':True,'version':VERSION,'engine':'unchanged A3.0-0.2 + B-1.1'})
            if url.path=='/api/catalogue':return self.send(200,{'prefectures':[{'code':f'{i:02d}','name':n} for i,n in enumerate(PREFECTURES,1)],'environments':ENVIRONMENTS})
            if url.path=='/api/saves':
                saves=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(self.app.save_dir.glob('*.meta.json'),key=lambda p:p.stat().st_mtime,reverse=True)]
                return self.send(200,{'saves':saves})
            if url.path=='/api/session':return self.send(200,{'view':self.app.session(q.get('sid',[''])[0]).view()})
            static={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
            if url.path in static:
                name,mime=static[url.path];return self.send(200,(ROOT/'web'/name).read_bytes(),mime)
            return self.send(404,{'error':'このページはありません。'})
        except LookupError as e:return self.send(404,{'error':str(e)})
        except Exception:
            traceback.print_exc();return self.send(500,{'error':'記録を読み込めません。logs/server.logを確認してください。'})
    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if (origin and urllib.parse.urlsplit(origin).netloc!=self.headers.get('Host')) or self.headers.get('X-C0-Client')!='browser-v1':return self.send(403,{'error':'ゲーム画面から操作してください。'})
            if self.headers.get_content_type()!='application/json':return self.send(415,{'error':'JSON形式で送信してください。'})
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=32768:return self.send(413,{'error':'送信量の上限を超えました。'})
            b=json.loads(self.rfile.read(length))
            if not isinstance(b,dict):raise ValueError('操作形式が正しくありません。')
            path=urllib.parse.urlsplit(self.path).path
            if path=='/api/start':
                sid,g=self.app.create(b);return self.send(200,{'sid':sid,'view':g.view()})
            if path=='/api/load':
                if set(b)!={'slot'}:raise ValueError('保存記録だけを指定してください。')
                sid,g=self.app.load(b['slot']);return self.send(200,{'sid':sid,'view':g.view()})
            if path!='/api/command':return self.send(404,{'error':'この操作はありません。'})
            if set(b)-{'sid','revision','command','event_id','choice_id','running','speed','remaining_ms','kind'}:raise ValueError('指定できない操作項目です。')
            g=self.app.session(b.get('sid'))
            if type(b.get('revision')) is not int or b['revision']!=g.revision:return self.send(409,{'error':'別の操作で記録が更新されました。最新の表示を読み直してください。','view':g.view()})
            command=b.get('command')
            if command=='advance':g.advance()
            elif command=='choose':g.choose(b.get('event_id'),b.get('choice_id'))
            elif command=='playback':g.set_playback(b.get('running'),b.get('speed'),b.get('remaining_ms'))
            elif command=='observe':
                if g.event():raise ValueError('先に相談の選択肢を選んでください。')
                g.game.observe('observe');g.child_scene(interaction=True);g.revision+=1
            elif command=='save':return self.send(200,{'view':g.view(),'saved':self.app.save(b['sid'])})
            else:raise ValueError('この操作は選べません。')
            return self.send(200,{'view':g.view()})
        except (ValueError,TypeError,KeyError) as e:return self.send(422,{'error':'条件を確認してください。'+str(e)[:240]})
        except LookupError as e:return self.send(404,{'error':str(e)})
        except Exception:
            traceback.print_exc();return self.send(500,{'error':'操作を完了できません。logs/server.logを確認してください。'})

def main():
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1',choices=['127.0.0.1']);p.add_argument('--port',type=int,default=8783);p.add_argument('--save-dir',type=Path,default=ROOT/'runtime/saves');p.add_argument('--runtime-db',type=Path);a=p.parse_args()
    server=HTTPServer((a.host,a.port),Handler);server.application=Application(make_engine(a.runtime_db),a.save_dir)
    print(json.dumps({'ready':True,'port':server.server_port,'version':VERSION}),flush=True);server.serve_forever()
if __name__=='__main__':main()
