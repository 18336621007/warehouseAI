from langchain.schema import Document
# 将数据库的元数据（表结构）和业务指标口径转换成 LangChain 的 Document 对象列表，
# 以便后续用于检索增强生成（RAG）或大模型上下文提示。
def build_docs_from_metadata(df_meta):
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
        docs.append(Document(page_content=doc_str))

    return docs