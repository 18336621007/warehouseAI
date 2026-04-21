import pandas as pd
from data_service.db_connection import engine

def fetch_metadata(database: str):
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