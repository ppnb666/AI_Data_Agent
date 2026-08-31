"""
通用数值解析模块

将常见中文金额、英文金额缩写、百分比等转换成数字。

支持：
    100
    100.5
    1,000           千分位
    100万 / 100万元
    1.5亿 / 1.5亿元
    -100万
    $100 / ￥100 / ¥100
    RMB100 / CNY100 / USD100
    50%              → 0.5
    1K / 1M / 1B     → 千 / 百万 / 十亿
    (100)            → -100（会计括号负数）

解析失败：
    raise ValueError
"""

import re

import pandas as pd


def parse_numeric_value(value):
    """
    将常见中文金额转换成数字，解析失败抛 ValueError。
    """
    # ------------------------------------------------------
    # 如果本身就是数字
    # ------------------------------------------------------

    if isinstance(value, (int, float)):

        if pd.isna(value):

            raise ValueError(
                f"无法解析空值: {value}"
            )

        return float(value)

    # ------------------------------------------------------
    # 字符串清洗
    # ------------------------------------------------------

    text = str(value).strip()

    if not text:

        raise ValueError(
            "数值不能为空"
        )

    # 去掉千分位
    text = text.replace(",", "")

    # 去掉空格
    text = text.replace(" ", "")

    # ------------------------------------------------------
    # 括号负数：(100) → -100
    # ------------------------------------------------------

    if text.startswith("(") and text.endswith(")"):

        inner = text[1:-1]

        if not inner:

            raise ValueError(
                f"无法解析数值: {value}"
            )

        return parse_numeric_value("-" + inner)

    # ------------------------------------------------------
    # 剥离货币符号 / 货币单位（前后缀均可）
    # ------------------------------------------------------

    for currency in (
        "人民币",
        "元",
        "￥",
        "¥",
        "$",
        "RMB",
        "CNY",
        "USD",
        "EUR",
    ):

        text = text.replace(currency, "")

    if not text:

        raise ValueError(
            f"无法解析数值: {value}"
        )

    # ------------------------------------------------------
    # 百分比：50% → 0.5
    # ------------------------------------------------------

    if text.endswith("%"):

        number_text = text[:-1]

        try:

            number = float(number_text)

        except ValueError:

            raise ValueError(
                f"无法解析数值: {value}"
            )

        return number / 100.0

    # ------------------------------------------------------
    # 单位放大（中英文）
    # ------------------------------------------------------

    multipliers = [
        ("亿", 100_000_000),
        ("万", 10_000),
        ("B", 1_000_000_000),
        ("M", 1_000_000),
        ("K", 1_000),
    ]

    for suffix, multiplier in multipliers:

        if text.endswith(suffix):

            number_text = text[:-len(suffix)]

            try:

                number = float(number_text)

            except ValueError:

                raise ValueError(
                    f"无法解析金额: {value}"
                )

            return number * multiplier

    # ------------------------------------------------------
    # 普通数字
    # ------------------------------------------------------

    try:

        return float(text)

    except ValueError:

        raise ValueError(
            f"无法解析数值: {value}"
        )


def is_numeric_constant(value):
    """
    判断给定的比较右侧是否是数字常量。

    True:
        100
        100万
        1.5亿
        $100
        50%
        1K

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

    try:

        parse_numeric_value(text)

        return True

    except ValueError:

        return False


def extract_number(text):
    """
    从任意文本中提取第一个数字（含 万/亿/K/M/B/% 等后缀）。

    例如：
        "金额约100万" → 1000000.0
        "单价$50.5"  → 50.5

    找不到数字返回 None。
    """
    if text is None:

        return None

    if isinstance(text, (int, float)):

        return float(text)

    match = re.search(
        r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)\s*(?:万|亿|[KMB])?",
        str(text)
    )

    if not match:

        return None

    try:

        return parse_numeric_value(
            match.group(0)
        )

    except ValueError:

        return None
