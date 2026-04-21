from data_service.meta_fetcher import fetch_metadata
from rag.doc_builder import build_docs_from_metadata
from rag.vector_store import get_vector_db
from rag.retriever import retrieve_relevant_tables
from agent.sql_agent import create_sql_agent_instance
from data_service.sql_executor import detect_gmv_anomaly
import sys
import time
from threading import Thread
from constants.table_relations import TABLE_RELATIONS, VALID_ORDER_RULE
from constants.metrics import METRIC_STANDARD
from constants.biz_rules import BIZ_RULES
from langchain.schema import SystemMessage

# 加载动画
def loading_animation(stop_event):
    symbols = ["|", "/", "-", "\\"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r🤖 AI正在思考并查询数据 {symbols[i]} ")
        sys.stdout.flush()
        time.sleep(0.2)
        i = (i + 1) % 4
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()

def chat(query: str, vector_db, agent):
    table_info = retrieve_relevant_tables(query, vector_db)

    prompt = f"""
    你是企业级电商数据仓库专属智能分析师，全程使用中文进行简洁回答。
    
    【表关联关系】
    {TABLE_RELATIONS}

    【有效订单规则】
    {VALID_ORDER_RULE}

    【指标计算口径】
    {METRIC_STANDARD}

    【业务约束】
    {BIZ_RULES}

    ====================
    【检索到的表结构】
    {table_info}

    【用户问题】
    {query}

    """
    response = agent.invoke({
        "input": prompt
    })
    return response.get("output", response)

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 智能数据问答系统已启动")
    print("💡 输入 exit 退出")
    print("=" * 60)

    # 初始化
    df_meta = fetch_metadata("dw_retail")
    docs = build_docs_from_metadata(df_meta)
    vec_db = get_vector_db(docs)
    agent = create_sql_agent_instance()


    while True:
        user_query = input("请输入你的问题：")
        if user_query.lower() in ["exit", "quit", "q"]:
            print("👋 退出程序")
            break
        # 新增：清空对话记忆指令
        if user_query.lower() == "clear":
            agent.memory.clear()
            print("🔄 已清空对话历史")
            continue

        if not user_query.strip():
            continue

        # 加载动画
        stop_event = Thread(target=lambda: None)
        stop_event = type('obj', (object,), {'is_set': lambda: False, 'set': lambda: None})()
        from threading import Event
        stop_event = Event()
        t = Thread(target=loading_animation, args=(stop_event,))
        t.daemon = True
        t.start()

        try:
            result = chat(user_query, vec_db, agent)
        finally:
            stop_event.set()
            time.sleep(0.1)

        print("\n" + "="*60)
        print(f"✅ 回答：{result}")
        print("="*60 + "\n")