"""
Agent Executor

职责:

1. 接收Planner任务
2. 根据task选择工具
3. 调用Tool
4. 返回执行结果

Planner负责想
Executor负责做
Tool负责计算
"""


from tools import tool_registry



class AgentExecutor:


    def __init__(self):

        self.registry = tool_registry



    def execute(
            self,
            task,
            state
    ):


        tool_name = task.get(
            "tool"
        )


        print(
            f"\n🚀 Executor执行:{tool_name}"
        )


        tool = self.registry.get_tool(
            tool_name
        )


        if not tool:


            return {

                "status":
                "failed",

                "message":
                f"工具不存在:{tool_name}"

            }



        try:


            result = tool["function"](
                state
            )


            return {


                "status":
                "success",


                "tool":
                tool_name,


                "result":
                result


            }



        except Exception as e:


            return {


                "status":
                "failed",


                "tool":
                tool_name,


                "message":
                str(e)

            }