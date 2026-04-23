"""CLI 入口模块：组织 RAG 检索、指标词典约束与 SQL Agent 问答流程。"""

from data_service.meta_fetcher import fetch_metadata
from rag.doc_builder import build_docs_from_metadata, build_rule_docs
from rag.vector_store import get_vector_db
from rag.retriever import retrieve_relevant_tables, retrieve_relevant_rules
from agent.sql_agent import create_sql_agent_instance
from configs.settings import Config
from core.metric_dictionary import (
    build_metric_prompt_block,
    load_metric_dictionary,
    match_metric,
)
from core.sql_validator import SQLValidator
from core.query_planner import build_query_plan
from core.sql_renderer import render_sql_from_plan
from data_service.db_connection import sql_db
import json
import sys
import time
from threading import Event, Thread
from collections import deque
from datetime import datetime
from constants.table_relations import TABLE_RELATIONS, VALID_ORDER_RULE
from constants.metrics import METRIC_STANDARD
from constants.biz_rules import BIZ_RULES

METRIC_DICT = {"metrics": []}


def _log_query_plan_event(payload):
    """记录结构化 query plan 执行日志，便于回归与排障。"""
    try:
        with open(Config.QUERY_PLAN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"timestamp": datetime.utcnow().isoformat(), **payload},
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass


def loading_animation(stop_event):
    """在主线程等待回答时显示终端加载动画。"""
    symbols = ["|", "/", "-", "\\"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r🤖 AI正在思考并查询数据 {symbols[i]} ")
        sys.stdout.flush()
        time.sleep(0.2)
        i = (i + 1) % 4
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()


def _build_history_context(history_pairs):
    """将历史问答拼接为多轮上下文字符串。"""
    if not history_pairs:
        return "（无历史对话）"
    lines = []
    for idx, (q, a) in enumerate(history_pairs, start=1):
        lines.append(f"第{idx}轮用户：{q}")
        lines.append(f"第{idx}轮助手：{a}")
    return "\n".join(lines)


def chat(query: str, vector_db, agent, history_pairs):
    """执行单轮问答：检索上下文、构造提示词并调用 Agent。"""
    table_info = retrieve_relevant_tables(query, vector_db)
    rule_info = retrieve_relevant_rules(query, vector_db)
    history_context = _build_history_context(history_pairs)
    metric_rule = match_metric(query, METRIC_DICT)
    metric_rule_prompt = build_metric_prompt_block(metric_rule)


    ###########################################
    # Prompt
    # 1.系统角色层（常驻）
    # 2.会话上下文层（动态），注入历史对话
    # 3.业务硬约束层（常驻），红线规则
    # 4.RAG规则召回层（动态），把规则文档里与问题最相关的部分按需注入，而不是全量塞入
    # 5.RAG表结构召回层（动态）当前问题相关的表
    # 6.指标词典命中层（动态），命中某个指标后把 must/forbidden 规则注入 prompt。这层是“业务定义结构化提示”，针对你最容易错的指标口径问题。
    ###########################################

    prompt = f"""
    你是企业级电商数仓分析师。全程中文，回答简洁。
    只基于给定上下文与SQL查询结果作答，不编造表、字段或数值。
    必须执行SQL并返回最终结论；若无数据，明确回答“无数据”。
    涉及指标口径时优先遵循“指标词典命中规则”和“检索规则”。
    输出格式：先结论，再给依据（使用的表/字段/口径）。
    ====================
    【多轮对话上下文】
    {history_context}
    ====================
    必须做到：
    {BIZ_RULES}
    ====================
    【检索到的业务规则与口径】
    {rule_info}
    ====================
    【指标词典命中规则】
    {metric_rule_prompt}
    ====================
    【检索到的表结构】
    {table_info}

    【用户问题】
    {query}

    """
    SQLValidator.set_active_metric_rule(metric_rule)
    try:
        if Config.USE_QUERY_PLANNER:
            query_plan = build_query_plan(query, METRIC_DICT)
            if query_plan and query_plan.get("metric_id") in Config.QUERY_PLANNER_METRICS:
                try:
                    rendered_sql = render_sql_from_plan(query_plan, METRIC_DICT)
                    validated_sql = SQLValidator.validate_sql(rendered_sql)
                    sql_result = sql_db.run(validated_sql)
                    _log_query_plan_event(
                        {
                            "route": "planner",
                            "query": query,
                            "query_plan": query_plan,
                            "rendered_sql": rendered_sql,
                            "validated_sql": validated_sql,
                            "result_preview": str(sql_result)[:500],
                        }
                    )
                    planner_answer_prompt = f"""
                    你是企业级电商数仓分析师，请基于执行结果给出简洁结论。
                    【用户问题】{query}
                    【查询计划】{query_plan}
                    【执行SQL】{validated_sql}
                    【SQL结果】{sql_result}
                    回答要求：先结论，再给依据；若无数据，请明确回答“无数据”。
                    """
                    response = agent.invoke({"input": planner_answer_prompt})
                    return response.get("output", response)
                except Exception as planner_exc:
                    _log_query_plan_event(
                        {
                            "route": "planner_fallback",
                            "query": query,
                            "query_plan": query_plan,
                            "error": str(planner_exc),
                        }
                    )

        response = agent.invoke({
            "input": prompt
        })
        _log_query_plan_event(
            {
                "route": "legacy_agent",
                "query": query,
                "metric_hit": metric_rule.get("id") if metric_rule else None,
            }
        )
        return response.get("output", response)
    finally:
        SQLValidator.set_active_metric_rule(None)

if __name__ == "__main__":
    # 启动提示：告知可用命令与交互方式。
    print("=" * 60)
    print("🔥 智能数据问答系统已启动")
    print("💡 输入 exit 退出，输入 clear 清空历史，输入 history 查看历史")
    print("=" * 60)

    # 启动阶段：读取数据库元数据并构建向量检索知识库。
    df_meta = fetch_metadata(Config.DB_NAME)
    docs = build_docs_from_metadata(df_meta)
    # 将关系规则与指标口径写入向量库，支持按问题动态召回规则上下文。
    docs.extend(
        build_rule_docs(
            TABLE_RELATIONS, VALID_ORDER_RULE, METRIC_STANDARD
        )
    )
    # 载入结构化指标词典，用于指标匹配与 SQL 约束校验。
    METRIC_DICT = load_metric_dictionary(Config.METRIC_DICT_PATH)
    vec_db = get_vector_db(docs)
    # 初始化 SQL Agent 与会话历史窗口。
    agent = create_sql_agent_instance()
    history_pairs = deque(maxlen=Config.MAX_HISTORY_ROUNDS) #双端队列

    # 交互主循环：持续接收用户问题并返回分析结果。
    while True:
        user_query = input("请输入你的问题：")
        # 退出命令。
        if user_query.lower() in ["exit", "quit", "q"]:
            print("👋 退出程序")
            break
        # 清理模型记忆与本地历史。
        if user_query.lower() == "clear":
            agent.memory.clear()
            history_pairs.clear()
            print("🔄 已清空对话历史")
            continue
        # 打印最近会话，便于排查多轮上下文问题。
        if user_query.lower() == "history":
            if not history_pairs:
                print("📝 当前暂无历史对话")
            else:
                print("\n" + "=" * 60)
                print("📝 最近对话：")
                for idx, (q, a) in enumerate(history_pairs, start=1):
                    print(f"{idx}. Q: {q}")
                    print(f"   A: {a}")
                print("=" * 60 + "\n")
            continue

        if not user_query.strip():
            continue

        # 启动等待动画，提升命令行交互体验。
        stop_event = Event()
        t = Thread(target=loading_animation, args=(stop_event,))
        t.daemon = True
        t.start()

        try:
            # 执行检索增强问答与 SQL Agent 推理。
            result = chat(user_query, vec_db, agent, history_pairs)
        finally:
            # 无论成功或失败都停止动画，避免终端残留。
            stop_event.set()
            time.sleep(0.1)

        # 写入本轮历史并输出最终回答。
        history_pairs.append((user_query, str(result)))
        print("\n" + "=" * 60)
        print(f"✅ 回答：{result}")
        print("=" * 60 + "\n")