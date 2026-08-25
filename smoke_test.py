import os

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-for-local-check")

from agent import read_only_agent, select_agent, write_agent


test_cases = [
    ("请记录一次新实验", read_only_agent),
    ("帮我记录下面的信息", read_only_agent),
    ("请保存下面的实验", read_only_agent),
    ("确认保存以上内容", read_only_agent),
    ("确认保存", write_agent),
    ("确认保存。", write_agent),
    ("确认写入数据库", write_agent),
    ("确认修改", write_agent),
    ("请修改这条记录", read_only_agent),
]


failed = []

for user_input, expected_agent in test_cases:
    actual_agent = select_agent(user_input)

    if actual_agent is not expected_agent:
        failed.append(user_input)


if failed:
    print("检查失败：以下输入的授权判断不正确")
    for item in failed:
        print("-", item)
    raise SystemExit(1)


print("自动检查通过：保存授权规则正常")