import pandas as pd
from config import DATA_PATH, REPORT_PATH
from utils.analysis import (
    clean_data,
    check_missing_values,
    check_duplicates,
    get_top_product,
    detect_outliers,
    generate_summary,
    generate_report
)
from utils.data_parser import detect_columns
from utils.visualization import plot_product_sales  # ← 新增


def analyze_excel(file_path, report_path):
    # 读取Excel
    df = pd.read_excel(file_path)

    # 自动检测列名
    columns = detect_columns(df)
    sales_col = columns.get('sales_column')
    product_col = columns.get('product_column')

    print("=" * 50)
    print("列名自动检测结果：")
    print(f"销售额列：{sales_col}")
    print(f"产品列：{product_col}")
    print(f"日期列：{columns.get('date_column')}")

    if sales_col is None:
        print("⚠️ 警告：未找到销售额列，请检查数据格式！")
        return
    if product_col is None:
        print("⚠️ 警告：未找到产品列，请检查数据格式！")
        return

    print("\n" + "=" * 50)
    print("原始数据：")
    print(df.head())

    # 数据清洗
    df, clean_count = clean_data(df)

    print("\n清洗完成")
    print(f"删除数据：{clean_count} 条")

    # 缺失值检测
    print("\n" + "=" * 50)
    print("缺失值检测：")
    print(check_missing_values(df))

    # 重复值检测
    print("\n" + "=" * 50)
    print("重复数据：")
    print(check_duplicates(df))

    # 销售冠军
    print("\n" + "=" * 50)
    top_product, top_sales = get_top_product(df, sales_col, product_col)

    print(f"最高销售产品：{top_product}")
    print(f"销售额：{top_sales}")

    # 异常检测
    print("\n" + "=" * 50)
    print("异常销售数据：")
    print(detect_outliers(df, sales_col))

    # 数据摘要
    print("\n" + "=" * 50)
    print("数据摘要")
    summary = generate_summary(df)

    for key, value in summary.items():
        print(f"{key}:{value}")

    # ===== 新增：生成可视化图表 =====
    print("\n" + "=" * 50)
    print("正在生成图表...")

    chart_path = "reports/product_sales.png"
    plot_product_sales(df, product_col, sales_col, chart_path)
    print(f"图表已保存：{chart_path}")

    # 生成报告
    report = generate_report(df, clean_count, top_product, top_sales)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n报告已经生成：{report_path}")


if __name__ == "__main__":
    analyze_excel(DATA_PATH, REPORT_PATH)