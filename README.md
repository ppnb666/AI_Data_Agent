# 🤖 AI_Data_Agent

> 基于大语言模型（LLM）的企业 Excel 数据智能分析 Agent

## 📌 项目介绍

AI_Data_Agent 是一个面向企业业务数据分析场景的智能 Agent 系统。

针对企业 Excel 数据存在的：

- 文件结构复杂
- 多 Sheet 数据分散
- 字段名称不统一
- 数据质量参差不齐（空值、无效格式、脏数据）
- 非技术人员难以查询分析

等问题，设计了一套基于 **LLM + Schema理解 + 数据质量检测 + 工具执行** 的自然语言数据分析系统。

用户无需了解 Excel 数据结构，只需要输入业务需求，系统即可自动理解用户意图，分析 Excel 数据结构，自动检测数据质量并清洗，生成查询任务，并调用对应工具完成数据查询和分析。

**核心能力：**

| 能力 | 说明 |
| :--- | :--- |
| **精确查询** | 查询指定客户、指定业务条件的合同/数据 |
| **字段比较** | 比较两个字段是否相等、大小关系 |
| **模糊分析** | 自动理解“发展前景”、“经营状况”等模糊商业问题 |
| **自动排名** | 按客户分组汇总指标并排序，自动识别 Top N |
| **数据质量检测** | 自动检测空值、异常格式、格式不一致等质量问题，自动清洗 |
| **通用格式适配** | 任意 Excel 结构（字段名不同、Sheet不同）自动适配 |

---

### 使用示例

# 精确查询
查询保利长大工程有限公司公路建设期产品运维(JSYW)有哪些合同

# 模糊分析
分析哪个公司发展前景好

# 比较查询
查询保利长大工程有限公司本期贷方和贷方累计是否相等
系统自动完成：

用户需求
    ↓
DeepSeek LLM 理解需求
    ↓
Planner 生成结构化任务
    ↓
Schema Agent 分析 Excel 结构
    ↓
Data Profiler 检测数据质量 → 自动清洗
    ↓
Executor 调度工具执行
    ↓
Pandas 执行数据处理
    ↓
返回结构化结果 + AI 洞察
🏗️ 系统架构
                用户(User)
                   |
                   |
          FastAPI 接口层
                   |
                   |
          AI Agent 核心层
                   |
    ┌────────────────────┐
    │   DeepSeek API     │
    └────────────────────┘
                   |
              Planner
    用户需求 → 查询任务(JSON)
                   |
            Schema Agent
    Excel结构理解 / 字段映射
                   |
         Data Profiler
    数据质量检测 / 自动清洗
                   |
              Executor
    根据任务调用工具
                   |
          Tools 工具执行层
    ┌──────┬──────┬──────┬──────┐
    │查询   │比较   │排名   │图表   │
    └──────┴──────┴──────┴──────┘
                   |
             数据层
          Excel + Pandas
✨ 核心功能
1. LLM 任务规划（Planner）
通过 DeepSeek API 将用户自然语言需求转换为结构化任务。

精确查询示例：

用户输入：

查询保利长大工程有限公司的公路建设期产品运维(JSYW)合同
Planner 生成：

json
{
    "tool": "query_value",
    "customer": "保利长大工程有限公司",
    "filters": {
        "业务条件": "公路建设期产品运维(JSYW)"
    },
    "output": "rows"
}
模糊分析示例：

用户输入：

分析哪个公司发展前景好
Planner 自动识别为排名任务：

json
{
    "tool": "rank_rows",
    "reason": "按期末余额排名，评估客户发展前景",
    "metrics": ["期末余额"],
    "condition": {"order": "desc", "limit": 10},
    "output": "rows"
}
LLM 只负责理解需求和生成计划，数据处理由 Python 工具完成，降低幻觉风险。

2. Schema Agent 自动理解 Excel 结构
企业 Excel 通常没有固定数据库 Schema。

系统通过 Schema Agent 自动分析：

Sheet 数量

表头位置

字段类型

字段语义（客户、金额、业务类型、日期等）

Sheet 之间关联关系

示例：

Excel 中可能存在：

Sheet1: 客商名称 | 业务种类 | 期末余额
Sheet2: 客商名称 | 业务类型（新）| 合同名称 | 万元
Schema Agent 自动识别：

客户字段: 客商名称
业务字段: 业务种类、业务类型、业务类型（新）
金额字段: 期末余额、万元
为后续查询提供字段映射。

3. 动态字段匹配（字段映射）
系统不依赖固定字段名称，支持用户自定义字段映射。

用户概念	可匹配的 Excel 字段
客户	客商名称、客户名称、集团内/外客商
业务类型	业务种类、业务类型、业务类型（新）名称
金额	期末余额、本期贷方、贷方累计、万元
即使不同企业的 Excel 结构完全不同，通过首次上传时的字段映射配置，系统也能自动适配。

4. 数据质量自动检测与清洗（Data Profiler）
这是项目的核心创新之一。系统自动检测数据质量问题：

检测项	说明
空值检测	自动识别空值率过高的字段
格式一致性	检测字段格式是否统一（如部分数据带前缀【】）
异常值检测	数值字段的负值占比、常量字段
唯一值分析	识别 ID 字段、低基数分类字段
自动清洗动作：

空值率 > 30% → 自动删除该行

空值率 10%-30% → 自动用众数填充

格式不一致 → 自动清理前缀/后缀

质量评分 < 80 分时自动触发清洗，确保后续分析基于干净数据。

5. 多工具支持
工具	功能	触发关键词
query_value	精确查询数据	查询、查看、有哪些
compare_rows	字段比较	比较、是否相等、大于
rank_rows	分组排名	排名、最高、Top、前N
aggregate_value	汇总统计	合计、总额、汇总
detect_anomaly	异常检测	异常、风险、波动
6. 多 Sheet 数据关联查询
支持：

多 Sheet 扫描

客户字段关联

条件过滤

查询结果合并

7. LLM + Python 工具执行模式
LLM 负责决策 → Python 负责执行
优势：

查询逻辑可控

结果稳定可预期

易于调试

降低 LLM 幻觉风险

支持复杂数据计算

🛠️ 技术栈
模块	技术
后端接口	FastAPI
编程语言	Python 3.10+
数据处理	Pandas、Openpyxl
大语言模型	DeepSeek API
Agent 架构	Planner-Executor
数据理解	Schema Agent
数据质量	Data Profiler（自动检测+清洗）
可视化	Matplotlib
工程管理	Git、Logging
📂 项目结构

AI_Data_Agent/
│
├── main.py                 # 命令行启动入口
├── api.py                  # FastAPI 接口服务
├── agent.py                # Agent 核心流程调度
├── planner.py              # LLM 任务规划
├── state.py                # Agent 状态管理
├── config.py               # 配置文件
│
├── llm/
│   └── client.py           # DeepSeek API 封装
│
├── schema/
│   └── schema_agent.py     # Excel 结构分析
│
├── profiler/
│   └── data_profiler_agent.py  # 数据质量检测 + 清洗
│
├── executor/
│   └── executor.py         # 工具执行调度
│
├── tools/
│   ├── query_tools.py      # 数据查询工具
│   ├── compare_tools.py    # 字段比较工具
│   ├── rank_tools.py       # 排名工具
│   ├── data_tools.py       # 数据清洗分析
│   ├── report_tools.py     # 报告生成
│   ├── chart_tools.py      # 数据可视化
│   └── registry.py         # 工具注册管理
│
├── utils/
│   ├── excel_loader.py     # Excel 读取
│   ├── data_parser.py      # 字段解析
│   ├── data_profiler.py    # 数据画像
│   ├── logger.py           # 日志系统
│   ├── trace.py            # 执行轨迹追踪
│   └── visualization.py    # 图表生成
│
├── data/                   # 数据文件目录
│   └── 合同.xlsx
│
├── reports/                # 报告输出目录
├── logs/                   # 日志目录
│
├── requirements.txt
├── README.md
└── .gitignore
🚀 使用方式
1. 安装依赖
pip install -r requirements.txt
2. 配置 DeepSeek API
创建 .env 文件：

env
OPENAI_API_KEY=你的API_KEY
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
3. CLI 运行
python main.py
输入分析需求，例如：

查询保利长大工程有限公司公路建设期产品运维(JSYW)合同
或：

分析哪个公司发展前景好
系统自动完成分析并输出结果。

4. FastAPI 服务
启动服务：

uvicorn api:app --reload
访问 API 文档：

http://127.0.0.1:8000/docs
5. 文件上传 + 字段映射
通过 /preview 接口上传任意 Excel，系统自动猜测字段含义，用户确认后保存映射，后续查询自动适配该文件结构。

📊 运行示例
示例 1：精确查询
输入：

查询保利长大工程有限公司公路建设期产品运维(JSYW)合同
输出：

客户：保利长大工程有限公司
匹配合同：xxx合同、xxx合同...
示例 2：模糊分析（发展前景）
输入：

分析哪个公司发展前景好
输出：

========== 排名结果 ==========
📊 按 期末余额 排名（降序），共 1487 条记录，显示前 10 条

排名 | 客户名称                     | 指标值        |
-----|----------------------------|--------------|
 1   | 广东新粤交通投资有限公司本部    | 112,700,287.93 |
 2   | 广东京珠高速公路广珠北段有限公司 | 97,249,538.96 |
 3   | 广东省交通集团有限公司本部     | 56,679,661.28 |
...

🤖 AI 业务建议：
发展前景最好的客户是【广东新粤交通投资有限公司本部】...
示例 3：数据质量自动检测
输入：

（上传任意 Excel，系统自动分析）
输出：

📊 数据质量报告:
{
  "overall_score": 72,
  "overall_status": "needs_review",
  "fields": {
    "客商名称": {
      "null_rate": 2.5,
      "issues": [
        {"type": "inconsistent_format", "message": "格式不一致：65% 数据带前缀【】"}
      ]
    },
    "期末余额": {
      "null_rate": 0,
      "issues": [
        {"type": "high_negative_rate", "message": "负值占比 8%"}
      ]
    }
  }
}

🧹 数据质量评分: 72，自动执行清洗...
   清洗后数据: 6820 行
🎯 项目亮点
1. 从传统数据分析脚本升级为 Agent 系统
传统方式	本项目
人工打开 Excel	自然语言输入
手动寻找字段	Agent 自动理解
手动筛选数据	自动查询执行
手工统计分析	返回结果 + AI 洞察
2. Schema 驱动的数据理解
通过 Schema Agent 解决企业 Excel 字段不统一问题，提高系统泛化能力。

3. 数据质量自动检测与清洗
系统自动识别并处理脏数据，确保分析结果准确可靠，无需人工干预。

4. 模糊意图理解
支持“发展前景”、“经营状况”等模糊商业问题的自动分析，真正智能。

5. LLM 与代码结合
LLM 负责规划 → Python 负责执行
兼顾智能性和稳定性，降低幻觉风险。

6. 通用格式适配
支持任意 Excel 结构，通过字段映射实现“一次配置，终身使用”。

🔮 后续优化计划
□ 接入 MySQL/PostgreSQL 数据库
□ 增加向量数据库实现语义检索
□ 支持 PDF、CSV 等更多文件格式
□ 增加 Web 前端展示界面
□ 引入多 Agent 协作机制
□ 支持更多分析工具（趋势预测、异常归因）
□ 增加流式输出，实时展示执行进度
👨‍💻 Author
蒲家森

AI Application Development Project

2026