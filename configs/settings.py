import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_URI = "mysql+pymysql://root:123456@localhost:3306/dw_retail"
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL")
    LLM_MODEL = "qwen-turbo"

    VECTOR_DB_PATH = "./faiss_index"
    ANOMALY_THRESHOLD = 0.3
    TOP_K_TABLES = 5 #RAG检索时，最多返回3张相关结果