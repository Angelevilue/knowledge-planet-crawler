"""
爬虫核心模块 - 知识星球爬虫
获取话题列表和详情
"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

import config
from login import WeChatLogin
from parser import TopicParser
from downloader import FileDownloader
from storage import TopicStorage


class KnowledgePlanetCrawler:
    """知识星球爬虫"""

    def __init__(self, group_id: str = None, cookies: List[dict] = None):
        self.group_id = group_id or config.GROUP_ID
        self.session = requests.Session()
        self.parser = TopicParser()
        self.storage = TopicStorage()

        # 设置请求头
        if cookies:
            login = WeChatLogin()
            self.session.headers.update(login.get_session_headers(cookies))
        else:
            # 尝试加载保存的cookies
            login = WeChatLogin()
            saved_cookies = login.load_cookies()
            if saved_cookies:
                self.session.headers.update(login.get_session_headers(saved_cookies))
            else:
                raise ValueError("需要提供有效的cookies")

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发送HTTP请求，带重试"""
        kwargs.setdefault("timeout", config.REQUEST_TIMEOUT)

        for attempt in range(config.MAX_RETRY):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                print(f"请求失败 (尝试 {attempt + 1}/{config.MAX_RETRY}): {e}")
                if attempt < config.MAX_RETRY - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def get_group_info(self) -> Dict:
        """获取群组信息"""
        url = f"{config.API_BASE_URL}/groups/{self.group_id}"
        response = self._request("GET", url)
        data = response.json()

        group = data.get("resp_data", {}).get("group", {})
        print(f"群组名称: {group.get('name', '未知')}")
        print(f"群组ID: {group.get('group_id', '')}")

        return group

    def get_topics(self, end_time: str = None, count: int = None) -> List[Dict]:
        """
        获取话题列表

        Args:
            end_time: 结束时间 (ISO格式字符串)，用于分页
            count: 每页数量

        Returns:
            话题列表
        """
        count = count or config.PAGE_SIZE
        url = f"{config.API_BASE_URL}/groups/{self.group_id}/topics"

        params = {
            "count": count,
        }

        if end_time:
            # API expects ISO format string like "2026-03-17T22:40:19.324+0800"
            params["end_time"] = end_time

        response = self._request("GET", url, params=params)
        data = response.json()

        if not data.get("succeeded"):
            print(f"API返回错误: {data.get('error', '未知错误')}")

        topics = data.get("resp_data", {}).get("topics", [])
        print(f"获取到 {len(topics)} 条话题")

        return topics

    def get_topic_detail(self, topic_id: str) -> Dict:
        """获取话题详情"""
        url = f"{config.API_BASE_URL}/topics/{topic_id}"
        response = self._request("GET", url)
        data = response.json()

        # resp_data 可能是 {"topic": {...}} 或直接是 {...}
        resp_data = data.get("resp_data", {})
        topic = resp_data.get("topic") or resp_data
        return topic

    def crawl_topic(self, topic: Dict, download_media: bool = True, skip_if_crawled: bool = True) -> Dict:
        """
        爬取单个话题

        Args:
            topic: 话题数据
            download_media: 是否下载媒体文件
            skip_if_crawled: 是否跳过已爬取的话题(用于增量模式)

        Returns:
            解析后的话题数据
        """
        topic_id = topic.get("topic_id") or topic.get("id")

        # 检查是否已爬取
        if skip_if_crawled and self.storage.is_crawled(topic_id):
            print(f"话题 {topic_id} 已爬取，跳过")
            return None

        # 获取详情(如果是列表页数据不够完整)
        if "text" not in topic or "owner" not in topic:
            topic = self.get_topic_detail(topic_id)
            # 检查获取详情是否成功
            if not topic or not topic.get("topic_id"):
                print(f"警告: 无法获取话题 {topic_id} 的详情，跳过")
                return None

        # 解析话题
        parsed = self.parser.parse_topic(topic)

        # 下载媒体文件
        if download_media:
            self._download_media(parsed)

        return parsed

    def _download_media(self, parsed_topic: Dict):
        """下载话题中的媒体文件"""
        topic_id = parsed_topic.get("id")

        # 获取话题目录
        date_dir = self.storage.get_date_dir(parsed_topic.get("created_at"))
        topic_dir = self.storage.get_topic_dir(topic_id, date_dir)

        images_dir = os.path.join(topic_dir, "images")
        files_dir = os.path.join(topic_dir, "files")

        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(files_dir, exist_ok=True)

        # 准备headers
        headers = dict(self.session.headers)

        # 下载图片
        downloader = FileDownloader(headers, topic_dir)
        for img in parsed_topic.get("images", []):
            url = img.get("url")
            if url:
                filename = downloader._extract_filename_from_url(url)
                local_path = downloader.download_image(url, filename)
                if local_path:
                    img["local_path"] = local_path

        # 下载附件
        for file_info in parsed_topic.get("files", []):
            file_id = file_info.get("file_id")
            filename = file_info.get("name", f"file_{file_id}")
            file_hash = file_info.get("hash", "")
            file_size = file_info.get("size", 0)

            # 检查是否已下载
            local_file = os.path.join(files_dir, filename)
            if os.path.exists(local_file):
                print(f"文件已存在，跳过: {filename}")
                file_info["local_path"] = local_file
                continue

            # 获取下载 URL
            download_url = self._get_file_download_url(topic_id, file_id, filename)
            if download_url:
                local_path = downloader.download_document(download_url, filename)
                if local_path:
                    file_info["local_path"] = local_path
            else:
                # 无法自动下载，记录信息供手动下载
                print(f"⚠️ 文件需手动下载: {filename} ({file_size / 1024 / 1024:.1f}MB)")
                print(f"   话题ID: {topic_id}")
                print(f"   文件ID: {file_id}")
                if file_hash:
                    print(f"   Hash: {file_hash}")

    def _get_file_download_url(self, topic_id: str, file_id: str, filename: str) -> str:
        """
        使用 API 获取文件下载 URL

        Args:
            topic_id: 话题ID
            file_id: 文件ID
            filename: 文件名

        Returns:
            文件下载 URL
        """
        try:
            import requests as req

            # 读取 cookies 获取 access_token
            cookies_file = os.path.join(os.path.dirname(__file__), "cookies.json")
            if not os.path.exists(cookies_file):
                print("未找到cookies文件")
                return None

            with open(cookies_file, "r") as f:
                cookies = json.load(f)

            access_token = None
            for cookie in cookies:
                if cookie.get("name") == "zsxq_access_token":
                    access_token = cookie.get("value")
                    break

            if not access_token:
                print("未找到access_token")
                return None

            # 调用API获取下载URL
            url = f"{config.API_BASE_URL}/files/{file_id}/download_url"
            headers = {
                "Cookie": f"zsxq_access_token={access_token}",
                "Referer": "https://wx.zsxq.com/",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            response = req.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get("succeeded"):
                    download_url = data.get("resp_data", {}).get("download_url")
                    if download_url:
                        return download_url
                print(f"API返回: {response.text[:200]}")
            else:
                print(f"获取下载URL失败: {response.status_code}")

            return None

        except ImportError as e:
            print(f"requests库未安装: {e}")
            return None
        except Exception as e:
            print(f"获取文件下载URL失败: {e}")
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """
        解析日期字符串为 datetime 对象

        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS

        Returns:
            datetime 对象
        """
        date_str = date_str.strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"无法解析日期: {date_str}")

    def _topic_in_date_range(self, topic: dict, start_date: datetime = None, end_date: datetime = None) -> bool:
        """
        检查话题是否在指定日期范围内

        Args:
            topic: 话题数据
            start_date: 开始日期（包含）
            end_date: 结束日期（包含）

        Returns:
            是否在范围内
        """
        create_time = topic.get("create_time")
        if not create_time:
            return True

        try:
            from datetime import timezone, timedelta
            import re

            # 处理 ISO 格式: 2026-03-22T13:56:49.224+0800
            # 使用正则表达式解析，不依赖 dateutil
            create_time_str = create_time.replace('+0800', '+08:00')

            # 解析 ISO 格式时间
            # 格式: 2026-03-22T13:56:49.224+08:00
            match = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?([+-]\d{2}:\d{2})?', create_time_str)
            if not match:
                print(f"⚠️ 日期格式无法解析: {create_time}")
                return True

            year, month, day, hour, minute, second = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6))
            microsecond = int(match.group(7).ljust(6, '0')[:6]) if match.group(7) else 0
            tz_str = match.group(8)

            # 创建带时区的时间对象
            if tz_str:
                # 解析时区 +08:00
                tz_sign = 1 if tz_str[0] == '+' else -1
                tz_hours = int(tz_str[1:3])
                tz_minutes = int(tz_str[4:6])
                tz_offset = timedelta(hours=tz_sign * tz_hours, minutes=tz_sign * tz_minutes)
                topic_tz = timezone(tz_offset)
            else:
                topic_tz = timezone(timedelta(hours=8))  # 默认东八区

            topic_date = datetime(year, month, day, hour, minute, second, microsecond, tzinfo=topic_tz)

            # 确保 start_date 和 end_date 是 offset-aware 并使用相同的 +08:00 时区
            if start_date:
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone(timedelta(hours=8)))
            if end_date:
                if end_date.tzinfo is None:
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999,
                                                tzinfo=timezone(timedelta(hours=8)))
                else:
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            if start_date and topic_date < start_date:
                return False
            if end_date and topic_date > end_date:
                return False
            return True
        except Exception as e:
            # 解析失败时打印错误，但仍然返回True以避免丢失数据
            print(f"⚠️ 日期解析失败: {create_time}, 错误: {e}")
            return True

    def crawl_all(self, max_count: int = None, incremental: bool = True,
                  start_date: str = None, end_date: str = None):
        """
        爬取所有话题

        Args:
            max_count: 最大爬取数量
            incremental: 是否增量爬取(只爬取新话题)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
        """
        print("=" * 50)
        print(f"开始爬取群组: {self.group_id}")
        print(f"增量模式: {'是' if incremental else '否'}")

        # 解析日期范围
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = self._parse_date(start_date)
            print(f"开始日期: {start_date}")
        if end_date:
            end_dt = self._parse_date(end_date)
            print(f"结束日期: {end_date}")

        print("=" * 50)

        # 获取群组信息
        self.get_group_info()

        # 如果是增量模式，获取最早的话题时间作为起点
        end_time = None
        if incremental and self.storage.get_crawled_count() > 0:
            print("增量模式：跳过已爬取的话题")

        crawled = 0
        skipped_by_date = 0
        page = 0
        consecutive_empty = 0  # 连续空结果计数

        while True:
            page += 1
            print(f"\n--- 第 {page} 页 ---")

            try:
                topics = self.get_topics(end_time=end_time)

                if not topics:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        print("连续多次获取不到话题，停止爬取")
                        break
                    # 可能是API限流，等待后重试
                    print(f"获取到空结果，等待5秒后重试... (连续空结果: {consecutive_empty})")
                    time.sleep(5)
                    continue
                else:
                    consecutive_empty = 0  # 重置计数

                for topic in topics:
                    topic_id = topic.get("topic_id") or topic.get("id")

                    # 更新分页时间 (每个话题都要更新，避免日期范围过滤时卡在第一页)
                    create_time = topic.get("create_time")
                    if create_time:
                        end_time = create_time

                    # 日期范围过滤
                    if start_dt or end_dt:
                        if not self._topic_in_date_range(topic, start_dt, end_dt):
                            print(f"跳过日期范围外: {topic_id} ({topic.get('create_time', '')})")
                            skipped_by_date += 1
                            continue

                    # 增量模式检查
                    if incremental and self.storage.is_crawled(topic_id):
                        print(f"跳过已爬取: {topic_id}")
                        continue

                    # 爬取话题
                    parsed = self.crawl_topic(topic, skip_if_crawled=incremental)
                    if parsed:
                        # 转换为Markdown
                        md_content = self.parser.topic_to_markdown(parsed)
                        # 保存
                        saved_path = self.storage.save_topic(parsed, md_content)
                        print(f"已保存: {saved_path}")
                        crawled += 1

                    # 检查是否达到最大数量
                    if max_count and crawled >= max_count:
                        print(f"已达到最大数量: {max_count}")
                        return

                # 避免请求过快 - 增加延迟避免API限流
                time.sleep(3)

            except Exception as e:
                print(f"爬取出错: {e}")
                break

        print(f"\n爬取完成! 共爬取 {crawled} 条话题")
        if skipped_by_date > 0:
            print(f"日期范围外跳过: {skipped_by_date} 条")
        print(f"已累计爬取 {self.storage.get_crawled_count()} 条话题")


def main():
    """测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description="知识星球爬虫")
    parser.add_argument("--group", type=str, default=config.GROUP_ID, help="群组ID")
    parser.add_argument("--test", action="store_true", help="测试模式(只爬取一页)")
    parser.add_argument("--max", type=int, default=None, help="最大爬取数量")

    args = parser.parse_args()

    crawler = KnowledgePlanetCrawler(group_id=args.group)

    if args.test:
        # 测试模式：只爬取一页
        topics = crawler.get_topics()
        print(f"获取到 {len(topics)} 条话题")
        if topics:
            topic = topics[0]
            parsed = crawler.crawl_topic(topic)
            print(parsed)
    else:
        crawler.crawl_all(max_count=args.max)


