"""
Excel数据画像工具

负责分析Excel结构
"""

import pandas as pd


def profile_dataframe(df):

    """
    分析DataFrame结构

    返回：
    字段信息
    数据规模
    样例数据
    """

    profile = {

        "rows": len(df),

        "columns": []

    }


    for col in df.columns:


        info = {

            "name": col,

            "dtype": str(
                df[col].dtype
            ),

            "missing":

                int(
                    df[col].isnull().sum()
                ),


            "unique":

                int(
                    df[col].nunique()
                ),


            "samples":

                df[col]
                .dropna()
                .head(3)
                .tolist()

        }


        profile["columns"].append(
            info
        )


    return profile