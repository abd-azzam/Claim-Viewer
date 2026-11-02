"""Fixed desktop settings actions. No arbitrary paths or commands from the page."""
import json
import pathlib
import runpy
import subprocess
import threading
import urllib.request
import zipfile
import winreg
import os
import webview
# Bundle the dependencies used by the shipped Word preparation script.
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

WORD_ID = 'b1a3d266-67e6-4232-a98b-7935cda2930c'
CATALOG_ID = '{f7947c71-8a31-47de-8f55-0a57ea702d27}'
INSTALL_LOCK = threading.Lock()

def word_status(root):
    registered = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Office\16.0\WEF\Developer') as key:
            manifest = pathlib.Path(winreg.QueryValueEx(key, WORD_ID)[0])
            registered = manifest.resolve() == (root / 'word/manifest.xml').resolve() and manifest.exists()
    except FileNotFoundError:
        pass
    running = False
    try:
        with urllib.request.urlopen('https://localhost:38491/health', timeout=2) as response:
            running = json.load(response).get('service') == 'Claim Viewer Word'
    except Exception:
        pass
    catalog = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Office\16.0\WEF\TrustedCatalogs' + '\\' + CATALOG_ID) as key:
            url = winreg.QueryValueEx(key, 'Url')[0]
            catalog = url == r'\\localhost\ClaimViewerWord' and pathlib.Path(url, 'ClaimViewer.xml').is_file()
    except FileNotFoundError:
        pass
    ribbon = False
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Office\Word\Addins\ClaimViewer.Citations', 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            ribbon = winreg.QueryValueEx(key, 'LoadBehavior')[0] == 3
    except FileNotFoundError:
        pass
    return {'ok': True, 'registered': ribbon or registered and catalog, 'running': running, 'catalog': catalog, 'ribbon': ribbon}

def command(directory, action, executable, window):
    root = pathlib.Path(directory)
    if action == 'info':
        return {'ok': True, 'folder': str(root), 'sources': len(json.loads((root / 'library.json').read_text(encoding='utf-8'))['items'])}
    if action == 'word-status':
        return word_status(root)
    if action == 'word-open':
        documents = sorted((root / 'word').glob('Claim Viewer Word setup-*.docx'), key=lambda p: p.stat().st_mtime, reverse=True)
        if not documents:
            raise ValueError('Install the Word add-in first to create its setup document.')
        document = documents[0]
        os.startfile(str(document))
        return {'ok': True, 'message': 'Opened the disposable setup document in Word. Follow any activation prompt there.'}
    if action in ('word-install', 'word-uninstall'):
        if not INSTALL_LOCK.acquire(blocking=False):
            raise ValueError('Word setup is already running.')
        try:
            if action == 'word-install':
                runpy.run_path(str(root / 'tools/prepare-word-addin.py'), run_name='__main__')
            script = 'install-web-addin.ps1' if action == 'word-install' else 'uninstall-web-addin.ps1'
            args = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(root / 'word' / script)]
            if action == 'word-install':
                args += ['-AppExe', executable if pathlib.Path(executable).name.lower() == 'claimviewer.exe' else str(root / 'ClaimViewer.exe')]
            # PowerShell 7's module path can break Windows PowerShell 5.1 cmdlets.
            environment = {k: v for k, v in os.environ.items() if k.upper() != 'PSMODULEPATH'}
            result = subprocess.run(args, capture_output=True, text=True, timeout=180,
                                    creationflags=subprocess.CREATE_NO_WINDOW, env=environment)
            if result.returncode:
                raise ValueError((result.stderr or result.stdout).strip()[-300:])
            return dict(word_status(root), message=result.stdout.strip()[-300:])
        finally:
            INSTALL_LOCK.release()
    if action == 'open-data':
        os.startfile(str(root))
        return {'ok': True}
    if action == 'backup':
        paths = window.create_file_dialog(webview.SAVE_DIALOG, save_filename='ClaimViewer-backup.zip', file_types=('ZIP archive (*.zip)',))
        if not paths:
            return {'ok': True, 'cancelled': True}
        destination = pathlib.Path(paths[0] if isinstance(paths, (list, tuple)) else paths)
        files = [root / name for name in ('library.json', 'state.json', 'last-pages.json', 'ocr.json')]
        files += list((root / 'data').rglob('*.json')) + list((root / 'pdf').glob('*.pdf'))
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                if path.is_file():
                    archive.write(path, path.relative_to(root))
        return {'ok': True, 'message': 'Backup saved. Includes library, PDFs, claims, notes and reading positions. API keys are excluded.'}
    if action == 'export-ris':
        paths = window.create_file_dialog(webview.SAVE_DIALOG, save_filename='ClaimViewer-library.ris', file_types=('RIS references (*.ris)',))
        if not paths:
            return {'ok': True, 'cancelled': True}
        lines = []
        for ident, item in json.loads((root / 'library.json').read_text(encoding='utf-8'))['items'].items():
            meta = item.get('meta') or {}
            kind = {'book': 'BOOK', 'chapter': 'CHAP', 'report': 'RPRT', 'thesis': 'THES'}.get(meta.get('type'), 'JOUR')
            lines += ['TY  - ' + kind, 'ID  - ' + ident]
            for field, value in [('TI', meta.get('title') or item.get('title') or ident), ('PY', meta.get('year')), ('DO', meta.get('doi')), ('JO', meta.get('journal'))]:
                if value:
                    lines.append(field + '  - ' + str(value).replace('\n', ' '))
            for author in str(meta.get('author') or '').split(';'):
                if author.strip():
                    lines.append('AU  - ' + author.strip().replace('\n', ' '))
            lines += ['ER  - ', '']
        pathlib.Path(paths[0] if isinstance(paths, (list, tuple)) else paths).write_text('\n'.join(lines), encoding='utf-8')
        return {'ok': True, 'message': 'References exported. Import the RIS file in Zotero, Mendeley or EndNote.'}
    raise ValueError('Unknown settings action.')
