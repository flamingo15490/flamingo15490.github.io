# 告木的博客

个人文章、课程资料、项目与画廊。独立静态网站，无须 Sites 发布工具或服务器数据库。

正式地址：https://flamingo15490.github.io/

## 本地预览

需要 Python 3.12 或更新版本。

```sh
python -m pip install -r requirements.txt
python build.py
python -m http.server 8767 --directory dist
```

打开 http://localhost:8767/ 。`dist/` 是生成目录，不提交。构建不读取任何个人资料数据库，也不需要 API Key。

## 内容维护

- `site.json`：站名、正式域名和公开联系邮箱。
- `about.md`：个人简介。
- `wechat-articles.json`、`content/wechat/`：文章来源、原文、校验值与配图。更新文章时同时核对正文哈希。
- `build.py`、`app.js`、`style.css`：页面生成、阅读功能和样式。
- `course-repository.json`、`project-media.json`：课程入口与真实项目图片；项目介绍在 `build.py`。
- `gallery.json`：旅行相册，按省份筛选、按目录中的市名分组。
- `other-gallery.json`：其他图片，格式为 `{"photos":[]}`。照片条目字段与 `gallery.json` 中的照片一致，包含 display/small/medium 路径、尺寸、SHA256 与替代文字；支持可选 caption、date。
- `private-gallery.json`、`assets/gallery/locked/`：个照合照的加密目录与密文。
- `private-viewer.js`：浏览器密码派生、解密与会话内照片 URL 管理。
- `GALLERY.md`：照片处理与地图来源说明。

原图放在仓库之外，或已忽略的 `.local/travel-photos/省份/市名（可选）/图片`。只提交优化后的副本：

```sh
python import_travel_photos.py --source /path/to/travel-photos
python build.py
```

导入会更新 `gallery.json` 与 `assets/gallery/photos/`，原图保持不变。它会根据这次来源文件夹重建旅行目录，请使用完整的旅行照片目录。

## 发布

推送到 `main` 后，GitHub Actions 自动构建并部署到 GitHub Pages。工作流只上传 `dist/`，部署成功才会更新网站。也可在 Actions 手动运行 Deploy blog。

Claude Code、Cursor 或任何能修改此仓库的工具均可维护；使用仓库协作者已有的 GitHub 权限推送即可，不需要 Sites 账号。

文章、个人照片及头像的著作权归各自权利人所有。第三方资源来源见 `SOURCES.md`、`GALLERY.md` 和 `THIRD_PARTY.md`。

## 其他图片与个照合照

两者是独立画廊，与旅行省份筛选分开。安装导入依赖后，指定仓库外的原图目录：

```sh
python -m pip install -r requirements-import.txt
python import_extra_photos.py --other /path/to/other-photos
python import_extra_photos.py --private /path/to/private-photos --password-file .local/画廊密码.txt
python build.py
```

`.local/画廊密码.txt` 仅本地保存，不提交、不进入 dist。密码不传给网页服务器，浏览器不将密码或密钥写入 localStorage/sessionStorage。使用本人设置的至少20字符强密码，或用 `secrets.token_urlsafe(24)` 生成。导入器不会覆盖密码。

个照合照使用 PBKDF2-HMAC-SHA256（600,000次、随机16字节盐）派生256位密钥，使用 AES-GCM 加密每个缩略图、大图和相册目录。每个文件独立随机12字节nonce，文件路径用作附加认证数据；公开文件名随机，不含原始文件名或原图哈希。网页只有密文，解锁后在浏览器内存中生成照片URL。离开该分类、重新锁定或刷新后需要重新输入密码；锁定会取消请求、清空网格并释放已解密URL。大图仅在点击时解密。

解锁者可以保存照片。这是公开静态站的密码加密相册，不提供逐人授权或服务端访问日志。更换密码需使用原图重新导入和发布；公开Git历史中已存在的旧密文仍可能用旧密码解密，因此密码轮换不撤销已经分发的旧照片或旧密码。

构建无需密码或 cryptography，只校验并复制密文。原图、密码、导入明细与测试凭据必须放在仓库外或 `.local/`。不要把私密照片放入 `assets/gallery/photos/` 或 `static/`。
