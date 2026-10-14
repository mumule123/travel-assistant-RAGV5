import asyncio
import json
import streamlit as st

from agentscope.model import OpenAIChatModel
from cli import AligoCLI
from config import LLM_CONFIG
from config_agentscope import init_agentscope
from context.memory_manager import MemoryManager
from agents.intention_agent import IntentionAgent
from agents.orchestration_agent import OrchestrationAgent
from agents.lazy_agent_registry import LazyAgentRegistry


st.set_page_config(page_title="TravelOps Agent Hub", page_icon="✈️", layout="wide")
st.title("✈️ TravelOps Agent Hub")


def safe_rerun():
    """Compat for different Streamlit versions."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


@st.cache_resource
def init_system(user_id: str):
    init_agentscope()
    model = OpenAIChatModel(
        model_name=LLM_CONFIG["model_name"],
        api_key=LLM_CONFIG["api_key"],
        client_kwargs={"base_url": LLM_CONFIG["base_url"]},
    )
    memory_manager = MemoryManager(user_id=user_id, session_id="web_session", llm_model=model)
    intention_agent = IntentionAgent(name="IntentionAgent", model=model)
    registry = LazyAgentRegistry(model=model, cache={}, memory_manager=memory_manager)
    orchestrator = OrchestrationAgent(name="Orchestrator", agent_registry=registry, memory_manager=memory_manager)
    return model, memory_manager, intention_agent, orchestrator


def get_active_user_id() -> str:
    return st.session_state.get("current_user_id", "default_user")


def ensure_messages():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "您好！我是 TravelOps Agent Hub，可以帮您规划行程、查询差旅政策。请问有什么可以帮您？",
            }
        ]


def _sanitize_display_text(text: str) -> str:
    """Avoid markdown side effects in model text (e.g. strikethrough)."""
    if not text:
        return ""
    # Remove markdown strikethrough markers and normalize temperature ranges.
    sanitized = text.replace("~~", "")
    sanitized = sanitized.replace("~", "-")
    return sanitized


def build_final_response(result_data: dict) -> str:
    """Keep Web final response in sync with CLI plain-text formatter."""
    formatter = AligoCLI()
    response = formatter._build_plain_response(result_data)
    return _sanitize_display_text(response)


async def build_long_term_summary(memory_manager: MemoryManager, user_input: str = "") -> str:
    summary_parts = []

    prefs = memory_manager.long_term.get_preference()
    if prefs:
        pref_lines = ["【用户背景信息】（来自长期记忆，可用于推断缺失信息）"]
        for pref_key, pref_value in prefs.items():
            if pref_value:
                if isinstance(pref_value, list):
                    pref_lines.append(f"• {pref_key}: {', '.join(pref_value)}")
                else:
                    pref_lines.append(f"• {pref_key}: {pref_value}")
        if len(pref_lines) > 1:
            summary_parts.extend(pref_lines)

    chat_summary = await memory_manager.get_long_term_summary_async(max_messages=50)
    if chat_summary:
        summary_parts.append("\n【历史会话总结】")
        summary_parts.append(chat_summary)

    all_trips = memory_manager.long_term.get_trip_history(limit=None)
    if all_trips:
        relevant_trips = []
        other_trips = []
        for trip in all_trips:
            origin = trip.get("origin", "") or ""
            destination = trip.get("destination", "") or ""
            if (origin and origin in user_input) or (destination and destination in user_input):
                relevant_trips.append(trip)
            else:
                other_trips.append(trip)
        trips_to_show = relevant_trips[:2] + other_trips[:1]
        if trips_to_show:
            summary_parts.append("\n【历史行程】")
            for i, trip in enumerate(trips_to_show[:3], 1):
                origin = trip.get("origin", "未知")
                destination = trip.get("destination", "未知")
                start_date = trip.get("start_date", "")
                purpose = trip.get("purpose", "")
                relevance_mark = "✦ " if trip in relevant_trips else ""
                summary_parts.append(
                    f"{i}. {relevance_mark}{origin} → {destination} ({start_date}) - {purpose}"
                )

    return "\n".join(summary_parts) if summary_parts else ""


async def process_chat(user_input: str, memory_manager: MemoryManager, intention_agent, orchestrator):
    from agentscope.message import Msg

    long_term_summary = await build_long_term_summary(memory_manager, user_input)
    recent_context = memory_manager.short_term.get_recent_context(n_turns=5)
    context_messages = []
    if long_term_summary:
        context_messages.append(Msg(name="system", content=long_term_summary, role="system"))
    for msg in recent_context:
        context_messages.append(Msg(name=msg["role"], content=msg["content"], role=msg["role"]))
    context_messages.append(Msg(name="user", content=user_input, role="user"))

    intention_result = await intention_agent.reply(context_messages)
    orchestration_result = await orchestrator.reply(intention_result)
    result_data = json.loads(orchestration_result.content)
    memory_manager.add_message("user", user_input)
    memory_manager.add_message("assistant", json.dumps(result_data, ensure_ascii=False))
    return result_data


st.sidebar.header("身份与数据")
user_options = ["default_user", "test_user", "user_001"]
selected_user = st.sidebar.selectbox("选择用户", user_options, index=0)
custom_user = st.sidebar.text_input("或输入自定义用户ID")
if st.sidebar.button("登录"):
    st.session_state.current_user_id = custom_user.strip() or selected_user
    # 彻底清理旧用户的对话
    if "messages" in st.session_state:
        del st.session_state["messages"]
    # 清理缓存，确保新用户获得独立的 MemoryManager 实例
    init_system.clear()
    safe_rerun()

if st.sidebar.button("刷新数据"):
    safe_rerun()

current_user_id = get_active_user_id()
model, memory_manager, intention_agent, orchestrator = init_system(current_user_id)
ensure_messages()

st.sidebar.divider()
st.sidebar.subheader("🛠️ 系统后台")
st.sidebar.markdown(
    """
    <a href="http://localhost:8502" target="_blank" style="
        display: inline-block;
        padding: 0.5em 1em;
        color: white;
        background-color: #FF4B4B;
        border-radius: 0.3em;
        text-decoration: none;
        text-align: center;
        width: 100%;
        margin-bottom: 0.5em;">
        👉 打开 RAG 监控大盘
    </a>
    """,
    unsafe_allow_html=True
)
st.sidebar.caption("提示：点击可跳转至独立的 Modular RAG 控制台，查看知识库状态与底层检索漏斗。")
st.sidebar.divider()

st.sidebar.subheader("记忆统计")
full_context = memory_manager.get_full_context()
short_term_stats = full_context["short_term"]["statistics"]
long_term_stats = full_context["long_term"]["statistics"]
st.sidebar.metric("短期消息数", short_term_stats.get("total_messages", 0))
st.sidebar.metric("历史行程数", long_term_stats.get("total_trips", 0))

st.sidebar.subheader("历史行程")
history_items = memory_manager.long_term.get_trip_history(10)
if history_items:
    st.sidebar.table([
        {
            "出发地": trip.get("origin", ""),
            "目的地": trip.get("destination", ""),
            "日期": trip.get("start_date", ""),
            "目的": trip.get("purpose", ""),
        }
        for trip in history_items
    ])
else:
    st.sidebar.caption("暂无历史行程")

st.sidebar.subheader("用户偏好")
prefs = memory_manager.long_term.get_preference()
if prefs:
    pref_rows = []
    for key, value in prefs.items():
        if value and (not isinstance(value, list) or len(value) > 0):
            pref_rows.append({"类型": key, "值": ", ".join(value) if isinstance(value, list) else value})
    if pref_rows: 
        st.sidebar.table(pref_rows)
    else:
        st.sidebar.caption("暂无偏好记录")
else:
    st.sidebar.caption("暂无偏好记录")


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


if user_input := st.chat_input("请输入您的需求，例如：我要去北京出差，住宿标准是多少？"):
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("思考中，正在调度智能体..."):
            try:
                result_data = asyncio.run(process_chat(user_input, memory_manager, intention_agent, orchestrator))
                final_response = build_final_response(result_data)
                # Render unified final answer after all agent tasks complete.
                st.text(final_response)
                st.session_state.messages.append({"role": "assistant", "content": final_response})

                with st.expander("查看原始 JSON"):
                    st.json(result_data)
                safe_rerun()
            except Exception as e:
                st.error(f"处理出错: {str(e)}")
