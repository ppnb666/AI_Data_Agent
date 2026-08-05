# utils/data_parser.py
# 自动检测 Excel 中的列名
import pandas as pd
def find_sales_column(df):
    """
    自动查找销售额列
    根据常见列名进行匹配，返回匹配到的列名
    """
    candidates = [
        "销售额", "销售金额", "销售收入", "实际销售额", "总销售额",
        "金额", "收入", "营收", "成交额", "订单金额", "结算金额",
        "total_sales", "sales_amount", "revenue", "turnover",
        "price", "sales", "amount", "total", "sum"
    ]

    for col in df.columns:
        col_lower = col.lower().strip()
        for keyword in candidates:
            if keyword.lower() in col_lower:
                return col

    # 如果没找到，找第一个数值类型的列
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        return numeric_cols[0]

    return None


def find_product_column(df):
    """
    自动查找产品列
    根据常见列名进行匹配，返回匹配到的列名
    """
    candidates = [
        "产品", "商品", "产品名称", "商品名称", "产品名", "品名",
        "项目", "服务", "分类", "类别", "品类", "类目",
        "产品编号", "商品编号", "SKU", "产品编码",
        "product", "product_name", "name", "item", "category", "type"
    ]

    for col in df.columns:
        col_lower = col.lower().strip()
        for keyword in candidates:
            if keyword.lower() in col_lower:
                return col

    # 如果没找到，找第一个文本类型的列（排除日期列）
    string_cols = df.select_dtypes(include=['object']).columns.tolist()
    # 排除日期格式的列
    for col in string_cols[:]:
        try:
            pd.to_datetime(df[col])
            string_cols.remove(col)
        except:
            pass

    if string_cols:
        return string_cols[0]

    return None


def find_date_column(df):
    """
    自动查找日期列
    """
    candidates = [
        "日期", "时间", "下单时间", "支付时间", "创建时间", "更新时间",
        "订单日期", "交易日期", "完成时间", "开始时间", "结束时间",
        "date", "time", "created_at", "updated_at", "order_date", "transaction_date"
    ]

    for col in df.columns:
        col_lower = col.lower().strip()
        for keyword in candidates:
            if keyword.lower() in col_lower:
                return col

    # 尝试自动检测日期类型列
    for col in df.columns:
        try:
            pd.to_datetime(df[col])
            return col
        except:
            pass

    return None


def detect_columns(df):
    """
    自动检测所有关键列
    返回：{
        'sales_column': 销售额列名,
        'product_column': 产品列名,
        'date_column': 日期列名
    }
    """
    result = {
        'sales_column': find_sales_column(df),
        'product_column': find_product_column(df),
        'date_column': find_date_column(df)
    }
    return result