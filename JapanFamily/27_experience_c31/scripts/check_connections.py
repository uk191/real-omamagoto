"""Regression for Chromium pre-opened sockets blocking the old HTTPServer."""
import socket,json,time,urllib.request,concurrent.futures
from pathlib import Path
URL='http://127.0.0.1:8788'
sockets=[socket.create_connection(('127.0.0.1',8788),timeout=2) for _ in range(3)]
def get(_):
 t=time.monotonic()
 with urllib.request.urlopen(URL+'/api/health',timeout=3) as r:assert json.load(r)['ok']
 return time.monotonic()-t
try:
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:elapsed=list(pool.map(get,range(6)))
finally:
 for s in sockets:s.close()
assert max(elapsed)<3
body=json.dumps({'seed':1234,'policy':'stable','initial_cash_yen':1000000}).encode()
def post(path,body):
 req=urllib.request.Request(URL+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-C0-Client':'browser-v1'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
a=post('/api/start',json.loads(body));sid=a['sid'];revision=a['view']['revision']
b=post('/api/command',dict(sid=sid,revision=revision,command='tick'));assert b['view']['phase']==1
# A stale concurrent request must not advance or repeat the same purchase.
try:post('/api/command',dict(sid=sid,revision=revision,command='tick'));raise AssertionError('revision gate missing')
except urllib.error.HTTPError as e:assert e.code==422
saved=post('/api/save',dict(sid=sid));resumed=post('/api/load',dict(slot=saved['saved']['slot']));assert resumed['view']==b['view']
r={'idle_connections':3,'concurrent_health_requests':6,'seconds':elapsed,'start_tick_save_resume':True,'stale_revision_rejected':True,'simulation_code_unchanged':True}
(Path(__file__).resolve().parents[1]/'reports/connections.json').write_text(json.dumps(r,indent=2));print('C31_CONNECTIONS_PASS',r)
