"""
读取json计算受益所有人

"""

import json
import os
import sys
from typing import Dict, List, Tuple, Union, Optional

ITEM_KEYWORD = "QCC_公司查询"
FALLBACK_ITEM_KEYWORD = "QCC_企查查公司查询"

class ShareholderCalculator:
    def __init__(self):
        # 存储公司直接股东信息：{股东名称: 持股比例}
        self.direct_shareholders = {}
        # 存储非自然人股东的股权结构：{非自然人名称: {股东名称: 持股比例}}
        self.entity_structure = {}
        # 缓存最终计算结果
        self._result_cache = None
    
    def add_direct_shareholder(self, name: str, percentage: float):
        """添加直接股东"""
        self.direct_shareholders[name] = percentage
        self._result_cache = None  # 清除缓存
    
    def set_entity_structure(self, entity_name: str, shareholders: Dict[str, float]):
        """设置非自然人股东的股权结构"""
        self.entity_structure[entity_name] = shareholders.copy()
        self._result_cache = None  # 清除缓存
    
    def calculate_ultimate_ownership(self) -> Dict[str, float]:
        """计算最终的实际持股比例"""
        if self._result_cache is not None:
            return self._result_cache
        
        result = {}
        
        # 处理所有直接股东
        for shareholder, percentage in self.direct_shareholders.items():
            if self._is_natural_person(shareholder):
                # 自然人直接持股
                result[shareholder] = result.get(shareholder, 0) + percentage
            else:
                # 非自然人股东，需要穿透计算
                self._calculate_entity_ownership(shareholder, percentage, result)
        
        self._result_cache = result
        return result
    
    def _is_natural_person(self, name: str) -> bool:
        """判断是否为自然人（这里用简单规则：不包含'公司'、'基金'等字眼的视为自然人）"""
        indicators = ['公司', '基金', '合伙', '企业', '银行', '保险', '信托', '资管']
        return not any(indicator in name for indicator in indicators)
    
    def _calculate_entity_ownership(self, entity_name: str, entity_percentage: float, 
                                  result: Dict[str, float], visited: set = None):
        """递归计算非自然人股东的穿透持股"""
        if visited is None:
            visited = set()
        
        # 防止循环引用
        if entity_name in visited:
            return
        visited.add(entity_name)
        
        # 如果该非自然人没有定义股权结构，则无法穿透
        if entity_name not in self.entity_structure:
            return
        
        # 遍历该非自然人的所有股东
        for sub_shareholder, sub_percentage in self.entity_structure[entity_name].items():
            effective_percentage = entity_percentage * sub_percentage / 100.0
            
            if self._is_natural_person(sub_shareholder):
                # 找到自然人，累加股份
                result[sub_shareholder] = result.get(sub_shareholder, 0) + effective_percentage
            else:
                # 继续穿透计算
                self._calculate_entity_ownership(sub_shareholder, effective_percentage, result, visited)
    
    def get_major_shareholders(self, threshold: float = 30.0) -> List[Tuple[str, float]]:
        """获取持股超过阈值的实际受益人，按持股比例降序排列"""
        ultimate_ownership = self.calculate_ultimate_ownership()
        
        # 过滤并排序
        major_shareholders = [
            (name, percentage) for name, percentage in ultimate_ownership.items() 
            if percentage >= threshold
        ]
        major_shareholders.sort(key=lambda x: x[1], reverse=True)
        
        return major_shareholders
    
    def print_detailed_analysis(self):
        """打印详细分析结果"""
        print("=== 股权结构分析 ===")
        print("\n直接股东结构:")
        for shareholder, percentage in self.direct_shareholders.items():
            person_type = "自然人" if self._is_natural_person(shareholder) else "非自然人"
            print(f"  {shareholder}: {percentage}% ({person_type})")
        
        print("\n非自然人股东股权结构:")
        for entity, shareholders in self.entity_structure.items():
            print(f"  {entity}:")
            for sub_shareholder, percentage in shareholders.items():
                person_type = "自然人" if self._is_natural_person(sub_shareholder) else "非自然人"
                print(f"    {sub_shareholder}: {percentage}% ({person_type})")
        
        print("\n实际受益人计算:")
        ultimate_ownership = self.calculate_ultimate_ownership()
        for person, percentage in sorted(ultimate_ownership.items(), key=lambda x: x[1], reverse=True):
            print(f"  {person}: {percentage:.2f}%")
        
        print(f"\n持股超过30%的主要股东:")
        major_shareholders = self.get_major_shareholders(30.0)
        if major_shareholders:
            for person, percentage in major_shareholders:
                print(f"  {person}: {percentage:.2f}%")
        else:
            print("  无")

def _company_json_path(company_name: str) -> str:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    return os.path.join(desktop, company_name, f"{company_name}.json")


def _safe_float(value: Union[str, float, int]) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_company_record(company_name: str, keyword: str = ITEM_KEYWORD):
    json_path = _company_json_path(company_name)
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"找不到输入数据文件：{json_path}")
    
    with open(json_path, "r", encoding="utf-8") as f:
        content = json.load(f)
    
    if isinstance(content, dict):
        records = [content]
    elif isinstance(content, list):
        records = content
    else:
        raise ValueError("JSON 格式不支持。")
    
    def _find_record(target_keyword):
        for record in records:
            if record.get("item") == target_keyword and record.get("name") == company_name:
                return record
        return None
    
    record = _find_record(keyword)
    if record is None:
        record = _find_record(FALLBACK_ITEM_KEYWORD)
    
    if record is None:
        raise ValueError(f"未在 JSON 中找到 item={keyword} 的记录。")
    
    return record, json_path


def _build_calculator_from_record(record: Dict[str, Dict]) -> Tuple[ShareholderCalculator, Dict]:
    data = record.get("data") or {}
    calc_input = data.get("calculator_input") or {}
    direct_shareholders = calc_input.get("direct_shareholders") or {}
    entity_structure = calc_input.get("entity_structure") or {}
    
    calculator = ShareholderCalculator()
    
    for name, percentage in direct_shareholders.items():
        value = _safe_float(percentage)
        if value is not None:
            calculator.add_direct_shareholder(name, value)
    
    for entity_name, shareholders in entity_structure.items():
        if not isinstance(shareholders, dict):
            continue
        normalized = {}
        for sub_name, percentage in shareholders.items():
            value = _safe_float(percentage)
            if value is not None:
                normalized[sub_name] = value
        if normalized:
            calculator.set_entity_structure(entity_name, normalized)
    
    if not calculator.direct_shareholders:
        raise ValueError("记录中没有可用的股东数据。")
    
    return calculator, data


def analyze_company(company_name: str):
    record, json_path = _load_company_record(company_name)
    calculator, data = _build_calculator_from_record(record)
    
    print("=" * 60)
    print(f"{company_name} 股份计算")
    print("=" * 60)
    print(f"数据文件: {json_path}")
    print(f"记录时间: {record.get('queried_at', '未知')}")
    print(f"结果页面: {record.get('ret_url', '未知')}")
    
    shareholders = data.get("shareholders") or []
    if shareholders:
        print("\n原始股东列表（来自 JSON ）:")
        for entry in shareholders:
            name = entry.get("name")
            percentage = entry.get("percentage")
            label = entry.get("type", "")
            if name is None or percentage is None:
                continue
            label_text = f" ({label})" if label else ""
            print(f"  - {name}: {percentage:.2f}%{label_text}")
    
    print("\n股权穿透分析:")
    calculator.print_detailed_analysis()
    
    print("\n主要受益人（>=30%）:")
    major = calculator.get_major_shareholders()
    if major:
        for person, percentage in major:
            print(f"  * {person}: {percentage:.2f}%")
    else:
        print("  无")


def main():
    if len(sys.argv) > 1:
        company_name = sys.argv[1]
    else:
        company_name = input("请输入需要分析的公司名称: ").strip()
    
    if not company_name:
        print("未提供公司名称，程序退出。")
        sys.exit(1)
    
    try:
        analyze_company(company_name)
    except Exception as exc:
        print(f"计算失败: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    main()
