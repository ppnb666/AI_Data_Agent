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
import re


class SchemaAgent:

    def __init__(self, llm=None):

        self.llm = llm

        self.logger = logging.getLogger(
            __name__
        )

    # ==================================================
    # 主入口：分析 Excel
    # ==================================================

    def analyze(self, sheet_profiles):

        schema = {

            # ==========================================
            # Excel Sheets
            # ==========================================

            "sheets": [],

            # ==========================================
            # 实体字段
            # ==========================================

            "entities": {

                "customer": [],
                "business": [],
                "product": [],
                "department": [],
                "project": []

            },

            # ==========================================
            # 指标字段
            # ==========================================

            "metrics": {

                "money": [],
                "number": []

            },

            # ==========================================
            # 时间字段
            # ==========================================

            "time_fields": [],

            # ==========================================
            # 所有字段
            # ==========================================

            "fields": {},

            # ==========================================
            # Sheet关系
            # ==========================================

            "relationships": [],

            # ==========================================
            # 查询地图
            # ==========================================

            "query_map": {}

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
                # 字段分类
                # ------------------------------------------

                self.classify_field(

                    schema,

                    sheet_name,

                    col

                )

        # ==================================================
        # 2.去重
        # ==================================================

        self.deduplicate_schema(
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
    # 字段分类
    # ==================================================

    def classify_field(
        self,
        schema,
        sheet_name,
        col
    ):

        field = (
            f"{sheet_name}.{col}"
        )

        # ==================================================
        # 客户
        # ==================================================

        customer_keywords = [

            "客商名称",
            "客商",
            "客户名称",
            "客户",
            "客户编码",
            "客商编码",
            "客户编号",
            "客商编号"

        ]

        if any(
            keyword in col
            for keyword in customer_keywords
        ):

            schema["entities"][
                "customer"
            ].append(
                field
            )

        # ==================================================
        # 业务
        # ==================================================

        business_keywords = [

            "业务种类",
            "业务类型",
            "业务名称",
            "业务",
            "产品业务",
            "业务分类",
            "业务类别"

        ]

        if any(
            keyword in col
            for keyword in business_keywords
        ):

            schema["entities"][
                "business"
            ].append(
                field
            )

        # ==================================================
        # 产品
        # ==================================================

        product_keywords = [

            "产品",
            "商品",
            "产品名称",
            "商品名称",
            "产品编码",
            "商品编码"

        ]

        if any(
            keyword in col
            for keyword in product_keywords
        ):

            schema["entities"][
                "product"
            ].append(
                field
            )

        # ==================================================
        # 部门
        # ==================================================

        department_keywords = [

            "部门",
            "事业部",
            "部门名称",
            "组织",
            "组织名称",
            "机构"

        ]

        if any(
            keyword in col
            for keyword in department_keywords
        ):

            schema["entities"][
                "department"
            ].append(
                field
            )

        # ==================================================
        # 项目
        # ==================================================

        project_keywords = [

            "项目",
            "项目名称",
            "项目编码",
            "项目编号",
            "工程名称",
            "工程项目"

        ]

        if any(
            keyword in col
            for keyword in project_keywords
        ):

            schema["entities"][
                "project"
            ].append(
                field
            )

        # ==================================================
        # 金额
        # ==================================================

        money_keywords = [

            "金额",
            "余额",
            "销售额",
            "销售金额",
            "合同金额",
            "收入",
            "利润",
            "贷方",
            "借方",
            "应收",
            "应付",
            "回款",
            "万元",
            "元",
            "成本",
            "费用",
            "价格",
            "单价",
            "营业额"

        ]

        if any(
            keyword in col
            for keyword in money_keywords
        ):

            schema["metrics"][
                "money"
            ].append(
                field
            )

        # ==================================================
        # 数值指标
        # ==================================================

        number_keywords = [

            "数量",
            "次数",
            "销量",
            "人数",
            "面积",
            "比例",
            "率",
            "增长",
            "占比",
            "排名",
            "数量"

        ]

        if any(
            keyword in col
            for keyword in number_keywords
        ):

            schema["metrics"][
                "number"
            ].append(
                field
            )

        # ==================================================
        # 时间
        # ==================================================

        time_keywords = [

            "日期",
            "时间",
            "月份",
            "月份",
            "年份",
            "年度",
            "期间",
            "账期",
            "季度",
            "年",
            "月"

        ]

        if any(
            keyword in col
            for keyword in time_keywords
        ):

            schema[
                "time_fields"
            ].append(
                field
            )

    # ==================================================
    # 去重
    # ==================================================

    def deduplicate_schema(
        self,
        schema
    ):

        # entities

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

        # metrics

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

        # time

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
            "\n【客户字段】"
        )

        print(
            schema[
                "entities"
            ]["customer"]
        )

        print(
            "\n【业务字段】"
        )

        print(
            schema[
                "entities"
            ]["business"]
        )

        print(
            "\n【产品字段】"
        )

        print(
            schema[
                "entities"
            ]["product"]
        )

        print(
            "\n【部门字段】"
        )

        print(
            schema[
                "entities"
            ]["department"]
        )

        print(
            "\n【项目字段】"
        )

        print(
            schema[
                "entities"
            ]["project"]
        )

        print(
            "\n【金额字段】"
        )

        print(
            schema[
                "metrics"
            ]["money"]
        )

        print(
            "\n【数值字段】"
        )

        print(
            schema[
                "metrics"
            ]["number"]
        )

        print(
            "\n【时间字段】"
        )

        print(
            schema[
                "time_fields"
            ]
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