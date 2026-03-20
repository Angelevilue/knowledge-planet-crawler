"""
增量更新调度器 - 知识星球爬虫
定期检查并爬取新话题
"""
import signal
import sys
import time
from datetime import datetime

import config
from crawler import KnowledgePlanetCrawler


class IncrementalScheduler:
    """增量更新调度器"""

    def __init__(self, group_id: str = None, interval: int = None):
        self.group_id = group_id or config.GROUP_ID
        self.interval = interval or config.DEFAULT_CHECK_INTERVAL
        self.running = False
        self.crawler = None

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        print("\n收到退出信号，正在停止调度器...")
        self.stop()

    def _init_crawler(self):
        """初始化爬虫"""
        if self.crawler is None:
            self.crawler = KnowledgePlanetCrawler(group_id=self.group_id)

    def run_once(self):
        """执行一次爬取"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始检查新话题...")

        try:
            self._init_crawler()
            self.crawler.crawl_all(incremental=True)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查完成")
        except Exception as e:
            print(f"爬取出错: {e}")

    def run(self):
        """持续运行调度器"""
        print("=" * 50)
        print("知识星球增量更新调度器")
        print(f"检查间隔: {self.interval} 秒")
        print(f"群组ID: {self.group_id}")
        print("=" * 50)
        print("按 Ctrl+C 停止")
        print("=" * 50)

        self.running = True

        while self.running:
            self.run_once()

            if self.running:
                print(f"\n等待 {self.interval} 秒后进行下一次检查...")
                # 使用分段时间，以便能响应退出信号
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)

        print("调度器已停止")

    def stop(self):
        """停止调度器"""
        self.running = False


def main():
    """调度器入口"""
    import argparse

    parser = argparse.ArgumentParser(description="知识星球增量更新调度器")
    parser.add_argument("--group", type=str, default=config.GROUP_ID, help="群组ID")
    parser.add_argument("--interval", type=int, default=config.DEFAULT_CHECK_INTERVAL,
                       help="检查间隔(秒)")

    args = parser.parse_args()

    scheduler = IncrementalScheduler(group_id=args.group, interval=args.interval)
    scheduler.run()


if __name__ == "__main__":
    main()
