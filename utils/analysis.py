import pandas as pd


def clean_data(df, key_columns=None):
    """
    数据清洗：
    1. 删除重复数据
    2. 删除关键字段缺失的数据

    修复说明：
    此前用无参数的 df.dropna()，会因为任意一列（哪怕是备注、
    次要联系方式这类本来就允许为空的字段）有空值就删掉整行，
    在企业Excel场景下很容易误删大量本该保留的正常数据。

    现在改为：默认只删除"整行全部为空"的行（drop_duplicates后
    的正常清洗），如果调用方传入 key_columns（比如销售额列、
    客户名称列这些真正不该为空的关键字段），才对这些列做
    dropna，其余字段允许为空。
    """

    before = len(df)

    df = df.drop_duplicates()

    if key_columns:
        # 只有真正指定了"哪些字段不能为空"时，才按这些字段清洗
        existing_key_columns = [c for c in key_columns if c in df.columns]
        if existing_key_columns:
            df = df.dropna(subset=existing_key_columns)
    else:
        # 未指定关键字段时，只删除整行全部为空的记录，
        # 不再无差别删除"任意一列有空值"的行
        df = df.dropna(how="all")

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
    report.append(f"- 数据总量：{len(df)} 条\n")
    report.append(f"- 清洗删除数据：{clean_count} 条\n")
    report.append(f"- 字段数量：{len(df.columns)} 个\n\n")

    # 销售分析
    report.append("## 2. 销售分析\n\n")
    report.append(f"- 销售最高产品：{top_product}\n")
    report.append(f"- 最高销售额：{top_sales}\n\n")

    # 异常检测
    report.append("## 3. 异常检测\n\n")
    report.append(f"- 发现异常数据：{len(outliers)} 条\n\n")

    # 字段信息
    report.append("## 4. 字段信息\n\n")
    for col in df.columns:
        report.append(f"- {col}\n")

    # ===== 数据可视化（两张图） =====
    report.append("\n## 5. 数据可视化\n\n")

    report.append("### 产品销售排行\n\n")
    report.append("![产品销售额柱状图](product_sales.png)\n\n")

    report.append("### 销售趋势\n\n")
    report.append("![销售趋势图](sales_trend.png)\n")

    return "".join(report)