"""Start the local API and Analyst Studio; stop both on exit."""
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent

def main():
    children = []
    try:
        # Refuse to silently attach to an unrelated service on this port.
        import socket
        with socket.socket() as sock:
            try: sock.bind(('127.0.0.1', 8000))
            except OSError:
                print('Port 8000 is already in use. Stop the old churn API before starting this suite.')
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
        print('\nOpen http://localhost:8501 and select Customer retention. Press Ctrl+C to stop.\n', flush=True)
        while ui.poll() is None and api.poll() is None: time.sleep(.5)
        return ui.returncode or api.returncode or 0
    except (KeyboardInterrupt, RuntimeError) as exc:
        print(str(exc) or 'Stopping retention suite.')
        return 1 if isinstance(exc, RuntimeError) else 0
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=10)
                except subprocess.TimeoutExpired: child.kill(); child.wait()

if __name__ == '__main__': sys.exit(main())
