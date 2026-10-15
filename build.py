"""Build the blog from an explicit, reviewed content allowlist."""
from pathlib import Path
import sys, re, json, html, hashlib, subprocess, base64, urllib.request
import markdown
from bs4 import BeautifulSoup
from PIL import Image

SITE = Path(__file__).resolve().parent
from site_io import write
config=json.loads((SITE/'site.json').read_text(encoding='utf-8'))
for asset in (SITE/'static').rglob('*'):
    if asset.is_file(): write('dist/'+asset.relative_to(SITE/'static').as_posix(),asset.read_bytes())

def md(source):
    math = []
    def save(m):
        math.append(m.group(0))
        return 'MATHPLACEHOLDER' + str(len(math)-1) + 'END'
    source = re.sub(r'\$\$[\s\S]+?\$\$|(?<!\$)\$(?!\$)[^\n$]+?\$', save, source)
    result = markdown.markdown(source, extensions=['tables','fenced_code','toc'])
    for i, formula in enumerate(math):
        display = formula.startswith('$$')
        tex = formula[2:-2] if display else formula[1:-1]
        tag = 'div' if display else 'span'
        out = f'<{tag} class="math {"display" if display else "inline"}" data-tex="{html.escape(tex.strip(), quote=True)}">{html.escape(tex)}</{tag}>'
        result = result.replace(f'<p>MATHPLACEHOLDER{i}END</p>', out) if display else result
        result = result.replace(f'MATHPLACEHOLDER{i}END', out)
    return result

articles = sorted(json.loads((SITE / 'wechat-articles.json').read_text(encoding='utf-8')), key=lambda a: (a['date'], a['published_original']), reverse=True)
course_repo = json.loads((SITE / 'course-repository.json').read_text(encoding='utf-8'))
for article in articles:
    content = (SITE / article['content_file']).read_bytes()
    if hashlib.sha256(content).hexdigest() != article['body_sha256']:
        raise ValueError('公众号原文与已核对版本不符，请复核来源')
    article['body'] = content.decode('utf-8')
    for image in article.get('images', []):
        image_bytes = (SITE / image['file']).read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != image['sha256']:
            raise ValueError('公众号配图与核对版本不符')
        write('dist/' + image['deployed_path'], image_bytes)

projects = [
 {'name':'有色智研','en':'ZhiKuang Industry Research','description':'把财报利润桥、五维评分与经营情景，放进一条可追查的公司研究流程。','tags':['Python','Gradio','AI Agent'],'role':'比赛项目参与 · AI 辅助开发','url':'https://github.com/flamingo15490/zhikuang-industry-research','other':'https://github.com/flamingo15490/nonferrous-metals-research','type':'研究工具','image':'assets/research.webp','detail':'研究池配置为 140 家 A 股有色公司；模型负责工具选择与文字组织，数值由确定性函数计算。研究辅助原型，结论需核验数据与假设。'},
 {'name':'北大社团展位查询平台','en':'PKU Club Map','description':'让校园里的相遇更简单：把社团展位查询从线下搬到线上。','tags':['校园工具','交互地图'],'role':'主持搭建 · 需求、数据结构与功能迭代','url':'https://github.com/lcpu-club/pkuclub-map','type':'校园实践','symbol':'校园 × 地图','color':'sage','detail':'依据个人项目记录，平台累计浏览量 1 万+；域名部署由合作同学协助完成。访问量为个人记录，未另作外部核验。'},
 {'name':'airi-nahida','en':'A local-first desktop companion','description':'基于 AIRI 的个性化桌面伙伴，连接外部记忆、角色设定与受控的主动交互。','tags':['TypeScript','AIRI','桌面应用'],'role':'个人定制开发 · 基于上游 AIRI','url':'https://github.com/flamingo15490/airi-nahida','type':'个人应用','symbol':'hello, world.','color':'sand','detail':'保留上游框架与外部服务架构，围绕稳定性、记忆读写和主动交互的边界持续迭代。'},
 {'name':'Relife-CheckIn','en':'Make everyday progress visible','description':'把日常任务变成经验值，用等级、成就与自定义奖励记录一点点进步。','tags':['Flutter','Dart','SQLite'],'role':'个人项目 · AI 辅助开发','url':'https://github.com/flamingo15490/Relife-CheckIn','type':'个人应用','symbol':'+ 100 XP','color':'rose','detail':'Android 习惯打卡应用，包含自定义任务维度、经验等级、奖励商店、统计和成就系统。'},
 {'name':'山河战国','en':'Mountains & Rivers · The Warring States','description':'以战国七雄为背景的轻量级 4X 策略游戏，探索地形、资源与合纵连横。','tags':['Godot','GDScript','合作项目'],'role':'合作项目 · 负责代码写作','url':'https://github.com/52HZ-GGG/Mountains_Rivers-The_Warring_States','type':'游戏探索','symbol':'山 河 战 国','color':'blue','detail':'强调山川天堑与百家争鸣。个人参与方式以本地已确认项目记录为据，不将合作成果表述为独立完成。'},
 {'name':'Personal Course Materials','en':'Learn, practice, keep a record','description':'整理课程作业与实践，把学习过程留下来，也让后续复习有迹可循。','tags':['Python','课程实践','Notebook'],'role':'个人课程资料整理','url':'https://github.com/flamingo15490/Personal-Course-Materials','type':'代码实践','symbol':'learn / build','color':'paper','detail':'公开仓库入口。具体课程目录与内容以仓库为准，博客不复制第三方整套讲义。'},
]

project_media = json.loads((SITE / 'project-media.json').read_text(encoding='utf-8'))
for project in projects:
    project['gallery'] = project_media.get(project['url'], [])
    for media in project['gallery']:
        media_bytes = (SITE / media['file']).read_bytes()
        if hashlib.sha256(media_bytes).hexdigest() != media['sha256']:
            raise ValueError('项目图片与核对版本不一致')
        write('dist/' + media['file'], media_bytes)

ORIGIN = config['origin'].rstrip('/')
arrow = '<span aria-hidden="true">↗</span>'
contact_email = config.get('contact_email','')
email_link = html.escape(contact_email, quote=True) if contact_email else ''
write('dist/assets/avatar.jpg', (SITE / 'assets/avatar.jpg').read_bytes())
def shell(title, body, active='home', description='告木的个人博客。随笔、课程资料与项目记录。'):
    nav=''.join(f'<a class="{"active" if active==key else ""}" href="{link}">{text}</a>' for key,link,text in [('home','/','首页'),('writing','/writing.html','文章'),('courses','/courses.html','课程资料'),('projects','/projects.html','项目'),('gallery','/gallery.html','画廊'),('about','/about.html','关于我')])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f8f7f3">{chr(60)+'meta name="referrer" content="strict-origin-when-cross-origin"'+chr(62) if active=='gallery' else ''}<title>{html.escape(title)} · 告木</title><meta name="description" content="{html.escape(description)}"><meta property="og:title" content="{html.escape(title)} · 告木"><meta property="og:description" content="{html.escape(description)}"><meta property="og:type" content="website"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/assets/katex/katex.min.css"><script defer src="/assets/katex/katex.min.js"></script><script defer src="/app.js"></script></head><body><a class="skip" href="#main">跳到正文</a><header class="site-header"><div class="header-inner"><a href="/" class="brand"><span>告木</span></a><button class="menu-button" aria-label="展开导航" aria-expanded="false">菜单 <span>☰</span></button><nav aria-label="主导航">{nav}</nav></div></header><main id="main">{body}</main><footer class="minimal-footer"><span>© 2026 告木</span></footer></body></html>'''

def article_card(a, featured=False):
    return f'''<a class="journal-row" href="/posts/{a['slug']}.html"><div class="journal-meta"><span>{a['date'].replace('-', '.')}</span><span>{a['category']}</span></div><div class="journal-copy"><h3>{html.escape(a['title'])}</h3><p>{html.escape(a['summary'])}</p><span class="journal-source">微信公众号 · {html.escape(a['account'])}</span></div><span class="journal-arrow" aria-hidden="true">↗</span></a>'''

def project_card(p, compact=False):
    gallery = p.get('gallery', [])
    preview = ''
    if gallery:
        first = gallery[0]
        preview = f'<a class="project-media actual-preview" href="/{first["file"]}" target="_blank" rel="noopener noreferrer" aria-label="查看{html.escape(p["name"],quote=True)}大图"><img src="/{first["file"]}" alt="{html.escape(p["name"])} · {first["caption"]}" width="{first["width"]}" height="{first["height"]}" loading="lazy"></a><p class="media-credit">{first["caption"]} · {first["source_label"]}</p>'
    thumbnails = ''
    if len(gallery) > 1 and not compact:
        thumbnails = '<div class="project-thumbnails">'+''.join(f'<a href="/{m["file"]}" target="_blank" rel="noopener noreferrer"><img src="/{m["file"]}" alt="{m["caption"]}" width="{m["width"]}" height="{m["height"]}" loading="lazy"><span>{m["caption"]}</span></a>' for m in gallery[1:])+'</div>'
    return f'''<article class="project-card {'no-preview' if not gallery else ''}">{preview}<div class="project-copy"><span class="eyebrow">{p['type']}</span><h3><a href="{p['url']}" target="_blank" rel="noopener noreferrer">{p['name']} {arrow}</a></h3><p>{p['description']}</p><div class="tags">{''.join(f'<span>{t}</span>' for t in p['tags'])}</div><p class="project-role">{p['role']}</p>{'' if compact else f'<p class="project-detail">{p["detail"]}</p>'}{f'<a class="text-link" href="{p["other"]}" target="_blank" rel="noopener noreferrer">相关研究仓库 ↗</a>' if p.get('other') and not compact else ''}{thumbnails}</div></article>'''


def prepare_reading(a):
    body = a['body'] if a.get('format') == 'html' else md(a['body'])
    soup = BeautifulSoup(body, 'html.parser')
    before = re.sub(r'\s+', '', soup.get_text())
    if a['category'] != '诗歌':
        for paragraph in list(soup.find_all('p')):
            pieces = re.split(r'(?:<br\s*/?>\s*){2,}', paragraph.decode_contents())
            if len(pieces) > 1:
                for piece in pieces:
                    fragment = BeautifulSoup(piece, 'html.parser')
                    if not fragment.get_text(strip=True) and not fragment.find('img'):
                        continue
                    replacement = soup.new_tag('p')
                    for child in list(fragment.contents):
                        replacement.append(child.extract())
                    paragraph.insert_before(replacement)
                paragraph.decompose()
    headings = []
    for node in soup.find_all(['p','h2','h3']):
        text = node.get_text(strip=True)
        if node.name in ['h2','h3'] or (len(text)<70 and re.match(r'^\d+[.、．]',text)):
            node.name = 'h2'
            node['id'] = f'read-section-{len(headings)+1}'
            headings.append((node['id'], text))
    outline = ''
    if len(before) >= 1800:
        first = soup.find('p')
        if first:
            first['id'] = 'read-start'
        if len(headings) >= 2:
            links = [('read-start','开篇')] + headings
            label = '本文目录'
        else:
            paragraphs = [n for n in soup.find_all('p') if len(n.get_text(strip=True))>45]
            stride = max(1, (len(paragraphs)+3)//4)
            links = []
            for i,node in enumerate(paragraphs[::stride]):
                node['id'] = f'read-part-{i+1}'
                text = node.get_text(strip=True)
                links.append((node['id'],text[:15]+'…'))
            label = '段落导航'
        if links:
            outline = '<aside class="reading-outline"><details open><summary>'+label+'</summary><nav aria-label="文章目录">'+''.join(f'<a href="#{ident}">{html.escape(label)}</a>' for ident,label in links)+'</nav></details></aside>'
    for image in list(soup.find_all('img')):
        if image.parent.name == 'a':
            continue
        link = soup.new_tag('a',href=image['src'],target='_blank',rel='noopener noreferrer')
        link['class'] = 'article-image-link'
        link['aria-label'] = '查看配图大图'
        image.wrap(link)
    assert before == re.sub(r'\s+', '', soup.get_text()), '阅读排版改变了正文文字'
    return str(soup), outline

hero = f'''<section class="hero wrap"><div class="hero-text"><h1>告木<span class="accent">。</span></h1><p class="hero-identity">北京大学 · 金融科技实验班</p><p class="hero-intro">在北大学习金融，也修读计算机科学与技术双学位。<br>对金融、计算机、数学，以及它们交汇的地方保持好奇。</p><a class="about-entry text-link" href="/about.html">更多关于我 →</a><div class="personal-links"><a href="https://github.com/flamingo15490" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M9 19c-4.3 1.3-4.3-2-6-2.5M15 22v-3.4c0-1 .1-1.4-.5-2 3.4-.4 6.9-1.7 6.9-7.5a5.8 5.8 0 0 0-1.6-4 5.4 5.4 0 0 0-.2-4s-1.3-.4-4.3 1.6a14.6 14.6 0 0 0-7.8 0C4.5.7 3.2 1.1 3.2 1.1a5.4 5.4 0 0 0-.2 4 5.8 5.8 0 0 0-1.6 4c0 5.8 3.5 7.1 6.9 7.5-.6.6-.6 1.2-.6 2V22" transform="translate(1 0) scale(.9)"/></svg><span>GitHub</span><span aria-hidden="true">↗</span></a>{f'<a href="mailto:{email_link}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 6 9 7 9-7"/></svg><span>{email_link}</span></a>' if email_link else ''}</div></div><div class="avatar-column"><img class="hero-avatar" src="/assets/avatar.jpg" width="940" height="940" alt="告木的头像"><p class="profile-signature" aria-label="个性签名预留位置"></p></div></section>'''
home = hero
home += '<section class="section wrap"><div class="section-head"><h2>文章</h2><a class="text-link" href="/writing.html">全部文章 →</a></div><div class="writing-list">'+''.join(article_card(a) for a in articles[:3])+'</div></section>'
home += '<section class="course-band wrap"><div><h2>个人课程资料</h2><p>课程笔记、作业与项目，按课程整理。</p></div><a class="text-link" href="/courses.html">浏览课程资料 →</a></section>'
home += '<section class="section projects-section"><div class="wrap"><div class="section-head"><h2>项目</h2><a class="text-link" href="/projects.html">全部项目 →</a></div><div class="projects-grid">'+''.join(project_card(p,True) for p in projects[:3])+'</div></div></section>'
write('dist/index.html',shell('首页',home))

writing = '<section class="page-head wrap"><h1>文章</h1><p>发表于微信公众号「告木」的文字。</p></section><section class="wrap writing-section"><div class="writing-list">'+''.join(article_card(a) for a in articles)+'</div></section>'
write('dist/writing.html',shell('文章',writing,'writing'))
course_cards = ''.join(f'<a class="course-directory" href="{html.escape(c["url"],quote=True)}" target="_blank" rel="noopener noreferrer"><span>{html.escape(c["name"])}</span><span aria-hidden="true">↗</span></a>' for c in course_repo['directories'])
courses = '<section class="page-head wrap"><h1>个人课程资料</h1><p>本科阶段的课程笔记、作业与项目文件，按课程整理。</p><a class="primary-button course-repo-link" href="'+course_repo['url']+'" target="_blank" rel="noopener noreferrer">打开 GitHub 仓库 ↗</a></section><section class="wrap course-page"><div class="course-directories">'+course_cards+'</div><p class="course-note">资料内容与后续更新以 GitHub 仓库为准。</p></section>'
write('dist/courses.html',shell('课程资料',courses,'courses'))

project_page = '<section class="page-head wrap"><h1>项目</h1></section><section class="wrap project-page"><div class="projects-grid">'+''.join(project_card(p) for p in projects)+'</div><div class="project-disclosure"><h3>关于这些项目</h3><p>多项实践使用 AI 辅助开发。基于上游框架的定制与合作项目均注明参与方式；GitHub 是代码和当前说明的入口。项目资料核对于 2026 年 10 月 15 日，后续更新以各仓库为准。</p></div></section>'
write('dist/projects.html',shell('项目',project_page,'projects'))
from gallery_builder import render_gallery
write('dist/gallery.html',shell('画廊',render_gallery(SITE, write),'gallery','告木的画廊与旅行足迹。'))
write('dist/style.css',(SITE/'style.css').read_bytes())
write('dist/app.js',(SITE/'app.js').read_bytes())
about_text = (SITE / 'about.md').read_text(encoding='utf-8').split('\n', 1)[1]
about = '<section class="about-story wrap"><header class="about-story-head"><img src="/assets/avatar.jpg" alt="告木的头像" width="64" height="64"><h1>关于我</h1></header><article class="about-story-text">'+md(about_text)+'</article></section>'
write('dist/about.html',shell('关于我',about,'about'))
for index, a in enumerate(articles):
    reading_body, outline = prepare_reading(a)
    pagination = '<nav class="article-pagination" aria-label="相邻文章">'
    if index > 0:
        neighbor = articles[index-1]
        pagination += f'<a rel="prev" href="/posts/{neighbor["slug"]}.html"><span>← 上一篇</span><strong>{html.escape(neighbor["title"])}</strong></a>'
    else:
        pagination += '<span aria-hidden="true"></span>'
    if index+1 < len(articles):
        neighbor = articles[index+1]
        pagination += f'<a rel="next" href="/posts/{neighbor["slug"]}.html"><span>下一篇 →</span><strong>{html.escape(neighbor["title"])}</strong></a>'
    else:
        pagination += '<span aria-hidden="true"></span>'
    pagination += '</nav>'
    body = '<div class="reading-progress" aria-hidden="true"></div><section class="post-head wrap"><a class="back-link" href="/writing.html">← 返回文章</a><div class="meta"><span>'+a['category']+'</span><span>'+a['date'].replace('-','.')+'</span><span>微信公众号 · '+html.escape(a['account'])+'</span></div><h1>'+html.escape(a['title'])+'</h1></section><div class="wechat-reading wrap '+('with-outline' if outline else '')+'">'+outline+'<article class="prose wechat-prose">'+reading_body+'<div class="original-link"><a class="text-link" href="'+html.escape(a['source_url'],quote=True)+'" target="_blank" rel="noopener noreferrer">阅读微信原文 ↗</a></div></article>'+pagination+'</div>'
    write('dist/posts/'+a['slug']+'.html',shell(a['title'],body,'writing',a['summary']))
for slug in ['self-attention','fama-macbeth','k-means','cpp-basics']:
    write('dist/posts/'+slug+'.html', '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=/writing.html"><title>文章 · 告木</title><p>此笔记已撤下。<a href="/writing.html">查看文章</a></p></html>')
write('dist/404.html',shell('页面未找到','<section class="page-head wrap"><span class="eyebrow">404 / A LITTLE DETOUR</span><h1>这页还没写到。</h1><p>回到首页，继续翻翻已有的笔记吧。</p><a class="primary-button" href="/">回到首页 →</a></section>'))
write('dist/assets/favicon.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#eee9df"/><text x="16" y="49" fill="#303d32" font-family="Georgia" font-size="50" font-style="italic">g</text><circle cx="45" cy="46" r="5" fill="#b65e43"/></svg>')
write('dist/robots.txt','User-agent: *\nAllow: /\nSitemap: '+ORIGIN+'/sitemap.xml\n')
write('dist/.nojekyll','')
urls=['/','/writing.html','/courses.html','/projects.html','/gallery.html','/about.html']+['/posts/'+a['slug']+'.html' for a in articles]
write('dist/sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+html.escape(ORIGIN+url)+'</loc></url>' for url in urls)+'</urlset>')
print(json.dumps({'articles':len(articles),'course_directories':len(course_repo['directories']),'projects':len(projects)},ensure_ascii=False))
