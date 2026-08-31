"""
Schema Agent V3

职责：

1. 分析 Excel Workbook 结构
2. 自动识别客户字段
3. 自动识别业务字段
4. 自动识别产品字段
5. 自动识别部门字段
6. 自动识别项目字段
7. 自动识别金额/数值指标字段
8. 自动识别时间字段
9. 自动发现 Sheet 之间的候选关系
10. 建立统一 Schema
11. 将 Planner 的业务概念映射到真实 Excel 字段
12. 为 Query / Compare / Aggregate / Rank 等工具提供字段依据


设计原则：

Planner：
    理解用户语言

Schema Agent：
    理解 Excel 结构
    + 完成 Planner → Excel 字段映射

Tool：
    执行真正的数据操作


重要：

Schema Agent 不负责：

    1. 执行查询
    2. 修改 Excel
    3. 计算最终业务结果

它只负责：

    “这个用户说的东西，在 Excel 里对应哪个字段？”
"""

import logging
import os
import re

from schema.keyword_roles import KEYWORD_ROLES
from schema.roles import (
    ALL_ROLES,
    DIMENSION_ROLES,
    METRIC_ROLES,
    LLM_ALLOWED_ROLES,
    ROLE_LABELS,
    normalize_role,
)


class SchemaAgent:

    def __init__(self, llm=None):

        self.llm = llm

        self.logger = logging.getLogger(
            __name__
        )

    # ==================================================
    # 包裹模式检测（如 【客商：xxx】）
    # ==================================================

    _PATTERN_RE = re.compile(
        r"^【(?P<label>[^【】:：]+)[:：](?P<body>[^】]+)】$"
    )

    # ==================================================
    # 主入口：分析 Excel
    # ==================================================

    def analyze(self, sheet_profiles, user_query="", mapping=None):

        schema = {

            # ==========================================
            # Excel Sheets
            # ==========================================

            "sheets": [],

            # ==========================================
            # 字段角色索引（唯一事实来源）
            #
            # {
            #   "customer": ["Sheet1.客商名称", ...],
            #   "amount":   [...],
            #   ...
            # }
            # ==========================================

            "roles": {
                role: []
                for role in ALL_ROLES
            },

            # ==========================================
            # 用户显式确认的映射（state.mapping）
            # ==========================================

            "user_mapping": dict(
                mapping or {}
            ),

            # ==========================================
            # 所有字段（含角色 / 单位 / 包裹模式）
            # ==========================================

            "fields": {},

            # ==========================================
            # Sheet关系
            # ==========================================

            "relationships": [],

            # ==========================================
            # 查询地图
            # ==========================================

            "query_map": {},

            # ==========================================
            # 兼容旧结构（迁移期同步维护，消费方全部
            # 迁移到 roles 后删除）
            # ==========================================

            "entities": {
                "customer": [],
                "business": [],
                "product": [],
                "department": [],
                "project": []
            },

            "metrics": {
                "money": [],
                "number": []
            },

            "time_fields": []

        }

        # ==================================================
        # 1.扫描所有 Sheet
        # ==================================================

        for sheet in sheet_profiles:

            df = sheet["df"]

            sheet_name = sheet["sheet"]

            schema["sheets"].append(
                sheet_name
            )

            columns = list(
                df.columns
            )

            # ------------------------------------------
            # LLM 角色识别（每 Sheet 一次调用）
            # ------------------------------------------

            llm_roles = self.classify_roles_with_llm(
                sheet_name,
                columns,
                df,
                user_query
            )

            for column in columns:

                col = str(
                    column
                ).strip()

                if not col:
                    continue

                field = (
                    f"{sheet_name}.{col}"
                )

                # ------------------------------------------
                # 保存字段信息
                # ------------------------------------------

                if field not in schema["fields"]:

                    schema["fields"][field] = {

                        "sheet":
                            sheet_name,

                        "column":
                            col,

                        "dtype":
                            str(
                                df[column].dtype
                            ),

                        "sample_values":
                            self.get_sample_values(
                                df[column]
                            )

                    }

                # ------------------------------------------
                # 字段角色：LLM 优先 → 关键词兜底 → unknown
                # ------------------------------------------

                self.assign_role(
                    schema,
                    field,
                    llm_roles
                )

        # ==================================================
        # 2.去重 + 同步旧结构
        # ==================================================

        self.deduplicate_schema(
            schema
        )

        self.sync_compat(
            schema
        )

        # ==================================================
        # 3.自动发现 Sheet 关系
        # ==================================================

        schema["relationships"] = (
            self.detect_relationships(
                schema
            )
        )

        # ==================================================
        # 4.生成 Query Map
        # ==================================================

        schema["query_map"] = (
            self.build_query_map(
                schema
            )
        )

        # ==================================================
        # 5.兼容旧代码
        # ==================================================

        schema["query_plan"] = {

            "customer_fields":
                schema["entities"].get(
                    "customer",
                    []
                ),

            "business_fields":
                schema["entities"].get(
                    "business",
                    []
                ),

            "money_fields":
                schema["metrics"].get(
                    "money",
                    []
                ),

            "relationships":
                schema["relationships"]

        }

        # ==================================================
        # 输出
        # ==================================================

        self.print_schema(
            schema
        )

        return schema

    # ==================================================
    # 字段角色分配：LLM 优先 → 关键词兜底 → unknown
    # ==================================================

    def assign_role(self, schema, field, llm_roles):

        info = schema["fields"][field]

        col = info["column"]

        role = None

        confidence = 0.0

        reason = ""

        unit = None

        # ----------------------------------------------
        # 1. LLM 识别结果（本 Sheet 一次调用）
        # ----------------------------------------------

        if llm_roles and col in llm_roles:

            llm_info = llm_roles[col]

            role = normalize_role(
                llm_info.get("role") if isinstance(llm_info, dict) else llm_info
            )

            if role != "unknown":

                confidence = 0.9

                reason = (
                    llm_info.get("reason", "")
                    if isinstance(llm_info, dict)
                    else "LLM识别"
                )

                if isinstance(llm_info, dict) and llm_info.get("unit"):

                    unit = str(llm_info["unit"])

        # ----------------------------------------------
        # 2. 关键词兜底
        # ----------------------------------------------

        if role == "unknown" or not role:

            keyword_role = self.classify_field(col)

            if keyword_role != "unknown":

                role = keyword_role

                confidence = 0.7

                reason = "关键词匹配"

        # ----------------------------------------------
        # 3. 仍无 → unknown（保留在 fields 中）
        # ----------------------------------------------

        if not role:

            role = "unknown"

            confidence = 0.3

            reason = "无法识别"

        # ----------------------------------------------
        # 单位推断（金额字段）
        # ----------------------------------------------

        if role == "amount" and not unit:

            unit = self.detect_unit(
                col,
                info.get("sample_values", [])
            )

        # ----------------------------------------------
        # 包裹模式检测（如 【客商：xxx】）
        # ----------------------------------------------

        pattern = self.detect_pattern(
            info.get("sample_values", [])
        )

        # ----------------------------------------------
        # 聚合标记
        # ----------------------------------------------

        aggregate = role in METRIC_ROLES

        # ----------------------------------------------
        # 写入字段 + 角色索引
        # ----------------------------------------------

        info["role"] = role

        info["role_confidence"] = round(confidence, 2)

        info["role_reason"] = reason

        info["unit"] = unit

        info["pattern"] = pattern

        info["aggregate"] = aggregate

        schema["roles"][role].append(field)

    # ==================================================
    # LLM 角色识别（每 Sheet 一次调用）
    #
    # 成功 → 返回 {"列名": {"role", "unit", "reason"}}
    # 失败 / 被禁用（DISABLE_LLM_SCHEMA=1）→ None
    # ==================================================

    def classify_roles_with_llm(
        self,
        sheet_name,
        columns,
        df,
        user_query=""
    ):

        if not self.llm:
            return None

        if os.environ.get("DISABLE_LLM_SCHEMA") == "1":
            print(
                f"[SchemaAgent] DISABLE_LLM_SCHEMA=1，跳过 LLM 角色识别（{sheet_name}）"
            )
            return None

        # ----------------------------------------------
        # 构造输入：每列 2-3 个样本值
        # ----------------------------------------------

        lines = []

        for column in columns:

            col = str(column).strip()

            if not col:
                continue

            samples = self.get_sample_values(
                df[column],
                limit=3
            )

            lines.append(
                f"- {col}: {samples}"
            )

        prompt = f"""
你是数据建模专家。下面是一个数据表的结构描述，请为每一列识别业务角色。

表名: {sheet_name}
用户问题: {user_query or "（无）"}

列名及样本值:
{chr(10).join(lines)}

角色定义：
- customer: 客户/客商/供应商/公司
- business: 业务类型/产品线
- product: 产品/商品/SKU
- department: 部门/组织/事业部
- project: 项目/工程
- region: 地区/区域
- person: 人员/姓名/员工
- category: 其他分类（品类/类别/状态/方向）
- amount: 金额（货币），unit 填单位（万元/元/千元，无法确定填 null）
- number: 数量/比率/计数/评分
- date: 日期/时间/年份/期间
- id: 编码/编号/工号/单号
- text: 备注/描述等自由文本

输出 JSON（不要 markdown 代码块，不要解释）：
{{"columns": [{{"column": "列名", "role": "角色", "unit": null, "reason": "一句话理由"}}]}}

注意：
1. 列数与输入一致，不得遗漏、不得新增
2. "名称"类列按前缀判断：客商名称→customer，部门名称→department，产品名称→product
3. 只有金额列才需要 unit；样本形如 100万 时可推断 unit=万
4. 无法判断的列给 unknown
"""

        response = self.llm.chat_json([

            {
                "role": "system",
                "content": "你是数据建模专家，只输出 JSON。"
            },

            {
                "role": "user",
                "content": prompt
            }

        ])

        if not response:
            print(
                f"[SchemaAgent] LLM 角色识别失败（{sheet_name}），降级到关键词兜底"
            )
            return None

        # ----------------------------------------------
        # 解析并校验
        # ----------------------------------------------

        result = {}

        raw_columns = response.get("columns", [])

        if not isinstance(raw_columns, list):
            return None

        for item in raw_columns:

            if not isinstance(item, dict):
                continue

            col = str(
                item.get("column", "")
            ).strip()

            if not col or col not in [str(c).strip() for c in columns]:
                continue

            role = normalize_role(
                item.get("role")
            )

            result[col] = {
                "role": role,
                "unit": item.get("unit") if role == "amount" else None,
                "reason": str(item.get("reason", ""))[:100],
            }

        if not result:
            return None

        return result

    # ==================================================
    # 关键词兜底分类（打分制）
    # ==================================================

    def classify_field(self, col):

        # pandas 对无列名列的自动命名，无业务含义
        if col.startswith("Unnamed"):

            return "unknown"

        best_role = "unknown"

        best_score = 0

        for role, keywords in KEYWORD_ROLES.items():

            score = sum(
                1
                for k in keywords
                if k in col
            )

            if score > best_score:

                best_score = score

                best_role = role

        return best_role

    # ==================================================
    # 金额单位推断
    # ==================================================

    def detect_unit(self, column, sample_values):

        col = str(column)

        for u in ("亿元", "千元", "万元", "元"):

            if u in col:
                return u

        # 从样本值推断（如 100万、1.5亿）
        for v in sample_values:

            m = re.search(
                r"(\d+(?:\.\d+)?)(万元|亿元|千元|万|亿|千|元)",
                str(v)
            )

            if m:
                u = m.group(2)
                if u == "万":
                    return "万元"
                if u == "亿":
                    return "亿元"
                return u

        return None

    # ==================================================
    # 包裹模式检测（样本确认后才生成）
    # ==================================================

    def detect_pattern(self, sample_values):

        if not sample_values:
            return None

        prefixes = []

        for v in sample_values:

            m = self._PATTERN_RE.match(str(v))

            if m:
                prefixes.append(
                    f"【{m.group('label')}："
                )

        if not prefixes:
            return None

        coverage = len(prefixes) / len(sample_values)

        if coverage < 0.5:
            return None

        prefix = max(
            set(prefixes),
            key=prefixes.count
        )

        return {
            "type": "prefix_suffix",
            "prefix": prefix,
            "suffix": "】",
            "coverage": round(coverage, 2),
        }

    # ==================================================
    # 同步兼容旧结构（entities/metrics/time_fields）
    # ==================================================

    def sync_compat(self, schema):

        roles = schema["roles"]

        schema["entities"]["customer"] = list(roles["customer"])
        schema["entities"]["business"] = list(roles["business"])
        schema["entities"]["product"] = list(roles["product"])
        schema["entities"]["department"] = list(roles["department"])
        schema["entities"]["project"] = list(roles["project"])

        schema["metrics"]["money"] = list(roles["amount"])
        schema["metrics"]["number"] = list(roles["number"])

        schema["time_fields"] = list(roles["date"])

        # 预留 _compat：所有消费方迁移到 roles 后，
        # 顶层 entities/metrics/time_fields 与 _compat 一并删除
        schema["_compat"] = {
            "entities": schema["entities"],
            "metrics": schema["metrics"],
            "time_fields": schema["time_fields"],
        }

    # ==================================================
    # 获取样本值
    # ==================================================

    def get_sample_values(
        self,
        series,
        limit=5
    ):

        try:

            values = (
                series
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

            return values[:limit]

        except Exception:

            return []

    # ==================================================
    def deduplicate_schema(
        self,
        schema
    ):

        # roles（唯一事实来源）

        for role in schema["roles"]:

            schema["roles"][role] = list(
                dict.fromkeys(
                    schema["roles"][role]
                )
            )

        # entities（兼容层）

        for category in schema[
            "entities"
        ]:

            schema[
                "entities"
            ][category] = list(
                dict.fromkeys(
                    schema[
                        "entities"
                    ][category]
                )
            )

        # metrics（兼容层）

        for category in schema[
            "metrics"
        ]:

            schema[
                "metrics"
            ][category] = list(
                dict.fromkeys(
                    schema[
                        "metrics"
                    ][category]
                )
            )

        # time（兼容层）

        schema[
            "time_fields"
        ] = list(
            dict.fromkeys(
                schema[
                    "time_fields"
                ]
            )
        )

    # ==================================================
    # 自动发现 Sheet 关系
    # ==================================================

    def detect_relationships(
        self,
        schema
    ):

        relationships = []

        # ==================================================
        # 客户字段
        # ==================================================

        customer_fields = (
            schema[
                "entities"
            ].get(
                "customer",
                []
            )
        )

        for i in range(
            len(customer_fields)
        ):

            for j in range(
                i + 1,
                len(customer_fields)
            ):

                source = (
                    customer_fields[i]
                )

                target = (
                    customer_fields[j]
                )

                source_sheet = (
                    source.split(
                        ".",
                        1
                    )[0]
                )

                target_sheet = (
                    target.split(
                        ".",
                        1
                    )[0]
                )

                if (
                    source_sheet
                    !=
                    target_sheet
                ):

                    relationships.append({

                        "source":
                            source,

                        "target":
                            target,

                        "type":
                            "customer_candidate",

                        "confidence":
                            0.8

                    })

        # ==================================================
        # 业务字段
        # ==================================================

        business_fields = (
            schema[
                "entities"
            ].get(
                "business",
                []
            )
        )

        for i in range(
            len(business_fields)
        ):

            for j in range(
                i + 1,
                len(business_fields)
            ):

                source = (
                    business_fields[i]
                )

                target = (
                    business_fields[j]
                )

                source_sheet = (
                    source.split(
                        ".",
                        1
                    )[0]
                )

                target_sheet = (
                    target.split(
                        ".",
                        1
                    )[0]
                )

                if (
                    source_sheet
                    !=
                    target_sheet
                ):

                    relationships.append({

                        "source":
                            source,

                        "target":
                            target,

                        "type":
                            "business_candidate",

                        "confidence":
                            0.6

                    })

        return relationships

    # ==================================================
    # Query Map
    # ==================================================

    def build_query_map(
        self,
        schema
    ):

        return {

            "customer_fields":
                schema[
                    "entities"
                ].get(
                    "customer",
                    []
                ),

            "business_fields":
                schema[
                    "entities"
                ].get(
                    "business",
                    []
                ),

            "product_fields":
                schema[
                    "entities"
                ].get(
                    "product",
                    []
                ),

            "department_fields":
                schema[
                    "entities"
                ].get(
                    "department",
                    []
                ),

            "project_fields":
                schema[
                    "entities"
                ].get(
                    "project",
                    []
                ),

            "money_fields":
                schema[
                    "metrics"
                ].get(
                    "money",
                    []
                ),

            "number_fields":
                schema[
                    "metrics"
                ].get(
                    "number",
                    []
                ),

            "time_fields":
                schema[
                    "time_fields"
                ]

        }

    # ==================================================
    # ==================================================
    # Planner → Schema 字段映射
    # ==================================================
    # ==================================================

    def resolve_plan(
        self,
        plan,
        schema
    ):
        """
        将 Planner 产生的自然语言概念
        映射成 Excel 中真实存在的字段。

        注意：

        本方法只负责字段映射，
        不执行真正的数据查询。
        """

        resolved_tasks = []

        for task in plan:

            resolved = {

                "tool":
                    task.get(
                        "tool",
                        ""
                    ),

                "reason":
                    task.get(
                        "reason",
                        ""
                    ),

                "customer":
                    self.resolve_customer(
                        task.get(
                            "customer",
                            ""
                        ),
                        schema
                    ),

                "filters":
                    self.resolve_filters(
                        task.get(
                            "filters",
                            {}
                        ),
                        schema
                    ),

                "metrics":
                    self.resolve_metrics(
                        task.get(
                            "metrics",
                            []
                        ),
                        schema
                    ),

                "compare":
                    self.resolve_compare(
                        task.get(
                            "compare",
                            {}
                        ),
                        schema
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

            resolved_tasks.append(
                resolved
            )

        print(
            "\n===== Schema 字段映射结果 ====="
        )

        for item in resolved_tasks:

            print(
                item
            )

        return resolved_tasks

    # ==================================================
    # 客户映射
    # ==================================================

    def resolve_customer(
        self,
        customer,
        schema
    ):

        if not customer:

            return {

                "value": "",

                "field": None,

                "confidence": 0

            }

        candidates = (
            schema[
                "entities"
            ].get(
                "customer",
                []
            )
        )

        best = self.find_best_field(
            customer,
            candidates
        )

        return {

            "value":
                customer,

            "field":
                best["field"],

            "confidence":
                best["confidence"],

            "candidates":
                best["candidates"]

        }

    # ==================================================
    # Filter 映射
    # ==================================================

    def resolve_filters(
        self,
        filters,
        schema
    ):

        if not filters:

            return []

        resolved = []

        for concept, value in filters.items():

            category = (
                self.detect_filter_category(
                    concept
                )
            )

            candidates = (
                schema[
                    "entities"
                ].get(
                    category,
                    []
                )
            )

            # 时间条件
            if category == "time":

                candidates = (
                    schema.get(
                        "time_fields",
                        []
                    )
                )

            best = self.find_best_field(
                concept,
                candidates
            )

            resolved.append({

                "concept":
                    concept,

                "value":
                    value,

                "field":
                    best["field"],

                "confidence":
                    best["confidence"],

                "candidates":
                    best["candidates"]

            })

        return resolved

    # ==================================================
    # 指标映射
    # ==================================================

    def resolve_metrics(
        self,
        metrics,
        schema
    ):

        if not metrics:

            return []

        candidates = (

            schema[
                "metrics"
            ].get(
                "money",
                []
            )
            +
            schema[
                "metrics"
            ].get(
                "number",
                []
            )

        )

        result = []

        for metric in metrics:

            best = self.find_best_field(
                metric,
                candidates
            )

            result.append({

                "concept":
                    metric,

                "field":
                    best["field"],

                "confidence":
                    best["confidence"],

                "candidates":
                    best["candidates"]

            })

        return result

    # ==================================================
    # Compare 映射
    # ==================================================

    def resolve_compare(
        self,
        compare,
        schema
    ):

        if not compare:

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
            "=="
        )

        candidates = (

            schema[
                "metrics"
            ].get(
                "money",
                []
            )
            +
            schema[
                "metrics"
            ].get(
                "number",
                []
            )

        )

        left_result = self.find_best_field(
            left,
            candidates
        )

        # ----------------------------------------------
        # right 如果是字段
        # ----------------------------------------------

        right_result = {

            "field": None,

            "confidence": 0,

            "candidates": []

        }

        if right:

            # 如果是数字 / 数值条件
            if self.is_number_value(
                right
            ):

                right_result = {

                    "value":
                        right,

                    "field":
                        None,

                    "confidence":
                        1.0,

                    "candidates":
                        []

                }

            else:

                right_result = (
                    self.find_best_field(
                        right,
                        candidates
                    )
                )

        return {

            "left": {

                "concept":
                    left,

                "field":
                    left_result["field"],

                "confidence":
                    left_result["confidence"],

                "candidates":
                    left_result["candidates"]

            },

            "right": {

                "concept":
                    right,

                "field":
                    right_result.get(
                        "field"
                    ),

                "value":
                    right_result.get(
                        "value"
                    ),

                "confidence":
                    right_result.get(
                        "confidence",
                        0
                    ),

                "candidates":
                    right_result.get(
                        "candidates",
                        []
                    )

            },

            "operator":
                operator

        }

    # ==================================================
    # 判断 Filter 类型
    # ==================================================

    def detect_filter_category(
        self,
        concept
    ):

        concept = str(
            concept
        )

        if (
            "客户" in concept
            or
            "客商" in concept
        ):

            return "customer"

        if "业务" in concept:

            return "business"

        if (
            "产品" in concept
            or
            "商品" in concept
        ):

            return "product"

        if (
            "部门" in concept
            or
            "事业部" in concept
            or
            "组织" in concept
        ):

            return "department"

        if (
            "项目" in concept
            or
            "工程" in concept
        ):

            return "project"

        if (
            "时间" in concept
            or
            "日期" in concept
            or
            "年份" in concept
            or
            "年度" in concept
            or
            "月份" in concept
            or
            "期间" in concept
        ):

            return "time"

        # 默认按照业务条件处理
        return "business"

    # ==================================================
    # 查找最佳字段
    # ==================================================

    def find_best_field(
        self,
        concept,
        candidates
    ):

        if not concept:

            return {

                "field": None,

                "confidence": 0,

                "candidates": []

            }

        if not candidates:

            return {

                "field": None,

                "confidence": 0,

                "candidates": []

            }

        concept = str(
            concept
        ).strip()

        scored = []

        for field in candidates:

            column = (
                field.split(
                    ".",
                    1
                )[-1]
            )

            score = self.field_similarity(
                concept,
                column
            )

            scored.append({

                "field":
                    field,

                "score":
                    score

            })

        scored.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        best = scored[0]

        return {

            "field":
                best["field"],

            "confidence":
                best["score"],

            "candidates":
                scored[:5]

        }

    # ==================================================
    # 字段相似度
    # ==================================================

    def field_similarity(
        self,
        concept,
        field
    ):

        concept = str(
            concept
        ).strip()

        field = str(
            field
        ).strip()

        if not concept or not field:

            return 0

        # ----------------------------------------------
        # 完全相等
        # ----------------------------------------------

        if concept == field:

            return 1.0

        # ----------------------------------------------
        # 包含关系
        # ----------------------------------------------

        if (
            concept in field
            or
            field in concept
        ):

            return 0.9

        # ----------------------------------------------
        # 去除常见修饰词
        # ----------------------------------------------

        normalize_words = [

            "字段",
            "数据",
            "条件",
            "指标",
            "信息",
            "名称"

        ]

        concept_clean = concept

        field_clean = field

        for word in normalize_words:

            concept_clean = (
                concept_clean.replace(
                    word,
                    ""
                )
            )

            field_clean = (
                field_clean.replace(
                    word,
                    ""
                )
            )

        if (
            concept_clean
            ==
            field_clean
        ):

            return 0.95

        # ----------------------------------------------
        # 字符重合度
        # ----------------------------------------------

        concept_chars = set(
            concept_clean
        )

        field_chars = set(
            field_clean
        )

        if not concept_chars:

            return 0

        overlap = (
            len(
                concept_chars
                &
                field_chars
            )
            /
            len(
                concept_chars
            )
        )

        return round(
            min(
                overlap,
                0.85
            ),
            3
        )

    # ==================================================
    # 判断数字
    # ==================================================

    def is_number_value(
        self,
        value
    ):

        value = str(
            value
        ).strip()

        # 100
        # 100.5
        # 100万
        # 100万元
        # 1000元

        pattern = (
            r"^-?\d+(\.\d+)?"
            r"(万|万元|元|千|百万|亿)?$"
        )

        return bool(
            re.match(
                pattern,
                value
            )
        )

    # ==================================================
    # 第一个字段
    # ==================================================

    def first_field(
        self,
        schema,
        key
    ):

        values = (
            schema[
                "entities"
            ].get(
                key,
                []
            )
        )

        if values:

            return values[0]

        return None

    # ==================================================
    # 打印 Schema
    # ==================================================

    def print_schema(
        self,
        schema
    ):

        print(
            "\n"
            + "=" * 60
        )

        print(
            "===== Schema Agent V3 分析结果 ====="
        )

        print(
            "=" * 60
        )

        print(
            "\n【Sheets】"
        )

        print(
            schema["sheets"]
        )

        print(
            "\n【字段角色】"
        )

        for role in ALL_ROLES:

            fields = schema["roles"].get(
                role,
                []
            )

            if fields:

                print(
                    f"  {ROLE_LABELS.get(role, role)}: "
                    f"{fields}"
                )

        # 逐字段展示（角色 / 单位 / 包裹模式）
        print(
            "\n【字段明细】"
        )

        for field, info in schema["fields"].items():

            unit = (
                f", unit={info['unit']}"
                if info.get("unit")
                else ""
            )

            pattern = (
                f", pattern={info['pattern']}"
                if info.get("pattern")
                else ""
            )

            print(
                f"  {field} → {info.get('role', 'unknown')}"
                f" ({info.get('role_reason', '')}, "
                f"conf={info.get('role_confidence', 0)}){unit}{pattern}"
            )

        print(
            "\n【Sheet关系】"
        )

        for relation in schema[
            "relationships"
        ]:

            print(
                relation
            )

        print(
            "\n【Query Map】"
        )

        print(
            schema[
                "query_map"
            ]
        )

        print(
            "=" * 60
        )