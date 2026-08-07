import pandas as pd


def clean_field(field):
    """
    去除Schema字段前缀

    Sheet1.客商名称 -> 客商名称
    """

    if "." in field:
        return field.split(".")[-1]

    return field



def get_compare_task(state):

    for task in state.plan:

        if task.get("tool") == "compare_rows":

            return task

    return None



def find_customer_field(schema, columns):

    customer_fields = [

        clean_field(x)

        for x in
        schema.get("entities", {})
        .get("customer", [])

    ]

    for field in customer_fields:

        if field in columns:

            return field

    return None



def apply_operator(df, left, right, operator):

    left_data = pd.to_numeric(
        df[left],
        errors="coerce"
    )

    right_data = pd.to_numeric(
        df[right],
        errors="coerce"
    )


    if operator == "!=":

        return df[left_data != right_data]


    elif operator == "==":

        return df[left_data == right_data]


    elif operator == ">":

        return df[left_data > right_data]


    elif operator == "<":

        return df[left_data < right_data]


    elif operator == ">=":

        return df[left_data >= right_data]


    elif operator == "<=":

        return df[left_data <= right_data]


    else:

        return df[left_data != right_data]



def compare_rows_tool(state):

    """
    通用字段比较工具

    Planner提供:

    customer
    filters
    compare:
        left
        right
        operator


    返回异常整行
    """

    task = get_compare_task(state)


    if not task:

        return {

            "type":
            "compare_rows",

            "status":
            "failed",

            "message":
            "没有找到compare_rows任务"

        }



    customer = task.get(
        "customer",
        ""
    )


    filters = task.get(
        "filters",
        {}
    )


    compare = task.get(
        "compare",
        {}
    )


    left = compare.get(
        "left"
    )

    right = compare.get(
        "right"
    )


    operator = compare.get(
        "operator",
        "!="
    )



    schema = getattr(
        state,
        "workbook_schema",
        {}
    )


    result_df = None



    # ======================
    # 自动寻找数据Sheet
    # ======================

    for sheet in state.sheet_profiles:


        df = sheet["df"].copy()


        columns = list(
            df.columns
        )


        customer_field = find_customer_field(
            schema,
            columns
        )


        if not customer_field:

            continue


        if left not in columns:

            continue


        if right not in columns:

            continue



        print(
            "compare使用Sheet:",
            sheet["sheet"]
        )



        # 客户过滤

        if customer:


            df = df[

                df[customer_field]
                .astype(str)
                .str.contains(
                    customer,
                    na=False
                )

            ]



        # 条件过滤

        for key,value in filters.items():


            target = None


            if key in df.columns:

                target = key


            else:

                for col in df.columns:

                    if key in col:

                        target = col

                        break



            if target:


                df=df[

                    df[target]
                    .astype(str)
                    .str.contains(
                        value,
                        regex=False,
                        na=False
                    )

                ]



        print(
            "过滤后数量:",
            len(df)
        )



        result_df = apply_operator(
            df,
            left,
            right,
            operator
        )


        break



    if result_df is None:


        return {

            "type":
            "compare_rows",

            "status":
            "failed",

            "message":
            "没有找到匹配字段"

        }



    rows = result_df.head(
        100
    ).to_dict(
        orient="records"
    )



    return {


        "type":
        "compare_rows",


        "status":
        "success",


        "customer":
        customer,


        "filters":
        filters,


        "compare":
        {

            "left":
            left,

            "right":
            right,

            "operator":
            operator

        },


        "count":
        len(result_df),


        "data":
        {

            "rows":
            rows

        }

    }