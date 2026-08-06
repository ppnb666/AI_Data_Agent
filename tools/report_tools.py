"""
报告生成工具
"""

from utils.analysis import (
    generate_report,
    generate_markdown_report
)


def generate_report_tool(
        df,
        clean_count,
        top_product,
        top_sales,
        report_path
):
    """
    生成文本报告工具
    """

    report = generate_report(
        df,
        clean_count,
        top_product,
        top_sales
    )

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(report)

    return {
        "report_path": report_path
    }



def generate_markdown_report_tool(
        df,
        clean_count,
        top_product,
        top_sales,
        outliers,
        md_path
):
    """
    生成 Markdown报告工具
    """

    md_report = generate_markdown_report(
        df,
        clean_count,
        top_product,
        top_sales,
        outliers
    )

    with open(
        md_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(md_report)


    return {
        "markdown_path": md_path
    }