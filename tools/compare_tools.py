import re
import pandas as pd


def clean_field(field):
    """
    去除 Schema 字段前缀

    Sheet1.客商名称 -> 客商名称
    """

    if "." in field:
        return field.split(".")[-1]

    return field


def get_compare_task(state):
    for task in state.plan:

        if task.get("tool") == "compare_rows":
            return task

    return None


def find_customer_field(schema, columns):
    """
    根据 Schema 自动寻找当前 Sheet 的客户字段
    """

    customer_fields = [
        clean_field(x)
        for x in
        schema.get("entities", {})
        .get("customer", [])
    ]

    for field in customer_fields:

        if field in columns:
            return field

    return None


# ==========================================================
# 数字 / 金额解析
# ==========================================================

def parse_numeric_value(value):
    """
    将常见中文金额转换成数字。

    支持：

    100
    100.5
    1,000
    100万
    100万元
    1.5亿
    1.5亿元
    -100万

    返回：
        float

    解析失败：
        raise ValueError
    """

    # ------------------------------------------
    # 如果本身就是数字
    # ------------------------------------------

    if isinstance(value, (int, float)):

        if pd.isna(value):
            raise ValueError(
                f"无法解析空值: {value}"
            )

        return float(value)

    # ------------------------------------------
    # 字符串清洗
    # ------------------------------------------

    text = str(value).strip()

    if not text:

        raise ValueError(
            "数值不能为空"
        )

    # 去掉千分位
    text = text.replace(",", "")

    # 去掉空格
    text = text.replace(" ", "")

    # 去掉常见货币单位
    text = text.replace("人民币", "")
    text = text.replace("元", "")

    # ------------------------------------------
    # 亿
    # ------------------------------------------

    if text.endswith("亿"):

        number_text = text[:-1]

        try:

            number = float(number_text)

        except ValueError:

            raise ValueError(
                f"无法解析金额: {value}"
            )

        return number * 100_000_000

    # ------------------------------------------
    # 万
    # ------------------------------------------

    if text.endswith("万"):

        number_text = text[:-1]

        try:

            number = float(number_text)

        except ValueError:

            raise ValueError(
                f"无法解析金额: {value}"
            )

        return number * 10_000

    # ------------------------------------------
    # 普通数字
    # ------------------------------------------

    try:

        return float(text)

    except ValueError:

        raise ValueError(
            f"无法解析数值: {value}"
        )


def is_numeric_constant(value):
    """
    判断 Planner 给出的 right 是否是常量。

    True:
        100
        100万
        1.5亿

    False:
        贷方累计
        期末余额
    """

    if isinstance(value, (int, float)):

        return True

    if value is None:

        return False

    text = str(value).strip()

    if not text:

        return False

    text = text.replace(",", "")
    text = text.replace(" ", "")
    text = text.replace("人民币", "")
    text = text.replace("元", "")

    # 普通数字
    if re.fullmatch(
        r"[-+]?\d+(?:\.\d+)?",
        text
    ):
        return True

    # 万
    if re.fullmatch(
        r"[-+]?\d+(?:\.\d+)?万",
        text
    ):
        return True

    # 亿
    if re.fullmatch(
        r"[-+]?\d+(?:\.\d+)?亿",
        text
    ):
        return True

    return False


# ==========================================================
# 构造比较数据
# ==========================================================

def build_compare_data(df, left, right):
    """
    构造左右两侧用于比较的数据。

    left:
        必须是 DataFrame 字段

    right:
        可以是：
        1. DataFrame 字段
        2. 数字常量

    返回：

        left_data
        right_data
        comparable_count
    """

    # ------------------------------------------
    # 左侧必须是字段
    # ------------------------------------------

    if left not in df.columns:

        raise ValueError(
            f"左侧字段不存在: {left}"
        )

    left_data = pd.to_numeric(
        df[left],
        errors="coerce"
    )

    # ------------------------------------------
    # 右侧如果是字段
    # ------------------------------------------

    if right in df.columns:

        right_data = pd.to_numeric(
            df[right],
            errors="coerce"
        )

    # ------------------------------------------
    # 右侧如果是数字常量
    # ------------------------------------------

    elif is_numeric_constant(right):

        right_value = parse_numeric_value(
            right
        )

        right_data = pd.Series(
            right_value,
            index=df.index,
            dtype="float64"
        )

    # ------------------------------------------
    # 右侧既不是字段也不是数字
    # ------------------------------------------

    else:

        raise ValueError(
            f"右侧比较对象既不是字段，也不是有效数字: {right}"
        )

    # ------------------------------------------
    # 缺失值不参与比较
    # ------------------------------------------

    valid_mask = (
        left_data.notna()
        &
        right_data.notna()
    )

    comparable_count = int(
        valid_mask.sum()
    )

    left_data = left_data[valid_mask]
    right_data = right_data[valid_mask]

    return (
        left_data,
        right_data,
        valid_mask,
        comparable_count
    )


# ==========================================================
# 执行比较运算
# ==========================================================

def apply_operator(
    df,
    left,
    right,
    operator
):
    """
    对字段与字段 / 字段与常量进行比较。

    支持：

        ==
        !=
        >
        <
        >=
        <=

    返回：

        result_df
        comparable_count
    """

    (
        left_data,
        right_data,
        valid_mask,
        comparable_count
    ) = build_compare_data(
        df,
        left,
        right
    )

    # ------------------------------------------
    # 比较
    # ------------------------------------------

    if operator == "==":

        mask = (
            left_data == right_data
        )

    elif operator == "!=":

        mask = (
            left_data != right_data
        )

    elif operator == ">":

        mask = (
            left_data > right_data
        )

    elif operator == "<":

        mask = (
            left_data < right_data
        )

    elif operator == ">=":

        mask = (
            left_data >= right_data
        )

    elif operator == "<=":

        mask = (
            left_data <= right_data
        )

    else:

        raise ValueError(
            f"不支持的比较运算符: {operator}"
        )

    # ------------------------------------------
    # 恢复原始 DataFrame 行
    # ------------------------------------------

    valid_df = df.loc[
        valid_mask
    ].copy()

    result_df = valid_df.loc[
        mask
    ].copy()

    return (
        result_df,
        comparable_count
    )


# ==========================================================
# 主 Tool
# ==========================================================

def compare_rows_tool(state):
    """
    通用字段比较工具

    Planner 提供：

        customer

        filters

        compare:
            left
            right
            operator

    支持：

        字段 vs 字段

        字段 vs 数字

    例如：

        本期贷方 == 贷方累计

        期末余额 > 100万

        期末余额 >= 1.5亿

    返回：

        total_count
            客户及业务条件过滤后的记录数

        comparable_count
            真正具备有效比较数据的记录数

        matched_count
            满足比较条件的记录数

        data.rows
            匹配记录
    """

    task = get_compare_task(
        state
    )

    # ==================================================
    # Planner任务不存在
    # ==================================================

    if not task:

        return {
            "type": "compare_rows",
            "status": "failed",
            "message": "没有找到compare_rows任务",
            "total_count": 0,
            "comparable_count": 0,
            "matched_count": 0,
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 获取Planner参数
    # ==================================================

    customer = task.get(
        "customer",
        ""
    )

    filters = task.get(
        "filters",
        {}
    )

    compare = task.get(
        "compare",
        {}
    )

    left = compare.get(
        "left"
    )

    right = compare.get(
        "right"
    )

    operator = compare.get(
        "operator",
        "!="
    )

    # ==================================================
    # 基础参数校验
    # ==================================================

    if not left:

        return {
            "type": "compare_rows",
            "status": "failed",
            "message": "缺少左侧比较字段",
            "total_count": 0,
            "comparable_count": 0,
            "matched_count": 0,
            "data": {
                "rows": []
            }
        }

    if right is None or str(right).strip() == "":

        return {
            "type": "compare_rows",
            "status": "failed",
            "message": "缺少右侧比较对象",
            "total_count": 0,
            "comparable_count": 0,
            "matched_count": 0,
            "data": {
                "rows": []
            }
        }

    if operator not in {
        "==",
        "!=",
        ">",
        "<",
        ">=",
        "<="
    }:

        return {
            "type": "compare_rows",
            "status": "failed",
            "message": (
                f"不支持的比较运算符: {operator}"
            ),
            "total_count": 0,
            "comparable_count": 0,
            "matched_count": 0,
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # Schema
    # ==================================================

    schema = getattr(
        state,
        "workbook_schema",
        {}
    )

    result_df = None

    total_count = 0

    comparable_count = 0

    found_sheet = False

    # ==================================================
    # 遍历Sheet
    # ==================================================

    for sheet in state.sheet_profiles:

        df = sheet["df"].copy()

        columns = list(
            df.columns
        )

        # ----------------------------------------------
        # 找客户字段
        # ----------------------------------------------

        customer_field = find_customer_field(
            schema,
            columns
        )

        if not customer_field:
            continue

        # ----------------------------------------------
        # 左侧字段必须存在
        # ----------------------------------------------

        if left not in columns:
            continue

        # ----------------------------------------------
        # 右侧如果不是字段，则必须是数字常量
        # ----------------------------------------------

        right_is_field = (
            right in columns
        )

        if not right_is_field:

            if not is_numeric_constant(
                right
            ):
                continue

        found_sheet = True

        print(
            "compare使用Sheet:",
            sheet["sheet"]
        )

        # ==================================================
        # 客户过滤
        # ==================================================

        if customer:

            df = df[
                df[customer_field]
                .astype(str)
                .str.contains(
                    customer,
                    na=False,
                    regex=False
                )
            ]

        # ==================================================
        # filters
        # ==================================================

        for key, value in filters.items():

            target = None

            # ------------------------------------------
            # 精确匹配
            # ------------------------------------------

            if key in df.columns:

                target = key

            # ------------------------------------------
            # 模糊匹配
            # ------------------------------------------

            else:

                for col in df.columns:

                    if key in col:

                        target = col
                        break

            if target:

                df = df[
                    df[target]
                    .astype(str)
                    .str.contains(
                        str(value),
                        regex=False,
                        na=False
                    )
                ]

        print(
            "过滤后数量:",
            len(df)
        )

        # ==================================================
        # 没有数据
        # ==================================================

        if len(df) == 0:

            continue

        total_count = len(df)

        # ==================================================
        # 执行比较
        # ==================================================

        try:

            (
                result_df,
                comparable_count
            ) = apply_operator(
                df,
                left,
                right,
                operator
            )

        except ValueError as e:

            return {
                "type": "compare_rows",
                "status": "failed",
                "message": str(e),
                "customer": customer,
                "filters": filters,
                "compare": {
                    "left": left,
                    "right": right,
                    "operator": operator
                },
                "total_count": total_count,
                "comparable_count": 0,
                "matched_count": 0,
                "data": {
                    "rows": []
                }
            }

        # 找到第一个适合的Sheet后停止
        break

    # ==================================================
    # 没有找到合适Sheet
    # ==================================================

    if not found_sheet:

        return {
            "type": "compare_rows",
            "status": "failed",
            "message": (
                f"没有找到可以执行比较的Sheet："
                f"{left} {operator} {right}"
            ),
            "customer": customer,
            "filters": filters,
            "compare": {
                "left": left,
                "right": right,
                "operator": operator
            },
            "total_count": 0,
            "comparable_count": 0,
            "matched_count": 0,
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 找到了Sheet，但是没有匹配数据
    # ==================================================

    if result_df is None:

        return {
            "type": "compare_rows",
            "status": "success",
            "message": "没有匹配的数据",
            "customer": customer,
            "filters": filters,
            "compare": {
                "left": left,
                "right": right,
                "operator": operator
            },
            "total_count": 0,
            "comparable_count": 0,
            "matched_count": 0,
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 返回前100条
    # ==================================================

    rows = (
        result_df
        .head(100)
        .to_dict(
            orient="records"
        )
    )

    # ==================================================
    # 最终结果
    # ==================================================

    return {
        "type": "compare_rows",
        "status": "success",
        "message": "比较完成",

        "customer": customer,

        "filters": filters,

        "compare": {
            "left": left,
            "right": right,
            "operator": operator
        },

        "total_count": total_count,

        "comparable_count": comparable_count,

        "matched_count": len(
            result_df
        ),

        "data": {
            "rows": rows
        }
    }