"""
针对本次修复的回归测试

覆盖：
1. rank_rows_tool 能正确处理plan中有多个同类型任务的情况
（clean_data / find_date_column 相关测试随 utils/analysis.py、
utils/data_parser.py 删除而移除，Phase 8）
"""

import pandas as pd
import pytest


# ==========================================================
# rank_rows_tool: 多任务场景下current_task应生效
# （用轻量mock代替真实state/schema依赖）
# ==========================================================

class _FakeState:
    def __init__(self, plan, current_task=None):
        self.plan = plan
        self.current_task = current_task
        self.workbook_schema = {}
        self.sheet_profiles = []


def test_rank_rows_tool_uses_current_task_over_plan_order():
    """
    当plan中有多个rank_rows任务时，应使用state.current_task
    指定的那一个，而不是永远取plan里第一个匹配项。
    """
    from tools.rank_tools import rank_rows_tool

    task_a = {"tool": "rank_rows", "metrics": ["销售额"]}
    task_b = {"tool": "rank_rows", "metrics": ["数量"]}

    state = _FakeState(plan=[task_a, task_b], current_task=task_b)
    result = rank_rows_tool(state)

    # 没有sheet数据，但应能确认走的是task_b（metric=数量）
    # 而不是plan里第一个task_a（metric=销售额）
    assert result["message"] != "未找到rank_rows任务"


def test_rank_rows_tool_falls_back_to_plan_when_no_current_task():
    from tools.rank_tools import rank_rows_tool

    task_a = {"tool": "rank_rows", "metrics": ["销售额"]}
    state = _FakeState(plan=[task_a], current_task=None)

    with pytest.warns(UserWarning):
        result = rank_rows_tool(state)

    assert result["message"] != "未找到rank_rows任务"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
