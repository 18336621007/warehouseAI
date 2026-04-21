from langchain_openai import ChatOpenAI
from configs.settings import Config

def get_llm():
    return ChatOpenAI(
        model=Config.LLM_MODEL,
        api_key=Config.LLM_API_KEY,
        base_url=Config.LLM_BASE_URL,
        temperature=0
    )