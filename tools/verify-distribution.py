"""Release gate: all runtime assets, empty research data, no account files."""
from pathlib import Path
from html.parser import HTMLParser
import json
import re

root=Path(__file__).resolve().parents[1]
stage=root/'dist'
app_version=re.search(r'^VERSION = "([\d.]+)"$', (root/'update_service.py').read_text(encoding='utf-8'), re.M)
setup_version=re.search(r'^#define AppVersion "([\d.]+)"$', (root/'ClaimViewer.iss').read_text(encoding='utf-8'), re.M)
assert app_version and setup_version and app_version[1]==setup_version[1], 'About and installer versions must match'
required=['ClaimViewer.exe','README.md','index.html','library.json','sources.js','template/template.html',
          'lib/pdf.min.js','lib/pdf.worker.min.js','lib/settings.js','lib/provider-settings.js','lib/source-context.js',
          'lib/tutorial.js','lib/settings.css','lib/reading-guide.js','lib/reading-guide.css','lib/workspace.js','lib/workspace.css','lib/idea-layout.js',
          'word/README.md','word/ClaimViewerWord.dll','word/APSA.xsl','word/native-bridge.js',
          'word/word.js','word/word.css','word/addin.html','word/install-web-addin.ps1',
          'word/uninstall-web-addin.ps1','word/install-ribbon.ps1','word/uninstall-ribbon.ps1',
          'word/install-native-ribbon.ps1','word/install-citation-styles.ps1',
          'word/Microsoft.Web.WebView2.Core.dll','word/Microsoft.Web.WebView2.WinForms.dll',
          'word/runtimes/win-x64/native/WebView2Loader.dll','word/runtimes/win-x86/native/WebView2Loader.dll',
          'tools/prepare-word-addin.py','word/manifest-template.xml']
for name in required:
    assert (stage/name).is_file(),f'Missing runtime asset: {name}'
library=json.loads((stage/'library.json').read_text(encoding='utf-8'))
assert library=={'collections':[],'items':{}},'Release contains library data'
page=(stage/'index.html').read_text(encoding='utf-8')
class StartupMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts=set()
        self.ids=set()

    def handle_starttag(self, tag, attrs):
        values=dict(attrs)
        if tag=='script' and values.get('src'):
            self.scripts.add(values['src'].split('?',1)[0])
        if values.get('id'):
            self.ids.add(values['id'])

markup=StartupMarkup()
markup.feed(page)
assert {'lib/workspace.js','lib/reading-guide.js'} <= markup.scripts, 'Missing startup scripts'
assert {'col','gout','pdfsel','guide-toggle'} <= markup.ids, 'Missing startup controls'
match=re.search(r'\bconst\s+DATA\s*=\s*',page)
data,_=json.JSONDecoder().raw_decode(page[match.end():])
assert not data['sources'] and not data['library']['items'],'Release contains research data'
for path in stage.rglob('*'):
    if not path.is_file():continue
    rel=path.relative_to(stage)
    assert rel.parts[0] in ('lib','word','tools','template') or str(rel) in ('ClaimViewer.exe','README.md','library.json','index.html','sources.js'),f'Unexpected root asset: {rel}'
    assert path.name not in {'ai.json','providers.json','state.json','state.js','ocr.json','last-pages.json','service-config.json','manifest.xml','catalog-config.json','data-root.txt'},f'Account data: {rel}'
    assert path.suffix.lower() not in ('.pdf','.docx','.pem','.cer','.bak','.bin'),f'Private/runtime artifact: {rel}'
print('Distribution gate PASS: required assets present, empty library, no research/account files.')
