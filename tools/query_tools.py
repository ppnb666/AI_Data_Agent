import pandas as pd


def clean_schema_field(field):

    """
    去掉Schema里的Sheet前缀

    Sheet1.客商名称
    ->
    客商名称
    """

    if "." in field:
        return field.split(".")[-1]

    return field



def query_value_tool(state):

    """
    Schema驱动智能查询

    不依赖固定Sheet
    不依赖固定字段

    """

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


    if not schema:

        return {
            "error":
            "没有Schema信息"
        }



    print("\n===== Schema驱动查询 =====")
    print(schema)



    # ======================
    # Planner参数
    # ======================

    customer = ""

    filters = {}


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



    if not customer:

        return {
            "error":
            "Planner没有客户"
        }



    print(
        "查询客户:",
        customer
    )

    print(
        "过滤条件:",
        filters
    )



    # ======================
    # Schema字段
    # ======================

    customer_fields = [

        clean_schema_field(x)

        for x in schema
        .get("entities", {})
        .get("customer", [])

    ]


    business_fields = [

        clean_schema_field(x)

        for x in schema
        .get("entities", {})
        .get("business", [])

    ]


    money_fields = [

        clean_schema_field(x)

        for x in schema
        .get("metrics", {})
        .get("money", [])

    ]



    print("客户字段:", customer_fields)

    print("业务字段:", business_fields)

    print("金额字段:", money_fields)



    # ======================
    # 自动找Sheet
    # ======================

    business_df = None

    money_df = None


    business_customer_field = None

    money_customer_field = None



    for sheet in sheets:


        df = sheet["df"]

        cols = list(df.columns)



        current_customer = None


        for c in customer_fields:

            if c in cols:

                current_customer = c

                break



        if not current_customer:

            continue



        # 业务Sheet

        if any(
            b in cols
            for b in business_fields
        ):

            business_df = df

            business_customer_field = current_customer



        # 金额Sheet

        if any(
            m in cols
            for m in money_fields
        ):

            money_df = df

            money_customer_field = current_customer




    if money_df is None:

        return {
            "error":
            "没有找到金额Sheet"
        }



    print(
        "业务Sheet:",
        business_df is not None
    )

    print(
        "金额Sheet:",
        money_df is not None
    )



    # ======================
    # 业务过滤
    # ======================

    target_customers=[]


    temp=None


    if business_df is not None:


        temp = business_df.copy()



        temp = temp[

            temp[business_customer_field]
            .astype(str)
            .str.contains(
                customer,
                na=False
            )

        ]



        for key,value in filters.items():


            target_business_field=None



            # Schema选择字段

            for field in business_fields:


                if field in temp.columns:

                    if (
                        key.replace(
                            "（新）",
                            ""
                        )
                        in field
                        or
                        "（新）" in field
                    ):

                        target_business_field = field

                        break



            if target_business_field is None:


                for field in business_fields:

                    if field in temp.columns:

                        target_business_field = field

                        break



            print(
                "最终业务字段:",
                target_business_field
            )


            if target_business_field:


                temp=temp[

                    temp[target_business_field]
                    .astype(str)
                    .str.contains(
                        value,
                        na=False,
                        regex=False
                    )

                ]



        print(
            "业务匹配数量:",
            len(temp)
        )



        if len(temp)>0:


            target_customers=(

                temp[business_customer_field]
                .dropna()
                .unique()
                .tolist()

            )



    # ======================
    # 金额查询
    # ======================


    result = money_df.copy()



    if target_customers:


        result=result[

            result[money_customer_field]
            .isin(
                target_customers
            )

        ]


    else:


        result=result[

            result[money_customer_field]
            .astype(str)
            .str.contains(
                customer,
                na=False
            )

        ]



    print(
        "最终金额记录:",
        len(result)
    )



    if len(result)==0:


        return {

            "customer":
            customer,

            "count":
            0,

            "message":
            "没有匹配数据"

        }




    # ======================
    # 汇总
    # ======================

    summary={}



    for col in money_fields:


        if col in result.columns:


            result[col]=pd.to_numeric(

                result[col],

                errors="coerce"

            ).fillna(0)



            summary[
                col+"总额"
            ] = round(

                result[col].sum(),

                2

            )



    return {


        "customer":
        customer,


        "filters":
        filters,


        "count":
        len(result),


        "business_count":
        len(temp)
        if temp is not None
        else 0,


        "summary":
        summary,


        "data":
        result.head(50)
        .to_dict(
            orient="records"
        )

    }