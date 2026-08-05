# AI_Data_Agent

基于 Python 的智能数据分析 Agent，用于自动读取 Excel 数据，完成数据清洗、字段识别、统计分析和分析报告生成。

## 项目介绍

在实际业务场景中，Excel 数据通常需要人工进行整理、清洗和分析。本项目尝试构建一个自动化数据分析工具，通过 Python 实现：

* Excel 文件自动读取
* 数据质量检测
* 数据清洗
* 关键字段自动识别
* 销售数据分析
* 异常数据检测
* 自动生成分析报告

项目目标是逐步从传统数据分析脚本升级为具备智能分析能力的 Data Agent。

---

## 当前实现功能

### 1. Excel 数据读取

支持读取 `.xlsx` 文件，并使用 pandas 进行数据处理。

---

### 2. 自动字段识别

通过 `data_parser.py` 自动识别 Excel 中的重要字段：

* 销售额字段
* 产品字段
* 日期字段

例如支持：

| 类型  | 示例字段              |
| --- | ----------------- |
| 销售额 | 销售额、金额、收入、revenue |
| 产品  | 产品、商品、product     |
| 日期  | 日期、时间、date        |

无需固定 Excel 列名。

---

### 3. 数据清洗

实现：

* 删除重复数据
* 删除缺失数据
* 统计清洗数量

---

### 4. 数据质量检测

支持：

* 缺失值检测
* 重复数据检测
* 数据类型分析

---

### 5. 销售分析

当前支持：

* 产品销售额统计
* 销售最高产品分析

---

### 6. 异常数据检测

使用统计方法检测异常销售数据，帮助发现可能存在的数据异常。

---

### 7. 自动生成分析报告

程序运行后生成：

```
reports/report.txt
```

报告包含：

* 数据量
* 清洗情况
* 销售冠军
* 字段信息
* 分析结果

---

# 项目结构

```
AI_Data_Agent

│
├── data
│   └── sales.xlsx              # 测试数据
│
├── reports
│   └── report.txt              # 分析报告
│
├── utils
│   ├── __init__.py
│   ├── analysis.py             # 数据分析模块
│   └── data_parser.py           # 自动字段识别模块
│
├── config.py                    # 项目配置
├── main.py                      # 程序入口
│
├── requirements.txt             # 项目依赖
├── README.md
└── .gitignore
```

---

# 环境配置

## 1. 创建虚拟环境

```bash
python -m venv .venv
```

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

---

# 使用方法

将需要分析的 Excel 文件放入：

```
data/
```

修改 `config.py` 中的数据路径：

```python
DATA_PATH = "data/sales.xlsx"
REPORT_PATH = "reports/report.txt"
```

运行：

```bash
python main.py
```

程序会自动：

1. 读取 Excel 文件
2. 检测数据字段
3. 清洗数据
4. 分析销售情况
5. 输出分析报告

---

# 技术栈

* Python
* pandas
* openpyxl
* Git

---

# 后续计划

## Version 1.1

* 增加数据可视化
* 自动生成图表
* 优化分析报告格式

## Version 1.2

* 增强异常检测算法
* 支持更多业务数据类型

## Version 2.0

* 接入大语言模型
* 实现自然语言数据分析
* 构建真正的 AI Data Agent

---

# 项目目标

通过 Python 数据分析技术与 AI 技术结合，实现从：

```
Excel数据
    ↓
自动解析
    ↓
数据分析
    ↓
智能报告生成
```

逐步构建面向实际业务场景的数据分析智能助手。
