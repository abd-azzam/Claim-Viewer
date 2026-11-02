"""Integration test: a separate hidden Word instance and an unsaved disposable document."""
import pathlib
import sys
import tempfile
import json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import word_citations as wc
import pythoncom
import win32com.client
pythoncom.CoInitialize()
app = win32com.client.DispatchEx('Word.Application')
app.Visible = False
doc = None
try:
    doc = app.Documents.Add()
    if '--ribbon' in sys.argv:
        app.COMAddIns.Update()
        addin = app.COMAddIns.Item('ClaimViewer.Citations')
        if not addin.Connect:
            addin.Connect = True
        assert addin.Connect
        print('Word COM ribbon add-in loaded PASS')
    with tempfile.TemporaryDirectory(dir=r'C:\Apps\ClaimViewer-test-temp') as folder:
        pathlib.Path(folder, 'library.json').write_text(json.dumps({'items': {'fixture': {'title': 'Citation integration fixture', 'meta': {'title': 'Citation integration fixture', 'author': 'Example, Test', 'year': '2020', 'type': 'book', 'publisher': 'Test fixture'}}}}))
        for action, payload in [('state', {}), ('citation', {'source': 'fixture', 'pages': '12–14'}), ('bibliography', {}), ('refresh', {})]:
            result = wc.command(folder, action, payload, app)
            assert result['ok'], (action, result)
            print(action, 'PASS')
        codes = [doc.Fields.Item(i).Code.Text for i in range(1, doc.Fields.Count+1)]
        assert any('CITATION CV' in c and '12–14' in c for c in codes), codes
        assert any('BIBLIOGRAPHY' in c for c in codes), codes
        assert doc.Bibliography.Sources.Count == 1
        assert 'Citation integration fixture' in doc.Content.Text, 'Bibliography text did not include source title'
        assert '12' in doc.Content.Text, 'Page locator did not appear in the rendered citation'
        style = next((s for s in wc.styles() if s.lower().startswith('apa')), None)
        if style:
            result = wc.command(folder, 'style', {'style': style}, app)
            assert result['ok'], result
            assert 'Citation integration fixture' in doc.Content.Text
            print('Installed citation style change PASS')
        result = wc.command(folder, 'citation', {'source': 'fixture', 'pages': '20'}, app)
        assert result['ok'], result
        assert doc.Bibliography.Sources.Count == 1
        print('Native fields, page locators, source deduplication PASS')
        for pages in ('', '24–26'):
            app.Selection.SetRange(doc.Content.End-1,doc.Content.End-1)
            app.Selection.TypeParagraph()
            start=doc.Content.End-1
            result=wc.command(folder,'citation',{'source':'fixture','form':'narrative','pages':pages},app)
            assert result['ok'],result
            text=doc.Range(start,doc.Content.End-1).Text
            assert 'Example (' in text and '2020' in text,text
            assert 'Example, 2020' not in text,text
            assert 'Citation integration fixture' not in text,text
            assert ('24' in text)==bool(pages),text
            field=doc.Fields.Item(doc.Fields.Count)
            code=field.Code.Text.replace(' \\t','')
            target=doc.Range(field.Code.Start-1,field.Code.Start-1)
            field.Delete()
            field=doc.Fields.Add(target,-1,code,True)
            field.Update()
            result=wc.command(folder,'refresh',{},app)
            assert result['ok'],result
            text=doc.Range(start,doc.Content.End-1).Text
            assert 'Citation integration fixture' not in text,text
            assert 'Example (2020' in text,text
            assert ('24' in text)==bool(pages),text
        print('Narrative citations with and without page numbers PASS')
finally:
    if doc is not None:
        doc.Close(False)
    app.Quit()
    pythoncom.CoUninitialize()
