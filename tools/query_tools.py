import pandas as pd



def query_value_tool(state):


    df = state.df


    # ==========================
    # 从Planner获取客户
    # ==========================

    customer = ""


    if hasattr(state, "plan"):

        for task in state.plan:

            if task.get("tool") == "query_value":

                customer = task.get(
                    "customer",
                    ""
                )

                break



    if not customer:

        return {

            "error":
            "Planner没有提取客户名称"

        }



    print(
        "查询客户:",
        customer
    )



    # ==========================
    # 精确匹配
    # ==========================


    target = f"【客商：{customer}】"



    result = df[

        df["客商名称"]
        .astype(str)
        ==
        target

    ]



    print(
        "匹配数量:",
        len(result)
    )



    if len(result)==0:


        return {

            "customer":
            customer,

            "count":
            0,

            "message":
            "没有找到该客户"

        }




    # ==========================
    # 查询字段
    # ==========================


    columns=[


        "客商名称",

        "期初余额",

        "本期贷方",

        "贷方累计",

        "期末余额"

    ]



    result=result[columns].copy()



    # ==========================
    # 金额转换
    # ==========================


    money_columns=[


        "期初余额",

        "本期贷方",

        "贷方累计",

        "期末余额"

    ]


    for col in money_columns:


        result[col]=pd.to_numeric(

            result[col],

            errors="coerce"

        ).fillna(0)




    # ==========================
    # 汇总
    # ==========================


    summary={


        "期初余额总额":

            round(
                result["期初余额"].sum(),
                2
            ),



        "本期贷方总额":

            round(
                result["本期贷方"].sum(),
                2
            ),



        "贷方累计总额":

            round(
                result["贷方累计"].sum(),
                2
            ),



        "期末余额总额":

            float(
                round(
                    result["期末余额"].sum(),
                    2
                )
            )


    }




    return {


        "customer":

            customer,


        "count":

            len(result),



        "summary":

            summary,



        "data":

            result.to_dict(
                orient="records"
            )


    }