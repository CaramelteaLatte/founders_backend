#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一入口：先用 qcc_nested 爬取股东结构，再用 test_nested 计算最终受益人
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from qcc_nested import search_and_screenshot, DEFAULT_COOKIES
from storage_utils import load_records, upsert_record, write_records
from test_nested import ShareholderCalculator


def _company_json_path(company_name: str) -> Path:
    desktop = Path.home() / "Desktop"
    return desktop / company_name / f"{company_name}.json"


def _persist_nested_judge_record(
    company_name: str,
    result_url: str | None,
    ultimate_shareholders: List[Dict[str, float]],
    major_shareholders: List[Dict[str, float]],
) -> Path:
    json_path = _company_json_path(company_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    record = {
        "item": "nestedjudge_穿透计算",
        "name": company_name,
        "ret_url": result_url,
        "data": {
            "ultimate_shareholders": ultimate_shareholders,
            "major_shareholders": major_shareholders,
        },
        "queried_at": timestamp,
    }
    existing_records = load_records(json_path)
    updated_records = upsert_record(existing_records, record)
    write_records(json_path, updated_records)
    return json_path


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
    json_path: Optional[Path] = None
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
    
    ultimate = calculator.calculate_ultimate_ownership()
    ultimate_list = [
        {"name": person, "percentage": round(percentage, 4)}
        for person, percentage in sorted(ultimate.items(), key=lambda x: x[1], reverse=True)
    ]
    
    print("\n=== 主要受益人 (>=30%) ===")
    major: List[Tuple[str, float]] = calculator.get_major_shareholders()
    major_list = [
        {"name": person, "percentage": round(percentage, 4)}
        for person, percentage in major
    ]
    if major_list:
        for entry in major_list:
            print(f"  - {entry['name']}: {entry['percentage']:.2f}%")
    else:
        print("  无")
    
    try:
        json_path = _persist_nested_judge_record(
            name,
            crawl_result.get("result_url"),
            ultimate_list,
            major_list,
        )
        print(f"\n分析结果已写入：{json_path}")
    except Exception as exc:
        print(f"\n写入 nested_judge 结果失败: {exc}")
    
    return {
        "legal_representative": crawl_result.get("legal_representative"),
        "major_shareholders": major,
        "ultimate_shareholders": ultimate_list,
        "result": crawl_result,
        "json_path": str(json_path) if json_path else None,
    }


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
