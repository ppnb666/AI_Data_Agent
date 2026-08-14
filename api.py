import math
import os
import shutil
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

import tools
from agent import DataAgent


app = FastAPI(
    title="AI Data Agent",
    description="基于LLM的Excel智能数据分析Agent",
    version="1.0.0"
)


# ==========================================================
# 健康检查
# ==========================================================

@app.get("/")
def root():
    return {
        "message": "AI Data Agent API is running",
        "status": "ok"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ==========================================================
# 结果清洗
# ==========================================================

def clean_result(value):
    """
    清理 pandas / Python 中无法直接安全返回 JSON 的值。

    例如：

        NaN -> None
        numpy 数值 -> Python 数值
    """

    if isinstance(value, dict):

        return {
            str(key): clean_result(item)
            for key, item in value.items()
        }

    if isinstance(value, list):

        return [
            clean_result(item)
            for item in value
        ]

    # NaN / Infinity
    if isinstance(value, float):

        if math.isnan(value) or math.isinf(value):

            return None

        return value

    # numpy 类型
    if hasattr(value, "item"):

        try:
            return clean_result(
                value.item()
            )

        except Exception:
            pass

    return value


# ==========================================================
# Excel文件检查
# ==========================================================

def validate_excel_file(file: UploadFile):

    filename = file.filename or ""

    if not filename:

        raise HTTPException(
            status_code=400,
            detail="没有提供文件名"
        )

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in {
        ".xlsx",
        ".xls"
    }:

        raise HTTPException(
            status_code=400,
            detail="目前只支持 .xlsx 和 .xls 文件"
        )


# ==========================================================
# Excel + 用户问题分析
# ==========================================================

@app.post("/analyze")
def analyze(
    file: UploadFile = File(...),
    query: str = Form(...)
):
    """
    上传Excel并执行AI数据分析。

    参数：

        file:
            Excel文件

        query:
            用户自然语言分析需求
    """

    validate_excel_file(file)

    if not query.strip():

        raise HTTPException(
            status_code=400,
            detail="分析需求不能为空"
        )

    temp_path = None

    try:

        # ==================================================
        # 保存上传文件
        # ==================================================

        suffix = os.path.splitext(
            file.filename
        )[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            temp_path = temp_file.name

            shutil.copyfileobj(
                file.file,
                temp_file
            )

        # ==================================================
        # 调用现有 DataAgent
        # ==================================================

        agent = DataAgent()

        result = agent.run(
            temp_path,
            user_query=query,
            with_ai=False
        )

        # ==================================================
        # 清洗结果
        # ==================================================

        result = clean_result(
            result
        )

        return {
            "status": "success",
            "filename": file.filename,
            "query": query,
            "result": result
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"数据分析失败：{str(e)}"
        )

    finally:

        # ==================================================
        # 删除临时文件
        # ==================================================

        if temp_path and os.path.exists(
            temp_path
        ):

            try:
                os.remove(
                    temp_path
                )

            except Exception:
                pass