"""Render the travel gallery from explicitly supplied photos only."""
from pathlib import Path
from PIL import Image
from io import BytesIO
import json, hashlib, html, re

def render_gallery(site, write):
    data = json.loads((site / 'gallery.json').read_text(encoding='utf-8'))
    assert data['schema_version'] == 4
    def asset(relative, expected=None):
        assert isinstance(relative, str) and relative.startswith('assets/gallery/')
        path = (site / relative).resolve()
        path.relative_to((site / 'assets/gallery').resolve())
        raw = path.read_bytes()
        if expected:
            assert hashlib.sha256(raw).hexdigest() == expected, '画廊资源与已核对版本不一致'
        with Image.open(BytesIO(raw)) as im:
            im.verify()
        write('dist/' + relative, raw)
        return raw
    base = data['map']
    raw = asset(base['file'], base['sha256'])
    with Image.open(BytesIO(raw)) as im:
        assert im.size == (base['width'], base['height'])
    assert isinstance(base['pins_enabled'], bool)
    from atlas_builder import build_atlas
    atlas_svg, atlas_data = build_atlas(site, base['vector'])
    ids = set()
    photo_ids = set()
    for place in data['places']:
        assert re.fullmatch(r'[a-z0-9][a-z0-9-]*', place['id']) and place['id'] not in ids
        ids.add(place['id'])
        assert place['name'].strip()
        assert place['province_id'] in {r['id'] for r in atlas_data['regions']}
        if place.get('location'):
            assert all(isinstance(place['location'][k],(int,float)) for k in ['lng','lat'])
            assert 73 <= place['location']['lng'] <= 136 and 3 <= place['location']['lat'] <= 55
        assert not place.get('pin'), '新地图使用经纬度location，不再使用图片百分比pin'
        for photo in place['photos']:
            assert photo['id'] not in photo_ids
            photo_ids.add(photo['id'])
            assert photo['file'].startswith('assets/gallery/photos/')
            assert photo['alt'].strip()
            content = asset(photo['file'], photo['sha256'])
            with Image.open(BytesIO(content)) as im:
                assert im.size == (photo['width'], photo['height'])
            if photo.get('thumbnail'):
                assert photo['thumbnail'].startswith('assets/gallery/photos/')
                asset(photo['thumbnail'], photo['thumbnail_sha256'])
            if photo.get('thumbnail_large'):
                content = asset(photo['thumbnail_large'], photo['thumbnail_large_sha256'])
                with Image.open(BytesIO(content)) as im:
                    assert im.size == (photo['thumbnail_large_width'], photo['thumbnail_large_height'])
            for field in ['file','thumbnail','thumbnail_large']:
                if photo.get(field):
                    with Image.open(site/photo[field]) as im:
                        assert not im.getexif() and 'xmp' not in im.info
            assert max(photo['width'],photo['height']) <= 1600
    other_photos = json.loads((site/'other-gallery.json').read_text(encoding='utf-8'))['photos']
    for photo in other_photos:
        assert photo['id'] not in photo_ids and photo['alt'].strip()
        photo_ids.add(photo['id'])
        for field in ['file','thumbnail','thumbnail_large']:
            assert photo[field].startswith('assets/gallery/photos/')
            content = asset(photo[field], photo[field+'_sha256'] if field != 'file' else photo['sha256'])
            with Image.open(BytesIO(content)) as im:
                prefix = '' if field == 'file' else field+'_'
                assert im.size == (photo[prefix+'width'],photo[prefix+'height'])
                assert not im.getexif() and 'xmp' not in im.info
        assert max(photo['width'],photo['height']) <= 1600
    from private_gallery import publish_locked_gallery
    private_config=publish_locked_gallery(site,write)
    places = data['places']
    count = sum(len(p['photos']) for p in places)
    # Embedding JSON safely also prevents captions from becoming HTML/script.
    client_places=[]
    client_fields={'id','file','width','height','alt','caption','date','thumbnail','thumbnail_width','thumbnail_height','thumbnail_large','thumbnail_large_width','thumbnail_large_height'}
    for place in places:
        client_places.append({k:v for k,v in place.items() if k in {'id','name','province_id','province_name','city_id','city_parent_id'}} | {'photos':[{k:v for k,v in photo.items() if k in client_fields} for photo in place['photos']]})
    client = json.dumps({'private_config':private_config,'places':client_places,'other_photos':[{k:v for k,v in photo.items() if k in client_fields} for photo in other_photos],**atlas_data},ensure_ascii=False,separators=(',',':')).replace('<',r'\u003c')
    esc = lambda s: html.escape(s, quote=True)
    write('dist/gallery.js', (site/'gallery.js').read_bytes())
    write('dist/private-viewer.js',(site/'private-viewer.js').read_bytes())
    return f'''<section class="page-head wrap gallery-heading"><h1>画廊</h1></section>
<div data-travel-gallery>
  <div class="wrap gallery-tabs" role="tablist" aria-label="画廊分类">
    <button type="button" id="gallery-travel-tab" role="tab" aria-selected="true" aria-controls="gallery-travel-panel" tabindex="0" data-gallery-view="travel">旅行足迹</button>
    <button type="button" id="gallery-other-tab" role="tab" aria-selected="false" aria-controls="gallery-other-panel" tabindex="-1" data-gallery-view="other">其他图片</button>
    <button type="button" id="gallery-private-tab" role="tab" aria-selected="false" aria-controls="gallery-private-panel" tabindex="-1" data-gallery-view="private">个照合照 <svg class="tab-lock" viewBox="0 0 16 18" fill="none" stroke="currentColor" aria-hidden="true"><rect x="2" y="8" width="12" height="9" rx="2"/><path d="M4 8V5a4 4 0 0 1 8 0v3"/></svg></button>
  </div>
<section class="wrap travel-gallery" id="gallery-travel-panel" role="tabpanel" aria-labelledby="gallery-travel-tab">
  <div class="travel-heading"><h2 id="travel-title" class="sr-only">旅行足迹</h2><p class="gallery-totals"><span id="place-total">{len(set(p["province_id"] for p in places))}</span> 个地区 <span aria-hidden="true">·</span> <span id="photo-total">{count}</span> 张照片</p></div>
  <div class="travel-layout">
    <figure class="travel-map">
      <div class="interactive-map-shell">
        {atlas_svg}
        <p id="map-status" class="sr-only" role="status" hidden></p>
        <div class="atlas-hover" id="atlas-hover" hidden></div>
        <div class="map-actions"><button type="button" id="map-overview" aria-label="全国总览" title="全国总览"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="m3 10 9-7 9 7M6 9v12h12V9m-9 12v-7h6v7"/></svg></button><button type="button" id="map-expand" aria-label="展开地图" title="展开地图"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg></button><span aria-hidden="true"></span><button type="button" id="map-zoom-in" aria-label="放大地图">＋</button><button type="button" id="map-zoom-out" aria-label="缩小地图">−</button></div>
      </div>
      <figcaption><a href="https://cloudcenter.tianditu.gov.cn/administrativeDivision/" target="_blank" rel="noopener noreferrer">边界数据 · 天地图 ↗</a><span class="atlas-legend"><span><i class="legend-visited" aria-hidden="true"></i>已收录照片</span><span><i class="legend-selected" aria-hidden="true"></i>已选择</span></span><span>点击省份查看相册 · 再次点击取消</span></figcaption>
    </figure>
    <aside class="travel-places" aria-label="已收录相册的地区"><div class="place-options" id="place-options"><button type="button" class="place-option is-selected" data-province="" aria-pressed="true">全部相册 <span>{count}</span></button></div></aside>
  </div>
  <section class="gallery-results" aria-labelledby="gallery-selection">
    <div class="gallery-results-head"><div><h2 id="gallery-selection">旅行相册</h2><p id="gallery-result-count" role="status" aria-live="polite">{count} 张照片</p></div><button type="button" class="gallery-reset" id="gallery-reset" hidden>全部相册 ×</button></div>
    <div class="gallery-albums" id="gallery-albums"></div><section class="pending-cities" id="pending-cities" aria-label="待出发的城市" hidden><p id="pending-city-names"></p><p class="pending-caption">待出发</p></section>
    <div class="gallery-empty" id="gallery-empty"><svg width="42" height="36" viewBox="0 0 42 36" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><rect x="2" y="2" width="38" height="31" rx="2"/><circle cx="29" cy="12" r="3"/><path d="m3 27 10-12 12 16m-5-8 5-6 14 14"/></svg><h3 id="gallery-empty-title">照片还在整理中</h3><p id="gallery-empty-text">旅行照片会陆续收录在这里。</p></div>
    <noscript><p>请启用 JavaScript 浏览地点与照片。</p></noscript>
  </section>
</section>
<section class="wrap other-gallery" id="gallery-other-panel" role="tabpanel" aria-labelledby="gallery-other-tab" hidden>
  <p class="extra-photo-count" id="other-photo-count" role="status"></p><div class="photo-grid" id="other-photo-grid"></div>
  <div class="gallery-empty" id="other-empty"><h2>这里还没有照片</h2><p>留给旅行之外的日常与瞬间。</p></div>
</section>
<section class="wrap other-gallery private-gallery" id="gallery-private-panel" role="tabpanel" aria-labelledby="gallery-private-tab" hidden>
  <div class="private-gate" id="private-gate">
    <svg class="private-lock-icon" width="32" height="38" viewBox="0 0 32 38" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><rect x="4" y="16" width="24" height="20" rx="3"/><path d="M9 16V9a7 7 0 0 1 14 0v7"/><path d="M16 24v5"/></svg>
    <h2>个照合照</h2><p>输入密码后查看相册。</p>
    <form id="private-unlock-form"><label class="sr-only" for="private-password">相册密码</label><div class="private-password-row"><input id="private-password" name="password" type="password" autocomplete="off" placeholder="相册密码" required maxlength="256" aria-describedby="private-status"><button type="submit" id="private-unlock">解锁相册</button></div></form>
    <p id="private-status" class="private-status" role="status" aria-live="polite"></p>
  </div>
  <div id="private-content" hidden><div class="private-gallery-heading"><p id="private-photo-count"></p><button type="button" id="private-lock">重新锁定</button></div><p class="private-session-note">离开此相册后会重新上锁。</p><div class="photo-grid" id="private-photo-grid"></div></div>
</section>
  <dialog class="gallery-lightbox" id="gallery-lightbox" aria-label="照片查看器" aria-describedby="lightbox-caption"><div class="lightbox-toolbar"><span id="lightbox-position" aria-live="polite"></span><button type="button" id="lightbox-close" autofocus aria-label="关闭照片">关闭 ×</button></div><div class="lightbox-stage"><button type="button" id="lightbox-prev" aria-label="上一张照片">←</button><img id="lightbox-image" alt=""><button type="button" id="lightbox-next" aria-label="下一张照片">→</button></div><p id="lightbox-caption"></p></dialog>
  <script type="application/json" id="travel-gallery-data">{client}</script><script type="module" src="/gallery.js"></script>
</div>'''
