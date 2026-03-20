"""
内容解析模块 - 知识星球爬虫
将话题内容转换为Markdown格式
"""
import re
from datetime import datetime
from typing import Dict, List, Optional

from markdownify import markdownify as md

import config


class TopicParser:
    """话题内容解析器"""

    def __init__(self):
        self.downloaded_files = {"images": [], "files": []}

    def parse_text(self, text: str) -> str:
        """解析文本内容，支持HTML转Markdown"""
        if not text:
            return ""

        # 将HTML转换为Markdown
        text = md(text, heading_style="ATX")

        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        return text

    def parse_topic(self, topic: dict) -> Dict:
        """
        解析话题数据

        Args:
            topic: API返回的话题数据

        Returns:
            解析后的话题字典
        """
        parsed = {
            "id": topic.get("topic_id") or topic.get("id"),
            "type": topic.get("type", "talk"),
            "title": self._extract_title(topic),
            "content": self._extract_content(topic),
            "author": self._extract_author(topic),
            "created_at": self._format_time(topic.get("create_time")),
            "updated_at": self._format_time(topic.get("update_time")),
            "images": self._extract_images(topic),
            "files": self._extract_files(topic),
            "likes_count": topic.get("likes_count", 0),
            "comments_count": topic.get("comments_count", 0),
        }

        return parsed

    def _extract_title(self, topic: dict) -> str:
        """提取话题标题"""
        # 问答类型可能有标题
        if topic.get("type") == "question":
            return f"【问答】{topic.get('question', {}).get('title', '未命名问题')}"
        return ""

    def _extract_content(self, topic: dict) -> str:
        """提取话题正文"""
        text = ""

        # talk类型 - 内容在 talk.text
        if topic.get("type") == "talk" and "talk" in topic:
            talk = topic["talk"]
            if talk.get("text"):
                text = self.parse_text(talk["text"])
        # text类型 - 内容在 topic.text
        elif "text" in topic:
            text = self.parse_text(topic["text"])
        # 问答的描述
        elif topic.get("type") == "question" and "question" in topic:
            question = topic["question"]
            if question.get("description"):
                text = self.parse_text(question["description"])

        return text

    def _extract_author(self, topic: dict) -> Dict:
        """提取作者信息"""
        owner = {}
        # talk类型 - owner在 talk.owner
        if topic.get("type") == "talk" and "talk" in topic:
            owner = topic["talk"].get("owner", {})
        else:
            owner = topic.get("owner", {})

        return {
            "id": owner.get("user_id"),
            "name": owner.get("name", "未知用户"),
            "avatar": owner.get("avatar_url", ""),
        }

    def _extract_images(self, topic: dict) -> List[Dict]:
        """提取话题中的图片"""
        images = []

        # 获取文本内容
        text_content = ""
        if topic.get("type") == "talk" and "talk" in topic:
            text_content = topic["talk"].get("text", "")
        elif "text" in topic:
            text_content = topic["text"]
        elif "question" in topic:
            text_content = topic["question"].get("description", "")

        # 从文本中提取图片 (data-src格式)
        if text_content:
            img_pattern = r'<img[^>]+data-src=["\']([^"\']+)["\'][^>]*>'
            for match in re.finditer(img_pattern, text_content):
                images.append({
                    "url": match.group(1),
                    "type": "image"
                })

            # 也尝试 src 格式
            img_pattern2 = r'<img[^>]+src=["\']([^"\']+(?:\.jpg|\.jpeg|\.png|\.gif|\.webp))["\'][^>]*>'
            for match in re.finditer(img_pattern2, text_content):
                url = match.group(1)
                if not any(img["url"] == url for img in images):
                    images.append({
                        "url": url,
                        "type": "image"
                    })

        # 去重
        seen = set()
        unique_images = []
        for img in images:
            if img["url"] not in seen:
                seen.add(img["url"])
                unique_images.append(img)

        return unique_images

    def _extract_files(self, topic: dict) -> List[Dict]:
        """提取话题中的附件"""
        files = []

        # 提取文件信息
        if "texts" in topic:
            for item in topic["texts"]:
                if item.get("type") == "file":
                    files.append({
                        "name": item.get("name", "未知文件"),
                        "url": item.get("url", ""),
                        "size": item.get("size", 0),
                        "type": "file"
                    })

        # 从resource_uris提取
        if "resource_uris" in topic:
            for uri in topic["resource_uris"]:
                if uri.get("type") in ("file", "video", "audio"):
                    files.append({
                        "name": uri.get("name", "未知文件"),
                        "url": uri.get("uri", ""),
                        "size": uri.get("size", 0),
                        "type": uri.get("type")
                    })

        return files

    def _format_time(self, timestamp) -> str:
        """格式化时间戳或ISO时间字符串"""
        if not timestamp:
            return ""

        try:
            # 如果是字符串（ISO格式），直接返回
            if isinstance(timestamp, str):
                # 2025-11-21T12:21:18.194+0800 格式
                dt = datetime.fromisoformat(timestamp.replace('+0800', '+08:00'))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            # 如果是整数，假设是毫秒时间戳
            elif isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp / 1000)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return str(timestamp)
        except Exception:
            return str(timestamp)

    def topic_to_markdown(self, topic: Dict, replace_local: bool = True) -> str:
        """
        将话题转换为Markdown格式

        Args:
            topic: 解析后的话题字典
            replace_local: 是否将远程URL替换为本地相对路径

        Returns:
            Markdown格式的字符串
        """
        lines = []

        # 标题
        if topic.get("title"):
            lines.append(f"# {topic['title']}")
            lines.append("")

        # 元信息
        author = topic.get("author", {})
        lines.append(f"**作者**: {author.get('name', '未知')}")
        lines.append(f"**时间**: {topic.get('created_at', '')}")
        lines.append(f"**点赞**: {topic.get('likes_count', 0)} | **评论**: {topic.get('comments_count', 0)}")
        lines.append("")

        # 正文内容
        content = topic.get("content", "")
        if content:
            lines.append(content)
            lines.append("")

        # 图片
        images = topic.get("images", [])
        if images:
            lines.append("## 图片")
            for img in images:
                if replace_local:
                    # 生成相对路径
                    filename = self._extract_filename_from_url(img["url"])
                    lines.append(f"![{filename}](./images/{filename})")
                else:
                    lines.append(f"![{img['url']}]({img['url']})")
            lines.append("")

        # 附件
        files = topic.get("files", [])
        if files:
            lines.append("## 附件")
            for file in files:
                if replace_local:
                    lines.append(f"- [{file['name']}](./files/{file['name']})")
                else:
                    size_kb = file.get("size", 0) / 1024
                    lines.append(f"- [{file['name']}]({file['url']}) ({size_kb:.1f}KB)")
            lines.append("")

        # 话题链接
        if topic.get("id"):
            lines.append(f"---")
            lines.append(f"原文链接: https://wx.zsxq.com/d/{topic['id']}")

        return "\n".join(lines)

    def _extract_filename_from_url(self, url: str) -> str:
        """从URL提取文件名"""
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        filename = os.path.basename(unquote(parsed.path))
        return filename or f"image_{hash(url) % 100000}"


# 导入os用于上面的函数
import os
