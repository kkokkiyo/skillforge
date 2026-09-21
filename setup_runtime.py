import io, pathlib, tarfile, urllib.request, subprocess
root=pathlib.Path(__file__).resolve().parent
with urllib.request.urlopen('https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz', timeout=60) as response:
    raw=response.read()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
    member=next(m for m in archive.getmembers() if m.name.endswith('/uv') and m.isfile())
    path=root/'.venv'/'uv'
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(archive.extractfile(member).read())
    path.chmod(0o700)
subprocess.run([str(path),'venv',str(root/'.runtime')],check=True)
subprocess.run([str(path),'pip','install','--python',str(root/'.runtime/bin/python'),'-r',str(root/'requirements-lock.txt')],check=True)

subprocess.run([str(path),'pip','install','--python',str(root/'.runtime/bin/python'),'-e',str(root)],check=True)
