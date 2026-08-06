"""
Agent执行轨迹记录
"""

import json
from datetime import datetime


class AgentTrace:


    def __init__(self):

        self.steps=[]


    def add_step(
            self,
            tool,
            status,
            message=""
    ):

        self.steps.append({

            "tool":tool,

            "status":status,

            "message":message,

            "time":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        })


    def save(
            self,
            path="logs/agent_trace.json"
    ):

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.steps,
                f,
                ensure_ascii=False,
                indent=4
            )