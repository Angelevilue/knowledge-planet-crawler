"""
知识星球爬虫 - 主程序入口
"""
import argparse
import sys

import config
from login import WeChatLogin
from crawler import KnowledgePlanetCrawler
from scheduler import IncrementalScheduler


def login_command(args):
    """登录命令"""
    print("=" * 50)
    print("知识星球登录")
    print("=" * 50)

    login = WeChatLogin()

    # 检查是否已有保存的cookies
    existing_cookies = login.load_cookies()
    if existing_cookies:
        print("发现已保存的cookies")
        if not args.force:
            response = input("是否重新登录? (y/N): ").strip().lower()
            if response != "y":
                headers = login.get_session_headers(existing_cookies)
                print("使用现有cookies")
                return

    if args.manual:
        # 手动导入cookies
        cookies = login.import_cookies_manually()
        if cookies:
            print("手动导入成功!")
        return

    # 执行新登录
    try:
        cookies = login.login(use_existing_browser=args.existing)
        login.save_cookies(cookies)
        print("登录完成!")
    except Exception as e:
        print(f"自动登录失败: {e}")
        print("\n建议使用手动方式导入cookies:")
        print("python main.py login --manual")


def crawl_command(args):
    """爬取命令"""
    print("=" * 50)
    print("知识星球爬虫")
    print("=" * 50)

    try:
        crawler = KnowledgePlanetCrawler(group_id=args.group)
        crawler.crawl_all(
            max_count=args.max,
            incremental=not args.no_incremental,
            start_date=args.start_date,
            end_date=args.end_date
        )
    except ValueError as e:
        print(f"错误: {e}")
        print("\n请先运行 'python main.py login' 进行登录")
        sys.exit(1)


def schedule_command(args):
    """调度命令"""
    print("=" * 50)
    print("知识星球增量更新调度器")
    print("=" * 50)

    scheduler = IncrementalScheduler(group_id=args.group, interval=args.interval)
    scheduler.run()


def main():
    parser = argparse.ArgumentParser(
        description="知识星球爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py login                                      # 登录知识星球
  python main.py crawl --group 12345678                     # 爬取指定群组
  python main.py crawl --test                               # 测试模式(爬取一页)
  python main.py crawl --start-date 2025-01-01              # 爬取指定日期之后的话题
  python main.py crawl --start-date 2025-01-01 --end-date 2025-12-31  # 爬取指定日期范围
  python main.py crawl --no-incremental                     # 禁用增量模式(重新爬取所有)
  python main.py schedule --interval 3600                    # 启动调度器(每小时检查一次)
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # login命令
    login_parser = subparsers.add_parser("login", help="登录知识星球")
    login_parser.add_argument("--force", action="store_true", help="强制重新登录")
    login_parser.add_argument("--manual", action="store_true", help="手动导入cookies")
    login_parser.add_argument("--existing", action="store_true", help="使用现有Chrome浏览器(需手动登录)")

    # crawl命令
    crawl_parser = subparsers.add_parser("crawl", help="爬取话题")
    crawl_parser.add_argument("--group", type=str, default=config.GROUP_ID, help="群组ID")
    crawl_parser.add_argument("--test", action="store_true", help="测试模式(只爬取一页)")
    crawl_parser.add_argument("--max", type=int, default=None, help="最大爬取数量")
    crawl_parser.add_argument("--no-incremental", action="store_true", help="禁用增量模式")
    crawl_parser.add_argument("--start-date", type=str, default=None,
                            help="开始日期 (YYYY-MM-DD)")
    crawl_parser.add_argument("--end-date", type=str, default=None,
                            help="结束日期 (YYYY-MM-DD)")

    # schedule命令
    schedule_parser = subparsers.add_parser("schedule", help="启动增量调度器")
    schedule_parser.add_argument("--group", type=str, default=config.GROUP_ID, help="群组ID")
    schedule_parser.add_argument("--interval", type=int, default=config.DEFAULT_CHECK_INTERVAL,
                                 help="检查间隔(秒)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # 执行命令
    if args.command == "login":
        login_command(args)
    elif args.command == "crawl":
        crawl_command(args)
    elif args.command == "schedule":
        schedule_command(args)


if __name__ == "__main__":
    main()
