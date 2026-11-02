"""A citation must reach its Word host, even with multiple Word instances."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('word_binding', Path(__file__).resolve().parents[1] / 'word_citations.py')
wc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wc)

class ComError(Exception):
    pass

def app_with(*paths):
    docs = [SimpleNamespace(FullName=path) for path in paths]
    app = SimpleNamespace(Documents=SimpleNamespace(Count=len(docs), Item=lambda i: docs[i-1]))
    for doc in docs:
        doc.Application = app
    return app, docs

class Moniker:
    def __init__(self, path, document):
        self.path, self.document = path, document

    def GetDisplayName(self, *args):
        return self.path

    def QueryInterface(self, *args):
        return self.document

class BindingTests(unittest.TestCase):
    def resolver(self, first, documents):
        looked_up = []
        monikers = [Moniker(path, doc) for path, doc in documents]
        def get_running(moniker):
            looked_up.append(moniker.path)
            return moniker
        table = SimpleNamespace(EnumRunning=lambda: iter(monikers), GetObject=get_running)
        com = SimpleNamespace(com_error=ComError, IID_IDispatch='dispatch',
                              CreateBindCtx=lambda _: None, GetRunningObjectTable=lambda: table)
        client = SimpleNamespace(GetActiveObject=lambda _: first, Dispatch=lambda doc: doc)
        return client, com, looked_up

    def test_hidden_empty_word_does_not_steal_a_visible_documents_citations(self):
        hidden, _ = app_with('Document1')
        visible, docs = app_with(r'C:\Docs\Target.docx')
        client, com, found = self.resolver(hidden, [(docs[0].FullName, docs[0])])
        self.assertIs(wc._word_application(r'C:\Docs\Target.docx', client, com), visible)
        self.assertEqual(found, [docs[0].FullName])

    def test_registered_document_uri_matches_without_opening_another_file(self):
        hidden, _ = app_with()
        visible, docs = app_with(r'C:\Docs\100% complete.docx')
        client, com, found = self.resolver(hidden, [(docs[0].FullName, docs[0])])
        self.assertIs(wc._word_application('file:///C:/Docs/100%25%20complete.docx', client, com), visible)
        self.assertEqual(len(found), 1)

    def test_unrelated_documents_are_not_bound_or_read(self):
        hidden, _ = app_with()
        target, docs = app_with(r'C:\Docs\Target.docx')
        client, com, found = self.resolver(hidden, [(r'C:\Docs\Other.docx', None), (docs[0].FullName, docs[0])])
        self.assertIs(wc._word_application(docs[0].FullName, client, com), target)
        self.assertEqual(found, [docs[0].FullName])

    def test_missing_host_fails_without_opening_a_file(self):
        hidden, _ = app_with('Document1')
        client, com, found = self.resolver(hidden, [])
        with self.assertRaisesRegex(ValueError, 'not found among open Word documents'):
            wc._word_application(r'C:\Docs\Closed.docx', client, com)
        self.assertEqual(found, [])

    def test_existing_matching_instance_needs_no_other_document_binding(self):
        target, docs = app_with(r'C:\Docs\Target.docx')
        client, com, found = self.resolver(target, [])
        self.assertIs(wc._word_application(docs[0].FullName, client, com), target)
        self.assertEqual(found, [])

    def test_bound_document_identity_must_still_match_host(self):
        hidden, _ = app_with()
        wrong, docs = app_with(r'C:\Docs\Other.docx')
        client, com, _ = self.resolver(hidden, [(r'C:\Docs\Target.docx', docs[0])])
        with self.assertRaises(ValueError):
            wc._word_application(r'C:\Docs\Target.docx', client, com)

if __name__ == '__main__':
    unittest.main(verbosity=2)
