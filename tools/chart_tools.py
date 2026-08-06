"""
可视化工具

v2.2 Agent State版本
"""


from utils.visualization import (
    plot_product_sales,
    plot_sales_trend
)



def create_chart_tool(state):

    """
    销售数据可视化工具

    输入:
        AgentState

    更新:
        state.charts
    """


    charts = {}



    # 产品销售排行图

    plot_product_sales(
        state.df,
        state.product_col,
        state.sales_col,
        state.chart_path
    )


    charts["product_chart"] = (
        state.chart_path
    )



    # 销售趋势图

    if (
        state.date_col
        and state.trend_chart_path
    ):


        plot_sales_trend(
            state.df,
            state.date_col,
            state.sales_col,
            state.trend_chart_path
        )


        charts["trend_chart"] = (
            state.trend_chart_path
        )



    state.charts = charts



    return state