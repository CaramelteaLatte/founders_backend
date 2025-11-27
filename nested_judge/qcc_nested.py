#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企查查搜索爬虫 - 搜索公司并截图保存
支持通过Cookie保持登录状态
读取多层股东结构返回json

https://www.qcc.com/web/search?key=%E5%AE%87%E6%A0%91%E7%A7%91%E6%8A%80%E8%82%A1%E4%BB%BD%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8

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
import re
import random
from urllib.parse import quote
from datetime import datetime
from typing import Any, Dict, List

# 默认Cookie（已写死）
# 公司的cookie。。。。为什么不开一个团体的账号呢。这会导致这个账号很容易在爬虫的时候出问题
# 每次要先登录qcc，修改cookie
# 不能并发，这个账号会被退出
DEFAULT_COOKIES = {
    'QCCSESSID': 'a1254941d8848e0a4f88c78062',
    'acw_tc': '1a0c599817642045157114141ed671663c3b7d38ff7ef72a677519972f8e05',
    'qcc_did': '11b92845-5179-4bed-8afd-82b0ace93c60'
}

# cyx
# DEFAULT_COOKIES = {
#     'QCCSESSID': '6c3a0ca7a7904adb0186ece71f',
#     'acw_tc': '0a47308817634484007275684ee92c773e374c03821f5ca8aae7a7a5066107',
#     'qcc_did': '11b92845-5179-4bed-8afd-82b0ace93c60'
# }


def _looks_like_natural_person(name: str) -> bool:
    """Heuristic similar to ShareholderCalculator for classifying自然人."""
    if not name:
        return False
    indicators = ['公司', '基金', '合伙', '企业', '银行', '保险', '信托', '资管']
    return not any(indicator in name for indicator in indicators)


def _parse_percentage(raw_text: str):
    """Convert textual ratio to float."""
    if not raw_text:
        return None
    text = raw_text.replace('％', '%').replace('﹪', '%')
    match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    digits = text.replace('%', '').replace('约', '').replace('~', '').replace('<', '').replace('>', '')
    digits = digits.replace('少于', '').replace('超过', '').replace('以上', '').replace('以下', '').strip()
    digits = digits.replace(',', '')
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def _human_pause(min_delay: float = 0.6, max_delay: float = 1.4):
    """Sleep a random amount of time to mimic human browsing."""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


def _extract_first_text(element, selectors: List[str]) -> str:
    """Return the first non-empty text within the given selectors for element."""
    for selector in selectors:
        try:
            matches = element.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            continue
        for match in matches:
            try:
                text = match.text.strip()
            except Exception:
                text = ''
            if text:
                return text
    return ''


def _expand_shareholder_section(driver):
    """Try to expand shareholder tables so all rows are visible."""
    keyword_variants = ["查看更多", "查看全部", "更多股东", "展开", "加载更多"]
    css_selectors = ['.show-more', '.more-btn', '.table-more-btn', '.btn-more']
    for selector in css_selectors:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            buttons = []
        for btn in buttons:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    driver.execute_script("arguments[0].click();", btn)
                    _human_pause(0.5, 1.2)
            except Exception:
                continue
    for keyword in keyword_variants:
        for _ in range(2):
            try:
                button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//a[contains(text(), '{keyword}')] | //button[contains(text(), '{keyword}')]")
                    )
                )
                driver.execute_script("arguments[0].click();", button)
                _human_pause(0.6, 1.3)
            except Exception:
                break


def _scrape_shareholders(driver) -> List[Dict[str, Any]]:
    """Collect all shareholder rows (name + percentage)."""
    _expand_shareholder_section(driver)
    
    # 首先定位到股东信息区域（根据HTML结构：section#partner.company-partner）
    partner_section = None
    section_selectors = [
        'section#partner.company-partner',
        'section.company-partner',
        'section#partner',
        '[id="partner"]',
    ]
    
    for selector in section_selectors:
        try:
            sections = driver.find_elements(By.CSS_SELECTOR, selector)
            for section in sections:
                if section.is_displayed():
                    partner_section = section
                    print(f"找到股东信息区域: {selector}")
                    break
            if partner_section:
                break
        except Exception:
            continue
    
    # 如果没有找到专门的股东区域，尝试在整个页面查找
    search_root = partner_section if partner_section else driver
    
    # 在股东区域内查找表格（根据HTML结构：.app-tree-table table.ntable）
    row_selectors = [
        '.app-tree-table table.ntable tr',  # 优先使用精确路径
        'section#partner table.ntable tr',
        'section.company-partner table.ntable tr',
        'table.ntable tr',
        '.partner-table tr',
        '.partner-list tr',
    ]
    
    # 股东名称选择器（根据HTML结构：td .td-coy.partner-app-tdcoy .name a）
    name_selectors = [
        'td .td-coy.partner-app-tdcoy .name a',  # 最精确的路径
        'td .td-coy .name a',
        'td .partner-app-tdcoy .name a',
        'td.left .name a',
        'td .name a',
        'td.left span.name a',
        'td.left span a',
        'td:nth-of-type(2) .name a',
        'td:nth-of-type(2) a',
    ]
    
    # 持股比例选择器
    ratio_selectors = [
        'td.right span.has-stock span',
        'td.right .has-stock',
        'td:nth-of-type(3) span',
        'td:nth-of-type(3)',
        '.has-stock span',
        '.partner-percent',
        '.percent',
    ]
    
    seen: Dict[str, Dict[str, Any]] = {}
    
    for selector in row_selectors:
        try:
            rows = search_root.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            rows = []
        
        if not rows:
            continue
        
        print(f"使用选择器 {selector} 找到 {len(rows)} 行")
        
        for row in rows:
            try:
                if not row.is_displayed():
                    continue
            except Exception:
                continue
            
            # 验证这一行是否在股东信息表格中（必须包含td单元格）
            cells = row.find_elements(By.CSS_SELECTOR, 'td')
            if not cells or len(cells) < 2:
                continue
            
            # 提取股东名称（优先从 .name a 中提取）
            name = _extract_first_text(row, name_selectors)
            if not name:
                # 备用方案：从第一个包含链接的单元格提取
                try:
                    name_cell = cells[1] if len(cells) > 1 else cells[0]
                    name_link = name_cell.find_element(By.CSS_SELECTOR, 'a')
                    if name_link:
                        name = name_link.text.strip()
                except Exception:
                    try:
                        name = cells[1].text.strip() if len(cells) > 1 else cells[0].text.strip()
                    except Exception:
                        name = ''
            
            # 过滤掉明显不是股东名称的内容（如企业动态、变更记录等）
            if not name or any(keyword in name for keyword in ['变更', '变更前', '变更后', '企业名称', '日期', '2022-', '2023-', '2024-', '2025-']):
                continue
            
            # 提取持股比例
            ratio_text = _extract_first_text(row, ratio_selectors)
            ratio = _parse_percentage(ratio_text)
            if ratio is None:
                # 尝试从整行文本中提取
                ratio = _parse_percentage(row.text)
            
            # 验证持股比例是否合理（0-100之间）
            if ratio is None or ratio < 0 or ratio > 100:
                continue
            
            entry = {
                "name": name,
                "percentage": ratio,
                "type": "natural" if _looks_like_natural_person(name) else "entity"
            }
            existing = seen.get(name)
            if existing is None or ratio > existing["percentage"]:
                seen[name] = entry
                print(f"  提取股东: {name} ({ratio}%)")
        
        # 如果找到了股东数据，就不需要尝试其他选择器了
        if seen:
            break
    
    shareholders = list(seen.values())
    shareholders.sort(key=lambda item: item["percentage"], reverse=True)
    print(f"共提取 {len(shareholders)} 位股东")
    return shareholders


def _navigate_to_company_page(driver, search_query: str):
    """Search for the company and navigate to the first result page."""
    search_url = f"https://www.qcc.com/web/search?key={quote(search_query)}"
    print(f"正在访问搜索页面: {search_url}")
    driver.get(search_url)
    _human_pause(2.0, 3.5)
    
    print("正在查找搜索结果...")
    result_link = None
    result_selectors = [
        (By.CSS_SELECTOR, '.search-result-item a'),
        (By.CSS_SELECTOR, '.search-item a'),
        (By.CSS_SELECTOR, '.result-item a'),
        (By.CSS_SELECTOR, 'a[href*="/firm/"]'),
        (By.CSS_SELECTOR, 'a[href*="/company/"]'),
        (By.CSS_SELECTOR, '.main-list a'),
    ]
    
    for selector_type, selector in result_selectors:
        try:
            elements = driver.find_elements(selector_type, selector)
        except Exception:
            elements = []
        for elem in elements:
            try:
                href = elem.get_attribute('href')
            except Exception:
                href = ''
            text = elem.text.strip() if elem.text else ''
            if href and ('/firm/' in href or '/company/' in href) and text:
                result_link = href
                print(f"找到结果链接: {text}")
                print(f"链接URL: {href}")
                break
        if result_link:
            break
    
    if not result_link:
        print("未找到特定结果链接，将使用当前搜索结果页面。")
        result_link = driver.current_url
    else:
        print(f"\n正在访问结果页面: {result_link}")
        driver.get(result_link)
        _human_pause(2.5, 4.0)
    
    return search_url, result_link


def _collect_shareholder_structure(driver, company_name: str, visited=None, cache=None):
    """Recursively collect shareholder data for company and nested entities."""
    normalized_name = (company_name or "").strip()
    if not normalized_name:
        return None
    
    if visited is None:
        visited = set()
    if cache is None:
        cache = {}
    
    if normalized_name in cache:
        print(f"缓存命中: {normalized_name}")
        return cache[normalized_name]
    
    if normalized_name in visited:
        print(f"检测到循环引用，跳过 {normalized_name}")
        return None
    
    visited.add(normalized_name)
    _human_pause(0.8, 1.6)
    try:
        search_url, page_url = _navigate_to_company_page(driver, normalized_name)
    except Exception as nav_err:
        print(f"跳转到 {normalized_name} 页面失败: {nav_err}")
        visited.discard(normalized_name)
        return None
    
    shareholders = _scrape_shareholders(driver)
    direct_shareholders = {entry["name"]: entry["percentage"] for entry in shareholders}
    entity_structure: Dict[str, Dict[str, float]] = {}
    
    for entry in shareholders:
        sub_name = entry.get("name")
        if entry.get("type") == "natural" or not sub_name:
            continue
        print(f"\n发现非自然人股东 {sub_name}，继续穿透查询...")
        _human_pause(1.0, 2.2)
        sub_data = _collect_shareholder_structure(driver, sub_name, visited, cache)
        if not sub_data:
            print(f"无法获取 {sub_name} 的股东信息，跳过。")
            continue
        sub_direct = sub_data.get("direct_shareholders", {})
        if sub_direct:
            entity_structure[sub_name] = sub_direct
        # 合并更深层的结构
        for entity, holders in sub_data.get("entity_structure", {}).items():
            if entity not in entity_structure:
                entity_structure[entity] = holders
    
    payload = {
        "search_url": search_url,
        "page_url": page_url,
        "shareholders": shareholders,
        "direct_shareholders": direct_shareholders,
        "entity_structure": entity_structure
    }
    
    cache[normalized_name] = payload
    visited.discard(normalized_name)
    return payload

def add_cookies_to_driver(driver, cookies):
    """
    向浏览器添加Cookie
    
    Args:
        driver: Selenium WebDriver实例
        cookies: Cookie数据：
            - 字典格式：{'name1': 'value1', 'name2': 'value2'}
    """
    # 先访问网站根域名，才能设置cookie
    print("正在访问企查查首页以设置Cookie...")
    driver.get("https://www.qcc.com")
    _human_pause(2.5, 4.0)  # 等待页面完全加载
    
    try:
        # 如果是字典格式
        if isinstance(cookies, dict):
            print("添加字典格式的Cookie...")
            for name, value in cookies.items():
                # 添加完整的Cookie对象，包括domain和path
                cookie_dict = {
                    'name': name,
                    'value': value,
                    'domain': '.qcc.com',  # 使用点号开头的域名，可以匹配所有子域名
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
        
        # 刷新页面让Cookie生效
        print("刷新页面以应用Cookie...")
        driver.refresh()
        _human_pause(1.2, 2.2)
        
        # 验证Cookie是否生效（可选）
        current_cookies = driver.get_cookies()
        # print(f"当前浏览器共有 {len(current_cookies)} 个Cookie")
        
        return True
        
    except Exception as e:
        print(f"添加Cookie时出错: {str(e)}")
        return False

def search_and_screenshot(search_query, cookies=None, save_to_desktop=True, save_cookies=False):
    """
    在企查查搜索公司并截图保存
    
    Args:
        search_query: 要搜索的公司名
        cookies: Cookie数据：
            - 字典: {'name1': 'value1', 'name2': 'value2'}
        save_to_desktop: 是否保存到桌面，默认True
        save_cookies: 是否保存当前cookie到文件，默认False
    """
    # 清除代理环境变量
    proxy_vars = ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']
    for var in proxy_vars:
        if var in os.environ:
            del os.environ[var]
    
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # 明确禁用代理
    chrome_options.add_argument('--no-proxy-server')
    chrome_options.add_argument('--proxy-server=direct://')
    chrome_options.add_argument('--proxy-bypass-list=*')
    
    # 设置用户代理（使用更真实的User-Agent）
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 禁用自动化检测（重要！）
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 添加额外的反检测措施
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    
    driver = None
    try:
        # 初始化浏览器
        print("正在初始化浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        
        # 执行JavaScript隐藏webdriver特征（重要！）
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            '''
        })
        
        # 如果提供了cookie，先添加cookie
        if cookies:
            print("正在添加Cookie...")
            add_cookies_to_driver(driver, cookies)
            _human_pause(1.5, 2.5)
        
        shareholder_cache: Dict[str, Dict[str, Any]] = {}
        company_graph = _collect_shareholder_structure(driver, search_query, visited=set(), cache=shareholder_cache)
        if not company_graph:
            print("无法获取公司股东信息，流程终止。")
            return None
        
        shareholders = company_graph.get("shareholders", [])
        calculator_payload = {
            "direct_shareholders": company_graph.get("direct_shareholders", {}),
            "entity_structure": company_graph.get("entity_structure", {})
        }
        search_url = company_graph.get("search_url", f"https://www.qcc.com/web/search?key={quote(search_query)}")
        result_link = company_graph.get("page_url")
        if result_link:
            driver.get(result_link)
            _human_pause(1.5, 2.7)
        else:
            result_link = driver.current_url
        
        # 滚动页面确保内容加载完整
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        _human_pause(0.8, 1.5)
        driver.execute_script("window.scrollTo(0, 0);")
        _human_pause(0.8, 1.5)
        
        # 提取法定代表人名字
        print("\n正在提取法定代表人信息...")
        legal_representative = None
        try:
            # 等待页面加载
            _human_pause(1.5, 2.6)
            
            # 根据HTML结构提取法定代表人名字
            # 法定代表人在工商信息表格中，路径: table.ntable tr td.base-opertd div div.td-coy span.cont span.upside-line span a
            legal_rep_selectors = [
                (By.CSS_SELECTOR, 'table.ntable tr td.base-opertd div.td-coy span.cont span.upside-line span a'),
                (By.CSS_SELECTOR, 'table.ntable tr td.base-opertd div.td-coy a'),
                (By.CSS_SELECTOR, 'table.ntable tr:has-text("法定代表人") td.base-opertd a'),
                (By.XPATH, '//table[@class="ntable"]//tr[td[contains(text(), "法定代表人")]]//td[@class="base-opertd"]//a'),
            ]
            
            # 方法1：直接查找包含"法定代表人"的行，然后提取该行的链接
            try:
                # 查找所有表格行
                table_rows = driver.find_elements(By.CSS_SELECTOR, 'table.ntable tr')
                for row in table_rows:
                    row_text = row.text
                    if '法定代表人' in row_text:
                        # 在这一行中查找链接（法定代表人名字）
                        links = row.find_elements(By.CSS_SELECTOR, 'td.base-opertd a, td a')
                        if links:
                            legal_representative = links[0].text.strip()
                            print(f"找到法定代表人: {legal_representative}")
                            break
            except Exception:
                pass
            
            # 方法2：如果方法1没找到，使用精确选择器
            if not legal_representative:
                for selector_type, selector in legal_rep_selectors:
                    try:
                        if selector_type == By.XPATH:
                            elements = driver.find_elements(selector_type, selector)
                        else:
                            elements = driver.find_elements(selector_type, selector)
                        
                        if elements:
                            legal_representative = elements[0].text.strip()
                            print(f"找到法定代表人: {legal_representative}")
                            break
                    except Exception as e:
                        continue
            
        except Exception as e:
            print(f"提取法定代表人时出错: {str(e)}")
        
        # 提取持股比例信息，找到最高的持股比例和对应的股东名字
        print("\n正在提取持股比例信息...")
        max_shareholder = None
        max_ratio = 0.0
        if shareholders:
            max_shareholder = shareholders[0]["name"]
            max_ratio = shareholders[0]["percentage"]
        
        # 打印结果
        print("\n" + "="*60)
        print("公司信息:")
        print("="*60)
        if legal_representative:
            print(f"法定代表人名字: {legal_representative}")
        if max_shareholder and max_ratio > 0:
            print(f"最多持股股东名字: {max_shareholder}")
            print(f"持股比例: {max_ratio}%")
        if not legal_representative and not (max_shareholder and max_ratio > 0):
            print("未找到相关信息")
        print("="*60)
        if shareholders:
            print(f"共提取 {len(shareholders)} 位股东:")
            for entry in shareholders:
                label = "自然人" if entry["type"] == "natural" else "非自然人"
                print(f"  - {entry['name']}: {entry['percentage']:.2f}% ({label})")
            print("\nShareholderCalculator 可直接使用的 JSON:")
            print(json.dumps(calculator_payload, ensure_ascii=False, indent=2))
        else:
            print("未解析到股东列表")
        
        # 获取页面完整尺寸（全页截图）
        print("正在获取页面完整尺寸...")
        total_width = driver.execute_script("return Math.max(document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth);")
        total_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
        
        viewport_width = driver.execute_script("return window.innerWidth")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        print(f"页面完整尺寸: {total_width} x {total_height}")
        print(f"当前视窗尺寸: {viewport_width} x {viewport_height}")
        
        max_width = min(total_width + 100, 3840)
        max_height = min(total_height + 200, 21600)
        
        if total_width > viewport_width or total_height > viewport_height:
            print(f"调整窗口大小至: {max_width} x {max_height}")
            driver.set_window_size(max_width, max_height)
            _human_pause(1.5, 2.5)
            driver.execute_script("window.scrollTo(0, 0);")
            _human_pause(0.4, 0.9)
        
        # 截图保存
        if save_to_desktop:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        else:
            desktop_path = os.getcwd()
        
        # 创建以公司名命名的文件夹
        company_folder = os.path.join(desktop_path, search_query)
        if not os.path.exists(company_folder):
            print(f"创建文件夹: {company_folder}")
            os.makedirs(company_folder, exist_ok=True)
        else:
            print(f"使用已存在的文件夹: {company_folder}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in search_query if c.isalnum() or c in (' ', '-', '_')).strip()[:30]
        filename = f"企查查_{safe_query}_{timestamp}.png"
        filepath = os.path.join(company_folder, filename)  # 保存到公司文件夹中
        
        print(f"正在截图全页内容并保存到: {filepath}")
        driver.save_screenshot(filepath)
        
        # 将结果写入/更新到 JSON（与其他脚本统一）
        try:
            json_filename = f"{search_query}.json"
            json_filepath = os.path.join(company_folder, json_filename)
            record = {
                "item": "QCC_企查查公司查询",
                "url": f"https://www.qcc.com/web/search?key={quote(search_query)}",
                "name": search_query,
                "ret_url": result_link,
                "data": {
                    "legal_representative": legal_representative,
                    "top_shareholder": max_shareholder,
                    "top_shareholding_ratio": f"{max_ratio}%" if max_ratio > 0 else "",
                    "shareholders": shareholders,
                    "calculator_input": calculator_payload
                },
                "screenshot": filepath,
                "queried_at": timestamp
            }
            if os.path.exists(json_filepath):
                try:
                    with open(json_filepath, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = None
                if isinstance(existing, list):
                    existing.append(record)
                    data_to_write = existing
                elif isinstance(existing, dict):
                    data_to_write = [existing, record]
                else:
                    data_to_write = [record]
            else:
                data_to_write = [record]
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_write, f, indent=2, ensure_ascii=False)
            print(f"查询结果已写入/更新：{json_filepath}")
        except Exception as write_err:
            print(f"写入JSON时出错：{write_err}")
        
        print("\n" + "="*60)
        print("操作完成！")
        print("="*60)
        print(f"搜索关键词: {search_query}")
        print(f"结果页面URL: {result_link}")
        print(f"截图保存路径: {filepath}")
        print("="*60)
        
        return {
            'search_url': search_url,
            'result_url': result_link,
            'screenshot_path': filepath,
            'legal_representative': legal_representative,
            'top_shareholder': max_shareholder,
            'top_shareholding_ratio': max_ratio,
            'shareholders': shareholders,
            'calculator_input': calculator_payload
        }
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if driver:
            print("\n正在关闭浏览器...")
            _human_pause(1.0, 2.0)
            driver.quit()


if __name__ == "__main__":
    # 如果命令行提供了参数，使用命令行参数
    if len(sys.argv) > 1:
        test_query = sys.argv[1]
    else:
        # 添加输入提示
        test_query = input("请输入你要查询的公司名: ").strip()
        if not test_query:
            print("错误: 未输入公司名，程序退出")
            sys.exit(1)
    
    # Cookie设置方式（按优先级）
    cookies = DEFAULT_COOKIES
    
    print(f"\n搜索内容: {test_query}")
    print()
    
    result = search_and_screenshot(test_query, cookies=cookies, save_to_desktop=True, save_cookies=False)
    
    sys.exit(0 if result else 1)
