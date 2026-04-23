"""SQL 校验模块：限制危险语句并校验指标词典约束。"""

import re
from typing import Dict, Set

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError
from constants.table_relations import VALID_ORDER_RULE


class SQLValidator:
    """集中管理 SQL 语法安全与业务口径规则校验。"""
    FORBIDDEN_PREFIX = (
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "replace",
    )
    ACTIVE_METRIC_RULE = None
    ORDER_STATUS_DEFAULT = "1"

    @staticmethod
    def set_active_metric_rule(metric_rule):
        """设置当前问题命中的指标规则，供 SQL 校验时使用。"""
        SQLValidator.ACTIVE_METRIC_RULE = metric_rule

    @staticmethod
    def _parse_sql(raw_sql: str):
        """将 SQL 解析为 AST，便于结构化校验与改写。"""
        try:
            return parse_one(raw_sql, read="mysql")
        except ParseError as exc:
            raise ValueError(f"[SQL_PARSE_ERROR] SQL 解析失败: {exc}") from exc

    @staticmethod
    def _validate_readonly_sql(sql_ast):
        """仅允许只读查询，支持 SELECT 与 WITH...SELECT。"""
        if isinstance(sql_ast, exp.Select):
            return
        if isinstance(sql_ast, exp.With):
            return
        if isinstance(sql_ast, exp.Subqueryable):
            return
        if isinstance(sql_ast, exp.Expression) and sql_ast.find(exp.Select):
            # 兜底：允许可解析到 SELECT 的只读结构，写操作仍由下方 AST 类型拦截。
            pass

        forbidden_types = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create)
        if isinstance(sql_ast, forbidden_types):
            raise ValueError("[READONLY_ENFORCED] 仅允许 SELECT 查询。")
        if not sql_ast.find(exp.Select):
            raise ValueError("[READONLY_ENFORCED] 仅允许 SELECT 查询。")

    @staticmethod
    def _collect_table_aliases(sql_ast) -> Dict[str, Set[str]]:
        """收集 SQL 中涉及的表与别名。"""
        table_aliases = {}
        for table in sql_ast.find_all(exp.Table):
            table_name = (table.name or "").lower()
            if not table_name:
                continue
            aliases = table_aliases.setdefault(table_name, set())
            aliases.add(table_name)
            alias_name = (table.alias_or_name or "").lower()
            if alias_name:
                aliases.add(alias_name)
        return table_aliases

    @staticmethod
    def _has_valid_order_equivalent_condition(normalized_sql: str, table_aliases: Dict[str, Set[str]]) -> bool:
        """检测 SQL 是否已包含有效订单等价条件（支持别名与 IN(1)）。"""
        candidates = {"order_status"}
        for table_name, aliases in table_aliases.items():
            if "order" in table_name:
                for alias in aliases:
                    candidates.add(f"{alias}.order_status")

        for field in candidates:
            if re.search(rf"\b{re.escape(field)}\s*=\s*\d+\b", normalized_sql):
                return True
            if re.search(rf"\b{re.escape(field)}\s+in\s*\(\s*\d+(?:\s*,\s*\d+)*\s*\)", normalized_sql):
                return True
        return False

    @staticmethod
    def _needs_valid_order_guard(table_aliases: Dict[str, Set[str]], normalized_sql: str) -> bool:
        """判断是否需要补充有效订单过滤条件。"""
        touches_order_fact = any("order" in table_name for table_name in table_aliases)
        if not touches_order_fact:
            return False
        return not SQLValidator._has_valid_order_equivalent_condition(normalized_sql, table_aliases)

    @staticmethod
    def _extract_default_order_status_value() -> str:
        """从全局口径规则中提取默认订单状态值，提取失败则回退 1。"""
        match = re.search(r"order_status\s*=\s*(\d+)", VALID_ORDER_RULE.lower())
        if match:
            return match.group(1)
        return SQLValidator.ORDER_STATUS_DEFAULT

    @staticmethod
    def _resolve_guard_condition(table_aliases: Dict[str, Set[str]]) -> str:
        """根据 SQL 实际涉及的订单事实表选择可执行的过滤条件。"""
        def preferred_name(names: Set[str], table_name: str) -> str:
            alias_only = sorted([name for name in names if name != table_name])
            return alias_only[0] if alias_only else table_name

        status_value = SQLValidator._extract_default_order_status_value()
        preferred_order_tables = ["ods_order", "dwd_order_detail", "dwd_order_info", "ods_order_item"]
        for table_name in preferred_order_tables:
            if table_name in table_aliases:
                target = preferred_name(table_aliases[table_name], table_name)
                return f"{target}.order_status = {status_value}"
        for table_name, names in table_aliases.items():
            if "order" in table_name:
                target = preferred_name(names, table_name)
                return f"{target}.order_status = {status_value}"
        return VALID_ORDER_RULE

    @staticmethod
    def _apply_valid_order_guard(sql_ast, table_aliases: Dict[str, Set[str]]) -> str:
        """在主查询层注入有效订单过滤条件（AST 改写）。"""
        if sql_ast.args.get("with") is not None:
            raise ValueError(
                "[GUARD_INJECTION_UNSAFE] 检测到 WITH 查询，无法安全推断注入层级，请模型显式添加有效订单过滤条件。"
            )

        guard_condition = SQLValidator._resolve_guard_condition(table_aliases)
        try:
            guard_expr = parse_one(guard_condition, into=exp.Condition, read="mysql")
        except ParseError as exc:
            raise ValueError(f"[GUARD_PARSE_ERROR] 无法解析注入条件: {exc}") from exc

        target_select = sql_ast.find(exp.Select)
        if target_select is None:
            raise ValueError("[GUARD_INJECTION_UNSAFE] 无法定位主查询层，无法注入有效订单条件。")

        where_clause = target_select.args.get("where")
        if where_clause is None:
            target_select.set("where", exp.Where(this=guard_expr))
        else:
            target_select.set("where", exp.Where(this=exp.and_(where_clause.this, guard_expr)))
        return sql_ast.sql(dialect="mysql")

    @staticmethod
    def _normalize_expr(expr: str) -> str:
        normalized = (expr or "").strip().lower()
        # 去掉反引号与多余空白
        normalized = normalized.replace("`", "")
        normalized = re.sub(r"\s+", " ", normalized)
        # 消除表前缀/别名影响：tbl.col -> col
        normalized = re.sub(r"\b[a-zA-Z_][\w]*\.", "", normalized)
        # 统一函数调用空白：count ( -> count(
        normalized = re.sub(r"\b(count|sum|avg|min|max)\s+\(", r"\1(", normalized)
        # 统一 in 语法空白
        normalized = re.sub(r"\s+in\s+\(", " in (", normalized)
        return normalized

    @staticmethod
    def _validate_metric_rule(lowered_sql: str, metric_rule):
        """校验指标词典规则：当前仅强制 forbidden，避免 must_include 硬编码。"""
        if not metric_rule:
            return

        normalized_sql = SQLValidator._normalize_expr(lowered_sql)
        for forbidden_expr in metric_rule.get("forbidden", []):
            if forbidden_expr and SQLValidator._normalize_expr(forbidden_expr) in normalized_sql:
                raise ValueError(
                    f"[METRIC_FORBIDDEN_HIT] SQL 违反指标词典约束，包含禁用表达式: {forbidden_expr}"
                )

    @staticmethod
    def validate_sql(sql: str) -> str:
        """校验并修正 SQL：只读校验、有效订单口径注入、指标词典约束校验。"""
        if not sql or not isinstance(sql, str):
            raise ValueError("SQL 为空，无法执行。")

        raw_sql = sql.strip()
        lowered = raw_sql.lower()
        if any(lowered.startswith(prefix) for prefix in SQLValidator.FORBIDDEN_PREFIX):
            raise ValueError("检测到危险 SQL 语句，已拒绝执行。")

        sql_ast = SQLValidator._parse_sql(raw_sql)
        SQLValidator._validate_readonly_sql(sql_ast)

        table_aliases = SQLValidator._collect_table_aliases(sql_ast)
        normalized_sql = SQLValidator._normalize_expr(raw_sql)
        if SQLValidator._needs_valid_order_guard(table_aliases, normalized_sql):
            raw_sql = SQLValidator._apply_valid_order_guard(sql_ast, table_aliases)
            lowered = raw_sql.lower()
        else:
            lowered = raw_sql.lower()

        SQLValidator._validate_metric_rule(lowered, SQLValidator.ACTIVE_METRIC_RULE)
        return raw_sql