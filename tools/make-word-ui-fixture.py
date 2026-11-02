"""Create a clearly labelled disposable Word document for add-in UI verification."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
p=Path(__file__).resolve().parent/'word-addin-smoke.docx'
if not p.exists():
    with ZipFile(p,'w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Claim Viewer add-in test document. This file contains no private writing.</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')
print(p)
