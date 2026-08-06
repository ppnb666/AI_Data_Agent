"""
Agent State

保存Agent执行过程中的上下文
"""


from config import (
    CHART_PATH,
    TREND_CHART_PATH,
    REPORT_PATH,
    MD_REPORT_PATH
)

from utils.trace import AgentTrace

class AgentState:


    def __init__(self):


        # 用户请求

        self.user_query = ""


        # Excel路径

        self.file_path = ""



        # Planner计划

        self.plan = []



        # 当前执行工具

        self.current_tool = None



        # DataFrame

        self.df = None



        # 字段信息

        self.sales_col = None

        self.product_col = None

        self.date_col = None



        # 中间结果

        self.clean_count = 0

        self.top_product = None

        self.top_sales = 0

        self.outliers = []



        # 图表

        self.charts = {}


        self.chart_path = CHART_PATH

        self.trend_chart_path = TREND_CHART_PATH



        # 报告

        self.report = None

        self.report_path = REPORT_PATH



        # Markdown报告

        self.md_report = None

        self.md_report_path = MD_REPORT_PATH



        # 最终分析结果

        self.analysis_result = {}



        # 错误

        self.error = None

        # Agent执行轨迹

        self.trace = AgentTrace()




    def summary(self):

        return {


            "current_tool":
                self.current_tool,


            "has_data":
                self.df is not None,


            "top_product":
                self.top_product,


            "has_report":
                self.report is not None,


            "charts":
                self.charts

        }