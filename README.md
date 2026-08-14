
# 🤖 AI_Data_Agent

> 基于大语言模型（LLM）的企业 Excel 数据智能分析 Agent

## 📌 项目介绍

AI_Data_Agent 是一个面向企业业务数据分析场景的智能 Agent 系统。

针对企业 Excel 数据存在的：

- 文件结构复杂
- 多 Sheet 数据分散
- 字段名称不统一
- 非技术人员难以查询分析

等问题，设计了一套基于 **LLM + Schema理解 + 工具执行** 的自然语言数据分析系统。

用户无需了解 Excel 数据结构，只需要输入业务需求，系统即可自动理解用户意图，分析 Excel 数据结构，生成查询任务，并调用对应工具完成数据查询和分析。

例如：

```

查询保利长大工程有限公司公路建设期产品运维(JSYW)有哪些合同

```

系统自动完成：

```

用户需求
↓
DeepSeek LLM理解需求
↓
Planner生成结构化任务
↓
Schema Agent分析Excel结构
↓
Executor调度查询工具
↓
Pandas执行数据处理
↓
返回结构化结果

```

---

# 🏗️ 系统架构


```

```
                用户(User)

                   |
                   |

          FastAPI 接口层

                   |
                   |

          AI Agent核心层

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

              Executor

    根据任务调用工具


                   |

          Tools工具执行层




                   |

             数据层

          Excel + Pandas
```

```

---

# ✨ 核心功能


## 1. LLM任务规划（Planner）

通过 DeepSeek API 将用户自然语言需求转换为结构化任务。

例如：

用户输入：

```

查询保利长大工程有限公司的公路建设期产品运维(JSYW)合同

````


Planner生成：

```json
{
    "tool": "query_value",
    "customer": "保利长大工程有限公司",
    "filters": {
        "业务条件": "公路建设期产品运维(JSYW)"
    },
    "output": "rows"
}
````

LLM只负责：

* 理解用户需求
* 生成任务计划

数据处理由 Python 工具完成，降低大模型直接处理数据产生的不确定性。

---

# 2. Schema Agent 自动理解Excel结构

企业 Excel 通常没有固定数据库 Schema。

系统通过 Schema Agent 自动分析：

* Sheet数量
* 表头位置
* 字段类型
* 字段语义
* Sheet之间关联关系

例如：

Excel中可能存在：

```
Sheet1:

客商名称
业务种类
期末余额


Sheet2:

客商名称
业务类型（新）
合同名称
万元

```

Schema Agent识别：

```
客户字段:

客商名称


业务字段:

业务种类
业务类型
业务类型（新）


金额字段:

期末余额
万元
```

为后续查询提供字段映射。

---

# 3. 动态字段匹配

系统不依赖固定字段名称。

例如用户说：

```
客户
```

系统可以匹配：

```
客商名称
客户名称
集团内/外客商
```

用户说：

```
业务类型
```

系统可以匹配：

```
业务种类
业务类型
业务类型（新）名称
```

提高系统对不同企业 Excel 数据结构的适应能力。

---

# 4. 多Sheet数据关联查询

支持：

* 多Sheet扫描
* 客户字段关联
* 条件过滤
* 查询结果合并

例如：

用户查询：

```
某客户某业务合同
```

系统流程：

```
Sheet2

客户
+
业务类型过滤


       ↓


提取客户Key


       ↓


关联Sheet1


       ↓


获取金额信息

```

---

# 5. LLM + Python工具执行模式

系统采用：

```
LLM负责决策

Python负责执行
```

而不是：

```
LLM直接操作Excel
```

优势：

* 查询逻辑可控
* 结果稳定
* 易调试
* 降低幻觉风险

---

# 🛠️ 技术栈

| 模块      | 技术               |
| ------- | ---------------- |
| 后端接口    | FastAPI          |
| 编程语言    | Python           |
| 数据处理    | Pandas、Openpyxl  |
| 大语言模型   | DeepSeek API     |
| Agent架构 | Planner-Executor |
| 数据理解    | Schema Agent     |
| 可视化     | Matplotlib       |
| 工程管理    | Git、Logging      |

---

# 📂 项目结构

```
AI_Data_Agent/

│
├── main.py
│   └── 命令行启动入口
│
├── api.py
│   └── FastAPI接口服务
│
├── agent.py
│   └── Agent核心流程调度
│
├── planner.py
│   └── LLM任务规划
│
├── state.py
│   └── Agent状态管理
│
├── config.py
│   └── 配置管理
│


├── llm/

│   └── client.py
│       └── DeepSeek API封装


├── schema/

│   └── schema_agent.py
│       └── Excel结构分析


├── executor/

│   └── executor.py
│       └── 工具执行调度


├── tools/

│   ├── query_tools.py
│   │   └── 数据查询工具
│   │
│   ├── data_tools.py
│   │   └── 数据清洗分析
│   │
│   ├── report_tools.py
│   │   └── 报告生成
│   │
│   ├── chart_tools.py
│   │   └── 数据可视化
│   │
│   └── registry.py
│       └── 工具注册管理


├── utils/

│   ├── excel_loader.py
│   │   └── Excel读取
│   │
│   ├── data_parser.py
│   │   └── 字段解析
│   │
│   ├── logger.py
│   │   └── 日志系统
│   │
│   └── visualization.py
│       └── 图表生成


├── data/

│   └── 合同.xlsx


├── reports/

├── logs/


├── requirements.txt

├── README.md

└── .gitignore

```

---

# 🚀 使用方式

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置DeepSeek API

创建：

```
.env
```

配置：

```env
OPENAI_API_KEY=你的API_KEY

OPENAI_BASE_URL=https://api.deepseek.com/v1
```

---

## CLI运行

```bash
python main.py
```

输入：

```
查询保利长大工程有限公司公路建设期产品运维(JSYW)合同
```

系统自动完成分析。

---

## FastAPI服务

启动：

```bash
uvicorn api:app --reload
```

访问：

```
http://127.0.0.1:8000/docs
```

通过接口调用Agent能力。

---

# 📊 示例

用户输入：

```
查询保利长大工程有限公司公路建设期产品运维(JSYW)有哪些合同
```

系统生成任务：

```json
{
 "tool":"query_value",
 "customer":"保利长大工程有限公司",
 "filters":{
    "业务条件":
    "公路建设期产品运维(JSYW)"
 }
}
```

最终返回：

```
客户：
保利长大工程有限公司


匹配合同：

xxx合同

xxx合同

xxx合同

```

---

# 🎯 项目亮点

## 1. 从传统数据分析脚本升级为Agent系统

传统方式：

```
人工打开Excel
↓
寻找字段
↓
筛选数据
↓
统计分析
```

本项目：

```
自然语言输入
↓
Agent理解
↓
自动查询
↓
返回结果
```

---

## 2. Schema驱动的数据理解

通过Schema Agent解决企业Excel字段不统一问题，提高系统泛化能力。

---

## 3. LLM与代码结合

采用：

```
LLM负责规划

Python负责执行

```

兼顾智能性和稳定性。

---

# 🔮 后续优化

* 接入MySQL/PostgreSQL数据库
* 增加向量数据库实现语义检索
* 支持PDF、CSV等文件
* 增加Web前端展示
* 引入多Agent协作机制

---

# 👨‍💻 Author

蒲家森

AI Application Development Project

2026
