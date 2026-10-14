"""Ingestion Traces page – browse ingestion trace history with per-stage detail.

Layout:
1. Trace list (reverse-chronological, filtered to trace_type=="ingestion")
2. Pipeline overview: source file, total time, stage timing waterfall
3. Per-stage detail tabs:
   📄 Load    – raw document text preview
   ✂️ Split   – chunk list with text
   🔄 Transform – before/after diff, enrichment metadata
   🔢 Embed   – vector stats
   💾 Upsert  – stored IDs
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import streamlit as st

from src.observability.dashboard.services.trace_service import TraceService

logger = logging.getLogger(__name__)

_INGEST_STAGE_LABELS = {
    "load": "加载",
    "split": "切块",
    "transform": "转换",
    "embed": "编码",
    "upsert": "写入",
}


def _ingest_stage_label(stage_name: str) -> str:
    return _INGEST_STAGE_LABELS.get(stage_name, stage_name)


def render() -> None:
    """Render the Ingestion Traces page."""
    st.header("🔬 摄取追踪")

    svc = TraceService()
    traces = svc.list_traces(trace_type="ingestion")

    if not traces:
        st.info("暂无摄取追踪记录，请先执行一次摄取。")
        return

    st.subheader(f"📋 追踪历史（{len(traces)}）")

    for idx, trace in enumerate(traces):
        trace_id = trace.get("trace_id", "unknown")
        started = trace.get("started_at", "—")
        total_ms = trace.get("elapsed_ms")
        total_label = f"{total_ms:.0f} ms" if total_ms is not None else "—"
        meta = trace.get("metadata", {})
        source_path = meta.get("source_path", "—")

        # Build expander title
        file_name = source_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] if source_path != "—" else "—"
        expander_title = f"📄 **{file_name}** · {total_label} · {started[:19]}"

        with st.expander(expander_title, expanded=(idx == 0)):
            timings = svc.get_stage_timings(trace)
            stages_by_name = {t["stage_name"]: t for t in timings}

            # ── 1. Overview metrics ────────────────────────────
            st.markdown("#### 📊 流水线概览")
            st.caption(f"来源文件: `{source_path}`")

            load_d = stages_by_name.get("load", {}).get("data", {})
            split_d = stages_by_name.get("split", {}).get("data", {})
            transform_d = stages_by_name.get("transform", {}).get("data", {})
            embed_d = stages_by_name.get("embed", {}).get("data", {})
            upsert_d = stages_by_name.get("upsert", {}).get("data", {})

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("文档长度", f"{load_d.get('text_length', 0):,} 字符")
            with c2:
                st.metric("分块数", split_d.get("chunk_count", 0))
            with c3:
                st.metric("图片数", load_d.get("image_count", 0))
            with c4:
                st.metric("向量数", upsert_d.get("vector_count", 0))
            with c5:
                st.metric("总耗时", total_label)

            st.divider()

            # ── 2. Stage timing waterfall ──────────────────────
            # Filter to main pipeline stages only (not sub-stages)
            main_stages = [
                t for t in timings
                if t["stage_name"] in ("load", "split", "transform", "embed", "upsert")
            ]
            if main_stages:
                st.markdown("#### ⏱️ 阶段耗时")
                chart_data = {_ingest_stage_label(t["stage_name"]): t["elapsed_ms"] for t in main_stages}
                st.bar_chart(chart_data, horizontal=True)
                st.table([
                    {
                        "阶段": _ingest_stage_label(t["stage_name"]),
                        "耗时(ms)": round(t["elapsed_ms"], 2),
                    }
                    for t in main_stages
                ])

            # ── Diagnostics ───────────────────────────────────
            _render_ingestion_diagnostics(stages_by_name, load_d, split_d, transform_d, embed_d, upsert_d)

            st.divider()

            # ── 3. Per-stage detail tabs ───────────────────────
            st.markdown("#### 🔍 阶段详情")

            tab_defs = []
            if "load" in stages_by_name:
                tab_defs.append(("📄 加载", "load"))
            if "split" in stages_by_name:
                tab_defs.append(("✂️ 切块", "split"))
            if "transform" in stages_by_name:
                tab_defs.append(("🔄 转换", "transform"))
            if "embed" in stages_by_name:
                tab_defs.append(("🔢 编码", "embed"))
            if "upsert" in stages_by_name:
                tab_defs.append(("💾 写入", "upsert"))

            if tab_defs:
                tabs = st.tabs([label for label, _ in tab_defs])
                for tab, (label, key) in zip(tabs, tab_defs):
                    with tab:
                        stage = stages_by_name[key]
                        data = stage.get("data", {})
                        elapsed = stage.get("elapsed_ms")
                        if elapsed is not None:
                            st.caption(f"⏱️ {elapsed:.1f} ms")

                        if key == "load":
                            _render_load_stage(data, trace_idx=idx)
                        elif key == "split":
                            _render_split_stage(data, trace_idx=idx)
                        elif key == "transform":
                            _render_transform_stage(data, trace_idx=idx)
                        elif key == "embed":
                            _render_embed_stage(data)
                        elif key == "upsert":
                            _render_upsert_stage(data)
            else:
                st.info("暂无阶段详情。")


def _render_ingestion_diagnostics(
    stages_by_name: Dict[str, Any],
    load_d: Dict[str, Any],
    split_d: Dict[str, Any],
    transform_d: Dict[str, Any],
    embed_d: Dict[str, Any],
    upsert_d: Dict[str, Any],
) -> None:
    """Render diagnostic hints for ingestion pipeline stages."""
    expected = ["load", "split", "transform", "embed", "upsert"]
    present = [s for s in expected if s in stages_by_name]
    missing = [s for s in expected if s not in stages_by_name]

    if missing:
        missing_labels = {"load": "📄 加载", "split": "✂️ 切块", "transform": "🔄 转换", "embed": "🔢 编码", "upsert": "💾 写入"}
        names = ", ".join(missing_labels.get(m, m) for m in missing)
        if "load" in missing:
            st.error(
                f"**流水线不完整，缺失阶段：{names}。** "
                "加载阶段失败或被跳过，文档可能损坏或格式不受支持。"
            )
        else:
            st.warning(
                f"**流水线不完整，缺失阶段：{names}。** "
                "处理过程中可能发生错误，请检查日志。"
            )

    # Stage-specific diagnostics
    if "load" in stages_by_name and load_d.get("text_length", 0) == 0:
        st.warning("**加载阶段产出为空文本。** 文档可能为纯图片或格式不受支持。")

    if "split" in stages_by_name and split_d.get("chunk_count", 0) == 0:
        st.warning("**切块阶段产出 0 个分块。** 文档文本可能过短或为空。")

    if "transform" in stages_by_name:
        refined_llm = transform_d.get("refined_by_llm", 0)
        refined_rule = transform_d.get("refined_by_rule", 0)
        if refined_llm == 0 and refined_rule == 0:
            st.info("**转换阶段：** 没有分块被精修，可能关闭了 LLM 精修或因分块过短被跳过。")

    if "embed" in stages_by_name and embed_d.get("dense_vector_count", 0) == 0:
        st.warning("**编码阶段产出 0 个向量。** Embedding API 可能调用失败，请检查 API Key 与地址。")

    if "upsert" in stages_by_name:
        vec_count = upsert_d.get("vector_count", upsert_d.get("dense_store", {}).get("count", 0))
        if vec_count == 0:
            st.warning("**写入阶段存储 0 个向量。** 数据库写入可能失败。")

    # Check for error fields in any stage data
    for stage_name in present:
        stage_data = stages_by_name[stage_name].get("data", {})
        err = stage_data.get("error", "")
        if err:
            label = stage_name.replace("_", " ").title()
            st.error(f"**{_ingest_stage_label(stage_name)}阶段错误：** {err}")


# ═══════════════════════════════════════════════════════════════
# Per-stage renderers
# ═══════════════════════════════════════════════════════════════

def _render_load_stage(data: Dict[str, Any], *, trace_idx: int = 0) -> None:
    """Render Load stage: raw document preview."""
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("文档ID", data.get("doc_id", "—")[:16])
    with c2:
        st.metric("文本长度", f"{data.get('text_length', 0):,}")
    with c3:
        st.metric("图片数", data.get("image_count", 0))

    preview = data.get("text_preview", "")
    if preview:
        st.markdown("**原始文档文本**")
        st.text_area(
            "raw_text",
            value=preview,
            height=max(120, min(len(preview) // 2, 600)),
            disabled=True,
            label_visibility="collapsed",
            key=f"load_raw_text_{trace_idx}",
        )
    else:
        st.info("该追踪中未记录文本预览。")


def _render_split_stage(data: Dict[str, Any], *, trace_idx: int = 0) -> None:
    """Render Split stage: chunk list with texts."""
    c1, c2 = st.columns(2)
    with c1:
        st.metric("分块数", data.get("chunk_count", 0))
    with c2:
        st.metric("平均长度", f"{data.get('avg_chunk_size', 0)} 字符")

    chunks = data.get("chunks", [])
    if chunks:
        st.markdown("**切块结果**")
        for i, chunk in enumerate(chunks):
            char_len = chunk.get("char_len", 0)
            chunk_id = chunk.get("chunk_id", "")
            text = chunk.get("text", "")
            header = f"📝 **分块 #{i+1}** — `{chunk_id[:20]}` — {char_len} 字符"
            with st.expander(header, expanded=(i < 2)):
                st.text_area(
                    f"split_{i}",
                    value=text,
                    height=max(100, min(len(text) // 2, 500)),
                    disabled=True,
                    label_visibility="collapsed",
                    key=f"split_{trace_idx}_{i}",
                )
    else:
        st.info("未记录分块文本，请重新执行摄取以生成新追踪。")


def _render_transform_stage(data: Dict[str, Any], *, trace_idx: int = 0) -> None:
    """Render Transform stage: before/after refinement + enrichment metadata."""
    # Summary metrics
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "精修数（LLM / 规则）",
            f"{data.get('refined_by_llm', 0)} / {data.get('refined_by_rule', 0)}",
        )
    with c2:
        st.metric(
            "增强数（LLM / 规则）",
            f"{data.get('enriched_by_llm', 0)} / {data.get('enriched_by_rule', 0)}",
        )
    with c3:
        st.metric("图片描述数", data.get("captioned_chunks", 0))

    chunks = data.get("chunks", [])
    if chunks:
        st.markdown("**分块级转换结果**")
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get("chunk_id", "")
            refined_by = chunk.get("refined_by", "")
            enriched_by = chunk.get("enriched_by", "")
            title = chunk.get("title", "")
            tags = chunk.get("tags", [])
            summary = chunk.get("summary", "")
            text_before = chunk.get("text_before", "")
            text_after = chunk.get("text_after", "")

            badge_parts = []
            if refined_by:
                badge_parts.append(f"精修:`{refined_by}`")
            if enriched_by:
                badge_parts.append(f"增强:`{enriched_by}`")
            badges = " · ".join(badge_parts)

            header = f"🔄 **分块 #{i+1}** — `{chunk_id[:20]}` — {badges}"
            with st.expander(header, expanded=(i == 0)):
                # Metadata from enrichment
                if title or tags or summary:
                    st.markdown("**增强元数据**")
                    meta_cols = st.columns(3)
                    with meta_cols[0]:
                        st.markdown(f"**标题:** {title}" if title else "_无标题_")
                    with meta_cols[1]:
                        if tags:
                            st.markdown("**标签:** " + ", ".join(f"`{t}`" for t in tags))
                        else:
                            st.markdown("_无标签_")
                    with meta_cols[2]:
                        if summary:
                            st.markdown(f"**摘要:** {summary}")

                # Before / After text comparison
                if text_before or text_after:
                    st.markdown("**文本对比**")
                    # Compute a uniform height so both sides match
                    _max_len = max(len(text_before or ""), len(text_after or ""))
                    _h = max(150, min(_max_len // 2, 600))
                    col_before, col_after = st.columns(2)
                    with col_before:
                        st.markdown("*精修前:*")
                        st.text_area(
                            f"before_{i}",
                            value=text_before if text_before else "(empty)",
                            height=_h,
                            disabled=True,
                            label_visibility="collapsed",
                            key=f"transform_before_{trace_idx}_{i}",
                        )
                    with col_after:
                        st.markdown("*精修与增强后:*")
                        st.text_area(
                            f"after_{i}",
                            value=text_after if text_after else "(empty)",
                            height=_h,
                            disabled=True,
                            label_visibility="collapsed",
                            key=f"transform_after_{trace_idx}_{i}",
                        )
    else:
        st.info("未记录分块级转换数据，请重新执行摄取以生成新追踪。")


def _render_embed_stage(data: Dict[str, Any]) -> None:
    """Render Embed stage: dual-path Dense + Sparse encoding details."""
    # ── Overview metrics ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("稠密向量数", data.get("dense_vector_count", 0))
    with c2:
        st.metric("向量维度", data.get("dense_dimension", 0))
    with c3:
        st.metric("稀疏文档数", data.get("sparse_doc_count", 0))
    with c4:
        st.metric("方法", data.get("method", "—"))

    chunks = data.get("chunks", [])
    if not chunks:
        st.info("未记录分块编码数据。")
        return

    # ── Dual-path per-chunk table ──
    st.markdown("---")
    dense_tab, sparse_tab = st.tabs(["🟦 稠密编码", "🟨 稀疏编码（BM25）"])

    with dense_tab:
        st.markdown("每个分块通过 Embedding 模型编码为**浮点向量**（如 `text-embedding-ada-002`）")
        dense_rows = []
        for i, chunk in enumerate(chunks):
            char_len = chunk.get("char_len", 0)
            dense_rows.append({
                "#": i + 1,
                "序号": i + 1,
                "分块ID": chunk.get("chunk_id", ""),
                "字符数": char_len,
                "预估Token": max(1, char_len // 3),
                "稠密维度": chunk.get("dense_dim", data.get("dense_dimension", "—")),
            })
        st.table(dense_rows)

    with sparse_tab:
        st.markdown("每个分块会生成用于 BM25 建索引的**词频统计**")
        sparse_rows = []
        for i, chunk in enumerate(chunks):
            sparse_rows.append({
                "#": i + 1,
                "序号": i + 1,
                "分块ID": chunk.get("chunk_id", ""),
                "文档长度(词项)": chunk.get("doc_length", "—"),
                "去重词项数": chunk.get("unique_terms", "—"),
            })
        st.table(sparse_rows)

        # Top terms per chunk
        for i, chunk in enumerate(chunks):
            top_terms = chunk.get("top_terms", [])
            if top_terms:
                with st.expander(f"🔤 分块 {i + 1} — 高频词", expanded=False):
                    term_rows = [{"词项": t["term"], "频次": t["freq"]} for t in top_terms]
                    st.table(term_rows)


def _render_upsert_stage(data: Dict[str, Any]) -> None:
    """Render Upsert stage: per-store details with chunk mapping."""
    dense_store = data.get("dense_store", {})
    sparse_store = data.get("sparse_store", {})
    image_store = data.get("image_store", {})

    # ── Overview metrics ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("稠密向量", dense_store.get("count", data.get("vector_count", 0)))
    with c2:
        st.metric("稀疏索引(BM25)", sparse_store.get("count", data.get("bm25_docs", 0)))
    with c3:
        st.metric("图片", image_store.get("count", data.get("images_indexed", 0)))

    # ── Dense store details ──
    if dense_store:
        with st.expander("🟦 稠密向量库（ChromaDB）", expanded=True):
            dc1, dc2 = st.columns(2)
            with dc1:
                st.markdown(f"**后端:** `{dense_store.get('backend', '—')}`")
                st.markdown(f"**集合:** `{dense_store.get('collection', '—')}`")
            with dc2:
                st.markdown(f"**路径:** `{dense_store.get('path', '—')}`")
                st.markdown(f"**向量数:** {dense_store.get('count', 0)}")

    # ── Sparse store details ──
    if sparse_store:
        with st.expander("🟨 稀疏索引（BM25）", expanded=True):
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown(f"**后端:** `{sparse_store.get('backend', '—')}`")
                st.markdown(f"**集合:** `{sparse_store.get('collection', '—')}`")
            with sc2:
                st.markdown(f"**路径:** `{sparse_store.get('path', '—')}`")
                st.markdown(f"**文档数:** {sparse_store.get('count', 0)}")

    # ── Image store details ──
    if image_store and image_store.get("count", 0) > 0:
        with st.expander(f"🖼️ 图片存储（{image_store.get('count', 0)} 张）", expanded=True):
            st.markdown(f"**后端:** `{image_store.get('backend', '—')}`")
            imgs = image_store.get("images", [])
            if imgs:
                img_rows = [
                    {
                        "图片ID": img.get("image_id", ""),
                        "页码": img.get("page", 0),
                        "文件": img.get("file_path", ""),
                        "文档哈希": img.get("doc_hash", "")[:16] + "…",
                    }
                    for img in imgs
                ]
                st.table(img_rows)

    # ── Chunk → Vector ID mapping ──
    chunk_mapping = data.get("chunk_mapping", [])
    if chunk_mapping:
        with st.expander(f"🔗 分块 → 向量映射（{len(chunk_mapping)} 条）", expanded=False):
            mapping_rows = [
                {
                    "序号": i + 1,
                    "分块ID": m.get("chunk_id", ""),
                    "向量ID": m.get("vector_id", ""),
                    "存储": m.get("store", ""),
                    "集合": m.get("collection", ""),
                }
                for i, m in enumerate(chunk_mapping)
            ]
            st.table(mapping_rows)

    # ── Fallback: legacy format with just vector_ids ──
    if not chunk_mapping and not dense_store:
        vector_ids = data.get("vector_ids", [])
        if vector_ids:
            with st.expander("向量ID", expanded=False):
                for vid in vector_ids:
                    st.code(vid, language=None)
