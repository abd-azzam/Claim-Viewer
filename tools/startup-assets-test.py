"""Interface upgrades must preserve research data and leave invalid pages untouched."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from startup_assets import refresh_page

class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'template').mkdir()
        (self.root/'template/template.html').write_text('<new>const DATA=/*DATA*/null;</new>',encoding='utf-8')
    def write(self,path,text):Path(path).write_text(text,encoding='utf-8')
    def test_upgrade_preserves_claims_and_keeps_previous_page(self):
        data={'sources':[{'id':'reading','claims':[{'quote':'Unicode café and braces } ;'}]}],'seed':{'notes':'Keep these notes'}}
        payload=json.dumps(data,ensure_ascii=False)
        old='<old>const DATA = '+payload+';</old>'
        (self.root/'index.html').write_text(old,encoding='utf-8')
        self.assertTrue(refresh_page(self.root,self.write))
        self.assertEqual((self.root/'index.html').read_text(encoding='utf-8'),'<new>const DATA='+payload+';</new>')
        self.assertEqual((self.root/'index.html.previous').read_text(encoding='utf-8'),old)
        self.assertFalse(refresh_page(self.root,self.write))
    def test_unrecognized_page_is_not_overwritten(self):
        (self.root/'index.html').write_text('unknown custom page',encoding='utf-8')
        with self.assertRaises(ValueError):refresh_page(self.root,self.write)
        self.assertEqual((self.root/'index.html').read_text(),'unknown custom page')
        self.assertFalse((self.root/'index.html.previous').exists())
    def test_malformed_template_is_not_applied(self):
        (self.root/'index.html').write_text('const DATA={};',encoding='utf-8')
        (self.root/'template/template.html').write_text('bad template',encoding='utf-8')
        with self.assertRaises(ValueError):refresh_page(self.root,self.write)
        self.assertEqual((self.root/'index.html').read_text(),'const DATA={};')

if __name__=='__main__':unittest.main(verbosity=2)
