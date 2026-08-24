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
from supabase import Client, create_client


set_tracing_disabled(True)


def connect_database() -> Client | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        return None

    return create_client(url, key)


database = connect_database()


@function_tool
def save_action(action: str) -> str:
    """把用户确认的下一步行动保存起来。"""
    if database:
        database.table("agent_records").insert({
            "record_type": "action",
            "content": {
                "action": action,
            },
        }).execute()

        return f"已保存云端行动：{action}"

    with open("actions.txt", "a", encoding="utf-8") as file:
        file.write(action + "\n")

    return f"已保存在本地：{action}"


@function_tool
def read_actions() -> str:
    """读取以前保存的行动记录。"""
    if database:
        response = (
            database.table("agent_records")
            .select("content, created_at")
            .eq("record_type", "action")
            .order("created_at")
            .execute()
        )

        rows = response.data or []

        if not rows:
            return "目前还没有保存任何行动。"

        actions = []

        for row in rows:
            content = row.get("content") or {}
            action = content.get("action")

            if action:
                actions.append(f"- {action}")

        return "\n".join(actions)

    if not os.path.exists("actions.txt"):
        return "目前还没有保存任何行动。"

    with open("actions.txt", "r", encoding="utf-8") as file:
        content = file.read().strip()

    return content or "目前还没有保存任何行动。"


@function_tool
def save_experiment(
    version: str,
    goal: str,
    changes: str,
    human_intervention: str,
    failures: str,
    result: str,
) -> str:
    """把一次完整的 Agent 实验保存起来。"""
    experiment = {
        "version": version,
        "goal": goal,
        "changes": changes,
        "human_intervention": human_intervention,
        "failures": failures,
        "result": result,
    }

    if database:
        try:
            database.table("agent_records").insert({
                "record_type": "experiment",
                "content": experiment,
            }).execute()

            return f"云端实验记录已保存：{version}"

        except Exception as error:
            error_text = str(error).lower()

            if "23505" in error_text or "duplicate" in error_text:
                return f"版本 {version} 已经存在，本次没有重复保存。"

            raise

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

    return f"本地实验记录已保存：{version}"
@function_tool
def read_experiments() -> str:
    """读取以前保存的 Agent 实验档案。"""
    if database:
        response = (
            database.table("agent_records")
            .select("content, created_at")
            .eq("record_type", "experiment")
            .order("created_at")
            .execute()
        )

        rows = response.data or []

        if not rows:
            return "目前还没有保存实验档案。"

        records = []

        for row in rows:
            content = row.get("content") or {}
            created_at = row.get("created_at", "")

            records.append(
                f"## {created_at} | "
                f"{content.get('version', '未命名版本')}\n\n"
                f"- 实验目标：{content.get('goal', '')}\n"
                f"- 修改内容：{content.get('changes', '')}\n"
                f"- 人工介入："
                f"{content.get('human_intervention', '')}\n"
                f"- 失败与异常：{content.get('failures', '')}\n"
                f"- 最终结果：{content.get('result', '')}"
            )

        return "\n\n---\n\n".join(records)

    if not os.path.exists("lab_log.md"):
        return "目前还没有保存实验档案。"

    with open("lab_log.md", "r", encoding="utf-8") as file:
        content = file.read().strip()

    return content or "目前还没有保存实验档案。"


deepseek_client = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

deepseek_model = OpenAIChatCompletionsModel(
    model="deepseek-v4-flash",
    openai_client=deepseek_client,
)

write_agent = Agent(
    name="Agent实验记录助手",
    instructions=(
        "当前用户消息已经通过程序的保存授权检查。"
        "实验必须包含版本号、实验目标、修改内容、人工介入、失败与异常、最终结果。"
        "缺少任何一项都不能调用保存工具，也不能自行编造。"
        "如果实验信息不完整，使用中文自然语言一次只询问一项。"
        "不要向用户展示 version、changes 等内部字段名。"
        "保存行动时使用 save_action。"
        "保存实验时使用 save_experiment。"
        "查询行动时使用 read_actions。"
        "查询实验时使用 read_experiments。"
    ),
    tools=[
        save_action,
        read_actions,
        save_experiment,
        read_experiments,
    ],
    model=deepseek_model,
)


read_only_agent = Agent(
    name="Agent实验记录助手",
        instructions=(
        "帮助用户查询和整理 Agent 实验。"
        "你当前没有保存权限，不能声称已经保存任何内容。"
        "普通描述不能写入数据库。"
        "查询行动时使用 read_actions。"
        "查询实验时使用 read_experiments。"
        "一份完整实验必须包含：版本号、实验目标、修改内容、"
        "人工介入、失败与异常、最终结果。"
        "如果用户想记录实验，必须按照上述顺序逐项收集，不能漏项。"
        "每次只询问一个问题，使用自然中文，不显示英文参数名。"
        "全部收集完成后先复述整理结果，"
        "再要求用户明确回复“确认保存”。"
    ),
    tools=[
        read_actions,
        read_experiments,
    ],
    model=deepseek_model,
)


def select_agent(user_input: str):
    normalized = user_input.strip()

    save_commands = (
        "请保存",
        "帮我保存",
        "请记录",
        "帮我记录",
        "写入数据库",
    )

    if normalized == "确认保存":
        return write_agent

    if any(normalized.startswith(command) for command in save_commands):
        return write_agent

    return read_only_agent


async def main():
    conversation = []
    print("Agent 实验记录助手已启动。输入“退出”即可结束。\n")

    while True:
        user_input = input("你：").strip()

        if user_input.lower() in ["退出", "exit", "quit"]:
            print("对话已结束。")
            break

        if not user_input:
            continue

        conversation.append({
            "role": "user",
            "content": user_input,
        })

        result = await Runner.run(
    select_agent(user_input),
    conversation,
)

        print("\nAgent：")
        print(result.final_output)
        print()

        conversation = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(main())