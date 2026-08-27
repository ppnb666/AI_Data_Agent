"""
排名工具：按客户分组汇总指定指标，并排序
"""

import pandas as pd


def find_customer_field(schema, columns):
    """根据Schema寻找客户字段，与 query_tools 中的一致"""
    customer_fields = []
    entities = schema.get("entities", {})
    customer_fields = [field.split(".")[-1] for field in entities.get("customer", [])]
    for field in customer_fields:
        if field in columns:
            return field
    # 兜底关键词
    keywords = ["客商名称", "客户名称", "客户", "客商"]
    for col in columns:
        if any(k in str(col) for k in keywords):
            return col
    return None


def rank_rows_tool(state):
    """
    按客户分组汇总指定的指标字段，并排序返回前N条记录。
    """
    # 获取当前任务
    task = None
    for t in getattr(state, "plan", []):
        if t.get("tool") == "rank_rows":
            task = t
            break
    if not task:
        return {"type": "rank_rows", "status": "failed", "message": "未找到rank_rows任务"}

    # 提取参数
    metrics = task.get("metrics", [])
    if not metrics:
        return {"type": "rank_rows", "status": "failed", "message": "未指定要排名的指标字段"}
    metric = metrics[0]  # 只取第一个指标

    condition = task.get("condition", {})
    order = condition.get("order", "desc")
    limit = condition.get("limit", 10)
    filters = task.get("filters", {})
    customer = task.get("customer", "")

    schema = getattr(state, "workbook_schema", {})
    sheets = getattr(state, "sheet_profiles", [])

    all_results = []  # 存储所有Sheet的客户汇总数据

    for sheet in sheets:
        df = sheet["df"].copy()
        sheet_name = sheet["sheet"]
        columns = list(df.columns)

        # 找客户字段
        customer_field = find_customer_field(schema, columns)
        if not customer_field:
            continue

        # 如果 metric 不在当前sheet的列中，跳过
        if metric not in columns:
            continue

        # 将指标列转换为数值，非数值转为NaN
        df[metric] = pd.to_numeric(df[metric], errors='coerce')
        # 删除指标为NaN的行（无法参与汇总）
        df = df[df[metric].notna()]

        if len(df) == 0:
            continue

        # 应用过滤条件（简化：只做包含匹配）
        if filters:
            for key, value in filters.items():
                matched_col = None
                for col in columns:
                    if key in str(col):
                        matched_col = col
                        break
                if matched_col:
                    df = df[df[matched_col].astype(str).str.contains(str(value), na=False, regex=False)]

        # 如果指定了客户，过滤
        if customer:
            df = df[df[customer_field].astype(str).str.contains(customer, na=False, regex=False)]

        if len(df) == 0:
            continue

        # 按客户字段分组，对指标求和
        grouped = df.groupby(customer_field, as_index=False)[metric].sum()
        # 添加Sheet来源
        grouped["来源Sheet"] = sheet_name
        all_results.extend(grouped.to_dict(orient="records"))

    if not all_results:
        return {
            "type": "rank_rows",
            "status": "success",
            "message": "没有匹配的数据",
            "data": {"rows": []},
            "total_count": 0
        }

    # 排序（此时所有值都是数值）
    reverse = (order == "desc")
    all_results.sort(key=lambda x: x.get(metric, 0), reverse=reverse)

    # 取前N条
    top_results = all_results[:limit]

    # 添加排名序号
    for i, row in enumerate(top_results, 1):
        row["排名"] = i

    return {
        "type": "rank_rows",
        "status": "success",
        "message": f"排名完成，共 {len(all_results)} 条记录，返回前 {len(top_results)} 条",
        "metric": metric,
        "order": order,
        "limit": limit,
        "total_count": len(all_results),
        "data": {"rows": top_results}
    }