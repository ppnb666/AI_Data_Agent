"""
大模型客户端 - 负责与大模型 API 通信
"""

import os
import sys
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 修复 Windows 编码问题
if sys.platform == 'win32':
    import locale
    locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')

# 强制使用 UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

load_dotenv()


class LLMClient:
    """
    大模型客户端
    支持 OpenAI API 格式的模型
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        """
        初始化大模型客户端
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "deepseek-chat")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
        self.temperature = temperature
        self.max_tokens = max_tokens

        if not self.api_key:
            print("⚠️ 警告：未设置 OPENAI_API_KEY")
            print("   请在 .env 文件中配置")

    def chat(self, messages: list) -> str:
        """
        发送对话请求
        """
        try:
            from openai import OpenAI

            client_kwargs = {
                "api_key": self.api_key,
            }
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            client = OpenAI(**client_kwargs)

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            return response.choices[0].message.content

        except ImportError:
            print("❌ 未安装 openai 库，请执行：pip install openai")
            return ""
        except Exception as e:
            print(f"❌ API 调用失败：{e}")
            return ""

    def summarize_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """
        总结数据分析结果
        """
        # 使用纯英文 prompt 避免编码问题
        prompt = f"""You are a data analyst. Analyze the following sales data and provide insights.

Data Summary:
- Total records: {analysis_data.get('total_count', 0)}
- Records cleaned: {analysis_data.get('clean_count', 0)}
- Top product: {analysis_data.get('top_product', 'Unknown')}
- Top sales: {analysis_data.get('top_sales', 0)}
- Outliers detected: {analysis_data.get('outlier_count', 0)}
- Columns: {', '.join(analysis_data.get('columns', []))}

Please provide:
1. Data quality assessment
2. Sales performance analysis
3. Business recommendations

Respond in Chinese (中文). Keep it under 200 words.
"""

        messages = [
            {"role": "system", "content": "You are a professional data analyst. Respond in Chinese."},
            {"role": "user", "content": prompt}
        ]

        result = self.chat(messages)

        # 如果结果为空，尝试纯英文 prompt
        if not result:
            print("⚠️ 中文回复失败，尝试英文...")
            eng_prompt = f"""Analyze sales data:
Total: {analysis_data.get('total_count', 0)}
Top product: {analysis_data.get('top_product', 'Unknown')}
Top sales: {analysis_data.get('top_sales', 0)}
Outliers: {analysis_data.get('outlier_count', 0)}

Provide: data quality, sales analysis, recommendations. Keep concise."""
            messages = [
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": eng_prompt}
            ]
            result = self.chat(messages)

        return result


# 默认客户端实例
default_client = LLMClient()


def get_client(
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> LLMClient:
    """获取大模型客户端实例"""
    return LLMClient(api_key=api_key, model=model)


def quick_summary(analysis_data: Dict[str, Any]) -> str:
    """快速生成分析总结"""
    return default_client.summarize_analysis(analysis_data)


if __name__ == "__main__":
    test_data = {
        "total_count": 100,
        "clean_count": 5,
        "top_product": "A产品",
        "top_sales": 50000,
        "outlier_count": 3,
        "columns": ["日期", "产品", "销售额"]
    }

    print("测试数据：")
    print(test_data)
    print("\n正在调用大模型总结...")
    result = quick_summary(test_data)
    print("\n" + "=" * 50)
    print(result if result else "❌ 调用失败")
    print("=" * 50)