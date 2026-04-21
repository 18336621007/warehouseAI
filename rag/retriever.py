from configs.settings import Config

def retrieve_relevant_tables(query, vector_db):
    retriever = vector_db.as_retriever(search_kwargs={"k": Config.TOP_K_TABLES})
    retrieved = retriever.invoke(query)
    return "\n".join([doc.page_content for doc in retrieved])