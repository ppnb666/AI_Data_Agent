"""
字段角色枚举常量表（全系统唯一事实来源）

角色分为三类：
    维度角色：customer / business / product / department / project /
              region / person / category —— 用于分组、过滤、关联
    指标角色：amount（货币，含 unit）/ number（计数 / 比率）
    其他：date / id / text / unknown

消费方：
    - api.py 的 allowed_keys（LLM 字段猜测 JSON 键）
    - tools.field_resolver 的 DEFAULT_FALLBACK_KEYWORDS 键
    - schema_agent 的 classify_roles_with_llm 输出校验

任何新增 / 修改角色，只改这一处。
"""

# 维度角色
DIMENSION_ROLES = [
    "customer",     # 客户 / 客商 / 供应商 / 公司
    "business",     # 业务类型 / 产品线
    "product",      # 产品 / 商品 / SKU
    "department",   # 部门 / 组织 / 事业部
    "project",      # 项目 / 工程
    "region",       # 地区 / 区域
    "person",       # 人员 / 姓名 / 负责人
    "category",     # 其他分类（品类 / 类别 / 状态 / 类型）
]

# 指标角色
METRIC_ROLES = [
    "amount",       # 货币金额（含 unit）
    "number",       # 计数 / 比率 / 数量
]

# 其他
OTHER_ROLES = [
    "date",         # 时间 / 日期 / 年份 / 期间
    "id",           # 编码 / 编号 / 主键
    "text",         # 备注 / 描述等自由文本
    "unknown",      # 无法识别
]

ALL_ROLES = DIMENSION_ROLES + METRIC_ROLES + OTHER_ROLES

# LLM 角色识别 JSON 中允许出现的角色（unknown 不要求 LLM 输出，
# 由兜底链在识别失败时填写）
LLM_ALLOWED_ROLES = [
    "customer", "business", "product", "department", "project",
    "region", "person", "category",
    "amount", "number", "date", "id", "text",
]

# 中文角色名（供 prompt / 日志使用）
ROLE_LABELS = {
    "customer": "客户/客商",
    "business": "业务类型",
    "product": "产品/商品",
    "department": "部门/组织",
    "project": "项目/工程",
    "region": "地区/区域",
    "person": "人员/姓名",
    "category": "分类/类别",
    "amount": "金额（货币）",
    "number": "数量/比率",
    "date": "日期/时间",
    "id": "编码/编号",
    "text": "备注/描述",
    "unknown": "未知",
}


def normalize_role(role):
    """把 LLM / 关键词可能输出的别名归一为规范角色，未知返回 unknown"""
    if not role:
        return "unknown"
    role = str(role).strip().lower()
    # 常见别名映射
    alias = {
        "customer_name": "customer",
        "name": "customer",
        "money": "amount",
        "currency": "amount",
        "price": "amount",
        "amounts": "amount",
        "numeric": "number",
        "count": "number",
        "quantity": "number",
        "rate": "number",
        "ratio": "number",
        "time": "date",
        "datetime": "date",
        "year": "date",
        "month": "date",
        "code": "id",
        "no": "id",
        "desc": "text",
        "description": "text",
        "remark": "text",
        "notes": "text",
    }
    if role in alias:
        return alias[role]
    if role in ALL_ROLES:
        return role
    return "unknown"
