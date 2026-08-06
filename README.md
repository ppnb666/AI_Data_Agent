# AI_Data_Agent

基于 **LLM Planner + Tool Registry + Agent State** 架构的智能数据分析 Agent。

本项目旨在构建一个能够理解用户自然语言需求、自主规划分析任务、调用数据分析工具并生成业务洞察报告的 AI 数据分析助手。

相比传统的数据分析脚本，本项目采用 Agent 架构，将数据清洗、数据分析、异常检测、可视化、报告生成等能力封装为独立工具，由 Agent 根据任务需求自动调度执行。

---

## 📌 项目背景

在实际业务场景中，Excel 数据分析通常需要人工完成：

- 数据整理与字段确认
- 数据清洗与质量检查
- 指标统计与异常发现
- 图表制作与报告编写

**AI_Data_Agent** 尝试将这一完整流程自动化。

用户只需要输入自然语言需求，例如：

```
帮我生成销售分析报告
```

Agent 即可自动完成：

```
用户需求 → LLM理解需求 → Planner生成任务计划 → 
Agent调用分析工具 → 更新执行状态 → 生成图表与报告 → 
LLM生成业务洞察
```

---

## 🏗️ 核心架构

```
            用户需求
                |
                ↓
          DeepSeek LLM
                |
                ↓
          Task Planner
                |
          生成执行计划
                |
                ↓
          Agent State
                |
    保存Agent执行上下文
                |
                ↓
         Tool Registry
                |
    ----------------------
    |        |           |
 DataTool ChartTool ReportTool
    |        |           |
    ----------------------
                |
                ↓
        Execution Trace
                |
                ↓
          分析结果输出
                |
                ↓
         LLM业务洞察
```

---

## ✨ 项目特点

### 1. LLM Planner 任务规划

项目接入 DeepSeek 大语言模型，实现自然语言任务理解。

**用户输入：**
```
帮我生成销售报告
```

**Planner 自动生成：**
```json
[
    {"tool": "clean_data", "reason": "数据分析前需要清洗数据"},
    {"tool": "top_product", "reason": "分析销售冠军"},
    {"tool": "generate_report", "reason": "生成销售报告"}
]
```

Agent 根据 Planner 结果自动执行对应工具。

---

### 2. Tool Registry 工具管理

项目采用工具注册中心设计，支持动态注册和调用工具。

**结构：**
```
tools/
├── registry.py          # 工具注册中心
├── data_tools.py        # 数据清洗、分析、异常检测
├── chart_tools.py       # 图表生成
└── report_tools.py      # 报告生成
```

**目前包含：**

| 工具 | 功能 |
|------|------|
| `clean_data` | 数据清洗 |
| `top_product` | 销售冠军分析 |
| `detect_outliers` | 异常检测 |
| `create_chart` | 图表生成 |
| `generate_report` | TXT报告生成 |
| `generate_markdown_report` | Markdown报告生成 |

---

### 3. Agent State 状态管理

为了避免工具之间通过参数传递大量上下文，项目设计 Agent State 统一管理执行状态。

**保存内容包括：**
- 用户请求
- Excel文件路径
- Planner任务计划
- DataFrame数据
- 自动识别字段
- 中间分析结果
- 图表路径
- 报告路径
- 错误信息

```python
# 示例
state.top_product      # "A产品"
state.top_sales        # 4000
state.analysis_result  # {...}
```

实现 Agent 执行过程中的上下文共享。

---

### 4. Excel 字段智能识别

系统无需固定 Excel 表头，通过 `utils/data_parser.py` 自动识别关键字段。

| 类型 | 示例 |
|------|------|
| 销售字段 | 销售额、金额、sales、revenue |
| 产品字段 | 产品、商品、product |
| 日期字段 | 日期、时间、date |

**示例数据：**
```
日期       产品      销售额
2025-01   A产品     4000
2025-02   B产品     3000
```

系统可自动识别字段并执行分析。

---

### 5. 数据清洗工具

通过 `clean_data_tool` 实现：
- 删除缺失数据
- 删除重复数据
- 数据质量检查
- 清洗数量统计

---

### 6. 销售分析工具

通过 `top_product_tool` 实现：
- 产品销售额统计
- 销售冠军分析

**输出：**
```
最高销售产品：A产品
销售额：4000
```

---

### 7. 异常检测工具

通过 `outlier_detection_tool` 实现：
- 异常销售额检测（超过均值2倍）
- 数据质量分析
- 异常记录定位

---

### 8. 数据可视化

自动生成：
- 产品销售排行图 `reports/product_sales.png`
- 销售趋势图 `reports/sales_trend.png`

---

### 9. 自动报告生成

支持两种格式：
- TXT报告 `reports/report.txt`
- Markdown报告 `reports/analysis_report.md`

报告包含：数据概览、清洗结果、产品销售分析、异常检测、字段信息、可视化图表。

---

### 10. LLM 业务洞察

通过 `llm/client.py` 调用大模型生成：
- 数据质量分析
- 销售情况总结
- 业务优化建议

**示例：**
```
A产品当前销售额最高，
建议增加库存并持续关注销售趋势。
```

---

### 11. Agent Execution Trace

为提高 Agent 可观察性，项目增加执行轨迹记录。

**保存位置：**
```
logs/
├── app_xxxx.log        # 运行日志
└── agent_trace.json    # 执行轨迹
```

**记录内容：**
- 用户任务
- 工具调用顺序
- 执行状态
- 执行时间
- 错误信息

**示例：**
```json
[
    {"tool": "clean_data", "status": "success", "duration_ms": 111},
    {"tool": "top_product", "status": "success", "duration_ms": 111},
    {"tool": "generate_report", "status": "success", "duration_ms": 110}
]
```

---

## 📁 项目结构

```
AI_Data_Agent
│
├── data
│   └── sales.xlsx                 # Excel测试数据
│
├── reports
│   ├── report.txt                 # 文本报告
│   ├── analysis_report.md         # Markdown报告
│   ├── product_sales.png          # 销售排行图
│   └── sales_trend.png            # 销售趋势图
│
├── logs
│   ├── app_xxxx.log               # 运行日志
│   └── agent_trace.json           # 执行轨迹
│
├── llm
│   ├── __init__.py
│   └── client.py                  # 大模型客户端
│
├── tools
│   ├── __init__.py                # 工具注册入口
│   ├── registry.py                # 工具注册中心
│   ├── data_tools.py              # 数据分析工具
│   ├── chart_tools.py             # 图表生成工具
│   └── report_tools.py            # 报告生成工具
│
├── utils
│   ├── __init__.py
│   ├── analysis.py                # 数据分析底层实现
│   ├── data_parser.py             # 字段自动识别
│   ├── logger.py                  # 日志系统
│   └── visualization.py           # 可视化底层实现
│
├── trace
│   ├── __init__.py
│   └── tracer.py                  # 执行轨迹记录器
│
├── .env                           # 环境变量（API Key）
├── .gitignore
├── agent.py                       # AI Agent核心
├── planner.py                     # 任务规划器
├── state.py                       # Agent状态管理
├── config.py                      # 配置文件
├── main.py                        # 程序入口
├── README.md                      # 项目说明
└── requirements.txt               # 项目依赖
```

---

## ⚙️ 环境配置

### 创建虚拟环境

```bash
python -m venv .venv
```

### 激活虚拟环境

**Windows：**
```bash
.venv\Scripts\activate
```

**Mac/Linux：**
```bash
source .venv/bin/activate
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 大模型配置

创建 `.env` 文件：

```env
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

---

## 🚀 使用方式

### 准备 Excel 数据

将需要分析的 Excel 文件放入 `data/` 目录：

```
data/sales.xlsx
```

### 运行程序

```bash
python main.py
```

### 输入需求

程序会提示你输入分析需求，例如：

```
请输入你的分析需求：帮我生成销售报告
```

### Agent 自动执行

1. LLM 理解需求
2. Planner 生成任务计划
3. 工具按序执行（清洗 → 分析 → 检测 → 图表 → 报告）
4. LLM 生成业务洞察
5. 保存执行轨迹

### 查看结果

- 分析结果：`reports/`
- 执行轨迹：`logs/agent_trace.json`
- 运行日志：`logs/app_xxxx.log`

---

## 🛠️ 技术栈

| 分类 | 技术 |
|------|------|
| 编程语言 | Python |
| 数据处理 | pandas, openpyxl |
| 可视化 | matplotlib |
| AI Agent | DeepSeek API, OpenAI SDK |
| 架构模式 | LLM Planner, Tool Registry, Agent State |
| 工程化 | Git, logging, python-dotenv |

---

## 📊 当前版本

**Version 2.3**

已完成功能：

- [x] Excel 数据读取
- [x] 字段智能识别
- [x] 数据清洗
- [x] 销售分析
- [x] 异常检测
- [x] 数据可视化
- [x] 自动报告生成（TXT + Markdown）
- [x] DeepSeek LLM Planner
- [x] Tool Registry 工具管理
- [x] Agent State 状态管理
- [x] Logging 日志系统
- [x] Execution Trace 执行轨迹

---

## 🗺️ 后续规划

### Version 2.4

- [ ] Agent Memory 短期记忆
- [ ] 多轮任务对话
- [ ] 历史分析结果复用

### Version 3.0

- [ ] Multi-Agent 协作
- [ ] 数据库数据源接入
- [ ] 自动生成 SQL
- [ ] Web Dashboard

---

## 🎯 项目目标

最终构建一个能够理解业务问题、自主规划任务、调用数据分析工具并生成智能分析报告的 **AI Data Agent**。

---

## 📝 简历项目描述

**AI数据分析Agent（LLM + Planner-Executor + Tool Registry）**

基于DeepSeek API构建智能数据分析Agent，引入Planner-Executor架构和Agent State管理机制，实现：
- **任务规划**：LLM自动理解用户需求，生成最优工具调用链
- **工具注册**：统一管理数据清洗、销售分析、异常检测、可视化、报告生成等6个核心工具
- **执行轨迹**：全流程追踪记录，包含每一步的输入、输出、耗时和状态，支持审计与调试
- **智能洞察**：自动生成数据质量评估、销售分析和业务建议

技术栈：Python、Pandas、Matplotlib、DeepSeek API、OpenAI SDK、JSON Trace

---

## 📄 License

MIT License