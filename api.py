import json
import math
import os
import shutil
import tempfile
import uuid
from typing import Dict, Optional, List, Any

import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

# 导入你的现有模块
from agent import DataAgent
from llm.client import get_client
from utils.logger import get_logger

# ==========================================================
# 初始化 FastAPI
# ==========================================================
app = FastAPI(
    title="AI Data Agent",
    description="基于LLM的Excel智能数据分析Agent - 支持任意格式文件",
    version="2.0.0"
)

logger = get_logger(__name__)

# ==========================================================
# 全局映射存储（生产环境请替换为Redis或数据库）
# ==========================================================
mapping_store: Dict[str, Dict[str, Optional[str]]] = {}  # session_id -> mapping


# ==========================================================
# Pydantic 模型
# ==========================================================
class MappingConfirmRequest(BaseModel):
    mapping: Dict[str, Optional[str]]  # {"customer": "客商名称", "amount": "期末余额", ...}


# ==========================================================
# 辅助函数：清理返回结果（来自原文件）
# ==========================================================
def clean_result(value):
    """清理 pandas / Python 中无法直接安全返回 JSON 的值。"""
    if isinstance(value, dict):
        return {str(key): clean_result(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_result(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if hasattr(value, "item"):  # numpy 类型
        try:
            return clean_result(value.item())
        except Exception:
            pass
    return value


# ==========================================================
# 辅助函数：字段猜测 Prompt 构建
# ==========================================================
def build_field_guess_prompt(columns: List[str], sample: List[Dict]) -> str:
    """构建让 LLM 猜测字段映射的 Prompt。"""
    sample_text = ""
    for i, row in enumerate(sample, 1):
        row_items = [f"{col}: {row.get(col, '')}" for col in columns if col in row]
        sample_text += f"第{i}行: " + " | ".join(row_items) + "\n"

    prompt = f"""
请分析以下Excel文件的列名和前3行示例数据，判断每个列属于哪种业务概念。

列名: {columns}

示例数据:
{sample_text}

请输出一个JSON对象，键为以下概念，值为对应的列名（如果找不到对应列，则填null）：
- customer: 客户名称/客商名称/公司名称
- amount: 金额/数值（如销售额、余额、贷方、借方等）
- business: 业务类型/业务种类/产品线
- date: 日期/年份/期间
- product: 产品名称/商品名称
- department: 部门/事业部
- project: 项目名称/工程名称

注意：
1. 列名可能中英文混合，请根据语义匹配。
2. 如果某一列包含"客户"、"客商"、"公司"等词，应映射为customer。
3. 如果某一列包含"金额"、"余额"、"销售额"、"收入"、"贷方"、"借方"等词，应映射为amount。
4. 如果某一列包含"业务"、"产品线"、"类型"等词，应映射为business。
5. 日期列可能叫"日期"、"时间"、"月份"、"年份"等。
6. 如果某个概念在数据中不存在，请填null。

只输出JSON，不要包含markdown代码块或其他文字。
JSON格式示例:
{{"customer": "客户名称", "amount": "期末余额", "business": "业务类型", "date": "年份", "product": null, "department": null, "project": null}}
"""
    return prompt


# ==========================================================
# 辅助函数：解析 LLM 返回的 JSON
# ==========================================================
def parse_llm_response(response: str) -> Dict[str, Optional[str]]:
    """从 LLM 返回的文本中提取 JSON 映射。"""
    if not response:
        return {}

    text = response.strip()

    # 去除可能的 markdown 标记
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
        # 角色集合从 schema.roles.LLM_ALLOWED_ROLES 动态获取，
        # 避免新角色（region/person/category 等）漏掉（不含 unknown）
        from schema.roles import LLM_ALLOWED_ROLES
        allowed_keys = set(LLM_ALLOWED_ROLES)
        result = {k: data.get(k) for k in allowed_keys}
        # 将空字符串转为 None
        for k in result:
            if result[k] == "":
                result[k] = None
        return result
    except json.JSONDecodeError:
        # 若解析失败，返回空映射（所有字段为 None）
        return {}


# ==========================================================
# 健康检查接口
# ==========================================================
@app.get("/")
def root():
    return {
        "message": "AI Data Agent API is running",
        "status": "ok",
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ==========================================================
# 支持的文件扩展名
# ==========================================================
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".json"}


# ==========================================================
# 接口1：文件预览 + 字段猜测
# ==========================================================
@app.post("/preview")
async def preview_file(file: UploadFile = File(...)):
    """
    上传数据文件，返回列名、示例数据以及LLM猜测的字段映射。
    支持 .xlsx / .xls / .csv / .json。
    """
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"仅支持 {sorted(SUPPORTED_EXTENSIONS)} 文件")

    # 保存临时文件
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        # 用统一加载器读取（复用表头启发式检测）
        from utils.data_loader import load_file

        sheets = load_file(tmp_path)
        first = sheets[0]
        df_preview = first["df"]
        if df_preview.empty:
            raise HTTPException(status_code=400, detail="文件为空或无法读取")

        columns = [str(col) for col in df_preview.columns]
        # 示例数据（处理特殊类型）
        sample_records = df_preview.head(3).to_dict(orient="records")
        for record in sample_records:
            for k, v in record.items():
                if pd.isna(v):
                    record[k] = None
                elif isinstance(v, (pd.Timestamp, pd.Timedelta)):
                    record[k] = str(v)

        # 调用 LLM 猜测映射
        llm = get_client()
        prompt = build_field_guess_prompt(columns, sample_records)
        llm_response = llm.chat([
            {"role": "system", "content": "你是一个数据分析专家，擅长识别Excel列的含义。只输出JSON，不要解释。"},
            {"role": "user", "content": prompt}
        ])
        suggested_mapping = parse_llm_response(llm_response)

        # 确保所有键都存在
        for key in ["customer", "amount", "business", "date", "product", "department", "project"]:
            if key not in suggested_mapping:
                suggested_mapping[key] = None

        return {
            "status": "success",
            "filename": filename,
            "columns": columns,
            "sample": sample_records,
            "suggested_mapping": suggested_mapping
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# ==========================================================
# 接口2：确认/保存字段映射
# ==========================================================
@app.post("/confirm_mapping")
async def confirm_mapping(request: MappingConfirmRequest):
    """
    接收用户确认的字段映射，生成 session_id 并保存映射。
    """
    mapping = request.mapping
    if not isinstance(mapping, dict):
        raise HTTPException(status_code=400, detail="映射格式错误")

    # 清理映射：去除空值，统一键
    cleaned = {}
    for key in ["customer", "amount", "business", "date", "product", "department", "project"]:
        val = mapping.get(key)
        if val and isinstance(val, str) and val.strip():
            cleaned[key] = val.strip()
        else:
            cleaned[key] = None

    # 生成 session_id
    session_id = str(uuid.uuid4())
    mapping_store[session_id] = cleaned

    return {
        "status": "success",
        "session_id": session_id,
        "mapping": cleaned,
        "message": "映射已保存，请在后续请求中传入 session_id"
    }


# ==========================================================
# 接口3：核心数据分析接口（原有功能增强）
# ==========================================================
@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    query: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    """
    上传Excel并执行AI数据分析。
    如果提供了 session_id，则加载对应的字段映射。
    """
    # 验证文件
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"目前只支持 {sorted(SUPPORTED_EXTENSIONS)} 文件")

    if not query.strip():
        raise HTTPException(status_code=400, detail="分析需求不能为空")

    # 获取映射（如果提供了 session_id）
    mapping = None
    if session_id:
        if session_id not in mapping_store:
            raise HTTPException(status_code=404, detail="无效的 session_id，请重新上传文件并配置映射")
        mapping = mapping_store[session_id]

    temp_path = None
    try:
        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name

        # 调用 Agent
        agent = DataAgent()
        result = agent.run(
            file_path=temp_path,
            user_query=query,
            with_ai=False,
            mapping=mapping  # 假设 agent.run 已支持 mapping 参数
        )

        # 清洗结果（确保 JSON 可序列化）
        result = clean_result(result)

        return {
            "status": "success",
            "filename": filename,
            "query": query,
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据分析失败: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ==========================================================
# 可选：获取当前所有映射（调试用）
# ==========================================================
@app.get("/mappings")
def list_mappings():
    """返回当前存储的所有映射（仅用于调试）。"""
    return {"mappings": mapping_store}


# ==========================================================
# 启动服务（可直接运行该文件）
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)