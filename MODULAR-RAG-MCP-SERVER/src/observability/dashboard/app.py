"""Modular RAG Dashboard – multi-page Streamlit application.

Entry-point: ``streamlit run src/observability/dashboard/app.py``

Pages are registered via ``st.navigation()`` and rendered by their
respective modules under ``pages/``.  Pages not yet implemented show
a placeholder message.
"""

from __future__ import annotations

import streamlit as st


# ── Page definitions ─────────────────────────────────────────────────

def _page_overview() -> None:
    from src.observability.dashboard.pages.overview import render
    render()


def _page_data_browser() -> None:
    from src.observability.dashboard.pages.data_browser import render
    render()


def _page_ingestion_manager() -> None:
    from src.observability.dashboard.pages.ingestion_manager import render
    render()


def _page_ingestion_traces() -> None:
    from src.observability.dashboard.pages.ingestion_traces import render
    render()


def _page_query_traces() -> None:
    from src.observability.dashboard.pages.query_traces import render
    render()


def _page_evaluation_panel() -> None:
    from src.observability.dashboard.pages.evaluation_panel import render
    render()


# ── Navigation ───────────────────────────────────────────────────────

pages = [
    st.Page(_page_overview, title="系统总览", icon="📊", default=True),
    st.Page(_page_data_browser, title="数据浏览", icon="🔍"),
    st.Page(_page_ingestion_manager, title="摄取管理", icon="📥"),
    st.Page(_page_ingestion_traces, title="摄取追踪", icon="🔬"),
    st.Page(_page_query_traces, title="查询追踪", icon="🔎"),
    st.Page(_page_evaluation_panel, title="评估面板", icon="📏"),
]


def main() -> None:
    st.set_page_config(
        page_title="Modular RAG 可视化面板",
        page_icon="📊",
        layout="wide",
    )

    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
else:
    # When run directly via `streamlit run app.py`
    main()
