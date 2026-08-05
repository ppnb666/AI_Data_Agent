import matplotlib.pyplot as plt

# ===== 解决中文显示问题 =====
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
# ===========================


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

    # 设置标题（现在可以用中文了）
    plt.title("各产品销售额汇总")

    # 设置坐标轴（现在可以用中文了）
    plt.xlabel(product_column)
    plt.ylabel(sales_column)

    # 自动调整布局
    plt.tight_layout()

    # 保存图片
    plt.savefig(save_path, dpi=300)

    # 关闭图片
    plt.close()