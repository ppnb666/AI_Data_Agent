"""
大模型客户端
负责调用 DeepSeek API
"""

import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv


load_dotenv()



class LLMClient:
    """
    大模型客户端
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            model: Optional[str] = None,
            base_url: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 2000
    ):


        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
        )


        self.model = (
            model
            or os.getenv(
                "OPENAI_MODEL",
                "deepseek-chat"
            )
        )


        self.base_url = (
            base_url
            or os.getenv(
                "OPENAI_BASE_URL",
                "https://api.deepseek.com/v1"
            )
        )


        self.temperature = temperature

        self.max_tokens = max_tokens



        if not self.api_key:

            print(
                "⚠️ 未配置 OPENAI_API_KEY"
            )



    def chat(
            self,
            messages:list
    ) -> str:


        try:

            from openai import OpenAI


            client = OpenAI(

                api_key=self.api_key,

                base_url=self.base_url

            )


            response = client.chat.completions.create(

                model=self.model,

                messages=messages,

                temperature=self.temperature,

                max_tokens=self.max_tokens

            )


            return (
                response
                .choices[0]
                .message
                .content
            )


        except Exception as e:


            print(
                f"❌ DeepSeek调用失败:{e}"
            )

            return ""





    def summarize_analysis(
            self,
            analysis_data:Dict[str,Any]
    ) -> str:


        prompt=f"""

你是企业数据分析专家。


请根据以下分析结果生成业务分析。


数据:

记录数量:
{analysis_data.get("total_count")}


清洗数量:
{analysis_data.get("clean_count")}


最高销售:
{analysis_data.get("top_sales")}


异常数量:
{analysis_data.get("outlier_count")}


字段:
{analysis_data.get("columns")}



请输出:

1. 数据质量评价

2. 业务分析

3. 改进建议


要求:
中文输出
200字以内

"""


        messages=[


            {
                "role":"system",
                "content":
                "你是一名专业数据分析师"
            },


            {
                "role":"user",
                "content":prompt
            }


        ]


        return self.chat(messages)




# ==========================
# 默认客户端
# ==========================


default_client = LLMClient()



def get_client(

        api_key:Optional[str]=None,

        model:Optional[str]=None

):


    return LLMClient(

        api_key=api_key,

        model=model

    )




def quick_summary(
        analysis_data
):


    return default_client.summarize_analysis(
        analysis_data
    )




if __name__=="__main__":


    test_data={

        "total_count":100,

        "clean_count":5,

        "top_sales":50000,

        "outlier_count":3,

        "columns":[
            "日期",
            "产品",
            "销售额"
        ]

    }


    print(
        quick_summary(test_data)
    )