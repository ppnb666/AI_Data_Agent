"""
LLM Agent任务规划器 V2

功能:
1. 调用DeepSeek生成任务计划
2. 返回结构化任务
3. 自动读取Tool Registry
"""


import json
import logging


from tools import tool_registry



class TaskPlanner:
    def optimize_plan(self, plan):
        """
        根据工具依赖关系优化任务执行顺序
        """

        tool_names = [
            task["tool"]
            for task in plan
        ]

        optimized_plan = []

        def add_tool(tool, reason):

            existing_tools = [
                                 t["tool"]
                                 for t in optimized_plan
                             ] + tool_names

            if tool not in existing_tools:
                optimized_plan.append(
                    {
                        "tool": tool,
                        "reason": reason
                    }
                )

        # ==========================
        # 规则1:
        # 数据分析基础依赖
        # ==========================

        analysis_tools = [
            "top_product",
            "detect_outliers",
            "create_chart",
            "generate_report",
            "generate_markdown_report"
        ]

        need_clean = any(
            tool in tool_names
            for tool in analysis_tools
        )

        if need_clean:
            add_tool(
                "clean_data",
                "数据分析前需要清洗数据"
            )

        # ==========================
        # 规则2:
        # 销售分析依赖top_product
        # ==========================

        report_tools = [
            "generate_report",
            "generate_markdown_report"
        ]

        if any(
                tool in tool_names
                for tool in report_tools
        ):
            add_tool(
                "top_product",
                "生成报告前需要分析销售冠军"
            )

        # ==========================
        # 保留原计划
        # ==========================

        optimized_plan.extend(plan)

        return optimized_plan


    def __init__(self, llm_client):

        self.llm = llm_client

        self.logger = logging.getLogger(__name__)




    def create_plan(self, user_query:str):

        """
        根据用户需求生成任务计划


        返回:

        [
            {
                "tool":"clean_data",
                "reason":"数据分析前需要清洗"
            }
        ]

        """



        # 获取工具列表

        tools = tool_registry.list_tools()



        # 没有需求

        if not user_query:
            default_plan = [

                {
                    "tool": "clean_data",
                    "reason": "默认执行数据清洗"
                },

                {
                    "tool": "top_product",
                    "reason": "分析销售冠军产品"
                },

                {
                    "tool": "detect_outliers",
                    "reason": "检测异常销售数据"
                },

                {
                    "tool": "create_chart",
                    "reason": "生成数据可视化图表"
                },

                {
                    "tool": "generate_report",
                    "reason": "生成分析报告"
                },

                {
                    "tool": "generate_markdown_report",
                    "reason": "生成Markdown报告"
                }

            ]

            return self.optimize_plan(default_plan)



        prompt=f"""

你是一个专业的数据分析Agent Planner。


你的任务：

根据用户需求，选择需要执行的数据分析工具。


当前可用工具：

{tools}



用户需求：

{user_query}



请返回JSON数组。


格式必须严格如下：

[
    {{
        "tool":"工具名称",
        "reason":"选择该工具的原因"
    }}
]



例如：

[
    {{
        "tool":"detect_outliers",
        "reason":"用户要求分析销售异常"
    }},

    {{
        "tool":"generate_report",
        "reason":"用户要求生成报告"
    }}
]



注意：

1. tool字段必须来自可用工具列表
2. 不要输出解释
3. 只返回JSON
"""



        messages=[

            {
                "role":"system",
                "content":
                """
你是一个数据分析Agent规划器。
你必须输出合法JSON。
"""
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



            response=response.strip()



            # 去除markdown

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



            # 计划校验

            valid_plan=[]


            for task in plan:


                tool_name=task.get(
                    "tool"
                )


                if tool_name in tools:


                    valid_plan.append(
                        {
                            "tool":tool_name,
                            "reason":task.get(
                                "reason",
                                ""
                            )
                        }
                    )


                else:

                    print(
                        f"⚠️ 忽略不存在工具:{tool_name}"
                    )

            return self.optimize_plan(valid_plan)


        except Exception as e:


            self.logger.error(
                f"Planner失败:{e}"
            )


            print(
                "⚠️ Planner失败，使用默认计划"
            )



            return [

                {
                    "tool":"clean_data",
                    "reason":"默认数据清洗"
                },

                {
                    "tool":"top_product",
                    "reason":"默认销售分析"
                },

                {
                    "tool":"detect_outliers",
                    "reason":"默认异常检测"
                },

                {
                    "tool":"generate_report",
                    "reason":"默认生成报告"
                }

            ]