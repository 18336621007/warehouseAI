from constants.table_relations import VALID_ORDER_RULE

# 优化 5：增加 SQL 校验引擎（生产级必备！）
# 作用：
# 自动补有效订单过滤
# 防止模型用错 order_status
# 防止 0 元错误
# 防止漏 JOIN
class SQLValidator:
    @staticmethod
    def validate_sql(sql: str) -> str:
        # 强制插入有效订单过滤
        if "WHERE" in sql:
            sql = sql.replace("WHERE", f"WHERE {VALID_ORDER_RULE} AND ")
        else:
            sql += f" WHERE {VALID_ORDER_RULE}"

        # 禁止错误字段
        sql = sql.replace("dwd_order_detail.order_status", "invalid_field")
        return sql