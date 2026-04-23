"""检索模块：从向量库中分离召回表结构与业务规则上下文。"""

from configs.settings import Config


def retrieve_relevant_tables(query, vector_db):
    """按问题召回并返回表结构文档文本。"""
    retriever = vector_db.as_retriever(search_kwargs={"k": Config.TOP_K_TABLES * 3})
    retrieved = retriever.invoke(query)
    table_docs = [doc for doc in retrieved if doc.metadata.get("source") == "table_schema"]
    if not table_docs:
        table_docs = retrieved[: Config.TOP_K_TABLES]
    return "\n".join([doc.page_content for doc in table_docs[: Config.TOP_K_TABLES]])


def retrieve_relevant_rules(query, vector_db):
    """按问题召回并返回业务规则文档文本。"""
    retriever = vector_db.as_retriever(search_kwargs={"k": Config.TOP_K_RULES * 3})
    retrieved = retriever.invoke(query)
    rule_docs = [doc for doc in retrieved if doc.metadata.get("source") == "rule"]
    if not rule_docs:
        rule_docs = retrieved[: Config.TOP_K_RULES]
    return "\n".join([doc.page_content for doc in rule_docs[: Config.TOP_K_RULES]])