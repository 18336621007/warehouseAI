"""向量库模块：创建嵌入模型并将文档构建为 FAISS 索引。"""

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings  # 阿里官方专用
import os
from dotenv import load_dotenv
from configs.settings import Config

load_dotenv()

# --------------------------
# ✅ 阿里云通义千问 官方嵌入模型（100% 不报错）
# --------------------------
def get_embedding_model():
    """返回 DashScope 文本嵌入模型实例。"""
    return DashScopeEmbeddings(
        model="text-embedding-v3",#阿里云最新版文本嵌入模型，生成 1024 维向量（具体维度取决于模型版本）。
        dashscope_api_key=os.getenv("LLM_API_KEY"),
    )
    # 返回值：一个可调用对象，输入文本列表，输出向量列表。

# --------------------------
# 构建向量库
# 输入 docs：一个 Document 对象列表（来自前文的 build_docs_from_metadata 函数）。
# FAISS.from_documents 内部做了什么？
# 1.遍历 docs，提取每个 Document 的 page_content 文本。
# 2.调用 embed.embed_documents(texts) 将所有文本批量转换为向量（一次 HTTP 请求）。
# 3.使用 FAISS 库构建向量索引（默认为 IndexFlatL2，即精确 L2 距离索引，适合中小规模数据）。
# 4.返回一个 FAISS 包装对象，该对象包含索引和原始文本片段。
# 5.返回 db：可用于相似性检索，例如 db.similarity_search("GMV 计算方式")。
# --------------------------
def _chunk_documents(docs, chunk_size):
    """按固定大小切分文档，避免单次嵌入请求超出服务上限。"""
    for idx in range(0, len(docs), chunk_size):
        yield docs[idx : idx + chunk_size]


def get_vector_db(docs):
    """将文档向量化并构建内存中的 FAISS 向量库。"""
    if not docs:
        raise ValueError("docs 为空，无法构建向量库。")

    embed = get_embedding_model()
    chunks = list(_chunk_documents(docs, Config.EMBED_MAX_BATCH_SIZE))
    # 首批先创建索引，后续批次追加，确保每次嵌入请求不超过上限。
    db = FAISS.from_documents(chunks[0], embed)
    for batch in chunks[1:]:
        db.add_documents(batch)
    return db