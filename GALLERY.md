# 画廊

画廊分为「旅行足迹」与「其他图片」。旅行按省份筛选、按市名展示相册。再次点击所选省份取消筛选；暂无照片的城市统一列出并显示「待出发」。收录状态不等于完整旅行经历。

## 照片

目前旅行相册有59张照片、6个省级地区、8个相册。原图不进入此仓库或发布包。

使用 Pillow 校正 EXIF 方向，转换为 RGB，去除 EXIF/XMP，生成 WebP：

| 用途 | 最长边 | 初始质量 |
|---|---:|---:|
| 小缩略图 | 400px | 66 |
| 大缩略图 | 800px | 72 |
| 查看器 | 1600px | 80 |

按体积逐步降低质量，有最低质量限制。页面使用 srcset、懒加载与异步解码；进入相册只加载缩略图，打开照片时才加载查看器图片。不根据文件名或元数据推断日期。

`other-gallery.json` 的 photos 数组沿用旅行照片的完整条目格式。没有照片时显示空状态；填充后共用缩略图、键盘翻页及查看器。

## 地图来源

官方公开可视化页面：https://cloudcenter.tianditu.gov.cn/administrativeDivision/

省界数据：https://cloudcenter.tianditu.gov.cn/api/portal/region/map?gb=156000000&level=2

城市名称与层级：https://cloudcenter.tianditu.gov.cn/api/portal/region/menu

省界原文件：`assets/gallery/china-provinces.geojson`，SHA256：`aebcd73acc1bae5ca7161a5cd87b2c61e0387984c959a2c84c237e33f161f613`。

34个省级多面和8个境界线要素完整参与生成，包括台湾、海岛与海上断续线，保持原始边界，不抽稀坐标。使用 Albers 投影，省界和城市名称预先存放在仓库，浏览时不访问在线地图服务、不使用 Key。官方可视化页面标注数据时间为2025年9月。

图面标注数据出处，不将原地图或旧 SDK 的审图号当作本次自定义成图的审图结论。
