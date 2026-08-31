"""
数据分析工具

v2.2 Agent State版本
"""


from utils.analysis import (
    clean_data,
    get_top_product,
    detect_outliers
)




def clean_data_tool(state):

    """
    数据清洗工具

    输入:
        AgentState

    更新:
        state.df
        state.clean_count
    """


    # 修复：不再无差别删除"任意一列有空值"的行，
    # 只对真正关键的字段（销售额、产品名）做缺失值清洗，
    # 其它字段（如备注）允许为空，避免误删正常数据。
    key_columns = [
        c for c in [state.sales_col, state.product_col]
        if c
    ]

    result, count = clean_data(
        state.df,
        key_columns=key_columns
    )


    # 更新Agent状态

    state.df = result


    state.clean_count = count



    return state






def top_product_tool(state):

    """
    销售冠军分析工具

    更新:
        state.top_product
        state.top_sales
    """


    product, sales = get_top_product(
        state.df,
        state.sales_col,
        state.product_col
    )


    state.top_product = product


    state.top_sales = sales



    return state






def outlier_detection_tool(state):

    """
    异常检测工具

    更新:
        state.outliers
    """


    result = detect_outliers(
        state.df,
        state.sales_col
    )


    state.outliers = result



    return state