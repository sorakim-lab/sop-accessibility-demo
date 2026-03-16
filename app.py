import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SOP Accessibility Search",
    page_icon="📄",
    layout="wide"
)

LOG_FILE = Path("search_logs.csv")
QUERY_OUTCOME_FILE = Path("query_outcomes.csv")

# -----------------------------
# Home query-param handling
# -----------------------------
if "home" in st.query_params:
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = ""
    if "home_reset_counter" not in st.session_state:
        st.session_state.home_reset_counter = 0

    st.session_state.pending_query = ""
    st.session_state.home_reset_counter += 1
    st.query_params.clear()

# -----------------------------
# Custom CSS
# -----------------------------
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp {
        background-color: #f7f8fc;
    }

    /* 검색창 스타일 */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 1.5px solid #d0d5dd;
        padding: 10px 16px;
        font-size: 1rem;
        background: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: border-color 0.2s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4f8ef7;
        box-shadow: 0 0 0 3px rgba(79,142,247,0.12);
    }

    /* 결과 카드 */
    .result-card {
        background: #ffffff;
        border: 1px solid #e4e8ef;
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: 0 2px 10px rgba(15,23,42,0.05);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .result-card:hover {
        box-shadow: 0 6px 24px rgba(15,23,42,0.10);
        transform: translateY(-2px);
    }

    /* 제목 */
    .result-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 6px;
        line-height: 1.4;
    }

    /* 메타 (SOP ID, page) */
    .result-meta {
        font-size: 0.82rem;
        color: #6b7280;
        margin-bottom: 10px;
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
    }

    /* 뱃지 */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .badge-blue {
        background: #eff6ff;
        color: #3b82f6;
        border: 1px solid #bfdbfe;
    }
    .badge-green {
        background: #f0fdf4;
        color: #16a34a;
        border: 1px solid #bbf7d0;
    }
    .badge-yellow {
        background: #fefce8;
        color: #ca8a04;
        border: 1px solid #fde68a;
    }

    /* 스니펫 */
    .result-snippet {
        font-size: 0.93rem;
        line-height: 1.75;
        color: #374151;
    }

    /* 하이라이트 */
    mark {
        background-color: #fff3a3;
        padding: 1px 3px;
        border-radius: 3px;
    }

    /* 섹션 헤더 */
    .section-header {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9ca3af;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #e5e7eb;
    }

    /* 사이드바 히스토리 버튼 */
    .stButton > button {
        border-radius: 10px;
        font-size: 0.85rem;
        border: 1px solid #e5e7eb;
        background: #ffffff;
        color: #374151;
        transition: all 0.18s ease;
        width: 100%;
        text-align: left;
        padding: 6px 12px;
    }
    .stButton > button:hover {
        background: #f0f4ff;
        border-color: #c7d7fd;
        color: #1d4ed8;
    }

    /* suggestion pill */
    div[data-testid="column"] .stButton > button {
        border-radius: 999px;
        padding: 5px 14px;
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        color: #475569;
        font-size: 0.82rem;
        width: auto;
    }
    div[data-testid="column"] .stButton > button:hover {
        background: #e8f0fe;
        border-color: #93c5fd;
        color: #1d4ed8;
    }

    /* empty state */
    .empty-state {
        text-align: center;
        padding: 48px 24px;
        color: #9ca3af;
    }
    .empty-state .emoji {
        font-size: 2.5rem;
        margin-bottom: 12px;
    }
    .empty-state p {
        font-size: 0.95rem;
        margin: 4px 0;
    }

    /* stats bar */
    .stats-bar {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 16px;
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 16px;
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
    }

    /* floating nav */
    .floating-nav {
        position: fixed;
        right: 22px;
        bottom: 28px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        z-index: 9999;
    }
    .floating-nav a {
        width: 44px;
        height: 44px;
        border-radius: 999px;
        background: #ffffff;
        border: 1px solid #dbe2ea;
        box-shadow: 0 4px 14px rgba(15,23,42,0.10);
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        color: #334155;
        font-size: 1.1rem;
        font-weight: 600;
        transition: all 0.18s ease;
    }
    .floating-nav a:hover {
        background: #f0f4ff;
        border-color: #bfd2ff;
        color: #1d4ed8;
        transform: translateY(-1px);
    }

    /* anchor spacing */
    .anchor-offset {
        position: relative;
        top: -10px;
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Data loading
# -----------------------------
def load_data():
    keyword_df = pd.read_csv("keyword_index.csv")
    parsed_df = pd.read_csv("parsed_pages.csv")

    keyword_df["keyword"] = (
        keyword_df["keyword"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    parsed_df["text"] = (
        parsed_df["text"]
        .fillna("")
        .astype(str)
    )
    return keyword_df, parsed_df


# -----------------------------
# Utility functions
# -----------------------------
def extract_title(text: str) -> str:
    if not text:
        return "Untitled SOP"
    match = re.split(r"\b1\.\s*Purpose\b", text, maxsplit=1, flags=re.IGNORECASE)
    title = match[0].strip() if match else text.strip()
    if not title:
        title = text[:60].strip()
    return title


def make_snippet(text: str, max_len: int = 220) -> str:
    if not text:
        return ""
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_len:
        return clean
    return clean[:max_len].rstrip() + "..."


def highlight_keyword(text: str, query: str) -> str:
    if not text or not query:
        return text
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(
        lambda m: f"<mark>{m.group(0)}</mark>",
        text
    )


def get_match_badge(count: int) -> str:
    if count >= 5:
        cls = "badge-green"
        label = f"🔍 {count} matches"
    elif count >= 2:
        cls = "badge-blue"
        label = f"🔍 {count} matches"
    else:
        cls = "badge-yellow"
        label = f"🔍 {count} match"
    return f"<span class='badge {cls}'>{label}</span>"


def build_results(
    query: str,
    keyword_df: pd.DataFrame,
    parsed_df: pd.DataFrame
) -> pd.DataFrame:
    query_norm = query.strip().lower()
    if not query_norm:
        return pd.DataFrame()

    results = keyword_df[
        keyword_df["keyword"].str.contains(
            query_norm, case=False, na=False, regex=False
        )
    ].copy()

    if results.empty:
        return pd.DataFrame()

    merged = results.merge(
        parsed_df,
        left_on=["sop_id", "page"],
        right_on=["sop_id", "page_number"],
        how="left"
    )

    merged["text"] = merged["text"].fillna("").astype(str)
    merged["clean_text"] = (
        merged["text"]
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    merged["keyword_count"] = merged["clean_text"].str.lower().str.count(
        re.escape(query_norm)
    )

    merged["document_title"] = merged["clean_text"].apply(extract_title)
    merged["snippet"] = merged["clean_text"].apply(make_snippet)

    merged = merged.drop_duplicates(subset=["sop_id", "page"]).copy()
    merged = merged.sort_values(
        by="keyword_count", ascending=False
    ).reset_index(drop=True)

    return merged


def append_search_log(
    query: str,
    results_df: pd.DataFrame,
    found: str = "unknown"
) -> None:
    if results_df.empty:
        return

    new_logs = results_df[["sop_id", "page"]].copy()
    new_logs.insert(0, "query", query)
    new_logs.insert(0, "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    new_logs["found"] = found

    if LOG_FILE.exists():
        existing = pd.read_csv(LOG_FILE)
        combined = pd.concat([existing, new_logs], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["query", "sop_id", "page", "found"],
            keep="last"
        )
        combined.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
    else:
        new_logs.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")


def append_query_outcome(query: str, found: bool) -> None:
    outcome_df = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query,
        "found_target": "yes" if found else "no"
    }])

    if QUERY_OUTCOME_FILE.exists():
        existing = pd.read_csv(QUERY_OUTCOME_FILE)
        combined = pd.concat([existing, outcome_df], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["query", "found_target"],
            keep="last"
        )
        combined.to_csv(QUERY_OUTCOME_FILE, index=False, encoding="utf-8-sig")
    else:
        outcome_df.to_csv(QUERY_OUTCOME_FILE, index=False, encoding="utf-8-sig")


# -----------------------------
# Load data
# -----------------------------
keyword_df, parsed_df = load_data()

# -----------------------------
# Session state
# -----------------------------
if "search_history" not in st.session_state:
    st.session_state.search_history = []

if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""

if "feedback" not in st.session_state:
    st.session_state.feedback = {}

if "query_outcome_feedback" not in st.session_state:
    st.session_state.query_outcome_feedback = {}

if "home_reset_counter" not in st.session_state:
    st.session_state.home_reset_counter = 0

# -----------------------------
# Floating nav anchors
# -----------------------------
st.markdown('<div id="top-anchor" class="anchor-offset"></div>', unsafe_allow_html=True)

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("### 📋 Search History")
    st.caption("Click to search again")

    if st.session_state.search_history:
        recent = list(dict.fromkeys(reversed(st.session_state.search_history)))
        for q in recent[:10]:
            if st.button(f"🔍 {q}", key=f"hist_{q}"):
                st.session_state.pending_query = q
                st.rerun()
    else:
        st.markdown(
            "<div style='color:#aaa; font-size:0.85rem;'>No searches yet.</div>",
            unsafe_allow_html=True
        )

    st.divider()

    st.markdown("### 📊 Session Stats")
    total_searches = len(st.session_state.search_history)
    found_count = sum(1 for v in st.session_state.feedback.values() if v is True)
    not_found_count = sum(1 for v in st.session_state.feedback.values() if v is False)

    st.metric("Total searches", total_searches)
    col1, col2 = st.columns(2)
    col1.metric("✅ Found", found_count)
    col2.metric("❌ Not found", not_found_count)

    st.divider()
    st.caption("SOP Accessibility Research Prototype · 2026")

# -----------------------------
# Main UI
# -----------------------------
st.markdown("## 📄 SOP Accessibility Search")
st.caption(
    "Keyword-based retrieval interface for synthetic GMP-style SOP documents · "
    "HCI research prototype"
)

st.markdown('<div id="search-anchor" class="anchor-offset"></div>', unsafe_allow_html=True)

default_query = st.session_state.pending_query
st.session_state.pending_query = ""

top_col1, top_col2 = st.columns([6, 1])

with top_col1:
    query = st.text_input(
        "Enter keyword",
        value=default_query,
        placeholder="e.g., sterility, bioburden, endotoxin",
        label_visibility="collapsed",
        key=f"query_box_{st.session_state.home_reset_counter}"
    )

with top_col2:
    if st.button("🏠 Home"):
        st.session_state.pending_query = ""
        st.session_state.home_reset_counter += 1
        st.rerun()

# -----------------------------
# Suggested queries (empty state)
# -----------------------------
SUGGESTIONS = [
    "sterility", "endotoxin", "bioburden",
    "environmental", "sampling", "monitoring",
    "preparation", "protein"
]

if not query:
    st.markdown(
        "<div class='section-header'>💡 Suggested searches</div>",
        unsafe_allow_html=True
    )
    cols = st.columns(len(SUGGESTIONS))
    for col, s in zip(cols, SUGGESTIONS):
        if col.button(s, key=f"sug_{s}"):
            st.session_state.pending_query = s
            st.rerun()

    st.markdown(
        """
        <div class='empty-state'>
            <div class='emoji'>🔬</div>
            <p><strong>Search GMP-style SOP documents</strong></p>
            <p>Enter a keyword above to find relevant procedures,<br>
            specifications, and methods across the SOP corpus.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------
# Search & results
# -----------------------------
if query:
    if query not in st.session_state.search_history:
        st.session_state.search_history.append(query)

    merged = build_results(query, keyword_df, parsed_df)

    st.markdown(
        "<div id='results-anchor' class='anchor-offset'></div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='section-header'>Search Results</div>",
        unsafe_allow_html=True
    )

    if merged.empty:
        st.markdown(
            f"""
            <div class='empty-state'>
                <div class='emoji'>🔍</div>
                <p><strong>No results found for "{query}"</strong></p>
                <p>Try a different keyword or check the spelling.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        top_results = merged.head(10).copy()
        append_search_log(query, top_results, found="unknown")

        unique_sops = top_results["sop_id"].nunique()
        st.markdown(
            f"""
            <div class='stats-bar'>
                📁 <strong>{len(merged)}</strong> section(s) found across
                <strong>{unique_sops}</strong> SOP(s) ·
                Showing top <strong>{len(top_results)}</strong> results ·
                Sorted by relevance
            </div>
            """,
            unsafe_allow_html=True
        )

        for idx, row in top_results.iterrows():
            highlighted_title = highlight_keyword(row["document_title"], query)
            highlighted_snippet = highlight_keyword(row["snippet"], query)
            match_badge = get_match_badge(int(row["keyword_count"]))
            card_key = f"{query}_{row['sop_id']}_{row['page']}"

            feedback_val = st.session_state.feedback.get(card_key)
            if feedback_val is True:
                feedback_indicator = "✅"
            elif feedback_val is False:
                feedback_indicator = "❌"
            else:
                feedback_indicator = ""

            st.markdown(
                f"""
                <div class='result-card'>
                    <div class='result-title'>
                        📄 {highlighted_title} {feedback_indicator}
                    </div>
                    <div class='result-meta'>
                        <span class='badge badge-blue'>{row['sop_id']}</span>
                        <span>Page {row['page']}</span>
                        {match_badge}
                    </div>
                    <div class='result-snippet'>{highlighted_snippet}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if feedback_val is None:
                fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 6])
                with fb_col1:
                    if st.button("✅ Found", key=f"found_{card_key}_{idx}"):
                        st.session_state.feedback[card_key] = True
                        append_search_log(
                            query,
                            top_results[top_results.index == idx],
                            found="yes"
                        )
                        st.rerun()
                with fb_col2:
                    if st.button("❌ Not this", key=f"notfound_{card_key}_{idx}"):
                        st.session_state.feedback[card_key] = False
                        append_search_log(
                            query,
                            top_results[top_results.index == idx],
                            found="no"
                        )
                        st.rerun()

        st.markdown(
            "<div class='section-header'>Did you find what you were looking for?</div>",
            unsafe_allow_html=True
        )

        query_feedback = st.session_state.query_outcome_feedback.get(query)

        if query_feedback is None:
            q_col1, q_col2, q_col3 = st.columns([1, 1, 6])

            with q_col1:
                if st.button("✅ Yes", key=f"query_yes_{query}"):
                    st.session_state.query_outcome_feedback[query] = True
                    append_query_outcome(query, True)
                    st.rerun()

            with q_col2:
                if st.button("❌ No", key=f"query_no_{query}"):
                    st.session_state.query_outcome_feedback[query] = False
                    append_query_outcome(query, False)
                    st.rerun()
        else:
            if query_feedback is True:
                st.success("Marked as successful search.")
            else:
                st.error("Marked as unsuccessful search.")

st.markdown('<div id="bottom-anchor" class="anchor-offset"></div>', unsafe_allow_html=True)

# -----------------------------
# Floating scroll controls
# -----------------------------
st.markdown(
    """
    <div class="floating-nav">
        <a href="#top-anchor" title="Page up">↑</a>
        <a href="?home=1" title="Go home">⌂</a>
        <a href="#bottom-anchor" title="Page down">↓</a>
    </div>
    """,
    unsafe_allow_html=True
)