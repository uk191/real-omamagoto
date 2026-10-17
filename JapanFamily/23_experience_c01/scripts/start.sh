#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
C01_SELECTED_PORT="${C01_PORT:-8783}"
mkdir -p "$ROOT/runtime"
if python - "$C01_SELECTED_PORT" <<'PY'
import sys,json,urllib.request
try:
 with urllib.request.urlopen('http://127.0.0.1:'+sys.argv[1]+'/api/health',timeout=1) as r:data=json.load(r)
 assert data.get('ok') and data.get('version')=='C-0.1-P0.1'
except Exception:raise SystemExit(1)
PY
then
  echo "C-0.1 ready on local port $C01_SELECTED_PORT"
  exit 0
fi
nohup python "$ROOT/server.py" --port "$C01_SELECTED_PORT" > "$ROOT/runtime/server.log" 2>&1 &
printf '%s\n' "$!" > "$ROOT/runtime/server.pid"
python - "$C01_SELECTED_PORT" <<'PY'
import sys,json,time,urllib.request
for _ in range(100):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+sys.argv[1]+'/api/health',timeout=.5) as r:data=json.load(r)
  if data.get('ok') and data.get('version')=='C-0.1-P0.1':print('C-0.1 local server verified');break
 except OSError:pass
 time.sleep(.1)
else:raise SystemExit('Startup failed. Read JapanFamily/23_experience_c01/runtime/server.log')
PY
