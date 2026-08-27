# 🤖 AI_Data_Agent

> 基于大语言模型（LLM）的企业 Excel 数据智能分析 Agent

---

## 📌 项目介绍

AI_Data_Agent 是一个面向企业业务数据分析场景的智能 Agent 系统。

**解决的核心问题：**

- 文件结构复杂（多 Sheet、多层表头）
- 字段名称不统一（不同企业不同叫法）
- 数据质量参差不齐（空值、无效格式、脏数据）
- 非技术人员难以查询分析

**设计理念：**

> **LLM 负责理解与规划，Python 负责执行与计算**

用户无需了解 Excel 数据结构，只需输入自然语言需求，系统自动完成：意图理解 → 结构分析 → 质量检测 → 任务规划 → 工具执行 → 结果返回。

---

## ✨ 核心能力

| 能力 | 说明 |
| :--- | :--- |
| **精确查询** | 查询指定客户、指定业务条件的合同/数据 |
| **字段比较** | 比较两个字段是否相等、大小关系 |
| **模糊分析** | 自动理解"发展前景"、"经营状况"等模糊商业问题 |
| **自动排名** | 按客户分组汇总指标并排序，自动识别 Top N |
| **数据质量检测** | 自动检测空值、异常格式、格式不一致等质量问题 |
| **自动清洗** | 根据质量报告自动清洗脏数据 |
| **通用格式适配** | 任意 Excel 结构（字段名不同、Sheet不同）自动适配 |

---

## 🚀 使用示例

```bash
# 精确查询
查询保利长大工程有限公司公路建设期产品运维(JSYW)有哪些合同

# 模糊分析
分析哪个公司发展前景好

# 字段比较
查询保利长大工程有限公司本期贷方和贷方累计是否相等
```

---

## 🏗️ 系统架构

```text
用户(User)
    |
FastAPI 接口层
    |
AI Agent 核心层
    |
    ├── Planner          → 用户需求 → 查询任务(JSON)
    ├── Schema Agent     → Excel结构理解 / 字段映射
    ├── Data Profiler    → 数据质量检测 / 自动清洗
    ├── Executor         → 根据任务调用工具
    |
Tools 工具执行层
    ├── query_value      → 精确查询
    ├── compare_rows     → 字段比较
    ├── rank_rows        → 分组排名
    ├── aggregate_value  → 汇总统计
    └── detect_anomaly   → 异常检测
    |
数据层 (Excel + Pandas)
```

---

## 📂 项目结构

```text
AI_Data_Agent/
│
├── main.py                  # 命令行启动入口
├── api.py                   # FastAPI 接口服务
├── agent.py                 # Agent 核心流程调度
├── planner.py               # LLM 任务规划
├── state.py                 # Agent 状态管理
├── config.py                # 配置文件
│
├── llm/
│   └── client.py            # DeepSeek API 封装
│
├── schema/
│   └── schema_agent.py      # Excel 结构分析
│
├── profiler/
│   └── data_profiler_agent.py  # 数据质量检测 + 清洗
│
├── executor/
│   └── executor.py          # 工具执行调度
│
├── tools/
│   ├── query_tools.py       # 数据查询工具
│   ├── compare_tools.py     # 字段比较工具
│   ├── rank_tools.py        # 排名工具
│   ├── data_tools.py        # 数据清洗分析
│   ├── report_tools.py      # 报告生成
│   ├── chart_tools.py       # 数据可视化
│   └── registry.py          # 工具注册管理
│
├── utils/
│   ├── excel_loader.py      # Excel 读取
│   ├── data_parser.py       # 字段解析
│   ├── data_profiler.py     # 数据画像
│   ├── logger.py            # 日志系统
│   ├── trace.py             # 执行轨迹追踪
│   └── visualization.py     # 图表生成
│
├── data/                    # 数据文件目录
│   └── 合同.xlsx
│
├── reports/                 # 报告输出目录
├── logs/                    # 日志目录
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🛠️ 技术栈

| 模块 | 技术 |
| :--- | :--- |
| 后端接口 | FastAPI |
| 编程语言 | Python 3.10+ |
| 数据处理 | Pandas、Openpyxl |
| 大语言模型 | DeepSeek API |
| Agent 架构 | Planner-Executor |
| 数据理解 | Schema Agent |
| 数据质量 | Data Profiler（自动检测+清洗） |
| 可视化 | Matplotlib |
| 工程管理 | Git、Logging |

---

## 🚀 使用方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 DeepSeek API

创建 `.env` 文件：

```env
OPENAI_API_KEY=你的API_KEY
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

### 3. CLI 运行

```bash
python main.py
```

输入分析需求即可，例如：

```text
查询保利长大工程有限公司公路建设期产品运维(JSYW)合同
```

或：

```text
分析哪个公司发展前景好
```

### 4. FastAPI 服务

```bash
uvicorn api:app --reload
```

访问 API 文档：`http://127.0.0.1:8000/docs`

### 5. 文件上传 + 字段映射

通过 `/preview` 接口上传任意 Excel，系统自动猜测字段含义，用户确认后保存映射，后续查询自动适配该文件结构。

---

## 📊 运行示例

### 示例 1：精确查询

**输入：**

```text
查询保利长大工程有限公司公路建设期产品运维(JSYW)合同
```

**输出：**

```text
客户：保利长大工程有限公司
匹配合同：xxx合同、xxx合同...
```

### 示例 2：模糊分析（发展前景）

**输入：**

```text
分析哪个公司发展前景好
```

**输出：**

```text
========== 排名结果 ==========
📊 按 期末余额 排名（降序），共 1487 条记录，显示前 10 条

排名 | 客户名称                     | 指标值          |
-----|----------------------------|----------------|
  1  | 广东新粤交通投资有限公司本部    | 112,700,287.93 |
  2  | 广东京珠高速公路广珠北段有限公司 | 97,249,538.96  |
  3  | 广东省交通集团有限公司本部     | 56,679,661.28  |
...

🤖 AI 业务建议：
发展前景最好的客户是【广东新粤交通投资有限公司本部】...
```

### 示例 3：数据质量自动检测

**输入：** 上传任意 Excel，系统自动分析

**输出：**

```json
{
  "overall_score": 72,
  "overall_status": "needs_review",
  "fields": {
    "客商名称": {
      "null_rate": 2.5,
      "issues": [
        {"type": "inconsistent_format", "message": "格式不一致：65% 数据带前缀【】"}
      ]
    }
  }
}
```

```text
🧹 数据质量评分: 72，自动执行清洗...
   清洗后数据: 6820 行
```

---

## 🎯 项目亮点

| 维度 | 说明 |
| :--- | :--- |
| **自然语言交互** | 用户无需了解数据结构，直接用业务语言提问 |
| **Schema 驱动** | 自动理解任意 Excel 结构，不依赖固定模板 |
| **数据质量自检** | 自动检测并清洗脏数据，确保分析准确 |
| **模糊意图理解** | 支持"发展前景"、"经营状况"等模糊商业问题 |
| **多工具协作** | 查询、比较、排名、汇总、异常检测一站式完成 |
| **LLM + 代码结合** | LLM 负责理解与规划，Python 负责稳定执行，降低幻觉风险 |

---

## 🔮 后续优化计划

- [ ] 接入 MySQL/PostgreSQL 数据库
- [ ] 增加向量数据库实现语义检索
- [ ] 支持 PDF、CSV 等更多文件格式
- [ ] 增加 Web 前端展示界面
- [ ] 引入多 Agent 协作机制
- [ ] 支持更多分析工具（趋势预测、异常归因）
- [ ] 增加流式输出，实时展示执行进度

---

## 👨‍💻 Author

蒲家森

AI Application Development Project

2026