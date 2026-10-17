"""Actual browser play: auto clock, prominent decisions, choose/resume, save."""
import json,time,hashlib,datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports';(OUT/'screenshots').mkdir(exist_ok=True)
results=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for i,(role,pref,policy,partner) in enumerate([('father','13','play',True),('mother','47','stable',False),('mother','23','social',True)],1):
  page=browser.new_page(viewport={'width':1440,'height':900});page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8787')
  page.locator('[name=role]').select_option(role);page.locator('[name=partner]').select_option('true' if partner else 'false');page.locator('#pref').select_option(pref);page.locator('summary').first.click();page.locator('[name=initial_cash_yen]').fill('1500000');page.locator('[name=seed]').fill(str(2300+i))
  page.get_by_role('button',name='この家族で、暮らしを始める').click();page.locator('[data-policy]').first.wait_for(timeout=30000);assert page.locator('[data-policy]').count()==6
  page.screenshot(path=str(OUT/f'screenshots/family{i}_policy.png'));t=time.monotonic();page.locator(f'[data-policy={policy}]').click();page.wait_for_function('()=>v.policy!==null&&!busy')
  # A live log must arrive before the calendar boundary, from the first real phase.
  page.wait_for_function('()=>v.logs.length>0',timeout=7000);assert page.evaluate('v.phase')==1
  assert page.evaluate('v.age_months')==0
  firstlog=time.monotonic()-t;page.wait_for_function('()=>v.age_months===1',timeout=12000);elapsed=time.monotonic()-t;assert 9<elapsed<14,(elapsed,firstlog)
  visible_buttons=page.locator('main button:visible').count();assert visible_buttons<=6,visible_buttons
  page.locator('#toggle').click();page.wait_for_function('()=>!v.running&&!busy');age=page.evaluate('v.age_months');page.wait_for_timeout(1000);assert page.evaluate('v.age_months')==age
  page.locator('#money-detail').click();assert '給与の発生' in page.locator('#dialog-content').inner_text();page.screenshot(path=str(OUT/f'screenshots/family{i}_money.png'));page.locator('#close').click()
  page.locator('#new-joy').click();page.locator('[data-theme=remember]').click();page.locator('[data-choice=photo]').wait_for();page.locator('[data-choice=photo]').click();page.locator('#return-life').wait_for();assert page.evaluate('v.album.length')>0;page.screenshot(path=str(OUT/f'screenshots/family{i}_own_photo.png'));page.locator('#return-life').click();page.locator('#toggle').click();page.wait_for_function('()=>!v.running&&!busy');
  page.locator('#save').click();page.wait_for_function('()=>document.querySelector("#toast").textContent.includes("保存しました")');page.reload();page.locator('[data-load]').first.wait_for();page.locator('[data-load]').first.click();page.wait_for_function('()=>v!==null&&!busy');assert page.evaluate('v.policy')==policy and page.evaluate('v.age_months')==age
  page.locator('#speed').select_option('4');page.wait_for_function('()=>v.speed===4&&!busy');page.locator('#toggle').click();events=[];progress_month=-1;deadline=time.monotonic()+145
  while not page.evaluate('v.finished'):
   if time.monotonic()>deadline:
    page.screenshot(path=str(OUT/f'screenshots/family{i}_timeout.png'));(OUT/'browser_failure.json').write_text(json.dumps({'view':page.evaluate('v'),'dialog':page.locator('#dialog').inner_text(),'toast':page.locator('#toast').inner_text(),'errors':errors},ensure_ascii=False,indent=2));raise AssertionError('24month play timed out; inspect browser_failure.json')
   current=page.evaluate('v.age_months')
   if current!=progress_month and current%6==0:print('browser progress',i,current,flush=True);progress_month=current
   if page.locator('[data-choice]').count():
    event=page.evaluate('v.event');before=page.evaluate('v.money.cash');eid=event['id'];page.wait_for_timeout(400)
    if len(events)<2:page.screenshot(path=str(OUT/f'screenshots/family{i}_event{len(events)}.png'))
    assert page.evaluate('v.running') is False
    page.locator('[data-choice]').nth((i-1)%len(event['choices'])).click();page.locator('#return-life').wait_for();assert '今日の支払い' in page.locator('#dialog-content').inner_text()
    result=page.evaluate('v.last_choice_result');assert result['event_id']==eid
    if len(events)<2:page.screenshot(path=str(OUT/f'screenshots/family{i}_result{len(events)}.png'))
    events.append({'event':event,'result':result});page.locator('#return-life').click();page.wait_for_timeout(150);assert page.evaluate('v.running') is True
   page.wait_for_timeout(200)
  page.locator('#album').click();assert page.locator('.memory').count()>2;page.screenshot(path=str(OUT/f'screenshots/family{i}_album.png'));page.locator('#close').click();assert page.locator('#toggle').is_disabled();page.wait_for_timeout(500);page.screenshot(path=str(OUT/f'screenshots/family{i}_24months.png'))
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  results.append({'role':role,'partner':partner,'pref':pref,'policy':policy,'first_log_seconds':firstlog,'first_month_seconds':elapsed,'visible_main_buttons':visible_buttons,'events':events,'final_view':page.evaluate('v'),'save_resume':True,'pause_resume':True});page.close();print('browser family',i,'24mo PASS',flush=True)
 # Mobile is the same screen and decision flow, no navigation tabs.
 page=browser.new_page(viewport={'width':390,'height':844});page.goto('http://127.0.0.1:8787');page.locator('[data-load]').first.wait_for();page.locator('[data-load]').first.click();page.wait_for_function('()=>v!==null');assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path=str(OUT/'screenshots/phone.png'),full_page=True);browser.close()
assert not errors,errors
(OUT/'browser.json').write_text(json.dumps({'families':results,'errors':errors,'human_usability_test':False,'completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'server.py',ROOT/'c3/model.py',ROOT/'c3/scenes.py',ROOT/'web/app.js']}},ensure_ascii=False,indent=2));print('C3_BROWSER_PASS')
