

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
    使用IQR方法检测异常值

    规则：
    大于 Q3 + 1.5*IQR 的数据认为是异常
    小于 Q1 - 1.5*IQR 的数据认为是异常
    """

    Q1 = df[column].quantile(0.25)

    Q3 = df[column].quantile(0.75)

    IQR = Q3 - Q1


    lower_bound = Q1 - 1.5 * IQR

    upper_bound = Q3 + 1.5 * IQR


    outliers = df[
        (df[column] < lower_bound) |
        (df[column] > upper_bound)
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

def generate_markdown_report(
        df,
        clean_count,
        top_product,
        top_sales,
        outliers
):
    """
    生成Markdown格式分析报告
    """

    report = []

    report.append("# 数据分析报告\n\n")


    # 数据概览
    report.append("## 1. 数据概览\n\n")

    report.append(
        f"- 数据总量：{len(df)} 条\n"
    )

    report.append(
        f"- 清洗删除数据：{clean_count} 条\n"
    )

    report.append(
        f"- 字段数量：{len(df.columns)} 个\n\n"
    )


    # 销售分析
    report.append("## 2. 销售分析\n\n")

    report.append(
        f"- 销售最高产品：{top_product}\n"
    )

    report.append(
        f"- 最高销售额：{top_sales}\n\n"
    )


    # 异常检测
    report.append("## 3. 异常检测\n\n")

    report.append(
        f"- 发现异常数据：{len(outliers)} 条\n\n"
    )


    # 字段信息
    report.append("## 4. 字段信息\n\n")

    for col in df.columns:
        report.append(
            f"- {col}\n"
        )


    # 图片
    report.append("\n## 5. 数据可视化\n\n")

    report.append(
        "![产品销售额柱状图](product_sales.png)\n"
    )


    return "".join(report)