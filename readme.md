# 多种文档下载器

适用于下载豆丁、道客巴巴、淘豆网、原创力（book118）、新浪爱问、金锄头这些站点里**可以自由预览**的文档，抓到的图片会拼成 PDF。

> 只处理公开预览内容；需要登录、付费、拖动滑块才能继续阅读的页面不做绕过。

## 环境要求

- Python 3.9+
- Chrome（推荐最新稳定版，程序会自动匹配对应驱动）

```bash
pip install -r requirements.txt
```

## 用法

```bash
# 交互式，循环输入网址
python docDownloader.py

# 直接处理一个网址
python docDownloader.py https://www.docin.com/p-xxxxxxxx.html
```

下载的图片在 `temp/<文档标题>/`，生成的 PDF 在 `output/<文档标题>.pdf`。

## 驱动管理（本次重写）

旧版本仓库里内置的是 Chrome 89 时代的 `chromedriver.exe`，浏览器一升级就报
`SessionNotCreatedException`。现在改为自动匹配：

1. 读取本机 Chrome 版本（注册表 `BLBeacon`，失败则读 exe 文件版本）；
2. 命中 `%LOCALAPPDATA%\doc_downloader\driver\` 缓存则复用；
3. 否则从 npmmirror 的 chrome-for-testing 镜像下载同主版本驱动；
4. 都失败时退回 Selenium Manager。

可用环境变量：

| 变量 | 作用 |
|---|---|
| `CHROMEDRIVER` | 直接指定 chromedriver 路径，跳过全部探测 |
| `CHROMEDRIVER_MIRROR` | 替换驱动下载镜像 |

单独检查驱动状态：

```bash
python driver_setup.py
```

## 各站点当前状态（2026-10-27 实测）

| 站点 | 状态 | 说明 |
|---|---|---|
| 道客巴巴 doc88 | ⚠️ 受限 | 阅读器改版为「单页 canvas + 拖动滑块解锁」，未解锁只剩第 1 页；程序会识别并明确退出 |
| 豆丁 docin | ⚠️ 受限 | 图床 `docimg1.docin.com` 对批量取图返回 `204` 空响应（防盗链），程序会报错而不是写 0 字节文件 |
| 原创力 book118 | ⚠️ 待适配 | 页面改为前端渲染，`webpreview-item` 等选择器已失效 |
| 淘豆 taodocs | ⚠️ 待适配 | 页面结构变更，选择器需重新确认 |
| 金锄头 jinchutou | ⚠️ 待适配 | 链接结构变为 `/shtml/...`，原 id 规则失效 |
| 新浪爱问 ishare | ❌ 站点已下线 | 返回 502 |

## 本次修复内容

- 全量迁移到 Selenium 4 API（`find_element(By.*)`、`Service`），删除 `executable_path` / `chrome_options` 等已移除参数
- 删除内置 `chromedriver.exe`，改为按浏览器版本自动下载并缓存
- 新增 `utils.py`：Windows 非法文件名清洗、目录准备、带重试与 http 回退的下载、图片有效性校验
- `img2pdf` 按数字顺序排序（`1,2,10` 而不是 `1,10,2`），空目录给出明确错误
- `img.py` 修复 `time.clock()`（Python 3.11 起移除）与 `Image.ROTATE_*`（Pillow 10 起改为 `Image.Transpose`）
- `docDownloader.py` 支持直接传 URL；单条链接失败不再中断整个循环
- 各模块统一 `finally: driver.quit()`，异常时不再残留 Chrome 进程
- 依赖升级：selenium 4.51 / Pillow 13 / reportlab 5.1

## 已知限制

- 站点改版频繁，选择器失效属于常态；失败时会打印具体原因而不是静默产出空 PDF。
- 新浪爱问的 SVG 需要 `svg2png`（Node）或 `cairosvg`（Python）才能转换，二选一安装。
