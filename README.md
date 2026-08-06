# AI_Data_Agent

基于 Python 的智能数据分析 Agent。

项目目标是构建一个能够自动理解 Excel 数据、调用数据分析工具、生成业务洞察报告的 AI 数据分析助手。

相比传统的数据分析脚本，本项目采用 Agent + Tool Registry 架构，将数据处理、分析、可视化、报告生成等能力封装为独立工具，由 Agent 统一调度执行。

---

# 项目介绍

在实际业务场景中，Excel 数据分析通常需要人工完成：

- 数据整理
- 字段确认
- 数据清洗
- 指标统计
- 异常发现
- 图表制作
- 分析报告编写


AI_Data_Agent 尝试将这一流程自动化。


用户只需要提供 Excel 数据文件，系统即可自动完成：

```
Excel文件

↓

字段智能识别

↓

数据清洗

↓

数据分析

↓

异常检测

↓

数据可视化

↓

自动生成分析报告

↓

AI业务洞察
```


---

# 项目特点

## 1. Agent 架构设计

项目采用：

```
DataAgent

    |
    |
    ↓

Tool Registry

    |
    |
    ↓

Tools

    |
    |
    ↓

Utils
```


其中：

### Agent层

负责：

- 控制分析流程
- 调用工具
- 整合分析结果
- 调用大模型生成业务洞察


### Tools层

负责：

- 数据清洗
- 销售分析
- 异常检测
- 图表生成
- 报告生成


### Utils层

负责：

- 基础数据处理
- Excel字段解析
- 可视化底层实现


---

# 当前实现功能


## 1. Excel 数据读取

支持：

- `.xlsx` 文件读取
- pandas 数据处理


示例：

```
data/

└── sales.xlsx
```


---

# 2. Excel字段智能识别

系统无需固定 Excel 表头。


通过：

```
utils/data_parser.py
```

自动识别关键字段。


支持：

| 类型 | 示例 |
|-|-|
| 销售字段 | 销售额、金额、收入、sales、revenue |
| 产品字段 | 产品、商品、product |
| 日期字段 | 日期、时间、date |


例如：

数据1：

```
日期    产品    销售额

2025-01 A产品  3000
2025-01 B产品  2000
```


数据2：

```
transaction_date

item

revenue
```


均可以自动识别。


---

# 3. 数据清洗工具


通过 Tool Registry 调用：

```
clean_data_tool
```


实现：

- 删除缺失数据
- 删除重复数据
- 统计清洗数量


---

# 4. 销售分析工具


支持：

```
top_product_tool
```


功能：

- 产品销售额统计
- 销售冠军分析


输出：

```
最高销售产品：

A产品

销售额：

5000
```


---

# 5. 异常检测工具


支持：

```
outlier_detection_tool
```


用于发现：

- 异常订单
- 异常销售额
- 数据质量问题


---

# 6. 数据可视化


自动生成：

## 产品销售排行图

输出：

```
reports/product_sales.png
```


## 销售趋势图

输出：

```
reports/sales_trend.png
```


---

# 7. 自动生成分析报告


系统自动生成：


## TXT报告

```
reports/report.txt
```


## Markdown报告

```
reports/analysis_report.md
```


报告包含：

- 数据概览
- 清洗结果
- 销售分析
- 异常检测
- 字段信息
- 分析结果


---

# 8. 大模型业务洞察


项目支持接入大语言模型。


通过：

```
llm/client.py
```


调用模型生成：

- 数据质量评价
- 销售情况分析
- 业务优化建议


示例：

```
当前数据完整性较高。

A产品销售额最高，
建议增加库存与推广。

建议扩大数据范围，
进一步分析销售趋势。
```


---

# 项目结构


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
│   └── app.log                    # 运行日志
│
├── tools
│   ├── __init__.py
│   │
│   ├── registry.py                # Agent工具注册中心
│   │
│   ├── data_tools.py              # 数据分析工具
│   │
│   ├── chart_tools.py             # 可视化工具
│   │
│   └── report_tools.py            # 报告生成工具
│
├── utils
│   ├── analysis.py                # 基础分析函数
│   ├── data_parser.py              # 字段自动识别
│   ├── visualization.py            # matplotlib绘图
│   └── logger.py                  # 日志系统
│
├── llm
│   ├── __init__.py
│   └── client.py                  # LLM接口封装
│
├── agent.py                       # Agent核心逻辑
│
├── main.py                        # 程序入口
│
├── config.py                      # 项目配置
│
├── requirements.txt
│
├── .env                           # API配置
│
└── README.md
```


---

# 环境配置


## 创建虚拟环境


```bash
python -m venv .venv
```


激活：


Windows：

```bash
.venv\Scripts\activate
```


---

## 安装依赖


```bash
pip install -r requirements.txt
```


---

# 配置大模型


创建：

```
.env
```


填写：

```env
API_KEY=your_api_key
BASE_URL=your_base_url
MODEL_NAME=your_model
```


---

# 使用方式


将 Excel 文件放入：

```
data/
```


修改：

```
config.py
```


例如：

```python
DATA_PATH="data/sales.xlsx"
```


运行：


```bash
python main.py
```


---

# Agent执行流程


```
用户输入Excel

        |

        ↓

DataAgent

        |

        ↓

字段智能识别

        |

        ↓

Tool Registry

        |

        ↓

调用分析工具

        |

        ↓

生成图表

        |

        ↓

生成报告

        |

        ↓

LLM生成业务洞察
```


---

# 技术栈


## 编程语言

- Python


## 数据处理

- pandas
- openpyxl


## 数据可视化

- matplotlib


## 工程化

- Git
- logging
- dotenv


## AI Agent

- Tool Registry
- LLM API


---

# 当前版本


## Version 1.0

已完成：

- Excel数据读取
- 自动字段识别
- 数据清洗
- 销售分析
- 异常检测
- 数据可视化
- Markdown报告
- LLM业务洞察


## Version 1.5（开发中）

计划增加：

- 用户自然语言需求输入
- Agent自动选择工具
- Tool Calling机制
- 多任务分析能力


## Version 2.0（未来）

目标：

实现真正的 AI Data Agent


```
用户：

"帮我分析最近销售下降原因"


↓

AI Agent理解需求


↓

自动选择分析工具


↓

执行数据分析


↓

生成业务报告
```


---

# 项目目标


最终构建：

> 一个能够理解业务问题，并自主调用数据分析工具完成任务的 AI 数据分析 Agent。

