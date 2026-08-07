import pandas as pd


def clean_schema_field(field):

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
    """

    schema = state.workbook_schema

    sheets = state.sheet_profiles


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
            "error":"没有客户"
        }



    print("\n查询客户:",customer)


    customer_fields=[

        clean_schema_field(x)

        for x in schema
        .get("entities",{})
        .get("customer",[])

    ]



    business_fields=[

        clean_schema_field(x)

        for x in schema
        .get("entities",{})
        .get("business",[])

    ]



    money_fields=[

        clean_schema_field(x)

        for x in schema
        .get("metrics",{})
        .get("money",[])

    ]



    all_results=[]


    business_count=0



    # =========================
    # 遍历所有Sheet
    # =========================

    for sheet in sheets:


        df=sheet["df"].copy()

        sheet_name=sheet["sheet"]


        cols=list(df.columns)


        customer_col=None


        for c in customer_fields:

            if c in cols:

                customer_col=c

                break



        if not customer_col:

            continue



        # 客户过滤

        temp=df[

            df[customer_col]
            .astype(str)
            .str.contains(
                customer,
                na=False,
                regex=False
            )

        ]



        if len(temp)==0:

            continue



        print(
            sheet_name,
            "匹配:",
            len(temp)
        )



        # ======================
        # 业务过滤
        # ======================

        for key,value in filters.items():


            for field in business_fields:

                if field in temp.columns:

                    temp=temp[

                        temp[field]
                        .astype(str)
                        .str.contains(
                            value,
                            na=False,
                            regex=False
                        )

                    ]

                    break



        if len(temp)>0:


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



            business_count+=len(temp)



    if len(all_results)==0:


        return {

            "customer":customer,

            "count":0,

            "message":"没有匹配数据"

        }



    result=pd.DataFrame(
        all_results
    )



    summary={}


    for col in money_fields:


        if col in result.columns:


            result[col]=pd.to_numeric(

                result[col],

                errors="coerce"

            ).fillna(0)



            summary[

                col+"总额"

            ]=round(

                result[col].sum(),

                2

            )



    print(
        "最终返回:",
        len(result)
    )



    return {


        "customer":

        customer,


        "filters":

        filters,


        "count":

        len(result),


        "business_count":

        business_count,


        "summary":

        summary,


        "data":

        result.head(100)
        .to_dict(
            orient="records"
        )

    }