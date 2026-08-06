
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd

# ===== 解决中文显示问题 =====
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
# ===========================
# 使用标准字体，避免警告
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

def plot_product_sales(df, product_column, sales_column, save_path):
    """
    绘制产品销售额柱状图

    参数：
    df: 数据
    product_column: 产品字段名
    sales_column: 销售额字段名
    save_path: 图片保存路径
    """

    # 按产品统计销售额
    product_sales = (
        df.groupby(product_column)[sales_column]
        .sum()
        .sort_values(ascending=False)
    )

    # 创建图像
    plt.figure(figsize=(8, 5))

    # 绘制柱状图
    product_sales.plot(kind="bar")

    # 设置标题
    plt.title("各产品销售额汇总")

    # 设置坐标轴
    plt.xlabel(product_column)
    plt.ylabel(sales_column)

    # 自动调整布局
    plt.tight_layout()

    # 保存图片
    plt.savefig(save_path, dpi=300)

    # 关闭图片
    plt.close()


def plot_sales_trend(df, date_column, sales_column, save_path):
    """
    绘制销售趋势折线图

    参数：
    df: 数据
    date_column: 日期字段名
    sales_column: 销售额字段名
    save_path: 图片保存路径
    """
    # 确保日期列是日期类型
    df_copy = df.copy()
    df_copy[date_column] = pd.to_datetime(df_copy[date_column])

    # 按日期分组，计算每天的总销售额
    daily_sales = (
        df_copy.groupby(date_column)[sales_column]
        .sum()
        .sort_index()
    )

    # 创建图像
    plt.figure(figsize=(12, 6))

    # 绘制折线图
    plt.plot(
        daily_sales.index,
        daily_sales.values,
        marker='o',
        linestyle='-',
        linewidth=2,
        markersize=6,
        color='#2E86AB',
        markerfacecolor='#A23B72'
    )

    # 填充区域（美化）
    plt.fill_between(
        daily_sales.index,
        daily_sales.values,
        alpha=0.3,
        color='#2E86AB'
    )

    # 设置标题和标签
    plt.title("销售趋势图", fontsize=16, fontweight='bold')
    plt.xlabel(date_column, fontsize=12)
    plt.ylabel(sales_column, fontsize=12)

    # 旋转日期标签，避免重叠
    plt.xticks(rotation=45, ha='right')

    # 添加网格线
    plt.grid(True, alpha=0.3, linestyle='--')

    # 自动调整布局
    plt.tight_layout()

    # 保存图片
    plt.savefig(save_path, dpi=300, bbox_inches='tight')

    # 关闭图片
    plt.close()