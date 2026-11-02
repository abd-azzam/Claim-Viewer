"""Build only this account's local Word add-in manifest and localhost TLS certificate."""
import datetime
import ipaddress
import json
import pathlib
import secrets
import struct
import zlib
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

root=pathlib.Path(__file__).resolve().parents[1]/'word'
config_path=root/'service-config.json'
config=json.loads(config_path.read_text()) if config_path.exists() else {'token':secrets.token_hex(32)}
config_path.write_text(json.dumps(config),encoding='utf-8')
if not (root/'localhost.pem').exists():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Claim Viewer localhost')])
    now=datetime.datetime.now(datetime.timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=5)).not_valid_after(now+datetime.timedelta(days=365))
          .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
          .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False)
          .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False)
          .sign(key,hashes.SHA256()))
    (root/'localhost.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (root/'localhost.cer').write_bytes(cert.public_bytes(serialization.Encoding.DER))
    (root/'localhost-key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
(root/'manifest.xml').write_text((root/'manifest-template.xml').read_text().replace('{{TOKEN}}',config['token']),encoding='utf-8')
# Small book glyph, used only to identify the citation command in Word's required icon sizes.
for size in (16,32,80):
    rows=[]
    for y in range(size):
        row=bytearray()
        for x in range(size):
            book=size*.18<x<size*.82 and size*.12<y<size*.88
            line=book and size*.32<x<size*.73 and any(abs(y-size*t)<size*.018 for t in (.32,.47,.62))
            row.extend((255,255,255,255) if line else (31,95,191,255) if book else (0,0,0,0))
        rows.append(b'\0'+row)
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
    (root/f'icon-{size}.png').write_bytes(data)
print('Word task-pane manifest and localhost TLS files prepared; no certificate trust or registry changes made.')
