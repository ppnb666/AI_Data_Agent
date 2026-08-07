"""
AI Data Agent

LLM Planner + Schema Agent + Tool Registry
"""

from state import AgentState

from utils.logger import get_logger

from config import (
    DATA_PATH
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

# ⭐新增
from schema.schema_agent import SchemaAgent



class DataAgent:

    def __init__(
            self,
            llm_client: LLMClient = None
    ):

        self.logger = get_logger(
            __name__
        )

        # ======================
        # LLM
        # ======================

        self.llm = (
                llm_client
                or get_client()
        )

        # ======================
        # Planner
        # ======================

        self.planner = TaskPlanner(
            self.llm
        )

        # ======================
        # Schema Agent
        # 负责理解整个Excel结构
        # ======================

        self.schema_agent = SchemaAgent(
            self.llm
        )

        # ======================
        # Data Profiler Agent
        # 负责理解当前Sheet
        # ======================

        self.data_profiler = DataProfilerAgent(
            self.llm
        )

        # ======================
        # 保存结果
        # ======================

        self.analysis_result = {}

        self.user_query = ""




    def analyze(
            self,
            state
    ):


        self.logger.info(
            f"读取数据文件:{state.file_path}"
        )



        # ======================
        # 1. 加载所有Sheet
        # ======================

        from utils.excel_loader import load_excel


        sheet_profiles = load_excel(
            state.file_path
        )


        state.sheet_profiles = sheet_profiles



        print(
            "\n📂 Excel Sheet数量:",
            len(sheet_profiles)
        )




        # ==========================
        # Schema Agent理解整个Excel
        # ==========================

        workbook_schema = self.schema_agent.analyze(
            sheet_profiles
        )

        state.workbook_schema = workbook_schema

        print(
            "\n📚 Excel结构理解:"
        )

        print(
            workbook_schema
        )


        state.workbook_schema = workbook_schema



        print(
            "\n🗂️ Excel数据地图:"
        )


        print(
            workbook_schema
        )




        # ======================
        # 3. AI选择Sheet
        # ======================


        selected = self.data_profiler.select_sheet(
            sheet_profiles,
            state.user_query
        )



        if not selected:


            self.logger.warning(
                "AI选择Sheet失败，使用第一个Sheet"
            )


            selected = sheet_profiles[0]




        df = selected["df"]


        sheet_name = selected["sheet"]



        state.df = df

        state.sheet_name = sheet_name



        self.logger.info(
            f"当前使用Sheet:{sheet_name}"
        )




        # ======================
        # 4. 单Sheet数据理解
        # ======================


        schema = self.data_profiler.analyze(
            df
        )


        state.schema = schema



        print(
            "\n📚 AI数据理解:"
        )


        print(
            schema
        )



        state.data_profile = profile_dataframe(
            df
        )




        # ======================
        # 5. 自动识别字段
        # ======================


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




        # ======================
        # 6. 执行Planner计划
        # ======================


        print(
            "\n执行计划:"
        )



        for task in state.plan:



            tool_name = task["tool"]



            print(
                f"\n执行工具:{tool_name}"
            )


            print(
                f"原因:{task.get('reason','')}"
            )



            state.current_tool = tool_name



            state.trace.add_step(
                tool_name,
                "running",
                "开始执行工具"
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


                result = func(
                    state
                )



                if tool_name == "query_value":


                    state.query_result = result



                state.trace.add_step(
                    tool_name,
                    "success",
                    "工具执行完成"
                )



            except Exception as e:


                self.logger.error(
                    f"{tool_name}执行失败:{e}"
                )


                state.error = str(e)



                state.trace.add_step(
                    tool_name,
                    "failed",
                    str(e)
                )



                break





        # ======================
        # 7. 汇总结果
        # ======================


        self.analysis_result = {



            "total_count":
                len(state.df),



            "clean_count":
                getattr(
                    state,
                    "clean_count",
                    0
                ),



            "top_product":
                getattr(
                    state,
                    "top_product",
                    None
                ),



            "top_sales":
                getattr(
                    state,
                    "top_sales",
                    None
                ),



            "outlier_count":
                len(
                    getattr(
                        state,
                        "outliers",
                        []
                    )
                ),



            "columns":
                list(
                    state.df.columns
                ),



            "query_result":
                getattr(
                    state,
                    "query_result",
                    {}
                )

        }



        state.analysis_result = (
            self.analysis_result
        )



        state.trace.save()



        return self.analysis_result







    def get_ai_insight(
            self
    ):



        query_result = (

            self.analysis_result
            .get(
                "query_result",
                {}
            )

        )



        # ======================
        # 合同分析
        # ======================


        if query_result:



            prompt=f"""

你是一名企业财务分析专家。


根据以下查询结果生成分析。


数据:

{query_result}


输出:

一、客户概况

二、金额分析

三、风险分析

四、业务建议


不要分析销售。


"""



            return self.llm.chat(

                [

                    {
                        "role":
                        "system",

                        "content":
                        "企业财务分析助手"

                    },


                    {

                        "role":
                        "user",

                        "content":
                        prompt

                    }

                ]

            )



        # ======================
        # 销售分析
        # ======================


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



        state = AgentState()



        state.file_path = file_path


        state.user_query = user_query




        # Planner

        state.plan = self.planner.create_plan(
            user_query
        )



        print(
            "\n🤖 AI Planner计划:"
        )


        print(
            state.plan
        )




        # 执行

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



    print(
        "\n==========分析结果=========="
    )


    print(
        result
    )





if __name__ == "__main__":


    main()