import pandas as pd
import logging
from config import (
    DATA_PATH,
    REPORT_PATH,
    CHART_PATH,
    MD_REPORT_PATH,
    TREND_CHART_PATH
)
from utils.analysis import (
    clean_data,
    check_missing_values,
    check_duplicates,
    get_top_product,
    detect_outliers,
    generate_summary,
    generate_report,
    generate_markdown_report
)
from utils.data_parser import detect_columns
from utils.visualization import plot_product_sales, plot_sales_trend


def analyze_excel(file_path, report_path, chart_path, md_path, trend_path):
    # 获取日志记录器
    logger = logging.getLogger()

    try:
        # 读取Excel
        logger.info("=" * 50)
        logger.info("开始执行数据分析")
        logger.info(f"数据文件路径：{file_path}")

        df = pd.read_excel(file_path)
        logger.info(f"成功读取 Excel 文件，共 {len(df)} 行数据")

        # 自动检测列名
        columns = detect_columns(df)
        sales_col = columns.get('sales_column')
        product_col = columns.get('product_column')
        date_col = columns.get('date_column')

        logger.info("列名自动检测结果：")
        logger.info(f"  销售额列：{sales_col}")
        logger.info(f"  产品列：{product_col}")
        logger.info(f"  日期列：{date_col}")

        if sales_col is None:
            logger.error("未找到销售额列，请检查数据格式！")
            return
        if product_col is None:
            logger.error("未找到产品列，请检查数据格式！")
            return
        if date_col is None:
            logger.warning("未找到日期列，部分功能（如趋势图）可能无法使用")

        # 数据预览
        logger.info("原始数据预览：")
        logger.info("\n" + str(df.head()))

        # 数据清洗
        logger.info("开始执行数据清洗...")
        df, clean_count = clean_data(df)
        logger.info(f"数据清洗完成，删除 {clean_count} 条数据")

        # 缺失值检测
        logger.info("执行缺失值检测...")
        missing = check_missing_values(df)
        if missing.empty:
            logger.info("✅ 无缺失值")
        else:
            logger.warning(f"发现缺失值：\n{missing}")

        # 重复值检测
        logger.info("执行重复值检测...")
        dup_count = check_duplicates(df)
        if dup_count == 0:
            logger.info("✅ 无重复数据")
        else:
            logger.warning(f"发现 {dup_count} 行重复数据")

        # 销售冠军
        logger.info("分析销售冠军...")
        top_product, top_sales = get_top_product(df, sales_col, product_col)
        logger.info(f"🏆 销售冠军：{top_product}，总销售额：{top_sales}")

        # 异常检测
        logger.info("执行异常检测...")
        outliers = detect_outliers(df, sales_col)
        if len(outliers) == 0:
            logger.info("✅ 未发现异常数据")
        else:
            logger.warning(f"发现 {len(outliers)} 条异常数据")
            logger.info(f"异常数据：\n{outliers}")

        # 数据摘要
        logger.info("生成数据摘要...")
        summary = generate_summary(df)
        for key, value in summary.items():
            logger.info(f"  {key}：{value}")

        # ===== 生成可视化图表 =====
        logger.info("生成可视化图表...")

        # 柱状图：产品销售排行
        if product_col is not None and sales_col is not None:
            plot_product_sales(df, product_col, sales_col, chart_path)
            logger.info(f"销售排行图已保存：{chart_path}")

        # 折线图：销售趋势
        if date_col is not None and sales_col is not None:
            plot_sales_trend(df, date_col, sales_col, trend_path)
            logger.info(f"销售趋势图已保存：{trend_path}")
        else:
            logger.warning("缺少日期列，跳过生成趋势图")

        # ===== 生成 TXT 报告 =====
        logger.info("生成 TXT 报告...")
        report = generate_report(df, clean_count, top_product, top_sales)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"TXT 报告已生成：{report_path}")

        # ===== 生成 Markdown 报告 =====
        logger.info("生成 Markdown 报告...")
        md_report = generate_markdown_report(
            df,
            clean_count,
            top_product,
            top_sales,
            outliers
        )
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)
        logger.info(f"Markdown 报告已生成：{md_path}")

        logger.info("=" * 50)
        logger.info("数据分析完成！✅")

    except FileNotFoundError:
        logger.error(f"文件未找到：{file_path}")
        logger.error("请检查文件路径是否正确")
    except Exception as e:
        logger.error(f"程序运行出错：{str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # 在程序入口初始化日志系统
    from utils.logger import setup_logger

    # 创建日志实例，同时输出到控制台和文件
    logger = setup_logger(console_output=True)

    analyze_excel(
        DATA_PATH,
        REPORT_PATH,
        CHART_PATH,
        MD_REPORT_PATH,
        TREND_CHART_PATH
    )