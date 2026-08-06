"""
Tool Registry

Agent工具注册中心
"""


class ToolRegistry:


    def __init__(self):

        self.tools = {}



    def register(
            self,
            name,
            description,
            function
    ):


        self.tools[name] = {


            "name":
                name,


            "description":
                description,


            "function":
                function

        }



    def get_tool(
            self,
            name
    ):


        return self.tools.get(
            name
        )



    def list_tools(self):


        return self.tools





# 全局工具注册中心

tool_registry = ToolRegistry()