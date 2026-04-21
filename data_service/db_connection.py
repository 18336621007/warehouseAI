from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from configs.settings import Config

engine = create_engine(Config.DB_URI, pool_pre_ping=True) #数据库实例
sql_db = SQLDatabase.from_uri(Config.DB_URI) #创建一个 LangChain数据库工具实例，内部也会调用 create_engine（使用默认参数）