import pandas as pd

from utils.data_profiler import profile_dataframe



df=pd.read_excel(
    "data/sales.xlsx"
)


result=profile_dataframe(
    df
)


print(result)