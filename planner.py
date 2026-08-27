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
Planner只负责理解用户语言，不负责：
1. 读取Excel
2. 判断Excel有哪些Sheet
3. 判断Excel有哪些字段
4. 判断哪个Sheet包含哪个字段
5. 将业务概念强制映射为Excel字段
"""

import json
import logging
import re
from tools import tool_registry


class TaskPlanner:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.logger = logging.getLogger(__name__)

    # ==========================================================
    # JSON解析
    # ==========================================================
    def parse_json_response(self, response):
        if response is None:
            raise ValueError("LLM返回为空")
        response = str(response).strip()
        if not response:
            raise ValueError("LLM返回为空字符串")
        # 直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        # 清理Markdown代码块
        cleaned = response
        cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # 提取JSON数组
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            json_text = cleaned[start:end + 1]
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass
        # 提取JSON对象
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_text = cleaned[start:end + 1]
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass
        raise ValueError("无法从LLM返回内容中解析JSON")

    # ==========================================================
    # 标准化方法
    # ==========================================================
    def normalize_string(self, value):
        if value is None:
            return ""
        if not isinstance(value, str):
            return value
        return value.strip()

    def normalize_metrics(self, metrics):
        if metrics is None:
            return []
        if isinstance(metrics, str):
            metrics = metrics.strip()
            return [metrics] if metrics else []
        if not isinstance(metrics, list):
            return []
        result = []
        for item in metrics:
            if item is None:
                continue
            item = str(item).strip()
            if item and item not in result:
                result.append(item)
        return result

    def normalize_filters(self, filters):
        if filters is None or not isinstance(filters, dict):
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

    def normalize_compare(self, compare):
        if compare is None or not isinstance(compare, dict):
            return {}
        left = str(compare.get("left", "")).strip()
        right = str(compare.get("right", "")).strip()
        operator = str(compare.get("operator", "")).strip()
        valid_operators = ["==", "!=", ">", "<", ">=", "<="]
        if operator not in valid_operators:
            operator = ""
        if not left and not right and not operator:
            return {}
        return {"left": left, "right": right, "operator": operator}

    def normalize_condition(self, condition):
        if condition is None or not isinstance(condition, dict):
            return {}
        return condition

    def normalize_task(self, task, tools):
        if not isinstance(task, dict):
            return None
        tool = task.get("tool", "")
        if not isinstance(tool, str):
            return None
        tool = tool.strip()
        if tool not in tools:
            print("忽略不存在工具:", tool)
            return None
        return {
            "tool": tool,
            "reason": self.normalize_string(task.get("reason", "")),
            "customer": self.normalize_string(task.get("customer", "")),
            "metrics": self.normalize_metrics(task.get("metrics", [])),
            "filters": self.normalize_filters(task.get("filters", {})),
            "compare": self.normalize_compare(task.get("compare", {})),
            "condition": self.normalize_condition(task.get("condition", {})),
            "output": self.normalize_string(task.get("output", "rows")) or "rows"
        }

    # ==========================================================
    # 创建Planner Prompt
    # ==========================================================
    def build_prompt(self, user_query, tools):
        prompt = f"""
你是一个企业级AI数据分析Agent的任务规划器。

你的任务是：理解用户的自然语言需求，提取用户真正想执行的数据分析任务，并生成标准JSON任务计划。

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

尤其注意：【不要把用户业务语言直接转换成Excel字段】。
例如：用户说"公路建设期产品运维(JSYW)"，应保留为业务条件，而不是映射到"业务类型（新）"。

==================================================
三、可用工具
==================================================
{tools}

只能选择上述工具。如果工具不存在，不要创造新工具。

==================================================
四、任务类型
==================================================
1. 普通查询 (query_value) - 用户表达：查询、查、查看、寻找、看看、多少、有哪些、明细、数据、信息
2. 字段比较 (compare_rows) - 用户表达：比较、是否相等、一致、相同、不同、大于、小于、不少于、不超过等
3. 汇总统计 (aggregate_value) - 用户表达：合计、总额、总计、统计、汇总、求和、加总
4. 排名 (rank_rows) - 用户表达：最高、最低、最大、最小、排名、TOP、前几、前十、前五、前三
5. 异常检测 (detect_anomaly) - 用户表达：异常、异常数据、波动、异常波动、风险数据、异常值

==================================================
五、客户提取
==================================================
如果用户明确提到客户/公司/客商/企业，必须完整保留。
例如："查询保利长大工程有限公司" → "customer": "保利长大工程有限公司"
如果没有明确客户，则 "customer": ""，不要猜测。

==================================================
六、业务条件提取
==================================================
用户表达的业务条件必须保留为 filters 中的键值对，例如：
- "业务条件": "公路建设业务"
- "项目": "某项目"
- "产品": "某产品"
- "部门": "某部门"
- "时间": "2025"

==================================================
七、用户明确字段名
==================================================
如果用户自己说出了字段名称（如"业务类型是公路建设期产品运维"），可以直接使用该字段名作为 filters 的键，因为字段名称来自用户。

==================================================
八、指标提取
==================================================
只有用户明确要求某个指标时，才放入 metrics。
例如："查询A公司的销售额" → "metrics": ["销售额"]
如果用户只说"查询A公司的数据"，则 "metrics": []

==================================================
九、禁止猜测指标
==================================================
如果用户没有明确指标，不要生成任何 metrics。

==================================================
十、模糊业务词处理
==================================================
以下表达通常属于业务概念，不要擅自转换成Excel字段：
销售数据、业务数据、经营情况、经营数据、财务情况、项目情况、合同情况、客户情况、业务情况
例如："查询华为2025年的销售数据" → 可以提取 customer 和 时间，但 metrics 留空。

==================================================
十一、比较条件 (compare_rows)
==================================================
如果工具是 compare_rows，必须提取 compare 字段，格式：
"compare": {{"left": "字段1", "right": "字段2或数字", "operator": "运算符"}}
运算符：==, !=, >, <, >=, <=

==================================================
十二、汇总统计 (aggregate_value)
==================================================
如果用户表达总额/合计/总计/求和/汇总，使用 aggregate_value，并在 condition 中设置 "aggregation": "sum"。

==================================================
十三、排名 (rank_rows)
==================================================
如果用户表达最高/最低/最大/最小/排名/TOP/前N，使用 rank_rows，并在 condition 中设置 "order": "desc"/"asc" 和 "limit": N。
默认 order 为 desc，limit 为 10。

==================================================
十四、异常检测 (detect_anomaly)
==================================================
如果用户表达异常/风险/波动等，使用 detect_anomaly。

==================================================
十五、多个任务
==================================================
如果用户一次提出多个明确且相互独立的任务，可以返回多个任务的数组。但不要无意义拆分。

==================================================
十六、模糊意图与综合评价处理（关键）
==================================================
当用户的问题属于"分析、评价、判断、展望"类，且**没有指定具体客户或具体指标**时（例如：发展前景、经营状况、合作价值、风险评估、哪个最好、谁最优秀），
你**必须**按以下优先级处理，**严禁**使用 query_value 进行全表查询。

优先级一：识别隐含的分析维度
将模糊问题映射为具体的数值指标。通常，财务数据分析中：
- "发展前景"、"经营状况"、"盈利能力" → 映射为"期末余额"或"本期贷方"
- "客户价值"、"合作价值" → 映射为"期末余额"或"贷方累计"
- "业务活跃度" → 映射为"本期贷方"或"业务种类计数"

优先级二：生成排名任务
使用 rank_rows 工具，按映射后的指标进行汇总排名。

必须遵循的生成规则：
1. 工具：固定为 "tool": "rank_rows"
2. 指标 (metrics)：根据上述映射，选择最合适的金额字段。如果用户没有明确指定，默认使用"期末余额"。
3. 排名条件 (condition)：默认 "order": "desc"（从高到低），"limit": 10（取前10名）。如果用户提到"前几名"或"TOP N"，则按实际数字调整。
4. 客户 (customer)：如果用户没有指定具体客户，留空 ""。
5. 过滤条件 (filters)：如果用户提到年份或业务类型，则填入，否则留空 {{}}。

示例：
用户问："哪个公司发展前景好？"
应返回：
[
  {{
    "tool": "rank_rows",
    "reason": "按期末余额排名，评估客户发展前景",
    "customer": "",
    "metrics": ["期末余额"],
    "filters": {{}},
    "compare": {{}},
    "condition": {{"order": "desc", "limit": 10}},
    "output": "rows"
  }}
]

用户问："2025年哪些客户收入最高？"
应返回：
[
  {{
    "tool": "rank_rows",
    "reason": "按2025年本期贷方排名，找出收入最高客户",
    "customer": "",
    "metrics": ["本期贷方"],
    "filters": {{"时间": "2025"}},
    "compare": {{}},
    "condition": {{"order": "desc", "limit": 10}},
    "output": "rows"
  }}
]

禁止行为：
- 禁止返回空 metrics。
- 禁止使用 query_value 处理模糊问题（除非用户明确要求查看明细）。
- 如果无法从问题中推断出任何指标，则使用默认指标"期末余额"。



==================================================
十七、输出格式
==================================================
只能返回JSON数组。禁止Markdown、```json、解释文字、自然语言说明。

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
十八、用户需求
==================================================
{user_query}

==================================================
现在开始生成任务计划。
"""
        return prompt

    # ==========================================================
    # 创建任务计划
    # ==========================================================
    def create_plan(self, user_query: str):
        if user_query is None:
            raise ValueError("用户需求不能为空")
        user_query = str(user_query).strip()
        if not user_query:
            raise ValueError("用户需求不能为空")

        tools = tool_registry.list_tools()
        prompt = self.build_prompt(user_query, tools)

        messages = [
            {"role": "system", "content": """
你是企业数据分析Agent Planner。
你的核心职责是：理解用户意图，提取查询参数，选择正确工具。
不要假设Excel字段，不要绑定任何具体Excel模板，不要读取Excel，不要猜测Sheet，不要进行字段映射。
字段映射由Schema Agent完成。
只能输出JSON数组。
"""},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.llm.chat(messages)
            print("\n===== DeepSeek Planner原始返回 =====")
            print(response)

            plan = self.parse_json_response(response)
            if not isinstance(plan, list):
                raise ValueError("Planner返回的不是JSON数组")

            valid = []
            for task in plan:
                normalized = self.normalize_task(task, tools)
                if normalized is not None:
                    valid.append(normalized)

            if not valid:
                raise ValueError("Planner没有生成有效任务")

            print("\n===== V9 Planner计划 =====")
            print(json.dumps(valid, ensure_ascii=False, indent=2))
            return valid

        except Exception as e:
            self.logger.error(f"Planner失败: {e}")
            print("\nPlanner失败:", e)
            return self.fallback_plan(user_query)

    # ==========================================================
    # Fallback
    # ==========================================================
    def fallback_plan(self, query):
        query = str(query).strip()

        # 模糊分析关键词 (新增)
        fuzzy_analysis_keywords = [
            "前景", "发展", "潜力", "评价", "评估", "分析", "表现",
            "哪个", "哪些", "最好", "最优秀", "最优", "合作价值",
            "经营状况", "盈利能力", "客户价值"
        ]
        if any(keyword in query for keyword in fuzzy_analysis_keywords):
            return [
                {
                    "tool": "rank_rows",
                    "reason": "根据模糊分析需求，按期末余额排名评估客户",
                    "customer": "",
                    "metrics": ["期末余额"],
                    "filters": {},
                    "compare": {},
                    "condition": {"order": "desc", "limit": 10},
                    "output": "rows"
                }
            ]

        # 比较关键词
        compare_keywords = [
            "比较", "是否", "相等", "一致", "相同", "一样",
            "不相等", "不同", "差异", "大于", "超过", "高于",
            "小于", "低于", "不少于", "至少", "不超过", "最多"
        ]
        if any(keyword in query for keyword in compare_keywords):
            if any(k in query for k in ["不相等", "不同", "不一致", "差异"]):
                operator = "!="
            elif any(k in query for k in ["不少于", "至少", "不低于"]):
                operator = ">="
            elif any(k in query for k in ["不超过", "最多", "不高于"]):
                operator = "<="
            elif any(k in query for k in ["大于", "超过", "高于"]):
                operator = ">"
            elif any(k in query for k in ["小于", "低于"]):
                operator = "<"
            elif any(k in query for k in ["相等", "一致", "相同", "一样", "是否"]):
                operator = "=="
            else:
                operator = "!="
            return [
                {
                    "tool": "compare_rows",
                    "reason": "Planner失败，使用比较关键词进行基础判断",
                    "customer": "",
                    "metrics": [],
                    "filters": {},
                    "compare": {"left": "", "right": "", "operator": operator},
                    "condition": {},
                    "output": "rows"
                }
            ]

        # 汇总任务
        aggregate_keywords = ["合计", "总额", "总计", "汇总", "求和", "加总"]
        if any(keyword in query for keyword in aggregate_keywords):
            return [
                {
                    "tool": "aggregate_value",
                    "reason": "Planner失败，使用汇总关键词进行基础判断",
                    "customer": "",
                    "metrics": [],
                    "filters": {},
                    "compare": {},
                    "condition": {"aggregation": "sum"},
                    "output": "value"
                }
            ]

        # 排名任务
        rank_keywords = ["最高", "最低", "最大", "最小", "排名", "TOP", "top", "前十", "前五", "前三"]
        if any(keyword in query for keyword in rank_keywords):
            order = "desc"
            if any(k in query for k in ["最低", "最小"]):
                order = "asc"
            limit = 10
            match = re.search(r"前\s*(\d+)", query)
            if match:
                try:
                    limit = int(match.group(1))
                except ValueError:
                    limit = 10
            return [
                {
                    "tool": "rank_rows",
                    "reason": "Planner失败，使用排名关键词进行基础判断",
                    "customer": "",
                    "metrics": [],
                    "filters": {},
                    "compare": {},
                    "condition": {"order": order, "limit": limit},
                    "output": "rows"
                }
            ]

        # 异常任务
        anomaly_keywords = ["异常", "异常数据", "异常波动", "风险数据", "异常值"]
        if any(keyword in query for keyword in anomaly_keywords):
            return [
                {
                    "tool": "detect_anomaly",
                    "reason": "Planner失败，使用异常关键词进行基础判断",
                    "customer": "",
                    "metrics": [],
                    "filters": {},
                    "compare": {},
                    "condition": {},
                    "output": "rows"
                }
            ]

        # 默认普通查询
        return [
            {
                "tool": "query_value",
                "reason": "Planner失败，使用默认查询",
                "customer": "",
                "metrics": [],
                "filters": {},
                "compare": {},
                "condition": {},
                "output": "rows"
            }
        ]