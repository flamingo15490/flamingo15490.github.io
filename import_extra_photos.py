"""Import public extra photos and encrypt private photos entirely before publication."""
from pathlib import Path
from io import BytesIO
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps, ImageCms
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import argparse, base64, json, secrets
from site_io import write
SITE=Path(__file__).resolve().parent
ITERATIONS=600000
PROFILES=[('small',400,66,30000,54),('medium',800,72,80000,60),('display',1600,80,240000,68)]
FIELDS={'display':('file','sha256','width','height'),'small':('thumbnail','thumbnail_sha256','thumbnail_width','thumbnail_height'),'medium':('thumbnail_large','thumbnail_large_sha256','thumbnail_large_width','thumbnail_large_height')}

def encode(path):
    original=path.read_bytes()
    digest=sha256(original).hexdigest()
    with Image.open(BytesIO(original)) as opened:
        image=ImageOps.exif_transpose(opened).convert('RGB')
        icc=opened.info.get('icc_profile')
        if icc:
            image=ImageCms.profileToProfile(image,ImageCms.ImageCmsProfile(BytesIO(icc)),ImageCms.createProfile('sRGB'),outputMode='RGB')
        image.info.clear()
        variants={}
        for name,edge,quality,cap,floor in PROFILES:
            variant=image.copy();variant.thumbnail((edge,edge),Image.Resampling.LANCZOS)
            while True:
                out=BytesIO();variant.save(out,format='WEBP',quality=quality,method=6)
                raw=out.getvalue()
                if len(raw)<=cap or quality<=floor:break
                quality=max(floor,quality-6)
            with Image.open(BytesIO(raw)) as checked:
                assert not checked.getexif() and 'xmp' not in checked.info
            variants[name]={'bytes':raw,'width':variant.width,'height':variant.height,'quality':quality}
    assert sha256(path.read_bytes()).hexdigest()==digest,'原图在导入过程中发生变化'
    return path,digest,len(original),variants

def inputs(folder):
    folder=folder.resolve()
    assert folder.is_dir(),'照片文件夹不存在'
    # Plain originals must never be placed in the publishable source directories.
    assert not folder.is_relative_to(SITE) or folder.is_relative_to(SITE/'.local')
    files=sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in {'.jpg','.jpeg','.png','.webp'})
    assert files,'照片文件夹为空'
    return folder,files

def import_public(folder):
    folder,files=inputs(folder);photos=[];manifest=[];total=0
    for index,(path,digest,size,variants) in enumerate(ThreadPoolExecutor(max_workers=4).map(encode,files),1):
        photo={'id':'other-'+digest[:20],'alt':f'其他照片 {index}'}
        for name,v in variants.items():
            relative=f'assets/gallery/photos/other-{digest[:20]}-{name}.webp'
            write(relative,v['bytes']);total+=len(v['bytes'])
            photo.update(dict(zip(FIELDS[name],[relative,sha256(v['bytes']).hexdigest(),v['width'],v['height']])))
        photos.append(photo);manifest.append({'source':path.relative_to(folder).as_posix(),'source_sha256':digest,'source_bytes':size})
    assert len({p['id'] for p in photos})==len(photos),'发现重复图片，请先核对来源'
    write('other-gallery.json',json.dumps({'photos':photos},ensure_ascii=False,indent=2)+'\n')
    write('.local/other-photo-import.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return {'photos':len(photos),'source_bytes':sum(m['source_bytes'] for m in manifest),'published_bytes':total}

def import_private(folder,password_file):
    folder,files=inputs(folder)
    password_file=password_file.resolve()
    assert not password_file.is_relative_to(SITE) or password_file.is_relative_to(SITE/'.local'),'密码不能放在公开源码目录'
    password=password_file.read_text(encoding='utf-8-sig').rstrip('\r\n')
    assert len(password)>=20,'请使用至少20个字符的强密码'
    salt=secrets.token_bytes(16)
    key=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=ITERATIONS).derive(password.encode('utf-8'))
    aes=AESGCM(key);published=[];photos=[];manifest=[]
    def encrypt(raw):
        relative='assets/gallery/locked/'+secrets.token_hex(16)+'.bin'
        nonce=secrets.token_bytes(12)
        payload=b'GMP1'+nonce+aes.encrypt(nonce,raw,('gaomu-private-v1:'+relative).encode('utf-8'))
        assert aes.decrypt(nonce,payload[16:],('gaomu-private-v1:'+relative).encode('utf-8'))==raw
        write(relative,payload)
        entry={'file':relative,'sha256':sha256(payload).hexdigest(),'bytes':len(payload)}
        published.append(entry)
        return entry
    for index,(path,digest,size,variants) in enumerate(ThreadPoolExecutor(max_workers=4).map(encode,files),1):
        photo={'id':'private-'+secrets.token_hex(12),'alt':f'个照合照 {index}'}
        for name,v in variants.items():
            entry=encrypt(v['bytes'])
            photo.update(dict(zip(FIELDS[name],[entry['file'],entry['sha256'],v['width'],v['height']])))
        photos.append(photo);manifest.append({'source':path.relative_to(folder).as_posix(),'source_sha256':digest,'source_bytes':size})
    encrypted_manifest=encrypt(json.dumps({'schema_version':1,'photos':photos},ensure_ascii=False,separators=(',',':')).encode())
    config={'schema_version':1,'cipher':'AES-GCM','kdf':'PBKDF2','hash':'SHA-256','iterations':ITERATIONS,'salt':base64.b64encode(salt).decode(),'manifest':encrypted_manifest,'files':published}
    write('private-gallery.json',json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    write('.local/private-photo-import.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return {'photos':len(photos),'source_bytes':sum(m['source_bytes'] for m in manifest),'encrypted_files':len(published),'published_bytes':sum(f['bytes'] for f in published)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--other',type=Path)
    parser.add_argument('--private',type=Path)
    parser.add_argument('--password-file',type=Path,default=SITE/'.local/画廊密码.txt')
    args=parser.parse_args()
    assert args.other or args.private,'请指定要导入的文件夹'
    stats={}
    if args.other:stats['other']=import_public(args.other)
    if args.private:stats['private']=import_private(args.private,args.password_file)
    write('.local/extra-photo-stats.json',json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':main()
