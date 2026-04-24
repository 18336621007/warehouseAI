# AI 数仓智能问答系统
### 基于 Python + RAG + SQL Agent 的电商数仓问答系统。
目标是将自然语言问题转为可执行 SQL，并通过语义层、SQL 校验器和回归机制保障结果可解释、可追踪、可落地。
## 1. 项目特性
RAG 双路召回：表结构与业务规则分流召回，减少模型幻觉

语义层词典：支持 measures / dimensions / metrics，实现指标口径结构化

查询计划链路：Query Planner -> SQL Renderer -> SQL Validator -> Execute

AST 级 SQL 校验：只读限制、危险语句拦截、口径保护、禁用表达式校验

灰度回退机制：新链路异常时自动回退到旧 SQLAgent 路径

多轮上下文支持：窗口化历史会话，支持连续追问与指代问题

结构化日志：记录 query plan、渲染 SQL、校验结果与路由信息

## 2. 项目结构
.  
├─ main.py                       # CLI入口，主流程编排  
├─ configs/  
│  ├─ settings.py                # 全局配置  
│  └─ metric_dictionary.yaml     # 语义层词典（指标/维度/规则）  
├─ core/  
│  ├─ metric_dictionary.py       # 词典加载与匹配  
│  ├─ query_planner.py           # 查询计划器  
│  ├─ sql_renderer.py            # SQL渲染器  
│  ├─ sql_validator.py           # AST SQL校验器  
│  └─ planner_regression.py      # 回归脚本  
├─ rag/  
│  ├─ doc_builder.py             # 文档构建（元数据/规则）  
│  ├─ retriever.py               # 检索逻辑  
│  └─ vector_store.py            # 向量库构建（分批嵌入）  
├─ data_service/  
│  ├─ db_connection.py           # 数据库连接  
│  └─ meta_fetcher.py            # 元数据拉取  
└─ constants/                    # 业务规则与关系常量  

## 3. 运行流程（简版）
拉取数据库元数据（表/字段/主键信息）  
构建文档并写入向量库  
接收用户问题  
命中语义词典并构建 query plan（可灰度）  
渲染 SQL 并做 AST 校验  
执行 SQL，返回“结论 + 依据”  

## 4.环境依赖
Python 3.8+  
MySQL  
关键库：  
langchain  
langchain-openai  
faiss-cpu  
sqlalchemy  
pymysql  
python-dotenv  
pyyaml  
sqlglot  
安装依赖：`pip install -r requirements.txt  
## 5.指标词典说明
configs/metric_dictionary.yaml 包含：  

measures：原子指标（如订单数、支付金额）  
dimensions：原子维度（如用户、日期、类目）  
metrics：派生指标（如 GMV、客单价）  
join_paths：合法 Join 路径  
forbidden：禁用表达式（防止指标混淆）  
## 6.安全与质量保障
仅允许只读查询（禁止写操作）  
危险语句拦截  
指标规则校验（禁用表达式）  
口径自动保护（按规则补充有效条件）  
结构化日志追踪  
回归脚本验证核心链路  

## 7.常见问题（FAQ）
### Q1: 报错 batch size ... should not be larger than 10  
A: 嵌入接口单次批量上限问题。项目已支持分批嵌入，确认 EMBED_MAX_BATCH_SIZE<=10。

### Q2: 问答显示“无数据”，但数据库有数据
A: 先检查 DB_URI 和 DB_NAME 是否一致指向目标库；再检查词典与表关系是否与当前库结构一致。

### Q3: 为什么某些问题走回退链路
A: 仅配置在 QUERY_PLANNER_METRICS 内的指标优先走新链路，其他问题会回退旧 SQLAgent 路径。Q1: 报错 batch size ... should not be larger than 10  
A: 嵌入接口单次批量上限问题。项目已支持分批嵌入，确认 EMBED_MAX_BATCH_SIZE<=10。

### Q2: 问答显示“无数据”，但数据库有数据
A: 先检查 DB_URI 和 DB_NAME 是否一致指向目标库；再检查词典与表关系是否与当前库结构一致。

### Q3: 为什么某些问题走回退链路
A: 仅配置在 QUERY_PLANNER_METRICS 内的指标优先走新链路，其他问题会回退旧 SQLAgent 路径。

## 8.项目目标与后续计划
完善语义层覆盖更多业务指标与维度  
优化 Planner 的意图解析能力（时间范围、复杂过滤）  
增强 SQL 渲染器对复杂分析场景支持  
增加自动化评测集与性能压测流程  
