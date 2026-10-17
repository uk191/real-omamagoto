"""Operate real player controls; preserve screenshots and player-visible history."""
import json,sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports';(OUT/'screenshots').mkdir(exist_ok=True)
URL='http://127.0.0.1:8784';results=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for index,(seed,pref,start_age) in enumerate([(1301,'13',0),(1302,'27',6),(1303,'01',12)]):
  page=browser.new_page(viewport={'width':1440,'height':900});page.on('pageerror',lambda err:errors.append(str(err)))
  page.goto(URL);page.locator('[name=seed]').fill(str(seed));page.locator('#pref').select_option(pref)
  page.locator('summary').first.click();page.locator('[name=initial_cash_yen]').fill('8000000')
  page.get_by_role('button',name='この家族の暮らしを確認する').click();page.locator('#begin').wait_for(timeout=30000);page.wait_for_timeout(500);page.screenshot(path=str(OUT/f'screenshots/family{index+1}_identity.png'));page.locator('#begin').click()
  # Advance only through documented controls, no internal state edits.
  for _ in range(start_age*3):
   old=page.evaluate('v.revision');page.locator('#step').click();page.wait_for_function('r=>v.revision>r',arg=old)
  page.wait_for_timeout(500);page.screenshot(path=str(OUT/f'screenshots/family{index+1}_before.png'))
  snapshots=[]
  for m in range(6):
   kind='voice' if start_age+m<2 else 'book'
   page.locator(f'[data-plan={kind}]').click();page.locator('#confirm-plan').click();page.wait_for_function('()=>!document.querySelector("#dialog").open')
   if m==0:
    page.locator('[data-decision=shorter]').click();page.locator('#confirm-decision').click();page.wait_for_function('()=>!document.querySelector("#dialog").open')
   if start_age+m>=1:
    page.locator('[data-plan=park]').click();page.locator('#confirm-plan').click();page.wait_for_function('()=>!document.querySelector("#dialog").open')
   if m==1:
    page.locator('[data-plan=handover]').click();page.locator('#confirm-plan').click();page.wait_for_function('()=>!document.querySelector("#dialog").open')
   for stage in range(3):
    old=page.evaluate('v.revision');page.locator('#step').click();page.wait_for_function('r=>v.revision>r',arg=old)
    if m==0 and stage==0:page.wait_for_timeout(500);page.screenshot(path=str(OUT/f'screenshots/family{index+1}_immediate.png'))
   snapshots.append(page.evaluate('v'))
  page.wait_for_timeout(500);page.screenshot(path=str(OUT/f'screenshots/family{index+1}_six_months.png'))
  # Real timers: at 1x one stage arrives after ~3.33s, not only at month boundary.
  old_logs=page.evaluate('v.logs.length');page.locator('#toggle').click();page.wait_for_function('n=>v.logs.length>n',arg=old_logs,timeout=15000)
  first=page.evaluate('({phase:v.phase,age:v.age_months})');assert first['phase']==1
  page.locator('#toggle').click()
  age=page.evaluate('v.age_months');page.locator('#save').click();page.wait_for_function('()=>document.querySelector("#toast").textContent.includes("保存しました")')
  page.reload();page.locator('[data-load]').first.wait_for();page.locator('[data-load]').first.click();page.wait_for_function('()=>v!==null');assert page.evaluate('v.age_months')==age
  # Check full 24mo horizon with player controls. Continue staged timer at4x.
  page.locator('#speed').select_option('4');page.wait_for_timeout(200);page.locator('#toggle').click()
  deadline=time.monotonic()+110
  while True:
   state=page.evaluate('({finished:v.finished,running:v.running})')
   if state['finished']:break
   if time.monotonic()>deadline:raise AssertionError('24mo timer timeout')
   if not state['running']:
    page.locator('#toggle').click()
   page.wait_for_timeout(400)
  assert page.locator('#toggle').is_disabled();page.wait_for_timeout(500);page.screenshot(path=str(OUT/f'screenshots/family{index+1}_24months.png'))
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  results.append({'seed':seed,'pref':pref,'start_age':start_age,'six_month_views':snapshots,'timer_stage_check':first,'save_resume':True,'completed_24months':True,'browser_errors':list(errors)})
  page.close()
 # Phone layout with action and records accessible without tabs.
 page=browser.new_page(viewport={'width':390,'height':844});page.goto(URL);page.locator('[data-load]').first.wait_for();page.locator('[data-load]').first.click();page.wait_for_function('()=>v!==null');assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');page.screenshot(path=str(OUT/'screenshots/phone.png'),full_page=True);browser.close()
assert not errors,errors
(OUT/'browser_results.json').write_text(json.dumps({'families':results,'errors':errors,'actual_user_test':False},ensure_ascii=False,indent=2))
print('PASS: three families, real controls, staged timers, save/resume, 24mo, no console errors')
