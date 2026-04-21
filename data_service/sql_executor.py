import pandas as pd
from data_service.db_connection import engine
from configs.settings import Config

def detect_gmv_anomaly():
    sql = """
    SELECT
        DATE(pay_time) AS dt,
        SUM(pay_amount) AS gmv,
        COUNT(DISTINCT order_id) AS order_cnt
    FROM dwd_order_detail
    GROUP BY dt
    ORDER BY dt DESC
    LIMIT 2
    """
    df = pd.read_sql(sql, engine)

    if len(df) < 2:
        return "数据不足，无法检测"

    today = df.iloc[0]
    yesterday = df.iloc[1]

    rate = (today["gmv"] - yesterday["gmv"]) / (yesterday["gmv"] + 1e-6)
    is_abnormal = abs(rate) > Config.ANOMALY_THRESHOLD

    res = f"GMV={today['gmv']:.2f}，环比变化：{rate:.1%}"
    return res + (" ⚠️ 异常" if is_abnormal else " ✅ 正常")