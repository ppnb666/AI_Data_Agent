"""
通用性样例验证脚本（Phase 9）

覆盖：
1. data/员工.csv：无任何财务词的行业数据（rank 按部门分组 + 客户查询）
2. data/库存.json：JSON 格式 + 无客户字段降级路径

用法：
    python scripts/verify_samples.py
"""
import contextlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import DataAgent  # noqa: E402


def run_case(path, query):
    if not os.path.exists(path):
        print(f"⚠ 样例文件不存在（被 .gitignore 忽略，不入库）: {path}")
        return
    agent = DataAgent()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = agent.run(path, query, with_ai=False)
    except Exception as e:
        print(f"❌ [{query}] 执行失败: {e}")
        return
    t = result.get("query_result", {})
    print(f"\n▶ 用例: {query} ({path.split(chr(92))[-1]})")
    print(f"  类型: {t.get('type')} | 状态: {t.get('status')} | 记录数: {t.get('total_count')}")
    if t.get("type") == "rank_rows":
        print(f"  排名指标: {t.get('metric')}")
        for row in (t.get("data") or {}).get("rows", [])[:3]:
            print("   ", {k: v for k, v in row.items() if k != "来源Sheet"})
    elif t.get("type") == "query_value":
        print(f"  汇总: {t.get('summary')}")
        rows = (t.get("data") or {}).get("rows", [])
        if rows:
            print("   首行:", {k: v for k, v in rows[0].items() if k != "来源Sheet"})
    elif t.get("type") == "compare_rows":
        print(f"  比较: {t.get('compare')} | 匹配: {t.get('matched_count')}")
    elif t.get("type") == "aggregate_value":
        print(f"  汇总: {t.get('summary')}")
    elif t.get("type") == "detect_anomaly":
        print(f"  异常: {t.get('anomaly_summary')}")


if __name__ == "__main__":
    run_case("data/员工.csv", "哪个部门薪资最高？")
    run_case("data/员工.csv", "查张三的月薪是多少")
    run_case("data/库存.json", "哪些产品库存量最高？")
    run_case("data/库存.json", "电子产品的库存量合计多少")
    print("\n✅ 样例验证完成")
