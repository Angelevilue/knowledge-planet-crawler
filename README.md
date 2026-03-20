# Knowledge Planet Crawler

A Python crawler for [知识星球 (Knowledge Planet)](https://wx.zsxq.com/) - a Chinese knowledge sharing platform.

## Features

- WeChat QR code login (via Selenium)
- Crawl topics and save as Markdown
- Download images and attachments
- Incremental crawling (only new topics)
- Organized by date
- Metadata storage (author, time, likes, comments)

## Requirements

- Python 3.12+
- Chrome/Chromium browser
- Conda (recommended)

## Installation

```bash
# Create conda environment
conda create -n knowledge_planet python=3.12 -y
conda activate knowledge_planet

# Install dependencies
pip install -r requirements.txt

# Install ChromeDriver (automatic via webdriver-manager)
```

## Configuration

Edit `config.py` to set your target group ID:

```python
GROUP_ID = "your_group_id_here"
```

## Usage

### 1. Login

```bash
python main.py login
```

A Chrome window will open. Scan the QR code with WeChat to login. Cookies will be saved to `cookies.json`.

### 2. Crawl Topics

```bash
# Crawl all topics (full run)
python main.py crawl

# Test mode (limited topics)
python main.py crawl --test

# Specify max count
python main.py crawl --max 100

# Disable incremental mode
python main.py crawl --no-incremental
```

### 3. Schedule Incremental Updates

```bash
# Run scheduler (check every hour by default)
python main.py schedule

# Custom interval (in seconds)
python main.py schedule --interval 3600
```

## Output Structure

```
output/
├── 2025-11-21/
│   ├── topic_12345678901234/
│   │   ├── content.md       # Markdown content
│   │   ├── metadata.json    # Topic metadata
│   │   ├── images/          # Downloaded images
│   │   └── files/           # Downloaded files
│   └── topic_...
└── 2025-11-20/
    └── ...
```

## Commands

| Command | Description |
|---------|-------------|
| `python main.py login` | Login to Knowledge Planet |
| `python main.py crawl` | Crawl topics |
| `python main.py schedule` | Run incremental scheduler |

## Notes

- Cookies expire periodically. Re-run login if you get "Unauthorized" errors.
- Some topics may fail to fetch due to API limitations - these are skipped automatically.
- Be respectful of rate limits when crawling.

## Troubleshooting

**Login fails with Cloudflare verification**
- The website may block automated browsers. Try using `--existing` flag to use your existing browser profile.

**"Unauthorized" errors**
- Your cookies have expired. Run `python main.py login` again.

**Empty results**
- Check if GROUP_ID is correct and you have access to the group.
