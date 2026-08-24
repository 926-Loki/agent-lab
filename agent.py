import asyncio
import os
from datetime import datetime

from agents import (
    Agent,
    Runner,
    function_tool,
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)

set_tracing_disabled(True)

@function_tool
def save_action(action: str) -> str:
    """把用户确认的下一步行动保存到本地文件。"""
    with open("actions.txt", "a", encoding="utf-8") as file:
        file.write(action + "\n")

    return f"已保存行动：{action}"

@function_tool
def read_actions() -> str:
    """读取之前保存在本地文件里的行动记录。"""
    if not os.path.exists("actions.txt"):
        return "目前还没有保存任何行动。"

    with open("actions.txt", "r", encoding="utf-8") as file:
        content = file.read().strip()

    if not content:
        return "目前还没有保存任何行动。"

    return content

@function_tool
def save_experiment(
    version: str,
    goal: str,
    changes: str,
    human_intervention: str,
    failures: str,
    result: str,
) -> str:
    """把一次完整的 Agent 实验保存到实验日志。"""
    record_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = (
        f"## {record_time} | {version}\n\n"
        f"- 实验目标：{goal}\n"
        f"- 修改内容：{changes}\n"
        f"- 人工介入：{human_intervention}\n"
        f"- 失败与异常：{failures}\n"
        f"- 最终结果：{result}\n\n"
        "---\n\n"
    )

    with open("lab_log.md", "a", encoding="utf-8") as file:
        file.write(entry)

    return f"实验记录已保存：{version}"

@function_tool
def read_experiments() -> str:
    """读取以前保存在本地的 Agent 实验档案。"""
    if not os.path.exists("lab_log.md"):
        return "目前还没有保存实验档案。"

    with open("lab_log.md", "r", encoding="utf-8") as file:
        content = file.read().strip()

    if not content:
        return "目前还没有保存实验档案。"

    return content
deepseek_client = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

deepseek_model = OpenAIChatCompletionsModel(
    model="deepseek-v4-flash",
    openai_client=deepseek_client,
)

agent = Agent(
    name="行动教练",
    instructions=(
        "把用户的目标拆成一个现在就能完成的小步骤。"
        "回答要简短、具体。"
        "只有当用户明确要求记录或保存行动时，才使用 save_action 工具。"
        "当用户要求查看、回顾或读取行动记录时，使用 read_actions 工具。"
        "当用户要求保存实验档案时，使用 save_experiment 工具。"
        "不得编造缺失的实验信息，缺少必要内容时先询问用户。"
        "当用户要求查询、回顾或总结以前的实验时，使用 read_experiments 工具。"
    ),
    tools=[save_action, read_actions, save_experiment, read_experiments],
    model=deepseek_model,
)

async def main():
    conversation = []
    print("行动教练已启动。输入“退出”即可结束。\n")

    while True:
        user_input = input("你：").strip()

        if user_input.lower() in ["退出", "exit", "quit"]:
            print("对话已结束。")
            break

        if not user_input:
            continue

        conversation.append({
            "role": "user",
            "content": user_input
        })

        result = await Runner.run(agent, conversation)

        print("\nAgent：")
        print(result.final_output)
        print()

        conversation = result.to_input_list()

if __name__ == "__main__":
    asyncio.run(main())