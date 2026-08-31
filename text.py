"""
field_resolver 回归测试

核心场景：验证 state.mapping（用户在前端手动确认/纠正过的映射）
优先于 schema['entities']（LLM自动猜测），而不是像修复前那样
被静默忽略。
"""

import pytest

from tools.field_resolver import find_customer_field, resolve_field


class FakeState:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}


COLUMNS = ["客商名称", "金额", "备注"]
SCHEMA_CORRECT = {"entities": {"customer": ["Sheet1.客商名称"]}}
SCHEMA_WRONG = {"entities": {"customer": ["Sheet1.备注"]}}
SCHEMA_EMPTY = {"entities": {}}


def test_no_user_mapping_falls_back_to_schema():
    state = FakeState(mapping={})
    assert find_customer_field(state, SCHEMA_CORRECT, COLUMNS) == "客商名称"


def test_user_mapping_matches_schema():
    state = FakeState(mapping={"customer": "客商名称"})
    assert find_customer_field(state, SCHEMA_CORRECT, COLUMNS) == "客商名称"


def test_user_correction_overrides_wrong_schema_guess():
    """
    核心场景：LLM(schema)猜错了(猜成'备注')，用户在前端手动
    纠正为'客商名称'——这个纠正必须生效，不能被schema的错误
    猜测覆盖。这是本次修复要解决的主要问题。
    """
    state = FakeState(mapping={"customer": "客商名称"})
    result = find_customer_field(state, SCHEMA_WRONG, COLUMNS)
    assert result == "客商名称"


def test_user_mapping_not_in_current_sheet_falls_back():
    """用户映射的字段不在当前Sheet里时，应fallback到schema猜测，
    而不是直接返回None"""
    state = FakeState(mapping={"customer": "不存在的字段"})
    assert find_customer_field(state, SCHEMA_CORRECT, COLUMNS) == "客商名称"


def test_keyword_fallback_when_nothing_else_available():
    state = FakeState(mapping={})
    assert find_customer_field(state, SCHEMA_EMPTY, COLUMNS) == "客商名称"


def test_resolve_field_generic_key():
    """resolve_field应支持customer之外的任意概念"""
    state = FakeState(mapping={"amount": "金额"})
    schema = {"entities": {}}
    result = resolve_field(state, schema, COLUMNS, "amount")
    assert result == "金额"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))