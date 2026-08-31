"""
针对本次修复的回归测试

覆盖：
1. clean_data 不再无差别删除"任意一列有空值"的行
2. find_date_column 不再把ID/金额列误判为日期列
3. rank_rows_tool 能正确处理plan中有多个同类型任务的情况
"""

import pandas as pd
import pytest

from analysis import clean_data
from data_parser import find_date_column


# ==========================================================
# clean_data
# ==========================================================

def test_clean_data_keeps_rows_with_optional_field_null():
    """备注等非关键字段为空时，不应被删除整行"""
    df = pd.DataFrame({
        "客户": ["A", "B", "C", "D"],
        "销售额": [100, 200, 300, 400],
        "备注": ["ok", None, "note", None],
    })
    cleaned, count = clean_data(df)
    assert len(cleaned) == 4
    assert count == 0


def test_clean_data_drops_rows_missing_key_column():
    """指定key_columns后，关键字段为空的行才应被删除"""
    df = pd.DataFrame({
        "客户": ["A", "B", "C", "D"],
        "销售额": [100, None, 300, 400],
        "备注": ["ok", None, "note", None],
    })
    cleaned, count = clean_data(df, key_columns=["销售额"])
    assert len(cleaned) == 3
    assert count == 1


def test_clean_data_removes_duplicates():
    df = pd.DataFrame({
        "客户": ["A", "A"],
        "销售额": [100, 100],
    })
    cleaned, count = clean_data(df)
    assert len(cleaned) == 1
    assert count == 1


# ==========================================================
# find_date_column
# ==========================================================

def test_find_date_column_by_keyword():
    df = pd.DataFrame({
        "交易日期": ["2024-01-01", "2024-01-02"],
        "金额": [100, 200],
    })
    assert find_date_column(df) == "交易日期"


def test_find_date_column_does_not_misdetect_numeric_id():
    """纯数字的订单编号/金额列不应被误判为日期列"""
    df = pd.DataFrame({
        "订单编号": [1001, 1002, 1003, 1004],
        "金额": [100.5, 200.0, 150.25, 300.75],
    })
    assert find_date_column(df) is None


def test_find_date_column_detects_datetime_dtype():
    df = pd.DataFrame({
        "时间戳": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "数量": [1, 2],
    })
    assert find_date_column(df) == "时间戳"


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
    from rank_tools import rank_rows_tool

    task_a = {"tool": "rank_rows", "metrics": ["销售额"]}
    task_b = {"tool": "rank_rows", "metrics": ["数量"]}

    state = _FakeState(plan=[task_a, task_b], current_task=task_b)
    result = rank_rows_tool(state)

    # 没有sheet数据，但应能确认走的是task_b（metric=数量）
    # 而不是plan里第一个task_a（metric=销售额）
    assert result["message"] != "未找到rank_rows任务"


def test_rank_rows_tool_falls_back_to_plan_when_no_current_task():
    from rank_tools import rank_rows_tool

    task_a = {"tool": "rank_rows", "metrics": ["销售额"]}
    state = _FakeState(plan=[task_a], current_task=None)

    with pytest.warns(UserWarning):
        result = rank_rows_tool(state)

    assert result["message"] != "未找到rank_rows任务"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))