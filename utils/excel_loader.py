import re

import pandas as pd

from utils.logger import get_logger


logger = get_logger(__name__)


# ==========================================================
# 表头检测（结构启发式）
#
# 不再依赖任何行业关键词，任何行业 / 任何语言的表头都能识别。
# 评分特征：
#   1. 非空单元格数（列名行通常很"满"）
#   2. 唯一值比例（列名行几乎每个单元格都不同；"本币/本币/本币"这种
#      重复标签行或空行会显著失分）
#   3. 文本占比（列名行几乎全是文本；数据行常有大量数字）
#   4. 单元格平均长度（列名通常较短；长文本数据行失分）
#   5. 后续行非空奖励（表头之后紧跟着数据行）
#   6. 位置奖励（表头更倾向于出现在文件靠前的位置）
#
# 逃生门：load_excel(header_row=N) 显式指定时跳过检测。
# ==========================================================

_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?([万亿]$)?")


def _row_features(row):
    """
    提取一行的结构特征。

    返回：(non_empty, unique_ratio, text_ratio, avg_len, numeric_count)
    """
    values = []
    for x in row.tolist():
        if pd.isna(x):
            continue
        text = str(x).strip()
        if text == "":
            continue
        values.append(text)

    non_empty = len(values)
    if non_empty == 0:
        return 0, 0.0, 0.0, 0.0, 0

    unique_ratio = len(set(values)) / non_empty
    numeric = sum(1 for v in values if _NUMBER_RE.match(v))
    text_ratio = 1.0 - numeric / non_empty
    avg_len = sum(len(v) for v in values) / non_empty

    return non_empty, unique_ratio, text_ratio, avg_len, numeric


def detect_header_row(raw_df):
    """
    自动寻找真实表头行（返回行索引）。

    评分公式：
        score = non_empty * 3
              + unique_ratio * 8
              + text_ratio * 6
              - avg_len * 0.5      # 长文本数据行（客商名、备注）失分
              - numeric_count * 3  # 数字单元格强惩罚（表头几乎无数字）
              + next_non_empty * 0.3
              + max(0, 4 - i * 0.4)
    """

    best_row = 0

    max_score = -1

    nrows = len(raw_df)

    for i, row in raw_df.iterrows():

        non_empty, unique_ratio, text_ratio, avg_len, numeric = _row_features(row)

        if non_empty == 0:
            continue

        score = (
            non_empty * 3
            + unique_ratio * 8
            + text_ratio * 6
            - avg_len * 0.5
            - numeric * 3
            + max(0, 4 - i * 0.4)
        )

        # 后续行非空奖励（数据行通常紧跟在表头后）
        if i + 1 < nrows:
            next_non_empty, _, _, _, _ = _row_features(raw_df.iloc[i + 1])
            score += next_non_empty * 0.3

        if score > max_score:

            max_score = score

            best_row = i

    return best_row




def load_excel(path, header_row=None):


    logger.info(
        f"开始扫描Excel文件:{path}"
    )



    excel = pd.ExcelFile(path)



    logger.info(
        f"发现Sheet:{excel.sheet_names}"
    )



    sheets=[]



    for sheet_name in excel.sheet_names:



        # ==========================
        # 第一次读取全部内容
        # ==========================


        raw = pd.read_excel(

            path,

            sheet_name=sheet_name,

            header=None

        )



        # ==========================
        # 自动寻找表头（header_row 显式指定时跳过检测）
        #
        # 注意：用局部变量 current_header_row，避免把第一个
        # Sheet 的检测结果带入下一个 Sheet
        # ==========================


        if header_row is not None:

            current_header_row = header_row

        else:

            current_header_row = detect_header_row(
                raw
            )



        logger.info(

            f"{sheet_name}识别表头行:{current_header_row}"

        )



        # ==========================
        # 重新读取
        # ==========================


        df = pd.read_excel(

            path,

            sheet_name=sheet_name,

            header=current_header_row

        )



        # 删除空列

        df = df.dropna(

            axis=1,

            how="all"

        )



        # 删除空行

        df = df.dropna(

            axis=0,

            how="all"

        )



        logger.info(

            f"{sheet_name}: {len(df)}行 {len(df.columns)}列"

        )



        logger.info(

            f"{sheet_name}字段:{list(df.columns)}"

        )



        sheets.append(

            {

                "sheet":
                sheet_name,


                "df":
                df

            }

        )



    return sheets