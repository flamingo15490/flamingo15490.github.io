"""Render official, unsimplified provincial geometry as a self-contained SVG."""
import json, math, html, hashlib

def build_atlas(site, config):
    raw=(site/config['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==config['sha256'], '矢量边界与已核对来源不符'
    features=json.loads(raw)['features']
    assert len(features)==42
    provinces=[f for f in features if f['geometry']['type']=='MultiPolygon']
    assert len(provinces)==34 and any(f['properties']['name']=='台湾省' for f in provinces)
    rad=math.pi/180
    n=(math.sin(25*rad)+math.sin(47*rad))/2
    c=math.cos(25*rad)**2+2*n*math.sin(25*rad)
    rho0=math.sqrt(c-2*n*math.sin(35*rad))/n
    def raw_project(lng,lat):
        rho=math.sqrt(c-2*n*math.sin(lat*rad))/n
        theta=n*(lng-105)*rad
        return rho*math.sin(theta), rho*math.cos(theta)-rho0
    def vertices(cs):
        if isinstance(cs[0],(int,float)): yield cs
        else:
            for item in cs: yield from vertices(item)
    coords=[raw_project(*p[:2]) for f in features for p in vertices(f['geometry']['coordinates'])]
    xmin=min(x for x,y in coords);xmax=max(x for x,y in coords)
    ymin=min(y for x,y in coords);ymax=max(y for x,y in coords)
    width,height=1000,800
    scale=min((width-120)/(xmax-xmin),(height-110)/(ymax-ymin))
    ox=(width-scale*(xmax+xmin))/2;oy=(height-scale*(ymax+ymin))/2
    def project(lng,lat):
        x,y=raw_project(lng,lat);return x*scale+ox,y*scale+oy
    def path(f):
        geometry=f['geometry'];cs=geometry['coordinates'];polygons=geometry['type']=='MultiPolygon'
        lines=[ring for poly in cs for ring in poly] if polygons else cs
        parts=[]
        for line in lines:
            points=[project(*p[:2]) for p in line]
            parts.append('M'+'L'.join(f'{x:.3f},{y:.3f}' for x,y in points)+('Z' if polygons else ''))
        return ''.join(parts)
    def center(f):
        # The largest polygon keeps island groups from pulling province labels offshore.
        best=None
        for polygon in f['geometry']['coordinates']:
            pts=[project(*p[:2]) for p in polygon[0]]
            cross=[a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1])]
            area=sum(cross)
            if abs(area)<1e-8: continue
            x=sum((a[0]+b[0])*v for a,b,v in zip(pts,pts[1:]+pts[:1],cross))/(3*area)
            y=sum((a[1]+b[1])*v for a,b,v in zip(pts,pts[1:]+pts[:1],cross))/(3*area)
            if best is None or abs(area)>best[0]: best=(abs(area),x,y)
        return best[1:]
    def short(name):
        for suffix in ['维吾尔自治区','壮族自治区','回族自治区','自治区','特别行政区','省','市']:
            if name.endswith(suffix): return name[:-len(suffix)]
        return name
    esc=lambda s:html.escape(str(s),quote=True)
    paths=[];labels=[];regions=[]
    for f in provinces:
        p=f['properties'];code=p['gb'];name=p['name'];x,y=center(f)
        points=[project(*p[:2]) for p in vertices(f['geometry']['coordinates'])]
        bounds=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
        paths.append(f'<path d="{path(f)}" data-region="{code}" class="atlas-province" fill-rule="evenodd" tabindex="0" role="button" aria-label="查看{esc(name)}的照片" aria-pressed="false"><title>{esc(name)}</title></path>')
        compact=code in ['156110000','156120000','156310000','156810000','156820000']
        labels.append(f'<g class="atlas-label{ " atlas-label-small" if compact else ""}" data-label-region="{code}" data-label-x="{x:.3f}" data-label-y="{y:.3f}" transform="translate({x:.3f} {y:.3f})"><text text-anchor="middle" dominant-baseline="central">{esc(short(name))}</text></g>')
        regions.append({'id':code,'name':name,'bounds':bounds,'lng':p['lng'],'lat':p['lat']})
    boundaries=[]
    for f in features:
        if f['geometry']['type']=='MultiLineString':
            code=f['properties']['gb']
            cls='atlas-boundary atlas-boundary-special' if code in ['156970000','156980000'] else 'atlas-boundary'
            boundaries.append(f'<path d="{path(f)}" class="{cls}" data-boundary="{code}"/>')
    svg='<svg id="travel-atlas" class="travel-atlas" viewBox="0 0 1000 800" role="group" aria-label="中国旅行地图，34个省级行政区；支持拖动、缩放和地点选择" tabindex="0"><g id="atlas-viewport"><g class="atlas-regions">'+''.join(paths)+'</g><g class="atlas-boundaries">'+''.join(boundaries)+'</g><g class="atlas-labels">'+''.join(labels)+'</g></g></svg>'
    tree=json.loads((site/'sources/china-region-names.json').read_text(encoding='utf-8'))['data'][0]['children']
    municipality={'156110000','156120000','156310000','156500000','156810000','156820000'}
    city_names={p['gb']:[] if p['gb'] in municipality else [{'id':c['gb'],'name':c['name']} for c in p['children']] for p in tree}
    return svg, {'regions':[{'id':r['id'],'name':r['name']} for r in regions],'city_names':city_names}
