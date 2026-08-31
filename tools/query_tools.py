import pandas as pd

from tools.field_resolver import (
    find_customer_field as _resolve_customer_field,
    resolve_field as _resolve_field,
)


# ==========================================================
# Schema字段处理
# ==========================================================

def clean_schema_field(field):
    """
    去除Schema字段前缀

    例如：

    Sheet1.客商名称
        ↓
    客商名称
    """

    if not field:
        return ""

    field = str(field)

    if "." in field:
        return field.split(".", 1)[-1]

    return field


# ==========================================================
# 获取Planner任务
# ==========================================================

def get_query_task(state):
    """
    获取 query_value 任务
    """

    for task in getattr(state, "plan", []):

        if task.get("tool") == "query_value":
            return task

    return None


# ==========================================================
# 获取Schema字段
# ==========================================================

def get_schema_fields(schema, category):
    """
    获取Schema中的字段。

    支持：

    customer
    business
    product
    department
    project
    money
    number
    time
    """

    if category == "time":

        fields = schema.get(
            "time_fields",
            []
        )

    elif category in schema.get(
        "entities",
        {}
    ):

        fields = schema.get(
            "entities",
            {}
        ).get(
            category,
            []
        )

    elif category in schema.get(
        "metrics",
        {}
    ):

        fields = schema.get(
            "metrics",
            {}
        ).get(
            category,
            []
        )

    else:

        fields = []

    return [
        clean_schema_field(field)
        for field in fields
    ]


# ==========================================================
# 获取全部Schema字段
# ==========================================================

def get_all_schema_fields(schema):
    """
    获取Schema中所有字段。
    """

    result = []

    entities = schema.get(
        "entities",
        {}
    )

    for fields in entities.values():

        result.extend(fields)

    metrics = schema.get(
        "metrics",
        {}
    )

    for fields in metrics.values():

        result.extend(fields)

    result.extend(
        schema.get(
            "time_fields",
            []
        )
    )

    return list(
        dict.fromkeys(
            clean_schema_field(x)
            for x in result
        )
    )


# ==========================================================
# 字段匹配
# ==========================================================

def match_field(
    schema,
    columns,
    user_field
):
    """
    将Planner逻辑字段
    映射到当前Sheet真实字段。

    匹配优先级：

    1. 精确匹配
    2. Schema字段匹配
    3. 包含匹配
    4. Schema模糊匹配
    """

    if not user_field:
        return None

    user_field = clean_schema_field(
        user_field
    )

    columns = [
        str(x).strip()
        for x in columns
    ]

    # ------------------------------------------------------
    # 1. 精确匹配
    # ------------------------------------------------------

    if user_field in columns:
        return user_field

    # ------------------------------------------------------
    # 2. Schema字段
    # ------------------------------------------------------

    schema_fields = get_all_schema_fields(
        schema
    )

    for schema_field in schema_fields:

        if schema_field not in columns:
            continue

        if user_field == schema_field:
            return schema_field

    # ------------------------------------------------------
    # 3. 包含匹配
    # ------------------------------------------------------

    for column in columns:

        if (
            user_field in column
            or
            column in user_field
        ):

            return column

    # ------------------------------------------------------
    # 4. Schema模糊匹配
    # ------------------------------------------------------

    for schema_field in schema_fields:

        if schema_field not in columns:
            continue

        if (
            user_field in schema_field
            or
            schema_field in user_field
        ):

            return schema_field

    return None


# ==========================================================
# 找客户字段
#
# 修复：此前这里是独立实现（schema猜测 + 关键词兜底两层），
# 与 rank_tools.py / compare_tools.py 里几乎一样的代码各自维护
# 一份，且都没有读取用户在前端确认过的 state.mapping。
# 现在改为统一委托给 field_resolver.find_customer_field，
# 优先级变为：state.mapping（用户确认） → schema猜测 → 关键词兜底。
# ==========================================================

def find_customer_field(
    state,
    schema,
    columns
):
    """
    寻找当前Sheet中的客户字段。
    委托给field_resolver统一处理，保留函数名以兼容本文件内其它调用。
    """
    return _resolve_customer_field(state, schema, columns)


# ==========================================================
# 找任意字段
# ==========================================================

def find_any_field(
    schema,
    columns,
    key,
    state=None
):
    """
    根据用户语义寻找字段。

    优先级：明确字段匹配 → 语义映射（state.mapping → schema.roles
    → 关键词兜底）。
    """

    if not key:
        return None

    # ------------------------------------------------------
    # 1. 明确字段匹配
    # ------------------------------------------------------

    field = match_field(
        schema,
        columns,
        key
    )

    if field:
        return field

    key = str(key)

    # ------------------------------------------------------
    # 2. 语义匹配：用户词 → 角色 → schema 字段
    #
    # 不再使用硬编码的"合同名称/业务类型"关键词表，统一委托
    # field_resolver.resolve_field（state.mapping → schema.roles
    # → 关键词兜底）。任何行业的字段都能命中。
    # ------------------------------------------------------

    category_keywords = {

        "customer": [
            "客户",
            "客商"
        ],

        "business": [
            "业务种类",
            "业务类型",
            "业务条件",
            "业务"
        ],

        "product": [
            "产品",
            "商品",
            "物料"
        ],

        "department": [
            "部门",
            "事业部",
            "组织"
        ],

        "project": [
            "项目",
            "合同",
            "工程"
        ],

        "date": [
            "时间",
            "日期",
            "月份",
            "年份",
            "年度",
            "期间",
            "账期"
        ],

        "amount": [
            "金额",
            "余额",
            "销售",
            "收入",
            "利润",
            "贷方",
            "借方"
        ],

        "number": [
            "数量",
            "次数",
            "销量",
            "人数"
        ]
    }

    for category, keywords in category_keywords.items():

        if any(
            keyword in key
            for keyword in keywords
        ):

            field = _resolve_field(
                state,
                schema,
                columns,
                category
            )

            if field:

                return field

    return None


# ==========================================================
# 获取客户名称包裹模式
#
# 修复：此前 normalize_customer 硬编码了"【客商：xxx】"的剥离
# 规则，这是为财务台账模板定制的。现在改为从 schema 的
# pattern（由 SchemaAgent 根据样本实际统计，coverage>=0.5 才
# 记录）读取，仅当样本确认包含该模式时才剥离。
# ==========================================================

def get_customer_pattern(schema, columns, customer_field):
    """
    从 schema 读取客户字段的包裹模式。

    返回 (prefix, suffix) 或 None。
    schema.fields 的 key 形如 "Sheet.列名"，info.column 为列名；
    多个 Sheet 存在同名列时取第一个匹配项。
    """

    if not schema or not customer_field:

        return None

    fields = schema.get("fields", {}) or {}

    for info in fields.values():

        if not isinstance(info, dict):

            continue

        if info.get("column") != customer_field:

            continue

        pattern = info.get("pattern")

        if (
            pattern
            and isinstance(pattern, dict)
            and pattern.get("type") == "prefix_suffix"
            and pattern.get("prefix")
        ):

            return (
                pattern.get("prefix"),
                pattern.get("suffix", "") or ""
            )

        break

    return None


# ==========================================================
# 获取客户标准化名称
# ==========================================================

def normalize_customer(value, pattern=None):
    """
    标准化客户名称。

    1. 优先使用 schema 样本检测到的包裹模式（如 "【客商：", "】"）
    2. 通用语义前缀兜底：客商：/客户：
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    if pattern:

        prefix, suffix = pattern

        if value.startswith(prefix):

            value = value[len(prefix):]

            if suffix and value.endswith(suffix):

                value = value[:-len(suffix)]

            return value.strip()

    for start in ("客商：", "客户："):

        if value.startswith(start):

            value = value[len(start):]

            break

    return value.strip()


# ==========================================================
# 客户过滤
# ==========================================================

def filter_customer(
    df,
    customer_field,
    customer,
    pattern=None
):
    """
    客户模糊查询。
    """

    if (
        not customer_field
        or
        customer_field not in df.columns
    ):

        return df.iloc[0:0].copy()

    target = normalize_customer(
        customer,
        pattern
    )

    normalized = (
        df[customer_field]
        .apply(
            lambda v: normalize_customer(
                v,
                pattern
            )
        )
    )

    return df[
        normalized.str.contains(
            target,
            na=False,
            regex=False
        )
    ]


# ==========================================================
# 获取客户关联Key
# ==========================================================

def get_customer_keys(
    df,
    customer_field,
    pattern=None
):
    """
    获取当前Sheet客户关联键。
    """

    if (
        not customer_field
        or
        customer_field not in df.columns
    ):

        return set()

    values = (
        df[customer_field]
        .dropna()
        .apply(
            lambda v: normalize_customer(
                v,
                pattern
            )
        )
    )

    return {
        value
        for value in values
        if value
    }


# ==========================================================
# 根据客户Key过滤
# ==========================================================

def filter_by_customer_keys(
    df,
    customer_field,
    customer_keys,
    pattern=None
):
    """
    根据客户关联键过滤Sheet。
    """

    if (
        not customer_field
        or
        customer_field not in df.columns
    ):

        return df.iloc[0:0].copy()

    normalized = (
        df[customer_field]
        .apply(
            lambda v: normalize_customer(
                v,
                pattern
            )
        )
    )

    return df[
        normalized.isin(customer_keys)
    ]


# ==========================================================
# 应用Filter
# ==========================================================

def apply_filters(
    df,
    schema,
    filters,
    state=None
):
    """
    应用Planner产生的filters。

    例如：

    {
        "业务条件": "公路建设期产品运维(JSYW)",
        "业务对象": "合同"
    }

    会自动映射为：

    业务条件
        ↓
    业务类型（新）名称

    业务对象
        ↓
    合同名称
    """

    temp = df.copy()

    matched_fields = {}

    for key, value in filters.items():

        if value is None:
            continue

        if str(value).strip() == "":
            continue

        # --------------------------------------------------
        # 找字段
        # --------------------------------------------------

        target_field = find_any_field(
            schema,
            list(temp.columns),
            key,
            state=state
        )

        if not target_field:

            # 修复：此前过滤字段无法匹配时直接返回空表，导致
            # 一个条件名对不上就让整个查询结果为空。现在记录
            # 警告后跳过该条件，其余条件继续生效。
            print(
                f"⚠️ Filter字段无法匹配，跳过该条件: {key}"
            )

            continue

        matched_fields[key] = target_field

        print(
            f"过滤条件: {key} "
            f"→ {target_field} "
            f"= {value}"
        )

        # --------------------------------------------------
        # 执行过滤
        # --------------------------------------------------

        temp = temp[
            temp[target_field]
            .astype(str)
            .str.contains(
                str(value),
                na=False,
                regex=False
            )
        ]

        if len(temp) == 0:
            break

    return (
        temp,
        matched_fields
    )


# ==========================================================
# 找Metric字段
# ==========================================================

def find_metric_fields(
    df,
    schema,
    metrics
):
    """
    将Planner中的metrics
    映射为当前Sheet真实字段。
    """

    result = []

    columns = list(df.columns)

    for metric in metrics:

        field = match_field(
            schema,
            columns,
            metric
        )

        if field and field not in result:

            result.append(field)

    return result


# ==========================================================
# DataFrame -> Rows
# ==========================================================

def dataframe_to_rows(
    df,
    sheet_name
):
    """
    DataFrame转结构化数据。
    """

    if len(df) == 0:
        return []

    temp = df.copy()

    if "来源Sheet" not in temp.columns:

        temp.insert(
            0,
            "来源Sheet",
            sheet_name
        )

    return temp.to_dict(
        orient="records"
    )


# ==========================================================
# 空结果
# ==========================================================

def empty_result(
    customer,
    filters,
    metrics,
    message="没有匹配数据"
):

    return {

        "type":
            "query_value",

        "status":
            "success",

        "message":
            message,

        "customer":
            customer,

        "filters":
            filters,

        "metrics":
            metrics,

        "total_count":
            0,

        "matched_count":
            0,

        "business_count":
            0,

        "sheet_counts":
            {},

        "summary":
            {},

        "data":
            {
                "rows":
                    []
            }
    }


# ==========================================================
# Query Value Tool
# ==========================================================

def query_value_tool(state):
    """
    通用Schema驱动查询工具。

    支持：

    1. 客户查询
    2. 多Sheet查询
    3. 任意字段过滤
    4. 多条件过滤
    5. 合同查询
    6. 产品查询
    7. 部门查询
    8. 项目查询
    9. 指标字段定位
    10. 跨Sheet客户JOIN
    11. 金额汇总
    12. 多Sheet结果返回
    """

    schema = state.workbook_schema

    sheets = state.sheet_profiles

    # ======================================================
    # 1. 获取任务
    # ======================================================

    task = get_query_task(
        state
    )

    if not task:

        return empty_result(
            "",
            {},
            [],
            "没有找到query_value任务"
        )

    customer = task.get(
        "customer",
        ""
    )

    filters = task.get(
        "filters",
        {}
    )

    metrics = task.get(
        "metrics",
        []
    )

    print(
        "\n========== Query Tool =========="
    )

    print(
        "查询客户:",
        customer
    )

    print(
        "过滤条件:",
        filters
    )

    print(
        "指标:",
        metrics
    )

    # ======================================================
    # 2. 扫描所有Sheet
    # ======================================================

    sheet_infos = []

    for sheet in sheets:

        df = sheet["df"].copy()

        sheet_name = sheet["sheet"]

        columns = list(df.columns)

        # --------------------------------------------------
        # 客户字段（修复：改用统一的field_resolver，优先读取
        # state.mapping中用户手动确认过的映射）
        # --------------------------------------------------

        customer_field = find_customer_field(
            state,
            schema,
            columns
        )

        # 客户名称包裹模式（仅当样本确认含该模式时才剥离）
        customer_pattern = get_customer_pattern(
            schema,
            columns,
            customer_field
        )

        # --------------------------------------------------
        # Filter字段
        # --------------------------------------------------

        filter_fields = {}

        if filters:

            for key in filters:

                field = find_any_field(
                    schema,
                    columns,
                    key,
                    state=state
                )

                if field:

                    filter_fields[key] = field

        # --------------------------------------------------
        # Metric字段
        # --------------------------------------------------

        metric_fields = find_metric_fields(
            df,
            schema,
            metrics
        )

        # --------------------------------------------------
        # 客户过滤
        # --------------------------------------------------

        if customer and not customer_field:

            customer_df = df.iloc[0:0].copy()

        elif customer:

            customer_df = filter_customer(
                df,
                customer_field,
                customer,
                customer_pattern
            )

        else:

            customer_df = df.copy()

        info = {

            "sheet":
                sheet_name,

            "df":
                df,

            "customer_field":
                customer_field,

            "customer_pattern":
                customer_pattern,

            "customer_df":
                customer_df,

            "filter_fields":
                filter_fields,

            "metric_fields":
                metric_fields
        }

        sheet_infos.append(
            info
        )

        print(
            f"\n[{sheet_name}]"
        )

        print(
            "客户字段:",
            customer_field
        )

        print(
            "过滤字段:",
            filter_fields
        )

        print(
            "指标字段:",
            metric_fields
        )

        print(
            "客户匹配:",
            len(customer_df)
        )

    # ======================================================
    # 3. 判断客户是否存在
    # ======================================================

    if customer:

        customer_exists = any(
            len(info["customer_df"]) > 0
            for info in sheet_infos
        )

        if not customer_exists:

            return empty_result(
                customer,
                filters,
                metrics,
                "没有找到指定客户"
            )

    # ======================================================
    # 4. 执行Filter
    # ======================================================

    filter_infos = []

    if filters:

        for info in sheet_infos:

            if not info["filter_fields"]:
                continue

            filtered_df, matched_fields = apply_filters(
                info["customer_df"],
                schema,
                filters,
                state
            )

            print(
                f"{info['sheet']} "
                f"过滤后:",
                len(filtered_df)
            )

            if len(filtered_df) > 0:

                filter_infos.append(
                    {

                        **info,

                        "filtered_df":
                            filtered_df,

                        "matched_fields":
                            matched_fields
                    }
                )

    # ======================================================
    # 5. 获取客户JOIN Key
    # ======================================================

    join_customer_keys = set()

    for info in filter_infos:

        keys = get_customer_keys(
            info["filtered_df"],
            info["customer_field"],
            info.get("customer_pattern")
        )

        join_customer_keys.update(
            keys
        )

    # ======================================================
    # 6. 有Filter但没有结果
    # ======================================================

    if filters and not join_customer_keys:

        return empty_result(
            customer,
            filters,
            metrics
        )

    # ======================================================
    # 7. 确定目标Sheet
    # ======================================================

    target_infos = []

    for info in sheet_infos:

        # --------------------------------------------------
        # 没有Filter
        # --------------------------------------------------

        if not filters:

            if len(info["customer_df"]) > 0:

                target_infos.append(
                    {

                        **info,

                        "result_df":
                            info["customer_df"]
                    }
                )

            continue

        # --------------------------------------------------
        # 当前Sheet就是Filter Sheet
        # --------------------------------------------------

        if info["filter_fields"]:

            matched = None

            for filter_info in filter_infos:

                if (
                    filter_info["sheet"]
                    ==
                    info["sheet"]
                ):

                    matched = filter_info

                    break

            if matched:

                target_infos.append(
                    {

                        **info,

                        "result_df":
                            matched["filtered_df"]
                    }
                )

            continue

        # --------------------------------------------------
        # 其他Sheet
        #
        # 如果有指标，则通过客户Key JOIN
        # --------------------------------------------------

        if info["metric_fields"]:

            joined_df = filter_by_customer_keys(
                info["customer_df"],
                info["customer_field"],
                join_customer_keys,
                info.get("customer_pattern")
            )

            if len(joined_df) > 0:

                target_infos.append(
                    {

                        **info,

                        "result_df":
                            joined_df
                    }
                )

            continue

        # --------------------------------------------------
        # 没有Metric
        #
        # 默认不强制JOIN
        # 但如果客户相同，也可以作为关联Sheet
        # --------------------------------------------------

        joined_df = filter_by_customer_keys(
            info["customer_df"],
            info["customer_field"],
            join_customer_keys,
            info.get("customer_pattern")
        )

        if len(joined_df) > 0:

            target_infos.append(
                {

                    **info,

                    "result_df":
                        joined_df
                }
            )

    # ======================================================
    # 8. 没有Metrics时
    #
    # 必须保证Filter Sheet返回
    # ======================================================

    if filters and not metrics:

        existing = {
            info["sheet"]
            for info in target_infos
        }

        for info in filter_infos:

            if info["sheet"] not in existing:

                target_infos.append(
                    {

                        **info,

                        "result_df":
                            info["filtered_df"]
                    }
                )

    # ======================================================
    # 9. 没有目标Sheet
    # ======================================================

    if not target_infos:

        return empty_result(
            customer,
            filters,
            metrics
        )

    # ======================================================
    # 10. 构造结果
    # ======================================================

    all_results = []

    sheet_counts = {}

    for info in target_infos:

        result_df = info["result_df"]

        if len(result_df) == 0:
            continue

        rows = dataframe_to_rows(
            result_df,
            info["sheet"]
        )

        all_results.extend(
            rows
        )

        sheet_counts[
            info["sheet"]
        ] = len(rows)

    # ======================================================
    # 11. 没有结果
    # ======================================================

    if not all_results:

        return empty_result(
            customer,
            filters,
            metrics
        )

    # ======================================================
    # 12. 指标汇总
    # ======================================================

    summary = {}

    # 修复：汇总字段从 schema.roles 的 amount/number 角色取
    # （唯一事实来源），兼容旧结构 metrics.money 兜底
    roles = schema.get(
        "roles",
        {}
    ) or {}

    money_fields = [
        clean_schema_field(f)
        for f in (
            roles.get("amount", [])
            + roles.get("number", [])
        )
    ]

    if not money_fields:

        money_fields = get_schema_fields(
            schema,
            "money"
        )

    requested_metric_fields = set()

    for info in target_infos:

        requested_metric_fields.update(
            info.get(
                "metric_fields",
                []
            )
        )

    fields_to_sum = []

    # ------------------------------------------------------
    # Planner指定指标
    # ------------------------------------------------------

    for field in requested_metric_fields:

        if field not in fields_to_sum:

            fields_to_sum.append(
                field
            )

    # ------------------------------------------------------
    # 没指定指标
    #
    # 自动统计Schema金额字段
    # ------------------------------------------------------

    if not fields_to_sum:

        for field in money_fields:

            if field not in fields_to_sum:

                fields_to_sum.append(
                    field
                )

    # ------------------------------------------------------
    # 汇总
    # ------------------------------------------------------

    for field in fields_to_sum:

        total = 0.0

        found = False

        for row in all_results:

            if field not in row:
                continue

            value = row[field]

            numeric_value = pd.to_numeric(
                pd.Series([value]),
                errors="coerce"
            ).iloc[0]

            if pd.notna(
                numeric_value
            ):

                total += float(
                    numeric_value
                )

                found = True

        if found:

            summary[
                field + "总额"
            ] = round(
                total,
                2
            )

    # ======================================================
    # 13. 日志
    # ======================================================

    print(
        "\n========== Query结果 =========="
    )

    print(
        "目标Sheet:",
        [
            info["sheet"]
            for info in target_infos
        ]
    )

    print(
        "Sheet结果:",
        sheet_counts
    )

    print(
        "最终返回:",
        len(all_results)
    )

    print(
        "汇总:",
        summary
    )

    # ======================================================
    # 14. 返回
    # ======================================================

    return {

        "type":
            "query_value",

        "status":
            "success",

        "message":
            "查询完成",

        "customer":
            customer,

        "filters":
            filters,

        "metrics":
            metrics,

        "total_count":
            len(all_results),

        "matched_count":
            len(all_results),

        "business_count":
            len(all_results),

        "sheet_counts":
            sheet_counts,

        "summary":
            summary,

        "data":
            {
                "rows":
                    all_results[:100]
            }
    }

# ==========================================================
# 汇总统计工具（合计/总额/总计/求和）
#
# 指标优先取任务 metrics，为空时自动取 schema 中全部
# amount/number 字段 —— 不依赖任何行业字段名。
# ==========================================================

def aggregate_value_tool(state):
    """汇总统计金额/数量字段"""

    schema = getattr(
        state,
        "workbook_schema",
        {}
    )

    sheets = getattr(
        state,
        "sheet_profiles",
        []
    )

    task = getattr(
        state,
        "current_task",
        None
    ) or {}

    filters = task.get(
        "filters",
        {}
    )

    metrics = task.get(
        "metrics",
        []
    )

    print(
        "\n========== Aggregate Tool =========="
    )

    print(
        "过滤条件:",
        filters
    )

    # --------------------------------------------------
    # 汇总字段：任务 metrics → schema amount/number 角色
    # --------------------------------------------------

    if not metrics:

        role_fields = []

        roles = schema.get(
            "roles",
            {}
        )

        for role in ("amount", "number"):

            role_fields.extend(
                roles.get(
                    role,
                    []
                )
            )

        # 兼容旧结构 metrics
        if not role_fields:

            metrics_map = schema.get(
                "metrics",
                {}
            )

            role_fields = (
                metrics_map.get(
                    "money",
                    []
                )
                + metrics_map.get(
                    "number",
                    []
                )
            )

        metrics = [
            clean_schema_field(f)
            for f in role_fields
        ]

    summaries = []

    total = {}

    for sheet in sheets:

        df = sheet["df"].copy()

        sheet_name = sheet["sheet"]

        columns = list(df.columns)

        # 过滤
        if filters:

            filtered_df, _ = apply_filters(
                df,
                schema,
                filters,
                state
            )

        else:

            filtered_df = df

        if len(filtered_df) == 0:
            continue

        sheet_summary = {}

        for metric in metrics:

            field = match_field(
                schema,
                columns,
                metric
            )

            if not field:

                continue

            series = pd.to_numeric(
                filtered_df[field],
                errors="coerce"
            ).dropna()

            if len(series) == 0:
                continue

            sheet_summary[field] = round(
                float(series.sum()),
                2
            )

        if sheet_summary:

            summaries.append(
                {
                    "sheet": sheet_name,
                    "summary": sheet_summary
                }
            )

            for field, value in sheet_summary.items():

                total[field] = round(
                    total.get(field, 0.0) + value,
                    2
                )

    result = {
        "type": "aggregate_value",
        "status": "success",
        "filters": filters,
        "metrics": metrics,
        "total_count": sum(len(s["df"]) for s in sheets),
        "summary": total,
        "data": {
            "sheet_summaries": summaries,
            "rows": []
        }
    }

    if not total:

        result["status"] = "success"

        result["message"] = "没有可汇总的数值字段"

    return result


# ==========================================================
# 异常检测工具（均值 ± 2σ）
# ==========================================================

def detect_anomaly_tool(state):
    """检测数值字段的异常值（均值±2σ）"""

    schema = getattr(
        state,
        "workbook_schema",
        {}
    )

    sheets = getattr(
        state,
        "sheet_profiles",
        []
    )

    task = getattr(
        state,
        "current_task",
        None
    ) or {}

    filters = task.get(
        "filters",
        {}
    )

    metrics = task.get(
        "metrics",
        []
    )

    print(
        "\n========== Anomaly Tool =========="
    )

    print(
        "过滤条件:",
        filters
    )

    # 异常检测字段：任务 metrics → schema amount/number 角色
    if not metrics:

        roles = schema.get(
            "roles",
            {}
        )

        for role in ("amount", "number"):

            metrics.extend(
                roles.get(
                    role,
                    []
                )
            )

        if not metrics:

            metrics_map = schema.get(
                "metrics",
                {}
            )

            metrics = (
                metrics_map.get(
                    "money",
                    []
                )
                + metrics_map.get(
                    "number",
                    []
                )
            )

    anomaly_rows = []

    anomaly_summary = {}

    for sheet in sheets:

        df = sheet["df"].copy()

        sheet_name = sheet["sheet"]

        columns = list(df.columns)

        if filters:

            filtered_df, _ = apply_filters(
                df,
                schema,
                filters,
                state
            )

        else:

            filtered_df = df

        if len(filtered_df) == 0:
            continue

        for metric in metrics:

            field = match_field(
                schema,
                columns,
                metric
            )

            if not field:

                continue

            series = pd.to_numeric(
                filtered_df[field],
                errors="coerce"
            ).dropna()

            if len(series) < 3:
                continue

            mean = series.mean()

            std = series.std()

            if std == 0 or pd.isna(std):
                continue

            lower = mean - 2 * std

            upper = mean + 2 * std

            outlier_mask = (
                (series < lower)
                | (series > upper)
            )

            count = int(outlier_mask.sum())

            if count > 0:

                anomaly_summary[field] = count

                for idx in series[outlier_mask].index:

                    row = df.loc[idx].to_dict()

                    row["来源Sheet"] = sheet_name

                    row["_anomaly_field"] = field

                    row["_anomaly_value"] = round(
                        float(series.loc[idx]),
                        2
                    )

                    row["_anomaly_range"] = [
                        round(lower, 2),
                        round(upper, 2)
                    ]

                    anomaly_rows.append(row)

    return {
        "type": "detect_anomaly",
        "status": "success",
        "filters": filters,
        "metrics": metrics,
        "total_count": len(anomaly_rows),
        "anomaly_summary": anomaly_summary,
        "data": {
            "rows": anomaly_rows[:100]
        }
    }
