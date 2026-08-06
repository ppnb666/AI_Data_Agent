"""
报告生成工具

v2.2 Agent State版本
"""


from utils.analysis import (
    generate_report,
    generate_markdown_report
)




def generate_report_tool(state):

    """
    生成文本报告

    更新:
        state.report
    """


    report = generate_report(
        state.df,
        state.clean_count,
        state.top_product,
        state.top_sales
    )


    with open(
        state.report_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report)



    state.report = report


    return state





def generate_markdown_report_tool(state):

    """
    生成Markdown报告
    """


    md_report = generate_markdown_report(
        state.df,
        state.clean_count,
        state.top_product,
        state.top_sales,
        state.outliers
    )


    with open(
        state.md_report_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(md_report)



    state.md_report = md_report


    return state