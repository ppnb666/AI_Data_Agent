# ==============================
# 先加载工具注册
# 必须放最前面
# ==============================

import os
import tools

from agent import DataAgent
from config import DATA_PATH


def print_query_value_result(result):
    print("\n========== 查询结果 ==========")

    status = result.get("status", "unknown")

    if status != "success":
        print(
            f"❌ 查询失败："
            f"{result.get('message', '未知错误')}"
        )
        return

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

    filters = result.get("filters", {})

    if filters:

        print("\n🔎 过滤条件：")

        for key, value in filters.items():
            print(f"  {key}：{value}")

    summary = result.get("summary", {})

    if summary:

        print("\n💰 金额汇总：")

        for key, value in summary.items():
            print(f"  {key}：{value}")

    rows = result.get(
        "data",
        {}
    ).get(
        "rows",
        []
    )

    if not rows:

        print("\n📋 没有匹配数据")
        return

    print(
        f"\n📋 匹配数据（前 {len(rows)} 条）："
    )

    for i, row in enumerate(
        rows,
        start=1
    ):

        print(f"\n--- 第 {i} 条 ---")

        for key, value in row.items():
            print(f"{key}：{value}")


def print_compare_rows_result(result):
    print(
        "\n========== 比较结果 =========="
    )

    status = result.get("status", "unknown")

    if status != "success":

        print(
            f"❌ 比较失败："
            f"{result.get('message', '未知错误')}"
        )

        return

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

    invalid_count = (
        total_count
        - comparable_count
    )

    if invalid_count > 0:

        print(
            f"⚠️ 未参与比较："
            f"{invalid_count} 条（存在空值）"
        )

    rows = result.get(
        "data",
        {}
    ).get(
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

        left = compare.get(
            "left"
        )

        right = compare.get(
            "right"
        )

        if left in row:
            print(
                f"{left}："
                f"{row[left]}"
            )

        if right in row:
            print(
                f"{right}："
                f"{row[right]}"
            )

        if "客商名称" in row:
            print(
                f"客商名称："
                f"{row['客商名称']}"
            )

        if "摘要" in row:
            print(
                f"年份："
                f"{row['摘要']}"
            )

        if "业务种类" in row:

            value = row["业务种类"]

            if str(value) != "nan":

                print(
                    f"业务种类："
                    f"{value}"
                )


def print_result(result):
    query_result = result.get(
        "query_result"
    )

    if not query_result:

        print(
            "没有查询结果"
        )

        return

    result_type = query_result.get(
        "type"
    )

    if result_type == "query_value":

        print_query_value_result(
            query_result
        )

    elif result_type == "compare_rows":

        print_compare_rows_result(
            query_result
        )

    else:

        print(
            "\n========== 查询结果 =========="
        )

        print(query_result)


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

    if not file_path:

        file_path = default_path

    # 支持用户输入相对路径
    file_path = os.path.normpath(
        file_path
    )

    if not os.path.exists(
        file_path
    ):

        print(
            f"\n❌ 文件不存在："
            f"{file_path}"
        )

        return None

    # 检查扩展名
    if not file_path.lower().endswith(
        (".xlsx", ".xls")
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


def main():

    agent = DataAgent()

    # ==========================================
    # 选择 Excel
    # ==========================================

    data_path = choose_data_file()

    if not data_path:

        return

    # ==========================================
    # 用户需求
    # ==========================================

    query = input(
        "\n请输入你的分析需求："
    )

    # ==========================================
    # Agent执行
    # ==========================================

    result = agent.run(
        data_path,
        user_query=query,
        with_ai=False
    )

    # ==========================================
    # 输出
    # ==========================================

    print(
        "\n======================"
    )

    print(
        "📊 数据分析结果"
    )

    print_result(
        result
    )

    print(
        "\n🤖 AI业务建议:"
    )

    print(
        result.get(
            "ai_insight",
            "没有生成AI建议"
        )

    )


if __name__ == "__main__":

    main()