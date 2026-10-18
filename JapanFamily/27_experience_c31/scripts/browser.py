"""Real Chromium UI: clock, four choices, follow-ups, save/resume, full 24 mo.
Automated developer inspection only, not a human enjoyment test.
"""
import json,time,sys,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];OUT=R/'reports';(OUT/'screenshots').mkdir(exist_ok=True)
sources=[R/'server.py',*(R/'c31').glob('*.py'),*(R/'web').glob('*')];fingerprints={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
baseline='--baseline' in sys.argv;port=8787 if baseline else 8788;errors=[];records=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for i in range(1 if baseline else 2):
  page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{port}');page.locator('#pref option').first.wait_for(state='attached')
  if baseline:page.locator('summary').first.click()
  else:
   assert page.locator('[name=initial_cash_yen]').count()==page.locator('[name=father_income_yen]').count()==0
   page.locator('[name=father_education]').select_option('4');page.locator('[name=mother_education]').select_option('2')
   page.locator('summary').first.click()
  page.locator('[name=father_age]').fill('23' if i==0 else '38');page.locator('[name=mother_age]').fill('22' if i==0 else '34');page.locator('[name=seed]').fill(str(4401+i));page.locator('[name=neighborhood]').select_option('city' if i==0 else 'rural')
  page.get_by_role('button',name='この家族で、暮らしを始める').click();page.locator('[data-policy=stable]').wait_for(timeout=45000)
  page.locator('[data-policy=stable]').click();start=time.monotonic();page.wait_for_function('()=>v.logs.length>0&&!busy',timeout=8000);assert page.evaluate('v.age_months')==0
  firstlog=time.monotonic()-start;page.wait_for_function('()=>v.age_months===1&&!busy',timeout=16000);monthsec=time.monotonic()-start;assert 9<monthsec<15
  page.locator('#toggle').click();page.wait_for_function('()=>!v.running&&!busy');snap=page.evaluate('v.age_months');page.wait_for_timeout(1100);assert page.evaluate('v.age_months')==snap
  page.locator('#money-detail').click();assert '給与の発生' in page.locator('#dialog-content').inner_text()
  if not baseline:
   page.get_by_text('資産・負債と初期生成の根拠',exact=True).click();assert '年齢との同時分布は未校正' in page.locator('#dialog-content').inner_text()
  page.locator('#close').click();page.locator('#save').click();page.wait_for_function('()=>document.querySelector("#toast").textContent.includes("保存しました")');page.reload();page.locator('[data-load]').first.wait_for();page.locator('[data-load]').first.click();page.wait_for_function('()=>v!==null&&!busy');assert page.evaluate('v.age_months')==snap and not page.evaluate('v.running')
  rec={'family':i,'first_log_seconds':firstlog,'month_seconds':monthsec,'paused_save_reload':True,'events':[]}
  if not baseline:
   page.locator('#speed').select_option('4');page.wait_for_function('()=>v.speed===4&&!busy');page.locator('#toggle').click();deadline=time.monotonic()+160
   while not page.evaluate('v.finished'):
    assert time.monotonic()<deadline,('timeout',page.evaluate('v.age_months'),page.locator('#toast').inner_text())
    if page.locator('[data-choice]').count():
     event=page.evaluate('v.event');assert len(event['choices'])==4 and not page.evaluate('v.running')
     if i==0:page.screenshot(path=str(OUT/f'screenshots/{event["domain"]}_{"followup" if event.get("parent_case_id") else "main"}.png'))
     page.locator('[data-choice]').nth(i).click();page.locator('#return-life').wait_for(timeout=12000);res=page.evaluate('v.last_choice_result');assert res['case_id']
     if i==0:page.screenshot(path=str(OUT/f'screenshots/{event["domain"]}_result_{len(rec["events"])}.png'))
     rec['events'].append({'event':event,'result':res});page.locator('#return-life').click();page.wait_for_timeout(100)
    page.wait_for_timeout(150)
   assert len(rec['events'])==8;assert page.locator('#toggle').is_disabled();page.locator('#save').click();page.wait_for_function('()=>!busy');rec['final_view']=page.evaluate('v')
   page.screenshot(path=str(OUT/f'screenshots/family{i}_24mo.png'));assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
   page.locator('#album').click();assert page.locator('.memory').count()>2;page.screenshot(path=str(OUT/f'screenshots/family{i}_album.png'));page.locator('#close').click()
   page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path=str(OUT/f'screenshots/family{i}_mobile.png'),full_page=True)
  records.append(rec);page.close();print('browser',i,'PASS',flush=True)
 browser.close()
assert not errors,errors
assert fingerprints=={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'Runtime source changed during browser test'
(OUT/('browser_baseline.json' if baseline else 'browser.json')).write_text(json.dumps({'records':records,'errors':errors,'source_sha256':fingerprints,'human_enjoyment_test':False,'Windows_native_test':False},ensure_ascii=False,indent=2));print('BROWSER_PASS')
