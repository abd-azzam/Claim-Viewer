"""Word desktop integration using editable native CITATION/BIBLIOGRAPHY fields."""
import hashlib
import json
import pathlib
import re
import functools
import os
import xml.etree.ElementTree as ET
import urllib.parse
from xml.sax.saxutils import escape

STYLE_DIRS = [pathlib.Path(base) / suffix for base in
              (r'C:\Program Files\Microsoft Office', r'C:\Program Files (x86)\Microsoft Office')
              for suffix in ('root/Office16/Bibliography/Style', 'Office16/Bibliography/Style')]
STYLE_DIRS.append(pathlib.Path(os.environ.get('APPDATA', pathlib.Path.home() / 'AppData/Roaming')) / 'Microsoft/Bibliography/Style')

@functools.lru_cache(maxsize=1)
def style_paths():
    found = {}
    for folder in STYLE_DIRS:
        if not folder.exists():
            continue
        for path in folder.glob('*.xsl'):
            tree = ET.parse(path)
            keys = tree.findall('.//{http://www.w3.org/1999/XSL/Transform}when')
            key = next((''.join(e.itertext()).strip() for e in keys if e.get('test') == 'b:OfficeStyleKey'), None)
            if not key:
                local = next((e for e in keys if e.get('test') == 'b:StyleNameLocalized'), None)
                if local is not None:
                    key = next((''.join(e.itertext()).strip() for e in local.iter() if e.get('test') in ("b:StyleNameLocalized/b:Lcid='1033'", 'b:StyleNameLocalized/b:Lcid="1033"')), None)
            found[key or path.stem] = path
    return found

def styles():
    return sorted(style_paths(), key=str.lower)

def source_xml(ident, item):
    meta = item.get('meta') or {}
    title = meta.get('title') or item.get('title') or ''
    if not title or not meta.get('author') or not meta.get('year'):
        raise ValueError('Complete this source’s title, author and year in Library before citing it.')
    tag = 'CV' + hashlib.sha256(ident.encode()).hexdigest()[:20]
    kind = {'book': 'Book', 'chapter': 'BookSection', 'paper': 'JournalArticle', 'article': 'JournalArticle', 'journal': 'JournalArticle', 'report': 'Report', 'thesis': 'Report'}.get(meta.get('type'), 'Misc')
    people = []
    for author in meta['author'].split(';'):
        author = author.strip()
        if not author:
            continue
        if ',' in author:
            last, first = author.split(',', 1)
        elif ' ' in author:
            first, last = author.rsplit(' ', 1)
        else:
            first, last = '', author
        people.append('<b:Person><b:Last>'+escape(last.strip())+'</b:Last><b:First>'+escape(first.strip())+'</b:First></b:Person>')
    fields = dict(Tag=tag, SourceType=kind, Title=title, Year=meta['year'])
    for field, key in [('JournalName', 'journal'), ('Publisher', 'publisher'), ('City', 'city'), ('Volume', 'volume'), ('Issue', 'issue'), ('Pages', 'pages'), ('URL', 'url'), ('StandardNumber', 'doi')]:
        if meta.get(key):
            fields[field] = meta[key]
    xml = '<b:Source xmlns:b="http://schemas.microsoft.com/office/word/2004/10/bibliography">'
    xml += ''.join('<b:'+k+'>'+escape(str(v))+'</b:'+k+'>' for k, v in fields.items())
    xml += '<b:Author><b:Author><b:NameList>'+''.join(people)+'</b:NameList></b:Author></b:Author></b:Source>'
    return tag, xml

def _document_key(value):
    if value.lower().startswith(('file:', 'https:', 'http:')):
        value = urllib.parse.unquote(value)
    if value.lower().startswith('file:'):
        value = value[5:].lstrip('/')
    return value.replace('/', '\\').lower()

def _word_application(host, client, com):
    try:
        app = client.GetActiveObject('Word.Application')
        if not host or any(_document_key(app.Documents.Item(i).FullName) == _document_key(host)
                           for i in range(1, app.Documents.Count + 1)):
            return app
    except com.com_error:
        pass
    if host:
        table = com.GetRunningObjectTable()
        context = com.CreateBindCtx(0)
        for moniker in table.EnumRunning():
            try:
                if _document_key(moniker.GetDisplayName(context, None)) != _document_key(host):
                    continue
                doc = client.Dispatch(table.GetObject(moniker).QueryInterface(com.IID_IDispatch))
                if _document_key(doc.FullName) == _document_key(host):
                    return doc.Application
            except com.com_error:
                continue
    raise ValueError('This document was not found among open Word documents. Activate it and refresh the connection.')

def command(root, action, payload, application=None):
    import pythoncom
    import win32com.client
    owns_com = application is None
    if owns_com:
        pythoncom.CoInitialize()
    try:
        app = application if application is not None else _word_application(payload.get('host_document', ''), win32com.client, pythoncom)
        if not app.Documents.Count:
            raise ValueError('Open a Word document first.')
        doc = app.ActiveDocument
        if payload.get('host_document'):
            if _document_key(payload['host_document']) != _document_key(doc.FullName):
                raise ValueError('This task pane is attached to a different Word document. Activate this document and refresh.')
        if payload.get('document') and payload['document'] != doc.FullName:
            raise ValueError('The active Word document changed. Refresh the connection before inserting.')
        if action == 'state':
            return {'ok': True, 'document': doc.FullName, 'name': doc.Name,
                    'selection': app.Selection.Text[:80000], 'styles': styles(),
                    'style': app.Bibliography.BibliographyStyle}
        if doc.ReadOnly:
            raise ValueError('This Word document is read-only.')
        if action == 'style':
            style = payload.get('style')
            if style not in styles():
                raise ValueError('Choose a bibliography style installed in Word.')
            app.Options.BibliographyStyle = style
        elif action == 'citation':
            form = payload.get('form', 'parenthetical')
            if form not in ('parenthetical', 'narrative'):
                raise ValueError('Choose parenthetical or narrative citation.')
            pages = payload.get('pages', '').strip()
            if not re.fullmatch(r'[0-9ivxlcdmIVXLCDM,\-– ]{0,80}', pages):
                raise ValueError('Use page numbers or ranges, such as 12 or 12–14.')
            library = json.loads(pathlib.Path(root, 'library.json').read_text(encoding='utf-8'))
            ident = payload['source']
            tag, xml = source_xml(ident, library['items'][ident])
            existing = {doc.Bibliography.Sources.Item(i).Tag for i in range(1, doc.Bibliography.Sources.Count+1)}
            if tag not in existing:
                doc.Bibliography.Sources.Add(xml)
            # Collapse rather than replace selected writing.
            target = app.Selection.Range
            target.Collapse(0)
            if form == 'narrative':
                authors = [a.strip() for a in library['items'][ident]['meta']['author'].split(';') if a.strip()]
                names = [a.split(',', 1)[0].strip() if ',' in a else a.rsplit(' ', 1)[-1] for a in authors]
                author = names[0] if len(names) == 1 else ' and '.join(names) if len(names) == 2 else names[0]+' et al.'
                if 'APSA' in app.Bibliography.BibliographyStyle.upper() and len(names) == 3:
                    author = ', '.join(names[:-1])+', and '+names[-1]
                target.InsertAfter(author+' ')
                target.Collapse(0)
            field = doc.Fields.Add(target, -1, 'CITATION '+tag+(' \\n \\t' if form == 'narrative' else '')+(' \\p "'+pages+'"' if pages else ''), True)
            field.Update()
            # Move beyond the field's end marker; a collapsed Result range is still inside it.
            end = min(field.Result.End + 2, doc.Content.End - 1)
            doc.Range(end, end).InsertAfter(' ')
            app.Selection.SetRange(end + 1, end + 1)
        elif action == 'bibliography':
            target = app.Selection.Range
            target.Collapse(0)
            if not any(doc.Fields.Item(i).Code.Text.strip().upper().startswith('BIBLIOGRAPHY') for i in range(1, doc.Fields.Count+1)):
                doc.Fields.Add(target, -1, 'BIBLIOGRAPHY', True)
        elif action != 'refresh':
            raise ValueError('Unknown Word action.')
        # Update only citation-related fields, not dates, tables of contents or other fields.
        for i in range(1, doc.Fields.Count+1):
            f = doc.Fields.Item(i)
            code = f.Code.Text
            # Repair narrative fields created before title suppression was added.
            if (re.match(r'\s*CITATION\s+CV[0-9a-f]{20}\b', code, re.I)
                    and re.search(r'\\n(?=\s|$)', code)
                    and not re.search(r'\\t(?=\s|$)', code)):
                # Word prevents direct edits to native CITATION field codes.
                target = doc.Range(f.Code.Start - 1, f.Result.End + 1)
                font = f.Result.Font.Duplicate
                target.Delete()
                target.Collapse(1)
                f = doc.Fields.Add(target, -1, code.strip()+' \\t', True)
                f.Result.Font = font
            if f.Code.Text.strip().upper().startswith(('CITATION ', 'BIBLIOGRAPHY')):
                f.Update()
        return {'ok': True, 'document': doc.FullName, 'message': 'Word citations and bibliography updated.'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:500]}
    finally:
        if owns_com:
            pythoncom.CoUninitialize()
