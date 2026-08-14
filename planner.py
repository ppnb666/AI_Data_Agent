"""
LLM Agent任务规划器 V8

职责:

1. 理解用户意图
2. 判断任务类型
3. 选择执行工具
4. 提取客户
5. 提取业务过滤条件
6. 提取比较字段
7. LLM失败时使用规则Fallback

支持:

query_value:
查询数据

compare_rows:
字段比较

aggregate_value:
汇总统计

rank_rows:
排序排名

detect_anomaly:
异常检测
"""

import json
import logging
import re

from tools import tool_registry


class TaskPlanner:

    def __init__(self, llm_client):

        self.llm = llm_client

        self.logger = logging.getLogger(
            __name__
        )

    # ==================================================
    # JSON解析
    # ==================================================

    def parse_json_response(self, response):

        if response is None:

            raise ValueError(
                "LLM返回为空"
            )

        response = str(
            response
        ).strip()

        if not response:

            raise ValueError(
                "LLM返回为空字符串"
            )

        # ---------------------------------------------
        # ① 直接解析
        # ---------------------------------------------

        try:

            return json.loads(
                response
            )

        except json.JSONDecodeError:

            pass

        # ---------------------------------------------
        # ② 去除Markdown代码块
        # ---------------------------------------------

        cleaned = response

        cleaned = cleaned.replace(
            "```json",
            ""
        )

        cleaned = cleaned.replace(
            "```JSON",
            ""
        )

        cleaned = cleaned.replace(
            "```",
            ""
        )

        cleaned = cleaned.strip()

        try:

            return json.loads(
                cleaned
            )

        except json.JSONDecodeError:

            pass

        # ---------------------------------------------
        # ③ 提取JSON数组
        # ---------------------------------------------

        start = cleaned.find(
            "["
        )

        end = cleaned.rfind(
            "]"
        )

        if (
            start != -1
            and end != -1
            and end > start
        ):

            json_text = cleaned[
                start:end + 1
            ]

            try:

                return json.loads(
                    json_text
                )

            except json.JSONDecodeError:

                pass

        # ---------------------------------------------
        # ④ 提取JSON对象
        # ---------------------------------------------

        start = cleaned.find(
            "{"
        )

        end = cleaned.rfind(
            "}"
        )

        if (
            start != -1
            and end != -1
            and end > start
        ):

            json_text = cleaned[
                start:end + 1
            ]

            try:

                return json.loads(
                    json_text
                )

            except json.JSONDecodeError:

                pass

        raise ValueError(
            "无法从LLM返回内容中解析JSON"
        )

    # ==================================================
    # 客户名称提取
    # ==================================================

    def extract_customer(
        self,
        query
    ):

        """
        从用户问题中提取客户名称。

        例如:

        查询保利长大工程有限公司

        返回:

        保利长大工程有限公司
        """

        if not query:

            return ""

        # ---------------------------------------------
        # 第一优先级:
        # 公司名称
        # ---------------------------------------------

        patterns = [

            r"([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,30}(?:有限公司|公司|集团|股份有限公司))",

        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                query
            )

            if match:

                return match.group(
                    1
                ).strip()

        # ---------------------------------------------
        # 第二优先级:
        # 查询 + 名称
        # ---------------------------------------------

        text = query

        prefixes = [

            "查询",
            "查询一下",
            "查一下",
            "查",
            "查看",
            "获取",
            "分析",
            "统计"

        ]

        for prefix in prefixes:

            if text.startswith(
                prefix
            ):

                text = text[
                    len(prefix):
                ]

                break

        # 去掉常见连接词

        text = re.split(
            r"(的|本期|期末|期初|业务类型|业务种类|金额|余额|是否|比较|大于|小于)",
            text
        )[0]

        text = text.strip()

        return text

    # ==================================================
    # 业务过滤条件提取
    # ==================================================

    def extract_filters(
        self,
        query
    ):

        """
        提取业务类型等过滤条件。

        例如:

        查询保利长大工程有限公司的
        公路建设期产品运维(JSYW)

        返回:

        {
            "业务类型（新）":
            "公路建设期产品运维(JSYW)"
        }
        """

        filters = {}

        if not query:

            return filters

        # ---------------------------------------------
        # 业务类型（新）
        # ---------------------------------------------

        match = re.search(
            r"(公路建设期产品运维\(JSYW\))",
            query
        )

        if match:

            filters[
                "业务类型（新）"
            ] = match.group(
                1
            )

        # ---------------------------------------------
        # 更通用:
        # "业务类型（新）: xxx"
        # ---------------------------------------------

        match = re.search(
            r"业务类型（新）\s*[:：]\s*([^，,。；;\n]+)",
            query
        )

        if match:

            filters[
                "业务类型（新）"
            ] = match.group(
                1
            ).strip()

        # ---------------------------------------------
        # 业务类型
        # ---------------------------------------------

        match = re.search(
            r"业务类型\s*[:：]\s*([^，,。；;\n]+)",
            query
        )

        if match:

            filters[
                "业务类型"
            ] = match.group(
                1
            ).strip()

        # ---------------------------------------------
        # 业务种类
        # ---------------------------------------------

        match = re.search(
            r"业务种类\s*[:：]\s*([^，,。；;\n]+)",
            query
        )

        if match:

            filters[
                "业务种类"
            ] = match.group(
                1
            ).strip()

        return filters

    # ==================================================
    # 比较条件提取
    # ==================================================

    def extract_compare(
        self,
        query
    ):

        """
        提取字段比较条件。

        例如:

        本期贷方和贷方累计是否相等

        返回:

        {
            "left": "本期贷方",
            "right": "贷方累计",
            "operator": "=="
        }
        """

        if not query:

            return {}

        # ---------------------------------------------
        # 字段名称
        # ---------------------------------------------

        left = None
        right = None

        if (
            "本期贷方" in query
            and "贷方累计" in query
        ):

            left = "本期贷方"

            right = "贷方累计"

        elif (
            "期初余额" in query
            and "期末余额" in query
        ):

            left = "期初余额"

            right = "期末余额"

        elif (
            "本期贷方" in query
            and "期末余额" in query
        ):

            left = "本期贷方"

            right = "期末余额"

        # 如果没有找到两个字段

        if not left or not right:

            return {}

        # ---------------------------------------------
        # 运算符
        # ---------------------------------------------

        if any(
            word in query
            for word in [
                "是否相等",
                "相等",
                "一致",
                "相同",
                "一样",
                "等于"
            ]
        ):

            operator = "=="

        elif any(
            word in query
            for word in [
                "不相等",
                "不一致",
                "不同",
                "有差别",
                "差异"
            ]
        ):

            operator = "!="

        elif any(
            word in query
            for word in [
                "不少于",
                "至少",
                "大于等于"
            ]
        ):

            operator = ">="

        elif any(
            word in query
            for word in [
                "不超过",
                "最多",
                "小于等于"
            ]
        ):

            operator = "<="

        elif any(
            word in query
            for word in [
                "大于",
                "超过",
                "高于"
            ]
        ):

            operator = ">"

        elif any(
            word in query
            for word in [
                "小于",
                "低于"
            ]
        ):

            operator = "<"

        else:

            return {}

        return {

            "left":
            left,

            "right":
            right,

            "operator":
            operator

        }

    # ==================================================
    # 创建任务计划
    # ==================================================

    def create_plan(
        self,
        user_query: str
    ):

        tools = tool_registry.list_tools()

        prompt = f"""

你是企业级AI数据分析Agent规划器。

根据用户自然语言需求生成执行计划。

======================

可用工具:

{tools}

======================

【任务分类】

普通查询:

查询、查、查看、多少、余额、金额

使用:

query_value


字段比较:

比较、是否相等、是否一致、相同、一样、
不相等、不同、差异、大于、超过、高于、
小于、低于、不少于、不超过

使用:

compare_rows


汇总:

合计、总额、统计、汇总

使用:

aggregate_value


排名:

最高、最低、排名、TOP

使用:

rank_rows


异常:

异常、波动、异常数据

使用:

detect_anomaly


======================

【客户提取规则】

必须完整提取客户名称。

例如:

用户:

查询保利长大工程有限公司

必须返回:

"customer":"保利长大工程有限公司"

禁止返回:

"保利长大"


======================

【过滤条件】

如果用户指定业务条件，必须放入filters。

例如:

业务类型（新）:
公路建设期产品运维(JSYW)

返回:

"filters":
{{
    "业务类型（新）":
    "公路建设期产品运维(JSYW)"
}}


======================

【比较格式】

必须返回:

"compare":
{{
    "left":"字段1",
    "right":"字段2或者数字",
    "operator":"运算符"
}}


相等:

"=="


不相等:

"!="


大于:

">"


小于:

"<"


大于等于:

">="


小于等于:

"<="


======================

【重要】

即使用户只说:

查询保利长大工程有限公司

也必须生成有效任务。

不能返回空数组。

======================

【输出格式】

只能返回JSON数组。

禁止解释。

格式:

[
{{
    "tool":"",
    "reason":"",
    "customer":"",
    "metrics":[],
    "filters":{{}},
    "compare":{{}},
    "condition":{{}},
    "output":"rows"
}}
]

======================

用户需求:

{user_query}

"""

        messages = [

            {
                "role":
                "system",

                "content":
                """
你是企业数据Agent规划器。

必须严格返回JSON数组。

不能返回空数组。

必须提取用户问题中的客户名称。
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

            plan = self.parse_json_response(
                response
            )

            if not isinstance(
                plan,
                list
            ):

                raise ValueError(
                    "Planner返回的不是JSON数组"
                )

            valid = []

            for task in plan:

                if not isinstance(
                    task,
                    dict
                ):

                    continue

                tool = task.get(
                    "tool"
                )

                if tool not in tools:

                    print(
                        "忽略不存在工具:",
                        tool
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
                        ),

                        "compare":
                        task.get(
                            "compare",
                            {}
                        ),

                        "condition":
                        task.get(
                            "condition",
                            {}
                        ),

                        "output":
                        task.get(
                            "output",
                            "rows"
                        )
                    }

                )

            # ==========================================
            # 关键修复
            # ==========================================

            if not valid:

                raise ValueError(
                    "Planner没有生成有效任务"
                )

            # ==========================================
            # 对LLM结果进行补全
            #
            # 防止LLM返回:
            #
            # {
            #   "tool":"query_value"
            # }
            #
            # 但是没有customer
            # ==========================================

            for task in valid:

                if not task.get(
                    "customer"
                ):

                    task["customer"] = (
                        self.extract_customer(
                            user_query
                        )
                    )

                if not task.get(
                    "filters"
                ):

                    task["filters"] = (
                        self.extract_filters(
                            user_query
                        )
                    )

                if (
                    task["tool"]
                    == "compare_rows"
                ):

                    compare = task.get(
                        "compare",
                        {}
                    )

                    if not compare.get(
                        "left"
                    ):

                        compare = (
                            self.extract_compare(
                                user_query
                            )
                        )

                    task["compare"] = (
                        compare
                    )

            print(
                "\n===== V8 Planner计划 ====="
            )

            print(valid)

            return valid

        except Exception as e:

            self.logger.error(
                f"Planner失败:{e}"
            )

            print(
                "Planner失败:",
                e
            )

            return self.fallback_plan(
                user_query
            )

    # ==================================================
    # Fallback
    # ==================================================

    def fallback_plan(
        self,
        query
    ):

        """
        LLM失败时的本地规则规划器。

        重点:

        即使DeepSeek返回 []

        也可以继续完成基本查询。
        """

        customer = (
            self.extract_customer(
                query
            )
        )

        filters = (
            self.extract_filters(
                query
            )
        )

        compare = (
            self.extract_compare(
                query
            )
        )

        # ==================================================
        # ① 比较任务
        # ==================================================

        if compare:

            return [

                {
                    "tool":
                    "compare_rows",

                    "reason":
                    "LLM失败，使用本地规则识别比较任务",

                    "customer":
                    customer,

                    "metrics":
                    [],

                    "filters":
                    filters,

                    "compare":
                    compare,

                    "condition":
                    {},

                    "output":
                    "rows"
                }

            ]

        # ==================================================
        # ② 汇总任务
        # ==================================================

        if any(
            keyword in query
            for keyword in [
                "合计",
                "总额",
                "统计",
                "汇总"
            ]
        ):

            return [

                {
                    "tool":
                    "aggregate_value",

                    "reason":
                    "LLM失败，使用关键词判断汇总任务",

                    "customer":
                    customer,

                    "metrics":
                    [],

                    "filters":
                    filters,

                    "compare":
                    {},

                    "condition":
                    {},

                    "output":
                    "summary"
                }

            ]

        # ==================================================
        # ③ 排名任务
        # ==================================================

        if any(
            keyword in query
            for keyword in [
                "最高",
                "最低",
                "排名",
                "TOP"
            ]
        ):

            return [

                {
                    "tool":
                    "rank_rows",

                    "reason":
                    "LLM失败，使用关键词判断排名任务",

                    "customer":
                    customer,

                    "metrics":
                    [],

                    "filters":
                    filters,

                    "compare":
                    {},

                    "condition":
                    {},

                    "output":
                    "rows"
                }

            ]

        # ==================================================
        # ④ 异常检测
        # ==================================================

        if any(
            keyword in query
            for keyword in [
                "异常",
                "波动",
                "异常数据"
            ]
        ):

            return [

                {
                    "tool":
                    "detect_anomaly",

                    "reason":
                    "LLM失败，使用关键词判断异常任务",

                    "customer":
                    customer,

                    "metrics":
                    [],

                    "filters":
                    filters,

                    "compare":
                    {},

                    "condition":
                    {},

                    "output":
                    "rows"
                }

            ]

        # ==================================================
        # ⑤ 普通查询
        # ==================================================

        return [

            {
                "tool":
                "query_value",

                "reason":
                "LLM失败，使用本地规则判断普通查询",

                "customer":
                customer,

                "metrics":
                [],

                "filters":
                filters,

                "compare":
                {},

                "condition":
                {},

                "output":
                "rows"
            }

        ]