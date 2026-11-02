"""Verify APSA output in native Word using disposable sources and documents."""
from pathlib import Path
import json
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import word_citations as wc
import pythoncom
import win32com.client

pythoncom.CoInitialize()
app=win32com.client.DispatchEx('Word.Application')
app.Visible=False
original=app.Options.BibliographyStyle
doc=app.Documents.Add()
try:
    style='American Political Science Association (APSA)'
    assert style in wc.styles()
    result=wc.command(Path.cwd(),'style',{'style':style},app)
    assert result['ok'],result
    with tempfile.TemporaryDirectory(dir='C:/Apps/ClaimViewer-test-temp') as folder:
        items={}
        for count in (1,2,3,4):
            names=['Alami, Ilias','Dixon, Adam','Smith, Jane','Jones, John'][:count]
            if count==4:names[0]='Zeta, Ilias'
            items[str(count)]={'meta':{'title':'APSA fixture '+str(count),'author':'; '.join(names),'year':'2023','type':'book','city':'Oxford','publisher':'Fixture Press'}}
        Path(folder,'library.json').write_text(json.dumps({'items':items}),encoding='utf-8')
        for count,authors in ((1,'Alami'),(2,'Alami and Dixon'),(3,'Alami, Dixon, and Smith'),(4,'Zeta et al.')):
            for form in ('parenthetical','narrative'):
                for pages in ('','12'):
                    app.Selection.SetRange(doc.Content.End-1,doc.Content.End-1)
                    start=doc.Content.End-1
                    result=wc.command(folder,'citation',{'source':str(count),'form':form,'pages':pages},app)
                    assert result['ok'],result
                    actual=doc.Range(start,doc.Content.End-1).Text.strip()
                    year='2023'+(', 12' if pages else '')
                    expected=(authors+' ('+year+')') if form=='narrative' else '('+authors+' '+year+')'
                    assert actual==expected,(expected,actual)
                    print(expected,'PASS')
                    app.Selection.TypeParagraph()
        result=wc.command(folder,'bibliography',{},app)
        assert result['ok'],result
        field=doc.Fields.Item(doc.Fields.Count)
        text=field.Result.Text
        assert 'Alami, Ilias. 2023.' in text,text
        assert 'Oxford: Fixture Press' in text,text
        assert '——' not in text and text.count('Alami, Ilias')==3,text
        assert 'APSA fixture 1' in text,text
        print('APSA bibliography: full names, year, title, publisher and repeated authors PASS')
finally:
    doc.Close(False)
    app.Options.BibliographyStyle=original
    app.Quit()
    pythoncom.CoUninitialize()
