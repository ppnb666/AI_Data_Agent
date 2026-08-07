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

        prompt = f"""

    你是Excel数据分析专家。


    用户需求:

    {query}


    下面是Excel所有Sheet信息:

    {sheet_profiles}



    请选择最适合分析的Sheet。


    只返回Sheet名称。


    """

        result = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": "你负责Excel结构理解"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        sheet_name = result.strip()

        for sheet in sheet_profiles:

            if sheet["sheet"] in sheet_name:
                return sheet

        # 防止AI乱返回

        return sheet_profiles[0]