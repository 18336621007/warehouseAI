"""查询计划器：将自然语言问题转换为结构化 query_plan。"""

import re
from typing import Any, Dict, List, Optional

from core.metric_dictionary import list_dimension_defs, match_metric


def _detect_time_grain(query: str) -> Optional[str]:
    lowered = query.lower()
    if any(token in lowered for token in ["按天", "每日", "日均", "按日", "每天"]):
        return "day"
    if any(token in lowered for token in ["按月", "每月", "月度"]):
        return "month"
    return None


def _detect_limit_and_order(query: str) -> Dict[str, Any]:
    lowered = query.lower()
    # 默认针对排行榜问题使用降序
    order = "desc" if any(token in lowered for token in ["最高", "最多", "top", "前"]) else None
    limit = None
    match = re.search(r"前\s*(\d+)", lowered)
    if match:
        limit = int(match.group(1))
    elif "top" in lowered:
        top_match = re.search(r"top\s*(\d+)", lowered)
        if top_match:
            limit = int(top_match.group(1))
    return {"order": order, "limit": limit}


def _extract_dimensions(query: str, metric_dict: Dict[str, Any]) -> List[str]:
    lowered = query.lower()
    matched = []
    for dim in list_dimension_defs(metric_dict):
        dim_id = dim.get("id")
        if not dim_id:
            continue
        aliases = dim.get("aliases", [])
        if any(alias and alias.lower() in lowered for alias in aliases):
            matched.append(dim_id)
    return matched


def _extract_basic_filters(query: str) -> List[Dict[str, Any]]:
    """MVP 过滤器抽取：支持 user_id/sku_id 的简单匹配。"""
    filters = []
    user_match = re.search(r"(?:用户|user)[^\d]*(\d+)", query, flags=re.IGNORECASE)
    if user_match:
        filters.append({"field": "dwd_order_info.user_id", "op": "=", "value": int(user_match.group(1))})
    sku_match = re.search(r"(?:sku)[^\d]*(\d+)", query, flags=re.IGNORECASE)
    if sku_match:
        filters.append({"field": "ods_sku.sku_id", "op": "=", "value": int(sku_match.group(1))})
    return filters


def build_query_plan(query: str, metric_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """构建结构化查询计划。未命中指标时返回 None。"""
    metric = match_metric(query, metric_dict)
    if not metric:
        return None

    order_limit = _detect_limit_and_order(query)
    return {
        "metric_id": metric.get("id"),
        "metric_name": metric.get("zh_name", metric.get("id")),
        "dimensions": _extract_dimensions(query, metric_dict),
        "filters": _extract_basic_filters(query),
        "time_grain": _detect_time_grain(query),
        "order": order_limit["order"],
        "limit": order_limit["limit"],
    }
