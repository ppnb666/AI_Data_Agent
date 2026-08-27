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

from tools.registry import tool_registry

# 已有工具
from tools.query_tools import query_value_tool
from tools.compare_tools import compare_rows_tool
# 新增排名工具
from tools.rank_tools import rank_rows_tool

tool_registry.register("query_value", "查询企业数据", query_value_tool)
tool_registry.register("compare_rows", "比较两个字段差异并返回异常行", compare_rows_tool)
tool_registry.register("rank_rows", "按客户分组汇总指标并排名", rank_rows_tool)