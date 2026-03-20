"""
存储模块 - 知识星球爬虫
负责话题数据的持久化存储
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import config


class TopicStorage:
    """话题存储器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.state_file = config.STATE_FILE

        # 创建output目录
        os.makedirs(self.output_dir, exist_ok=True)

        # 加载已爬取话题ID
        self.crawled_ids = self._load_crawled_ids()

    def _load_crawled_ids(self) -> set:
        """加载已爬取的话题ID"""
        if not os.path.exists(self.state_file):
            return set()

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            return set(state.get("crawled_ids", []))
        except Exception:
            return set()

    def _save_crawled_ids(self):
        """保存已爬取的话题ID"""
        state = {
            "crawled_ids": list(self.crawled_ids),
            "last_update": datetime.now().isoformat()
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def is_crawled(self, topic_id: str) -> bool:
        """检查话题是否已爬取"""
        return topic_id in self.crawled_ids

    def mark_crawled(self, topic_id: str):
        """标记话题已爬取"""
        self.crawled_ids.add(topic_id)
        self._save_crawled_ids()

    def get_date_dir(self, created_at: str = None) -> str:
        """
        获取日期目录路径

        Args:
            created_at: 创建时间 (格式: YYYY-MM-DD HH:MM:SS)

        Returns:
            日期目录路径
        """
        if created_at:
            # 从时间字符串提取日期
            date_str = created_at.split(" ")[0]
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        date_dir = os.path.join(self.output_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        return date_dir

    def get_topic_dir(self, topic_id: str, date_dir: str = None) -> str:
        """
        获取话题专属目录

        Args:
            topic_id: 话题ID
            date_dir: 日期目录路径

        Returns:
            话题目录路径
        """
        if date_dir is None:
            date_dir = self.get_date_dir()

        topic_dir = os.path.join(date_dir, f"topic_{topic_id}")
        os.makedirs(topic_dir, exist_ok=True)

        # 创建子目录
        os.makedirs(os.path.join(topic_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(topic_dir, "files"), exist_ok=True)

        return topic_dir

    def save_topic(self, topic: Dict, markdown_content: str = None) -> str:
        """
        保存话题

        Args:
            topic: 解析后的话题数据
            markdown_content: Markdown格式的内容

        Returns:
            保存的文件路径
        """
        topic_id = topic.get("id")
        if not topic_id:
            raise ValueError("话题ID不能为空")

        # 获取日期目录
        date_dir = self.get_date_dir(topic.get("created_at"))

        # 获取话题目录
        topic_dir = self.get_topic_dir(topic_id, date_dir)

        # 保存元数据JSON
        metadata_file = os.path.join(topic_dir, "metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            # 移除大字段，保存元信息
            metadata = {k: v for k, v in topic.items()
                       if k not in ("content",)}
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 保存Markdown内容
        if markdown_content is None:
            from parser import TopicParser
            parser = TopicParser()
            markdown_content = parser.topic_to_markdown(topic)

        md_file = os.path.join(topic_dir, "content.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # 标记已爬取
        self.mark_crawled(topic_id)

        return md_file

    def get_crawled_count(self) -> int:
        """获取已爬取话题数量"""
        return len(self.crawled_ids)

    def get_all_crawled_ids(self) -> List[str]:
        """获取所有已爬取的话题ID"""
        return list(self.crawled_ids)
