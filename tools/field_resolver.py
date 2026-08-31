"""
字段解析统一模块

优先级（全系统统一）：
    1. state.mapping（用户显式确认过的，最权威）
    2. schema["roles"]（SchemaAgent LLM 识别 / 关键词兜底的
       字段角色索引，通用化改造后的唯一事实来源）
    3. 关键词兜底（KEYWORD_ROLES，最后一道保险）

此前 rank_tools / compare_tools / query_tools 各自维护一份
find_customer_field() 的重复实现，现在统一收敛到本模块；
"customer"之外的其它概念（amount/date/product/department/
project……）也统一走 resolve_field / resolve_role_fields。
"""

from typing import Dict, List, Optional

from schema.keyword_roles import KEYWORD_ROLES


# ==========================================================
# 关键词兜底表（与 schema/keyword_roles.py 同一份词表，
# 覆盖全部角色：customer/business/product/department/project/
# region/person/category/amount/number/date/id/text）
# ==========================================================

DEFAULT_FALLBACK_KEYWORDS: Dict[str, List[str]] = {
    role: list(keywords)
    for role, keywords in KEYWORD_ROLES.items()
}

# 旧概念名 → 角色名 别名
_ROLE_ALIAS = {
    "money": "amount",
    "time": "date",
}


def _normalize_key(key: str) -> str:
    return _ROLE_ALIAS.get(str(key), str(key))


def clean_field(field: str) -> str:
    """
    去除 Schema 字段前缀

    Sheet1.客商名称 -> 客商名称
    """
    if field and "." in str(field):
        return str(field).split(".")[-1]
    return field


def get_schema_fields(schema: dict, key: str) -> List[str]:
    """
    从 schema 中取出候选字段名（已去除 Sheet 前缀）。

    优先读 schema["roles"]（唯一事实来源），
    兼容旧结构 entities / metrics / time_fields。
    """
    if not isinstance(schema, dict):
        return []
    role = _normalize_key(key)

    # 新结构：roles 角色索引
    roles = schema.get("roles", {}) or {}
    if role in roles:
        return [clean_field(f) for f in roles[role]]

    # 兼容旧结构
    entities = schema.get("entities", {}) or {}
    if role in entities:
        return [clean_field(f) for f in entities[role]]

    metrics = schema.get("metrics", {}) or {}
    if role in metrics:
        return [clean_field(f) for f in metrics[role]]

    if role == "date":
        return [clean_field(f) for f in schema.get("time_fields", [])]

    return []


def resolve_field(
    state,
    schema: dict,
    columns: List[str],
    key: str,
    fallback_keywords: Optional[List[str]] = None,
) -> Optional[str]:
    """
    统一的字段解析入口。

    参数：
        state: AgentState，用于读取 state.mapping（用户确认过的映射）
        schema: 当前workbook/sheet的schema（包含LLM猜测的entities）
        columns: 当前Sheet实际存在的列名列表
        key: 要找的业务概念，如 "customer" / "amount" / "date"
        fallback_keywords: 可选，覆盖默认的关键词兜底列表

    优先级：
        1. state.mapping[key]  —— 用户在前端确认过的映射，
           只要该字段确实存在于当前Sheet的列里就直接采用
        2. schema['entities'][key] —— SchemaAgent/LLM自动猜测的候选，
           取第一个在当前Sheet列中存在的
        3. 关键词兜底 —— 历史遗留的保险丝，行业相关，建议逐步淘汰
    """

    # ------------------------------------------------------
    # 1. 用户确认过的映射优先
    # ------------------------------------------------------
    mapping = getattr(state, "mapping", None) or {}
    mapped_field = mapping.get(key)
    if mapped_field:
        mapped_field = clean_field(mapped_field)
        if mapped_field in columns:
            return mapped_field
        # 用户映射的字段在当前Sheet里不存在（比如映射的是Sheet1的字段，
        # 现在处理的是Sheet2），不强行返回，继续往下走schema兜底

    # ------------------------------------------------------
    # 2. Schema（LLM/关键词识别）的候选
    # ------------------------------------------------------
    for field in get_schema_fields(schema, key):
        if field in columns:
            return field

    # 客户字段缺失时，person（姓名列）可作为查询实体兜底
    if _normalize_key(key) == "customer":

        for field in get_schema_fields(schema, "person"):

            if field in columns:

                return field

    # ------------------------------------------------------
    # 3. 关键词兜底
    # ------------------------------------------------------
    keywords = (
        fallback_keywords
        if fallback_keywords is not None
        else DEFAULT_FALLBACK_KEYWORDS.get(_normalize_key(key), [])
    )
    for column in columns:
        if any(k in str(column) for k in keywords):
            return column

    # 客户关键词兜底同样允许命中 person 关键词（姓名列）
    if _normalize_key(key) == "customer":

        person_keywords = DEFAULT_FALLBACK_KEYWORDS.get("person", [])

        for column in columns:

            if any(k in str(column) for k in person_keywords):

                return column

    return None


def resolve_role_fields(
    state,
    schema: dict,
    columns: List[str],
    role: str,
) -> List[str]:
    """
    解析某个角色的全部候选字段（只返回当前 Sheet 中真实存在的列）。

    例如 rank_tools 需要"按 customer → business/product/department/
    project 依次取分组字段"时，逐个角色调用本函数即可。

    优先级：state.mapping → schema.roles → 关键词兜底
    """
    role = _normalize_key(role)

    # 1. 用户确认过的映射
    mapping = getattr(state, "mapping", None) or {}
    mapped = mapping.get(role)
    if mapped:
        mapped = clean_field(mapped)
        if mapped in columns:
            return [mapped]

    # 2. Schema 角色索引（多个 Sheet 的同名列去重）
    schema_fields = get_schema_fields(schema, role)
    found = list(dict.fromkeys(f for f in schema_fields if f in columns))
    if found:
        return found

    # 3. 关键词兜底（列名包含任意角色关键词）
    keywords = DEFAULT_FALLBACK_KEYWORDS.get(role, [])
    found = [c for c in columns if any(k in str(c) for k in keywords)]
    return found


def find_customer_field(state, schema: dict, columns: List[str]) -> Optional[str]:
    """
    寻找客户字段的统一入口，替代此前分散在
    rank_tools.py / compare_tools.py / query_tools.py 里的三份重复实现。
    """
    return resolve_field(state, schema, columns, "customer")