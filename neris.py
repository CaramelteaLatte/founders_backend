#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSRC 失信查询爬虫（https://neris.csrc.gov.cn/shixinchaxun/）

功能:
- 打开网站，在搜索框输入“法定代表人姓名”后回车
- 自动切换到打开的新页面
- 若出现人机校验，提示用户完成校验并等待
- 完成后解析查询结果，并打印输出
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import time
import sys
import os
import json
from urllib.parse import quote


def _build_chrome_options() -> Options:
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1440,900")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # 更真实的 UA
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    # 明确禁用代理（避免本地代理导致连接失败）
    chrome_options.add_argument("--no-proxy-server")
    chrome_options.add_argument("--proxy-server=direct://")
    chrome_options.add_argument("--proxy-bypass-list=*")
    return chrome_options


def _clear_proxy_env_vars() -> None:
    for var in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        if var in os.environ:
            del os.environ[var]


def _wait_for_new_window(driver, current_handles, timeout: int = 10):
    end = time.time() + timeout
    while time.time() < end:
        if len(driver.window_handles) > len(current_handles):
            return True
        time.sleep(0.2)
    return False


def _maybe_wait_for_human_verification(driver) -> None:
    """
    检测是否出现人机验证/验证码页面，如果出现则等待用户人工完成。
    检测逻辑：页面包含“人机验证/请完成验证/验证/滑动/验证码”等字样或常见验证码控件。
    """
    page_text = driver.page_source
    keywords = ["人机验证", "请完成验证", "验证", "滑动", "captcha", "geetest", "yidun", "滑块", "安全检查"]
    need_wait = any(kw in page_text for kw in keywords)
    if need_wait:
        print("\n检测到人机验证/验证码页面，请在浏览器中手动完成验证...")
        try:
            input("验证完成后按回车继续：")
        except KeyboardInterrupt:
            pass


def _extract_results(driver):
    """
    解析结果页的两个区块：
    - 证券期货市场严重违法失信
    - 证券期货市场失信记录查询

    不同时间页面结构可能调整，这里使用多套选择器尽可能鲁棒。
    返回结构化结果 dict。
    """
    results = {
        "url": driver.current_url,
        "serious_violations": [],   # 严重违法失信
        "dishonesty_records": [],   # 失信记录
        "raw_sections": []
    }

    wait = WebDriverWait(driver, 8)
    # 等待主要容器出现（容器 class 名称可能变化，这里用多个备选）
    possible_containers = [
        (By.CSS_SELECTOR, ".contTwoBox"),
        (By.CSS_SELECTOR, ".countBox"),
        (By.CSS_SELECTOR, ".content, .giveBox"),
    ]
    container = None
    for by_, sel in possible_containers:
        try:
            container = wait.until(EC.presence_of_element_located((by_, sel)))
            if container:
                break
        except Exception:
            continue

    # 优先读取两个标题区块之后的表格/行
    # 标题通常是 h3 或者包含相应文字的元素
    section_candidates = []
    try:
        section_candidates.extend(driver.find_elements(By.XPATH, '//*[self::h2 or self::h3 or self::div][contains(.,"严重违法失信")]'))
        section_candidates.extend(driver.find_elements(By.XPATH, '//*[self::h2 or self::h3 or self::div][contains(.,"失信记录")]'))
    except Exception:
        pass

    def _parse_rows_from_section(el):
        rows = []
        # 行容器可能是 table > tr，或一系列 div.text 两列布局
        try:
            # 方式1：table 行
            trs = el.find_elements(By.CSS_SELECTOR, "table tr")
            for tr in trs:
                tds = [td.text.strip() for td in tr.find_elements(By.CSS_SELECTOR, "td")]
                txt = "  ".join([t for t in tds if t])
                if txt:
                    rows.append(txt)
        except Exception:
            pass
        try:
            # 方式2：两列 div.text
            texts = [t.text.strip() for t in el.find_elements(By.CSS_SELECTOR, ".text") if t.text.strip()]
            # 将相邻两条合并为一条记录（左列+右列）
            if len(texts) >= 2:
                for i in range(0, len(texts), 2):
                    left = texts[i]
                    right = texts[i + 1] if i + 1 < len(texts) else ""
                    rows.append(f"{left}  |  {right}")
            elif texts:
                rows.extend(texts)
        except Exception:
            pass
        return rows

    # 解析标题段落周边的内容
    for sec in section_candidates:
        try:
            title = sec.text.strip().replace("\n", " ")
            # 找到标题的父容器向下解析
            parent = sec.find_element(By.XPATH, "./ancestor::*[1]")
            rows = _parse_rows_from_section(parent)
            if rows:
                results["raw_sections"].append({"title": title, "rows": rows})
                if "严重违法" in title:
                    results["serious_violations"].extend(rows)
                elif "失信记录" in title:
                    results["dishonesty_records"].extend(rows)
        except Exception:
            continue

    # 兜底：从整个容器解析
    if not results["serious_violations"] and not results["dishonesty_records"] and container:
        rows = _parse_rows_from_section(container)
        if rows:
            results["raw_sections"].append({"title": "查询结果", "rows": rows})

    return results


def search_and_get_results(legal_name: str, company_name: str = None):
    """
    在 CSRC 失信查询网站中输入法定代表人姓名并回车，等待新页面加载；
    若出现人机验证，暂停等待用户完成；之后解析并返回查询结果。
    
    Args:
        legal_name: 法定代表人姓名（用于查询）
        company_name: 公司名称（可选，如果提供则用于文件夹和JSON文件名）
    """
    _clear_proxy_env_vars()
    chrome_options = _build_chrome_options()
    driver = None

    try:
        print("正在启动浏览器并访问: https://neris.csrc.gov.cn/shixinchaxun/")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        driver.get("https://neris.csrc.gov.cn/shixinchaxun/")

        wait = WebDriverWait(driver, 12)

        # 寻找姓名输入框（多套选择器兜底）
        input_selectors = [
            (By.CSS_SELECTOR, 'input[placeholder*="姓名"]'),
            (By.XPATH, '//label[contains(.,"姓名") or contains(.,"姓名/名称")]/following::input[1]'),
            (By.CSS_SELECTOR, '.ivu-input'),
        ]
        name_input = None
        for by_, sel in input_selectors:
            try:
                name_input = wait.until(EC.presence_of_element_located((by_, sel)))
                if name_input:
                    break
            except Exception:
                continue

        if not name_input:
            raise RuntimeError("无法定位姓名输入框，请检查页面结构是否已变更。")

        # 输入姓名并回车
        print(f"正在输入姓名并触发搜索: {legal_name}")
        name_input.clear()
        name_input.send_keys(legal_name)
        time.sleep(0.3)
        current_handles = driver.window_handles[:]
        name_input.send_keys(Keys.ENTER)

        time.sleep(2)

        # 如遇到人机验证，等待用户处理
        _maybe_wait_for_human_verification(driver)

        # 等待新窗口打开并切换
        if _wait_for_new_window(driver, current_handles, timeout=10):
            new_handles = driver.window_handles
            target_handle = list(set(new_handles) - set(current_handles))[0]
            driver.switch_to.window(target_handle)
            print("已切换到查询结果页面")
        else:
            # 有些情况下不会新开窗口，而是当前页内跳转
            print("未检测到新窗口，将继续在当前页面解析")


        # 再等待结果元素出现，获取查询结果（简化逻辑）
        time.sleep(1.0)
        try:
            no_data_el = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.noData"))
            )
            no_data_text = (no_data_el.text or "").strip()
        except Exception:
            no_data_text = ""

        page_text_sample = (driver.page_source or "")[:10000]
        has_no_data = "无符合条件记录" in no_data_text or "无符合条件记录" in page_text_sample

        print("\n" + "=" * 60)
        print("查询结果：")
        print("=" * 60)
        print(f"结果页面: {driver.current_url}")
        
        # 确定保存目录和JSON文件名：优先使用company_name，否则使用legal_name
        folder_name = company_name if company_name else legal_name
        json_filename = company_name if company_name else legal_name
            
        # 截图保存到桌面/公司名称 文件夹
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        save_dir = os.path.join(desktop_path, folder_name)
        # 仅当文件夹不存在时创建；若存在则直接使用
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        screenshot_path = os.path.join(save_dir, f"CSRC_失信查询_{legal_name}_{ts}.png")
        driver.save_screenshot(screenshot_path)
        print(f"截图已保存：{screenshot_path}")
        print("=" * 60)

        # 将查询结果落盘为 JSON（文件名：公司名称.json 或 姓名.json）
        try:
            record = {
                "item": "CSRC_失信查询",
                "url": "https://neris.csrc.gov.cn/shixinchaxun/",
                "name": legal_name,
                "has_issue": not has_no_data,
                "ret_url": driver.current_url,
                "screenshot": screenshot_path,
                "queried_at": ts
            }
            json_path = os.path.join(save_dir, f"{json_filename}.json")
            if os.path.exists(json_path):
                # 如果已有文件，尽量在原有基础上追加
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = None
                # 统一存为列表
                if isinstance(existing, list):
                    existing.append(record)
                    data_to_write = existing
                elif isinstance(existing, dict):
                    data_to_write = [existing, record]
                else:
                    data_to_write = [record]
            else:
                data_to_write = [record]
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data_to_write, f, indent=2, ensure_ascii=False)
            print(f"查询结果已写入/更新：{json_path}")
        except Exception as write_err:
            print(f"写入JSON时出错：{write_err}")

        result_payload = {
            "url": driver.current_url,
            "has_issue": not has_no_data,
            "screenshot": screenshot_path,
            "name": legal_name,
            "queried_at": ts
        }

        if has_no_data:
            print("无失信问题")
            print("=" * 60)
        else:
            print(f"查询人{legal_name}存在失信问题")

        return result_payload

    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if driver:
            # 根据你的需要：保持打开便于核对，或自动关闭
            # print("\n操作完成，浏览器保持打开以便查看。如需自动关闭，可修改脚本。")
            print("操作完成")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        name = sys.argv[1]
    else:
        name = input("请输入查询失信者姓名: ").strip()
        if not name:
            print("未输入姓名，程序退出。")
            sys.exit(1)

    search_and_get_results(name)

