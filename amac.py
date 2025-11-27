#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索框爬虫 - 在中国证券投资基金业协会网站搜索并获取结果URL，然后截图保存
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import sys
import os
import json
from urllib.parse import quote
from datetime import datetime

def search_and_screenshot(search_query, save_to_desktop=True):
    """
    直接访问搜索URL，获取结果链接，访问并截图保存
    
    Args:
        search_query: 要搜索的内容
        save_to_desktop: 是否保存到桌面，默认True
    """
    # 清除代理环境变量（避免使用无效的代理）
    proxy_vars = ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']
    for var in proxy_vars:
        if var in os.environ:
            del os.environ[var]
            # print(f"已清除环境变量: {var}")
    
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 明确禁用代理（避免使用系统代理设置）
    chrome_options.add_argument('--no-proxy-server')
    chrome_options.add_argument('--proxy-server=direct://')
    chrome_options.add_argument('--proxy-bypass-list=*')
    
    # 设置用户代理
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 设置窗口大小（确保截图完整）
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = None
    try:
        # 初始化浏览器
        print("正在初始化浏览器...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()
        
        # 构建搜索URL
        search_url = f"https://www.amac.org.cn/index/qzss/?key={quote(search_query)}"
        print(f"正在访问搜索页面: {search_url}")
        driver.get(search_url)
        
        # 等待搜索结果加载
        print("等待搜索结果加载...")
        time.sleep(3)
        
        # 查找搜索结果链接
        # 根据图片描述，结果在"机构、产品搜索结果"部分，链接在h3 > a中
        wait = WebDriverWait(driver, 10)
        
        result_link = None
        result_selectors = [
            (By.CSS_SELECTOR, '#count.textList h3 a'),  # 根据图片中的结构
            (By.CSS_SELECTOR, '.textList h3 a'),
            (By.CSS_SELECTOR, '.text h3 a'),
            (By.CSS_SELECTOR, 'li h3 a'),
            (By.CSS_SELECTOR, 'a[href*="name="][href*="code="]'),  # 包含name和code参数的链接
        ]
        
        print("正在查找搜索结果链接...")
        for selector_type, selector in result_selectors:
            try:
                elements = driver.find_elements(selector_type, selector)
                for elem in elements:
                    href = elem.get_attribute('href')
                    text = elem.text.strip()
                    # 检查链接是否包含搜索关键词或code参数
                    if href and ('name=' in href or 'code=' in href) and href not in ['javascript:void(0);', '#', '']:
                        result_link = href
                        print(f"找到结果链接: {text}")
                        print(f"链接URL: {href}")
                        break
                if result_link:
                    break
            except Exception as e:
                continue
        
        # 如果没有找到结果链接，直接在当前搜索页面截图
        if not result_link:
            print("未找到搜索结果链接，将在当前搜索页面截图")
            result_link = driver.current_url  # 使用当前页面URL
        else:
            # 访问结果链接
            print(f"\n正在访问结果页面: {result_link}")
            driver.get(result_link)
            time.sleep(3)  # 等待页面加载
        
        # 滚动页面确保内容加载完整
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 提取企业信息（只有在访问了详情页时才尝试提取）
        print("\n正在提取企业信息...")
        company_info = {}
        # 只有在访问了详情页（result_link 不是搜索页URL）时才尝试提取企业信息
        if result_link and result_link != search_url:
            try:
                # 等待页面加载
                time.sleep(2)
                
                # 根据HTML结构，信息可能在以下位置：
                # 1. div.countBox li.text 或 li.text.w25（列表项结构）
                # 2. div.countBox div.text（div结构）
                # 每个元素包含 span.tit（标题）和 span（值）
                info_selectors = [
                    'div.countBox li.text',  # 列表项结构（如 li.text.w25）
                    'div.countBox li.text.w25',  # 带w25类的列表项
                    '.countBox li.text',  # 备用选择器
                    'div.countBox div.text',  # div结构（原有）
                    '.countBox div.text',  # 备用选择器
                ]
                
                info_elements = []
                for selector in info_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            info_elements = elements
                            print(f"使用选择器 '{selector}' 找到 {len(elements)} 条信息元素")
                            break
                    except Exception:
                        continue
                
                if not info_elements:
                    print("未找到信息元素，尝试更宽泛的选择器...")
                    # 最后尝试：查找所有包含 span.tit 的元素
                    try:
                        info_elements = driver.find_elements(By.CSS_SELECTOR, 'div.countBox *:has(span.tit), .countBox *:has(span.tit)')
                        if not info_elements:
                            # 如果 :has() 不支持，使用 XPath
                            info_elements = driver.find_elements(By.XPATH, '//div[contains(@class,"countBox")]//*[span[@class="tit"]]')
                    except Exception:
                        pass
                
                print(f"共找到 {len(info_elements)} 条信息元素")
                
                for element in info_elements:
                    try:
                        # 提取标题（span.tit）
                        title_elements = element.find_elements(By.CSS_SELECTOR, 'span.tit')
                        # 提取值（span，但不是span.tit）
                        value_elements = element.find_elements(By.CSS_SELECTOR, 'span:not(.tit)')
                        
                        if title_elements and value_elements:
                            title = title_elements[0].text.strip()
                            # 移除末尾的冒号
                            if title.endswith(':'):
                                title = title[:-1]
                            
                            # 获取所有值的文本（可能有多个span）
                            value = ' '.join([v.text.strip() for v in value_elements if v.text.strip()])
                            
                            if title and value:
                                company_info[title] = value
                                print(f"  {title}: {value}")
                    except Exception as e:
                        continue
                
                print(f"\n成功提取 {len(company_info)} 条企业信息")
                
            except Exception as e:
                print(f"提取企业信息时出错: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            print("当前为搜索页面，无法提取详细企业信息")
        
        # 保存企业信息到JSON文件（与 neris.py 统一格式）
        # 即使没有提取到企业信息，也保存记录（包含搜索页面信息）
        if True:  # 总是保存JSON，即使没有提取到详细信息
            try:
                # 创建以公司名命名的文件夹
                if save_to_desktop:
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                else:
                    desktop_path = os.getcwd()
                
                company_folder = os.path.join(desktop_path, search_query)
                if not os.path.exists(company_folder):
                    print(f"创建文件夹: {company_folder}")
                    os.makedirs(company_folder, exist_ok=True)
                else:
                    print(f"使用已存在的文件夹: {company_folder}")
                
                # JSON 文件名：公司名.json
                json_filename = f"{search_query}.json"
                json_filepath = os.path.join(company_folder, json_filename)
                
                # 统一的记录结构
                record = {
                    "item": "AMAC_证监会搜索",
                    "url": search_url,
                    "name": search_query,
                    "ret_url": result_link if result_link else driver.current_url,
                    "data": company_info if company_info else {"note": "未找到详情页，仅保存搜索页面截图"},
                    "queried_at": datetime.now().strftime("%Y%m%d_%H%M%S")
                }
                
                # 若已存在，则以列表形式叠加；否则创建新列表
                if os.path.exists(json_filepath):
                    try:
                        with open(json_filepath, 'r', encoding='utf-8') as f:
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
                
                with open(json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_to_write, f, indent=2, ensure_ascii=False)
                
                print(f"\n查询记录已写入/更新: {json_filepath}")
                
            except Exception as e:
                print(f"保存JSON文件时出错: {str(e)}")
        
        # 获取页面完整尺寸（全页截图）
        print("正在获取页面完整尺寸...")
        # 获取页面的总宽度和高度（使用多种方法确保获取到完整尺寸）
        total_width = driver.execute_script("return Math.max(document.body.scrollWidth, document.body.offsetWidth, document.documentElement.clientWidth, document.documentElement.scrollWidth, document.documentElement.offsetWidth);")
        total_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
        
        # 获取当前窗口大小
        viewport_width = driver.execute_script("return window.innerWidth")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        print(f"页面完整尺寸: {total_width} x {total_height}")
        print(f"当前视窗尺寸: {viewport_width} x {viewport_height}")
        
        # 设置窗口大小为页面完整尺寸（加上一些边距以确保完整显示）
        # 限制最大尺寸以避免超出屏幕
        max_width = min(total_width + 100, 3840)  # 最大宽度限制为3840
        max_height = min(total_height + 200, 21600)  # 最大高度限制为21600（足够大）
        
        if total_width > viewport_width or total_height > viewport_height:
            print(f"调整窗口大小至: {max_width} x {max_height}")
            driver.set_window_size(max_width, max_height)
            time.sleep(2)  # 等待窗口调整和页面重新渲染
            
            # 再次滚动确保所有内容加载
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
        
        # 截图保存
        if save_to_desktop:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        else:
            desktop_path = os.getcwd()
        
        # 确保文件夹已创建（如果之前没创建）
        company_folder = os.path.join(desktop_path, search_query)
        if not os.path.exists(company_folder):
            print(f"创建文件夹: {company_folder}")
            os.makedirs(company_folder, exist_ok=True)
        
        # 生成文件名（使用搜索关键词和时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in search_query if c.isalnum() or c in (' ', '-', '_')).strip()[:30]
        filename = f"证监会_{safe_query}_{timestamp}.png"
        filepath = os.path.join(company_folder, filename)  # 保存到公司文件夹中
        
        print(f"正在截图全页内容并保存到: {filepath}")
        # 使用 save_screenshot 截图（此时窗口大小已调整为页面完整尺寸）
        driver.save_screenshot(filepath)
        
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
            time.sleep(2)  # 等待一下以便查看结果
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
    
    # 测试用例
    #test_query = "杭州哲石私募基金管理有限公司"

    print(f"\n搜索内容: {test_query}")
    print()
    
    result = search_and_screenshot(test_query, save_to_desktop=True)
    
    # 返回结果供其他脚本使用
    sys.exit(0 if result else 1)

