"""
AI Data Agent

LLM Planner + Tool Registry
"""
from state import AgentState

import pandas as pd
from utils.logger import get_logger

from config import (
    DATA_PATH,
    REPORT_PATH,
    CHART_PATH,
    MD_REPORT_PATH,
    TREND_CHART_PATH
)


from tools import tool_registry


from utils.data_parser import detect_columns
from utils.data_profiler import profile_dataframe


from llm.client import (
    get_client,
    LLMClient
)


from planner import TaskPlanner
from profiler.data_profiler_agent import DataProfilerAgent


class DataAgent:


    def __init__(
            self,
            llm_client: LLMClient = None
    ):

        self.logger = get_logger(
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
        self.data_profiler = DataProfilerAgent(
            self.llm
        )


        self.analysis_result = {}

        self.user_query = ""



    def analyze(
            self,
            state
    ):
        self.logger.info(
            f"读取数据文件:{state.file_path}"
        )



        # 读取数据

        from utils.excel_loader import load_excel
        df, sheet_name = load_excel(
            state.file_path
        )

        state.sheet_name = sheet_name


        state.df = df
        # AI理解数据结构

        schema = self.data_profiler.analyze(
            df
        )

        state.schema = schema

        self.logger.info(
            f"AI数据理解结果:{schema}"
        )

        print(
            "\n📚 AI数据理解:"
        )

        print(
            schema
        )

        state.data_profile = profile_dataframe(
            df
        )

        self.logger.info(
            f"数据画像:{state.data_profile}"
        )

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
            self.logger.info(
                f"开始执行工具: {tool_name}"
            )
            state.trace.add_step(
                tool_name,
                "running",
                "开始执行工具"
            )

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

                # ⭐保存工具返回结果

                tool_result = func(
                    state
                )

                if tool_name == "query_value":
                    state.query_result = tool_result

                state.trace.add_step(
                    tool_name,
                    "success",
                    "工具执行完成"
                )

                self.logger.info(
                    f"工具执行完成: {tool_name}"
                )


            except Exception as e:
                self.logger.error(
                    f"{tool_name}执行失败: {e}"
                )

                state.trace.add_step(
                    tool_name,
                    "failed",
                    str(e)
                )

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
                list(state.df.columns),



            "query_result":
                state.query_result,

        }



        state.analysis_result = (
            self.analysis_result
        )
        self.logger.info(
            f"分析完成:{self.analysis_result}"
        )

        state.trace.save()


        return self.analysis_result

    def get_ai_insight(self):

        query_result = (
            self.analysis_result
            .get(
                "query_result",
                {}
            )
        )

        # ==========================
        # 合同查询场景
        # ==========================

        if query_result:
            prompt = f"""

    你是一名企业财务数据分析专家。


    请根据以下客户合同查询结果，
    生成业务分析建议。


    查询数据:

    {query_result}



    请按照以下结构输出：


    一、客户查询概况

    说明：

    - 客户名称
    - 匹配合同数量
    - 金额规模


    二、合同金额分析

    重点分析：

    - 期初余额
    - 本期贷方
    - 贷方累计
    - 期末余额


    判断：

    - 当前合同金额规模
    - 客户资金情况
    - 是否存在较大余额


    三、业务建议

    结合数据提出：

    - 合同跟踪建议
    - 回款管理建议
    - 风险关注点


    注意：

    不要分析：
    - 产品销量
    - 销售冠军
    - 销售排名

    因为当前数据属于合同财务数据。



    请输出中文分析。
    """

            return self.llm.chat(
                [
                    {
                        "role": "system",
                        "content":
                            "你是一名企业财务分析助手"
                    },

                    {
                        "role": "user",
                        "content": prompt
                    }

                ]
            )

        # ==========================
        # 原销售分析场景
        # ==========================

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
        self.logger.info(
            f"Agent开始执行任务: {user_query}"
        )



        # 创建Agent状态

        state = AgentState()


        state.user_query = user_query

        state.file_path = file_path



        # Planner生成计划

        state.plan = self.planner.create_plan(
            user_query
        )

        self.logger.info(
            f"Planner生成计划: {state.plan}"
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