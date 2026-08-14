import pandas as pd


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
# ==========================================================

def find_customer_field(
    schema,
    columns
):
    """
    根据Schema寻找当前Sheet中的客户字段。
    """

    customer_fields = get_schema_fields(
        schema,
        "customer"
    )

    # ------------------------------------------------------
    # 1. Schema优先
    # ------------------------------------------------------

    for field in customer_fields:

        if field in columns:
            return field

    # ------------------------------------------------------
    # 2. 兜底
    # ------------------------------------------------------

    customer_keywords = [
        "客商名称",
        "客户名称",
        "客户",
        "客商"
    ]

    for column in columns:

        if any(
            keyword in str(column)
            for keyword in customer_keywords
        ):

            return column

    return None


# ==========================================================
# 找任意字段
# ==========================================================

def find_any_field(
    schema,
    columns,
    key
):
    """
    根据用户语义寻找字段。
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
    # 2. 业务对象特殊处理
    #
    # 例如：
    #
    # 业务对象 = 合同
    #
    # 应该寻找：
    #
    # 合同名称
    # ------------------------------------------------------

    special_keywords = {

        "业务对象": [
            "合同名称",
            "合同"
        ],

        "合同": [
            "合同名称",
            "合同"
        ],

        "合同名称": [
            "合同名称"
        ],

        "业务条件": [
            "业务类型（新）名称",
            "业务类型",
            "业务种类"
        ]
    }

    if key in special_keywords:

        candidates = special_keywords[key]

        # 优先当前Sheet真实字段
        for candidate in candidates:

            for column in columns:

                if candidate == str(column):

                    return column

        # 再做包含匹配
        for candidate in candidates:

            for column in columns:

                if candidate in str(column):

                    return column

    # ------------------------------------------------------
    # 3. 通用语义匹配
    # ------------------------------------------------------

    category_keywords = {

        "customer": [
            "客户",
            "客商"
        ],

        "business": [
            "业务"
        ],

        "product": [
            "产品",
            "商品"
        ],

        "department": [
            "部门",
            "事业部",
            "组织"
        ],

        "project": [
            "项目"
        ],

        "time": [
            "时间",
            "日期",
            "月份",
            "年份",
            "年度",
            "期间",
            "账期"
        ]
    }

    for category, keywords in category_keywords.items():

        if any(
            keyword in key
            for keyword in keywords
        ):

            fields = get_schema_fields(
                schema,
                category
            )

            for field in fields:

                if field in columns:

                    return field

    return None


# ==========================================================
# 获取客户标准化名称
# ==========================================================

def normalize_customer(value):
    """
    标准化客户名称。

    支持：

    【客商：xxx】
    【客户：xxx】
    客商：xxx
    客户：xxx
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    wrappers = [
        ("【客商：", "】"),
        ("【客户：", "】"),
        ("客商：", ""),
        ("客户：", "")
    ]

    for start, end in wrappers:

        if value.startswith(start):

            value = value[len(start):]

            if end and value.endswith(end):

                value = value[:-len(end)]

            break

    return value.strip()


# ==========================================================
# 客户过滤
# ==========================================================

def filter_customer(
    df,
    customer_field,
    customer
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
        customer
    )

    normalized = (
        df[customer_field]
        .apply(normalize_customer)
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
    customer_field
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
        .apply(normalize_customer)
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
    customer_keys
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
        .apply(normalize_customer)
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
    filters
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
            key
        )

        if not target_field:

            print(
                f"⚠️ Filter字段无法匹配: {key}"
            )

            return (
                temp.iloc[0:0].copy(),
                matched_fields
            )

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
        # 客户字段
        # --------------------------------------------------

        customer_field = find_customer_field(
            schema,
            columns
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
                    key
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
                customer
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
                filters
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
            info["customer_field"]
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
                join_customer_keys
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
            join_customer_keys
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