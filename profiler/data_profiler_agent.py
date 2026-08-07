"""
DataProfiler Agent

负责:
1. 理解Excel结构
2. 判断数据类型
3. 识别关键字段
"""

import json


class DataProfilerAgent:

    def __init__(self, llm):

        self.llm = llm

    def analyze(self, df):

        # 基础信息

        columns = list(df.columns)

        sample = (
            df.head(5)
            .to_dict(
                orient="records"
            )
        )

        prompt = f"""

你是一个数据理解专家。

请分析下面Excel数据。

字段:

{columns}


前5行数据:

{sample}


请输出JSON格式:

{{
 "data_type":"",
 "description":"",
 "fields": {{

 }}
}}


data_type可选:

- finance 财务余额表
- contract 合同经营表
- sales 销售表
- inventory 库存表
- unknown


fields中识别:

customer:
客户/客商字段

amount:
金额字段

date:
日期字段

product:
产品字段

department:
部门字段


如果不存在字段填null。


只返回JSON，不要解释。

"""

        result = self.llm.chat(
            [
                {
                    "role": "system",
                    "content":
                        "You are a data profiling AI."
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ]
        )

        try:

            schema = json.loads(
                result
            )

        except Exception:

            schema = {
                "data_type": "unknown",
                "fields": {}
            }

        return schema

    def select_sheet(
            self,
            sheet_profiles,
            query
    ):

        # 根据用户问题判断关键词
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

            print(
                f"Sheet匹配评分:{sheet['sheet']} -> {score}"
            )

            if score > max_score:
                max_score = score
                best_sheet = sheet

        return best_sheet