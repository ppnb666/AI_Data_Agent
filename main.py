from agent import DataAgent
from config import DATA_PATH


agent = DataAgent()


query=input(
    "请输入你的分析需求："
)


result = agent.run(
    DATA_PATH,
    user_query=query,
    with_ai=True
)



print("\n======================")

print("📊 数据分析结果:")

print(result)



print("\n🤖 AI业务建议:")

print("----------------------")


print(
    result.get(
        "ai_insight",
        "没有生成AI建议"
    )
)


print("----------------------")