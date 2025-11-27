#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企查查搜索爬虫 - 搜索公司并截图保存
支持通过Cookie保持登录状态

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
from urllib.parse import quote
from datetime import datetime

# 默认Cookie（已写死）
# zjfzzq
# DEFAULT_COOKIES = {
#     'QCCSESSID': 'a3a0938745bbbdb7c2473224c9',
#     'acw_tc': '0a47315117639518404767680ee2c18cbaa424297028f72522b631fee471e2',
#     'qcc_did': '17e0aa6e-c8ea-48f8-b245-99ac2a5415d3'
# }

DEFAULT_COOKIES = {
    'QCCSESSID': '5c275beff01878a20dd8b71433',
    'acw_tc': '0a47308817639535328167636ee8eba42c9b021790f9534053261509a55aa1',
    'qcc_did': '11b92845-5179-4bed-8afd-82b0ace93c60'
}

# cyx
# DEFAULT_COOKIES = {
#     'QCCSESSID': '6c3a0ca7a7904adb0186ece71f',
#     'acw_tc': '0a47308817634484007275684ee92c773e374c03821f5ca8aae7a7a5066107',
#     'qcc_did': '11b92845-5179-4bed-8afd-82b0ace93c60'
# }

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
    time.sleep(3)  # 等待页面完全加载
    
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
                    print(f"  ✓ 添加Cookie: {name}")
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
        time.sleep(2)
        
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
            time.sleep(2)
        
        # 构建搜索URL
        search_url = f"https://www.qcc.com/web/search?key={quote(search_query)}"
        print(f"正在访问搜索页面: {search_url}")
        driver.get(search_url)
        
        # # 等待页面加载
        print("等待页面加载...")
        time.sleep(5)  # 企查查可能需要更长的加载时间
        
        # 检查是否需要登录（如果cookie无效）
        try:
            # 检查是否有登录提示或验证码
            login_elements = driver.find_elements(By.CSS_SELECTOR, '.login, .verify, [class*="login"], [class*="verify"]')
            if login_elements:
                print("⚠️  检测到可能需要登录，请手动登录后按回车继续...")
                input("登录完成后按回车继续...")
                # 如果设置了保存cookie，保存登录后的cookie
                if save_cookies:
                    try:
                        cookies = driver.get_cookies()
                        with open('qcc_cookies.json', 'w', encoding='utf-8') as f:
                            json.dump(cookies, f, indent=2, ensure_ascii=False)
                        print(f"Cookie已保存到: qcc_cookies.json")
                    except Exception as e:
                        print(f"保存Cookie时出错: {str(e)}")
        except:
            pass
        
        # 查找搜索结果链接（企查查的结果通常在第一个）
        print("正在查找搜索结果...")
        time.sleep(2)
        
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
                for elem in elements:
                    href = elem.get_attribute('href')
                    text = elem.text.strip()
                    if href and ('/firm/' in href or '/company/' in href) and text:
                        result_link = href
                        print(f"找到结果链接: {text}")
                        print(f"链接URL: {href}")
                        break
                if result_link:
                    break
            except Exception as e:
                continue
        
        # 如果没找到链接，使用当前页面
        if not result_link:
            print("未找到特定结果链接，将截图当前搜索结果页面")
            result_link = driver.current_url
        else:
            # 访问结果链接
            print(f"\n正在访问结果页面: {result_link}")
            driver.get(result_link)
            time.sleep(3)
        
        # 滚动页面确保内容加载完整
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 提取法定代表人名字
        print("\n正在提取法定代表人信息...")
        legal_representative = None
        try:
            # 等待页面加载
            time.sleep(2)
            
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
            except Exception as e:
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
        try:
            # 等待页面加载
            wait = WebDriverWait(driver, 10)
            
            # 尝试点击"股东信息"标签页
            shareholder_tab_selectors = [
                (By.XPATH, '//a[contains(text(), "股东信息")]'),
                (By.XPATH, '//a[contains(@href, "partner")]'),
                (By.CSS_SELECTOR, '.tablist a[href*="partner"]'),
                (By.CSS_SELECTOR, '.tablist a'),
                (By.CSS_SELECTOR, 'a[href*="股东信息"]'),
            ]
            
            shareholder_tab_clicked = False
            for selector_type, selector in shareholder_tab_selectors:
                try:
                    if selector_type == By.XPATH:
                        elements = driver.find_elements(selector_type, selector)
                    else:
                        elements = driver.find_elements(selector_type, selector)
                    
                    for elem in elements:
                        text = elem.text.strip()
                        href = elem.get_attribute('href') or ''
                        if '股东' in text or 'partner' in href.lower() or '股东' in href:
                            # print(f"找到股东信息标签: {text}")
                            driver.execute_script("arguments[0].click();", elem)
                            time.sleep(2)  # 等待标签页内容加载
                            shareholder_tab_clicked = True
                            break
                    if shareholder_tab_clicked:
                        break
                except Exception as e:
                    continue
            
            # 等待表格加载
            time.sleep(2)
            
            # 只读取第一行数据（第一行的持股比例一定是最高的）
            try:
                # 根据HTML结构提取第一行的股东名称和持股比例
                # 股东名称在: table.ntable tr td.left span.name a
                # 持股比例在: table.ntable tr td.right span.has-stock span
                
                # 提取第一行的股东名称（在 a 标签中）
                shareholder_name_selectors = [
                    (By.CSS_SELECTOR, 'table.ntable tr:first-of-type td.left span.name a'),
                    (By.CSS_SELECTOR, 'table.ntable tr td.left span.name a'),
                    (By.CSS_SELECTOR, 'table.ntable tr td.left.has-son-td span.name a'),
                    (By.CSS_SELECTOR, '.app-tree-table tr td.left span.name a'),
                ]
                
                for selector_type, selector in shareholder_name_selectors:
                    try:
                        name_elements = driver.find_elements(selector_type, selector)
                        if name_elements:
                            # 取第一个（第一行）
                            max_shareholder = name_elements[0].text.strip()
                            # print(f"找到股东名称: {max_shareholder}")
                            break
                    except Exception as e:
                        continue
                
                # 提取第一行的持股比例
                ratio_selectors = [
                    (By.CSS_SELECTOR, 'table.ntable tr:first-of-type td.right span.has-stock span'),
                    (By.CSS_SELECTOR, 'table.ntable tr td.right span.has-stock span'),
                    (By.CSS_SELECTOR, '.app-tree-table tr td.right span.has-stock span'),
                ]
                
                for selector_type, selector in ratio_selectors:
                    try:
                        ratio_elements = driver.find_elements(selector_type, selector)
                        if ratio_elements:
                            # 取第一个（第一行）
                            ratio_text = ratio_elements[0].text.strip()
                            if '%' in ratio_text:
                                try:
                                    max_ratio = float(ratio_text.replace('%', ''))
                                    # print(f"找到持股比例: {max_ratio}%")
                                    break
                                except ValueError:
                                    pass
                    except Exception as e:
                        continue
            except Exception as e:
                print(f"提取数据时出错: {str(e)}")
                pass
            
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
            
        except Exception as e:
            print(f"提取持股比例时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
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
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        
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
                    "top_shareholding_ratio": f"{max_ratio}%" if max_ratio > 0 else ""
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
            'screenshot_path': filepath
        }
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if driver:
            print("\n正在关闭浏览器...")
            time.sleep(2)
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

    # input("按回车继续...")
    
    result = search_and_screenshot(test_query, cookies=cookies, save_to_desktop=True, save_cookies=False)
    


    sys.exit(0 if result else 1)

