# app/douyin/auto_upload.py
import base64
import json
import requests
import asyncio
import time
import aiohttp
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


async def get_douyin_qr_code(login_id, qr_code_callback_url, verification_api_url, douyin_login_info_map):
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
            loop.run_in_executor(pool, send_qr_code_to_callback, login_id, img_str, qr_code_callback_url, expire_time)

        # 等待用户扫码，最多等待70秒
        try:
            # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
            print('[-] 等待用户扫码...')
            login_res = await wait_for_multiple_urls(page, [
                "https://creator.douyin.com/creator-micro/content/upload",
                "https://creator.douyin.com/creator-micro/home"
            ], timeout=70000)

            if login_res == "send_code":
                print("[-] 需要接收短信验证")
                # 点击“接收短信验证”文本
                # await page.click("span:has-text('接收短信验证')")
                # 点击“接收短信验证”文本
                await page.click("p.uc-ui-typography_text.uc-ui-lists_item_content_title:has-text('接收短信验证')")
                print("[-] 已点击 接收短信验证")

                try:
                    # 点击“获取验证码”按钮
                    await page.click("div.uc-ui-input_right:has-text('获取验证码')")
                    print("[-] 已点击 获取验证码")
                    print("[-] 等待用户输入验证码...")
                except Exception as e:
                    print("[error] [playwright] 点击【获取验证码】按钮错误：", e)
                    return None, None

                try:
                    verification_code = await get_verification_code_from_map(login_id, douyin_login_info_map)
                    print(f"[-] 获取到的验证码: {verification_code}")
                except Exception as e:
                    print("[error] 等待用户输入验证码超时:", e)
                    return None, None

                try:
                    # 在页面中输入验证码
                    await page.fill("input[type='number'][placeholder='请输入验证码']", verification_code)
                except Exception as e:
                    print("[error] [playwright] 在页面中输入验证码出错:", e)
                    return None, None

                try:
                    # 点击“验证”按钮
                    await page.click("div.uc-ui-verify_sms-verify_button.primary.default.uc-ui-button:has-text('验证')")
                    print("[-] 已点击 提交验证码")
                except Exception as e:
                    print("[error] [playwright] 点击“验证”按钮出错:", e)
                    return None, None

            print("[-] 页面登录成功")

            douyin_id = ""
            try:
                # 使用文本选择器找到“抖音号：”后面的内容
                douyin_id_element = await page.locator("text=抖音号：").element_handle()
                if douyin_id_element:
                    douyin_id_text = await douyin_id_element.inner_text()
                    # 提取“抖音号：”后面的部分
                    douyin_id = douyin_id_text.split("抖音号：")[1].strip()
                    print("抖音号：", douyin_id)
                else:
                    print("未找到抖音号")
            except Exception as e:
                print("[error] [playwright] 获取抖音号出错:", e)

        except Exception as e:
            print(f"[+] 等待用户输入登录超时: {e}")
            return None, None

        # 获取存储状态并转换为字符串
        storage_state = await context.storage_state()
        storage_state_str = json.dumps(storage_state)
        # print("[-] 获取到的 storage_state:", storage_state_str)

        # 将存储状态写入文件，以 login_id 命名
        storage_file_name = Path(BASE_DIR / "app" / "douyin" / "accounts" / f"{douyin_id}.json")
        storage_file_name.parent.mkdir(parents=True, exist_ok=True)  # 确保目录存在
        with open(storage_file_name, "w") as storage_file:
            storage_file.write(storage_state_str)
        print(f"[-] 存储状态已保存到文件: {storage_file_name}")

        # 关闭浏览器
        await browser.close()

        return img_str, storage_file_name, douyin_id


async def check_cookie(douyin_id):
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
        account_file = Path(BASE_DIR / "app" / "douyin" / "accounts" / f"{douyin_id}.json")
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
    该方法会循环检查页面的当前 URL，并在匹配到目标 URL 或页面包含 "发送短信验证" 文本时返回结果字符串。

    Args:
        page (playwright.async_api.Page): Playwright 页面对象，用于操作和检查页面状态。
        urls (list): 包含多个目标 URL 的列表，方法会等待页面导航到这些 URL 中的任意一个。
        timeout (int): 最大等待时间（毫秒）。如果在此时间内未导航到目标 URL 或包含指定文本的元素，则抛出超时异常。

    Raises:
        asyncio.TimeoutError: 如果在指定的时间内未导航到目标 URL 或包含指定文本的元素。

    Returns:
        str: "login_success" 表示成功登录，"send_code" 表示页面包含 "发送短信验证" 文本。
    """
    end_time = asyncio.get_event_loop().time() + timeout / 1000
    while True:
        current_url = page.url
        if current_url in urls:
            return "login_success"

        # 检查页面是否包含 "发送短信验证" 文本
        if await page.locator("text=发送短信验证").count() > 0:
            return "send_code"

        if asyncio.get_event_loop().time() > end_time:
            raise asyncio.TimeoutError("Timeout waiting for one of the specified URLs or text '发送短信验证'")

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


async def get_verification_code(api_url, timeout=60):
    """
    调用其他 HTTP 接口获取用户输入的验证码，超过 60 秒后无输入则超时。

    Args:
        api_url (str): 用于获取验证码的 API URL。
        timeout (int): 最大等待时间（秒）。如果在此时间内未获取到验证码，则抛出超时异常。

    Raises:
        asyncio.TimeoutError: 如果在指定的时间内未获取到验证码。

    Returns:
        str: 获取到的验证码。
    """
    end_time = asyncio.get_event_loop().time() + timeout
    while True:
        if asyncio.get_event_loop().time() > end_time:
            raise asyncio.TimeoutError("Timeout waiting for verification code")

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    result = await response.json()
                    code = result.get("verification_code")
                    if code:
                        return code

        await asyncio.sleep(1)  # 等待一秒后再次检查


async def get_verification_code_from_map(login_id, douyin_login_info_map, timeout=60):
    """
    从 douyin_login_info_map 中获取指定 loginId 下的 verificationCode 字段。
    如果 verificationCode 不存在或一直为空，则等待 1 秒后再获取，最多等待 60 秒。

    Args:
        login_id (str): 用户登录ID。
        timeout (int): 最大等待时间（秒）。如果在此时间内未获取到验证码，则抛出超时异常。

    Raises:
        asyncio.TimeoutError: 如果在指定的时间内未获取到有效的验证码。

    Returns:
        str: 获取到的验证码。
    """
    end_time = asyncio.get_event_loop().time() + timeout
    while True:
        if login_id in douyin_login_info_map and douyin_login_info_map[login_id].get("verifyCode"):
            return douyin_login_info_map[login_id]["verifyCode"]

        if asyncio.get_event_loop().time() > end_time:
            raise asyncio.TimeoutError("Timeout waiting for verification code")

        await asyncio.sleep(1)
