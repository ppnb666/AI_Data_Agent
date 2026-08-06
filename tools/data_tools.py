
from utils.analysis import (
    clean_data,
    check_missing_values,
    check_duplicates,
    get_top_product,
    detect_outliers,
    generate_summary
)


def sales_analysis_tool(df, sales_column, product_column):
    """
    销售分析工具
    """

    result = {}


    # 数据清洗
    df_clean, clean_count = clean_data(df)

    result["clean_df"] = df_clean
    result["clean_count"] = clean_count


    # 缺失值
    missing = check_missing_values(df_clean)

    result["missing"] = missing.to_dict()


    # 重复数据
    result["duplicates"] = check_duplicates(df_clean)


    # 销售冠军

    top_product, top_sales = get_top_product(
        df_clean,
        sales_column,
        product_column
    )


    result["top_product"] = top_product
    result["top_sales"] = top_sales


    # 异常检测

    outliers = detect_outliers(
        df_clean,
        sales_column
    )

    result["outliers"] = outliers
    result["outlier_count"] = len(outliers)


    # 数据摘要

    result["summary"] = generate_summary(df_clean)


    return result