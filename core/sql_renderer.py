"""SQL 渲染器：根据 query_plan 和语义层词典生成 SQL。"""

from typing import Any, Dict, List

from core.metric_dictionary import (
    get_filter_expression,
    get_measure_map,
    get_metric_by_id,
    list_dimension_defs,
)


def _expand_metric_expression(metric_def: Dict[str, Any], measure_map: Dict[str, Dict[str, Any]]) -> str:
    """将指标表达式中的 measure 引用展开为 SQL 片段。"""
    expression = metric_def.get("expression", "")
    for measure_id in metric_def.get("measure_refs", []):
        measure_def = measure_map.get(measure_id, {})
        measure_expr = measure_def.get("expression", "")
        expression = expression.replace(f"{{{{{measure_id}}}}}", measure_expr)
    return expression


def _collect_dimension_defs(dimension_ids: List[str], metric_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    dim_map = {item.get("id"): item for item in list_dimension_defs(metric_dict) if item.get("id")}
    return [dim_map[dim_id] for dim_id in dimension_ids if dim_id in dim_map]


def _render_filters(plan: Dict[str, Any], metric_dict: Dict[str, Any], metric_def: Dict[str, Any]) -> List[str]:
    conditions = []
    measure_map = get_measure_map(metric_dict)
    for measure_id in metric_def.get("measure_refs", []):
        for filter_key in measure_map.get(measure_id, {}).get("default_filters", []):
            filter_expr = get_filter_expression(metric_dict, filter_key)
            if filter_expr:
                conditions.append(filter_expr)

    for item in plan.get("filters", []):
        value = item.get("value")
        if isinstance(value, str):
            conditions.append(f"{item['field']} {item['op']} '{value}'")
        else:
            conditions.append(f"{item['field']} {item['op']} {value}")
    return conditions


def render_sql_from_plan(plan: Dict[str, Any], metric_dict: Dict[str, Any]) -> str:
    """按结构化计划渲染 SQL。"""
    metric_id = plan.get("metric_id")
    metric_def = get_metric_by_id(metric_dict, metric_id)
    if not metric_def:
        raise ValueError(f"[PLAN_METRIC_NOT_FOUND] 未找到指标定义: {metric_id}")

    measure_map = get_measure_map(metric_dict)
    metric_expr = _expand_metric_expression(metric_def, measure_map)
    if not metric_expr:
        raise ValueError(f"[PLAN_METRIC_EXPR_EMPTY] 指标表达式为空: {metric_id}")

    base_table = metric_def.get("base_table")
    if not base_table:
        raise ValueError(f"[PLAN_BASE_TABLE_MISSING] 指标未定义 base_table: {metric_id}")

    dimension_defs = _collect_dimension_defs(plan.get("dimensions", []), metric_dict)
    select_parts = [f"{metric_expr} AS {metric_id}"]
    group_by_parts = []
    join_clauses = []
    join_paths = metric_dict.get("join_paths", {})
    added_join_path = set()

    for dim in dimension_defs:
        select_parts.append(f"{dim['column']} AS {dim['id']}")
        group_by_parts.append(dim["column"])
        join_key = dim.get("join_path")
        if join_key and join_key not in added_join_path:
            join_clauses.extend(join_paths.get(join_key, []))
            added_join_path.add(join_key)

    where_conditions = _render_filters(plan, metric_dict, metric_def)

    sql_parts = [f"SELECT {', '.join(select_parts)}", f"FROM {base_table}"]
    if join_clauses:
        sql_parts.extend(join_clauses)
    if where_conditions:
        sql_parts.append("WHERE " + " AND ".join(dict.fromkeys(where_conditions)))
    if group_by_parts:
        sql_parts.append("GROUP BY " + ", ".join(group_by_parts))

    order = plan.get("order")
    limit = plan.get("limit")
    if order:
        sql_parts.append(f"ORDER BY {metric_id} {order.upper()}")
    if limit:
        sql_parts.append(f"LIMIT {int(limit)}")
    return "\n".join(sql_parts)
