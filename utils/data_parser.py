"""
Excel字段自动识别模块
支持：
1. 中英文字段
2. 模糊匹配
3. 字段评分
"""

import pandas as pd


# =========================
# 字段关键词
# =========================

SALES_KEYWORDS = {
    "销售额": 10,
    "销售金额": 10,
    "销售收入": 10,
    "成交金额": 9,
    "支付金额": 9,
    "订单金额": 8,
    "金额": 5,
    "收入": 8,
    "营收": 8,
    "revenue": 10,
    "sales": 10,
    "amount": 6,
    "price": 5
}


PRODUCT_KEYWORDS = {
    "产品名称":10,
    "商品名称":10,
    "产品":8,
    "商品":8,
    "品类":7,
    "类别":6,
    "product":10,
    "item":8,
    "category":7
}


DATE_KEYWORDS = {
    "日期":10,
    "时间":8,
    "交易日期":10,
    "订单日期":10,
    "date":10,
    "time":8
}


def score_column(column, keywords):
    """
    计算字段匹配分数
    """

    column = str(column).lower().strip()

    score = 0

    for key, weight in keywords.items():

        if key.lower() in column:
            score += weight

    return score



def find_best_column(df, keywords):
    """
    找最高评分字段
    """

    best_column = None
    best_score = 0


    for col in df.columns:

        score = score_column(
            col,
            keywords
        )


        if score > best_score:

            best_score = score
            best_column = col


    return best_column



def find_sales_column(df):

    col = find_best_column(
        df,
        SALES_KEYWORDS
    )


    if col:
        return col


    # 数值兜底

    numeric_cols = df.select_dtypes(
        include=["number"]
    ).columns


    if len(numeric_cols)>0:
        return numeric_cols[0]


    return None




def find_product_column(df):

    col = find_best_column(
        df,
        PRODUCT_KEYWORDS
    )


    if col:
        return col


    # 文本兜底

    text_cols = df.select_dtypes(
        include=["object"]
    ).columns


    return text_cols[0] if len(text_cols)>0 else None





def find_date_column(df):

    col = find_best_column(
        df,
        DATE_KEYWORDS
    )


    if col:
        return col


    # ==================================================
    # 自动日期检测（修复）
    #
    # 此前用 try: pd.to_datetime(df[col]) except: pass 来判断
    # 一列是不是日期，但纯数字列（订单编号、金额、Excel序列号）
    # 也常常能被 pd.to_datetime 成功解析（当成Unix时间戳/序列号
    # 处理），导致把ID列或金额列误判成日期列。后续画趋势图会
    # 全部基于错误的列，运行不报错，但结果是错的。
    #
    # 现在只在以下两种更可靠的情况下才自动判定为日期列：
    # 1. 该列本身的 dtype 已经是 datetime 类型
    # 2. 该列是字符串/object类型，且转换成功率高（缺失值除外），
    #    同时不是纯数字字符串（纯数字更可能是ID或金额，
    #    而不是日期文本）
    # 不再对数值型（int/float）列做兜底日期猜测。
    # ==================================================

    for col in df.columns:

        series = df[col]

        # 情况1：已经是datetime类型，直接认定
        if pd.api.types.is_datetime64_any_dtype(series):
            return col

        # 跳过纯数值类型列，避免把金额/编号误判为日期
        if pd.api.types.is_numeric_dtype(series):
            continue

        # 情况2：文本类型，尝试转换，且要求足够高的成功率
        non_null = series.dropna()
        if len(non_null) == 0:
            continue

        # 纯数字字符串（如"20230101"这种可能是日期，
        # 但"1001"这种更像编号）交给关键词匹配去判断，
        # 这里不再兜底猜测，避免误判ID列
        if non_null.astype(str).str.fullmatch(r"\d+").mean() > 0.5:
            continue

        try:
            parsed = pd.to_datetime(non_null, errors="coerce")
        except Exception:
            continue

        success_rate = parsed.notna().mean()

        if success_rate >= 0.9:
            return col

    return None




def detect_columns(df):

    return {

        "sales_column":
            find_sales_column(df),

        "product_column":
            find_product_column(df),

        "date_column":
            find_date_column(df)

    }