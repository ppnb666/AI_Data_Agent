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
            elif pd.api.types.is_object_dtype(col_data):
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

            # ---- 文本字段清洗 ----
            if pd.api.types.is_object_dtype(df[col]):
                # 检测是否有"【前缀】"模式需要清理
                samples = df[col].dropna().astype(str)
                if len(samples) > 10:
                    has_prefix = samples.str.contains(r"^【").sum()
                    if has_prefix / len(samples) > 0.5:
                        actions.append({
                            "type": "clean_prefix",
                            "pattern": r"^【.*?：",
                            "suffix_pattern": r"】$",
                            "reason": "数据包含统一的前缀格式，建议提取干净的名称"
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

                # ---- 清理前缀 ----
                elif action_type == "clean_prefix":
                    pattern = action.get("pattern", r"^【.*?：")
                    suffix = action.get("suffix_pattern", r"】$")
                    df_cleaned[col] = df_cleaned[col].astype(str).str.replace(pattern, "", regex=True)
                    df_cleaned[col] = df_cleaned[col].str.replace(suffix, "", regex=True)
                    df_cleaned[col] = df_cleaned[col].str.strip()

        return df_cleaned

    # ==========================================================
    # 5. 选择Sheet（原有逻辑）
    # ==========================================================
    def select_sheet(self, sheet_profiles, query):
        keywords = []
        if "业务类型" in query or "业务类型（新）" in query:
            keywords.append("业务类型")
        if "本期贷方" in query:
            keywords.append("本期贷方")
        if "贷方累计" in query:
            keywords.append("贷方累计")
        if "客商" in query or "客户" in query:
            keywords.append("客商名称")

        best_sheet = None
        max_score = -1

        for sheet in sheet_profiles:
            score = 0
            columns = sheet["df"].columns.tolist()
            for key in keywords:
                for col in columns:
                    if key in str(col):
                        score += 1
            print(f"Sheet匹配评分:{sheet['sheet']} -> {score}")

            if score > max_score:
                max_score = score
                best_sheet = sheet

        return best_sheet