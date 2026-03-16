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
# Query-param handling
# -----------------------------
if "home" in st.query_params:
    st.session_state.pending_query = ""
    st.session_state.home_reset_counter = st.session_state.get("home_reset_counter", 0) + 1
    st.query_params.clear()

# -----------------------------
# Custom CSS
# -----------------------------
st.markdown("""
<style>
    .stApp {
        background: #f6f8fb;
    }

    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 4rem;
        max-width: 1200px;
    }

    /* header */
    .hero-wrap {
        padding: 0.2rem 0 1.1rem 0;
    }

    .hero-title {
        font-size: 2.75rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #1f2937;
        margin-bottom: 0.35rem;
    }

    .hero-subtitle {
        font-size: 1.02rem;
        color: #6b7280;
        line-height: 1.65;
        margin-bottom: 0.6rem;
    }

    /* section label */
    .section-label {
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #98a2b3;
        margin-top: 1rem;
        margin-bottom: 0.8rem;
    }

    /* search box */
    div[data-testid="stTextInput"] input {
        border-radius: 16px !important;
        border: 1.5px solid #d9e0ea !important;
        background: #ffffff !important;
        min-height: 56px !important;
        padding: 0 18px !important;
        font-size: 1rem !important;
        color: #111827 !important;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05) !important;
    }

    div[data-testid="stTextInput"] input:focus {
        border-color: #7aa2ff !important;
        box-shadow: 0 0 0 4px rgba(122, 162, 255, 0.14) !important;
    }

    /* default button */
    .stButton > button {
        border-radius: 14px;
        border: 1px solid #dde3ec;
        background: #ffffff;
        color: #334155;
        min-height: 44px;
        font-weight: 500;
        box-shadow: none;
        transition: all 0.18s ease;
    }

    .stButton > button:hover {
        border-color: #bfd1ff;
        background: #f8fbff;
        color: #1d4ed8;
    }

    /* home button */
    div[data-testid="column"]:last-child .stButton > button {
        min-height: 56px;
        border-radius: 16px;
        font-size: 1rem;
        font-weight: 600;
    }

    /* suggestion chip buttons */
    .suggestion-row {
        margin-top: 0.2rem;
        margin-bottom: 0.2rem;
    }

    div[data-testid="column"] .stButton > button {
        width: 100%;
    }

    .chip-caption {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-top: 0.15rem;
        margin-bottom: 0.9rem;
    }

    /* stats bar */
    .stats-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 14px;
        background: #ffffff;
        border: 1px solid #e6ebf2;
        border-radius: 16px;
        padding: 14px 18px;
        margin-top: 0.3rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
        font-size: 0.92rem;
        color: #667085;
    }

    .stats-bar strong {
        color: #111827;
    }

    /* result card */
    .result-card {
        background: #ffffff;
        border: 1px solid #e7ecf3;
        border-radius: 18px;
        padding: 20px 22px 18px 22px;
        margin-bottom: 14px;
        box-shadow: 0 6px 24px rgba(15, 23, 42, 0.05);
    }

    .result-title {
        font-size: 1.06rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.45;
        margin-bottom: 0.55rem;
    }

    .result-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        margin-bottom: 0.9rem;
        color: #64748b;
        font-size: 0.82rem;
    }

    .result-snippet {
        font-size: 0.95rem;
        color: #475467;
        line-height: 1.8;
    }

    /* badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        white-space: nowrap;
    }

    .badge-sop {
        background: #eef4ff;
        color: #2456d3;
        border: 1px solid #d8e4ff;
    }

    .badge-page {
        background: #f8fafc;
        color: #475467;
        border: 1px solid #e2e8f0;
    }

    .badge-green {
        background: #ecfdf3;
        color: #027a48;
        border: 1px solid #d1fadf;
    }

    .badge-blue {
        background: #eff8ff;
        color: #175cd3;
        border: 1px solid #d1e9ff;
    }

    .badge-yellow {
        background: #fffaeb;
        color: #b54708;
        border: 1px solid #fedf89;
    }

    /* highlight */
    mark {
        background: #fff1a8;
        color: inherit;
        padding: 0 4px;
        border-radius: 6px;
    }

    /* empty state */
    .empty-state {
        background: #ffffff;
        border: 1px solid #e7ecf3;
        border-radius: 20px;
        padding: 44px 24px;
        text-align: center;
        color: #94a3b8;
        box-shadow: 0 6px 24px rgba(15, 23, 42, 0.04);
    }

    .empty-emoji {
        font-size: 2.2rem;
        margin-bottom: 0.6rem;
    }

    .empty-title {
        font-size: 1rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.35rem;
    }

    .empty-text {
        font-size: 0.95rem;
        line-height: 1.7;
        color: #667085;
    }

    /* anchor */
    .anchor-offset {
        position: relative;
        top: -8px;
        visibility: hidden;
    }

    /* floating nav */
    .floating-nav {
        position: fixed;
        right: 22px;
        bottom: 26px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        z-index: 9999;
    }

    .floating-nav a {
        width: 46px;
        height: 46px;
        border-radius: 999px;
        background: rgba(255,255,255,0.95);
        border: 1px solid #dbe4ee;
        box-shadow: 0 8px 24px rgba(15,23,42,0.10);
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        color: #334155;
        font-size: 1.05rem;
        font-weight: 700;
        transition: all 0.18s ease;
        backdrop-filter: blur(10px);
    }

    .floating-nav a:hover {
        background: #f8fbff;
        border-color: #c7d7fd;
        color: #1d4ed8;
        transform: translateY(-1px);
    }

    /* sidebar polish */
    section[data-testid="stSidebar"] {
        background: #fbfcfe;
        border-right: 1px solid #edf1f6;
    }

    /* feedback buttons */
    .feedback-label {
        font-size: 0.85rem;
        color: #98a2b3;
        margin-top: -0.2rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Data loading
# -----------------------------
@st.cache_data
def load_data():
    keyword_df = pd.read_csv("keyword_index.csv")
    parsed_df = pd.read_csv("parsed_pages.csv")

    keyword_df.columns = [c.strip() for c in keyword_df.columns]
    parsed_df.columns = [c.strip() for c in parsed_df.columns]

    required_keyword_cols = {"keyword", "sop_id", "page"}
    required_parsed_cols = {"sop_id", "page_number", "text"}

    if not required_keyword_cols.issubset(set(keyword_df.columns)):
        raise ValueError(
            f"keyword_index.csv must contain columns: {sorted(required_keyword_cols)}"
        )

    if not required_parsed_cols.issubset(set(parsed_df.columns)):
        raise ValueError(
            f"parsed_pages.csv must contain columns: {sorted(required_parsed_cols)}"
        )

    keyword_df["keyword"] = (
        keyword_df["keyword"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    keyword_df["sop_id"] = keyword_df["sop_id"].astype(str)
    keyword_df["page"] = pd.to_numeric(keyword_df["page"], errors="coerce")

    parsed_df["sop_id"] = parsed_df["sop_id"].astype(str)
    parsed_df["page_number"] = pd.to_numeric(parsed_df["page_number"], errors="coerce")
    parsed_df["text"] = parsed_df["text"].fillna("").astype(str)

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


def make_snippet(text: str, max_len: int = 240) -> str:
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
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)


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


def build_results(query: str, keyword_df: pd.DataFrame, parsed_df: pd.DataFrame) -> pd.DataFrame:
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

    merged["keyword_count"] = merged["clean_text"].str.lower().str.count(re.escape(query_norm))
    merged["document_title"] = merged["clean_text"].apply(extract_title)
    merged["snippet"] = merged["clean_text"].apply(make_snippet)

    merged = merged.drop_duplicates(subset=["sop_id", "page"]).copy()
    merged = merged.sort_values(
        by=["keyword_count", "sop_id", "page"],
        ascending=[False, True, True]
    ).reset_index(drop=True)

    return merged


def append_search_log(query: str, results_df: pd.DataFrame, found: str = "unknown") -> None:
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


def render_suggestion_grid(suggestions, cols_per_row=4):
    for i in range(0, len(suggestions), cols_per_row):
        row_terms = suggestions[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            with cols[j]:
                if j < len(row_terms):
                    term = row_terms[j]
                    if st.button(term, key=f"suggestion_{term}", use_container_width=True):
                        st.session_state.pending_query = term
                        st.rerun()
                else:
                    st.empty()


# -----------------------------
# Session state init
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
# Load data
# -----------------------------
try:
    keyword_df, parsed_df = load_data()
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

# -----------------------------
# Top anchor
# -----------------------------
st.markdown('<div id="top-anchor" class="anchor-offset"></div>', unsafe_allow_html=True)

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("### Search History")
    st.caption("Click any previous query to run it again")

    if st.session_state.search_history:
        recent = list(dict.fromkeys(reversed(st.session_state.search_history)))
        for q in recent[:10]:
            if st.button(f"🔍 {q}", key=f"hist_{q}"):
                st.session_state.pending_query = q
                st.rerun()
    else:
        st.caption("No searches yet")

    st.divider()

    st.markdown("### Session Stats")
    total_searches = len(st.session_state.search_history)
    found_count = sum(1 for v in st.session_state.feedback.values() if v is True)
    not_found_count = sum(1 for v in st.session_state.feedback.values() if v is False)

    st.metric("Total searches", total_searches)
    c1, c2 = st.columns(2)
    c1.metric("Found", found_count)
    c2.metric("Not found", not_found_count)

    st.divider()
    st.caption("SOP Accessibility Research Prototype · 2026")

# -----------------------------
# Main header
# -----------------------------
st.markdown(
    """
    <div class="hero-wrap">
        <div class="hero-title">📄 SOP Accessibility Search</div>
        <div class="hero-subtitle">
            Keyword-based retrieval interface for synthetic GMP-style SOP documents ·
            HCI research prototype
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('<div id="search-anchor" class="anchor-offset"></div>', unsafe_allow_html=True)

# -----------------------------
# Search bar
# -----------------------------
default_query = st.session_state.pending_query
st.session_state.pending_query = ""

search_col, home_col = st.columns([7.2, 1])

with search_col:
    query = st.text_input(
        "Search",
        value=default_query,
        placeholder="e.g., sterility, bioburden, endotoxin",
        label_visibility="collapsed",
        key=f"query_box_{st.session_state.home_reset_counter}"
    )

with home_col:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.pending_query = ""
        st.session_state.home_reset_counter += 1
        st.rerun()

# -----------------------------
# Suggestions / empty state
# -----------------------------
SUGGESTIONS = [
    "sterility",
    "endotoxin",
    "bioburden",
    "environmental",
    "sampling",
    "monitoring",
    "preparation",
    "protein"
]

if not query:
    st.markdown("<div class='section-label'>Suggested Searches</div>", unsafe_allow_html=True)
    render_suggestion_grid(SUGGESTIONS, cols_per_row=4)

    st.markdown(
        """
        <div class="empty-state" style="margin-top: 1rem;">
            <div class="empty-emoji">🔬</div>
            <div class="empty-title">Search synthetic GMP-style SOP documents</div>
            <div class="empty-text">
                Enter a keyword above to find relevant procedures, methods,
                specifications, and document sections across the SOP corpus.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------------
# Search / results
# -----------------------------
if query:
    if query not in st.session_state.search_history:
        st.session_state.search_history.append(query)

    merged = build_results(query, keyword_df, parsed_df)

    st.markdown('<div id="results-anchor" class="anchor-offset"></div>', unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Search Results</div>", unsafe_allow_html=True)

    if merged.empty:
        st.markdown(
            f"""
            <div class="empty-state">
                <div class="empty-emoji">🔍</div>
                <div class="empty-title">No results found for "{query}"</div>
                <div class="empty-text">
                    Try a different keyword, broaden the term,
                    or check the spelling.
                </div>
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
            <div class="stats-bar">
                <span>📁 <strong>{len(merged)}</strong> section(s) found</span>
                <span>🧾 across <strong>{unique_sops}</strong> SOP(s)</span>
                <span>⭐ showing top <strong>{len(top_results)}</strong> results</span>
                <span>↕ sorted by relevance</span>
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
                feedback_indicator = " ✅"
            elif feedback_val is False:
                feedback_indicator = " ❌"
            else:
                feedback_indicator = ""

            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-title">📄 {highlighted_title}{feedback_indicator}</div>
                    <div class="result-meta">
                        <span class="badge badge-sop">{row['sop_id']}</span>
                        <span class="badge badge-page">Page {int(row['page']) if pd.notna(row['page']) else '-'}</span>
                        {match_badge}
                    </div>
                    <div class="result-snippet">{highlighted_snippet}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if feedback_val is None:
                st.markdown("<div class='feedback-label'>Was this result helpful?</div>", unsafe_allow_html=True)
                fb1, fb2, fb3 = st.columns([1, 1, 6])

                with fb1:
                    if st.button("✅ Found", key=f"found_{card_key}_{idx}", use_container_width=True):
                        st.session_state.feedback[card_key] = True
                        append_search_log(
                            query,
                            top_results[top_results.index == idx],
                            found="yes"
                        )
                        st.rerun()

                with fb2:
                    if st.button("❌ Not this", key=f"notfound_{card_key}_{idx}", use_container_width=True):
                        st.session_state.feedback[card_key] = False
                        append_search_log(
                            query,
                            top_results[top_results.index == idx],
                            found="no"
                        )
                        st.rerun()

                st.write("")

        st.markdown("<div class='section-label'>Overall Search Feedback</div>", unsafe_allow_html=True)
        query_feedback = st.session_state.query_outcome_feedback.get(query)

        if query_feedback is None:
            q1, q2, q3 = st.columns([1, 1, 6])

            with q1:
                if st.button("✅ Yes", key=f"query_yes_{query}", use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = True
                    append_query_outcome(query, True)
                    st.rerun()

            with q2:
                if st.button("❌ No", key=f"query_no_{query}", use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = False
                    append_query_outcome(query, False)
                    st.rerun()
        else:
            if query_feedback is True:
                st.success("Marked as a successful search.")
            else:
                st.error("Marked as an unsuccessful search.")

# -----------------------------
# Bottom anchor
# -----------------------------
st.markdown('<div id="bottom-anchor" class="anchor-offset"></div>', unsafe_allow_html=True)

# -----------------------------
# Floating controls
# -----------------------------
st.markdown(
    """
    <div class="floating-nav">
        <a href="#top-anchor" title="Top">↑</a>
        <a href="?home=1" title="Home">⌂</a>
        <a href="#bottom-anchor" title="Bottom">↓</a>
    </div>
    """,
    unsafe_allow_html=True
)
