"""Reproducible offline package builder. Windows + Python stdlib + .NET Framework."""
from pathlib import Path
import ast
import hashlib
import json
import os
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'

def package_files():
    files = sorted(ROOT.glob('*.py'))
    files += [ROOT/name for name in ('README.md','LICENSE','NOTICE.md','COMMANDS.md','FEATURES.md','requirements.txt','requirements-xtts.txt','JARVIS.ico') if (ROOT/name).is_file()]
    files += [ROOT/'installer'/'prepare_models.py']
    files += sorted((ROOT/'assets').glob('*.svg'))
    return files

def version():
    module = ast.parse((ROOT/'product.py').read_text(encoding='utf-8-sig'))
    for node in module.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('Missing VERSION')

def build():
    DIST.mkdir(exist_ok=True)
    csc=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET'/'Framework64'/'v4.0.30319'/'csc.exe'
    icon=ROOT/'JARVIS.ico'
    common=[str(csc),'/nologo','/target:winexe','/optimize+','/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll']
    if icon.exists():common.append('/win32icon:'+str(icon))
    subprocess.run(common+['/out:'+str(DIST/'JARVIS.exe'),str(ROOT/'installer'/'Launcher.cs')],check=True)
    payload=DIST/'jarvis-app.zip'
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as zip_:
        for file in package_files():zip_.writestr(file.relative_to(ROOT).as_posix(),file.read_bytes())
        zip_.writestr('README.txt',(ROOT/'README.md').read_bytes())
        zip_.write(DIST/'JARVIS.exe','JARVIS.exe')
    subprocess.run(common+['/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll','/resource:'+str(payload)+',payload.zip','/out:'+str(DIST/'InstallUpdates.exe'),str(ROOT/'installer'/'InstallUpdates.cs'),str(ROOT/'installer'/'Components.cs')],check=True)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (payload,DIST/'InstallUpdates.exe',DIST/'JARVIS.exe')}
    (DIST/'SHA256SUMS.txt').write_text(''.join(sha+'  '+name+'\n' for name,sha in hashes.items()),encoding='utf-8')
    (DIST/'release.json').write_text(json.dumps({'version':version(),'sha256':hashes},indent=2),encoding='utf-8')
    print('Built JARVIS '+version()+' — '+str((DIST/'InstallUpdates.exe').stat().st_size)+' byte installer')

if __name__=='__main__':build()

