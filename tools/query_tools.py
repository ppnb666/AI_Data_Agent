import pandas as pd


def clean_schema_field(field):
    """
    去除 Schema 字段前缀

    Sheet1.客商名称 -> 客商名称
    """

    if "." in field:
        return field.split(".")[-1]

    return field


def query_value_tool(state):
    """
    Schema驱动多Sheet查询

    支持:
    1. 客户资料查询
    2. 多Sheet合并
    3. 业务过滤
    4. 金额汇总

    返回统一结构:

    {
        "type": "query_value",
        "status": "success",
        "customer": "...",
        "filters": {},
        "total_count": 93,
        "matched_count": 93,
        "business_count": 93,
        "summary": {},
        "data": {
            "rows": [...]
        }
    }
    """

    schema = state.workbook_schema

    sheets = state.sheet_profiles

    customer = ""
    filters = {}

    # ==================================================
    # 获取 Planner 任务
    # ==================================================

    for task in state.plan:

        if task.get("tool") == "query_value":

            customer = task.get(
                "customer",
                ""
            )

            filters = task.get(
                "filters",
                {}
            )

            break

    # ==================================================
    # 没有客户
    # ==================================================

    if not customer:

        return {
            "type": "query_value",
            "status": "failed",
            "message": "没有客户",
            "customer": "",
            "filters": filters,
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
    # Schema字段
    # ==================================================

    customer_fields = [
        clean_schema_field(x)
        for x in
        schema
        .get("entities", {})
        .get("customer", [])
    ]

    business_fields = [
        clean_schema_field(x)
        for x in
        schema
        .get("entities", {})
        .get("business", [])
    ]

    money_fields = [
        clean_schema_field(x)
        for x in
        schema
        .get("metrics", {})
        .get("money", [])
    ]

    # ==================================================
    # 查询结果
    # ==================================================

    all_results = []

    business_count = 0

    # ==================================================
    # 遍历所有Sheet
    # ==================================================

    for sheet in sheets:

        df = sheet["df"].copy()

        sheet_name = sheet["sheet"]

        cols = list(df.columns)

        customer_col = None

        # ------------------------------------------------
        # 自动寻找客户字段
        # ------------------------------------------------

        for c in customer_fields:

            if c in cols:

                customer_col = c
                break

        if not customer_col:

            continue

        # ==================================================
        # 客户过滤
        # ==================================================

        temp = df[
            df[customer_col]
            .astype(str)
            .str.contains(
                customer,
                na=False,
                regex=False
            )
        ]

        if len(temp) == 0:

            continue

        print(
            sheet_name,
            "匹配:",
            len(temp)
        )

        # ==================================================
        # 业务过滤
        # ==================================================

        for key, value in filters.items():

            target_field = None

            # ------------------------------------------------
            # 先找完全匹配字段
            # ------------------------------------------------

            if key in temp.columns:

                target_field = key

            # ------------------------------------------------
            # 再根据 Schema 中的业务字段寻找
            # ------------------------------------------------

            else:

                for field in business_fields:

                    if field in temp.columns and key in field:

                        target_field = field
                        break

            # ------------------------------------------------
            # 找到对应字段后过滤
            # ------------------------------------------------

            if target_field:

                temp = temp[
                    temp[target_field]
                    .astype(str)
                    .str.contains(
                        str(value),
                        na=False,
                        regex=False
                    )
                ]

        # ==================================================
        # 保存结果
        # ==================================================

        if len(temp) > 0:

            temp.insert(
                0,
                "来源Sheet",
                sheet_name
            )

            all_results.extend(
                temp.to_dict(
                    orient="records"
                )
            )

            business_count += len(temp)

    # ==================================================
    # 没有匹配数据
    # ==================================================

    if len(all_results) == 0:

        return {
            "type": "query_value",
            "status": "success",
            "message": "没有匹配数据",

            "customer": customer,

            "filters": filters,

            "total_count": 0,

            "matched_count": 0,

            "business_count": 0,

            "summary": {},

            "data": {
                "rows": []
            }
        }

    # ==================================================
    # 构造最终DataFrame
    # ==================================================

    result = pd.DataFrame(
        all_results
    )

    total_count = len(result)

    matched_count = len(result)

    # ==================================================
    # 金额字段汇总
    # ==================================================

    summary = {}

    for col in money_fields:

        if col in result.columns:

            numeric_data = pd.to_numeric(
                result[col],
                errors="coerce"
            )

            result[col] = (
                numeric_data
                .fillna(0)
            )

            summary[
                col + "总额"
            ] = round(
                result[col].sum(),
                2
            )

    print(
        "最终返回:",
        len(result)
    )

    # ==================================================
    # 最终统一返回结构
    # ==================================================

    return {
        "type": "query_value",

        "status": "success",

        "message": "查询完成",

        "customer": customer,

        "filters": filters,

        "total_count": total_count,

        "matched_count": matched_count,

        "business_count": business_count,

        "summary": summary,

        "data": {
            "rows":
            result
            .head(100)
            .to_dict(
                orient="records"
            )
        }
    }