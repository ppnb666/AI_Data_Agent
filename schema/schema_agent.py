"""
Schema Agent

负责:
1. 分析Excel结构
2. 自动识别实体字段
3. 自动识别金额字段
4. 自动建立Sheet关系
5. 提供查询路径
"""


class SchemaAgent:


    def __init__(self, llm=None):

        self.llm = llm



    def analyze(self, sheet_profiles):


        schema = {

            "entities": {},

            "metrics": {},

            "time_fields": [],

            "relationships": [],

            "query_map": {}

        }


        sheets = []



        # =========================
        # 1.字段扫描
        # =========================


        for sheet in sheet_profiles:


            df = sheet["df"]


            sheet_name = sheet["sheet"]


            sheets.append(sheet_name)



            columns = list(
                df.columns
            )


            for col in columns:


                col=str(col)



                # 客户

                if (
                    "客商" in col
                    or
                    "客户" in col
                ):


                    schema["entities"].setdefault(
                        "customer",
                        []
                    )

                    schema["entities"]["customer"].append(
                        f"{sheet_name}.{col}"
                    )



                # 业务类型

                elif (
                    "业务" in col
                ):


                    schema["entities"].setdefault(
                        "business",
                        []
                    )


                    schema["entities"]["business"].append(
                        f"{sheet_name}.{col}"
                    )



                # 产品

                elif (
                    "商品" in col
                    or
                    "产品" in col
                ):


                    schema["entities"].setdefault(
                        "product",
                        []
                    )


                    schema["entities"]["product"].append(
                        f"{sheet_name}.{col}"
                    )



                # 部门

                elif (
                    "部门" in col
                ):


                    schema["entities"].setdefault(
                        "department",
                        []
                    )


                    schema["entities"]["department"].append(
                        f"{sheet_name}.{col}"
                    )



                # 金额

                if (
                    "余额" in col
                    or
                    "金额" in col
                    or
                    "万元" in col
                ):


                    schema["metrics"].setdefault(
                        "money",
                        []
                    )


                    schema["metrics"]["money"].append(
                        f"{sheet_name}.{col}"
                    )



                # 时间

                if (
                    "月份" in col
                    or
                    "日期" in col
                    or
                    "时间" in col
                    or
                    "摘要" in col
                ):


                    schema["time_fields"].append(
                        f"{sheet_name}.{col}"
                    )



        # =========================
        # 2. 自动发现关系
        # =========================


        customers = (
            schema["entities"]
            .get(
                "customer",
                []
            )
        )


        businesses = (
            schema["entities"]
            .get(
                "business",
                []
            )
        )



        # 客商关联

        for c1 in customers:


            for c2 in customers:


                if c1 != c2:


                    schema["relationships"].append(

                        {

                            "source":c1,

                            "target":c2,

                            "type":"same entity"

                        }

                    )




        # 业务关联

        for b1 in businesses:


            for b2 in businesses:


                if b1 != b2:


                    schema["relationships"].append(

                        {

                            "source":b1,

                            "target":b2,

                            "type":"business mapping"

                        }

                    )





        # =========================
        # 3.生成查询地图
        # =========================


        schema["query_map"]={


            "customer_field":
            self.first_field(
                schema,
                "customer"
            ),



            "business_fields":
            schema["entities"].get(
                "business",
                []
            ),



            "money_fields":
            schema["metrics"].get(
                "money",
                []
            )


        }




        print(
            "\n===== Schema查询 ====="
        )

        print(
            schema
        )

        schema["query_plan"] = {

            "customer_fields":
                schema["entities"]["customer"],

            "business_fields":
                schema["entities"]["business"],

            "money_fields":
                schema["metrics"]["money"],

            "relationships":
                schema["relationships"]

        }

        return schema




    def first_field(
            self,
            schema,
            key
    ):


        values = schema["entities"].get(
            key,
            []
        )


        if values:

            return values[0]


        return None