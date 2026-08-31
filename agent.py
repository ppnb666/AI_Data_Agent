"""
AI Data Agent

LLM Planner + Schema Agent + Tool Registry
"""
from typing import Optional, Dict
from state import AgentState

from utils.logger import get_logger

from config import DATA_PATH

from tools import tool_registry

from tools.field_resolver import resolve_field

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
        """
        数据准备阶段（修复：此前此方法体内嵌套定义了一个同名的
        内部 prepare_context 函数，导致清洗逻辑从未被执行。
        现在合并为单一版本，清洗步骤真正生效。）
        """

        self.logger.info(
            f"读取数据文件:{state.file_path}"
        )

        from utils.data_loader import load_file

        sheets = load_file(
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
            sheets,
            user_query=getattr(
                state,
                "user_query",
                ""
            ),
            mapping=getattr(
                state,
                "mapping",
                {}
            )
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
            state.user_query,
            schema=schema
        )

        if not selected:

            selected = sheets[0]

        state.df = selected["df"]

        state.sheet_name = selected["sheet"]

        self.logger.info(
            f"当前Sheet:{state.sheet_name}"
        )

        # ==================================================
        # 数据理解（DataProfiler分析）
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
        # 获取清洗建议并执行（修复：此前被困在一个从未被调用的
        # 内部函数里，现在提到外层，真正会被执行）
        # ==================================================

        quality_report = data_schema.get("quality_report", {})
        clean_suggestions = data_schema.get("clean_suggestions", {})

        state.data_quality_report = quality_report
        state.clean_suggestions = clean_suggestions

        overall_score = quality_report.get("overall_score", 100)

        if overall_score < 80:
            print(f"\n🧹 数据质量评分: {overall_score}，自动执行清洗...")
            state.df = DataProfilerAgent.apply_clean_suggestions(
                state.df,
                clean_suggestions
            )
            print(f"   清洗后数据: {len(state.df)} 行")
        else:
            print(f"\n✅ 数据质量评分: {overall_score}，质量良好，无需清洗")

        # ==================================================
        # 数据画像
        # ==================================================

        state.data_profile = profile_dataframe(
            state.df
        )

        # ==================================================
        # 构造 Schema 摘要（供 Planner 选择真实存在的指标）
        # ==================================================

        state.schema_summary = self.build_schema_summary(
            state
        )

    # ==================================================
    # 构造 Schema 摘要（Planner 动态指标的唯一输入）
    # ==================================================

    def build_schema_summary(self, state):
        """
        从 workbook_schema 的 roles（唯一事实来源）构造：
        {
            "sheets": [...],
            "metric_fields": ["期末余额", ...],   # amount + number
            "dimension_fields": {"customer": [...], ...},
            "samples": {"列名": ["样本1", "样本2"]}
        }
        """
        schema = getattr(
            state,
            "workbook_schema",
            {}
        )

        if not schema:
            return None

        roles = schema.get(
            "roles",
            {}
        )

        metric_fields = list(
            roles.get("amount", [])
        ) + list(
            roles.get("number", [])
        )

        # 指标字段去 Sheet 前缀 + 去重
        metric_fields = list(
            dict.fromkeys(
                str(f).split(".", 1)[-1]
                for f in metric_fields
            )
        )

        dimension_roles = [
            "customer", "business", "product", "department",
            "project", "region", "person", "category",
        ]

        dimension_fields = {}

        for role in dimension_roles:

            fields = [
                str(f).split(".", 1)[-1]
                for f in roles.get(role, [])
            ]

            if fields:
                dimension_fields[role] = fields

        # 每列 2 个样本
        samples = {}

        for field, info in schema.get(
            "fields",
            {}
        ).items():

            col = info.get("column", "")

            if col:
                samples[col] = (
                    info.get("sample_values", [])[:2]
                )

        return {
            "sheets": schema.get("sheets", []),
            "metric_fields": metric_fields,
            "dimension_fields": dimension_fields,
            "samples": samples,
        }

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
        # 遍历所有Sheet，通过 field_resolver 找客户字段
        # （mapping → schema.roles → 关键词兜底，含 person
        # 姓名列兜底，任意行业都能命中）
        # ==================================================

        schema = getattr(
            state,
            "workbook_schema",
            {}
        )

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

            columns = list(
                df.columns
            )

            field = resolve_field(
                state,
                schema,
                columns,
                "customer"
            )

            if not field:

                continue

            if field not in df.columns:

                continue

            values = (
                df[field]
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
                # 【修复】同时把当前task本身也存到state.current_task，
                # 这样像rank_rows_tool这类工具就能直接读取当前正在
                # 执行的任务，而不用回头去state.plan里按tool名字
                # 搜索——避免一次plan里有多个同类型任务时只处理到
                # 第一个的问题。
                # ==================================================

                state.current_task = task

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

                    "compare_rows",

                    "rank_rows",

                    "aggregate_value",

                    "detect_anomaly",

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

    def get_ai_insight(self, state=None):
        """根据查询结果生成AI分析报告（通用化，不绑定任何行业）"""
        result = self.analysis_result.get("query_result", {})
        if not result:
            return "没有查询结果"

        result_type = result.get("type")

        # 排名分组字段：优先取 schema 的 customer 角色列，
        # 其次 business/product/department/project，最后"分组"
        dimension_cols = ["分组"]
        if state is not None:
            schema = getattr(state, "workbook_schema", {}) or {}
            roles = schema.get("roles", {}) or {}
            for role in (
                "customer", "business", "product",
                "department", "project",
            ):
                for field in roles.get(role, []):
                    col = str(field).split(".", 1)[-1]
                    if col not in dimension_cols:
                        dimension_cols.append(col)

        def _pick_name(row, i):
            """从结果行中提取分组/实体名称"""
            for col in dimension_cols:
                value = row.get(col)
                if value not in (None, ""):
                    return str(value)
            # 未知维度：取第一个非指标键
            for key, value in row.items():
                if key in ("排名", "来源Sheet", "指标"):
                    continue
                if not isinstance(value, (int, float)):
                    return str(value)
            return f"第{i}名"

        # ==========================================================
        # 1. 排名结果 → 表现分析
        # ==========================================================
        if result_type == "rank_rows":
            rows = result.get("data", {}).get("rows", [])
            if not rows:
                return "没有排名数据"

            metric = result.get("metric", "指标")
            # 构建排名摘要
            summary = f"按 {metric} 排名前 {len(rows)} 的数据主体：\n"
            for i, row in enumerate(rows, 1):
                name = _pick_name(row, i)
                value = row.get(metric, 0)
                summary += f"{i}. {name}：{metric} = {value:,.2f}\n"

            # 统计信息
            total = result.get("total_count", 0)
            summary += f"\n共 {total} 个数据主体参与排名。"

            prompt = f"""
    你是一名资深数据分析师。请根据以下排名数据，分析表现最好的数据主体，并给出理由。

    数据：
    {summary}

    请输出（请聚焦于数据分析，不要过度解读数据格式问题）：
    1. 表现最好的数据主体是哪个？为什么？
    2. 该主体的核心优势是什么？
    3. 前3名主体的简要对比分析
    4. 潜在的关注点或建议
    """
            return self.llm.chat([
                {"role": "system", "content": "你是一名资深数据分析师，擅长从数据中洞察规律与差异。"},
                {"role": "user", "content": prompt}
            ])

        # ==========================================================
        # 2. 比较结果 → 差异分析
        # ==========================================================
        if result_type == "compare_rows":
            rows = result.get("data", {}).get("rows", [])
            if not rows:
                return "未发现异常数据"

            prompt = f"""
    你是一名资深数据分析师。

    以下是不符合条件的数据：
    {rows}

    请输出：
    1. 数据差异分析
    2. 潜在风险
    3. 处理建议

    要求：只能根据数据分析，不要编造。
    """
            return self.llm.chat([
                {"role": "system", "content": "资深数据分析助手"},
                {"role": "user", "content": prompt}
            ])

        # ==========================================================
        # 3. 查询结果 → 数据摘要
        # ==========================================================
        if result_type == "query_value":
            rows = result.get("data", {}).get("rows", [])
            if not rows:
                return "没有查询到数据"

            # 简单摘要
            total_count = result.get("total_count", 0)
            summary = f"共查询到 {total_count} 条记录。\n"
            # 显示前5条
            for i, row in enumerate(rows[:5], 1):
                summary += f"第{i}条: {row}\n"
            if len(rows) > 5:
                summary += f"... 还有 {len(rows) - 5} 条"

            prompt = f"""
    请根据以下查询结果，生成简洁的数据摘要：
    {summary}

    输出要求：
    1. 数据概览
    2. 关键发现
    3. 建议
    """
            return self.llm.chat([
                {"role": "system", "content": "数据摘要助手"},
                {"role": "user", "content": prompt}
            ])

        # ==========================================================
        # 4. 未知类型
        # ==========================================================
        return "暂不支持该类型结果的AI分析"
    # ==================================================
    # Agent入口
    # ==================================================

    # agent.py 中修改
    def run(
            self,
            file_path,
            user_query="",
            with_ai=True,
            mapping: Optional[Dict[str, str]] = None  # 新增
    ):
        state = AgentState()
        state.file_path = file_path
        state.user_query = user_query
        state.mapping = mapping or {}  # 新增字段（需在state.py中定义）
        # ... 其余不变

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
            user_query,
            schema_summary=getattr(
                state,
                "schema_summary",
                None
            )
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
                self.get_ai_insight(state)
            )

        return result


# ==========================================================
# 单独测试
# ==========================================================

if __name__ == "__main__":

    agent = DataAgent()

    result = agent.run(

        DATA_PATH,

        "查询数据概况"

    )

    print(
        "\n==========分析结果=========="
    )

    print(
        result
    )