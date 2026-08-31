"""
scripts/regression.py — 回归门禁脚本（Phase 0 基线）

用例表驱动：file + query + 断言，每个用例独立跑一次完整 Agent 流程。
每阶段改造后运行本脚本，确保合同.xlsx 的 5 个核心流程不被破坏。

用法：
    python scripts/regression.py                    # 跑全部用例（真实 LLM）
    python scripts/regression.py --filter 合同      # 只跑名称含"合同"的用例
    python scripts/regression.py --update-snapshot  # 更新快照文件
    python scripts/regression.py --no-llm           # 不跑真实 LLM 用例（仅跑本地断言用例）

退出码：全部通过返回 0，任一失败返回 1。
"""

import argparse
import json
import os
import sys

# Windows GBK 控制台无法打印 emoji / 中文，统一走 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 保证可从项目根目录 import
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SNAPSHOT_PATH = os.path.join(ROOT, "scripts", "baseline_snapshot.json")

# ==========================================================
# 工具函数
# ==========================================================

def _result_type(result):
    return result.get("query_result", {}).get("type")


def _rows(result):
    return result.get("query_result", {}).get("data", {}).get("rows", [])


# ==========================================================
# 用例表
#
# execute(agent) -> result           （默认 agent.run）
# assert_result(result) -> (bool, msg)
# ==========================================================

CASES = []


def _make_contract_query_case(name, query, check):
    CASES.append({
        "name": name,
        "file": os.path.join(ROOT, "data", "合同.xlsx"),
        "query": query,
        "check": check,
    })


def _check_precise_query(result):
    """精确查询 → query_value，rows 非空，且包含期末余额汇总"""
    if _result_type(result) != "query_value":
        return False, f"type={_result_type(result)}，期望 query_value"
    rows = _rows(result)
    if not rows:
        return False, "rows 为空"
    summary = result.get("query_result", {}).get("summary", {})
    if not summary:
        return False, "summary 为空（期望有金额汇总）"
    return True, f"type=query_value, rows={len(rows)}, summary={list(summary.keys())}"


def _check_fuzzy_rank(result):
    """模糊分析 → rank_rows"""
    if _result_type(result) != "rank_rows":
        return False, f"type={_result_type(result)}，期望 rank_rows"
    rows = _rows(result)
    if not rows:
        return False, "rows 为空"
    return True, f"type=rank_rows, rows={len(rows)}"


def _check_compare(result):
    """字段比较 → compare_rows"""
    if _result_type(result) != "compare_rows":
        return False, f"type={_result_type(result)}，期望 compare_rows"
    qr = result.get("query_result", {})
    compare = qr.get("compare", {})
    if not compare.get("left") or not compare.get("right"):
        return False, f"compare 参数不完整: {compare}"
    return True, f"type=compare_rows, {compare.get('left')} {compare.get('operator')} {compare.get('right')}"


def _check_rank_grouping(result):
    """排名 → 分组字段仍为 客商名称"""
    if _result_type(result) != "rank_rows":
        return False, f"type={_result_type(result)}，期望 rank_rows"
    qr = result.get("query_result", {})
    rows = qr.get("data", {}).get("rows", [])
    if not rows:
        return False, "rows 为空"
    first = rows[0]
    if "客商名称" not in first:
        return False, f"排名结果缺少分组字段 客商名称，实际字段: {list(first.keys())}"
    return True, f"分组字段=客商名称, rows={len(rows)}"


_make_contract_query_case(
    "合同-精确查询",
    "查保利长大工程有限公司的期末余额",
    _check_precise_query,
)

_make_contract_query_case(
    "合同-模糊分析",
    "哪个公司发展前景好？",
    _check_fuzzy_rank,
)

_make_contract_query_case(
    "合同-字段比较",
    "查保利长大工程有限公司的公路建设期产品运维(JSYW)的本期贷方和贷方累计是否相等",
    _check_compare,
)

_make_contract_query_case(
    "合同-排名",
    "按期末余额从高到低给客商排名",
    _check_rank_grouping,
)


def _check_quality_clean(state):
    """
    质量检测 → 【客商：】清洗仍生效（样本驱动）

    Phase 0 基线：断言流程跑通（质量报告 + 清洗建议生成）。
    已知基线缺陷：pandas 2.x StringDtype 下 is_object_dtype 为 False，
    文本清洗分支（含 clean_prefix）从未执行。
    Phase 6（样本驱动清洗）完成后，此断言应提升为 clean_prefix 生效。
    """
    report = getattr(state, "data_quality_report", {}) or {}
    clean_suggestions = getattr(state, "clean_suggestions", {}) or {}
    if not report:
        return False, "quality_report 为空"
    if not clean_suggestions:
        return False, "clean_suggestions 为空"
    actions = clean_suggestions.get("actions", {})
    msg = f"report_score={report.get('overall_score')}, 清洗动作={len(actions)}个"
    if report.get("overall_score", 100) < 80:
        if not actions:
            return False, f"质量分<80 但未生成任何清洗动作, {msg}"
    # Phase 6 验收点：样本确认含 【】 包裹模式时应生成 clean_prefix
    for col, acts in actions.items():
        for act in acts:
            if act.get("type") == "clean_prefix":
                return True, f"清洗建议生效: {col} → {act.get('pattern')}"
    return True, msg + "（Phase 0 基线：clean_prefix 待 Phase 6 启用）"


def _execute_quality_case(agent):
    """质量检测用例不经过 planner（仅 prepare_context 阶段），省一次 LLM 调用"""
    from state import AgentState

    state = AgentState()
    state.file_path = os.path.join(ROOT, "data", "合同.xlsx")
    state.user_query = "检查数据质量"
    agent.prepare_context(state)
    return state


CASES.append({
    "name": "合同-质量检测",
    "file": os.path.join(ROOT, "data", "合同.xlsx"),
    "query": "检查数据质量",
    "execute": _execute_quality_case,
    "check": lambda state: _check_quality_clean(state),
})


# ==========================================================
# 快照
# ==========================================================

def build_snapshot(agent, results):
    snapshot = {
        "generated_by": "scripts/regression.py",
        "cases": {},
    }
    for case, result in zip(CASES, results):
        entry = {"query": case["query"]}
        if isinstance(result, dict):
            qr = result.get("query_result", {})
            entry["result_type"] = qr.get("type")
            entry["total_count"] = qr.get("total_count")
            entry["rows_count"] = len(qr.get("data", {}).get("rows", []))
            entry["summary"] = qr.get("summary")
            if qr.get("type") == "compare_rows":
                entry["compare"] = qr.get("compare")
            entry["ai_insight_len"] = len(result.get("ai_insight", ""))
        else:
            entry["note"] = "自定义用例（无 query_result）"
            entry["clean_suggestions"] = getattr(result, "clean_suggestions", None)
        snapshot["cases"][case["name"]] = entry
    return snapshot


# ==========================================================
# 主流程
# ==========================================================

def main():
    parser = argparse.ArgumentParser(description="AI Data Agent 回归门禁")
    parser.add_argument("--filter", default="", help="只跑名称包含该子串的用例")
    parser.add_argument("--update-snapshot", action="store_true", help="更新基线快照")
    parser.add_argument("--no-llm", action="store_true", help="跳过依赖真实 LLM 的用例")
    args = parser.parse_args()

    cases = [c for c in CASES if args.filter in c["name"]]
    if not cases:
        print(f"没有匹配的用例: {args.filter}")
        return 1

    from agent import DataAgent

    agent = DataAgent()

    results = []
    failures = 0

    for i, case in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] {case['name']}")
        print(f"  file : {os.path.basename(case['file'])}")
        print(f"  query: {case['query']}")

        if args.no_llm and case["name"] != "合同-质量检测":
            print("  SKIP (--no-llm)")
            continue

        try:
            if "execute" in case:
                result = case["execute"](agent)
            else:
                result = agent.run(
                    file_path=case["file"],
                    user_query=case["query"],
                    with_ai=True,
                )
            ok, msg = case["check"](result)
        except Exception as e:
            ok, msg = False, f"异常: {type(e).__name__}: {e}"
            import traceback
            traceback.print_exc()

        results.append(result if ok else None)

        if ok:
            print(f"  PASS: {msg}")
        else:
            failures += 1
            print(f"  FAIL: {msg}")

    print("\n" + "=" * 50)
    if failures:
        print(f"❌ 回归失败: {failures} 个用例未通过")
        return 1

    print("✅ 全部用例通过")

    if args.update_snapshot:
        snapshot = build_snapshot(agent, results)
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"快照已更新: {SNAPSHOT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
