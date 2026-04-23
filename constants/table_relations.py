# ====================== 数仓表关系（企业级硬编码，匹配当前MySQL表结构） ======================
# 核心关联：维度表 ↔ ODS原始表 ↔ DWD明细表，永不依赖模型记忆
TABLE_RELATIONS = """
1. dim_user.user_id = ods_order.user_id
2. ods_order.order_id = ods_order_item.order_id
3. ods_order_item.sku_id = dim_sku.sku_id
4. ods_order.order_id = dwd_order_detail.order_id
5. dwd_order_detail.user_id = dim_user.user_id
6. dwd_order_detail.sku_id = dim_sku.sku_id
"""

# ====================== 强制有效订单规则（生产级：锁死来源，模型不可篡改） ======================
# 订单状态定义：1-待付款 2-待发货 3-待收货 4-已完成(有效) 5-已取消
# 有效订单 = 已完成订单，支持 ODS层 / DWD层 双来源校验
VALID_ORDER_RULE = "ods_order.order_status = 4 AND dwd_order_detail.order_status = 4"