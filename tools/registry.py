"""
Agent工具注册中心
"""

from typing import Dict, Callable


class ToolRegistry:
    """
    管理Agent可调用工具
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}


    def register(
        self,
        name: str,
        description: str,
        func: Callable
    ):
        """
        注册工具
        """

        self.tools[name] = {
            "description": description,
            "function": func
        }


    def get_tool(self, name:str):
        """
        获取工具
        """

        return self.tools.get(name)


    def list_tools(self):
        """
        查看所有工具
        """

        return {
            name:data["description"]
            for name,data in self.tools.items()
        }


# 创建全局注册器

tool_registry = ToolRegistry()