# 数仓表关系（企业级硬编码，永不依赖模型记忆）
TABLE_RELATIONS = """
1. ods_user.user_id = dwd_order_info.user_id
2. dwd_order_info.order_id = dwd_order_detail.order_id
3. ods_sku.sku_id = dwd_order_detail.sku_id
"""

# 强制有效订单字段（生产级：锁死来源，模型不能乱选）
VALID_ORDER_RULE = "dwd_order_info.order_status = 1"