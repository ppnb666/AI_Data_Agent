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


    # 自动日期检测

    for col in df.columns:

        try:

            pd.to_datetime(df[col])

            return col

        except:

            pass


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