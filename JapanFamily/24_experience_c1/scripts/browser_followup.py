"""Targeted follow-up for scroll tracking, financial visibility, recurrence, inputs."""
import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports';findings=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for i,(seed,pref,age) in enumerate([(1301,'13',0),(1302,'27',6),(1303,'01',12)],1):
  page=browser.new_page(viewport={'width':1440,'height':900});page.goto('http://127.0.0.1:8784')
  page.locator('[name=seed]').fill(str(seed));page.locator('#pref').select_option(pref);page.locator('summary').first.click();page.locator('[name=initial_cash_yen]').fill('8000000');page.locator('[name=father_education]').select_option('4')
  page.get_by_role('button',name='この家族の暮らしを確認する').click();page.locator('#begin').wait_for(timeout=30000);page.locator('#begin').click()
  def step():
   r=page.evaluate('v.revision');page.locator('#step').click();page.wait_for_function('r=>v.revision>r&&!busy',arg=r)
  for _ in range(age*3):step()
  for m in range(6):
   page.locator('[data-plan=voice]').click();page.locator('#repeat-plan').check();page.locator('#confirm-plan').click();page.wait_for_function('()=>!document.querySelector("#dialog").open')
   # Retained recurring plans already cover later months; don't enqueue duplicates.
   break
  page.locator('[data-decision=shorter]').click();page.locator('#confirm-decision').click();page.wait_for_function('()=>!document.querySelector("#dialog").open')
  for _ in range(18):step()
  page.wait_for_timeout(600)
  scroll=page.locator('#logs').evaluate('(el)=>el.scrollHeight-el.scrollTop-el.clientHeight');assert scroll<3,scroll
  assert page.evaluate('v.experience_count')==6
  assert '入金' in page.locator('#money').inner_text()
  assert page.evaluate('v.profiles.father.education') is not None
  page.screenshot(path=str(OUT/f'screenshots/family{i}_followup_six_months.png'))
  # Save immediately after pause must wait for input handling, not silently drop it.
  page.locator('#toggle').click();page.locator('#toggle').click();page.locator('#save').click();page.wait_for_function('()=>document.querySelector("#toast").textContent.includes("保存しました")')
  assert not page.evaluate('v.running')
  findings.append({'seed':seed,'start_age':age,'following_latest_log_residual_pixels':scroll,'six_actual_recurring_experiences':page.evaluate('v.experience_count'),'education_option_accepted':True,'queued_input_save':True,'cash_flows_visible':True});page.close()
 browser.close()
(OUT/'browser_followup.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2));print(json.dumps(findings))
