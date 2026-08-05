import pandas as pd

from utils.analysis import (
    clean_data,
    check_missing_values,
    check_duplicates,
    get_top_product,
    detect_outliers,
    generate_summary,
    generate_report
)



def analyze_excel(file_path):

    # 读取Excel

    df = pd.read_excel(file_path)


    print("=" * 50)

    print("原始数据：")

    print(df.head())


    # 数据清洗

    df, clean_count = clean_data(df)


    print("\n清洗完成")

    print(
        f"删除数据：{clean_count} 条"
    )


    # 缺失值检测

    print("\n" + "="*50)

    print("缺失值检测：")

    print(
        check_missing_values(df)
    )


    # 重复值检测

    print("\n" + "="*50)

    print("重复数据：")

    print(
        check_duplicates(df)
    )


    # 销售冠军

    print("\n" + "="*50)

    top_product, top_sales = get_top_product(
        df,
        "销售额",
        "产品"
    )


    print(
        f"最高销售产品：{top_product}"
    )

    print(
        f"销售额：{top_sales}"
    )



    # 异常检测

    print("\n" + "="*50)

    print("异常销售数据：")

    print(
        detect_outliers(
            df,
            "销售额"
        )
    )



    # 数据摘要

    print("\n" + "="*50)

    print("数据摘要")

    summary = generate_summary(df)


    for key,value in summary.items():

        print(
            f"{key}:{value}"
        )



    # 生成报告

    report = generate_report(
        df,
        clean_count,
        top_product,
        top_sales
    )


    with open(
        "reports/report.txt",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report)



    print("\n报告已经生成：reports/report.txt")





if __name__ == "__main__":

    analyze_excel(
        "data/sales.xlsx"
    )