"""
LLM Agent任务规划器 V5

支持:

1. 合同查询
2. 财务余额查询
3. 多条件过滤查询
4. 销售分析
5. 自动选择工具

"""


import json
import logging

from tools import tool_registry



class TaskPlanner:


    def __init__(
            self,
            llm_client
    ):

        self.llm = llm_client

        self.logger = logging.getLogger(
            __name__
        )



    def optimize_plan(
            self,
            plan
    ):

        """
        根据任务类型优化执行顺序
        """


        # 查询任务直接执行

        if any(
            task.get("tool")
            ==
            "query_value"

            for task in plan
        ):

            return plan



        result=[]


        tools=[

            t.get("tool")

            for t in plan

        ]



        analysis_tools=[

            "top_product",

            "detect_outliers",

            "create_chart",

            "generate_report",

            "generate_markdown_report"

        ]



        if any(
            t in tools
            for t in analysis_tools
        ):


            result.append(

                {

                    "tool":
                    "clean_data",

                    "reason":
                    "数据分析前需要清洗"

                }

            )



        result.extend(plan)


        return result





    def create_plan(
            self,
            user_query:str
    ):



        tools = tool_registry.list_tools()



        prompt=f"""

你是企业数据分析Agent规划器。



你的任务:

根据用户需求选择正确工具。


========================

工具列表:

{tools}


========================


【合同财务查询规则】


如果用户包含:


查询

查

余额

合同

客户

客商

期末余额

期初余额

贷方累计

本期贷方


必须选择:


query_value



========================


返回格式:


[
{{
"tool":"query_value",

"reason":"查询合同数据",

"customer":"完整客户名称",

"metrics":[
"期末余额"
],

"filters":{{

"业务类型（新）":
"xxx"

}}

}}
]



========================


【客户名称规则】


必须保留完整客户名称。


例如:


用户:

查保利长大工程有限公司余额



返回:


保利长大工程有限公司



禁止:


保利长大



必须保留:

有限公司

集团

分公司

股份有限公司



========================


【多条件过滤规则】


用户出现:


业务类型

产品类型

合同类型

项目类型


必须提取:

filters



例如:


用户:

查询保利长大工程有限公司

业务类型（新）:

公路建设期产品运维(JSYW)



返回:


"filters":{{

"业务类型（新）":

"公路建设期产品运维(JSYW)"

}}



========================


【销售分析】


如果用户包含:


销售

销量

排行

趋势

异常

报告


选择销售分析工具。



========================


用户需求:


{user_query}



========================


要求:


1. 只能返回JSON数组


2. 不允许解释


3. tool必须来自工具列表


4. filters必须保留


5. customer必须完整



"""



        messages=[

            {

                "role":
                "system",

                "content":
                """
你是企业数据Agent规划器。
只能输出合法JSON。
"""

            },


            {

                "role":
                "user",

                "content":
                prompt

            }

        ]



        try:


            response = self.llm.chat(
                messages
            )


            print(
                "\n===== DeepSeek Planner原始返回 ====="
            )


            print(response)



            response=response.strip()



            # 去除markdown


            if response.startswith(
                "```"
            ):


                response=(

                    response

                    .replace(
                        "```json",
                        ""
                    )

                    .replace(
                        "```",
                        ""
                    )

                    .strip()

                )



            plan=json.loads(
                response
            )



            valid=[]



            for task in plan:


                tool=task.get(
                    "tool"
                )


                if tool not in tools:


                    print(
                        f"忽略不存在工具:{tool}"
                    )

                    continue



                valid.append(

                    {

                        "tool":
                        tool,


                        "reason":
                        task.get(
                            "reason",
                            ""
                        ),


                        "customer":
                        task.get(
                            "customer",
                            ""
                        ),


                        "metrics":
                        task.get(
                            "metrics",
                            []
                        ),


                        "filters":
                        task.get(
                            "filters",
                            {}

                        )

                    }

                )



            print(
                "\n=====最终Planner计划====="
            )


            print(valid)



            return self.optimize_plan(
                valid
            )



        except Exception as e:


            self.logger.error(

                f"Planner失败:{e}"

            )


            print(
                "Planner失败，使用默认查询"
            )



            # 默认不要乱分析

            if any(
                key in user_query

                for key in [

                    "查",

                    "查询",

                    "余额",

                    "合同"

                ]

            ):


                return [

                    {

                        "tool":
                        "query_value",


                        "reason":
                        "默认合同查询"

                    }

                ]



            return [

                {

                    "tool":
                    "clean_data",


                    "reason":
                    "默认数据清洗"

                }

            ]