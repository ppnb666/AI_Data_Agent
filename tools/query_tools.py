import pandas as pd


# ==========================================================
# Schema字段处理
# ==========================================================

def clean_schema_field(field):
    """
    去除Schema字段前缀

    Sheet1.客商名称 -> 客商名称
    """

    if "." in field:
        return field.split(".")[-1]

    return field


# ==========================================================
# Planner任务
# ==========================================================

def get_query_task(state):
    """
    获取query_value任务
    """

    for task in state.plan:

        if task.get("tool") == "query_value":
            return task

    return None


# ==========================================================
# 找客户字段
# ==========================================================

def find_customer_field(schema, columns):
    """
    根据Schema寻找当前Sheet的客户字段
    """

    customer_fields = [
        clean_schema_field(x)
        for x in
        schema
        .get("entities", {})
        .get("customer", [])
    ]

    for field in customer_fields:

        if field in columns:
            return field

    return None


# ==========================================================
# 找业务字段
# ==========================================================

def find_business_field(
    schema,
    columns,
    filter_key
):
    """
    根据Planner中的filter key寻找真实字段

    支持：

    业务类型（新）
    ->
    业务类型（新）名称

    业务类型
    ->
    业务类型
    """

    # ------------------------------------------------------
    # 1. 精确匹配
    # ------------------------------------------------------

    if filter_key in columns:
        return filter_key

    # ------------------------------------------------------
    # 2. Schema业务字段
    # ------------------------------------------------------

    business_fields = [
        clean_schema_field(x)
        for x in
        schema
        .get("entities", {})
        .get("business", [])
    ]

    for field in business_fields:

        if field not in columns:
            continue

        if (
            filter_key == field
            or filter_key in field
            or field in filter_key
        ):
            return field

    # ------------------------------------------------------
    # 3. 模糊匹配
    # ------------------------------------------------------

    for column in columns:

        if (
            filter_key in column
            or column in filter_key
        ):
            return column

    return None


# ==========================================================
# 找金额字段
# ==========================================================

def get_money_fields(schema):
    """
    获取Schema中的金额字段
    """

    return [
        clean_schema_field(x)
        for x in
        schema
        .get("metrics", {})
        .get("money", [])
    ]


# ==========================================================
# 客户匹配
# ==========================================================

def filter_customer(
    df,
    customer_field,
    customer
):
    """
    对客户进行模糊匹配
    """

    if (
        customer_field is None
        or customer_field not in df.columns
    ):

        return df.iloc[0:0].copy()

    return df[
        df[customer_field]
        .astype(str)
        .str.contains(
            customer,
            na=False,
            regex=False
        )
    ]


# ==========================================================
# 标准化客户名称
# ==========================================================

def normalize_customer(value):
    """
    简单标准化客户名称。

    处理：

    【客商：保利长大工程有限公司】
    保利长大工程有限公司

    统一成：

    保利长大工程有限公司
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    # ------------------------------------------------------
    # 去掉常见客商包装
    # ------------------------------------------------------

    if value.startswith("【客商："):

        value = value.replace(
            "【客商：",
            "",
            1
        )

        if value.endswith("】"):
            value = value[:-1]

    return value.strip()


# ==========================================================
# 获取客户关联键
# ==========================================================

def get_customer_keys(
    df,
    customer_field
):
    """
    获取当前Sheet中的标准化客户关联键
    """

    if (
        customer_field is None
        or customer_field not in df.columns
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
# 根据关联键过滤Sheet
# ==========================================================

def filter_by_customer_keys(
    df,
    customer_field,
    customer_keys
):
    """
    使用标准化后的客户名称进行关联过滤
    """

    if (
        customer_field is None
        or customer_field not in df.columns
    ):

        return df.iloc[0:0].copy()

    normalized = (
        df[customer_field]
        .apply(normalize_customer)
    )

    return df[
        normalized.isin(
            customer_keys
        )
    ]


# ==========================================================
# 应用业务过滤
# ==========================================================

def apply_filters(
    df,
    schema,
    filters
):
    """
    对当前Sheet应用业务条件

    返回：

        filtered_df
        matched_fields
    """

    temp = df.copy()

    matched_fields = {}

    for key, value in filters.items():

        target_field = find_business_field(
            schema,
            list(temp.columns),
            key
        )

        if not target_field:

            return (
                temp.iloc[0:0].copy(),
                matched_fields
            )

        matched_fields[key] = target_field

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
# 判断一个Sheet是不是过滤条件所在Sheet
# ==========================================================

def sheet_contains_filters(
    df,
    schema,
    filters
):
    """
    判断当前Sheet是否包含所有filter字段
    """

    if not filters:
        return False

    for key in filters:

        field = find_business_field(
            schema,
            list(df.columns),
            key
        )

        if not field:

            return False

    return True


# ==========================================================
# 根据metrics寻找目标Sheet
# ==========================================================

def sheet_contains_metrics(
    df,
    metrics
):
    """
    判断Sheet是否包含Planner请求的指标字段
    """

    if not metrics:
        return False

    columns = set(
        df.columns
    )

    for metric in metrics:

        metric = clean_schema_field(
            metric
        )

        if metric in columns:
            return True

    return False


# ==========================================================
# 行转换
# ==========================================================

def dataframe_to_rows(
    df,
    sheet_name
):
    """
    将DataFrame转成结构化rows。

    注意：

    每个Sheet只返回自己拥有的字段，
    不再把不同Sheet的列强行拼接。
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
# query_value
# ==========================================================

def query_value_tool(state):
    """
    Schema驱动多Sheet查询。

    支持：

    1. 普通客户查询
    2. Sheet内业务过滤
    3. 跨Sheet业务条件JOIN
    4. 根据metrics选择目标Sheet
    5. 客商名称作为跨Sheet关联键
    6. 金额汇总

    跨Sheet JOIN逻辑：

        Sheet2业务过滤
              ↓
        得到客户关联键
              ↓
        JOIN Sheet1
              ↓
        获取Sheet1指标

    例如：

        业务类型（新）= JSYW
              ↓
        Sheet2找到客户
              ↓
        客商名称
              ↓
        Sheet1
              ↓
        期末余额
    """

    schema = state.workbook_schema

    sheets = state.sheet_profiles

    # ==================================================
    # 获取Planner任务
    # ==================================================

    task = get_query_task(
        state
    )

    if not task:

        return {
            "type": "query_value",
            "status": "failed",
            "message": "没有找到query_value任务",
            "customer": "",
            "filters": {},
            "metrics": [],
            "total_count": 0,
            "matched_count": 0,
            "business_count": 0,
            "summary": {},
            "data": {
                "rows": []
            }
        }

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

    # ==================================================
    # 客户校验
    # ==================================================

    if not customer:

        return {
            "type": "query_value",
            "status": "failed",
            "message": "没有客户",
            "customer": "",
            "filters": filters,
            "metrics": metrics,
            "total_count": 0,
            "matched_count": 0,
            "business_count": 0,
            "summary": {},
            "data": {
                "rows": []
            }
        }

    print(
        "\n查询客户:",
        customer
    )

    # ==================================================
    # Schema信息
    # ==================================================

    money_fields = get_money_fields(
        schema
    )

    # ==================================================
    # 第一步：
    # 收集所有Sheet基础信息
    # ==================================================

    sheet_infos = []

    for sheet in sheets:

        df = sheet["df"].copy()

        sheet_name = sheet["sheet"]

        customer_field = find_customer_field(
            schema,
            list(df.columns)
        )

        if not customer_field:

            continue

        customer_df = filter_customer(
            df,
            customer_field,
            customer
        )

        sheet_infos.append(
            {
                "sheet": sheet_name,
                "df": df,
                "customer_df": customer_df,
                "customer_field":
                    customer_field
            }
        )

        print(
            f"{sheet_name} 客户匹配:",
            len(customer_df)
        )

    # ==================================================
    # 客户完全不存在
    # ==================================================

    if not sheet_infos:

        return {
            "type": "query_value",
            "status": "success",
            "message": "没有匹配数据",
            "customer": customer,
            "filters": filters,
            "metrics": metrics,
            "total_count": 0,
            "matched_count": 0,
            "business_count": 0,
            "summary": {},
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 第二步：
    # 如果存在filters，
    # 找到filter所在Sheet
    # ==================================================

    filter_sheet_infos = []

    for info in sheet_infos:

        if not filters:
            continue

        if sheet_contains_filters(
            info["df"],
            schema,
            filters
        ):

            filtered_df, matched_fields = apply_filters(
                info["customer_df"],
                schema,
                filters
            )

            print(
                f"{info['sheet']} 应用过滤后:",
                len(filtered_df)
            )

            if len(filtered_df) > 0:

                filter_sheet_infos.append(
                    {
                        **info,
                        "filtered_df":
                            filtered_df,
                        "matched_fields":
                            matched_fields
                    }
                )

    # ==================================================
    # 第三步：
    # 跨Sheet建立客户关联键
    # ==================================================

    join_customer_keys = set()

    for info in filter_sheet_infos:

        keys = get_customer_keys(
            info["filtered_df"],
            info["customer_field"]
        )

        join_customer_keys.update(
            keys
        )

    # 如果存在filter，
    # 但没有任何Sheet满足filter，
    # 直接返回空

    if filters and not join_customer_keys:

        return {
            "type": "query_value",
            "status": "success",
            "message": "没有匹配数据",
            "customer": customer,
            "filters": filters,
            "metrics": metrics,
            "total_count": 0,
            "matched_count": 0,
            "business_count": 0,
            "summary": {},
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 第四步：
    # 确定目标Sheet
    # ==================================================

    target_infos = []

    for info in sheet_infos:

        df = info["df"]

        # ----------------------------------------------
        # 没有filters：
        #
        # 保持原有行为：
        # 客户所在Sheet都作为结果
        # ----------------------------------------------

        if not filters:

            target_infos.append(
                {
                    **info,
                    "result_df":
                        info["customer_df"]
                }
            )

            continue

        # ----------------------------------------------
        # 有filters：
        #
        # 情况A：
        # 当前Sheet就是过滤Sheet
        # ----------------------------------------------

        if sheet_contains_filters(
            df,
            schema,
            filters
        ):

            matched_filter_info = None

            for filter_info in filter_sheet_infos:

                if (
                    filter_info["sheet"]
                    ==
                    info["sheet"]
                ):

                    matched_filter_info = (
                        filter_info
                    )

                    break

            if matched_filter_info:

                target_infos.append(
                    {
                        **info,
                        "result_df":
                            matched_filter_info[
                                "filtered_df"
                            ]
                    }
                )

            continue

        # ----------------------------------------------
        # 情况B：
        # 当前Sheet没有filter字段
        #
        # 但是包含目标metric
        #
        # 通过客户关联键JOIN
        # ----------------------------------------------

        if sheet_contains_metrics(
            df,
            metrics
        ):

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

        # ----------------------------------------------
        # 情况C：
        # 没有metrics
        #
        # 为了保持通用查询，
        # 允许其他客户关联Sheet参与返回
        # ----------------------------------------------

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

    # ==================================================
    # 第五步：
    # 如果存在filters，
    # 但Planner没有给metrics
    #
    # 保留过滤Sheet本身
    # ==================================================

    if filters and not metrics:

        target_sheet_names = {
            info["sheet"]
            for info in target_infos
        }

        for info in filter_sheet_infos:

            if (
                info["sheet"]
                not in target_sheet_names
            ):

                target_infos.append(
                    {
                        **info,
                        "result_df":
                            info["filtered_df"]
                    }
                )

    # ==================================================
    # 没有目标Sheet
    # ==================================================

    if not target_infos:

        return {
            "type": "query_value",
            "status": "success",
            "message": "没有匹配数据",
            "customer": customer,
            "filters": filters,
            "metrics": metrics,
            "total_count": 0,
            "matched_count": 0,
            "business_count": 0,
            "summary": {},
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 第六步：
    # 构造结果
    # ==================================================

    all_results = []

    sheet_counts = {}

    for info in target_infos:

        result_df = info[
            "result_df"
        ]

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

    # ==================================================
    # 没有结果
    # ==================================================

    if not all_results:

        return {
            "type": "query_value",
            "status": "success",
            "message": "没有匹配数据",
            "customer": customer,
            "filters": filters,
            "metrics": metrics,
            "total_count": 0,
            "matched_count": 0,
            "business_count": 0,
            "summary": {},
            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 第七步：
    # 金额汇总
    #
    # 注意：
    # 不再把不同Sheet的缺失金额字段
    # 强行补成0后再混合计算。
    #
    # 只有真正存在于结果中的金额字段才统计。
    # ==================================================

    summary = {}

    for money_field in money_fields:

        total = 0.0

        found = False

        for row in all_results:

            if money_field not in row:
                continue

            value = row[
                money_field
            ]

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
                money_field + "总额"
            ] = round(
                total,
                2
            )

    # ==================================================
    # 返回
    # ==================================================

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

    return {
        "type": "query_value",
        "status": "success",
        "message": "查询完成",

        "customer": customer,

        "filters": filters,

        "metrics": metrics,

        "total_count": len(
            all_results
        ),

        "matched_count": len(
            all_results
        ),

        "business_count": len(
            all_results
        ),

        "sheet_counts": sheet_counts,

        "summary": summary,

        "data": {
            "rows":
                all_results[:100]
        }
    }