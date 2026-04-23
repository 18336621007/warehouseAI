"""文档构建模块：将表元数据与业务规则转换为向量检索文档。"""

from langchain.schema import Document
# 将数据库的元数据（表结构）和业务指标口径转换成 LangChain 的 Document 对象列表，
# 以便后续用于检索增强生成（RAG）或大模型上下文提示。
def build_docs_from_metadata(df_meta):
    """把每张表的结构信息整理成可检索 Document 列表。"""
    docs = []

    for table_name, group in df_meta.groupby("TABLE_NAME"):
        table_comment = group["TABLE_COMMENT"].iloc[0]

        field_list = []
        for _, row in group.iterrows():
            pk_mark = "【主键】" if row["is_primary"] == "是" else ""
            field_list.append(
                f"{row['COLUMN_NAME']}({row['DATA_TYPE']}){pk_mark}：{row['COLUMN_COMMENT']}"
            )

        fields_str = "，".join(field_list)
        doc_str = f"表名：{table_name}，表注释：{table_comment}，字段：{fields_str}"
        docs.append(
            Document(
                page_content=doc_str,
                metadata={"source": "table_schema", "table_name": table_name},
            )
        )

    return docs


def build_rule_docs(table_relations, valid_order_rule, metric_standard):
    """把规则常量整理成可检索 Document 列表。"""
    return [
        Document(
            page_content=f"表关联关系：{table_relations}",
            metadata={"source": "rule", "rule_type": "relation"},
        ),
        Document(
            page_content=f"有效订单规则：{valid_order_rule}",
            metadata={"source": "rule", "rule_type": "valid_order"},
        ),
        Document(
            page_content=f"指标计算口径：{metric_standard}",
            metadata={"source": "rule", "rule_type": "metric"},
        ),
    ]