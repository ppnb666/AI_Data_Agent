"""
字段解析统一模块

修复背景：
此前 rank_tools.py / compare_tools.py / query_tools.py 各自都有
一份几乎相同的 find_customer_field()（三份重复代码），而且都只走
"schema.entities（LLM自动猜测） → 关键词兜底" 这条路径。

与此同时，api.py 有一整套"LLM猜字段 → 用户在前端确认 → 存进
state.mapping"的流程，但从未被任何工具函数读取——用户手动纠正
的映射结果会被静默丢弃，不会真正影响分析结果。

本模块把两套机制合并成统一的优先级：

    1. state.mapping（用户显式确认过的，最权威）
    2. schema["entities"]（LLM在SchemaAgent阶段自动猜测的）
    3. 关键词兜底（历史遗留，最后一道保险）

并把"customer"这个概念用的三份重复代码收敛为一处；后续如果要
支持"customer"之外的其它概念（amount/date/product/department/
project……），也统一走 resolve_field，不用再复制三份。
"""

from typing import Dict, List, Optional


# ==========================================================
# 内置的关键词兜底表
#
# 注意：这是"通用化改造"里第2步要动的地方——目前这份关键词表
# 是财务/合同场景专属的（客商名称、贷方等）。当你的Agent要支持
# 其它行业时，这里应该改成从行业模板加载，或者干脆去掉、完全
# 依赖 state.mapping + schema entities（LLM驱动），关键词表只
# 作为两者都失败时的最后兜底。
# ==========================================================

DEFAULT_FALLBACK_KEYWORDS: Dict[str, List[str]] = {
    "customer": ["客商名称", "客户名称", "客户", "客商"],
}


def clean_field(field: str) -> str:
    """
    去除 Schema 字段前缀

    Sheet1.客商名称 -> 客商名称
    """
    if field and "." in str(field):
        return str(field).split(".")[-1]
    return field


def get_schema_fields(schema: dict, key: str) -> List[str]:
    """从 schema['entities'][key] 中取出候选字段名（已去除Sheet前缀）"""
    if not isinstance(schema, dict):
        return []
    entities = schema.get("entities", {}) or {}
    raw_fields = entities.get(key, []) or []
    return [clean_field(f) for f in raw_fields]


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
    # 2. Schema（LLM）猜测的候选
    # ------------------------------------------------------
    for field in get_schema_fields(schema, key):
        if field in columns:
            return field

    # ------------------------------------------------------
    # 3. 关键词兜底
    # ------------------------------------------------------
    keywords = (
        fallback_keywords
        if fallback_keywords is not None
        else DEFAULT_FALLBACK_KEYWORDS.get(key, [])
    )
    for column in columns:
        if any(k in str(column) for k in keywords):
            return column

    return None


def find_customer_field(state, schema: dict, columns: List[str]) -> Optional[str]:
    """
    寻找客户字段的统一入口，替代此前分散在
    rank_tools.py / compare_tools.py / query_tools.py 里的三份重复实现。
    """
    return resolve_field(state, schema, columns, "customer")