"""Exact DOI lookup and recoverable removal of app-managed library PDFs."""
import html
import json
import pathlib
import re
import shutil
import time
import urllib.parse
import urllib.request


def remove_item(root, ident, library):
    if ident not in library['items']:
        raise ValueError('This reading is no longer in the library.')
    root = pathlib.Path(root).resolve()
    pdf = (root / 'pdf' / (ident + '.pdf')).resolve()
    if pdf.parent != (root / 'pdf').resolve():
        raise ValueError('Invalid reading identifier.')
    # Retain the app copy and metadata for recovery; never touch the imported original.
    backup = root / 'data' / 'deleted-readings' / str(time.time_ns())
    backup.mkdir(parents=True)
    (backup / 'reading.json').write_text(json.dumps({ident: library['items'][ident]}, ensure_ascii=False), encoding='utf-8')
    original = pdf.with_name(ident + '.original.pdf')
    moved = []
    try:
        for path in (pdf, original):
            if path.is_file():
                shutil.move(str(path), str(backup / path.name))
                moved.append(path)
    except OSError:
        for path in moved:
            shutil.move(str(backup / path.name), str(path))
        raise
    del library['items'][ident]
    library['_deleted'] = sorted(set(library.get('_deleted', [])) | {ident})
    return str(backup)


def lookup_doi(value):
    doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', str(value).strip(), flags=re.I)
    if not re.fullmatch(r'10\.\d{4,9}/\S{1,900}', doi):
        return {'ok': False, 'error': 'Enter a DOI such as 10.1234/example.'}
    encoded = urllib.parse.quote(doi, safe='/')
    urls = [('DOI', 'https://doi.org/' + encoded),
            ('Crossref DOI', 'https://api.crossref.org/works/' + encoded),
            ('DataCite DOI', 'https://api.datacite.org/dois/' + encoded)]
    def clean(text):
        if isinstance(text, dict):
            text = text.get('name', '')
        return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', '', str(text or '')))).strip()
    def first(value):
        return value[0] if isinstance(value, list) and value else value or ''
    for source, url in urls:
        try:
            request = urllib.request.Request(url, headers={'Accept': 'application/vnd.citationstyles.csl+json' if source == 'DOI' else 'application/json', 'User-Agent': 'ClaimViewer/2.4'})
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.load(response)
            if source == 'Crossref DOI':
                data = data['message']
            elif source == 'DataCite DOI':
                record = data['data']['attributes']
                data = {'title': record.get('titles', [{}])[0].get('title'), 'author': [{'family': a.get('familyName') or a.get('name'), 'given': a.get('givenName')} for a in record.get('creators', [])], 'year': record.get('publicationYear'), 'publisher': record.get('publisher'), 'type': (record.get('types') or {}).get('resourceTypeGeneral', '').lower()}
            title = clean(first(data.get('title')))
            if not title:
                continue
            authors = '; '.join(clean(a.get('literal') or ', '.join(filter(None, [a.get('family'), a.get('given')])) ) for a in data.get('author', []))
            dates = (data.get('issued') or data.get('published') or {}).get('date-parts') or [[]]
            kind = str(data.get('type') or '')
            return {'ok': True, 'source': source, 'doi': doi, 'title': title, 'author': authors,
                    'year': str(data.get('year') or (dates[0][0] if dates[0] else '')),
                    'type': {'article-journal': 'article', 'journal-article': 'article', 'article': 'article', 'proceedings-article': 'article', 'book': 'book', 'monograph': 'book', 'book-chapter': 'chapter', 'chapter': 'chapter', 'report': 'report', 'dissertation': 'thesis', 'thesis': 'thesis'}.get(kind, ''),
                    **{key: clean(first(data.get(remote))) for key, remote in [('journal', 'container-title'), ('volume', 'volume'), ('issue', 'issue'), ('pages', 'page'), ('publisher', 'publisher'), ('city', 'publisher-location'), ('isbn', 'ISBN')]}}
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            continue
    return {'ok': False, 'error': 'No metadata was available for this DOI. Your fields were not changed.'}
