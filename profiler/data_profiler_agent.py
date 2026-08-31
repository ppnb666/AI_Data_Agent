"""
DataProfiler Agent V2

职责：
1. 理解Excel结构
2. 判断数据类型
3. 识别关键字段
4. 【新增】自动检测数据质量问题
5. 【新增】生成通用的清洗建议
6. 【新增】记录数据质量报告
"""

import json
import os

import pandas as pd
from typing import Dict, Any, List, Optional


class DataProfilerAgent:
    def __init__(self, llm):
        self.llm = llm

    # ==========================================================
    # 主入口：分析DataFrame
    # ==========================================================
    def analyze(self, df) -> Dict[str, Any]:
        """
        分析DataFrame，返回数据结构 + 数据质量报告
        """
        columns = list(df.columns)
        sample = df.head(5).to_dict(orient="records")

        # ---- 1. 原有：数据结构理解 ----
        schema = self._analyze_structure(df, columns, sample)

        # ---- 2. 新增：数据质量检测 ----
        quality_report = self._detect_data_quality(df, columns)

        # ---- 3. 新增：清洗建议 ----
        clean_suggestions = self._generate_clean_suggestions(df, columns, quality_report)

        # ---- 4. 合并返回 ----
        schema["quality_report"] = quality_report
        schema["clean_suggestions"] = clean_suggestions

        print("\n📊 数据质量报告:")
        print(json.dumps(quality_report, ensure_ascii=False, indent=2))

        return schema

    # ==========================================================
    # 1. 数据结构理解（原有逻辑，略作精简）
    # ==========================================================
    def _analyze_structure(self, df, columns, sample) -> Dict:
        prompt = f"""
你是一个数据理解专家。请分析下面Excel数据。

字段:
{columns}

前5行数据:
{sample}

请输出JSON格式:
{{
    "data_type": "",
    "description": "",
    "fields": {{}}
}}

data_type可选: finance, contract, sales, inventory, unknown

fields中识别: customer, amount, date, product, department
如果不存在字段填null。
只返回JSON，不要解释。
"""
        result = self.llm.chat([
            {"role": "system", "content": "You are a data profiling AI."},
            {"role": "user", "content": prompt}
        ])

        try:
            schema = json.loads(result)
        except Exception:
            schema = {"data_type": "unknown", "fields": {}}

        # 补充字段列表
        schema["columns"] = columns
        return schema

    # ==========================================================
    # 2. 数据质量检测（核心新增）
    # ==========================================================
    def _detect_data_quality(self, df, columns) -> Dict[str, Any]:
        """
        自动检测每个字段的数据质量问题
        """
        report = {
            "total_rows": len(df),
            "total_columns": len(columns),
            "fields": {}
        }

        for col in columns:
            col_data = df[col]
            field_report = {
                "dtype": str(col_data.dtype),
                "null_count": int(col_data.isnull().sum()),
                "null_rate": round(col_data.isnull().sum() / len(df) * 100, 2),
                "unique_count": int(col_data.nunique()),
                "unique_rate": round(col_data.nunique() / len(df) * 100, 2),
                "sample_values": col_data.dropna().astype(str).head(3).tolist(),
                "issues": [],
                "suggest_clean": False
            }

            # ---- 空值检测 ----
            if field_report["null_rate"] > 30:
                field_report["issues"].append({
                    "type": "high_null_rate",
                    "level": "critical",
                    "message": f"空值率 {field_report['null_rate']}% 过高"
                })
                field_report["suggest_clean"] = True
            elif field_report["null_rate"] > 10:
                field_report["issues"].append({
                    "type": "moderate_null_rate",
                    "level": "warning",
                    "message": f"空值率 {field_report['null_rate']}% 偏高"
                })

            # ---- 唯一值检测 ----
            if field_report["unique_rate"] > 90 and field_report["null_rate"] < 10:
                field_report["issues"].append({
                    "type": "high_uniqueness",
                    "level": "info",
                    "message": f"唯一值率 {field_report['unique_rate']}% 极高，可能是ID字段"
                })

            # ---- 数值字段异常值检测 ----
            if pd.api.types.is_numeric_dtype(col_data):
                desc = col_data.describe()
                # 检测是否为常量
                if desc.get("std", 0) == 0 and len(col_data.dropna()) > 1:
                    field_report["issues"].append({
                        "type": "constant_value",
                        "level": "warning",
                        "message": "该字段所有值相同，可能是无效字段"
                    })

                # 检测负值异常（金额字段不应有大量负值）
                neg_count = (col_data < 0).sum()
                if neg_count > 0:
                    neg_rate = round(neg_count / len(col_data.dropna()) * 100, 2)
                    if neg_rate > 20:
                        field_report["issues"].append({
                            "type": "high_negative_rate",
                            "level": "warning",
                            "message": f"负值占比 {neg_rate}%，注意数据方向"
                        })

                # 检测空值行处理建议
                if field_report["null_rate"] > 0:
                    field_report["issues"].append({
                        "type": "has_null_values",
                        "level": "info",
                        "message": f"存在 {field_report['null_count']} 个空值，可能影响汇总"
                    })

            # ---- 文本字段异常值检测（通用模式） ----
            # 修复：pandas 2.x StringDtype 下 is_object_dtype 返回 False，
            # 文本检测永远不会执行，改用 is_string_dtype
            elif pd.api.types.is_string_dtype(col_data):
                # 检测格式一致性
                clean_samples = col_data.dropna().astype(str).str.strip()
                clean_samples = clean_samples[clean_samples != ""]
                if len(clean_samples) > 10:
                    # 检测是否有多样化的格式（如部分带前缀，部分不带）
                    has_prefix = clean_samples.str.contains(r"^【").sum()
                    has_suffix = clean_samples.str.contains(r"】$").sum()
                    prefix_rate = has_prefix / len(clean_samples) * 100
                    if 10 < prefix_rate < 90:
                        field_report["issues"].append({
                            "type": "inconsistent_format",
                            "level": "warning",
                            "message": f"格式不一致：{prefix_rate:.0f}% 数据带前缀【】"
                        })

                # 检测空字符串
                empty_count = (col_data.astype(str).str.strip() == "").sum()
                if empty_count > len(df) * 0.05:
                    field_report["issues"].append({
                        "type": "empty_strings",
                        "level": "warning",
                        "message": f"存在 {empty_count} 个空字符串，建议统一处理"
                    })

            report["fields"][col] = field_report

        # ---- 整体质量评分 ----
        critical_issues = sum(
            1 for f in report["fields"].values()
            for issue in f.get("issues", [])
            if issue.get("level") == "critical"
        )
        report["overall_score"] = max(0, 100 - critical_issues * 15)
        report["overall_status"] = "good" if report["overall_score"] >= 80 else "needs_review"

        return report

    # ==========================================================
    # 3. 生成通用的清洗建议
    # ==========================================================
    def _generate_clean_suggestions(self, df, columns, quality_report) -> Dict[str, Any]:
        """
        基于质量报告生成自动清洗建议
        """
        suggestions = {
            "recommendations": [],
            "actions": {}  # 字段级别的清洗操作
        }

        for col, info in quality_report["fields"].items():
            actions = []

            # ---- 空值处理 ----
            if info["null_rate"] > 30:
                actions.append({
                    "type": "drop_rows",
                    "condition": f"{col} is null",
                    "reason": f"空值率 {info['null_rate']}% 过高，建议删除这些行"
                })
            elif 10 < info["null_rate"] <= 30:
                actions.append({
                    "type": "fill_null",
                    "method": "mode",  # 用众数填充
                    "reason": f"空值率 {info['null_rate']}% 适中，建议用众数填充"
                })

            # ---- 文本字段清洗（样本驱动，修复：不再硬编码"【】"）
            #
            # 从实际样本统计前后缀：仅当覆盖率 > 50% 时生成清洗动作，
            # 并记录样本中真实出现的前缀（如"【客商："）与后缀（"】"），
            # 样本不含该模式则完全不生成，避免误伤正常文本列。
            # --------------------------------------------------
            if pd.api.types.is_string_dtype(df[col]):
                import re as _re

                samples = df[col].dropna().astype(str).str.strip()
                samples = samples[samples != ""]

                if len(samples) > 10:

                    wrapped = samples.str.startswith("【")

                    coverage = float(wrapped.sum()) / len(samples)

                    if coverage > 0.5:

                        # 统计样本中出现最多的前缀标签（【label：）
                        label_count = {}

                        for sample in samples[wrapped].head(200):

                            match = _re.match(
                                r"^【([^【】:：]+)[:：]",
                                sample
                            )

                            if match:

                                label = match.group(1)

                                label_count[label] = (
                                    label_count.get(label, 0) + 1
                                )

                        if label_count:

                            label = max(
                                label_count,
                                key=label_count.get
                            )

                            actions.append({
                                "type": "clean_prefix",
                                "prefix": f"【{label}：",
                                "suffix": "】",
                                "reason": (
                                    f"数据包含统一前缀格式【{label}：...】"
                                    f"（覆盖率{coverage:.0%}），"
                                    f"建议提取干净的名称"
                                )
                            })

            if actions:
                suggestions["actions"][col] = actions

        # ---- 整体建议 ----
        if quality_report["overall_score"] < 80:
            suggestions["recommendations"].append({
                "level": "critical",
                "message": "数据质量一般，建议在分析前执行推荐的清洗操作"
            })

        if quality_report["total_rows"] > 10000:
            suggestions["recommendations"].append({
                "level": "info",
                "message": f"数据量较大（{quality_report['total_rows']}行），建议分批处理或采样分析"
            })

        return suggestions

    # ==========================================================
    # 4. 应用清洗建议（工具可调用的辅助方法）
    # ==========================================================
    @staticmethod
    def apply_clean_suggestions(df: pd.DataFrame, suggestions: Dict) -> pd.DataFrame:
        """
        工具函数：根据清洗建议执行数据清洗
        返回清洗后的DataFrame
        """
        df_cleaned = df.copy()

        for col, actions in suggestions.get("actions", {}).items():
            if col not in df_cleaned.columns:
                continue

            for action in actions:
                action_type = action.get("type")

                # ---- 删除空值行 ----
                if action_type == "drop_rows":
                    df_cleaned = df_cleaned[df_cleaned[col].notna()]

                # ---- 用众数填充 ----
                elif action_type == "fill_null":
                    mode_val = df_cleaned[col].mode()
                    if len(mode_val) > 0:
                        df_cleaned[col] = df_cleaned[col].fillna(mode_val[0])

                # ---- 清理前缀（样本驱动：仅剥离实际统计出的前后缀）----
                elif action_type == "clean_prefix":
                    prefix = action.get("prefix", "")
                    suffix = action.get("suffix", "")
                    cleaned = df_cleaned[col].astype(str).str.strip()
                    if prefix:
                        mask = cleaned.str.startswith(prefix)
                        cleaned[mask] = cleaned[mask].str[len(prefix):]
                    if suffix:
                        cleaned = cleaned.str.replace(suffix, "", regex=False)
                    df_cleaned[col] = cleaned.str.strip()

        return df_cleaned

    # ==========================================================
    # 5. 选择Sheet
    #
    # 通用化：先尝试 LLM 判断（输入各表列名 + 前2行样本 + 用户
    # 问题），失败或 DISABLE_LLM_SCHEMA=1 时降级为通用打分：
    # 命中 schema.roles 任意角色的列数 + 非空密度，不再依赖任何
    # 财务关键词。
    # ==========================================================
    def select_sheet(self, sheet_profiles, query, schema=None):

        if len(sheet_profiles) <= 1:

            return sheet_profiles[0]

        # ----------------------------------------------
        # 1. LLM 判断（可被 DISABLE_LLM_SCHEMA=1 关闭）
        # ----------------------------------------------

        if not os.environ.get("DISABLE_LLM_SCHEMA") == "1":

            selected = self._select_sheet_with_llm(
                sheet_profiles,
                query
            )

            if selected:

                return selected

        # ----------------------------------------------
        # 2. 通用打分降级
        # ----------------------------------------------

        return self._select_sheet_by_score(
            sheet_profiles,
            schema
        )

    def _select_sheet_with_llm(self, sheet_profiles, query):
        """LLM 判断最相关 Sheet，失败返回 None"""

        try:

            lines = []

            for i, sheet in enumerate(sheet_profiles, 1):

                df = sheet["df"]

                lines.append(
                    f"表{i}名称: {sheet['sheet']}"
                )

                lines.append(
                    f"列: {list(df.columns)}"
                )

                lines.append(
                    f"样本: {df.head(2).to_dict(orient='records')}"
                )

            prompt = (
                f"用户问题: {query}\n\n"
                f"数据表概况:\n{chr(10).join(lines)}\n\n"
                "只输出JSON（不要任何其他内容），选择与用户问题"
                "最相关的一张表：\n"
                '{"sheet": "表名"} 或 {"sheet": null}（无法判断时）'
            )

            result = self.llm.chat_json([

                {
                    "role": "system",
                    "content": "你是数据表选择器，只输出JSON。"
                },

                {
                    "role": "user",
                    "content": prompt
                }
            ])

            if not result:

                return None

            name = str(result.get("sheet", "")).strip()

            if not name:

                return None

            # 精确 / 包含匹配
            for sheet in sheet_profiles:

                if str(sheet["sheet"]) == name:

                    return sheet

            for sheet in sheet_profiles:

                if (
                    name in str(sheet["sheet"])
                    or
                    str(sheet["sheet"]) in name
                ):

                    return sheet

        except Exception as e:

            print(
                f"select_sheet LLM失败，降级通用打分: {e}"
            )

        return None

    def _select_sheet_by_score(self, sheet_profiles, schema):
        """
        通用打分：命中 schema.roles 任意角色的列数 × 10
        + 非空密度（0~1）
        """

        best_sheet = None

        max_score = -1

        # 收集 schema 角色列（去 Sheet 前缀）
        role_columns = set()

        if schema:

            roles = schema.get(
                "roles",
                {}
            ) or {}

            for fields in roles.values():

                for field in fields:

                    role_columns.add(
                        str(field).split(".", 1)[-1]
                    )

        for sheet in sheet_profiles:

            df = sheet["df"]

            columns = list(df.columns)

            role_hit = sum(
                1
                for col in columns
                if col in role_columns
            )

            if len(df) > 0:

                density = float(
                    df.notna().mean().mean()
                )

            else:

                density = 0.0

            score = role_hit * 10 + density

            print(
                f"Sheet通用评分: {sheet['sheet']} "
                f"-> {score:.2f} "
                f"(角色命中{role_hit}, 密度{density:.2f})"
            )

            if score > max_score:

                max_score = score

                best_sheet = sheet

        return best_sheet