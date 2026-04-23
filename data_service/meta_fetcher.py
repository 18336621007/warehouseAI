"""元数据采集模块：从 INFORMATION_SCHEMA 读取表和字段描述信息。"""

import pandas as pd
from data_service.db_connection import engine


def fetch_metadata(database: str):
    """按数据库名拉取表/字段注释与主键信息，供 RAG 建库使用。"""
    if not database.replace("_", "").isalnum():
        raise ValueError("database 名称非法。")

    sql = f"""
    SELECT
        t.TABLE_NAME,
        t.TABLE_COMMENT,
        c.COLUMN_NAME,
        c.COLUMN_COMMENT,
        c.DATA_TYPE,
        IF(c.COLUMN_KEY='PRI', '是', '否') AS is_primary
    FROM INFORMATION_SCHEMA.TABLES t
    JOIN INFORMATION_SCHEMA.COLUMNS c
        ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
        AND t.TABLE_NAME = c.TABLE_NAME
    WHERE t.TABLE_SCHEMA = '{database}'
    ORDER BY t.TABLE_NAME, c.ORDINAL_POSITION
    """
    return pd.read_sql(sql, engine) #sql内容和数据库链接