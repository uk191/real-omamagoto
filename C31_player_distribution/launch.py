"""Local C-3.1 player launcher; inherited scientific A/B models are unchanged."""
import argparse
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

BASE = Path(__file__).resolve().parent
VERSION = 'C-3.1-four-decisions-research'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def health(port):
    try:
        with OPENER.open(f'http://127.0.0.1:{port}/api/health', timeout=.5) as response:
            data = json.load(response)
        return data.get('ok') and data.get('version') == VERSION
    except (OSError, ValueError):
        return False


def free_port(preferred=None):
    for port in ([preferred] if preferred is not None else [*range(18780,18801),0]):
        try:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',port))
                available = sock.getsockname()[1]
            return available
        except OSError:
            continue
    raise RuntimeError('利用できるポートがありません。別のプレイ画面を終了してから起動してください。')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true',help='For automated startup inspection only')
    parser.add_argument('--port',type=int,help='Optional local port')
    args = parser.parse_args()
    app = BASE/'app/JapanFamily/27_experience_c31'
    db = BASE/'app/JapanFamily/22_experience_c0/data/runtime_region.sqlite'
    if not (app/'server.py').is_file() or not db.is_file():
        raise RuntimeError('ZIPを「すべて展開」してからPLAY.cmdを開いてください。appフォルダが必要です。')
    if not sys.flags.utf8_mode:
        raise RuntimeError('PLAY.cmdから起動してください。日本語データのためUTF-8モードが必要です。')
    try:
        import numpy
        import scipy
        from scipy.special import ndtr
        assert numpy.__version__=='2.3.5' and scipy.__version__=='1.17.0'
        assert float(ndtr(0))==.5
    except (ImportError, AssertionError) as error:
        raise RuntimeError('同梱ライブラリを読み込めません。ZIPを別の空フォルダへ展開し直してください。') from error
    saves = BASE/'saves';saves.mkdir(exist_ok=True)
    logs = BASE/'logs';logs.mkdir(exist_ok=True)
    port = free_port(args.port)
    url = f'http://127.0.0.1:{port}/'
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0
    path = logs/'server.log'
    command=[sys.executable,'-I','-X','utf8',str(app/'server.py'),'--port',str(port),
             '--save-dir',str(saves),'--runtime-db',str(db)]
    with path.open('a',encoding='utf-8') as log:
        log.write('\n=== C-3.1 player startup '+datetime.datetime.now().isoformat()+' ===\n');log.flush()
        process = subprocess.Popen(command,cwd=BASE,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
        try:
            for attempt in range(200):
                if process.poll() is not None:
                    raise RuntimeError('起動できませんでした。logs/server.logを確認してください。')
                if health(port):
                    break
                time.sleep(.15)
            else:
                raise RuntimeError('起動に時間がかかっています。logs/server.logを確認してください。')
            print('\n「まいにちの、あいだ。」C-3.1を起動しました。',flush=True)
            print('ブラウザの画面から、家族を選んでプレイしてください。',flush=True)
            print('画面が自動で開かない場合： '+url,flush=True)
            print('保存先： '+str(saves),flush=True)
            print('このウィンドウはプレイ中そのままにしてください。',flush=True)
            print('終了する前に、ゲーム画面の「保存」を押してください。',flush=True)
            print('終了は Ctrl+C。この画面を閉じてもサーバーが終了します。\n',flush=True)
            if not args.no_browser:
                try:webbrowser.open(url,new=2)
                except OSError:print('上のアドレスをブラウザに入力してください。',flush=True)
            process.wait()
        except KeyboardInterrupt:
            print('\nC-3.1を終了します。保存した記録はsavesフォルダに残ります。',flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        print('\n起動エラー： '+str(error),file=sys.stderr,flush=True)
        sys.exit(1)
