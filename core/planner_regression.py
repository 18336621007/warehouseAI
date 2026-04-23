"""语义层链路回归脚本：校验 planner + renderer + validator 的关键场景。"""

from core.metric_dictionary import load_metric_dictionary
from core.query_planner import build_query_plan
from core.sql_renderer import render_sql_from_plan
from core.sql_validator import SQLValidator


CASES = [
    ("有效订单数是多少", "valid_order_count"),
    ("GMV是多少", "gmv"),
    ("客单价是多少", "avg_order_value"),
    ("按天查看GMV", "gmv"),
]


def run():
    metric_dict = load_metric_dictionary("./configs/metric_dictionary.yaml")
    for query, expected_metric in CASES:
        query_plan = build_query_plan(query, metric_dict)
        assert query_plan is not None, f"query_plan should not be None: {query}"
        assert query_plan["metric_id"] == expected_metric, (
            f"metric mismatch for query={query}, actual={query_plan['metric_id']}"
        )
        SQLValidator.set_active_metric_rule(
            next(item for item in metric_dict["metrics"] if item["id"] == query_plan["metric_id"])
        )
        try:
            rendered_sql = render_sql_from_plan(query_plan, metric_dict)
            validated_sql = SQLValidator.validate_sql(rendered_sql)
            print(f"[PASS] {query} -> {query_plan['metric_id']}\n{validated_sql}\n")
        finally:
            SQLValidator.set_active_metric_rule(None)


if __name__ == "__main__":
    run()
