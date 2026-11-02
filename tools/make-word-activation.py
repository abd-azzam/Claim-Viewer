"""Create a disposable activation document using Microsoft's sideload template.

Template: OfficeDev/Office-Addin-Scripts, office-addin-dev-settings/templates/
WordDocumentWithTaskPane.docx. This never opens or modifies a user's document.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET
import json
import secrets
from xml.sax.saxutils import escape

root = Path(__file__).resolve().parents[1]
manifest = ET.parse(root / 'word/manifest-template.xml').getroot()
addin_id = manifest.find('{http://schemas.microsoft.com/office/appforoffice/1.1}Id').text
catalog = json.loads((root / 'word/catalog-config.json').read_text(encoding='utf-8-sig'))['url']
output = root / ('word/Claim Viewer Word setup-' + secrets.token_hex(4) + '.docx')
with ZipFile(root / 'tools/word-sideload-template.docx') as source, ZipFile(output, 'w', ZIP_DEFLATED) as target:
    for entry in source.infolist():
        data = source.read(entry.filename)
        if entry.filename == 'word/webextensions/webextension.xml':
            data = data.replace(b'00000000-0000-0000-0000-000000000000', addin_id.encode())
            data = data.replace(b'store="developer" storeType="Registry"',
                                ('store="'+escape(catalog, {'"': '&quot;'})+'" storeType="FileSystem"').encode())
        if entry.filename == 'word/document.xml':
            doc = ET.fromstring(data)
            body = doc.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body')
            paragraph = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
            run = ET.SubElement(paragraph, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
            ET.SubElement(run, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t').text = 'Claim Viewer citation add-in setup. Disposable document; no private writing.'
            body.insert(0, paragraph)
            data = ET.tostring(doc, encoding='utf-8', xml_declaration=True)
        target.writestr(entry, data)
print(output)
