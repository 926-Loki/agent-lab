import asyncio
import hmac
import os

import streamlit as st
from agents import Runner


st.set_page_config(
    page_title="Agent 实验记录助手",
    page_icon="🧪",
)


def get_secret(name: str):
    if name in os.environ:
        return os.environ[name]

    try:
        return st.secrets[name]
    except Exception:
        return None


deepseek_key = get_secret("DEEPSEEK_API_KEY")

if not deepseek_key:
    st.error("尚未配置 DeepSeek API 密钥。")
    st.stop()

os.environ["DEEPSEEK_API_KEY"] = deepseek_key
supabase_url = get_secret("SUPABASE_URL")
supabase_key = get_secret("SUPABASE_KEY")

if supabase_url and supabase_key:
    os.environ["SUPABASE_URL"] = supabase_url
    os.environ["SUPABASE_KEY"] = supabase_key
app_password = get_secret("APP_PASSWORD")

if app_password:
    if not st.session_state.get("authenticated", False):
        st.title("Agent 实验记录助手")
        password_input = st.text_input(
            "请输入访问密码",
            type="password",
        )

        if st.button("进入"):
            if hmac.compare_digest(password_input, app_password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("密码错误。")

        st.stop()

    if st.sidebar.button("退出登录"):
        st.session_state.authenticated = False
        st.rerun()


from agent import select_agent, database

st.title("Agent 实验记录助手")
st.caption("记录、读取和复盘 Agent 实验")

st.sidebar.markdown("### 最近实验档案")

try:
    if database:
        response = (
            database.table("agent_records")
            .select("content, created_at")
            .eq("record_type", "experiment")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        recent_records = [
            row
            for row in (response.data or [])
            if (row.get("content") or {}).get("status") != "invalid"
        ]

        if recent_records:
            for row in recent_records:
                content = row.get("content") or {}
                version = content.get("version", "未命名版本")

                with st.sidebar.expander(version):
                    st.write(content.get("goal", "暂无实验目标"))
        else:
            st.sidebar.caption("暂无有效实验档案")
    else:
        st.sidebar.caption("数据库未连接")

except Exception:
    st.sidebar.warning("暂时无法读取实验档案")

if st.sidebar.button("开始新对话"):
    st.session_state.messages = []
    st.session_state.conversation = []
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("请输入你的问题或实验记录……")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.conversation.append({
        "role": "user",
        "content": user_input,
    })

    with st.chat_message("assistant"):
        with st.spinner("Agent 正在处理……"):
            try:
                result = asyncio.run(
                    Runner.run(
    select_agent(user_input),
    st.session_state.conversation,
)
                )

                answer = result.final_output
                st.markdown(answer)

                st.session_state.conversation = result.to_input_list()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                })

            except Exception as error:
                st.error(f"运行失败：{error}")