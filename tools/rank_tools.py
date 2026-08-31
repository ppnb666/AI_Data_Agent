"""
排名工具：按客户分组汇总指定指标，并排序
"""

import pandas as pd

from tools.field_resolver import find_customer_field


def rank_rows_tool(state, task=None):
    """
    按客户分组汇总指定的指标字段，并排序返回前N条记录。

    修复说明：
    此前该函数不接收当前任务，而是自己回头去 state.plan 里按
    tool == "rank_rows" 搜索第一个匹配项。如果一次 plan 里有
    多个 rank_rows 任务（例如"分别按销售额和按数量排名"），
    永远只会执行第一个，其余的会被静默忽略。

    现在优先读取 state.current_task —— Executor在每次调用工具前
    会把"当前正在执行的task"写入state.current_task（见agent.py
    execute_plan），这样能保证多任务场景下每次调用处理的都是
    正确的那一条任务，而不是永远命中第一条同类型任务。

    仍支持显式传入task参数（更直接、不依赖state），以及旧的
    state.plan搜索方式作为最后的兼容兜底。
    """
    if task is None:
        task = getattr(state, "current_task", None)
        if task is not None and task.get("tool") != "rank_rows":
            task = None

    if task is None:
        import warnings
        warnings.warn(
            "rank_rows_tool 未收到state.current_task，回退到旧的"
            "state.plan搜索方式，若一次计划中有多个rank_rows"
            "任务，只会执行第一个。"
        )
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

        # 找客户字段（修复：改用统一的field_resolver，优先读取
        # state.mapping中用户手动确认过的映射，而不是只看schema猜测）
        customer_field = find_customer_field(state, schema, columns)
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