"""
爬虫核心模块 - 知识星球爬虫
获取话题列表和详情
"""
import time
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

    def get_topics(self, end_time: int = None, count: int = None) -> List[Dict]:
        """
        获取话题列表

        Args:
            end_time: 结束时间戳(毫秒)，用于分页
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
            params["end_time"] = end_time

        response = self._request("GET", url, params=params)
        data = response.json()

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

    def crawl_topic(self, topic: Dict, download_media: bool = True) -> Dict:
        """
        爬取单个话题

        Args:
            topic: 话题数据
            download_media: 是否下载媒体文件

        Returns:
            解析后的话题数据
        """
        topic_id = topic.get("topic_id") or topic.get("id")

        # 检查是否已爬取
        if self.storage.is_crawled(topic_id):
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
        for file in parsed_topic.get("files", []):
            url = file.get("url")
            if url:
                filename = file.get("name", downloader._extract_filename_from_url(url))
                local_path = downloader.download_document(url, filename)
                if local_path:
                    file["local_path"] = local_path

    def crawl_all(self, max_count: int = None, incremental: bool = True):
        """
        爬取所有话题

        Args:
            max_count: 最大爬取数量
            incremental: 是否增量爬取(只爬取新话题)
        """
        print("=" * 50)
        print(f"开始爬取群组: {self.group_id}")
        print(f"增量模式: {'是' if incremental else '否'}")
        print("=" * 50)

        # 获取群组信息
        self.get_group_info()

        # 如果是增量模式，获取最早的话题时间作为起点
        end_time = None
        if incremental and self.storage.get_crawled_count() > 0:
            print("增量模式：跳过已爬取的话题")

        crawled = 0
        page = 0

        while True:
            page += 1
            print(f"\n--- 第 {page} 页 ---")

            try:
                topics = self.get_topics(end_time=end_time)

                if not topics:
                    print("没有更多话题了")
                    break

                for topic in topics:
                    topic_id = topic.get("topic_id") or topic.get("id")

                    # 增量模式检查
                    if incremental and self.storage.is_crawled(topic_id):
                        print(f"跳过已爬取: {topic_id}")
                        continue

                    # 爬取话题
                    parsed = self.crawl_topic(topic)
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

                    # 更新分页时间
                    create_time = topic.get("create_time")
                    if create_time:
                        end_time = create_time

                # 避免请求过快
                time.sleep(1)

            except Exception as e:
                print(f"爬取出错: {e}")
                break

        print(f"\n爬取完成! 共爬取 {crawled} 条话题")
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


# 导入os
import os
