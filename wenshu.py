#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国裁判文书网登录页自动填写并截图（wenshu_new.py）

- 打开登录页面：https://wenshu.court.gov.cn/website/wenshu/181010CARHS5BS3C/index.html?open=login
- 自动填入账号与密码（不点击登录）
- 截取全页截图，保存到桌面/文书网登录/ 目录
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

import os
import sys
import time
import platform
import subprocess
import base64
import json
from datetime import datetime

from storage_utils import load_records, upsert_record, write_records

WENSHU_LOGIN_URL = "https://wenshu.court.gov.cn/website/wenshu/181010CARHS5BS3C/index.html?open=login"

# 账号与密码（按需替换）
WENSHU_ACCOUNT = {
    "username": "18858117402",
    "password": "jm2,*kbxT3uLZA/",
}


def _clear_proxy_env_vars() -> None:
    for var in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        if var in os.environ:
            del os.environ[var]


def _build_chrome_options() -> Options:
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1440,900")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument("--no-proxy-server")
    chrome_options.add_argument("--proxy-server=direct://")
    chrome_options.add_argument("--proxy-bypass-list=*")
    return chrome_options


def _apply_stealth(driver) -> None:
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                  Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                  Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                  Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                  window.chrome = { runtime: {} };
                """
            },
        )
    except Exception:
        pass


def _ensure_fullpage_screenshot(driver) -> None:
    try:
        total_width = driver.execute_script(
            "return Math.max(document.body.scrollWidth, document.documentElement.scrollWidth, document.documentElement.clientWidth);"
        )
        total_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.documentElement.clientHeight);"
        )
        viewport_width = driver.execute_script("return window.innerWidth")
        viewport_height = driver.execute_script("return window.innerHeight")

        if total_width and total_height:
            max_w = min(int(total_width) + 100, 3840)
            max_h = min(int(total_height) + 300, 21600)
            if total_width > viewport_width or total_height > viewport_height:
                driver.set_window_size(max_w, max_h)
                time.sleep(1.0)
        driver.execute_script("window.scrollTo(0, 0);")
    except Exception:
        pass


def fill_login_and_screenshot(
    username: str,
    password: str,
    save_to_desktop: bool = True,
    search_keyword: str | None = None,
    output_directory: str | None = None,
    record_name: str | None = None,
) -> dict | None:
    _clear_proxy_env_vars()
    chrome_options = _build_chrome_options()
    driver = None

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        _apply_stealth(driver)

        print(f"打开登录页面：{WENSHU_LOGIN_URL}")
        driver.get(WENSHU_LOGIN_URL)
        WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1.0)

        wait = WebDriverWait(driver, 12)

        # 登录表单在 iframe 内部，先切换到 iframe
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "contentIframe")))
            print("成功切换到 iframe: contentIframe")
        except Exception as e:
            print(f"切换到 iframe 失败: {e}")
            try:
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@src,'account.court.gov.cn')]")))
                print("通过 XPATH 成功切换到 iframe")
            except Exception as e2:
                print(f"备用切换方式也失败: {e2}")
                raise RuntimeError("无法切换到登录 iframe")

        # 用户名输入框（手机号）
        user_input = None
        for by_, sel in [
            (By.CSS_SELECTOR, "input[name='username']"),
            (By.CSS_SELECTOR, "input.phone-number-inp"),
            (By.CSS_SELECTOR, "input.phone-number-input"),
            (By.XPATH, '//input[@type="text" and (@name="username" or contains(@placeholder,"手机号码"))]'),
            (By.XPATH, '//input[@placeholder="手机号码"]'),
        ]:
            try:
                user_input = wait.until(EC.presence_of_element_located((by_, sel)))
                if user_input:
                    print(f"已定位用户名输入框: {sel}")
                    break
            except Exception:
                continue
        if not user_input:
            raise RuntimeError("未找到用户名输入框")

        # 密码输入框
        pwd_input = None
        for by_, sel in [
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.XPATH, '//input[@type="password" and (@name="password" or contains(@placeholder,"密码"))]'),
            (By.CSS_SELECTOR, "input.password"),
        ]:
            try:
                pwd_input = wait.until(EC.presence_of_element_located((by_, sel)))
                if pwd_input:
                    print(f"已定位密码输入框: {sel}")
                    break
            except Exception:
                continue
        if not pwd_input:
            raise RuntimeError("未找到密码输入框")

        # 聚焦并滚动到可视区域
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", user_input)
            time.sleep(0.2)
        except Exception:
            pass

        # 使用 JS 设置值并派发事件，保证前端接收到变更
        try:
            driver.execute_script(
                "arguments[0].focus();"
                "arguments[0].value = arguments[2];"
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
                "arguments[1].value = arguments[3];"
                "arguments[1].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[1].dispatchEvent(new Event('change', {bubbles:true}));",
                user_input, pwd_input, username, password
            )
            print("已通过 JS 写入账号与密码并派发事件")
        except Exception:
            try:
                user_input.clear()
                user_input.send_keys(username)
                time.sleep(0.2)
                pwd_input.clear()
                pwd_input.send_keys(password)
                print("已通过 send_keys 输入账号与密码")
            except Exception:
                pass

        # 处理验证码：下载、展示、等待用户输入并填入
        cap_input = None
        cap_img = None
        try:
            # 留在 iframe 内部定位验证码
            for by_, sel in [
                (By.CSS_SELECTOR, "input[name='captcha']"),
                (By.XPATH, '//input[@name="captcha" or contains(@placeholder,"验证码")]'),
            ]:
                try:
                    cap_input = wait.until(EC.presence_of_element_located((by_, sel)))
                    if cap_input:
                        print(f"已定位验证码输入框: {sel}")
                        break
                except Exception:
                    continue
            for by_, sel in [
                (By.CSS_SELECTOR, "img.captcha-img"),
                (By.XPATH, '//img[contains(@class,"captcha") or contains(@src,"data:image")]'),
            ]:
                try:
                    cap_img = wait.until(EC.presence_of_element_located((by_, sel)))
                    if cap_img:
                        print(f"已定位验证码图片: {sel}")
                        break
                except Exception:
                    continue

            if cap_img:
                # 组织目录
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop") if save_to_desktop else os.getcwd()
                save_dir = os.path.join(desktop_path, "文书网登录")
                os.makedirs(save_dir, exist_ok=True)
                ts_cap = datetime.now().strftime("%Y%m%d_%H%M%S")
                cap_path = os.path.join(save_dir, f"WENSHU_验证码_{ts_cap}.png")

                # 优先从 data URL 保存
                saved_ok = False
                try:
                    src = cap_img.get_attribute("src") or ""
                    print(f"验证码图片 src 前缀: {src[:30]}...")
                    if src.startswith("data:image"):
                        try:
                            b64 = src.split(",", 1)[1]
                            with open(cap_path, "wb") as f:
                                f.write(base64.b64decode(b64))
                            saved_ok = os.path.exists(cap_path) and os.path.getsize(cap_path) > 0
                            print("已从 data URL 解码保存验证码图片")
                        except Exception:
                            saved_ok = False
                    if not saved_ok:
                        cap_img.screenshot(cap_path)
                        saved_ok = os.path.exists(cap_path) and os.path.getsize(cap_path) > 0
                        if saved_ok:
                            print("已通过元素截图保存验证码图片")
                except Exception:
                    pass

                if saved_ok:
                    try:
                        if platform.system() == "Darwin":
                            subprocess.Popen(["open", cap_path])
                        elif platform.system() == "Windows":
                            os.startfile(cap_path)  # type: ignore[attr-defined]
                        else:
                            subprocess.Popen(["xdg-open", cap_path])
                    except Exception:
                        pass
                    print(f"已保存验证码图片：{cap_path}")
                else:
                    print("未能保存验证码图片，请在页面中自行查看。")

                # 让用户输入验证码并填入
                try:
                    captcha_text = input("请输入验证码：").strip()
                except KeyboardInterrupt:
                    captcha_text = ""
                if captcha_text:
                    try:
                        cap_input.clear()
                        cap_input.send_keys(captcha_text)
                        print("验证码已输入")
                        # 回车尝试直接登录
                        try:
                            cap_input.send_keys(Keys.ENTER)
                            print("回车尝试登录")
                            time.sleep(4)
                        except Exception:
                            print("回车尝试直接登录失败")
                            pass
                        
                    except Exception:
                        # 兜底用 JS 赋值
                        try:
                            driver.execute_script(
                                "arguments[0].focus();arguments[0].value=arguments[1];"
                                "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));"
                                "arguments[0].dispatchEvent(new Event('change',{bubbles:true}));",
                                cap_input, captcha_text
                            )
                            print("已通过 JS 写入验证码")
                        except Exception:
                            pass
                # 点击“登录”按钮（在 iframe 内）
                try:
                    prev_iframe_url = driver.execute_script("return window.location.href")
                except Exception:
                    prev_iframe_url = ""
                clicked = False
                print("尝试点击登录按钮...")
                for by_, sel in [
                    (By.XPATH, '//span[contains(@class,"button-primary") and @data-api="/api/login"]'),
                    (By.CSS_SELECTOR, 'span.button.button-primary[data-api="/api/login"]'),
                    (By.XPATH, '//span[contains(.,"登录") and contains(@class,"button-primary")]'),
                ]:
                    try:
                        login_btn = wait.until(EC.element_to_be_clickable((by_, sel)))
                        if login_btn:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", login_btn)
                            driver.execute_script("arguments[0].click();", login_btn)
                            clicked = True
                            print(f"已点击登录按钮: {sel}")
                            break
                    except Exception:
                        continue
                # 等待 iframe 内地址或页面状态变化
                print("等待登录结果（iframe URL 变化或页面跳转）...")
                try:
                    WebDriverWait(driver, 8).until(
                        lambda d: d.execute_script("return window.location.href") != prev_iframe_url
                    )
                    print("检测到 iframe URL 变化")
                except Exception:
                    print("未检测到明显的 URL 变化，可能仍在当前页面")
                    pass
                try:
                    iframe_ret_url = driver.execute_script("return window.location.href")
                    print(f"iframe 返回地址：{iframe_ret_url}")
                except Exception:
                    iframe_ret_url = ""
            else:
                iframe_ret_url = ""
        except Exception as _:
            # 忽略验证码流程失败，继续截图
            iframe_ret_url = ""

        # 回到主文档后再截图（可选）
        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        # 在返回页面上执行一次搜索：询问用户关键词 -> 填入搜索框 -> 触发搜索 -> 等待渲染
        try:
            print("准备在返回页面上执行搜索...")
            if search_keyword is None:
                try:
                    search_kw = input("请输入返回页面要搜索的关键词（可留空跳过）：").strip()
                except KeyboardInterrupt:
                    search_kw = ""
            else:
                search_kw = search_keyword.strip()
                print(f"使用传入的搜索关键词：{search_kw}")
            if search_kw:
                # 定位搜索输入框
                search_input = None
                after_search_url = ""
                for by_, sel in [
                    (By.CSS_SELECTOR, "input.searchKey.search-inp"),
                    (By.CSS_SELECTOR, "input.search-inp"),
                    (By.XPATH, '//input[contains(@class,"searchKey") and @type="text"]'),
                    (By.XPATH, '//input[@type="text" and contains(@placeholder,"输入案由")]'),
                ]:
                    try:
                        search_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by_, sel)))
                        if search_input:
                            print(f"已定位返回页搜索框: {sel}")
                            break
                    except Exception:
                        continue
                if search_input:
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", search_input)
                    except Exception:
                        pass
                    # 使用 JS 写值并派发事件，保证前端接收
                    try:
                        driver.execute_script(
                            "arguments[0].focus();"
                            "arguments[0].value = arguments[1];"
                            "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                            search_input, search_kw
                        )
                        print("已在返回页搜索框写入关键词")
                    except Exception:
                        try:
                            search_input.clear()
                            search_input.send_keys(search_kw)
                        except Exception:
                            pass
                    # 点击“搜索”按钮或回车
                    clicked_search = False
                    for by_, sel in [
                        (By.CSS_SELECTOR, "div.search-rightBtn.search-click"),
                        (By.XPATH, '//div[contains(@class,"search-rightBtn") and contains(@class,"search-click")]'),
                        (By.XPATH, '//button[contains(.,"搜索") or contains(@class,"search-click")]'),
                    ]:
                        try:
                            btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((by_, sel)))
                            if btn:
                                driver.execute_script("arguments[0].click();", btn)
                                clicked_search = True
                                print(f"已触发搜索点击: {sel}")
                                break
                        except Exception:
                            continue
                    if not clicked_search:
                        try:
                            search_input.send_keys(Keys.ENTER)
                            print("已通过回车触发搜索")
                        except Exception:
                            pass
                    # 等待出现结果标志或 URL 变化
                    prev_url_after_login = driver.current_url
                    try:
                        WebDriverWait(driver, 10).until(
                            lambda d: d.current_url != prev_url_after_login or
                            ("search-list" in d.page_source) or
                            ("listMain" in d.page_source)
                        )
                    except Exception:
                        time.sleep(2.0)
                    after_search_url = driver.current_url
                    print(f"搜索后返回地址：{after_search_url}")
                else:
                    print("未找到返回页搜索框，跳过搜索步骤")
        except Exception as _:
            print("执行返回页搜索步骤时出现异常，继续截图")

        # 组织输出目录（可通过参数覆盖默认行为）
        if output_directory:
            save_dir = os.fspath(output_directory)
        else:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop") if save_to_desktop else os.getcwd()
            folder_name = search_kw if 'search_kw' in locals() and search_kw else "文书网登录"
            save_dir = os.path.join(desktop_path, folder_name)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        _ensure_fullpage_screenshot(driver)
        screenshot_label = search_kw if search_kw else "搜索"
        screenshot_path = os.path.join(save_dir, f"WENSHU_{screenshot_label}_{ts}.png")
        driver.save_screenshot(screenshot_path)
        print(f"截图已保存：{screenshot_path}")

        # 打印返回地址（优先：搜索后的地址；否则 iframe 内跳转地址或当前地址）
        ret_url = None
        try:
            if 'after_search_url' in locals() and after_search_url:
                ret_url = after_search_url
        except Exception:
            ret_url = None
        if not ret_url:
            ret_url = iframe_ret_url or driver.current_url
        print(f"返回地址：{ret_url}")

        # 写入 JSON（与 amac/qcc 对齐，列表累积）
        try:
            record_basename = record_name or (search_kw if search_kw else username)
            json_filename = f"{record_basename}.json"
            json_path = os.path.join(save_dir, json_filename)
            record = {
                "item": "WENSHU_裁判文书网搜索",
                "url": WENSHU_LOGIN_URL,
                "name": (search_kw if search_kw else username),
                "ret_url": ret_url,
                "data": {
                    "username": username,
                    "searched_keyword": (search_kw if search_kw else "")
                },
                "screenshot": screenshot_path,
                "queried_at": ts
            }
            all_records = load_records(json_path)
            updated_records = upsert_record(all_records, record)
            write_records(json_path, updated_records)
            print(f"查询记录已保存：{json_path}")
        except Exception as e:
            print(f"保存JSON文件时出错: {str(e)}")

        return record

    except Exception as e:
        print(f"发生错误：{e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            print("操作完成")


def search_wenshu(
    keyword: str,
    save_to_desktop: bool = True,
    target_directory: str | None = None,
    record_name: str | None = None,
):
    username = WENSHU_ACCOUNT.get("username", "").strip()
    password = WENSHU_ACCOUNT.get("password", "").strip()
    if not username or not password:
        raise RuntimeError("WENSHU_ACCOUNT 中缺少账号或密码，无法执行搜索。")
    return fill_login_and_screenshot(
        username=username,
        password=password,
        save_to_desktop=save_to_desktop,
        search_keyword=keyword,
        output_directory=target_directory,
        record_name=record_name,
    )


if __name__ == "__main__":
    u = None
    p = None
    search_kw = None
    if len(sys.argv) >= 2:
        u = sys.argv[1].strip()
    if len(sys.argv) >= 3:
        p = sys.argv[2].strip()
    if len(sys.argv) >= 4:
        search_kw = " ".join(sys.argv[3:]).strip()
    if not u:
        u = WENSHU_ACCOUNT.get("username", "").strip()
    if not p:
        p = WENSHU_ACCOUNT.get("password", "").strip()
    if not u or not p:
        print("账号或密码为空，程序退出。")
        sys.exit(1)
    fill_login_and_screenshot(u, p, search_keyword=search_kw)

    # print("程序运行到指定位置，按 Ctrl+C 中断或按回车继续...")
    # try:
    #     input()  # 等待用户按回车
    # except KeyboardInterrupt:
    #     print("\n收到 Ctrl+C，程序中断")
    #     # 执行清理操作或退出
    #     exit(0)
