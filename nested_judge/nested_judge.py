#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一入口：先用 qcc_nested 爬取股东结构，再用 test_nested 计算最终受益人
"""

import importlib
import sys

from qcc_nested import search_and_screenshot, DEFAULT_COOKIES
from test_nested import ShareholderCalculator


def build_calculator_from_payload(payload):
    calculator = ShareholderCalculator()
    direct_shareholders = payload.get("direct_shareholders") or {}
    entity_structure = payload.get("entity_structure") or {}
    
    for name, percentage in direct_shareholders.items():
        try:
            calculator.add_direct_shareholder(name, float(percentage))
        except (TypeError, ValueError):
            continue
    
    for entity, holders in entity_structure.items():
        if not isinstance(holders, dict):
            continue
        normalized = {}
        for sub_name, sub_percentage in holders.items():
            try:
                normalized[sub_name] = float(sub_percentage)
            except (TypeError, ValueError):
                continue
        if normalized:
            calculator.set_entity_structure(entity, normalized)
    
    return calculator


def analyze_company(name: str):
    print(f"开始处理公司：{name}")
    crawl_result = search_and_screenshot(name, cookies=DEFAULT_COOKIES, save_to_desktop=True)
    if not crawl_result:
        raise RuntimeError("爬虫失败，无法获取股东信息。")
    
    payload = crawl_result.get("calculator_input")
    if not payload:
        raise RuntimeError("爬虫结果中没有 calculator_input 数据。")
    
    if not crawl_result.get("top_shareholder"):
        legal_rep = crawl_result.get("legal_representative")
        if legal_rep:
            crawl_result["top_shareholder"] = legal_rep
    calculator = build_calculator_from_payload(payload)
    
    print("\n=== 股东结构 ===")
    calculator.print_detailed_analysis()
    
    print("\n=== 主要受益人 (>=30%) ===")
    major = calculator.get_major_shareholders()
    if major:
        for person, percentage in major:
            print(f"  - {person}: {percentage:.2f}%")
    else:
        print("  无")


def main():
    if len(sys.argv) > 1:
        company_name = sys.argv[1]
    else:
        company_name = input("请输入需要计算的公司名称: ").strip()
    
    if not company_name:
        print("未输入公司名称，程序退出。")
        sys.exit(1)
    
    try:
        analyze_company(company_name)
    except Exception as exc:
        print(f"处理失败: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
