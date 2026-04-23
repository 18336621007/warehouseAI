"""LLM 工厂模块：集中创建并返回项目统一配置的聊天模型。"""

from langchain_openai import ChatOpenAI
from configs.settings import Config

def get_llm():
    """按配置构造 ChatOpenAI 客户端实例。"""
    return ChatOpenAI(
        model=Config.LLM_MODEL,
        api_key=Config.LLM_API_KEY,
        base_url=Config.LLM_BASE_URL,
        temperature=0
    )