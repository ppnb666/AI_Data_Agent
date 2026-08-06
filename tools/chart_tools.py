"""
可视化工具
"""

from utils.visualization import (
    plot_product_sales,
    plot_sales_trend
)


def create_chart_tool(
        df,
        product_col,
        sales_col,
        chart_path,
        date_col=None,
        trend_path=None
):
    """
    销售数据可视化工具

    功能：
    1. 生成产品销售排行图
    2. 生成销售趋势图

    """

    result = {}

    # 产品销售排行图
    product_chart = plot_product_sales(
        df,
        product_col,
        sales_col,
        chart_path
    )

    result["product_chart"] = chart_path


    # 销售趋势图（如果存在日期字段）
    if date_col and trend_path:

        plot_sales_trend(
            df,
            date_col,
            sales_col,
            trend_path
        )

        result["trend_chart"] = trend_path


    return result