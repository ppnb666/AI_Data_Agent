"""
工具初始化
"""

from tools.registry import tool_registry


# =========================
# 查询工具
# =========================

from tools.query_tools import query_value_tool

tool_registry.register(
    "query_value",
    "查询企业数据",
    query_value_tool
)


# =========================
# 对比工具
# =========================

from tools.compare_tools import compare_rows_tool

tool_registry.register(
    "compare_rows",
    "比较两个字段差异并返回异常行",
    compare_rows_tool
)


# =========================
# 排名工具
# =========================

from tools.rank_tools import rank_rows_tool

tool_registry.register(
    "rank_rows",
    "按客户分组汇总指标并排名",
    rank_rows_tool
)


# =========================
# 汇总工具
# =========================

from tools.query_tools import aggregate_value_tool

tool_registry.register(
    "aggregate_value",
    "汇总统计金额/数量字段（合计/总额/总计/求和）",
    aggregate_value_tool
)


# =========================
# 异常检测工具
# =========================

from tools.query_tools import detect_anomaly_tool

tool_registry.register(
    "detect_anomaly",
    "检测数值字段的异常值（均值±2σ）",
    detect_anomaly_tool
)
