# ==============================
# 先加载工具注册
# 必须放最前面
# ==============================

import tools


from agent import DataAgent
from config import DATA_PATH



def main():

    agent = DataAgent()


    query = input(
        "请输入你的分析需求："
    )


    result = agent.run(
        DATA_PATH,
        user_query=query,
        with_ai=False
    )


    print(
        "\n======================"
    )

    print(
        "📊 数据分析结果:"
    )


    query_result = result.get(
        "query_result"
    )


    if query_result:


        print(
            "\n==========查询结果=========="
        )


        print(query_result)


    else:

        print(
            "没有查询结果"
        )


    print(
        "\n🤖 AI业务建议:"
    )

    print(
        result.get(
            "ai_insight",
            "没有生成AI建议"
        )
    )



if __name__ == "__main__":

    main()