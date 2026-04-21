from langchain.memory import ConversationBufferMemory
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from data_service.db_connection import sql_db
from agent.llm_factory import get_llm

# 生产级 SQL 校验
from core.sql_validator import SQLValidator

original_run = sql_db.run


def safe_run(*args, **kwargs):
    """兼容所有调用方式：生产级安全包装"""
    # 取出 SQL
    sql = args[0] if args else kwargs.get("query", "")

    # 安全校验
    safe_sql = SQLValidator.validate_sql(sql)

    # 替换参数
    if args:
        new_args = (safe_sql,) + args[1:]
        return original_run(*new_args, **kwargs)
    else:
        kwargs["query"] = safe_sql
        return original_run(**kwargs)


# 全局替换
sql_db.run = safe_run


def create_sql_agent_instance():
    llm = get_llm()
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
    )

    agent = create_sql_agent(
        llm=llm,
        db=sql_db,
        memory=memory,

        agent_type="openai-tools",
        verbose=False,
        top_k=10,
        timeout=10,
        max_retries=1,
        handle_parsing_errors=True
    )
    return agent