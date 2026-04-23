"""配置模块：统一加载环境变量并提供全局配置项。"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """项目运行时配置容器。"""
    # 数据库URI
    DB_URI = os.getenv("DB_URI", "mysql+pymysql://root:123456@localhost:3306/ecommerce_data_warehouse")
    # 数据库名称
    DB_NAME = os.getenv("DB_NAME", "ecommerce_data_warehouse")
    # LLM API密钥
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    # LLM 基础URL
    LLM_BASE_URL = os.getenv("LLM_BASE_URL")
    # LLM 模型
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3-max")

    # 向量数据库路径
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./faiss_index")
    # 嵌入接口单次最大批量（DashScope text-embedding-v3 上限为10）
    EMBED_MAX_BATCH_SIZE = int(os.getenv("EMBED_MAX_BATCH_SIZE", "10"))
    # 指标词典路径
    METRIC_DICT_PATH = os.getenv("METRIC_DICT_PATH", "./configs/metric_dictionary.yaml")
    # 是否启用“语义层计划器 + SQL渲染器”新链路
    USE_QUERY_PLANNER = os.getenv("USE_QUERY_PLANNER", "true").lower() == "true"
    # 允许走新链路的核心指标（逗号分隔）
    QUERY_PLANNER_METRICS = [
        item.strip()
        for item in os.getenv("QUERY_PLANNER_METRICS", "valid_order_count,gmv,avg_order_value").split(",")
        if item.strip()
    ]
    # 结构化日志路径
    QUERY_PLAN_LOG_PATH = os.getenv("QUERY_PLAN_LOG_PATH", "./query_plan_runs.log")
    # 异常阈值
    ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.3"))
    # 表结构召回数量
    TOP_K_TABLES = int(os.getenv("TOP_K_TABLES", "5"))
    # 规则召回数量
    TOP_K_RULES = int(os.getenv("TOP_K_RULES", "3"))
    # 最大历史对话轮数
    MAX_HISTORY_ROUNDS = int(os.getenv("MAX_HISTORY_ROUNDS", "6"))