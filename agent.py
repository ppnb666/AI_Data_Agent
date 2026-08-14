"""
AI Data Agent

LLM Planner + Schema Agent + Tool Registry
"""

from state import AgentState

from utils.logger import get_logger

from config import DATA_PATH

from tools import tool_registry

from utils.data_parser import detect_columns
from utils.data_profiler import profile_dataframe

from llm.client import (
    get_client,
    LLMClient
)

from planner import TaskPlanner

from profiler.data_profiler_agent import DataProfilerAgent

from schema.schema_agent import SchemaAgent


class DataAgent:

    def __init__(
            self,
            llm_client: LLMClient = None
    ):

        self.logger = get_logger(
            __name__
        )

        self.llm = (
            llm_client
            or get_client()
        )

        self.planner = TaskPlanner(
            self.llm
        )

        self.schema_agent = SchemaAgent(
            self.llm
        )

        self.data_profiler = DataProfilerAgent(
            self.llm
        )

        self.analysis_result = {}

    # ==================================================
    # 数据准备阶段
    # ==================================================

    def prepare_context(
            self,
            state
    ):

        self.logger.info(
            f"读取数据文件:{state.file_path}"
        )

        from utils.excel_loader import load_excel

        sheets = load_excel(
            state.file_path
        )

        state.sheet_profiles = sheets

        print(
            "\n📂 Excel Sheet数量:",
            len(sheets)
        )

        # ==================================================
        # Schema理解
        # ==================================================

        schema = self.schema_agent.analyze(
            sheets
        )

        state.workbook_schema = schema

        print(
            "\n📚 Excel结构理解:"
        )

        print(schema)

        # ==================================================
        # 选择Sheet
        # ==================================================

        selected = self.data_profiler.select_sheet(
            sheets,
            state.user_query
        )

        if not selected:

            selected = sheets[0]

        state.df = selected["df"]

        state.sheet_name = selected["sheet"]

        self.logger.info(
            f"当前Sheet:{state.sheet_name}"
        )

        # ==================================================
        # 数据理解
        # ==================================================

        data_schema = self.data_profiler.analyze(
            state.df
        )

        state.schema = data_schema

        print(
            "\n📚 AI数据理解:"
        )

        print(data_schema)

        # ==================================================
        # 数据画像
        # ==================================================

        state.data_profile = profile_dataframe(
            state.df
        )

        # ==================================================
        # 自动识别字段
        # ==================================================

        columns = detect_columns(
            state.df
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

    # ==================================================
    # 从Excel中自动寻找客户
    # ==================================================

    def find_customer_from_data(
            self,
            state
    ):

        """
        当Planner没有成功提取customer时，
        尝试直接从Excel客户字段中匹配。

        例如：

        用户：
            查询保利长大工程有限公司

        Excel：
            客商名称
            保利长大工程有限公司

        自动得到：

            state.customer = 保利长大工程有限公司
        """

        query = str(
            getattr(
                state,
                "user_query",
                ""
            )
        ).strip()

        if not query:

            return ""

        # ==================================================
        # 优先使用Schema中的customer字段
        # ==================================================

        customer_fields = []

        schema = getattr(
            state,
            "workbook_schema",
            {}
        )

        if isinstance(
            schema,
            dict
        ):

            entities = schema.get(
                "entities",
                {}
            )

            customer_fields = entities.get(
                "customer",
                []
            )

        # ==================================================
        # 如果Schema没有客户字段
        # 使用常见字段名
        # ==================================================

        if not customer_fields:

            customer_fields = [

                "客商名称",
                "集团内/外客商",
                "客户名称",
                "客户"

            ]

        # ==================================================
        # 遍历所有Sheet
        # ==================================================

        sheets = getattr(
            state,
            "sheet_profiles",
            []
        )

        for sheet in sheets:

            df = sheet.get(
                "df"
            )

            if df is None:

                continue

            for field in customer_fields:

                # ------------------------------------------
                # Schema字段可能是：
                #
                # Sheet1.客商名称
                #
                # 这里只取最后的字段名
                # ------------------------------------------

                column = str(
                    field
                ).split(
                    "."
                )[-1]

                if column not in df.columns:

                    continue

                values = (
                    df[column]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                )

                # ==========================================
                # 精确匹配
                # ==========================================

                for value in values:

                    if not value:

                        continue

                    if value in query:

                        return value

        return ""

    # ==================================================
    # 补充Planner参数
    # ==================================================

    def enrich_plan(
            self,
            state
    ):

        """
        对Planner输出进行二次处理。

        主要解决：

        Planner返回：

        [
            {
                "tool": "query_value"
            }
        ]

        但是没有：

            customer
            filters
            metrics

        的情况。
        """

        if not state.plan:

            return

        # ==================================================
        # 只处理第一个任务
        # ==================================================

        task = state.plan[0]

        # ==================================================
        # ① customer
        # ==================================================

        customer = task.get(
            "customer",
            ""
        )

        if not customer:

            customer = self.find_customer_from_data(
                state
            )

            if customer:

                task["customer"] = customer

        # ==================================================
        # ② filters
        # ==================================================

        filters = task.get(
            "filters",
            {}
        )

        if not isinstance(
            filters,
            dict
        ):

            filters = {}

        task["filters"] = filters

        # ==================================================
        # ③ metrics
        # ==================================================

        metrics = task.get(
            "metrics",
            []
        )

        if not isinstance(
            metrics,
            list
        ):

            metrics = []

        task["metrics"] = metrics

        # ==================================================
        # ④ compare
        # ==================================================

        compare = task.get(
            "compare",
            {}
        )

        if not isinstance(
            compare,
            dict
        ):

            compare = {}

        task["compare"] = compare

        # ==================================================
        # 写入State
        # ==================================================

        state.customer = task.get(
            "customer",
            ""
        )

        state.filters = task.get(
            "filters",
            {}
        )

        state.metrics = task.get(
            "metrics",
            []
        )

        state.compare = task.get(
            "compare",
            {}
        )

        # ==================================================
        # 输出调试信息
        # ==================================================

        print(
            "\n========== Planner参数补全 =========="
        )

        print(
            "客户:",
            state.customer
        )

        print(
            "过滤条件:",
            state.filters
        )

        print(
            "指标:",
            state.metrics
        )

        print(
            "比较条件:",
            state.compare
        )

        print(
            "最终任务:",
            state.plan
        )

    # ==================================================
    # 工具执行阶段
    # ==================================================

    def execute_plan(
            self,
            state
    ):

        results = []

        print(
            "\n==========执行计划=========="
        )

        for task in state.plan:

            tool_name = task.get(
                "tool"
            )

            print(
                "执行工具:",
                tool_name
            )

            tool = tool_registry.get_tool(
                tool_name
            )

            if not tool:

                print(
                    "工具不存在:",
                    tool_name
                )

                continue

            try:

                # ==================================================
                # 每次执行工具前，将当前任务参数同步到State
                # ==================================================

                state.customer = task.get(
                    "customer",
                    getattr(
                        state,
                        "customer",
                        ""
                    )
                )

                state.filters = task.get(
                    "filters",
                    getattr(
                        state,
                        "filters",
                        {}
                    )
                )

                state.metrics = task.get(
                    "metrics",
                    getattr(
                        state,
                        "metrics",
                        []
                    )
                )

                state.compare = task.get(
                    "compare",
                    getattr(
                        state,
                        "compare",
                        {}
                    )
                )

                result = tool["function"](
                    state
                )

                results.append(
                    result
                )

                if tool_name in [

                    "query_value",

                    "compare_rows"

                ]:

                    state.query_result = result

                state.trace.add_step(
                    tool_name,
                    "success",
                    "工具执行成功"
                )

            except Exception as e:

                self.logger.error(
                    f"{tool_name}失败:{e}"
                )

                state.trace.add_step(
                    tool_name,
                    "failed",
                    str(e)
                )

                state.error = str(e)

                print(
                    f"❌ {tool_name}执行失败:",
                    e
                )

        return results

    # ==================================================
    # 结果整理
    # ==================================================

    def build_result(
            self,
            state
    ):

        self.analysis_result = {

            "total_count":
                len(state.df),

            "sheet":
                state.sheet_name,

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

    # ==================================================
    # AI分析
    # ==================================================

    def get_ai_insight(
            self
    ):

        result = self.analysis_result.get(
            "query_result",
            {}
        )

        if not result:

            return "没有查询结果"

        rows = (
            result
            .get(
                "data",
                {}
            )
            .get(
                "rows",
                []
            )
        )

        if not rows:

            return "未发现异常数据"

        prompt = f"""

你是一名企业财务分析专家。

以下是不符合条件的数据：

{rows}

请输出：

1. 数据异常分析
2. 潜在风险
3. 处理建议

要求：

只能根据数据分析。
不要编造。
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

    # ==================================================
    # Agent入口
    # ==================================================

    def run(
            self,
            file_path,
            user_query="",
            with_ai=True
    ):

        state = AgentState()

        state.file_path = file_path

        state.user_query = user_query

        # ==================================================
        # 1. 先读取Excel
        # ==================================================

        self.prepare_context(
            state
        )

        # ==================================================
        # 2. Planner
        #
        # 注意：
        # 现在Planner是在Schema准备完成之后运行。
        # ==================================================

        state.plan = self.planner.create_plan(
            user_query
        )

        print(
            "\n🤖 AI Planner计划:"
        )

        print(
            state.plan
        )

        # ==================================================
        # 3. Planner参数补全
        # ==================================================

        self.enrich_plan(
            state
        )

        # ==================================================
        # 4. 执行工具
        # ==================================================

        self.execute_plan(
            state
        )

        # ==================================================
        # 5. 输出结果
        # ==================================================

        result = self.build_result(
            state
        )

        # ==================================================
        # 6. AI分析
        # ==================================================

        if with_ai:

            result["ai_insight"] = (
                self.get_ai_insight()
            )

        return result


# ==========================================================
# 单独测试
# ==========================================================

def main():

    agent = DataAgent()

    result = agent.run(

        DATA_PATH,

        "查保利长大工程有限公司的公路建设期产品运维(JSYW)的本期贷方和贷方累计是否相等"

    )

    print(
        "\n==========分析结果=========="
    )

    print(
        result
    )


if __name__ == "__main__":

    main()