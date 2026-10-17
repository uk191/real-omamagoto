"""Normal UI scenario inspection with real browser timers; not a user study."""
import json,time,sys,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('C01_TEST_OUTPUT',str(ROOT/'reports')));(OUT/'screenshots').mkdir(exist_ok=True)
records=[];errors=[];timings={}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1366,'height':768},device_scale_factor=1)
 page.on('pageerror',lambda e:errors.append(str(e)))
 def seed(route):
  b=route.request.post_data_json;b['seed']='C01-browser-p0';route.continue_(post_data=json.dumps(b))
 page.route('**/api/start',seed)
 page.goto(os.environ.get('C01_TEST_URL','http://127.0.0.1:8783'));expect(page.locator('#prefecture option')).to_have_count(47)
 page.select_option('[name=environment]','urban');page.fill('[name=mother_age]','30');page.fill('[name=father_age]','32');page.select_option('[name=mother_education]','4');page.select_option('[name=mother_employed]','true');page.select_option('[name=father_employed]','true');page.select_option('[name=birth_rank]','1');page.fill('[name=annual_income]','600');page.fill('[name=initial_cash]','500')
 page.screenshot(path=str(OUT/'screenshots/01_setup.png'),full_page=True)
 with page.expect_response('**/api/start') as response:page.click('#start-button')
 r=response.value.json();assert response.value.status==200,r;view=r['view']
 assert view['environment']['class']=='urban';assert next(x for x in view['parents'] if x['id']=='mother')['education_coarse']=='4'
 t=time.monotonic();expect(page.locator('#age')).to_contain_text('0か月');page.screenshot(path=str(OUT/'screenshots/02_autoplay_month0.png'),full_page=True)
 expect(page.locator('#age')).to_contain_text('1か月',timeout=15000);timings['one_month_1x_seconds']=time.monotonic()-t
 assert 9<=timings['one_month_1x_seconds']<=13
 expect(page.locator('#play-state')).to_contain_text('相談');expect(page.locator('[data-choice=apply]')).to_be_visible()
 page.screenshot(path=str(OUT/'screenshots/03_allowance_auto_pause.png'),full_page=True)
 assert not page.evaluate('document.documentElement.scrollHeight>window.innerHeight+2')
 assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth+2')
 with page.expect_response('**/api/command') as response:page.click('[data-choice=apply]')
 v=response.value.json()['view'];assert v['queue'][0]['kind']=='apply_child_allowance'
 expect(page.locator('#queued')).to_contain_text('児童手当')
 # Explicit pause, speed setting, then resume. Save while running and restore.
 page.select_option('#speed','4');page.wait_for_timeout(250)
 page.click('#toggle');expect(page.locator('#play-state')).to_contain_text('自動');t=time.monotonic()
 expect(page.locator('#age')).to_contain_text('2か月',timeout=6000);timings['one_month_4x_seconds']=time.monotonic()-t
 assert 1.8<=timings['one_month_4x_seconds']<=4.5
 # At month2 there may be a child event; resolve it before testing pause.
 while page.locator('[data-choice]').count():
  page.locator('[data-choice]').first.click();page.wait_for_timeout(100)
 if '自動' not in page.locator('#play-state').inner_text():page.click('#toggle')
 page.click('#toggle');expect(page.locator('#play-state')).to_contain_text('一時停止')
 frozen=page.locator('#age').inner_text();page.wait_for_timeout(3000);assert page.locator('#age').inner_text()==frozen
 page.select_option('#speed','0.5');page.wait_for_timeout(150);expect(page.locator('#speed')).to_have_value('0.5')
 before=float(page.locator('#progress-fill').evaluate('(e)=>parseFloat(e.style.width)'));page.click('#toggle');page.wait_for_timeout(1000);page.click('#toggle');after=float(page.locator('#progress-fill').evaluate('(e)=>parseFloat(e.style.width)'));assert 3<=after-before<=10
 page.select_option('#speed','2');page.wait_for_timeout(150);expect(page.locator('#speed')).to_have_value('2')
 before=float(page.locator('#progress-fill').evaluate('(e)=>parseFloat(e.style.width)'));page.click('#toggle');page.wait_for_timeout(1000);page.click('#toggle');after=float(page.locator('#progress-fill').evaluate('(e)=>parseFloat(e.style.width)'));assert 15<=after-before<=30
 page.select_option('#speed','4');page.wait_for_timeout(150)
 page.click('#toggle');expect(page.locator('#play-state')).to_contain_text('自動')
 with page.expect_response(lambda r:r.url.endswith('/api/command') and r.request.post_data_json.get('command')=='save') as saved_response:page.click('#save')
 saved=saved_response.value.json()['saved'];assert saved['slot']
 # Reload entire document; ordinary save-list UI resumes actual saved timer.
 page.reload();page.click('#show-saves');page.locator(f'[data-slot="{saved["slot"]}"]').click();expect(page.locator('#speed')).to_have_value('4')
 expect(page.locator('#game')).to_be_visible();expect(page.locator('#play-state')).to_contain_text('自動')
 took_months=set();deadline=time.monotonic()+160;last_age=-1
 while time.monotonic()<deadline:
  text=page.locator('#age').inner_text();age=int(text.split('·')[1].split('か月')[0].strip())
  if age!=last_age:
   last_age=age
   # Player-visible log only; no debug page or hidden model inspection.
   records.append({'age_months':age,'date':page.locator('#date').inner_text(),'cash':page.locator('#cash').inner_text(),'cash_delta':page.locator('#cash-delta').inner_text(),'logs':page.locator('#journal').inner_text()})
  if age in [6,12,18,24] and age not in took_months:
   page.screenshot(path=str(OUT/'screenshots'/f'month_{age:02d}.png'),full_page=True);took_months.add(age)
  if age==24:break
  if page.locator('[data-choice]').count():
   # Prefer real concrete actions, including trimming budget at scheduled reviews.
   choices=page.locator('[data-choice]');choices.first.click();page.wait_for_timeout(130)
  elif '自動で進行' not in page.locator('#play-state').inner_text() and '更新' not in page.locator('#play-state').inner_text():
   if page.locator('#toggle').is_enabled():page.click('#toggle')
  page.wait_for_timeout(150)
 assert last_age==24,last_age
 expect(page.locator('#play-state')).to_contain_text('24か月');assert not errors,errors
 last=page.locator('.log').last.bounding_box();box=page.locator('#journal').bounding_box();assert last['y']+last['height']<=box['y']+box['height']+12, 'latest life log did not follow time progression'
 if page.locator('.growth-item').count():
  last=page.locator('.growth-item').last.bounding_box();box=page.locator('#growth').bounding_box();assert last['y']+last['height']<=box['y']+box['height']+2, 'observed growth was clipped'
 # Save completed play, inspect the optional detail drawer once.
 page.click('#save');page.wait_for_timeout(150);page.click('#details');expect(page.locator('#detail-dialog')).to_be_visible();page.screenshot(path=str(OUT/'screenshots/09_details.png'),full_page=True);page.click('#close-details')
 assert not page.evaluate('document.documentElement.scrollHeight>window.innerHeight+2')
 result={'checks':{'customization_applies':True,'real_10_second_autoplay':True,'speed_4x':True,'pause_freezes_time':True,'speed_half_and_2x_progress_measured':True,'real_context_choice_and_queued_request':True,'save_reload_running_timer':True,'normal_ui_24_months':True,'one_screen_1366x768':True,'no_page_errors':True},'timings':timings,'errors':errors,'browser':browser.version,'kind':'developer browser scenario inspection, not human play test','records':records}
 (OUT/'browser_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');browser.close();print(json.dumps({k:v for k,v in result.items() if k!='records'},ensure_ascii=False),flush=True)
