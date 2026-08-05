

import pandas as pd


def clean_data(df):
    """
    数据清洗：
    1. 删除重复数据
    2. 删除缺失数据
    """

    before = len(df)

    df = df.drop_duplicates()

    df = df.dropna()

    after = len(df)

    clean_count = before - after

    return df, clean_count



def check_missing_values(df):
    """
    检查缺失值
    """

    missing = df.isnull().sum()

    return missing[missing > 0]



def check_duplicates(df):
    """
    检查重复数据
    """

    return df.duplicated().sum()



def get_top_product(df, sales_column, product_column):
    """
    找销售额最高产品
    """

    if df.empty:
        return "无数据", 0


    product_sales = (
        df.groupby(product_column)[sales_column]
        .sum()
    )


    top_product = product_sales.idxmax()

    top_sales = product_sales.max()


    return top_product, top_sales



def detect_outliers(df, column):
    """
    简单异常检测

    超过平均值2倍认为异常
    """

    mean_value = df[column].mean()

    outliers = df[
        df[column] > mean_value * 2
    ]

    return outliers



def generate_summary(df):
    """
    数据摘要
    """

    summary = {

        "总数据量": len(df),

        "字段数量": len(df.columns),

        "字段名称": list(df.columns),

        "数据类型":
            df.dtypes.astype(str).to_dict()

    }


    return summary



def generate_report(
        df,
        clean_count,
        top_product,
        top_sales
):

    """
    生成文本报告
    """

    report = []

    report.append(
        "====== 数据分析报告 ======\n"
    )


    report.append(
        f"数据总量：{len(df)} 条\n"
    )


    report.append(
        f"清洗删除数据：{clean_count} 条\n"
    )


    report.append(
        f"销售额最高产品：{top_product}\n"
    )


    report.append(
        f"最高销售额：{top_sales}\n"
    )


    report.append(
        "\n字段信息：\n"
    )


    for col in df.columns:

        report.append(
            f"- {col}\n"
        )


    return "".join(report)