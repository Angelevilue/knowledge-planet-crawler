"""
微信扫码登录模块 - 知识星球爬虫
使用selenium实现微信扫码登录获取cookies

备选方案: 如果selenium无法绕过验证，可以使用浏览器扩展导出cookies
推荐扩展: "EditThisCookie" 或 "Cookiebro"
"""
import json
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config


class WeChatLogin:
    """微信扫码登录"""

    def __init__(self):
        self.driver = None
        self.cookies = None

    def _init_driver(self, use_existing_browser=False, remote_debugging_port=9222):
        """初始化Chrome driver - 抗检测配置"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--lang=zh-CN")
        chrome_options.add_argument("--timezone=Asia/Shanghai")

        # 反检测选项
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # 使用远程调试模式连接用户现有的Chrome
        if use_existing_browser:
            chrome_options.add_argument(f"--remote-debugging-port={remote_debugging_port}")
            # 使用新的独立profile目录，避免冲突
            chrome_options.add_argument("--user-data-dir=/Users/zephyrmuse/Projects/Crawler/Knowledge_planet/chrome_profile")
            chrome_options.add_argument("--profile-directory=AutomationProfile")

        # 无头模式(注释掉以下行可看到浏览器窗口)
        # chrome_options.add_argument("--headless")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # 隐藏 webdriver 属性
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
                window.chrome = { runtime: {} };
            """
        })

        self.driver.implicitly_wait(10)

    def _wait_for_qr_code(self):
        """等待二维码加载 - 支持多种选择器"""
        selectors = [
            ".qrcode img",
            ".login-qrcode img",
            "[class*='qrcode'] img",
            "[class*='qr-code'] img",
            "canvas",
            ".weui-desktop-login__qrcode img",
            ".login__container img",
        ]

        for selector in selectors:
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                print(f"找到二维码元素: {selector}")
                return True
            except Exception:
                continue

        # 尝试截屏保存调试
        try:
            self.driver.save_screenshot("/Users/zephyrmuse/Projects/Crawler/Knowledge_planet/debug_screenshot.png")
            print("已保存调试截图到 debug_screenshot.png")
        except Exception:
            pass

        return False

    def _get_qr_code_image(self):
        """获取二维码图片用于调试"""
        try:
            img = self.driver.find_element(By.CSS_SELECTOR, ".qrcode img")
            return img.get_attribute("src")
        except Exception:
            return None

    def login(self, use_existing_browser=False) -> dict:
        """
        执行微信扫码登录
        use_existing_browser: True 使用用户现有的Chrome配置文件(直接复用已登录状态)
        返回登录后的cookies
        """
        print("正在初始化浏览器...")
        self._init_driver(use_existing_browser=use_existing_browser)

        try:
            print("正在打开登录页面...")
            self.driver.get(config.LOGIN_URL)

            if use_existing_browser:
                print("检测现有浏览器登录状态...")
                # 等待页面完全加载
                time.sleep(3)
                # 检查是否已登录
                current_url = self.driver.current_url
                if "login" not in current_url and "wx.zsxq.com" in current_url:
                    print(f"检测到已登录状态! 当前URL: {current_url}")
                else:
                    print("请在打开的浏览器中手动登录知识星球...")
                    print("登录完成后按 Enter 继续...")
                    input()
            else:
                print("等待二维码加载...")
                if not self._wait_for_qr_code():
                    raise Exception("二维码加载失败")

                print("=" * 50)
                print("请使用微信扫描二维码登录知识星球")
                print("=" * 50)

                # 等待登录成功 - 检查URL变化或cookies
                while True:
                    current_url = self.driver.current_url
                    if "login" not in current_url:
                        print(f"登录成功! 当前URL: {current_url}")
                        break

                    # 检查是否已扫描
                    try:
                        # 尝试查找登录成功的元素
                        self.driver.find_element(By.CSS_SELECTOR, ".logged-info")
                        print("检测到已登录状态")
                        break
                    except Exception:
                        pass

                    time.sleep(1)

            # 获取cookies
            self.cookies = self.driver.get_cookies()
            print(f"获取到 {len(self.cookies)} 个cookies")

            return self.cookies

        finally:
            if self.driver:
                self.driver.quit()

    def save_cookies(self, cookies: list = None):
        """保存cookies到文件"""
        if cookies is None:
            cookies = self.cookies

        if cookies is None:
            raise ValueError("没有可保存的cookies")

        with open(config.COOKIES_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f"Cookies已保存到: {config.COOKIES_FILE}")

    def load_cookies(self) -> list:
        """从文件加载cookies"""
        if not os.path.exists(config.COOKIES_FILE):
            return None

        with open(config.COOKIES_FILE, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        print(f"从文件加载了 {len(cookies)} 个cookies")
        return cookies

    def get_session_headers(self, cookies: list = None) -> dict:
        """
        从cookies生成请求头
        """
        if cookies is None:
            cookies = self.load_cookies()

        if cookies is None:
            raise ValueError("没有可用的cookies")

        # 构建cookie字符串
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://wx.zsxq.com/",
            "Origin": "https://wx.zsxq.com",
            "Cookie": cookie_str,
        }

        return headers

    @staticmethod
    def import_cookies_manually():
        """
        手动导入cookies - 当selenium无法绕过验证时使用

        使用方法:
        1. 在Chrome/Firefox中登录 wx.zsxq.com
        2. 安装 EditThisCookie 扩展
        3. 点击扩展图标，导出所有cookies为JSON
        4. 将JSON保存到 config.COOKIES_FILE 路径
        5. 或者直接调用此函数粘贴JSON内容
        """
        print("=" * 50)
        print("手动导入Cookies")
        print("=" * 50)
        print("""
由于Cloudflare验证无法绕过，请使用以下方法手动获取cookies:

方法1 - 使用浏览器扩展:
1. 在Chrome中打开 https://wx.zsxq.com/
2. 使用微信扫码登录
3. 安装 "EditThisCookie" 扩展
4. 点击扩展图标，点击导出按钮(Export)
5. 将导出的JSON内容保存到 cookies.json 文件
6. 将文件内容粘贴到提示中

方法2 - 直接复制:
1. 登录后按 F12 打开开发者工具
2. 在 Console 中输入: JSON.stringify(document.cookie)
3. 复制输出并按格式整理

请选择: 输入 1 使用方法1，输入 2 使用方法2
""")

        choice = input("请选择 (1/2): ").strip()

        if choice == "1":
            print(f"\n请将 EditThisCookie 导出的 JSON 内容粘贴到下面:")
            print(f"(或者直接将JSON文件内容保存到: {config.COOKIES_FILE})")
            json_input = input("\n粘贴JSON内容 (直接回车打开文件编辑): ").strip()

            if not json_input:
                # 尝试从文件读取
                if os.path.exists(config.COOKIES_FILE):
                    with open(config.COOKIES_FILE, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    print(f"成功从文件加载 {len(cookies)} 个cookies")
                    return cookies
                else:
                    print("文件不存在，请先保存cookies到文件")
                    return None

            try:
                cookies = json.loads(json_input)
                # 如果是字符串格式的cookie，转换为对象
                if isinstance(cookies, str):
                    cookie_list = []
                    for item in cookies.split(";"):
                        item = item.strip()
                        if "=" in item:
                            name, value = item.split("=", 1)
                            cookie_list.append({
                                "name": name.strip(),
                                "value": value.strip(),
                                "domain": ".zsxq.com",
                                "path": "/"
                            })
                    cookies = cookie_list

                # 保存到文件
                with open(config.COOKIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                print(f"成功保存 {len(cookies)} 个cookies到: {config.COOKIES_FILE}")
                return cookies
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                return None

        return None


def main():
    """登录测试入口"""
    login = WeChatLogin()

    # 检查是否已有保存的cookies
    existing_cookies = login.load_cookies()
    if existing_cookies:
        print("发现已保存的cookies")
        response = input("是否重新登录? (y/N): ").strip().lower()
        if response != "y":
            headers = login.get_session_headers(existing_cookies)
            print("使用现有cookies生成headers成功")
            return

    # 执行新登录
    cookies = login.login()
    login.save_cookies(cookies)
    headers = login.get_session_headers(cookies)
    print("登录完成!")


if __name__ == "__main__":
    main()
