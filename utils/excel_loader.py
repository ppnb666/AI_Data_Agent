import pandas as pd

from utils.logger import get_logger


logger = get_logger(__name__)



def detect_header_row(raw_df):

    """
    自动寻找Excel真实表头
    """

    keywords = [

        "客商名称",
        "客户名称",
        "业务类型",
        "业务种类",
        "期末余额",
        "余额"

    ]


    best_row = 0

    max_score = 0



    for i,row in raw_df.iterrows():


        values = [

            str(x)
            for x in row.tolist()

        ]


        text = " ".join(values)



        score = 0


        for key in keywords:

            if key in text:

                score += 1



        if score > max_score:


            max_score = score

            best_row = i



    return best_row




def load_excel(path):


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
        # 自动寻找表头
        # ==========================


        header_row = detect_header_row(
            raw
        )



        logger.info(

            f"{sheet_name}识别表头行:{header_row}"

        )



        # ==========================
        # 重新读取
        # ==========================


        df = pd.read_excel(

            path,

            sheet_name=sheet_name,

            header=header_row

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