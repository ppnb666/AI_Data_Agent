"""
LLM Agent任务规划器

调用DeepSeek生成任务执行计划
"""

import json
import logging



class TaskPlanner:


    def __init__(self, llm_client):

        self.llm = llm_client

        self.logger = logging.getLogger(__name__)



    def create_plan(self, user_query:str):

        """
        根据用户需求生成工具调用计划

        返回:

        [
            "clean_data",
            "detect_outliers"
        ]
        """


        # 没有需求，执行完整分析

        if not user_query:


            return [
                "clean_data",
                "top_product",
                "detect_outliers",
                "create_chart",
                "generate_report",
                "generate_markdown_report"
            ]



        prompt=f"""
你是一个数据分析Agent的任务规划器。

你的目标：
根据用户需求选择需要调用的工具。


可用工具：

clean_data:
数据清洗，删除缺失和重复数据

top_product:
分析销售额最高的产品

detect_outliers:
检测异常销售数据

create_chart:
生成销售图表

generate_report:
生成文本分析报告

generate_markdown_report:
生成Markdown报告


用户需求：

{user_query}


请只返回JSON数组。

例如：

[
"clean_data",
"detect_outliers"
]


不要输出任何解释。
"""


        messages=[

            {
                "role":"system",
                "content":
                "你是一个专业的数据分析任务规划器，只返回JSON数组。"
            },


            {
                "role":"user",
                "content":prompt
            }

        ]



        try:


            response=self.llm.chat(
                messages
            )


            print(
                "\nDeepSeek Planner返回:"
            )

            print(response)



            if not response:

                raise Exception(
                    "LLM返回为空"
                )



            # 去除markdown包裹

            response=response.strip()


            if response.startswith("```"):


                response=(
                    response
                    .replace("```json","")
                    .replace("```","")
                    .strip()
                )



            plan=json.loads(
                response
            )


            return plan



        except Exception as e:


            self.logger.error(
                f"Planner失败:{e}"
            )


            print(
                "⚠️ Planner失败，使用默认计划"
            )


            return [

                "clean_data",

                "top_product",

                "detect_outliers",

                "generate_report"

            ]