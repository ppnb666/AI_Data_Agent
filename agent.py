"""
AI Agent - 智能数据分析决策层
基于 Tool Registry 的工具调用架构
"""

import pandas as pd
import logging
from typing import Dict, Any

from config import (
    DATA_PATH,
    REPORT_PATH,
    CHART_PATH,
    MD_REPORT_PATH,
    TREND_CHART_PATH
)

# 只保留报告生成相关的工具
from utils.analysis import (
    generate_report,
    generate_markdown_report
)

# 工具注册中心
from tools import tool_registry
from utils.data_parser import detect_columns
from utils.visualization import plot_product_sales, plot_sales_trend
from llm.client import LLMClient, get_client


class DataAgent:
    """
    数据分析 Agent - 基于 Tool Registry 架构

    职责：
    1. 接收用户需求（文件路径）
    2. 通过 Tool Registry 调用工具执行数据分析
    3. 生成报告
    4. 调用大模型生成业务洞察
    """

    def __init__(self, llm_client: LLMClient = None):
        """
        初始化 Agent

        参数：
        llm_client: 大模型客户端（如果不传，使用默认）
        """
        self.logger = logging.getLogger(__name__)
        self.llm = llm_client or get_client()

        # 存储分析结果
        self.analysis_result = {}

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        执行完整的数据分析流程

        参数：
        file_path: Excel 文件路径

        返回：
        分析结果字典
        """
        self.logger.info("=" * 50)
        self.logger.info("🤖 Agent 开始执行数据分析")
        self.logger.info(f"📁 数据文件：{file_path}")

        try:
            # 1. 读取数据
            self.logger.info("📖 步骤 1/6：读取数据")
            df = pd.read_excel(file_path)
            self.logger.info(f"✅ 读取成功，共 {len(df)} 行数据")

            # 2. 检测列名
            self.logger.info("🔍 步骤 2/6：自动检测列名")
            columns = detect_columns(df)
            sales_col = columns.get('sales_column')
            product_col = columns.get('product_column')
            date_col = columns.get('date_column')

            self.logger.info(f"  销售额列：{sales_col}")
            self.logger.info(f"  产品列：{product_col}")
            self.logger.info(f"  日期列：{date_col}")

            if sales_col is None or product_col is None:
                self.logger.error("❌ 未能检测到关键列，请检查数据格式")
                return {"error": "未能检测到关键列"}

            # ============================================================
            # 3. 数据清洗
            # ============================================================

            self.logger.info("🧹 步骤 3/6：数据清洗")

            clean_tool = tool_registry.get_tool("clean_data")

            if clean_tool is None:
                return {"error": "工具未注册: clean_data"}

            clean_result = clean_tool["function"](df)
            print("调用工具：clean_data")

            df_cleaned = clean_result["data"]

            clean_count = clean_result["clean_count"]

            self.logger.info(
                f"✅ 清洗完成，删除 {clean_count} 条数据"
            )

            # ============================================================
            # 4. 数据分析 - 通过 Tool Registry 调用
            # ============================================================
            self.logger.info("📊 步骤 4/6：数据分析")

            # ============================================================
            # 4. 数据分析 - 通过 Tool Registry 调用
            # ============================================================
            self.logger.info("📊 步骤 4/6：数据分析")

            # 4.1 销售冠军分析
            top_tool = tool_registry.get_tool("top_product")

            if top_tool is None:
                self.logger.error("❌ 未找到 top_product 工具")
                return {"error": "工具未注册: top_product"}

            top_result = top_tool["function"](
                df_cleaned,
                sales_col,
                product_col
            )

            top_product = top_result["product"]
            top_sales = top_result["sales"]

            self.logger.info(
                f"🏆 销售冠军：{top_product}，销售额：{top_sales}"
            )
            print("调用工具：top_product")

            # 4.2 异常检测
            outlier_tool = tool_registry.get_tool("detect_outliers")
            if outlier_tool is None:
                self.logger.error("❌ 未找到 detect_sales_outliers 工具")
                return {"error": "工具未注册: detect_sales_outliers"}

            outlier_result = outlier_tool["function"](
                df_cleaned,
                sales_col
            )

            outliers = outlier_result["data"]

            self.logger.info(f"⚠️ 异常数据：{len(outliers)} 条")
            print("调用工具：detect_outliers")

            # ============================================================
            # 5. 生成图表 - Tool Registry调用
            # ============================================================

            self.logger.info("📈 步骤 5/6：生成可视化图表")

            chart_tool = tool_registry.get_tool(
                "create_chart"
            )

            if chart_tool is None:
                return {
                    "error": "工具未注册: create_chart"
                }

            chart_result = chart_tool["function"](
                df_cleaned,
                product_col,
                sales_col,
                CHART_PATH,
                date_col,
                TREND_CHART_PATH
            )

            self.logger.info(
                f"✅ 图表生成完成：{chart_result}"
            )

            # ============================================================
            # 6. 生成报告 - Tool Registry调用
            # ============================================================

            self.logger.info("📝 步骤 6/6：生成报告")

            # 文本报告

            report_tool = tool_registry.get_tool(
                "generate_report"
            )

            if report_tool is None:
                return {
                    "error": "工具未注册: generate_report"
                }

            report_result = report_tool["function"](
                df_cleaned,
                clean_count,
                top_product,
                top_sales,
                REPORT_PATH
            )

            # Markdown报告

            md_tool = tool_registry.get_tool(
                "generate_markdown_report"
            )

            if md_tool is None:
                return {
                    "error": "工具未注册: generate_markdown_report"
                }

            md_result = md_tool["function"](
                df_cleaned,
                clean_count,
                top_product,
                top_sales,
                outliers,
                MD_REPORT_PATH
            )

            self.logger.info(
                f"✅ 报告生成完成：{report_result}"
            )

            # 7. 收集分析结果
            self.analysis_result = {
                "total_count": len(df_cleaned),
                "clean_count": clean_count,
                "top_product": top_product,
                "top_sales": top_sales,
                "outlier_count": len(outliers),
                "columns": list(df_cleaned.columns),
                "raw_data": df_cleaned
            }

            self.logger.info("=" * 50)
            self.logger.info("✅ 数据分析完成！")

            return self.analysis_result

        except FileNotFoundError:
            self.logger.error(f"❌ 文件未找到：{file_path}")
            return {"error": "文件未找到"}
        except Exception as e:
            self.logger.error(f"❌ 分析失败：{e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"error": str(e)}

    def get_summary(self) -> str:
        """
        获取分析结果的文本摘要
        """
        result = self.analysis_result
        if not result:
            return "暂无分析结果"

        summary = f"""
========== 分析摘要 ==========

📊 数据总量：{result.get('total_count', 0)} 条
🧹 清洗删除：{result.get('clean_count', 0)} 条
🏆 销售冠军：{result.get('top_product', '未知')}
💰 最高销售额：{result.get('top_sales', 0)}
⚠️ 异常数据：{result.get('outlier_count', 0)} 条
📋 字段列表：{', '.join(result.get('columns', []))}

================================
"""
        return summary

    def get_ai_insight(self) -> str:
        """
        调用大模型生成业务洞察
        """
        if not self.analysis_result:
            return "请先执行数据分析"

        try:
            self.logger.info("🤖 正在调用大模型生成业务洞察...")

            # 准备数据
            insight_data = {
                "total_count": self.analysis_result.get("total_count", 0),
                "clean_count": self.analysis_result.get("clean_count", 0),
                "top_product": self.analysis_result.get("top_product", "未知"),
                "top_sales": self.analysis_result.get("top_sales", 0),
                "outlier_count": self.analysis_result.get("outlier_count", 0),
                "columns": self.analysis_result.get("columns", [])
            }

            # 调用大模型
            insight = self.llm.summarize_analysis(insight_data)

            if insight:
                self.logger.info("✅ 业务洞察生成成功")
                return insight
            else:
                return "⚠️ 大模型调用失败，请检查 API 配置"

        except Exception as e:
            self.logger.error(f"❌ 生成洞察失败：{e}")
            return f"❌ 生成洞察失败：{e}"

    def run(self, file_path: str, with_ai: bool = True) -> Dict[str, Any]:
        """
        一站式运行完整流程

        参数：
        file_path: 数据文件路径
        with_ai: 是否生成 AI 洞察

        返回：
        包含所有结果和洞察的字典
        """
        # 执行分析
        result = self.analyze(file_path)

        if "error" in result:
            return result

        # 生成 AI 洞察
        if with_ai and self.llm.api_key:
            insight = self.get_ai_insight()
            result["ai_insight"] = insight
        else:
            result["ai_insight"] = "未启用 AI 洞察（请设置 API Key）"

        # 打印摘要
        print(self.get_summary())

        if result.get("ai_insight"):
            print("\n🤖 AI 业务洞察：")
            print("-" * 30)
            print(result["ai_insight"])
            print("-" * 30)

        return result


def main():
    """
    测试 Agent
    """
    # 初始化 Agent
    agent = DataAgent()

    # 执行分析
    result = agent.run(DATA_PATH, with_ai=True)

    # 打印结果
    print("\n✅ 运行完成！")


if __name__ == "__main__":
    main()