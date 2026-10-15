"""Import the user's province/city folders as optimized, metadata-free WebP assets."""
from pathlib import Path
from io import BytesIO
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps, ImageCms
import json, sys
SITE=Path(__file__).resolve().parent
from site_io import write as save
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=SITE/'.local/travel-photos')
SOURCE=parser.parse_args().source.resolve()
PROFILES=[('small',400,66,30000,54),('medium',800,72,80000,60),('display',1600,80,240000,68)]
def normalize(s):
    for suffix in ['维吾尔自治区','壮族自治区','回族自治区','自治区','特别行政区','省','市']:
        if s.endswith(suffix):return s[:-len(suffix)]
    return s

def main():
    data=json.loads((SITE/'gallery.json').read_text(encoding='utf-8'))
    tree=json.loads((SITE/'sources/china-region-names.json').read_text(encoding='utf-8'))['data'][0]['children']
    provinces={normalize(p['name']):p for p in tree}
    source_files=sorted(p for p in SOURCE.rglob('*') if p.is_file() and p.suffix.lower() in ['.jpg','.jpeg','.png','.webp'])
    assert source_files,'旅行图片文件夹中没有支持的照片'
    groups={}
    before={}
    for p in source_files:
        parts=p.relative_to(SOURCE).parts
        assert len(parts) in (2,3),f'照片须按省份/可选城市/图片放置：{p.relative_to(SOURCE)}'
        assert parts[0] in provinces,f'省份名称无法核对：{parts[0]}'
        province=provinces[parts[0]]
        city_name=parts[1] if len(parts)==3 else parts[0]
        city_id=province['gb'] if len(parts)==2 else None
        parent_id=province['gb'] if len(parts)==2 else None
        if len(parts)==3:
            matches=[]
            for city in province['children']:
                if normalize(city['name'])==normalize(city_name):matches.append((city['gb'],city['gb']))
                for district in city['children']:
                    if normalize(district['name'])==normalize(city_name):matches.append((district['gb'],city['gb']))
            assert len(matches)==1,f'城市名称无法唯一核对：{parts[0]}/{city_name}'
            city_id,parent_id=matches[0]
        group_key=(province['gb'],city_name)
        groups.setdefault(group_key,{'id':'travel-'+city_id[3:],'name':city_name,'province_id':province['gb'],'province_name':province['name'],'city_id':city_id,'city_parent_id':parent_id,'source_kind':'travel-folder','photos':[]})
        before[p]=sha256(p.read_bytes()).hexdigest()
    def encode(p):
        original=p.read_bytes();digest=sha256(original).hexdigest()
        assert digest==before[p],'原图在读取过程中变化'
        with Image.open(BytesIO(original)) as opened:
            image=ImageOps.exif_transpose(opened).convert('RGB')
            icc=opened.info.get('icc_profile')
            if icc:
                try:image=ImageCms.profileToProfile(image,ImageCms.ImageCmsProfile(BytesIO(icc)),ImageCms.createProfile('sRGB'),outputMode='RGB')
                except (OSError,ValueError):pass
            image.info.clear()
            variants={}
            for name,edge,quality,cap,floor in PROFILES:
                variant=image.copy();variant.thumbnail((edge,edge),Image.Resampling.LANCZOS)
                while True:
                    out=BytesIO();variant.save(out,format='WEBP',quality=quality,method=6)
                    raw=out.getvalue()
                    if len(raw)<=cap or quality<=floor:break
                    quality=max(floor,quality-6)
                variants[name]={'bytes':raw,'width':variant.width,'height':variant.height,'quality':quality,'file':f'assets/gallery/photos/{digest[:20]}-{name}.webp'}
        return p,digest,variants,len(original)
    manifest=[];output_sizes={};small=0;medium=0;display=0
    for p,digest,variants,source_size in ThreadPoolExecutor(max_workers=4).map(encode,source_files):
        parts=p.relative_to(SOURCE).parts;province=provinces[parts[0]];city=parts[1] if len(parts)==3 else parts[0]
        group=groups[(province['gb'],city)]
        photo={'id':'photo-'+sha256(str(p.relative_to(SOURCE)).encode()).hexdigest()[:20],'alt':f'{city}旅行照片 {len(group["photos"])+1}'}
        for name,v in variants.items():
            save(v['file'],v['bytes']);output_sizes[v['file']]=len(v['bytes'])
            fields={'display':('file','sha256','width','height'),'small':('thumbnail','thumbnail_sha256','thumbnail_width','thumbnail_height'),'medium':('thumbnail_large','thumbnail_large_sha256','thumbnail_large_width','thumbnail_large_height')}[name]
            photo.update(dict(zip(fields,[v['file'],sha256(v['bytes']).hexdigest(),v['width'],v['height']])))
        group['photos'].append(photo)
        manifest.append({'source_file':p.relative_to(SOURCE).as_posix(),'source_sha256':digest,'source_bytes':source_size,'photo_id':photo['id'],'variants':{n:{k:v for k,v in item.items() if k!='bytes'} for n,item in variants.items()}})
        print(f'Optimized {len(manifest)}/{len(source_files)}',flush=True)
    for p,digest in before.items():assert sha256(p.read_bytes()).hexdigest()==digest,'原图在导入期间变化，停止保存清单'
    unmanaged=[p for p in data['places'] if p.get('source_kind')!='travel-folder']
    assert not ({p['id'] for p in unmanaged}&{p['id'] for p in groups.values()}),'与手工相册编号冲突'
    data['schema_version']=4;data['map']['pins_enabled']=False
    data['places']=unmanaged+list(groups.values())
    data['photo_optimization']={'format':'WebP','grid_long_edges':[400,800],'lightbox_long_edge':1600,'metadata_removed':True}
    save('gallery.json',(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
    stats={'photos':len(manifest),'albums':len(groups),'provinces':len({key[0] for key in groups}),'source_bytes':sum(p.stat().st_size for p in source_files),'deployed_photo_bytes':sum(output_sizes.values()),'small_thumbnails_bytes':sum(v for p,v in output_sizes.items() if '-small.' in p),'medium_thumbnails_bytes':sum(v for p,v in output_sizes.items() if '-medium.' in p),'display_bytes':sum(v for p,v in output_sizes.items() if '-display.' in p),'originals_unchanged':True}
    save('.local/photo-import-manifest.json',json.dumps({'date':'2026-10-16','stats':stats,'photos':manifest},ensure_ascii=False,indent=2).encode())
    print(json.dumps(stats,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
