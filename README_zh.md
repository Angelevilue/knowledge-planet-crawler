# 知识星球爬虫

用于爬取[知识星球](https://wx.zsxq.com/)内容的 Python 爬虫。

## 功能特点

- 微信扫码登录（Selenium）
- 爬取话题并保存为 Markdown 格式
- 下载图片和附件
- 增量爬取（只爬取新话题）
- 按日期分类存储
- 元数据存储（作者、时间、点赞数、评论数）

## 环境要求

- Python 3.12+
- Chrome/Chromium 浏览器
- Conda（推荐）

## 安装

```bash
# 创建 conda 环境
conda create -n knowledge_planet python=3.12 -y
conda activate knowledge_planet

# 安装依赖
pip install -r requirements.txt

# ChromeDriver 会自动通过 webdriver-manager 安装
```

## 配置

编辑 `config.py` 设置目标群组 ID：

```python
GROUP_ID = "你的群组ID"
```

## 使用方法

### 1. 登录

```bash
python main.py login
```

会打开 Chrome 窗口，用微信扫描二维码登录。Cookies 会保存到 `cookies.json`。

### 2. 爬取话题

```bash
# 爬取全部话题
python main.py crawl

# 测试模式（限制数量）
python main.py crawl --test

# 指定最大数量
python main.py crawl --max 100

# 禁用增量模式
python main.py crawl --no-incremental
```

### 3. 定时增量更新

```bash
# 启动调度器（默认每小时检查一次）
python main.py schedule

# 自定义检查间隔（秒）
python main.py schedule --interval 3600
```

## 输出结构

```
output/
├── 2025-11-21/
│   ├── topic_12345678901234/
│   │   ├── content.md       # Markdown 内容
│   │   ├── metadata.json    # 话题元数据
│   │   ├── images/          # 下载的图片
│   │   └── files/           # 下载的附件
│   └── topic_...
└── 2025-11-20/
    └── ...
```

## 命令一览

| 命令 | 说明 |
|------|------|
| `python main.py login` | 登录知识星球 |
| `python main.py crawl` | 爬取话题 |
| `python main.py schedule` | 启动增量调度器 |

## 注意事项

- Cookies 会定期过期。如果遇到 "Unauthorized" 错误，需要重新登录。
- 部分话题可能因 API 限制获取失败，程序会自动跳过。
- 爬取时请尊重速率限制。

## 故障排除

**登录遇到 Cloudflare 验证**
- 网站可能阻止自动化浏览器。可尝试使用 `--existing` 参数使用已有的浏览器配置文件。

**"Unauthorized" 错误**
- 你的 cookies 已过期。重新运行 `python main.py login`。

**结果为空**
- 检查 GROUP_ID 是否正确，以及你是否有该群组的访问权限。
