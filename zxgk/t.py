# 最初始版本的留稿

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


def search_zxgk(person_name: str, id_number: str):
    _clear_proxy_env_vars()
    chrome_options = _build_chrome_options()
    driver = None

    base_url = "https://zxgk.court.gov.cn/zhzxgk/"
    try:
        print(f"正在打开：{base_url}")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        driver.get(base_url)

        wait = WebDriverWait(driver, 12)
        time.sleep(3)

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

        # 证件号输入框（图片显示 id="pCardNum"）
        card_input = None
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
        if not card_input:
            raise RuntimeError("未找到证件号输入框（#pCardNum）")

        # 输入
        time.sleep(1)
        name_input.clear()
        name_input.send_keys(person_name)
        time.sleep(1)
        card_input.clear()
        card_input.send_keys(id_number)

        # 验证码：要求人工在页面第三个输入框里填写
        print("\n请在页面中手动输入验证码（第四个输入框），完成后回到终端按回车继续...")
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
    if len(sys.argv) >= 3:
        p_name = sys.argv[1]
        p_id = sys.argv[2]
    else:
        p_name = input("请输入被执行人姓名：").strip()
        p_id = input("请输入身份证号/组织机构代码：").strip()
        if not p_name or not p_id:
            print("姓名或证件号为空，程序退出。")
            sys.exit(1)

    search_zxgk(p_name, p_id)
