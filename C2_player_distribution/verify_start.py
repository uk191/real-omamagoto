"""Execute the shipped PowerShell body: extract, cache, repair, preserve, reject.
Linux PowerShell execution is explicitly not a Windows native smoke test.
"""
import hashlib,json,os,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
CHECK=Path('/workspace/c2_windows_checks');PW=Path('/workspace/c1_windows_checks/powershell/pwsh');BASE=CHECK/'safe_install_verified';LOGS=CHECK/'safe_logs';LOGS.mkdir(parents=True,exist_ok=True)
ARCHIVE=REPO/'artifacts/C2_PLAY_WINDOWS_X64.zip';PS=ROOT/'prepare_safe_start.ps1'
env=os.environ.copy();env['C2_SAFE_START']=str(ROOT/'START_C2.cmd');env['USERPROFILE']=str(CHECK/'fake_user');env['XDG_CACHE_HOME']=str(CHECK/'cache');env['XDG_CONFIG_HOME']=str(CHECK/'config');env['XDG_DATA_HOME']=str(CHECK/'data')
download=Path(env['USERPROFILE'])/'Downloads';download.mkdir(parents=True,exist_ok=True)
link=download/ARCHIVE.name
if not link.exists():link.symlink_to(ARCHIVE)
results={}
def run(name,*args,expected=0,code=None):
 cmd=[str(PW),'-NoLogo','-NoProfile']
 if code:cmd+=['-Command',code]
 else:cmd+=['-File',str(PS)]
 r=subprocess.run(cmd+list(args),env=env,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
 (LOGS/(name+'.txt')).write_text(r.stdout,encoding='utf8')
 assert r.returncode==expected,(name,r.returncode,r.stdout[-4000:]);results[name]=True;print(name,'PASS',flush=True);return r.stdout
# Parse both the .ps1 and the actual embedded single-file payload.
run('parser',code="$tokens=$null;$errors=$null;[Management.Automation.Language.Parser]::ParseFile('"+str(PS)+"',[ref]$tokens,[ref]$errors)|Out-Null;if($errors.Count){throw ($errors|Out-String)}")
run('initial_verified_extraction','-ArchivePath',str(ARCHIVE),'-InstallBase',str(BASE),'-PrepareOnly')
game=BASE/'game/C2_Play';manifest=json.loads((game/'PLAYER_MANIFEST.json').read_text())
for name,entry in manifest['files'].items():
 with (game/name).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==entry['sha256']
results['all_extracted_file_hashes']=len(manifest['files'])
run('valid_cached_install_needs_no_archive','-ArchivePath','/deliberately/unavailable.zip','-InstallBase',str(BASE),'-PrepareOnly')
saves=game/'saves';saves.mkdir(exist_ok=True);(saves/'preserve_test.json').write_text('{"synthetic_test":true}')
# Existing folders can look right while native files are absent or changed.
python=game/'runtime/python/tools/python.exe';expected_python=hashlib.sha256(python.read_bytes()).hexdigest();python.unlink()
assert (game/'runtime').is_dir()
run('missing_python_repaired_without_folder_choice','-InstallBase',str(BASE),'-PrepareOnly')
assert hashlib.sha256(python.read_bytes()).hexdigest()==expected_python
assert (saves/'preserve_test.json').read_text()=='{"synthetic_test":true}'
assert any((b/'C2_Play/saves/preserve_test.json').is_file() for b in BASE.glob('backup-*'))
results['saves_and_previous_install_preserved']=True
changed=game/'app/JapanFamily/24_experience_c1/web/app.js';changed.write_bytes(changed.read_bytes()+b'\n// corruption fixture\n')
run('changed_game_file_detected_and_repaired','-InstallBase',str(BASE),'-PrepareOnly')
assert hashlib.sha256(changed.read_bytes()).hexdigest()==manifest['files']['app/JapanFamily/24_experience_c1/web/app.js']['sha256']
invalid=CHECK/'invalid.zip';invalid.write_bytes(b'not a release')
run('invalid_archive_rejected_error_file_written','-ArchivePath',str(invalid),'-InstallBase',str(CHECK/'invalid_install'),'-PrepareOnly',expected=1)
assert 'SHA256' in (CHECK/'invalid_install/startup-error.txt').read_text(encoding='utf-8-sig')
run('actual_embedded_cmd_body',code="$raw=[IO.File]::ReadAllText($env:C2_SAFE_START,[Text.Encoding]::UTF8);$marker='#'+' C2_SAFE_POWERSHELL';$i=$raw.IndexOf($marker);& ([ScriptBlock]::Create($raw.Substring($i+$marker.Length))) -InstallBase '"+str(BASE)+"' -PrepareOnly")
# Exercise child-process capture, both success and a long failing stderr stream.
fixture=CHECK/'process fixture.py';fixture.write_text('import sys\nprint("output marker")\nprint("error marker"+"x"*150000,file=sys.stderr)\nsys.exit(int(sys.argv[1]))\n')
for n in [0,42]:
 prefix=LOGS/f'child{n}';code=f". '{PS}' -DefineOnly; try {{ Run-Captured '{sys.executable}' '\"{fixture}\" {n}' '{CHECK}' '{prefix}' -EchoOutput; if ({n} -ne 0) {{throw 'failure was ignored'}} }} catch {{if ({n} -eq 0) {{throw}}; if ($_.Exception.Message -notlike '*0x0000002A*') {{throw}}}}"
 run('child_process_capture_'+str(n),code=code+'; exit 0')
 assert 'error marker' in prefix.with_suffix('.stderr.txt').read_text()
results.update(platform='PowerShell7.4.7 on Linux; Windows cmd.exe and native .exe not executed',windows_native_execution_tested=False,no_simulation_code_changed=True,no_execution_policy_changes=True)
(REPO/'artifacts/C2_SAFE_START_VERIFICATION.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print('SAFE_START_TESTS_PASS')
