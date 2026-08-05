# AI_Data_Agent

基于 Python 的智能数据分析 Agent，用于自动读取 Excel 数据，完成数据解析、数据清洗、统计分析、异常检测、可视化展示以及自动生成分析报告。

项目目标是将传统的人工 Excel 数据分析流程自动化，逐步构建一个具备数据理解和分析能力的智能数据分析助手。

---

# 项目介绍

在实际业务场景中，Excel 数据通常需要人工完成：

* 数据整理
* 缺失值检查
* 数据统计
* 异常数据查找
* 报告制作

本项目通过 Python 数据分析技术，实现 Excel 文件的自动化处理。

当前项目支持：

* Excel 文件读取
* 自动识别关键字段
* 数据清洗
* 数据质量检测
* 销售数据分析
* 异常数据检测
* 数据可视化
* Markdown 分析报告生成

---

# 当前实现功能

## 1. Excel 数据读取

支持读取 `.xlsx` 文件，并使用 pandas 进行数据处理。

示例：

```text
data/
└── sales.xlsx
```

---

## 2. 自动字段识别

通过 `utils/data_parser.py` 自动识别 Excel 中的重要字段。

支持：

| 字段类型 | 支持示例                    |
| ---- | ----------------------- |
| 销售字段 | 销售额、金额、收入、revenue、sales |
| 产品字段 | 产品、商品、product           |
| 日期字段 | 日期、时间、date              |

无需固定 Excel 表头名称。

例如：

数据1：

```text
日期  产品  销售额
```

数据2：

```text
交易时间  商品名称  金额
```

均可以自动识别。

---

## 3. 数据清洗

实现：

* 删除重复数据
* 删除缺失数据
* 统计清洗数量

---

## 4. 数据质量检测

支持：

* 缺失值检测
* 重复值检测
* 数据字段分析
* 数据类型统计

---

## 5. 销售数据分析

当前支持：

* 产品销售额统计
* 销售额最高产品分析

示例：

```text
最高销售产品：A产品

最高销售额：5000
```

---

## 6. 异常数据检测

使用统计方法检测异常销售数据。

用于发现：

* 异常订单
* 异常销售额
* 潜在数据问题

---

## 7. 数据可视化

自动生成产品销售额柱状图。

输出：

```text
reports/
└── product_sales.png
```

示例：

```text
产品销售额排名

A产品 █████████

B产品 █████

C产品 ██
```

---

## 8. 自动生成分析报告

支持生成：

### 文本报告

```text
reports/report.txt
```

### Markdown报告

```text
reports/analysis_report.md
```

Markdown报告包含：

* 数据概览
* 清洗结果
* 销售分析
* 异常检测结果
* 字段信息
* 数据可视化图片

---

# 项目结构

```text
AI_Data_Agent

│
├── data
│   └── sales.xlsx                 # Excel测试数据
│
├── reports
│   ├── report.txt                 # 文本报告
│   ├── analysis_report.md         # Markdown分析报告
│   └── product_sales.png          # 可视化图片
│
├── utils
│   ├── __init__.py
│   ├── analysis.py                # 数据分析模块
│   ├── data_parser.py             # 自动字段识别模块
│   └── visualization.py           # 可视化模块
│
├── config.py                      # 项目配置
├── main.py                        # 程序入口
│
├── requirements.txt               # 项目依赖
├── README.md
└── .gitignore
```

---

# 环境配置

## 创建虚拟环境

```bash
python -m venv .venv
```

---

## 安装依赖

```bash
pip install -r requirements.txt
```

---

# 使用方法

将需要分析的 Excel 文件放入：

```text
data/
```

修改：

```python
config.py
```

中的路径：

```python
DATA_PATH = "data/sales.xlsx"

REPORT_PATH = "reports/report.txt"
```

运行：

```bash
python main.py
```

程序执行流程：

```text
Excel文件

↓

自动字段识别

↓

数据清洗

↓

数据分析

↓

异常检测

↓

生成图表

↓

生成分析报告
```

---

# 技术栈

* Python
* pandas
* openpyxl
* matplotlib
* Git

---

# 后续开发计划

## Version 1.2

计划增加：

* 更多数据可视化图表
* 自动生成业务分析结论
* 优化报告模板

## Version 2.0

计划接入大语言模型：

实现：

* 自然语言分析数据
* 根据用户需求选择分析方法
* 自动调用数据分析工具
* 生成智能分析报告

最终目标：

```text
用户上传Excel

↓

AI理解数据

↓

自动分析

↓

生成业务洞察报告
```

构建真正面向业务场景的 AI Data Agent。
