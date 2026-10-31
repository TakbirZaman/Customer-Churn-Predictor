"""Opt-in disposable Docker runner; never executes model code on the host."""
import io
import shutil
import subprocess
import tarfile
import uuid
from pathlib import Path


IMAGE='analyst-python:local'


def execute(data, outputs, code, timeout=30):
    if not shutil.which('docker'):
        raise RuntimeError('Docker is not installed. Built-in analysis tools still work.')
    if len(code)>20000: raise ValueError('Python code exceeds 20,000 characters.')
    name='analyst-'+uuid.uuid4().hex
    # No writable host mounts. Output exists only inside a size-limited tmpfs.
    wrapper = "import pathlib,time,traceback\ntry:\n exec("+repr(code)+", {'__name__': '__main__'})\nexcept BaseException:\n traceback.print_exc()\nfinally:\n pathlib.Path('/tmp/analysis-done').touch()\nwhile True: time.sleep(1)\n"
    args=['docker' ,'create','--name',name,'--network','none','--read-only',
          '--memory','512m','--memory-swap','512m','--cpus','1','--pids-limit','64',
          '--cap-drop','ALL','--security-opt','no-new-privileges',
          '--user','65534:65534','--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=1',
          '--tmpfs','/tmp:rw,noexec,nosuid,size=64m,mode=1777',
          '--tmpfs','/outputs:rw,noexec,nosuid,size=16m,mode=1777',
          '--mount',f'type=bind,source={Path(data).resolve()},target=/data,readonly',
          '--workdir','/outputs','--env','MPLCONFIGDIR=/tmp/matplotlib',
          '--entrypoint','python',IMAGE,'-u','-c',wrapper]
    try:
        created=subprocess.run(args,capture_output=True,text=True,timeout=15)
        if created.returncode:
            raise RuntimeError('Cannot create runner. Start Docker and run: docker build -f Dockerfile.runner -t analyst-python:local .')
        subprocess.run(['docker','start',name],capture_output=True,check=True,timeout=10)
        import time
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            probe=subprocess.run(['docker','exec',name,'test','-f','/tmp/analysis-done'],capture_output=True,timeout=5)
            if probe.returncode==0: break
            state=subprocess.run(['docker','inspect','-f','{{.State.Running}}',name],capture_output=True,text=True,timeout=5)
            if state.stdout.strip()!='true': raise RuntimeError('Python runner exited unexpectedly (possibly memory limit).')
            time.sleep(0.2)
        else: raise RuntimeError(f'Python stopped after {timeout} seconds.')
        logs=subprocess.run(['docker','logs','--tail','100',name],capture_output=True,timeout=10)
        archive=subprocess.run(['docker','cp',name+':/outputs/.','-'],capture_output=True,timeout=10,check=True)
        artifacts=[]
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            for member in tar:
                if not member.isfile() or member.size>8*1024*1024: continue
                suffix=Path(member.name).suffix.lower()
                if suffix not in ('.png','.csv','.md','.json','.txt'): continue
                filename='python_'+uuid.uuid4().hex[:8]+suffix
                (Path(outputs)/filename).write_bytes(tar.extractfile(member).read())
                artifacts.append({'original':member.name,'artifact':filename})
        return {'stdout':logs.stdout.decode(errors='replace')[-5000:],
                'stderr':logs.stderr.decode(errors='replace')[-2000:], 'artifacts':artifacts}
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)
