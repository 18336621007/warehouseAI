"""指标词典模块：加载词典、匹配问题指标并生成提示词片段。"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@lru_cache(maxsize=1) #给函数加缓存，最近最少使用策略，缓存maxsize个结果
def load_metric_dictionary(path: str) -> Dict[str, Any]:
    """从 YAML 文件加载指标词典；缺失时返回空词典。"""
    file_path = Path(path)
    if not file_path.exists():
        return {"metrics": []}
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "metrics" not in data:
        data["metrics"] = []
    # 兼容语义层扩展schema
    if "measures" not in data:
        data["measures"] = []
    if "dimensions" not in data:
        data["dimensions"] = []
    if "join_paths" not in data:
        data["join_paths"] = {}
    if "default_filters" not in data:
        data["default_filters"] = {}
    return data


def match_metric(query: str, metric_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """根据问题文本匹配指标别名并返回命中的指标定义。"""
    lowered_query = (query or "").lower()
    for metric in metric_dict.get("metrics", []): #遍历指标词典中的所有指标
        aliases = metric.get("aliases", []) #取指标的别名列表
        for alias in aliases: #遍历指标的别名列表
            if alias and alias.lower() in lowered_query:
                return metric #如果别名在问题中出现，则返回指标定义
    return None #如果没命中，则返回None


def get_metric_by_id(metric_dict: Dict[str, Any], metric_id: str) -> Optional[Dict[str, Any]]:
    """按ID获取指标定义。"""
    for metric in metric_dict.get("metrics", []):
        if metric.get("id") == metric_id:
            return metric
    return None


def list_dimension_defs(metric_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """返回维度定义列表。"""
    return metric_dict.get("dimensions", [])


def get_measure_map(metric_dict: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """将原子指标列表转为 id->definition 映射。"""
    return {item.get("id"): item for item in metric_dict.get("measures", []) if item.get("id")}


def get_filter_expression(metric_dict: Dict[str, Any], filter_key: str) -> Optional[str]:
    """按过滤键获取默认过滤表达式。"""
    return metric_dict.get("default_filters", {}).get(filter_key)


def build_metric_prompt_block(metric: Optional[Dict[str, Any]]) -> str:
    """将命中的指标规则转换为可注入提示词的文本块。"""
    if not metric:
        return "（未命中指标词典）"
    must_include = metric.get("must_include", [])
    forbidden = metric.get("forbidden", [])
    return (
        f"命中指标：{metric.get('zh_name', metric.get('id', 'unknown'))}\n"
        f"SQL必须包含：{must_include}\n"
        f"SQL禁止包含：{forbidden}"
    )
