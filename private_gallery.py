"""Validate and publish ciphertext only; no password or decryption is used at build time."""
import base64,hashlib,json,re

def publish_locked_gallery(site,write):
    config=json.loads((site/'private-gallery.json').read_text(encoding='utf-8'))
    assert config['schema_version']==1
    assert (config['cipher'],config['kdf'],config['hash'])==('AES-GCM','PBKDF2','SHA-256')
    assert 600000<=config['iterations']<=2000000
    assert len(base64.b64decode(config['salt'],validate=True))==16
    assert config['files'] and len({f['file'] for f in config['files']})==len(config['files'])
    assert config['manifest'] in config['files']
    for item in config['files']:
        relative=item['file']
        assert re.fullmatch(r'assets/gallery/locked/[a-f0-9]{32}\.bin',relative)
        path=(site/relative).resolve();path.relative_to((site/'assets/gallery/locked').resolve())
        raw=path.read_bytes()
        assert raw[:4]==b'GMP1' and len(raw)>32 and len(raw)==item['bytes']
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        write('dist/'+relative,raw)
    return {key:config[key] for key in ['schema_version','cipher','kdf','hash','iterations','salt','manifest']}
