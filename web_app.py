import asyncio
import os

import streamlit as st
from agents import Runner


st.set_page_config(
    page_title="Agent 实验记录助手",
    page_icon="🧪",
)

if "DEEPSEEK_API_KEY" not in os.environ:
    try:
        os.environ["DEEPSEEK_API_KEY"] = st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        st.error("尚未配置 DeepSeek API 密钥。")
        st.stop()

from agent import agent

st.title("Agent 实验记录助手")
st.caption("记录、读取和复盘 Agent 实验")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation" not in st.session_state:
    st.session_state.conversation = []

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
                        agent,
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