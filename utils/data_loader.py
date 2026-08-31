"""
多格式数据文件加载抽象

load_file(path) -> List[{"sheet", "df"}]

支持：
    .xlsx / .xls    复用 excel_loader.load_excel（含表头启发式检测）
    .csv            编码链 utf-8-sig → gbk → latin-1，同样走表头启发式
    .json           兼容 [{record}] 与 {"sheets": {"Sheet1": [...], ...}}

返回结构与 state.sheet_profiles 完全一致，下游零改动。
"""

import json
import os

import pandas as pd

from utils.logger import get_logger
from utils.excel_loader import load_excel, detect_header_row


logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".json"}

_CSV_ENCODINGS = ("utf-8-sig", "gbk", "latin-1")


def load_file(path, header_row=None):
    """按扩展名分发加载，返回 List[{"sheet": str, "df": DataFrame}]"""
    ext = os.path.splitext(str(path))[1].lower()

    if ext in {".xlsx", ".xls"}:
        return load_excel(path, header_row=header_row)

    if ext == ".csv":
        return _load_csv(path, header_row)

    if ext == ".json":
        return _load_json(path)

    raise ValueError(
        f"不支持的文件格式: {ext}，支持: {sorted(SUPPORTED_EXTENSIONS)}"
    )


# ==========================================================
# CSV
# ==========================================================

def _read_csv_raw(path):
    """按编码链读取 CSV，返回 (raw_df, encoding)，全部失败抛 ValueError"""
    last_err = None
    for enc in _CSV_ENCODINGS:
        try:
            raw = pd.read_csv(path, encoding=enc, header=None)
            return raw, enc
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
    raise ValueError(
        f"无法解码 CSV 文件: {path} "
        f"（已尝试 {_CSV_ENCODINGS}）: {last_err}"
    )


def _load_csv(path, header_row=None):
    raw, enc = _read_csv_raw(path)

    if header_row is None:
        header_row = detect_header_row(raw)

    df = pd.read_csv(path, encoding=enc, header=header_row)

    df = _clean_frame(df)

    sheet_name = os.path.splitext(os.path.basename(path))[0]

    logger.info(f"CSV加载完成: {path} → {sheet_name}: {len(df)}行 {len(df.columns)}列")

    return [{"sheet": sheet_name, "df": df}]


# ==========================================================
# JSON
# ==========================================================

def _load_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    sheets = []

    # 格式1: {"sheets": {"Sheet1": [record, ...], ...}}
    if isinstance(data, dict) and isinstance(data.get("sheets"), dict):
        for name, records in data["sheets"].items():
            df = _clean_frame(pd.DataFrame(records))
            sheets.append({"sheet": str(name), "df": df})

    # 格式2: [record, ...]
    elif isinstance(data, list):
        sheets.append({
            "sheet": "Sheet1",
            "df": _clean_frame(pd.DataFrame(data)),
        })

    # 格式3: 单个 record
    elif isinstance(data, dict):
        sheets.append({
            "sheet": "Sheet1",
            "df": _clean_frame(pd.DataFrame([data])),
        })

    else:
        raise ValueError(f"无法识别的 JSON 结构: {path}")

    logger.info(
        f"JSON加载完成: {path} → {[s['sheet'] for s in sheets]}"
    )

    return sheets


# ==========================================================
# 公共清洗
# ==========================================================

def _clean_frame(df):
    """删除全空列 / 全空行"""
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    return df
