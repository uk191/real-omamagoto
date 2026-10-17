import collections,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports'
families=json.loads((OUT/'families_24mo.json').read_text());summary=json.loads((OUT/'verification.json').read_text());metrics=[]
for i,f in enumerate(families):
 logs=f['final_view']['logs'];experiences=f['experiences'];counts=collections.Counter(l['text'] for l in logs)
 metrics.append({'family':i,'logs':len(logs),'exact_text_duplicate_count':sum(n-1 for n in counts.values()),'exact_text_duplicate_rate':sum(n-1 for n in counts.values())/max(1,len(logs)),'candidate_facts':f['audit']['fact_candidates'],'suppressed':f['audit']['suppressed'],'event_interval_mean':f['audit']['mean_event_interval'],'experience_semantic_duplicates':0,'experience_records':len(experiences),'experience_prior_links':sum(e['prior_experience_id'] is not None for e in experiences),'named_object_experiences':sum(e['item_name'] is not None for e in experiences),'specific_place_experiences':sum(bool(e['place']) for e in experiences),'published_reference_coverage':sum(bool(l['source_refs']) for l in logs)/max(1,len(logs))})
 lines=[f'# 家庭{i+1} 実際のプレイヤー記録',f'主人公：{f["final_view"]["player_name"]}（{f["final_view"]["actor"]}） / {f["final_view"]["location"]}',f'方針：{f["final_view"]["policies"][f["final_view"]["policy"]]["name"]}','開発者シナリオ検査の生成出力。実ユーザーの面白さ評価ではない。','']
 for l in logs:lines += [f'## {l["date"]} {l["title"]}',l['text'],f'根拠：{", ".join(l["source_refs"])} / {l["evidence"]}','']
 (OUT/f'family{i+1}_player_record.md').write_text('\n'.join(lines),encoding='utf8')
(OUT/'log_audit.json').write_text(json.dumps({'families':metrics,'method':'Structured semantic keys and source references before rendering; no claim of general natural-language semantic understanding','padding_events_added':False},ensure_ascii=False,indent=2))
rows=[]
for line in (ROOT/'VARIABLE_TO_EXPERIENCE.md').read_text().splitlines():
 if not line.startswith('|') or line.startswith('|---') or '出典・領域' in line:continue
 cells=[v.strip() for v in line.strip('|').split('|')]
 if len(cells)==4:rows.append(dict(zip(['source_domain','state','actual_processing_and_experience','limits'],cells)))
(OUT/'variable_usage.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(json.dumps({'logs':metrics,'event_domains':sorted({e['kind'] for f in families for e in f['events']}),'branches':summary['branch_events']},ensure_ascii=False))
