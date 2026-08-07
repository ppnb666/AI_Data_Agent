"""
LLM Agent任务规划器 V7

职责:

1. 理解用户意图
2. 判断任务类型
3. 选择执行工具
4. 提取查询参数

支持:

query_value:
查询数据

compare_rows:
字段比较

aggregate_value:
汇总统计

rank_rows:
排序排名

detect_anomaly:
异常检测
"""

import json
import logging

from tools import tool_registry


class TaskPlanner:

    def __init__(
        self,
        llm_client
    ):

        self.llm = llm_client

        self.logger = logging.getLogger(
            __name__
        )


    def create_plan(
        self,
        user_query: str
    ):

        tools = tool_registry.list_tools()


        prompt = f"""

你是企业级AI数据分析Agent规划器。


你的任务:

根据用户自然语言需求，
生成执行计划。


======================

可用工具:

{tools}

======================


【任务分类规则】


一、普通查询

用户出现:

查询
查
查看
多少
余额
金额


选择:

query_value


返回:

{{
"tool":"query_value",
"customer":"客户名称",
"metrics":["字段"],
"filters":{{}}
}}


======================


二、字段比较 ⭐


用户出现:

比较

是否相等

是否一致

相同

一样

不相等

不同

差异

大于

超过

高于

小于

低于

不少于

不超过


选择:

compare_rows



======================


【比较运算符规则】


相等:

是否相等
等于
一致
相同
一样


operator:

"=="


----------------------


不相等:

不相等
不同
不一致
差异
有差别


operator:

"!="


----------------------


大于:

大于
超过
高于


operator:

">"


----------------------


小于:

小于
低于


operator:

"<"


----------------------


大于等于:

不少于
至少


operator:

">="


----------------------


小于等于:

不超过
最多


operator:

"<="



======================


【compare格式】


必须返回:


"compare":
{{
    "left":"字段1",
    "right":"字段2或者数字",
    "operator":"运算符"
}}



======================


示例:


用户:

查询A公司本期贷方和贷方累计是否相等


返回:

[
{{
"tool":"compare_rows",

"customer":"A公司",

"filters":{{}},

"compare":
{{
"left":"本期贷方",

"right":"贷方累计",

"operator":"=="
}},

"output":"rows"

}}
]




用户:

查询A公司本期贷方和贷方累计不相等的数据


返回:

[
{{
"tool":"compare_rows",

"customer":"A公司",

"filters":{{}},

"compare":
{{
"left":"本期贷方",

"right":"贷方累计",

"operator":"!="
}},

"output":"rows"

}}
]




用户:

查询A公司期末余额大于100万的数据


返回:

[
{{
"tool":"compare_rows",

"customer":"A公司",

"filters":{{}},

"compare":
{{
"left":"期末余额",

"right":"100万",

"operator":">"
}},

"output":"rows"

}}
]



======================


三、汇总统计


用户出现:

合计

总额

统计

汇总


选择:

aggregate_value



======================


四、排序排名


用户出现:

最高

最低

排名

TOP


选择:

rank_rows



======================


五、异常检测


用户出现:

异常

波动

异常数据


选择:

detect_anomaly



======================


【字段提取规则】


客户:

必须完整保留。


例如:

正确:

保利长大工程有限公司


错误:

保利长大



业务条件:

必须放入filters。


例如:


用户:

业务类型（新）:
公路建设期产品运维(JSYW)



返回:


"filters":

{{
"业务类型（新）":
"公路建设期产品运维(JSYW)"
}}



======================


【输出格式】


只能返回JSON数组。

禁止解释。



格式:


[
{{
"tool":"",

"reason":"",

"customer":"",

"metrics":[],

"filters":{{}},

"compare":{{}},

"condition":{{}},

"output":""
}}
]



用户需求:

{user_query}

"""


        messages = [

            {
                "role":"system",

                "content":
                """
你是企业数据Agent规划器。
只能输出JSON数组。
"""
            },

            {
                "role":"user",

                "content":prompt
            }

        ]


        try:

            response = self.llm.chat(
                messages
            )


            print(
                "\n===== DeepSeek Planner原始返回 ====="
            )

            print(response)



            response = response.strip()



            if response.startswith("```"):

                response = (
                    response
                    .replace("```json","")
                    .replace("```","")
                    .strip()
                )


            plan = json.loads(
                response
            )


            valid=[]


            for task in plan:

                tool = task.get(
                    "tool"
                )


                if tool not in tools:

                    print(
                        "忽略不存在工具:",
                        tool
                    )

                    continue



                valid.append(

                    {

                    "tool":tool,

                    "reason":
                    task.get(
                        "reason",
                        ""
                    ),

                    "customer":
                    task.get(
                        "customer",
                        ""
                    ),

                    "metrics":
                    task.get(
                        "metrics",
                        []
                    ),

                    "filters":
                    task.get(
                        "filters",
                        {}
                    ),

                    "compare":
                    task.get(
                        "compare",
                        {}
                    ),

                    "condition":
                    task.get(
                        "condition",
                        {}
                    ),

                    "output":
                    task.get(
                        "output",
                        ""
                    )

                    }

                )


            print(
                "\n===== V7 Planner计划 ====="
            )

            print(valid)


            return valid



        except Exception as e:


            self.logger.error(
                f"Planner失败:{e}"
            )


            print(
                "Planner失败:",
                e
            )


            return self.fallback_plan(
                user_query
            )



    def fallback_plan(
        self,
        query
    ):


        compare_keywords = [

            "比较",
            "是否",
            "相等",
            "一致",
            "不相等",
            "不同",
            "差异",
            "大于",
            "超过",
            "高于",
            "小于",
            "低于",
            "不少于",
            "不超过"

        ]


        if any(
            k in query
            for k in compare_keywords
        ):


            if any(
                k in query
                for k in [
                    "相等",
                    "一致",
                    "相同",
                    "一样"
                ]
            ):

                operator="=="


            elif any(
                k in query
                for k in [
                    "大于",
                    "超过",
                    "高于"
                ]
            ):

                operator=">"


            elif any(
                k in query
                for k in [
                    "小于",
                    "低于"
                ]
            ):

                operator="<"


            else:

                operator="!="



            return [

                {

                "tool":
                "compare_rows",

                "reason":
                "关键词判断比较任务",

                "compare":
                {
                    "operator":operator
                }

                }

            ]


        return [

            {

            "tool":
            "query_value",

            "reason":
            "默认查询"

            }

        ]