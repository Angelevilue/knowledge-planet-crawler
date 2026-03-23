# Knowledge Planet Crawler

A Python crawler for [知识星球 (Knowledge Planet)](https://wx.zsxq.com/) - a Chinese knowledge sharing platform.

## Features

- WeChat QR code login via Selenium (or manual cookie import)
- Crawl topics and save as Markdown
- Download images, PDFs, DOCX and other attachments
- **Date range filtering** - crawl topics from specific dates
- Incremental crawling (only new topics)
- Organized by date
- Metadata storage (author, time, likes, comments)
- Automatic retry on API rate limiting

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
```

## Configuration

Edit `config.py` to set your target group ID:

```python
GROUP_ID = "your_group_id_here"
```

## Usage

### 1. Login

**Option A: Selenium QR Code Login (may be blocked by Cloudflare)**
```bash
python main.py login
```

**Option B: Manual Cookie Import (recommended)**
If Cloudflare blocks Selenium, manually export cookies from Chrome:

1. Open Chrome and login to https://wx.zsxq.com/
2. Press F12 → Application → Cookies → https://wx.zsxq.com
3. Copy all cookie names and values
4. Run: `python main.py login --manual`
5. Paste the cookies when prompted

### 2. Crawl Topics

```bash
# Crawl all topics (incremental mode - skips already crawled)
python main.py crawl

# Test mode (limited topics)
python main.py crawl --test

# Specify max count
python main.py crawl --max 100

# Crawl topics from a specific date onwards
python main.py crawl --start-date 2025-01-01

# Crawl topics within a date range
python main.py crawl --start-date 2025-01-15 --end-date 2025-01-15

# Disable incremental mode (re-crawl all, ignores state file)
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
│   │   └── files/           # Downloaded attachments (PDF, DOCX, etc.)
│   └── topic_...
└── 2025-11-20/
    └── ...
```

## Commands

| Command | Description |
|---------|-------------|
| `python main.py login` | Login to Knowledge Planet |
| `python main.py login --manual` | Manual cookie import |
| `python main.py crawl` | Crawl topics (incremental) |
| `python main.py crawl --test` | Test mode (first page only) |
| `python main.py crawl --start-date YYYY-MM-DD --end-date YYYY-MM-DD` | Crawl specific date range |
| `python main.py crawl --no-incremental` | Full re-crawl (ignores state) |
| `python main.py schedule` | Run incremental scheduler |

## How Date Range Filtering Works

**Note:** The Knowledge Planet API does not support direct date filtering. The crawler works by:

1. Fetching topics from newest to oldest using pagination
2. Filtering topics client-side based on your specified date range
3. Continuing to paginate until it passes your target date

This means crawling older dates (e.g., February when starting from March) requires more API calls and time.

## State Management

- `state.json` - Tracks crawled topic IDs to avoid duplicates in incremental mode
- Use `--no-incremental` to ignore state and re-crawl
- To completely reset: `rm state.json`

## Notes

- Cookies expire periodically. Re-login if you get "Unauthorized" errors.
- The API has rate limits - the crawler automatically retries with delays.
- File downloads require valid cookies with proper authentication tokens.
- Be respectful of rate limits when crawling.
- Some files may require manual download if API access is restricted (the crawler will print instructions).

## Troubleshooting

**Login fails with Cloudflare verification**
- The website blocks automated browsers. Use `--manual` to import cookies from your Chrome browser.

**"Unauthorized" errors**
- Your cookies have expired. Update `cookies.json` with fresh cookies from Chrome.

**Empty results**
- Check if GROUP_ID is correct and you have access to the group.
- Verify cookies are valid by checking if you can access the group in Chrome.

**API returns "内部错误" (Internal Error)**
- This is rate limiting. The crawler will automatically retry after a delay.
- Wait a few minutes before trying again.

**Date range filtering not working / wrong dates saved**
- Ensure you're using `--no-incremental` if you deleted output files and want to re-crawl.
- The API pagination may take time to reach older dates - be patient.

**Files not re-crawled after deletion**
- The `state.json` file remembers crawled topic IDs.
- Either use `--no-incremental` flag, or delete `state.json` to reset.

## License

MIT
