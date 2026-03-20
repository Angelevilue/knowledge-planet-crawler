"""
文件下载模块 - 知识星球爬虫
支持图片、文档等文件的下载和断点续传
"""
import hashlib
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

import config


class FileDownloader:
    """文件下载器"""

    # 图片扩展名
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    # 文档扩展名
    DOCUMENT_EXTENSIONS = {".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"}
    # 音视频扩展名
    MEDIA_EXTENSIONS = {".mp3", ".mp4", ".wav", ".avi", ".mov", ".flv"}

    def __init__(self, headers: dict, output_dir: str = None):
        self.headers = headers
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.session = requests.Session()
        self.session.headers.update(headers)

        # 创建子目录
        self.images_dir = os.path.join(self.output_dir, "images")
        self.files_dir = os.path.join(self.output_dir, "files")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)

    def _get_file_extension(self, url: str) -> str:
        """从URL获取文件扩展名"""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        ext = os.path.splitext(path)[1].lower()
        return ext if ext else ".bin"

    def _get_file_type(self, url: str) -> str:
        """判断文件类型"""
        ext = self._get_file_extension(url)
        if ext in self.IMAGE_EXTENSIONS:
            return "image"
        elif ext in self.DOCUMENT_EXTENSIONS:
            return "document"
        elif ext in self.MEDIA_EXTENSIONS:
            return "media"
        return "other"

    def _sanitize_filename(self, filename: str, max_length: int = 100) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 限制长度
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        return filename

    def _generate_unique_filename(self, directory: str, filename: str) -> str:
        """生成唯一的文件名"""
        filename = self._sanitize_filename(filename)
        filepath = os.path.join(directory, filename)

        if not os.path.exists(filepath):
            return filename

        # 如果文件已存在，添加数字后缀
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(filepath):
            filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(directory, filename)
            counter += 1

        return filename

    def _get_content_hash(self, filepath: str) -> str:
        """计算文件内容的MD5哈希"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(config.CHUNK_SIZE), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def download_file(self, url: str, filename: str = None, file_type: str = None) -> str:
        """
        下载单个文件

        Args:
            url: 文件URL
            filename: 指定文件名(可选)
            file_type: 文件类型，可选 "image" 或 "document"

        Returns:
            下载后的本地文件路径
        """
        if not filename:
            # 从URL提取文件名
            parsed = urlparse(url)
            filename = os.path.basename(unquote(parsed.path))
            if not filename or "." not in filename:
                filename = f"file_{int(time.time())}"

        # 确定文件类型和目标目录
        if file_type is None:
            file_type = self._get_file_type(url)

        if file_type == "image":
            target_dir = self.images_dir
        else:
            target_dir = self.files_dir

        # 生成唯一文件名
        filename = self._generate_unique_filename(target_dir, filename)
        filepath = os.path.join(target_dir, filename)

        # 检查是否已存在(断点续传检查)
        if os.path.exists(filepath):
            print(f"文件已存在，跳过: {filename}")
            return filepath

        # 下载文件
        print(f"下载: {filename}")
        print(f"  来源: {url}")

        max_size = config.MAX_IMAGE_SIZE if file_type == "image" else config.MAX_FILE_SIZE

        for attempt in range(config.MAX_RETRY):
            try:
                response = self.session.get(url, stream=True, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                if total_size > max_size:
                    print(f"文件过大 ({total_size / 1024 / 1024:.1f}MB)，跳过")
                    return None

                downloaded = 0
                with open(filepath + ".tmp", "wb") as f:
                    for chunk in response.iter_content(chunk_size=config.CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = downloaded / total_size * 100
                                print(f"\r  进度: {progress:.1f}%", end="", flush=True)

                print()  # 换行

                # 重命名临时文件
                os.rename(filepath + ".tmp", filepath)
                print(f"完成: {filepath}")
                return filepath

            except requests.exceptions.RequestException as e:
                print(f"\n下载失败 (尝试 {attempt + 1}/{config.MAX_RETRY}): {e}")
                if os.path.exists(filepath + ".tmp"):
                    os.remove(filepath + ".tmp")

                if attempt < config.MAX_RETRY - 1:
                    time.sleep(2 ** attempt)  # 指数退避

        print(f"下载失败，已达到最大重试次数")
        return None

    def download_image(self, url: str, filename: str = None) -> str:
        """下载图片"""
        return self.download_file(url, filename, "image")

    def download_document(self, url: str, filename: str = None) -> str:
        """下载文档"""
        return self.download_file(url, filename, "document")


def download_file(url: str, filename: str = None, headers: dict = None) -> str:
    """
    便捷函数：下载单个文件
    """
    downloader = FileDownloader(headers)
    return downloader.download_file(url, filename)
