# 全程自己搭的，但是没用，验证码图片弄不出来，一直被反爬
# 我最初以为是一直被反爬，现在发现是这个网站搭建本身就很有问题

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国执行信息公开网 被执行人综合查询（https://zxgk.court.gov.cn/zhzxgk/）

功能：
- 打开查询页面
- 将姓名、证件号分别写入前两个输入框（#pName、#pCardNum）
- 提示用户手动输入验证码（页面第三个输入框），按回车继续
- 自动点击“查询”按钮，等待结果
- 截图保存，并把本次查询写入桌面/<姓名>/<姓名>.json（累积方式）
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import time
import sys
import os
import json
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from storage_utils import load_records, upsert_record, write_records

# 默认Cookie（已写死）
DEFAULT_COOKIES = {
    'JSESSIONID': '9642C8842489F65EEF3FB32FB10D709E',
    'lqWVdQzgOVyaO': '57oVz3h2TPc4bX0apytYxBrAMa2YvQsaHBy8582saiAY.mDihnYHYdcuYxJ049GIE.4r.fKDStB6B1KHYpoGFiA',
    'lqWVdQzgOVyaP': 'p4NwNSnT2S9ALptUG2VzoqPLOxqB0s3HjUXJRQB53aDXOElXExxy2xMu8Va7Pu7wnCkZNOnQjaLCY1kblQ3heMSsbwzXb.cieFrlWF.wosipruzLnMgywDNpGs5uIbsQmVEMF0ukwP_zDJUhAxnA23vpiGZ4hzUgZo6quZifPVVquMXbO4_F2SOPHeifd8XCIiQ.s4Ul27yf8pmYsP.g2niLDfB7QCacrsu9V2KmqjKDO_gvVTKkjs39Lnq7RkVK8tW_hsh5Ali5RzFF5wqtRyxwJbBYt0PG4bjjXc9jLn3OKX811OLnuPnZZ.enwSf61Wj2qpUk9MUQtJHQIUaokdgjrapaCKuhra5ktV4xwHpPROaZoL0atuBwUfk.WvMG6MRo6DhkK4SPiV2Q0k0nbTbu7VcBuV7Sc5m6f23Kn.0',
    'wzws_cid': 'e91c1dc381fcbb4b91ff906c6d95a1c41ab30061d29f0800fd77e64ec92604955b83a48d1e3647c10a07b874337affd037deeb44c4c1a45e22267cc722975b986c64d1a7386cb49ba9b0f6a14e7d17950feb2bf9b97d1626ce8ab06ba9a3b31ef034742417dcb96aedfd456dbc859c65'
}

def add_cookies_to_driver(driver, cookies):
    """
    向浏览器添加Cookie
    
    Args:
        driver: Selenium WebDriver实例
        cookies: Cookie数据：
            - 字典格式：{'name1': 'value1', 'name2': 'value2'}
    """
    # 注意：调用本函数前，需先 driver.get(base_url) 一次以建立同域上下文
    
    try:
        # 如果是字典格式
        if isinstance(cookies, dict):
            print("添加字典格式的Cookie...")
            for name, value in cookies.items():
                # 添加完整的Cookie对象，包括domain和path
                cookie_dict = {
                    'name': name,
                    'value': value,
                    'domain': '.court.gov.cn',  # 使用点号开头的域名，可以匹配所有子域名
                    'path': '/',
                    'secure': True,  # HTTPS网站
                    'httpOnly': False
                }
                try:
                    driver.add_cookie(cookie_dict)
                    # print(f"  ✓ 添加Cookie: {name}")
                except Exception as e:
                    print(f"  ✗ 添加Cookie失败 {name}: {str(e)}")
                    # 如果失败，尝试不设置domain
                    try:
                        driver.add_cookie({'name': name, 'value': value, 'path': '/'})
                        print(f"  ✓ 添加Cookie (简化): {name}")
                    except:
                        pass
        
        print("Cookie添加成功！")
        
        # 不需要刷新，让调用者决定何时访问页面
        # Cookie已经添加，下次访问页面时会自动带上
        
        return True
        
    except Exception as e:
        print(f"添加Cookie时出错: {str(e)}")
        return False


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


def _ensure_captcha_loaded(driver, max_tries: int = 5, wait_secs: float = 1.0) -> bool:
    """
    检测验证码图片是否成功加载（不进行任何刷新或 src 修改）。
    """
    wait = WebDriverWait(driver, 10)
    try:
        img = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img")))
    except Exception:
        return False

    def _loaded() -> bool:
        try:
            return driver.execute_script(
                "var i=arguments[0];return !!(i && i.complete && i.naturalWidth>0);", img
            )
        except Exception:
            return False

    # 已加载则返回
    if _loaded():
        return True

    # # 反复刷新 src，保持在同一页面会话内，避免 400
    # for _ in range(max_tries):
    #     try:
    #         driver.execute_script(
    #             "var i=arguments[0];"
    #             "if(i&&i.src){"
    #             "  var u=new URL(i.src, window.location.href);"
    #             "  u.searchParams.set('t', Date.now().toString());"
    #             "  i.src=u.toString();"
    #             "}", img
    #         )
    #     except Exception:
    #         pass
    #     time.sleep(wait_secs)
    #     if _loaded():
    #         return True
    return False


def search_zxgk(person_name: str, id_number: str):
    _clear_proxy_env_vars()
    chrome_options = _build_chrome_options()
    driver = None

    base_url = "https://zxgk.court.gov.cn/zhzxgk/"
    try:
        print(f"正在打开：{base_url}")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        
        # 先访问页面，然后添加cookie（必须在访问页面后才能设置cookie）
        driver.get(base_url)
        time.sleep(2)  # 等待页面加载

        input("按回车继续：")
        
        # 如果提供了cookie，添加cookie
        cookies = DEFAULT_COOKIES
        if cookies:
            print("正在添加Cookie...")
            # 在已访问的页面上添加cookie（不再二次导航，不刷新）
            add_cookies_to_driver(driver, cookies)

        wait = WebDriverWait(driver, 12)

        # 姓名输入框（图片中显示 id="pName"）
        name_input = None
        for by_, sel in [
            (By.CSS_SELECTOR, "#pName"),
            (By.XPATH, '//input[@id="pName" or @name="pName"]'),
            (By.XPATH, '//label[contains(.,"被执行人姓名") or contains(.,"被执行人姓名/名称")]/following::input[1]'),
        ]:
            try:
                name_input = wait.until(EC.presence_of_element_located((by_, sel)))
                if name_input:
                    break
            except Exception:
                continue
        if not name_input:
            raise RuntimeError("未找到姓名输入框（#pName）")

        # 证件号输入框（图片显示 id="pCardNum"）——可选
        card_input = None
        if id_number:
            for by_, sel in [
                (By.CSS_SELECTOR, "#pCardNum"),
                (By.XPATH, '//input[@id="pCardNum" or @name="pCardNum"]'),
                (By.XPATH, '//label[contains(.,"身份证号码") or contains(.,"组织机构代码")]/following::input[1]'),
            ]:
                try:
                    card_input = wait.until(EC.presence_of_element_located((by_, sel)))
                    if card_input:
                        break
                except Exception:
                    continue

        # 输入
        time.sleep(0.3)
        name_input.clear()
        name_input.send_keys(person_name)
        time.sleep(0.5)
        if id_number and card_input:
            card_input.clear()
            card_input.send_keys(id_number)

        # 确保验证码图片可见/已加载；如未加载，程序尝试在同源会话内刷新 src 避免 400
        if not _ensure_captcha_loaded(driver):
            print("提示：验证码图片未能成功加载，我将继续提示你手动点击图片刷新。若仍失败，可尝试刷新页面后重试。")

        # 验证码：要求人工在页面第三个输入框里填写
        print("\n请在页面中手动输入验证码，完成后回到终端按回车继续...")
        try:
            input("按回车继续：")
        except KeyboardInterrupt:
            pass

        # 点击查询按钮（图片中 button.class='btn btn-zxgk btnn-block' 或 onclick 包含 search）
        search_btn = None
        for by_, sel in [
            (By.CSS_SELECTOR, "button.btn.btn-zxgk.btnn-block"),
            (By.XPATH, '//button[contains(@onclick,"search")]'),
        ]:
            try:
                search_btn = wait.until(EC.element_to_be_clickable((by_, sel)))
                if search_btn:
                    break
            except Exception:
                continue
        if not search_btn:
            raise RuntimeError("未找到查询按钮")

        driver.execute_script("arguments[0].click();", search_btn)
        time.sleep(3)  # 等待结果区域渲染

        # 判断是否验证码错误/过期
        page_text = driver.page_source
        # 常见提示
        err_keywords = ["验证码错误", "验证码已过期", "输入验证码"]
        has_error = any(kw in page_text for kw in err_keywords)

        # 截图与 JSON 写入
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        save_dir = os.path.join(desktop_path, person_name)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        # 计算页面尺寸，确保截取全屏
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
                max_w = min(total_width + 100, 3840)
                max_h = min(total_height + 200, 21600)
                if total_width > viewport_width or total_height > viewport_height:
                    driver.set_window_size(max_w, max_h)
                    time.sleep(1.5)
            driver.execute_script("window.scrollTo(0, 0);")
        except Exception:
            pass
        screenshot_path = os.path.join(save_dir, f"ZXGK_查询_{person_name}_{ts}.png")
        driver.save_screenshot(screenshot_path)
        print(f"截图已保存：{screenshot_path}")

        # 结果简单判断：若页面存在“查询结果”或出现数据表格则认为有结果，否则按可能的错误/无结果处理
        has_result = ("查询结果" in page_text) or ("被执行人" in page_text and "姓名" in page_text)

        record = {
            "item": "ZXGK_被执行人查询",
            "url": base_url,
            "name": person_name,
            "id_number": id_number,
            "ret_url": driver.current_url,
            "has_result": has_result and not has_error,
            "screenshot": screenshot_path,
            "queried_at": ts,
            "note": ("验证码可能错误或过期" if has_error else "")
        }

        json_path = os.path.join(save_dir, f"{person_name}.json")
        try:
            existing_records = load_records(json_path)
            updated_records = upsert_record(existing_records, record)
            write_records(json_path, updated_records)
            print(f"查询结果已写入/更新：{json_path}")
        except Exception as write_err:
            print(f"写入JSON时出错：{write_err}")

        # 简要输出
        print("\n================ 结果摘要 ================")
        print(f"页面链接：{driver.current_url}")
        if has_error:
            print("提示：验证码可能错误或已过期，请重新输入再查。")
        elif has_result:
            print("查询结果：已返回匹配数据（详见页面与截图）。")
        else:
            print("查询结果：未检测到明显的结果数据。")
        print("=========================================")

        return record

    except Exception as e:
        print(f"发生错误：{e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            print("操作完成")


if __name__ == "__main__":
    # 支持仅传姓名（身份证号可选）；交互模式下身份证号可留空
    p_name = None
    p_id = ""
    if len(sys.argv) >= 2:
        p_name = sys.argv[1].strip()
        if len(sys.argv) >= 3:
            p_id = sys.argv[2].strip()
    else:
        p_name = input("请输入被执行人姓名（必填）：").strip()
        p_id = input("请输入身份证号/组织机构代码（可留空）：").strip()
    if not p_name:
        print("姓名为空，程序退出。")
        sys.exit(1)

    search_zxgk(p_name, p_id)
