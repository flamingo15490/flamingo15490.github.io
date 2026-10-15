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
