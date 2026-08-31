"""
Agent State

保存Agent执行过程中的上下文
"""


from config import (
    REPORT_PATH,
    MD_REPORT_PATH
)

from utils.trace import AgentTrace
# state.py

class AgentState:


    def __init__(self):


        # 用户请求

        self.user_query = ""

        self.data_quality_report = {}  # 数据质量报告
        self.clean_suggestions = {}  # 清洗建议


        # Excel路径

        self.file_path = ""



        # Planner计划

        self.plan = []



        # 当前执行工具

        self.current_tool = None

        # 当前正在执行的task（修复rank_rows_tool等工具需要读取
        # 当前task而非回头搜索state.plan的问题）
        self.current_task = None



        # DataFrame

        self.df = None

        self.data_profile = {}



        # 中间结果

        self.clean_count = 0

        self.outliers = []



        # 报告

        self.report = None

        self.report_path = REPORT_PATH



        # Markdown报告

        self.md_report = None

        self.md_report_path = MD_REPORT_PATH



        # 最终分析结果

        self.analysis_result = {}

        # 查询结果

        self.query_result = {}



        # 错误

        self.error = None

        # Agent执行轨迹

        self.trace = AgentTrace()

        self.mapping = {}




    def summary(self):

        return {


            "current_tool":
                self.current_tool,


            "has_data":
                self.df is not None,


            "has_report":
                self.report is not None,


            "query_result":
                self.query_result

        }