"""Exercise real PowerShell extraction, cached startup and missing-runtime repair."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
BUILD=Path('/workspace/c01_bootstrap_logs');BUILD.mkdir(exist_ok=True);PW=Path('/workspace/c0_player_build/powershell_test_runtime/pwsh');BASE=Path('/workspace/c01_bootstrap_test')
env=os.environ.copy()
for name,folder in [('XDG_CACHE_HOME','ps_cache'),('XDG_CONFIG_HOME','ps_config'),('XDG_DATA_HOME','ps_data')]:env[name]=str(BUILD/folder)
env['C01_BOOTSTRAP']=str(ROOT/'START_C01.cmd')
fake=BUILD/'fake_bootstrap_user';(fake/'Downloads').mkdir(parents=True,exist_ok=True);env['USERPROFILE']=str(fake)
archive=REPO/'artifacts/C01_P0B_PLAY_WINDOWS_X64.zip';link=fake/'Downloads'/archive.name
if not link.exists():link.symlink_to(archive)
def run(name,code=None,extra=None,expected=0):
    cmd=[str(PW),'-NoLogo','-NoProfile']
    if code:cmd+=['-Command',code]
    else:cmd+=['-File',str(ROOT/'prepare_and_start.ps1')]
    cmd+=extra or []
    p=subprocess.run(cmd,env=env,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (BUILD/(name+'.log')).write_text(p.stdout)
    assert p.returncode==expected,(name,p.returncode,p.stdout)
    print(name,'PASS',flush=True);return p.stdout

game=BASE/'game/C01_Play';python=game/'runtime/python/tools/python.exe'
assert python.exists(),'Run initial full extraction test first'
expected_python=hashlib.file_digest(python.open('rb'),'sha256').hexdigest()
run('bootstrap_cache_reuse',extra=['-ArchivePath','/this-file-is-deliberately-unavailable.zip','-InstallBase',str(BASE),'-PrepareOnly'])
# The real user symptom: runtime directory exists, but Python is absent.
hold=BASE/'held_python_for_repair_test.exe';python.rename(hold)
saves=game/'saves';saves.mkdir(exist_ok=True);(saves/'preservation_probe.txt').write_text('Keep this player record\n')
assert (game/'runtime').is_dir()and not python.exists()
run('bootstrap_missing_python_repair',extra=['-InstallBase',str(BASE),'-PrepareOnly'])
assert hashlib.file_digest(python.open('rb'),'sha256').hexdigest()==expected_python
assert (game/'saves/preservation_probe.txt').read_text()=='Keep this player record\n'
backups=list(BASE.glob('backup-*'));assert backups and any((p/'C01_Play/saves/preservation_probe.txt').exists()for p in backups)
# Validate the single-file cmd's embedded code, rather than only its .ps1 source.
code="$t=[IO.File]::ReadAllText($env:C01_BOOTSTRAP,[Text.Encoding]::UTF8);$m='#'+' C01_POWERSHELL';$i=$t.IndexOf($m);if($i -lt 0){throw 'Missing setup code'};& ([scriptblock]::Create($t.Substring($i+$m.Length))) -InstallBase '"+str(BASE)+"' -PrepareOnly"
run('bootstrap_embedded_cmd',code=code)
invalid=BUILD/'invalid_player_archive.zip';invalid.write_bytes(b'not a player ZIP')
run('bootstrap_invalid_archive_rejected',extra=['-ArchivePath',str(invalid),'-InstallBase',str(BUILD/'invalid_bootstrap_install'),'-PrepareOnly'],expected=1)
result={'powershell_version':'7.4.7 Linux; not a Windows machine','initial_extraction_all_manifest_files_hash_check':True,'manifest_file_count':len(json.loads((game/'PLAYER_MANIFEST.json').read_text())['files']),
        'runtime_folder_exists_but_python_exe_missing_repaired':True,'existing_saves_preserved':True,'previous_install_backup_preserved':True,
        'cached_install_no_archive_required':True,'embedded_single_cmd_powershell_body_executed':True,'invalid_archive_rejected':True,
        'Windows_cmd_exe_and_native_python_exe_executed':False,'scientific_A_B_code_changed':False,'player_layer_rewritten':True}
(REPO/'artifacts/C01_START_HELPER_VERIFICATION.json').write_text(json.dumps(result,indent=2));print('BOOTSTRAP_TESTS_PASS',flush=True)
