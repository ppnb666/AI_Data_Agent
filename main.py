from agent import DataAgent
from config import DATA_PATH


if __name__ == "__main__":

    agent = DataAgent()

    result = agent.run(
        DATA_PATH,
        with_ai=True
    )

    print("任务完成")