from agent import DataAgent
from config import DATA_PATH


agent = DataAgent()


query = input(
    "请输入你的分析需求："
)


result = agent.run(
    DATA_PATH,
    user_query=query,
    with_ai=False
)



print("\n======================")

print("📊 数据分析结果:")



query_result = result.get(
    "query_result"
)



if query_result:


    print("\n==========合同查询结果==========")



    print(
f"""
客户:
{query_result.get('customer')}


匹配合同数量:
业务匹配数量:
{query_result.get('business_count',0)} 条


余额记录数量:
{query_result.get('count',0)} 条

"""
    )



    summary = query_result.get(
        "summary",
        {}
    )

    print("\n金额汇总:")

    print(
        f"期初余额总额: {summary.get('期初余额总额', 0):,.2f}"
    )

    print(
        f"本期贷方总额: {summary.get('本期贷方总额', 0):,.2f}"
    )

    print(
        f"贷方累计总额: {summary.get('贷方累计总额', 0):,.2f}"
    )

    print(
        f"期末余额总额: {summary.get('期末余额总额', 0):,.2f}"
    )



else:

    print(
        "没有查询结果"
    )



print("\n🤖 AI业务建议:")

print("----------------------")


print(
    result.get(
        "ai_insight",
        "没有生成AI建议"
    )
)


print("----------------------")