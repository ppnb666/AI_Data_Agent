"""
AI Data Agent

LLM Planner + Tool Registry
"""

import pandas as pd
import logging

from typing import Dict,Any


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
            llm_client:LLMClient=None
    ):


        self.logger=logging.getLogger(
            __name__
        )


        # DeepSeek

        self.llm = (
            llm_client
            or get_client()
        )


        # LLM Planner

        self.planner = TaskPlanner(
            self.llm
        )


        self.analysis_result={}

        self.user_query=""




    def analyze(
            self,
            file_path,
            plan
    ):


        df=pd.read_excel(
            file_path
        )


        columns=detect_columns(
            df
        )


        sales_col=columns.get(
            "sales_column"
        )

        product_col=columns.get(
            "product_column"
        )

        date_col=columns.get(
            "date_column"
        )



        context={

            "df":df,

            "sales_col":sales_col,

            "product_col":product_col,

            "date_col":date_col

        }



        result_data={

            "clean_count":0,

            "top_product":None,

            "top_sales":0,

            "outliers":[]

        }



        print("\n执行计划:")

        for task in plan:

            tool_name = task["tool"]

            reason = task["reason"]

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

                continue



            func=tool["function"]



            if tool_name=="clean_data":


                result=func(
                    context["df"]
                )


                context["df"]=result["data"]

                result_data["clean_count"]=(
                    result["clean_count"]
                )




            elif tool_name == "top_product":


                result=func(
                    context["df"],
                    sales_col,
                    product_col
                )


                result_data["top_product"]=(
                    result["product"]
                )


                result_data["top_sales"]=(
                    result["sales"]
                )




            elif tool_name == "detect_outliers":


                result=func(
                    context["df"],
                    sales_col
                )


                result_data["outliers"]=(
                    result["data"]
                )




            elif tool_name == "create_chart":


                func(
                    context["df"],
                    product_col,
                    sales_col,
                    CHART_PATH,
                    date_col,
                    TREND_CHART_PATH
                )




            elif tool_name == "generate_report":


                func(
                    context["df"],
                    result_data["clean_count"],
                    result_data["top_product"],
                    result_data["top_sales"],
                    REPORT_PATH
                )




            elif tool_name == "generate_markdown_report":


                func(
                    context["df"],
                    result_data["clean_count"],
                    result_data["top_product"],
                    result_data["top_sales"],
                    result_data["outliers"],
                    MD_REPORT_PATH
                )

        self.analysis_result = {

            "total_count":
                len(context["df"]),

            "clean_count":
                result_data["clean_count"],

            "top_product":
                result_data["top_product"],

            "top_sales":
                result_data["top_sales"],

            "outlier_count":
                len(result_data["outliers"]),

            "columns":
                list(context["df"].columns)

        }



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


        self.user_query=user_query



        # ① DeepSeek规划

        plan=self.planner.create_plan(
            user_query
        )


        print(
            "\n🤖 AI Planner计划:"
        )

        print(plan)



        # ② 执行工具

        result=self.analyze(
            file_path,
            plan
        )



        # ③ DeepSeek总结


        if with_ai:


            result["ai_insight"]=(
                self.get_ai_insight()
            )


        return result




def main():


    agent=DataAgent()


    agent.run(
        DATA_PATH,
        "帮我分析销售异常，并生成报告"
    )



if __name__=="__main__":

    main()