"""SQL Agent 组装模块：创建 Agent，并在执行 SQL 前注入安全校验。"""

from langchain.memory import ConversationBufferWindowMemory
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from data_service.db_connection import sql_db
from agent.llm_factory import get_llm
from configs.settings import Config
import json
import time

from core.sql_validator import SQLValidator

original_run = sql_db.run


def _debug_log(hypothesis_id, location, message, data):
    """调试模式日志：将运行时证据写入本地 NDJSON 文件。"""
    # #region agent log
    try:
        payload = {
            "sessionId": "192593",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open("debug-192593.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion


def safe_run(*args, **kwargs):
    """兼容所有调用方式：生产级安全包装"""
    # 取出 SQL
    sql = args[0] if args else kwargs.get("query", "")
    _debug_log("H2", "agent/sql_agent.py:safe_run:entry", "raw sql received", {"sql": str(sql)[:500]})

    # 安全校验
    safe_sql = SQLValidator.validate_sql(sql)
    _debug_log("H3", "agent/sql_agent.py:safe_run:validated", "sql after validator", {"safe_sql": str(safe_sql)[:500]})

    # 替换参数
    if args:
        new_args = (safe_sql,) + args[1:]
        result = original_run(*new_args, **kwargs)
        _debug_log("H4", "agent/sql_agent.py:safe_run:result", "sql execution result", {"result_preview": str(result)[:500]})
        return result
    else:
        kwargs["query"] = safe_sql
        result = original_run(**kwargs)
        _debug_log("H4", "agent/sql_agent.py:safe_run:result", "sql execution result", {"result_preview": str(result)[:500]})
        return result


# 全局替换
sql_db.run = safe_run


def create_sql_agent_instance():
    """创建带会话记忆的 SQL Agent 实例。"""
    llm = get_llm()
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        return_messages=True,
        k=Config.MAX_HISTORY_ROUNDS,
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