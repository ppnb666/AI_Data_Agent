from .registry import tool_registry
from .query_tools import query_value_tool

from .data_tools import (
    clean_data_tool,
    top_product_tool,
    outlier_detection_tool
)


from .chart_tools import create_chart_tool
from .report_tools import (
    generate_report_tool,
    generate_markdown_report_tool
)



# 注册工具

tool_registry.register(
    "clean_data",
    "清洗Excel数据，删除空值和异常格式",
    clean_data_tool
)


tool_registry.register(
    "top_product",
    "分析销售额最高的产品",
    top_product_tool
)


tool_registry.register(
    "detect_outliers",
    "检测销售异常数据",
    outlier_detection_tool
)


tool_registry.register(
    "create_chart",
    "生成销售分析图表",
    create_chart_tool
)

tool_registry.register(
    "generate_report",
    "生成销售分析文本报告",
    generate_report_tool
)


tool_registry.register(
    "generate_markdown_report",
    "生成Markdown分析报告",
    generate_markdown_report_tool
)

tool_registry.register(
    "query_value",
    "根据用户条件查询Excel数据",
    query_value_tool
)