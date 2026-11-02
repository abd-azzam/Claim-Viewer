"""Settings actions use disposable files and mocked installation commands."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
APP=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('settings_service',APP/'settings_service.py')
service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='settings-service-',dir=APP/'tools');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'pdf').mkdir();(self.root/'data').mkdir()
        (self.root/'library.json').write_text(json.dumps({'items':{'source':{'title':'Fixture book','meta':{'author':'Author, A','year':'2025','type':'book'}}}}))
        (self.root/'state.json').write_text('{"cv:zk":"fixture notes"}')
        (self.root/'providers.json').write_text('fixture-provider-secret')
        (self.root/'ai.json').write_text('fixture-legacy-secret')
        (self.root/'data/claims.json').write_text('{}');(self.root/'pdf/fixture.pdf').write_bytes(b'%PDF-fixture')
    def window(self,destination):
        class Window:
            def create_file_dialog(self,*args,**kwargs):return [str(destination)]
        return Window()
    def test_backup_contains_research_files_and_excludes_credentials(self):
        out=self.root/'backup.zip';r=service.command(self.root,'backup','fixture.exe',self.window(out))
        self.assertTrue(r['ok'])
        with zipfile.ZipFile(out) as z:
            self.assertIn('pdf/fixture.pdf',z.namelist());self.assertIn('state.json',z.namelist())
            self.assertNotIn('providers.json',z.namelist());self.assertNotIn('ai.json',z.namelist())
    def test_ris_preserves_title_author_year_and_source_type(self):
        out=self.root/'library.ris';service.command(self.root,'export-ris','fixture.exe',self.window(out))
        text=out.read_text();self.assertIn('TY  - BOOK',text);self.assertIn('TI  - Fixture book',text);self.assertIn('AU  - Author, A',text)
    def test_unknown_actions_fail_without_running_commands(self):
        with patch.object(service.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'Unknown settings action'):
                service.command(self.root,'arbitrary-command','fixture.exe',None)
            run.assert_not_called()
    def test_install_uses_fixed_script_and_current_app_executable(self):
        class Completed:
            returncode=0;stdout='Installed';stderr=''
        with patch.object(service.runpy,'run_path',return_value={'output':self.root/'word/Claim Viewer Word setup-fixture.docx'}) as prepare,patch.object(service.os,'startfile') as launch,patch.object(service.subprocess,'run',return_value=Completed()) as run,patch.object(service,'word_status',return_value={'ok':True,'registered':True,'running':True}):
            result=service.command(self.root,'word-install',r'C:\Program Files\Claim Viewer\ClaimViewer.exe',None)
            args=run.call_args.args[0]
            self.assertEqual(args[-2:],['-AppExe',r'C:\Program Files\Claim Viewer\ClaimViewer.exe'])
            self.assertIn(str(self.root/'word/install-web-addin.ps1'),args);self.assertTrue(result['registered'])
            self.assertEqual(prepare.call_count,1)
            self.assertNotIn('PSMODULEPATH',{k.upper() for k in run.call_args.kwargs['env']})
            launch.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
