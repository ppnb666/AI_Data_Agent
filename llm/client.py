"""
大模型客户端
负责调用 DeepSeek API
"""

import json
import os
import re
from typing import Optional, Dict, Any, List

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


    def chat_json(
            self,
            messages: list
    ) -> Optional[dict]:
        """
        调用 LLM 并解析 JSON 输出。

        自动去除 markdown 代码块标记，提取第一个 {...} 到最后一个 }。
        解析失败返回 None（调用方负责降级到关键词路径）。
        """
        text = self.chat(messages)

        if not text:
            return None

        text = text.strip()

        # 去除 markdown 代码块
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        start = text.find("{")

        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            return None

        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None


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