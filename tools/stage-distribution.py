"""Stage only application assets and an empty library; never package account data."""
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import build
out=ROOT/'dist'
# This directory contains generated distribution files only. Never merge stale assets.
assert out.resolve()==ROOT.resolve()/'dist' and not out.is_symlink()
if out.exists():shutil.rmtree(out)
out.mkdir(exist_ok=True)
for folder in ('lib','word','tools','template'):(out/folder).mkdir(exist_ok=True)
shutil.copy2(ROOT/'release/settings-build/ClaimViewer.exe',out/'ClaimViewer.exe')
for path in (ROOT/'lib').iterdir():
    if path.is_file() and path.suffix in ('.js','.css','.mjs','.wasm','.map','.png','.svg','.woff','.woff2'):shutil.copy2(path,out/'lib'/path.name)
for name in ('addin.html','word.css','word.js','office-bridge.js','native-bridge.js','manifest-template.xml','ClaimViewerWord.dll','Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','install-web-addin.ps1','uninstall-web-addin.ps1','install-native-ribbon.ps1','install-ribbon.ps1','uninstall-ribbon.ps1','install-catalog.ps1'):
    shutil.copy2(ROOT/'word'/name,out/'word'/name)
shutil.copytree(ROOT/'word/runtimes',out/'word/runtimes',dirs_exist_ok=True)
shutil.copy2(ROOT/'word/APSA.xsl',out/'word/APSA.xsl')
shutil.copy2(ROOT/'word/install-citation-styles.ps1',out/'word/install-citation-styles.ps1')
shutil.copy2(ROOT/'tools/prepare-word-addin.py',out/'tools/prepare-word-addin.py')
shutil.copy2(ROOT/'template/template.html',out/'template/template.html')
shutil.copy2(ROOT/'README.md',out/'README.md')
shutil.copy2(ROOT/'word/README.md',out/'word/README.md')
(out/'library.json').write_text(json.dumps({'collections':[],'items':{}}),encoding='utf-8')
(out/'sources.js').write_text('window.CV_SOURCES=[];\n',encoding='utf-8')
build.HERE=out
build.TEMPLATE=ROOT/'template/template.html'
build.OUT=out/'index.html'
build.main()
assert (out/'index.html').stat().st_size<1_048_576
assert not any((out/'word'/name).exists() for name in ('service-config.json','manifest.xml','localhost-key.pem','localhost.pem','catalog-config.json'))
print('Distribution staged with empty library and no account credentials.')
