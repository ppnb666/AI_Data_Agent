# ==============================
# 先加载工具注册
# 必须放最前面
# ==============================

import os
import tools

from agent import DataAgent
from config import DATA_PATH


# =========================================================
# 查询结果输出
# =========================================================

def print_query_value_result(result):

    print("\n========== 查询结果 ==========")

    status = result.get(
        "status",
        "unknown"
    )

    # -----------------------------------------------------
    # 查询失败
    # -----------------------------------------------------

    if status != "success":

        print(
            f"❌ 查询失败："
            f"{result.get('message', '未知错误')}"
        )

        return

    # -----------------------------------------------------
    # 基本信息
    # -----------------------------------------------------

    print(
        f"👤 客户："
        f"{result.get('customer', '')}"
    )

    print(
        f"📊 总记录数："
        f"{result.get('total_count', 0)} 条"
    )

    print(
        f"✅ 匹配记录："
        f"{result.get('matched_count', 0)} 条"
    )

    # -----------------------------------------------------
    # 过滤条件
    # -----------------------------------------------------

    filters = result.get(
        "filters",
        {}
    )

    if filters:

        print(
            "\n🔎 过滤条件："
        )

        for key, value in filters.items():

            print(
                f"  {key}：{value}"
            )

    # -----------------------------------------------------
    # 金额汇总
    # -----------------------------------------------------

    summary = result.get(
        "summary",
        {}
    )

    if summary:

        print(
            "\n💰 金额汇总："
        )

        for key, value in summary.items():

            print(
                f"  {key}：{value}"
            )

    # -----------------------------------------------------
    # 查询数据
    # -----------------------------------------------------

    data = result.get(
        "data",
        {}
    )

    rows = data.get(
        "rows",
        []
    )

    if not rows:

        print(
            "\n📋 没有匹配数据"
        )

        return

    print(
        f"\n📋 匹配数据（前 {len(rows)} 条）："
    )

    for i, row in enumerate(
        rows,
        start=1
    ):

        print(
            f"\n--- 第 {i} 条 ---"
        )

        for key, value in row.items():

            print(
                f"{key}：{value}"
            )


# =========================================================
# 比较结果输出
# =========================================================

def print_compare_rows_result(result):

    print(
        "\n========== 比较结果 =========="
    )

    status = result.get(
        "status",
        "unknown"
    )

    # -----------------------------------------------------
    # 比较失败
    # -----------------------------------------------------

    if status != "success":

        print(
            f"❌ 比较失败："
            f"{result.get('message', '未知错误')}"
        )

        return

    # -----------------------------------------------------
    # 比较条件
    # -----------------------------------------------------

    compare = result.get(
        "compare",
        {}
    )

    print(
        f"👤 客户："
        f"{result.get('customer', '')}"
    )

    print(
        f"🔍 比较条件："
        f"{compare.get('left', '')} "
        f"{compare.get('operator', '')} "
        f"{compare.get('right', '')}"
    )

    # -----------------------------------------------------
    # 统计信息
    # -----------------------------------------------------

    total_count = result.get(
        "total_count",
        0
    )

    comparable_count = result.get(
        "comparable_count",
        0
    )

    matched_count = result.get(
        "matched_count",
        0
    )

    print(
        f"📊 总记录数："
        f"{total_count} 条"
    )

    print(
        f"✅ 有效比较："
        f"{comparable_count} 条"
    )

    print(
        f"🎯 匹配记录："
        f"{matched_count} 条"
    )

    # -----------------------------------------------------
    # 无法比较的数据
    # -----------------------------------------------------

    invalid_count = (
        total_count
        - comparable_count
    )

    if invalid_count > 0:

        print(
            f"⚠️ 未参与比较："
            f"{invalid_count} 条（存在空值）"
        )

    # -----------------------------------------------------
    # 查询结果
    # -----------------------------------------------------

    data = result.get(
        "data",
        {}
    )

    rows = data.get(
        "rows",
        []
    )

    if not rows:

        print(
            "\n📋 没有满足条件的数据"
        )

        return

    print(
        f"\n📋 匹配数据（前 {len(rows)} 条）："
    )

    for i, row in enumerate(
        rows,
        start=1
    ):

        print(
            f"\n--- 第 {i} 条 ---"
        )

        # ---------------------------------------------
        # 比较字段
        # ---------------------------------------------

        left = compare.get(
            "left"
        )

        right = compare.get(
            "right"
        )

        if left and left in row:

            print(
                f"{left}："
                f"{row[left]}"
            )

        if right and right in row:

            print(
                f"{right}："
                f"{row[right]}"
            )

        # ---------------------------------------------
        # 客商名称
        # ---------------------------------------------

        if "客商名称" in row:

            print(
                f"客商名称："
                f"{row['客商名称']}"
            )

        # ---------------------------------------------
        # 年份
        # ---------------------------------------------

        if "摘要" in row:

            print(
                f"年份："
                f"{row['摘要']}"
            )

        # ---------------------------------------------
        # 业务种类
        # ---------------------------------------------

        if "业务种类" in row:

            value = row["业务种类"]

            if str(value) != "nan":

                print(
                    f"业务种类："
                    f"{value}"
                )


# =========================================================
# 统一结果输出
# =========================================================

def print_result(result):
    if not result:
        print("\n❌ Agent没有返回结果")
        return

    query_result = result.get("query_result")
    if not query_result:
        print("\n❌ 没有查询结果")
        return

    result_type = query_result.get("type")

    if result_type == "query_value":
        print_query_value_result(query_result)
    elif result_type == "compare_rows":
        print_compare_rows_result(query_result)
    elif result_type == "rank_rows":
        print_rank_rows_result(query_result)
    else:
        print("\n========== 查询结果 ==========")
        print(query_result)

def print_rank_rows_result(result):
    """输出排名结果"""
    print("\n========== 排名结果 ==========")
    status = result.get("status", "unknown")
    if status != "success":
        print(f"❌ 排名失败：{result.get('message', '未知错误')}")
        return

    metric = result.get("metric", "未知指标")
    order = result.get("order", "desc")
    total = result.get("total_count", 0)
    limit = result.get("limit", 0)
    print(f"📊 按 {metric} 排名（{'降序' if order == 'desc' else '升序'}），共 {total} 条记录，显示前 {limit} 条")

    rows = result.get("data", {}).get("rows", [])
    if not rows:
        print("📋 没有匹配的数据")
        return

    print("\n排名 | 客户名称 | 指标值 | 来源Sheet")
    print("-----|----------|--------|----------")
    for row in rows:
        rank = row.get("排名", "")
        # 尝试提取客户名称
        customer_name = ""
        for key in ["客商名称", "客户名称", "客商", "客户"]:
            if key in row:
                customer_name = row[key]
                break
        if not customer_name:
            # 如果没找到，取第一个字符串类型的值（跳过排名、来源Sheet、指标等）
            for key, value in row.items():
                if isinstance(value, str) and key not in ["来源Sheet", "排名", metric]:
                    customer_name = value
                    break
        metric_value = row.get(metric, "")
        sheet = row.get("来源Sheet", "")
        # 截断显示，避免过长
        print(f"{rank:^3} | {str(customer_name)[:20]:<20} | {metric_value:>12} | {sheet}")
# =========================================================
# Excel文件选择
# =========================================================

def choose_data_file():

    """
    让用户在运行时选择 Excel 文件。

    直接回车：
        使用 config.py 中的默认文件。

    输入文件路径：
        使用用户指定的文件。
    """

    default_path = DATA_PATH

    print(
        "\n========== 数据文件 =========="
    )

    print(
        f"默认文件：{default_path}"
    )

    file_path = input(
        "请输入Excel文件路径（直接回车使用默认文件）："
    ).strip()

    # -----------------------------------------------------
    # 使用默认文件
    # -----------------------------------------------------

    if not file_path:

        file_path = default_path

    # -----------------------------------------------------
    # 规范化路径
    # -----------------------------------------------------

    file_path = os.path.normpath(
        file_path
    )

    # -----------------------------------------------------
    # 文件存在性检查
    # -----------------------------------------------------

    if not os.path.exists(
        file_path
    ):

        print(
            f"\n❌ 文件不存在："
            f"{file_path}"
        )

        return None

    # -----------------------------------------------------
    # Excel格式检查
    # -----------------------------------------------------

    if not file_path.lower().endswith(
        (
            ".xlsx",
            ".xls"
        )
    ):

        print(
            "\n❌ 目前只支持 Excel 文件："
            ".xlsx / .xls"
        )

        return None

    print(
        f"\n✅ 使用数据文件："
        f"{file_path}"
    )

    return file_path


# =========================================================
# 主程序
# =========================================================

def main():

    print(
        "\n=========================================="
    )

    print(
        "        🤖 AI Data Agent"
    )

    print(
        "=========================================="
    )

    # -----------------------------------------------------
    # 创建 Agent
    # -----------------------------------------------------

    agent = DataAgent()

    # -----------------------------------------------------
    # 选择 Excel
    # -----------------------------------------------------

    data_path = choose_data_file()

    if not data_path:

        print(
            "\n程序结束。"
        )

        return

    # -----------------------------------------------------
    # 用户需求
    # -----------------------------------------------------

    query = input(
        "\n请输入你的分析需求："
    ).strip()

    # -----------------------------------------------------
    # 空需求检查
    # -----------------------------------------------------

    if not query:

        print(
            "\n❌ 分析需求不能为空。"
        )

        return

    print(
        "\n📝 用户需求："
    )

    print(
        query
    )

    # -----------------------------------------------------
    # Agent执行
    # -----------------------------------------------------

    print(
        "\n=========================================="
    )

    print(
        "🤖 Agent开始执行..."
    )

    print(
        "=========================================="
    )

    result = agent.run(
        data_path,
        user_query=query,
        with_ai=True
    )

    # -----------------------------------------------------
    # 输出结果
    # -----------------------------------------------------

    print(
        "\n=========================================="
    )

    print(
        "📊 数据分析结果"
    )

    print(
        "=========================================="
    )

    print_result(
        result
    )

    # -----------------------------------------------------
    # AI业务建议
    # -----------------------------------------------------

    print(
        "\n=========================================="
    )

    print(
        "🤖 AI业务建议"
    )

    print(
        "=========================================="
    )

    print(
        result.get(
            "ai_insight",
            "当前未生成AI建议"
        )
    )


# =========================================================
# 程序入口
# =========================================================

if __name__ == "__main__":

    main()