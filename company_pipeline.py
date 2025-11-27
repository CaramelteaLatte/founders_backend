#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键流程：
1. 通过 AMAC 爬虫抓取公司信息并截图；
2. 调用 nested_judge 模块（内部使用企查查）计算法定代表人与受益所有人；
3. 对法定代表人/受益人使用 neris.py 查询失信记录并截图；
4. 使用 wenshu.py 分别以公司名、法定代表人、受益人名搜索裁判文书并截图。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional

ROOT = Path(__file__).resolve().parent
NESTED_DIR = ROOT / "nested_judge"

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(NESTED_DIR) not in sys.path:
    sys.path.append(str(NESTED_DIR))

import amac as amac_spider
from nested_judge import nested_judge as nested_processor
from nested_judge import qcc_nested

import shutil

import neris
from wenshu import search_wenshu as wenshu_search


def _deduplicate_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        trimmed = (item or "").strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        result.append(trimmed)
    return result


def _company_folder(company_name: str) -> Path:
    folder = Path.home() / "Desktop" / company_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _copy_screenshot(src_path: Optional[str], target_dir: Path, prefix: str) -> Optional[str]:
    if not src_path:
        print(f"  ✗ 没有可复制的截图（{prefix}）")
        return None
    src = Path(src_path)
    if not src.exists():
        print(f"  ✗ 截图文件不存在：{src}")
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / f"{prefix}_{src.name}"
    try:
        shutil.copy2(src, dst)
        print(f"  ✓ 截图已复制到：{dst}")
        return str(dst)
    except Exception as exc:
        print(f"  ✗ 复制截图失败：{exc}")
        return None


def _run_amac(company_name: str):
    print(f"\n==> [AMAC] 开始查询 {company_name}")
    amac_result = amac_spider.search_and_screenshot(company_name, save_to_desktop=True)
    if not amac_result:
        raise RuntimeError("AMAC 查询失败，流程终止。")
    return amac_result


def _run_nested(company_name: str):
    print(f"\n==> [Nested Judge] 通过企查查获取股东结构")
    crawl_result = qcc_nested.search_and_screenshot(
        company_name,
        cookies=qcc_nested.DEFAULT_COOKIES,
        save_to_desktop=True,
    )
    if not crawl_result:
        raise RuntimeError("企查查爬取失败，无法构建股东结构。")

    calculator_input = crawl_result.get("calculator_input") or {}
    calculator = nested_processor.build_calculator_from_payload(calculator_input)
    major_shareholders = calculator.get_major_shareholders()

    legal_rep = crawl_result.get("legal_representative")
    print(f"法定代表人: {legal_rep or '未识别'}")
    if major_shareholders:
        print("受益所有人（>=30%）：")
        for person, ratio in major_shareholders:
            print(f"  - {person}: {ratio:.2f}%")
    else:
        print("未检测到满足阈值的受益所有人。")

    return legal_rep, major_shareholders


def _run_neris_for_people(names: List[str], company_folder: Path, company_name: str):
    print("\n==> [NERIS] 开始逐个查询失信记录")
    results = []
    for name in _deduplicate_keep_order(names):
        print(f"-- 查询 {name}")
        result = neris.search_and_get_results(name, company_name=company_name)
        if result:
            _copy_screenshot(result.get("screenshot"), company_folder, f"NERIS_{name}")
        results.append((name, result))
    return results


def _run_wenshu_for_keywords(keywords: List[str], company_folder: Path, max_retries: int = 3, retry_delay: float = 2.0):
    print("\n==> [Wenshu] 开始逐个关键词搜索并截图")
    results = []
    seen = set()
    for keyword in _deduplicate_keep_order(keywords):
        normalized = keyword.strip()
        if not normalized:
            continue
        if normalized in seen:
            print(f"-- 裁判文书网搜索：{normalized}（已处理，跳过）")
            continue
        seen.add(normalized)
        print(f"-- 裁判文书网搜索：{keyword}")
        result = None
        for attempt in range(1, max_retries + 1):
            try:
                result = wenshu_search(keyword, save_to_desktop=True)
            except Exception as exc:
                print(f"  ✗ 裁判文书网查询异常（第 {attempt} 次）：{exc}")
                result = None
            if result:
                break
            if attempt < max_retries:
                print(f"  … 查询失败，准备重试（{attempt}/{max_retries}）")
                time.sleep(retry_delay)
        if not result:
            print(f"  ✗ 裁判文书网查询多次失败：{keyword}")
        if result:
            _copy_screenshot(result.get("screenshot"), company_folder, f"WENSHU_{keyword}")
        results.append((keyword, result))
    return results


def run_full_pipeline(company_name: str):
    company_folder = _company_folder(company_name)
    amac_info = _run_amac(company_name)

    legal_rep, major_shareholders = _run_nested(company_name)

    beneficiary_names = [name for name, _ in major_shareholders]
    person_targets = []
    if legal_rep:
        person_targets.append(legal_rep)
    person_targets.extend(beneficiary_names)

    neris_targets = [company_name]
    neris_targets.extend(person_targets)
    _run_neris_for_people(neris_targets, company_folder, company_name)

    wenshu_targets = [company_name]
    wenshu_targets.extend(person_targets)
    _run_wenshu_for_keywords(wenshu_targets, company_folder)

    print("\n==> 流程结束")
    return {
        "amac": amac_info,
        "legal_representative": legal_rep,
        "beneficial_owners": major_shareholders,
    }


def main():
    if len(sys.argv) >= 2:
        company_name = " ".join(sys.argv[1:]).strip()
    else:
        company_name = input("请输入公司名称：").strip()

    if not company_name:
        print("未输入公司名称，程序退出。")
        sys.exit(1)

    try:
        run_full_pipeline(company_name)
    except Exception as exc:
        print(f"流程失败：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
