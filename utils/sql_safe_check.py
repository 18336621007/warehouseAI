import re

def is_safe_sql(sql: str) -> bool:
    sql = sql.strip().lower()
    forbidden = ["drop", "delete", "truncate", "update", "insert", "alter", "create"]
    return not any(re.match(rf"^\s*{w}\s", sql) for w in forbidden)