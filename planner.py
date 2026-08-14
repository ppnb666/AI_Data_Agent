"""
LLM Agent任务规划器 V9

职责：

1. 理解用户自然语言需求
2. 判断任务类型
3. 选择执行工具
4. 提取客户
5. 提取业务条件
6. 提取指标字段
7. 提取比较条件
8. 提取统计条件
9. 提取排序/排名条件

设计原则：

Planner只负责理解用户语言。

Planner不负责：

1. 读取Excel
2. 判断Excel有哪些Sheet
3. 判断Excel有哪些字段
4. 判断哪个Sheet包含哪个字段
5. 将业务概念强制映射为Excel字段

例如：

用户：

查询保利长大工程有限公司的公路建设期产品运维(JSYW)

Planner应该返回：

{
    "customer": "保利长大工程有限公司",
    "filters": {
        "业务条件": "公路建设期产品运维(JSYW)"
    }
}

而不是：

{
    "filters": {
        "业务类型（新）": "公路建设期产品运维(JSYW)"
    }

真正的Excel字段映射：

由后续Schema Agent完成。
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

    # ==========================================================
    # JSON解析
    # ==========================================================

    def parse_json_response(self, response):
        """
        从LLM返回内容中提取JSON。

        支持：

        1. 纯JSON
        2. Markdown代码块
        3. JSON数组
        4. JSON对象
        5. 前后存在说明文字
        """

        if response is None:
            raise ValueError(
                "LLM返回为空"
            )

        response = str(response).strip()

        if not response:
            raise ValueError(
                "LLM返回为空字符串"
            )

        # ------------------------------------------------------
        # ① 直接解析
        # ------------------------------------------------------

        try:
            return json.loads(response)

        except json.JSONDecodeError:
            pass

        # ------------------------------------------------------
        # ② 清理Markdown代码块
        # ------------------------------------------------------

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
            return json.loads(cleaned)

        except json.JSONDecodeError:
            pass

        # ------------------------------------------------------
        # ③ 提取JSON数组
        # ------------------------------------------------------

        start = cleaned.find("[")

        end = cleaned.rfind("]")

        if (
            start != -1
            and end != -1
            and end > start
        ):

            json_text = cleaned[
                start:end + 1
            ]

            try:
                return json.loads(json_text)

            except json.JSONDecodeError:
                pass

        # ------------------------------------------------------
        # ④ 提取JSON对象
        # ------------------------------------------------------

        start = cleaned.find("{")

        end = cleaned.rfind("}")

        if (
            start != -1
            and end != -1
            and end > start
        ):

            json_text = cleaned[
                start:end + 1
            ]

            try:
                return json.loads(json_text)

            except json.JSONDecodeError:
                pass

        raise ValueError(
            "无法从LLM返回内容中解析JSON"
        )

    # ==========================================================
    # 标准化字符串
    # ==========================================================

    def normalize_string(self, value):
        """
        标准化字符串。
        """

        if value is None:
            return ""

        if not isinstance(value, str):
            return value

        return value.strip()

    # ==========================================================
    # 标准化metrics
    # ==========================================================

    def normalize_metrics(self, metrics):
        """
        确保metrics最终一定是list。

        Planner不允许擅自创造Excel字段。

        例如：

        "销售额"
        ->
        ["销售额"]

        None
        ->
        []

        "销售数据"
        ->
        ["销售数据"]

        但是否是真正Excel字段，
        由Schema Agent后续判断。
        """

        if metrics is None:
            return []

        if isinstance(metrics, str):

            metrics = metrics.strip()

            if not metrics:
                return []

            return [metrics]

        if not isinstance(metrics, list):
            return []

        result = []

        for item in metrics:

            if item is None:
                continue

            item = str(item).strip()

            if not item:
                continue

            if item not in result:
                result.append(item)

        return result

    # ==========================================================
    # 标准化filters
    # ==========================================================

    def normalize_filters(self, filters):
        """
        标准化filters。

        注意：

        不改变用户表达的业务条件。

        Planner不会将：

        公路建设期产品运维(JSYW)

        自动转换成：

        业务类型（新）

        """

        if filters is None:
            return {}

        if not isinstance(filters, dict):
            return {}

        result = {}

        for key, value in filters.items():

            if key is None:
                continue

            key = str(key).strip()

            if not key:
                continue

            if value is None:
                continue

            if isinstance(value, str):

                value = value.strip()

                if not value:
                    continue

            result[key] = value

        return result

    # ==========================================================
    # 标准化compare
    # ==========================================================

    def normalize_compare(self, compare):
        """
        标准化比较条件。

        标准格式：

        {
            "left": "",
            "right": "",
            "operator": ""
        }
        """

        if compare is None:
            return {}

        if not isinstance(compare, dict):
            return {}

        left = compare.get(
            "left",
            ""
        )

        right = compare.get(
            "right",
            ""
        )

        operator = compare.get(
            "operator",
            ""
        )

        if left is None:
            left = ""

        if right is None:
            right = ""

        if operator is None:
            operator = ""

        left = str(left).strip()

        right = str(right).strip()

        operator = str(operator).strip()

        valid_operators = [
            "==",
            "!=",
            ">",
            "<",
            ">=",
            "<="
        ]

        if operator not in valid_operators:

            operator = ""

        if not left and not right and not operator:
            return {}

        return {
            "left": left,
            "right": right,
            "operator": operator
        }

    # ==========================================================
    # 标准化condition
    # ==========================================================

    def normalize_condition(self, condition):
        """
        标准化统计/排序等附加条件。

        Planner不强制具体结构。

        例如：

        {
            "limit": 10,
            "order": "desc"
        }

        """

        if condition is None:
            return {}

        if not isinstance(condition, dict):
            return {}

        return condition

    # ==========================================================
    # 标准化单个任务
    # ==========================================================

    def normalize_task(
        self,
        task,
        tools
    ):
        """
        对LLM生成的单个任务进行标准化。
        """

        if not isinstance(task, dict):
            return None

        tool = task.get(
            "tool",
            ""
        )

        if not isinstance(tool, str):
            return None

        tool = tool.strip()

        # ------------------------------------------------------
        # 工具存在性检查
        # ------------------------------------------------------

        if tool not in tools:

            print(
                "忽略不存在工具:",
                tool
            )

            return None

        # ------------------------------------------------------
        # reason
        # ------------------------------------------------------

        reason = task.get(
            "reason",
            ""
        )

        reason = self.normalize_string(
            reason
        )

        # ------------------------------------------------------
        # customer
        # ------------------------------------------------------

        customer = task.get(
            "customer",
            ""
        )

        customer = self.normalize_string(
            customer
        )

        # ------------------------------------------------------
        # metrics
        # ------------------------------------------------------

        metrics = self.normalize_metrics(
            task.get(
                "metrics",
                []
            )
        )

        # ------------------------------------------------------
        # filters
        # ------------------------------------------------------

        filters = self.normalize_filters(
            task.get(
                "filters",
                {}
            )
        )

        # ------------------------------------------------------
        # compare
        # ------------------------------------------------------

        compare = self.normalize_compare(
            task.get(
                "compare",
                {}
            )
        )

        # ------------------------------------------------------
        # condition
        # ------------------------------------------------------

        condition = self.normalize_condition(
            task.get(
                "condition",
                {}
            )
        )

        # ------------------------------------------------------
        # output
        # ------------------------------------------------------

        output = task.get(
            "output",
            "rows"
        )

        if output is None:
            output = "rows"

        output = str(output).strip()

        if not output:
            output = "rows"

        # ------------------------------------------------------
        # 最终任务
        # ------------------------------------------------------

        return {
            "tool": tool,
            "reason": reason,
            "customer": customer,
            "metrics": metrics,
            "filters": filters,
            "compare": compare,
            "condition": condition,
            "output": output
        }

    # ==========================================================
    # 创建Planner Prompt
    # ==========================================================

    def build_prompt(
        self,
        user_query,
        tools
    ):
        """
        构造Planner Prompt。
        """

        prompt = f"""
你是一个企业级AI数据分析Agent的任务规划器。

你的任务是：

理解用户的自然语言需求，
提取用户真正想执行的数据分析任务，
并生成标准JSON任务计划。

==================================================
一、核心职责
==================================================

你只负责：

1. 理解用户意图
2. 判断任务类型
3. 选择执行工具
4. 提取客户
5. 提取业务条件
6. 提取用户明确要求的指标
7. 提取比较条件
8. 提取统计条件
9. 提取排序/排名条件

==================================================
二、绝对禁止事项
==================================================

你不负责：

1. 读取Excel
2. 读取CSV
3. 判断Excel有哪些Sheet
4. 判断Excel有哪些字段
5. 猜测字段属于哪个Sheet
6. 将业务概念强制映射成Excel字段
7. 根据经验创造不存在的Excel字段

尤其注意：

【不要把用户业务语言直接转换成Excel字段】

例如：

用户：

查询保利长大工程有限公司的公路建设期产品运维(JSYW)

正确：

"filters": {{
    "业务条件": "公路建设期产品运维(JSYW)"
}}

错误：

"filters": {{
    "业务类型（新）": "公路建设期产品运维(JSYW)"
}}

因为Planner没有看到Excel Schema。

真正的字段映射交给Schema Agent。

==================================================
三、可用工具
==================================================

{tools}

只能选择上述工具。

如果工具不存在：

不要创造新工具。

==================================================
四、任务类型
==================================================

------------------------------
1. 普通查询
------------------------------

用户表达：

查询
查
查看
寻找
看看
多少
有哪些
明细
数据
信息

使用：

query_value

------------------------------
2. 字段比较
------------------------------

用户表达：

比较
是否相等
是否一致
相等
一样
相同
不同
不相等
差异
大于
超过
高于
小于
低于
不少于
至少
不超过
最多

使用：

compare_rows

------------------------------
3. 汇总统计
------------------------------

用户表达：

合计
总额
总计
统计
汇总
求和
加总

使用：

aggregate_value

------------------------------
4. 排名
------------------------------

用户表达：

最高
最低
最大
最小
排名
TOP
top
前几
前十
前五
前三

使用：

rank_rows

------------------------------
5. 异常检测
------------------------------

用户表达：

异常
异常数据
波动
异常波动
风险数据
异常值

使用：

detect_anomaly

==================================================
五、客户提取
==================================================

如果用户明确提到：

客户
公司
客商
企业

必须完整保留。

例如：

用户：

查询保利长大工程有限公司

必须：

"customer": "保利长大工程有限公司"

不能：

"customer": "保利长大"

如果没有明确客户：

"customer": ""

不要猜测。

==================================================
六、业务条件提取
==================================================

用户表达的业务条件必须保留。

例如：

查询A公司的公路建设业务

返回：

"filters": {{
    "业务条件": "公路建设业务"
}}

例如：

查询A公司的JSYW业务

返回：

"filters": {{
    "业务条件": "JSYW"
}}

例如：

查询A公司的某项目

返回：

"filters": {{
    "项目": "某项目"
}}

例如：

查询A公司的某产品

返回：

"filters": {{
    "产品": "某产品"
}}

例如：

查询A公司的某部门数据

返回：

"filters": {{
    "部门": "某部门"
}}

例如：

查询A公司2025年的数据

返回：

"filters": {{
    "时间": "2025"
}}

==================================================
七、非常重要：用户明确字段名
==================================================

如果用户自己明确说出了字段名称：

例如：

业务类型是公路建设期产品运维(JSYW)

那么可以：

"filters": {{
    "业务类型": "公路建设期产品运维(JSYW)"
}}

因为：

【字段名称来自用户】

而不是Planner自己猜测。

再例如：

用户：

部门是华南事业部

返回：

"filters": {{
    "部门": "华南事业部"
}}

用户：

项目名称是A项目

返回：

"filters": {{
    "项目名称": "A项目"
}}

==================================================
八、指标提取
==================================================

只有用户明确要求某个指标时，
才放入metrics。

例如：

查询A公司的销售额

返回：

"metrics": [
    "销售额"
]

例如：

查询A公司的期末余额

返回：

"metrics": [
    "期末余额"
]

例如：

查询A公司的本期贷方和贷方累计

返回：

"metrics": [
    "本期贷方",
    "贷方累计"
]

例如：

查询A公司的金额

返回：

"metrics": [
    "金额"
]

==================================================
九、禁止猜测指标
==================================================

如果用户只说：

查询A公司的数据

不要生成：

"销售额"

不要生成：

"金额"

不要生成：

"期末余额"

应该：

"metrics": []

==================================================
十、模糊业务词处理
==================================================

以下表达通常属于业务概念，
不要擅自转换成Excel字段：

销售数据
业务数据
经营情况
经营数据
财务情况
项目情况
合同情况
客户情况
业务情况

例如：

用户：

查询华为2025年的销售数据

可以：

"customer": "华为"

"filters": {{
    "时间": "2025"
}}

"metrics": []

因为“销售数据”不是明确字段。

==================================================
十一、比较条件
==================================================

如果工具是：

compare_rows

必须提取：

"compare"

格式：

"compare": {{
    "left": "字段1",
    "right": "字段2或者数字",
    "operator": "运算符"
}}

--------------------------------------------------
相等
--------------------------------------------------

是否相等
等于
一致
相同
一样

使用：

"=="

--------------------------------------------------
不相等
--------------------------------------------------

不相等
不同
不一致
差异
有差别

使用：

"!="

--------------------------------------------------
大于
--------------------------------------------------

大于
超过
高于

使用：

">"

--------------------------------------------------
小于
--------------------------------------------------

小于
低于

使用：

"<"

--------------------------------------------------
不少于
--------------------------------------------------

不少于
至少
不低于

使用：

">="

--------------------------------------------------
不超过
--------------------------------------------------

不超过
最多
不高于

使用：

"<="

==================================================
十二、比较示例
==================================================

用户：

查询A公司本期贷方和贷方累计是否相等

返回：

[
{{
    "tool": "compare_rows",
    "reason": "比较两个指标是否相等",
    "customer": "A公司",
    "metrics": [
        "本期贷方",
        "贷方累计"
    ],
    "filters": {{}},
    "compare": {{
        "left": "本期贷方",
        "right": "贷方累计",
        "operator": "=="
    }},
    "condition": {{}},
    "output": "rows"
}}
]

==================================================
十三、数字比较
==================================================

用户：

查询A公司期末余额大于100万的数据

返回：

[
{{
    "tool": "compare_rows",
    "reason": "查询指定客户期末余额大于100万的数据",
    "customer": "A公司",
    "metrics": [
        "期末余额"
    ],
    "filters": {{}},
    "compare": {{
        "left": "期末余额",
        "right": "100万",
        "operator": ">"
    }},
    "condition": {{}},
    "output": "rows"
}}
]

注意：

"100万"

必须保留用户原始表达。

不要在Planner阶段转换成：

1000000

单位转换交给后续执行层。

==================================================
十四、业务条件 + 比较条件
==================================================

用户：

查保利长大工程有限公司的公路建设期产品运维(JSYW)的本期贷方和贷方累计是否相等

返回：

[
{{
    "tool": "compare_rows",
    "reason": "比较指定业务条件下的两个金额字段",
    "customer": "保利长大工程有限公司",
    "metrics": [
        "本期贷方",
        "贷方累计"
    ],
    "filters": {{
        "业务条件": "公路建设期产品运维(JSYW)"
    }},
    "compare": {{
        "left": "本期贷方",
        "right": "贷方累计",
        "operator": "=="
    }},
    "condition": {{}},
    "output": "rows"
}}
]

再次强调：

不要把：

公路建设期产品运维(JSYW)

转换成：

业务类型（新）

==================================================
十五、多个业务条件
==================================================

如果用户明确提供多个条件：

查询A公司2025年华南事业部的数据

返回：

"filters": {{
    "时间": "2025",
    "部门": "华南事业部"
}}

如果用户说：

A公司的公路建设业务中2025年的数据

返回：

"filters": {{
    "业务条件": "公路建设业务",
    "时间": "2025"
}}

==================================================
十六、汇总统计
==================================================

如果用户表达：

总额
合计
总计
求和
汇总

使用：

aggregate_value

例如：

查询A公司的期末余额总额

返回：

[
{{
    "tool": "aggregate_value",
    "reason": "汇总指定客户的期末余额",
    "customer": "A公司",
    "metrics": [
        "期末余额"
    ],
    "filters": {{}},
    "compare": {{}},
    "condition": {{
        "aggregation": "sum"
    }},
    "output": "value"
}}
]

==================================================
十七、排名
==================================================

如果用户表达：

最高
最低
最大
最小
排名
TOP
前十
前三

使用：

rank_rows

例如：

查询销售额最高的前10个客户

返回：

[
{{
    "tool": "rank_rows",
    "reason": "查询销售额最高的前10个客户",
    "customer": "",
    "metrics": [
        "销售额"
    ],
    "filters": {{}},
    "compare": {{}},
    "condition": {{
        "order": "desc",
        "limit": 10
    }},
    "output": "rows"
}}
]

==================================================
十八、异常检测
==================================================

如果用户表达：

异常
异常数据
异常波动
风险数据

使用：

detect_anomaly

例如：

查询A公司的异常销售数据

返回：

[
{{
    "tool": "detect_anomaly",
    "reason": "检测指定客户的异常销售数据",
    "customer": "A公司",
    "metrics": [
        "销售数据"
    ],
    "filters": {{}},
    "compare": {{}},
    "condition": {{}},
    "output": "rows"
}}
]

如果“销售数据”只是业务概念，
也可以：

"metrics": []

不要为了填字段而猜测。

==================================================
十九、多个任务
==================================================

如果用户一次提出多个明确且相互独立的任务：

例如：

查询A公司的数据，并统计B公司的销售额总和

可以返回：

[
    {{
        "tool": "query_value",
        ...
    }},
    {{
        "tool": "aggregate_value",
        ...
    }}
]

但是：

不要无意义拆分任务。

==================================================
二十、输出格式
==================================================

只能返回JSON数组。

禁止：

1. Markdown
2. ```json
3. 解释文字
4. 自然语言说明
5. JSON数组之外的任何内容

标准格式：

[
    {{
        "tool": "",
        "reason": "",
        "customer": "",
        "metrics": [],
        "filters": {{}},
        "compare": {{}},
        "condition": {{}},
        "output": "rows"
    }}
]

==================================================
二十一、用户需求
==================================================

{user_query}

==================================================
现在开始生成任务计划。
"""

        return prompt

    # ==========================================================
    # 创建任务计划
    # ==========================================================

    def create_plan(
        self,
        user_query: str
    ):
        """
        根据用户需求生成Planner任务计划。
        """

        # ------------------------------------------------------
        # 基础校验
        # ------------------------------------------------------

        if user_query is None:
            raise ValueError(
                "用户需求不能为空"
            )

        user_query = str(
            user_query
        ).strip()

        if not user_query:
            raise ValueError(
                "用户需求不能为空"
            )

        # ------------------------------------------------------
        # 获取工具
        # ------------------------------------------------------

        tools = tool_registry.list_tools()

        # ------------------------------------------------------
        # 构造Prompt
        # ------------------------------------------------------

        prompt = self.build_prompt(
            user_query,
            tools
        )

        messages = [

            {
                "role": "system",
                "content": """
你是企业数据分析Agent Planner。

你的核心职责是：

理解用户意图，
提取查询参数，
选择正确工具。

不要假设Excel字段。

不要绑定任何具体Excel模板。

不要读取Excel。

不要猜测Sheet。

不要进行字段映射。

字段映射由Schema Agent完成。

只能输出JSON数组。
"""
            },

            {
                "role": "user",
                "content": prompt
            }

        ]

        # ------------------------------------------------------
        # 调用LLM
        # ------------------------------------------------------

        try:

            response = self.llm.chat(
                messages
            )

            print(
                "\n===== DeepSeek Planner原始返回 ====="
            )

            print(response)

            # --------------------------------------------------
            # JSON解析
            # --------------------------------------------------

            plan = self.parse_json_response(
                response
            )

            # --------------------------------------------------
            # 类型检查
            # --------------------------------------------------

            if not isinstance(
                plan,
                list
            ):

                raise ValueError(
                    "Planner返回的不是JSON数组"
                )

            # --------------------------------------------------
            # 标准化任务
            # --------------------------------------------------

            valid = []

            for task in plan:

                normalized = self.normalize_task(
                    task,
                    tools
                )

                if normalized is None:
                    continue

                valid.append(
                    normalized
                )

            # --------------------------------------------------
            # 没有有效任务
            # --------------------------------------------------

            if not valid:

                raise ValueError(
                    "Planner没有生成有效任务"
                )

            print(
                "\n===== V9 Planner计划 ====="
            )

            print(
                json.dumps(
                    valid,
                    ensure_ascii=False,
                    indent=2
                )
            )

            return valid

        except Exception as e:

            self.logger.error(
                f"Planner失败: {e}"
            )

            print(
                "\nPlanner失败:",
                e
            )

            # --------------------------------------------------
            # fallback
            # --------------------------------------------------

            return self.fallback_plan(
                user_query
            )

    # ==========================================================
    # Fallback
    # ==========================================================

    def fallback_plan(
        self,
        query
    ):
        """
        LLM失败时使用基础规则。

        注意：

        fallback同样不绑定Excel字段。
        """

        query = str(
            query
        ).strip()

        # ======================================================
        # 比较关键词
        # ======================================================

        compare_keywords = [

            "比较",
            "是否",
            "相等",
            "一致",
            "相同",
            "一样",
            "不相等",
            "不同",
            "差异",
            "大于",
            "超过",
            "高于",
            "小于",
            "低于",
            "不少于",
            "至少",
            "不超过",
            "最多"

        ]

        # ======================================================
        # 比较任务
        # ======================================================

        if any(
            keyword in query
            for keyword in compare_keywords
        ):

            # --------------------------------------------------
            # 判断运算符
            # --------------------------------------------------

            if any(
                keyword in query
                for keyword in [
                    "不相等",
                    "不同",
                    "不一致",
                    "差异"
                ]
            ):

                operator = "!="

            elif any(
                keyword in query
                for keyword in [
                    "不少于",
                    "至少",
                    "不低于"
                ]
            ):

                operator = ">="

            elif any(
                keyword in query
                for keyword in [
                    "不超过",
                    "最多",
                    "不高于"
                ]
            ):

                operator = "<="

            elif any(
                keyword in query
                for keyword in [
                    "大于",
                    "超过",
                    "高于"
                ]
            ):

                operator = ">"

            elif any(
                keyword in query
                for keyword in [
                    "小于",
                    "低于"
                ]
            ):

                operator = "<"

            elif any(
                keyword in query
                for keyword in [
                    "相等",
                    "一致",
                    "相同",
                    "一样",
                    "是否"
                ]
            ):

                operator = "=="

            else:

                operator = "!="

            return [

                {
                    "tool":
                    "compare_rows",

                    "reason":
                    "Planner失败，使用比较关键词进行基础判断",

                    "customer":
                    "",

                    "metrics":
                    [],

                    "filters":
                    {},

                    "compare":
                    {
                        "left":
                        "",

                        "right":
                        "",

                        "operator":
                        operator
                    },

                    "condition":
                    {},

                    "output":
                    "rows"
                }

            ]

        # ======================================================
        # 汇总任务
        # ======================================================

        aggregate_keywords = [

            "合计",
            "总额",
            "总计",
            "汇总",
            "求和",
            "加总"

        ]

        if any(
            keyword in query
            for keyword in aggregate_keywords
        ):

            return [

                {
                    "tool":
                    "aggregate_value",

                    "reason":
                    "Planner失败，使用汇总关键词进行基础判断",

                    "customer":
                    "",

                    "metrics":
                    [],

                    "filters":
                    {},

                    "compare":
                    {},

                    "condition":
                    {
                        "aggregation":
                        "sum"
                    },

                    "output":
                    "value"
                }

            ]

        # ======================================================
        # 排名任务
        # ======================================================

        rank_keywords = [

            "最高",
            "最低",
            "最大",
            "最小",
            "排名",
            "TOP",
            "top",
            "前十",
            "前五",
            "前三"

        ]

        if any(
            keyword in query
            for keyword in rank_keywords
        ):

            # 默认：

            # 最高 -> desc
            # 最低 -> asc

            order = "desc"

            if any(
                keyword in query
                for keyword in [
                    "最低",
                    "最小"
                ]
            ):

                order = "asc"

            # 默认TOP数量

            limit = 10

            match = re.search(
                r"前\s*(\d+)",
                query
            )

            if match:

                try:
                    limit = int(
                        match.group(1)
                    )

                except ValueError:
                    limit = 10

            return [

                {
                    "tool":
                    "rank_rows",

                    "reason":
                    "Planner失败，使用排名关键词进行基础判断",

                    "customer":
                    "",

                    "metrics":
                    [],

                    "filters":
                    {},

                    "compare":
                    {},

                    "condition":
                    {
                        "order":
                        order,

                        "limit":
                        limit
                    },

                    "output":
                    "rows"
                }

            ]

        # ======================================================
        # 异常任务
        # ======================================================

        anomaly_keywords = [

            "异常",
            "异常数据",
            "异常波动",
            "风险数据",
            "异常值"

        ]

        if any(
            keyword in query
            for keyword in anomaly_keywords
        ):

            return [

                {
                    "tool":
                    "detect_anomaly",

                    "reason":
                    "Planner失败，使用异常关键词进行基础判断",

                    "customer":
                    "",

                    "metrics":
                    [],

                    "filters":
                    {},

                    "compare":
                    {},

                    "condition":
                    {},

                    "output":
                    "rows"
                }

            ]

        # ======================================================
        # 默认普通查询
        # ======================================================

        return [

            {
                "tool":
                "query_value",

                "reason":
                "Planner失败，使用默认查询",

                "customer":
                "",

                "metrics":
                [],

                "filters":
                {},

                "compare":
                {},

                "condition":
                {},

                "output":
                "rows"
            }

        ]