"""Deletion persists across stale saves; exact DOI lookup never guesses a title."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import launch
import library_tools

class LibraryActions(unittest.TestCase):
    def test_delete_removes_pdf_and_count_and_keeps_recovery_copy(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder);(root/'pdf').mkdir()
            library={'collections':[],'items':{'a':{'title':'A'},'b':{'title':'B'}}}
            (root/'library.json').write_text(json.dumps(library))
            (root/'pdf/a.pdf').write_bytes(b'%PDF fixture')
            with patch.multiple(launch,ROOT=str(root),PDF_DIR=str(root/'pdf'),LIB_PATH=str(root/'library.json'),SRC_PATH=str(root/'sources.js')):
                result=launch.Api().delete_library_item('a')
                self.assertTrue(result['ok'],result)
                self.assertEqual(len(result['library']['items']),1)
                self.assertFalse((root/'pdf/a.pdf').exists())
                self.assertEqual((Path(result['backup'])/'a.pdf').read_bytes(),b'%PDF fixture')
                self.assertNotIn('a',launch.read_lib()['items'])
                launch.write_lib(copy.deepcopy(library))
                self.assertNotIn('a',launch.read_lib()['items'],'A stale metadata save must not resurrect a deletion')
                launch.write_lib(copy.deepcopy(library),restored=['a'])
                self.assertIn('a',launch.read_lib()['items'],'An explicit import can restore a reading')
    def test_delete_cannot_move_a_file_outside_the_managed_pdf_folder(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder);(root/'outside.pdf').write_bytes(b'untouched')
            with self.assertRaises(ValueError):library_tools.remove_item(root,'../outside',{'items':{'../outside':{}}})
            self.assertEqual((root/'outside.pdf').read_bytes(),b'untouched')
    def test_exact_doi_metadata_fills_csl_fields(self):
        data={'title':'A DOI title','author':[{'family':'Example','given':'A'}],'issued':{'date-parts':[[2024]]},'container-title':'Journal','page':'12-19','type':'article-journal'}
        with patch.object(library_tools.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(data).encode())) as request:
            result=library_tools.lookup_doi('https://doi.org/10.1234/exact')
        self.assertEqual(result['title'],'A DOI title');self.assertEqual(result['author'],'Example, A');self.assertEqual(result['year'],'2024')
        self.assertEqual(result['pages'],'12-19');self.assertEqual(result['doi'],'10.1234/exact')
        self.assertEqual(request.call_args.args[0].full_url,'https://doi.org/10.1234/exact')
    def test_doi_uses_an_exact_fallback_when_the_resolver_fails(self):
        data={'message':{'title':['Exact fallback'],'author':[],'issued':{'date-parts':[[2020]]}}}
        with patch.object(library_tools.urllib.request,'urlopen',side_effect=[OSError('offline'),io.BytesIO(json.dumps(data).encode())]):
            self.assertEqual(library_tools.lookup_doi('10.1234/exact')['title'],'Exact fallback')
    def test_invalid_doi_never_sends_a_request(self):
        with patch.object(library_tools.urllib.request,'urlopen') as request:
            self.assertFalse(library_tools.lookup_doi('https://example.com/private')['ok']);request.assert_not_called()
    def test_doi_preserves_report_type_and_structured_publisher(self):
        data={'title':'Report','type':'report','publisher':{'name':'Research Institute'}}
        with patch.object(library_tools.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
            result=library_tools.lookup_doi('10.1234/report')
        self.assertEqual(result['type'],'report');self.assertEqual(result['publisher'],'Research Institute')
if __name__=='__main__':unittest.main(verbosity=2)
