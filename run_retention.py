"""Start the local API and Analyst Studio; stop both on exit."""
import argparse
import tempfile
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-startup", action="store_true", help="Check both services and a sample report, then exit")
    args = parser.parse_args()
    children = []
    try:
        # Refuse to silently attach to an unrelated service on this port.
        import socket
        for port in (8000, 8501):
            with socket.socket() as sock:
                try: sock.bind(('127.0.0.1', port))
                except OSError:
                    print(f'Port {port} is already in use. Stop the old service before starting this suite.')
                    return 1
        api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8000'], cwd=ROOT/'backend')
        children.append(api)
        for _ in range(120):
            if api.poll() is not None: raise RuntimeError('Churn API failed to start. See the error above.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1) as response:
                    if response.status == 200: break
            except OSError: time.sleep(.5)
        else: raise RuntimeError('Churn API startup timed out.')
        env = dict(os.environ, CHURN_API_URL='http://127.0.0.1:8000')
        ui = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.address', '127.0.0.1', '--server.port', '8501'], cwd=ROOT/'analyst-studio', env=env)
        children.append(ui)
        for _ in range(120):
            if ui.poll() is not None or api.poll() is not None:
                raise RuntimeError('A service failed during startup. See the error above.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=1) as response:
                    if response.status == 200: break
            except OSError: time.sleep(.5)
        else: raise RuntimeError('Analyst Studio startup timed out.')
        if args.check_startup:
            with tempfile.TemporaryDirectory(prefix='retention-check-') as directory:
                subprocess.run([sys.executable, str(ROOT/'analyst-studio'/'cli.py'), '--retention',
                                '--file', str(ROOT/'sample_customers.csv'), '--home', directory],
                               check=True, timeout=120, env=env)
                reports = list(Path(directory).glob('sessions/*/outputs/*_report.md'))
                if len(reports) != 1:
                    raise RuntimeError('Sample report was not created.')
            print('Startup check passed: API, Studio and sample retention report.', flush=True)
            return 0
        print('\nOpen http://localhost:8501 and select Customer retention. Press Ctrl+C to stop.\n', flush=True)
        while ui.poll() is None and api.poll() is None: time.sleep(.5)
        return ui.returncode or api.returncode or 0
    except (KeyboardInterrupt, RuntimeError, subprocess.SubprocessError) as exc:
        print(str(exc) or 'Stopping retention suite.')
        return 0 if isinstance(exc, KeyboardInterrupt) else 1
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=10)
                except subprocess.TimeoutExpired: child.kill(); child.wait()

if __name__ == '__main__': sys.exit(main())
