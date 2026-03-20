"""
配置文件 - 知识星球爬虫
"""
import os

# 基础配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.json")
STATE_FILE = os.path.join(BASE_DIR, "state.json")

# 群组ID (需要修改为实际的知识星球群组ID)
GROUP_ID = "51111552522544"

# API配置
API_BASE_URL = "https://api.zsxq.com/v2"
LOGIN_URL = "https://wx.zsxq.com/"

# 请求配置
REQUEST_TIMEOUT = 30
MAX_RETRY = 3
PAGE_SIZE = 20

# 下载配置
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE = 8192

# 增量更新配置
DEFAULT_CHECK_INTERVAL = 3600  # 1小时检查一次
