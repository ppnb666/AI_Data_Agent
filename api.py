from fastapi import FastAPI
from pydantic import BaseModel

from agent import DataAgent
from config import DATA_PATH


# ======================
# 创建FastAPI应用
# ======================

app = FastAPI(
    title="AI Data Agent API",
    description="基于DeepSeek的企业数据查询Agent",
    version="1.0"
)


# ======================
# 初始化Agent
# ======================

agent = DataAgent()



# ======================
# 请求数据格式
# ======================

class QueryRequest(BaseModel):

    query: str



# ======================
# 测试接口
# ======================

@app.get("/")
def home():

    return {

        "message":
        "AI Data Agent运行成功"

    }



# ======================
# AI数据分析接口
# ======================

@app.post("/analyze")
def analyze(
    request: QueryRequest
):


    result = agent.run(

        DATA_PATH,

        user_query=request.query,

        with_ai=True

    )


    return result