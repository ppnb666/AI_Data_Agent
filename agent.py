"""
AI Data Agent

LLM Planner + Tool Registry
"""

from state import AgentState

import pandas as pd
import logging


from config import (
    DATA_PATH,
    REPORT_PATH,
    CHART_PATH,
    MD_REPORT_PATH,
    TREND_CHART_PATH
)


from tools import tool_registry


from utils.data_parser import detect_columns


from llm.client import (
    get_client,
    LLMClient
)


from planner import TaskPlanner



class DataAgent:


    def __init__(
            self,
            llm_client: LLMClient = None
    ):


        self.logger = logging.getLogger(
            __name__
        )


        # DeepSeek

        self.llm = (
            llm_client
            or get_client()
        )


        # Planner

        self.planner = TaskPlanner(
            self.llm
        )


        self.analysis_result = {}

        self.user_query = ""



    def analyze(
            self,
            state
    ):


        # 读取数据

        df = pd.read_excel(
            state.file_path
        )


        state.df = df



        # 自动识别字段

        columns = detect_columns(
            df
        )


        state.sales_col = columns.get(
            "sales_column"
        )

        state.product_col = columns.get(
            "product_column"
        )

        state.date_col = columns.get(
            "date_column"
        )



        print("\n执行计划:")

        for task in state.plan:

            tool_name = task["tool"]

            reason = task["reason"]

            state.current_tool = tool_name

            print(
                f"执行工具:{tool_name}"
            )

            print(
                f"原因:{reason}"
            )

            tool = tool_registry.get_tool(
                tool_name
            )

            if not tool:
                print(
                    f"⚠️ 工具不存在:{tool_name}"
                )

                continue

            func = tool["function"]

            try:

                # ⭐统一传递state

                func(
                    state
                )


            except Exception as e:

                state.error = str(e)

                print(
                    f"❌ 工具执行失败:{e}"
                )

                break


        # 最终结果

        self.analysis_result = {


            "total_count":
                len(state.df),


            "clean_count":
                state.clean_count,


            "top_product":
                state.top_product,


            "top_sales":
                state.top_sales,


            "outlier_count":
                len(state.outliers),


            "columns":
                list(state.df.columns)

        }



        state.analysis_result = (
            self.analysis_result
        )


        return self.analysis_result





    def get_ai_insight(self):


        return self.llm.summarize_analysis(
            self.analysis_result
        )






    def run(
            self,
            file_path,
            user_query="",
            with_ai=True
    ):


        self.user_query = user_query



        # 创建Agent状态

        state = AgentState()


        state.user_query = user_query

        state.file_path = file_path



        # Planner生成计划

        state.plan = self.planner.create_plan(
            user_query
        )



        print(
            "\n🤖 AI Planner计划:"
        )


        print(
            state.plan
        )



        # 执行任务

        result = self.analyze(
            state
        )



        # AI总结

        if with_ai:


            result["ai_insight"] = (
                self.get_ai_insight()
            )



        return result





def main():


    agent = DataAgent()


    result = agent.run(
        DATA_PATH,
        "帮我分析销售异常，并生成报告"
    )


    print("\n==========分析结果==========")

    print(result)



if __name__ == "__main__":

    main()