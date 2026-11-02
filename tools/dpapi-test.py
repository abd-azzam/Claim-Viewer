"""Test the app's actual Windows DPAPI helper without loading or writing user settings."""
import ast
import ctypes
import pathlib
source = pathlib.Path(__file__).resolve().parents[1] / 'launch.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in ('_Blob', '_dpapi')]
namespace = {'ctypes': ctypes}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
secret = b'fixture-key-not-a-real-provider-secret'
encrypted = namespace['_dpapi'](secret, True)
assert encrypted != secret
assert secret not in encrypted
assert namespace['_dpapi'](encrypted, False) == secret
print('Windows DPAPI encryption/decryption round trip PASS; no user settings accessed.')
