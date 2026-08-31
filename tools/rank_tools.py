"""
排名工具：按分组字段汇总指定指标，并排序

通用化：
1. 分组字段不再强依赖"客户"——按 customer → business → product
   → department → project 优先级取 schema 角色字段，全部缺失时
   不分组、直接对全表按指标排序
2. metrics 为空时从 schema.roles 的 amount/number 角色自动补齐，
   不再要求 Planner 必须给出指标
"""

import pandas as pd

from tools.field_resolver import (
    find_customer_field,
    resolve_field,
    resolve_role_fields,
)
from tools.query_tools import match_field


# 分组字段优先级（customer 缺失时依次降级）
GROUP_ROLE_PRIORITY = [
    "customer",
    "business",
    "product",
    "department",
    "project",
]

METRIC_ROLE_PRIORITY = [
    "amount",
    "number",
]


def _pick_metric(state, schema, columns, metrics):
    """
    解析排名指标：
    1. 任务 metrics → match_field 精确映射
    2. 仍无 → schema.roles amount/number 依次取第一个可用字段
    """
    for metric in metrics:
        field = match_field(
            schema,
            columns,
            metric
        )
        if field:
            return field

    for role in METRIC_ROLE_PRIORITY:
        fields = resolve_role_fields(
            state,
            schema,
            columns,
            role
        )
        if fields:
            return fields[0]

    return None


def rank_rows_tool(state, task=None):
    """
    按分组字段汇总指定的指标字段，并排序返回前N条记录。

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
    condition = task.get("condition", {})
    order = condition.get("order", "desc")
    limit = condition.get("limit", 10)
    filters = task.get("filters", {})
    customer = task.get("customer", "")

    schema = getattr(state, "workbook_schema", {})
    sheets = getattr(state, "sheet_profiles", [])

    all_results = []  # 存储所有Sheet的汇总数据
    used_metric = None

    for sheet in sheets:
        df = sheet["df"].copy()
        sheet_name = sheet["sheet"]
        columns = list(df.columns)

        # 解析排名指标（任务 metrics → schema 角色字段）
        metric = _pick_metric(state, schema, columns, metrics)
        if not metric:
            continue
        if used_metric is None:
            used_metric = metric

        # 指标列转数值（解析失败降级为 NaN）
        df[metric] = pd.to_numeric(df[metric], errors="coerce")
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
                    df = df[df[matched_col].astype(str).str.contains(
                        str(value), na=False, regex=False)]

        if len(df) == 0:
            continue

        # 分组字段：customer → business → product → department → project
        # （注意：不用 find_customer_field，避免其 person 兜底把
        # 姓名列当作分组字段——对排名而言应按业务维度而非个人分组）
        group_field = None
        for role in GROUP_ROLE_PRIORITY:
            role_fields = resolve_role_fields(
                state,
                schema,
                columns,
                role
            )
            if role_fields:
                group_field = role_fields[0]
                break

        # 指定了客户时，按客户过滤（此时必须有客户字段）
        if customer:
            if not group_field:
                continue
            df = df[df[group_field].astype(str).str.contains(
                customer, na=False, regex=False)]
            if len(df) == 0:
                continue

        if group_field:
            # 按分组字段汇总
            grouped = df.groupby(group_field, as_index=False)[metric].sum()
        else:
            # 无任何分组字段：不分组，直接全表一行（指标合计）
            total = float(df[metric].sum())
            grouped = pd.DataFrame([
                {"分组": "全部", metric: total}
            ])

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
    all_results.sort(
        key=lambda x: x.get(used_metric, 0),
        reverse=reverse
    )

    # 取前N条
    top_results = all_results[:limit]

    # 添加排名序号
    for i, row in enumerate(top_results, 1):
        row["排名"] = i

    return {
        "type": "rank_rows",
        "status": "success",
        "message": f"排名完成，共 {len(all_results)} 条记录，返回前 {len(top_results)} 条",
        "metric": used_metric,
        "order": order,
        "limit": limit,
        "total_count": len(all_results),
        "data": {"rows": top_results}
    }
