# app/douyin/auto_upload.py
import base64
import json
import requests
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
from config import BASE_DIR
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor


async def restore_session_with_storage_state(storage_state_str, url):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        storage_state = json.loads(storage_state_str)
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()

        # 访问指定的 URL
        await page.goto(url)

        print("[-] 恢复会话并访问页面:", url)

        # 执行其他操作...

        await browser.close()


async def get_douyin_qr_code(login_id, callback_url):
    """
    获取抖音创作者平台的登录二维码，并等待用户扫码登录。返回二维码图片的 Base64 编码字符串和会话存储状态。

    1. 启动 Playwright 并打开抖音创作者平台的登录页面。
    2. 获取登录二维码的图片 src 属性，并提取 Base64 编码数据。
    3. 等待用户扫码登录，最多等待 40 秒。
    4. 获取会话存储状态并将其转换为字符串。

    Args:
        login_id (str): 用户登录ID。
        callback_url (str): 回调URL，用于发送二维码信息。

    Returns:
        tuple: 二维码图片的 Base64 编码字符串和会话存储状态字符串。

    Raises:
        asyncio.TimeoutError: 如果在指定的时间内用户未扫码登录。
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")

        # 获取二维码图片的 src 属性
        qr_code_element = await page.wait_for_selector("div[class*='qrcode-image'] img")
        qr_code_src = await qr_code_element.get_attribute("src")

        # 由于图片的 src 属性已经是 Base64 编码格式，无需再进行编码
        img_str = qr_code_src.split(",")[1]
        print("[-] 二维码图片的Base64为：", img_str)

        # 计算二维码到期时间（当前时间+60秒）
        expire_time = int(time.time()) + 60

        # 异步回传二维码图片到指定callback_url接口上，并附带login_id和expire_time
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            loop.run_in_executor(pool, send_qr_code_to_callback, login_id, img_str, callback_url, expire_time)

        # 等待用户扫码，最多等待70秒
        try:
            # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
            print('[-] 等待用户扫码...')
            await wait_for_multiple_urls(page, [
                "https://creator.douyin.com/creator-micro/content/upload",
                "https://creator.douyin.com/creator-micro/home"
            ], timeout=70000)
            print("[-] 用户扫码成功")
        except asyncio.TimeoutError:
            print("[+] 等待用户扫码,70秒超时")

        # 获取存储状态并转换为字符串
        storage_state = await context.storage_state()
        storage_state_str = json.dumps(storage_state)
        # print("[-] 获取到的 storage_state:", storage_state_str)

        # 将存储状态写入文件，以 login_id 命名
        storage_file_name = Path(BASE_DIR / "app" / "douyin" / "accounts" / f"{login_id}.json")
        storage_file_name.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在
        with open(storage_file_name, "w") as storage_file:
            storage_file.write(storage_state_str)
        print(f"[-] 存储状态已保存到文件: {storage_file_name}")

        # 关闭浏览器
        await browser.close()

        return img_str, storage_file_name

async def check_cookie(account_file):
    """
    检查存储状态中的 cookie 是否有效。

    该方法使用提供的存储状态字符串创建一个新的浏览器上下文，并访问抖音创作者平台的指定 URL。
    如果在页面上找到指定的元素，则表示 cookie 有效；否则表示 cookie 失效。

    Args:
        storage_state_str (str): 存储状态的 JSON 字符串，包括 cookie 和其他会话信息。

    Returns:
        bool: 如果 cookie 有效返回 True，否则返回 False。

    Raises:
        Exception: 如果在执行过程中发生错误，则抛出异常。
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        # storage_state = json.loads(storage_state_str)
        # context = await browser.new_context(storage_state=storage_state)
        account_file = Path(BASE_DIR / "app" / "douyin" / "accounts" / f"{account_file}")
        account_file = str(account_file)
        context = await browser.new_context(storage_state=account_file)
        page = await context.new_page()

        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            # 等待特定元素出现，判断 cookie 是否有效
            # await page.wait_for_selector("div.boards-more h3:text('抖音排行榜')", timeout=5000)
            # 等待 "发布作品" 文字出现，判断 cookie 是否有效
            await page.wait_for_selector("span:has-text('发布作品')", timeout=5000)
            print("[+] Cookie 有效")
            return True
        except:
            print("[+] Cookie 失效")
            return False
        finally:
            await browser.close()


async def wait_for_multiple_urls(page, urls, timeout):
    """
        等待页面导航到指定的多个 URL 中的一个，直到达到超时时间。
        该方法会循环检查页面的当前 URL，并在匹配到目标 URL 或达到超时时间时返回或抛出超时异常。
        Args:
            page (playwright.async_api.Page): Playwright 页面对象，用于操作和检查页面状态。
            urls (list): 包含多个目标 URL 的列表，方法会等待页面导航到这些 URL 中的任意一个。
            timeout (int): 最大等待时间（毫秒）。如果在此时间内未导航到目标 URL，则抛出超时异常。
        Raises:
            asyncio.TimeoutError: 如果在指定的时间内未导航到目标 URL。
        Returns:
            None
        """
    end_time = asyncio.get_event_loop().time() + timeout / 1000
    while True:
        current_url = page.url
        if current_url in urls:
            return
        if asyncio.get_event_loop().time() > end_time:
            raise asyncio.TimeoutError("Timeout waiting for one of the specified URLs")
        await asyncio.sleep(0.1)



def send_qr_code_to_callback(login_id, qr_code, callback_url, expire_time):
    """
    回传二维码图片到指定的callback_url接口上，并附带login_id和expire_time

    Args:
        login_id (str): 用户登录ID
        qr_code (str): 二维码图片的Base64编码
        callback_url (str): 回调URL
        expire_time (int): 二维码到期时间的时间戳

    Returns:
        None
    """
    try:
        print("[-] 开始回传二维码图片 callback_url:", callback_url, "expire_time:", expire_time)
        response = requests.post(callback_url, json={
            "loginId": login_id,
            "qrCode": qr_code,
            "expireTime": expire_time
        })
        response.raise_for_status()
        print("[-] 成功回传二维码图片到回调URL")
    except requests.RequestException as e:
        print(f"[+] 回传二维码图片失败: {e}")
