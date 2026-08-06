"""
数据分析工具
"""

from utils.analysis import (
    clean_data,
    get_top_product,
    detect_outliers
)



def clean_data_tool(df):

    """
    数据清洗工具
    """

    result,count = clean_data(df)

    return {
        "data":result,
        "clean_count":count
    }



def top_product_tool(
    df,
    sales_col,
    product_col
):

    """
    销售冠军分析工具
    """

    product,sales = get_top_product(
        df,
        sales_col,
        product_col
    )

    return {
        "product":product,
        "sales":sales
    }



def outlier_detection_tool(
    df,
    sales_col
):

    """
    异常检测工具
    """

    result = detect_outliers(
        df,
        sales_col
    )

    return {
        "count":len(result),
        "data":result
    }