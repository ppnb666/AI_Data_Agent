import pandas as pd
from utils.logger import get_logger


logger = get_logger(__name__)


def load_excel(file_path):

    """
    智能读取Excel

    自动选择数据量最大的sheet
    """

    logger.info(
        f"开始扫描Excel文件:{file_path}"
    )


    excel = pd.ExcelFile(
        file_path
    )


    sheets = excel.sheet_names


    logger.info(
        f"发现Sheet:{sheets}"
    )


    candidates = []


    for sheet in sheets:

        try:

            df = pd.read_excel(
                file_path,
                sheet_name=sheet
            )


            rows = len(df)

            cols = len(df.columns)


            candidates.append(
                {
                    "sheet":sheet,
                    "rows":rows,
                    "cols":cols,
                    "df":df
                }
            )


            logger.info(
                f"{sheet}: {rows}行 {cols}列"
            )


        except Exception as e:

            logger.warning(
                f"{sheet}读取失败:{e}"
            )



    if not candidates:

        raise Exception(
            "没有找到有效数据Sheet"
        )


    # 选择数据量最大的sheet

    best = max(
        candidates,
        key=lambda x:x["rows"]*x["cols"]
    )


    logger.info(
        f"自动选择Sheet:{best['sheet']}"
    )


    return best["df"], best["sheet"]