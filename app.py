"""
SOP Accessibility Search
HCI research prototype — AI-free baseline version.
Design unified with pac_scaffold.py and sop_search.py.

Run: streamlit run sop_accessibility.py
Requires: keyword_index.csv, parsed_pages.csv in same directory
"""

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SOP Accessibility Search",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# Config
# =========================================================
LOG_FILE          = Path("search_logs.csv")
QUERY_OUTCOME_FILE = Path("query_outcomes.csv")
RESULTS_PER_PAGE  = 5
STUDY_FORM_URL    = "https://forms.gle/ce7QgjasyPBSXudm7"

SUGGESTIONS = [
    "sterility", "endotoxin", "bioburden", "environmental",
    "sampling",  "monitoring", "preparation", "protein",
]

# =========================================================
# Session state
# =========================================================
if "query_input"            not in st.session_state: st.session_state.query_input = ""
if "search_history"         not in st.session_state: st.session_state.search_history = []
if "feedback"               not in st.session_state: st.session_state.feedback = {}
if "query_outcome_feedback" not in st.session_state: st.session_state.query_outcome_feedback = {}
if "current_page"           not in st.session_state: st.session_state.current_page = 1
if "toast_msg"              not in st.session_state: st.session_state.toast_msg = None

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg)
    st.session_state.toast_msg = None

# =========================================================
# Helpers
# =========================================================
def set_query(term: str):
    st.session_state.query_input = term
    st.session_state.current_page = 1

def go_home():
    st.session_state.query_input = ""
    st.session_state.current_page = 1

def go_prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1

def go_next_page(total_pages: int):
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1

def render(html: str):
    st.markdown(html, unsafe_allow_html=True)

def overline(t: str) -> str:
    return (f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.08em;color:#9ca3af;margin-bottom:8px;">{t}</div>')

def heading(t: str, size="17px", mb="10px") -> str:
    return (f'<div style="font-size:{size};font-weight:700;color:#111827;'
            f'line-height:1.35;margin-bottom:{mb};">{t}</div>')

def body(t: str) -> str:
    return f'<div style="font-size:14px;color:#4b5563;line-height:1.7;">{t}</div>'

CARD = ('background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;'
        'padding:22px 24px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.05);')

# =========================================================
# Text utils
# =========================================================
def extract_title(text: str) -> str:
    if not text:
        return "Untitled SOP"
    clean = re.sub(r"\s+", " ", text).strip()
    for pattern in [r"\b1\.\s*Purpose\b", r"\b1\.\s*Objective\b",
                    r"\bPurpose\b", r"\bObjective\b", r"\bScope\b"]:
        parts = re.split(pattern, clean, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1 and parts[0].strip():
            title = re.sub(r"[:\-–]\s*$", "", parts[0].strip()).strip()
            return title[:140] if title else clean[:80].strip()
    return clean[:140]

def remove_title_from_text(text: str, title: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"\s+", " ", text).strip()
    if title and clean.lower().startswith(title.lower()):
        clean = clean[len(title):].strip(" .:-")
    return clean

def make_snippet(text: str, max_len: int = 260) -> str:
    if not text:
        return ""
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= max_len else clean[:max_len].rstrip() + "..."

def highlight_keyword(text: str, query: str) -> str:
    if not text or not query:
        return text
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(
        lambda m: f'<mark style="background:#fef08a;color:#111827;border-radius:3px;padding:0 3px;">{m.group(0)}</mark>',
        text
    )

def match_label(count: int):
    if count >= 5:   return "Strong match", "#16a34a", "#f0fdf4"
    elif count >= 2: return "Good match",   "#d97706", "#fefce8"
    else:            return "Weak match",   "#6b7280", "#f9fafb"

# =========================================================
# Search logic
# =========================================================
def build_results(query: str, keyword_df: pd.DataFrame, parsed_df: pd.DataFrame) -> pd.DataFrame:
    query_norm = query.strip().lower()
    if not query_norm:
        return pd.DataFrame()
    results = keyword_df[
        keyword_df["keyword"].str.contains(query_norm, case=False, na=False, regex=False)
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
    merged["clean_text"] = merged["text"].str.replace(r"\s+", " ", regex=True).str.strip()
    merged["keyword_count"] = merged["clean_text"].str.lower().str.count(re.escape(query_norm))
    merged["document_title"] = merged["clean_text"].apply(extract_title)
    merged["body_text"] = merged.apply(
        lambda row: remove_title_from_text(row["clean_text"], row["document_title"]), axis=1
    )
    merged["snippet"] = merged["body_text"].apply(make_snippet)
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
        combined = combined.drop_duplicates(subset=["query", "sop_id", "page", "found"], keep="last")
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
        combined = combined.drop_duplicates(subset=["query", "found_target"], keep="last")
        combined.to_csv(QUERY_OUTCOME_FILE, index=False, encoding="utf-8-sig")
    else:
        outcome_df.to_csv(QUERY_OUTCOME_FILE, index=False, encoding="utf-8-sig")

# =========================================================
# Data loading
# =========================================================
@st.cache_data
def load_data():
    keyword_df = pd.read_csv("keyword_index.csv")
    parsed_df  = pd.read_csv("parsed_pages.csv")
    keyword_df.columns = [c.strip() for c in keyword_df.columns]
    parsed_df.columns  = [c.strip() for c in parsed_df.columns]
    keyword_df["keyword"] = keyword_df["keyword"].fillna("").astype(str).str.strip().str.lower()
    keyword_df["sop_id"]  = keyword_df["sop_id"].astype(str)
    keyword_df["page"]    = pd.to_numeric(keyword_df["page"], errors="coerce")
    parsed_df["sop_id"]       = parsed_df["sop_id"].astype(str)
    parsed_df["page_number"]  = pd.to_numeric(parsed_df["page_number"], errors="coerce")
    parsed_df["text"]         = parsed_df["text"].fillna("").astype(str)
    return keyword_df, parsed_df

try:
    keyword_df, parsed_df = load_data()
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

# =========================================================
# CSS — unified with pac_scaffold & sop_search
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: #f4f5f7 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stHeader"],[data-testid="stDecoration"],
[data-testid="stToolbar"],footer { display:none !important; }

.block-container { max-width:1360px !important; padding:24px 32px 40px !important; }
[data-testid="stVerticalBlock"] > div:empty { display:none !important; }

div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border:none !important; background:transparent !important;
    box-shadow:none !important; padding:0 !important;
    border-radius:0 !important; margin:0 !important;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e5e7eb !important;
}
section[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif !important;
}

/* search input */
div[data-testid="stTextInput"] input {
    font-family:'Inter',sans-serif !important;
    font-size:15px !important; color:#111827 !important;
    background:#ffffff !important;
    border:1.5px solid #d1d5db !important;
    border-radius:10px !important; padding:12px 16px !important;
    height:50px !important;
    box-shadow:0 1px 3px rgba(0,0,0,.05) !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color:#2563eb !important; outline:none !important;
    box-shadow:0 0 0 3px rgba(37,99,235,.1) !important;
}

/* buttons */
div[data-testid="stButton"] > button {
    font-family:'Inter',sans-serif !important;
    font-size:13px !important; font-weight:600 !important;
    color:#374151 !important; background:#ffffff !important;
    border:1.5px solid #d1d5db !important; border-radius:9px !important;
    padding:8px 14px !important; min-height:2.4rem !important;
    box-shadow:0 1px 2px rgba(0,0,0,.05) !important;
    transition:all .12s ease !important; width:100% !important;
}
div[data-testid="stButton"] > button:hover {
    background:#f9fafb !important; border-color:#9ca3af !important; color:#111827 !important;
}
div[data-testid="stButton"] > button:disabled {
    opacity:.45 !important; color:#9ca3af !important;
}

/* expander */
[data-testid="stExpander"] {
    border:1px solid #e5e7eb !important; border-radius:9px !important;
    background:#f9fafb !important;
}
[data-testid="stExpander"] summary {
    font-size:13px !important; font-weight:600 !important; color:#374151 !important;
}

p, li { font-size:14px !important; color:#4b5563 !important; line-height:1.7 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    render(f"""
    <div style="padding:16px 4px 8px;">
      {overline("Search History")}
      <div style="font-size:13px;color:#6b7280;margin-bottom:12px;">
        Tap a previous query to search again.
      </div>
    </div>
    """)

    if st.session_state.search_history:
        recent = list(dict.fromkeys(reversed(st.session_state.search_history)))
        for q in recent[:10]:
            if st.button(f"🔍  {q}", key=f"hist_{q}", use_container_width=True):
                set_query(q)
                st.rerun()
    else:
        render('<div style="font-size:13px;color:#9ca3af;padding:0 4px;">No searches yet.</div>')

    st.divider()

    render(f'{overline("Session Stats")}')
    total_searches  = len(st.session_state.search_history)
    found_count     = sum(1 for v in st.session_state.feedback.values() if v is True)
    not_found_count = sum(1 for v in st.session_state.feedback.values() if v is False)

    render(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;">
      <div style="padding:10px 8px;background:#f9fafb;border:1px solid #e5e7eb;
          border-radius:9px;text-align:center;">
        <div style="font-size:20px;font-weight:700;color:#111827;">{total_searches}</div>
        <div style="font-size:11px;color:#9ca3af;font-weight:600;">Searches</div>
      </div>
      <div style="padding:10px 8px;background:#f0fdf4;border:1px solid #86efac;
          border-radius:9px;text-align:center;">
        <div style="font-size:20px;font-weight:700;color:#16a34a;">{found_count}</div>
        <div style="font-size:11px;color:#16a34a;font-weight:600;">Found</div>
      </div>
      <div style="padding:10px 8px;background:#fef2f2;border:1px solid #fca5a5;
          border-radius:9px;text-align:center;">
        <div style="font-size:20px;font-weight:700;color:#dc2626;">{not_found_count}</div>
        <div style="font-size:11px;color:#dc2626;font-weight:600;">Not found</div>
      </div>
    </div>
    """)

    st.divider()
    render(f"""
    <div style="padding:0 4px;">
      {overline("Participate in Study")}
      <a href="{STUDY_FORM_URL}" target="_blank" rel="noopener noreferrer"
         style="display:block;padding:10px 14px;background:#eff6ff;border:1px solid #bfdbfe;
         border-radius:9px;color:#1d4ed8;font-size:13px;font-weight:600;
         text-decoration:none;text-align:center;margin-bottom:8px;">
        Open Study Survey ↗
      </a>
      <div style="font-size:12px;color:#9ca3af;line-height:1.55;">
        Try the prototype, then share quick feedback in the survey.
      </div>
    </div>
    """)

# =========================================================
# Header
# =========================================================
render(f"""
<div style="{CARD}margin-bottom:16px;">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;
      flex-wrap:wrap;gap:16px;">
    <div style="max-width:680px;">
      {overline("SOP Accessibility · HCI Research Prototype")}
      <div style="font-size:24px;font-weight:700;color:#111827;letter-spacing:-.02em;
          margin-bottom:6px;">
        SOP Accessibility Search
      </div>
      <div style="font-size:15px;color:#4b5563;line-height:1.7;">
        Keyword search across synthetic GMP-style SOPs.
        This is the baseline interface — no AI support layer.
        Results are ranked by keyword frequency across title, section, and body text.
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:8px;min-width:200px;">
      <a href="{STUDY_FORM_URL}" target="_blank" rel="noopener noreferrer"
         style="display:block;padding:12px 18px;background:#eff6ff;
         border:1px solid #bfdbfe;border-radius:10px;color:#1d4ed8;
         font-size:14px;font-weight:700;text-decoration:none;text-align:center;">
        Participate in Study ↗
      </a>
      <div style="font-size:12px;color:#9ca3af;text-align:center;line-height:1.5;">
        Try the prototype, then share feedback in the survey.
      </div>
    </div>
  </div>
</div>
""")

# =========================================================
# Search bar
# =========================================================
render(f'<div style="{CARD}margin-bottom:10px;">'
       f'{overline("Search")}'
       f'{heading("Find procedural documents")}'
       f'</div>')

search_col, home_col = st.columns([8, 1], gap="small")
with search_col:
    query = st.text_input(
        "Search",
        key="query_input",
        placeholder="e.g., sterility, bioburden, endotoxin, sampling",
        label_visibility="collapsed",
    )
with home_col:
    if st.button("🏠 Home", use_container_width=True):
        go_home()
        st.rerun()

# =========================================================
# Suggestions (empty state)
# =========================================================
if not query:
    render(f"""
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
        letter-spacing:.08em;color:#9ca3af;margin:12px 0 8px;">
      Suggested searches
    </div>
    """)

    row1 = st.columns(4, gap="small")
    row2 = st.columns(4, gap="small")
    for col, term in zip(row1, SUGGESTIONS[:4]):
        with col:
            if st.button(term, key=f"s1_{term}", use_container_width=True):
                set_query(term)
                st.rerun()
    for col, term in zip(row2, SUGGESTIONS[4:]):
        with col:
            if st.button(term, key=f"s2_{term}", use_container_width=True):
                set_query(term)
                st.rerun()

    render(f"""
    <div style="{CARD}margin-top:12px;background:#fafafa;border-color:#e5e7eb;text-align:center;">
      <div style="font-size:2rem;margin-bottom:10px;">🔬</div>
      {heading("Search synthetic GMP-style SOPs")}
      {body("Enter a keyword above to find relevant procedures, methods, specifications, "
            "and document sections across the SOP corpus.")}
      <div style="margin-top:16px;">
        <a href="{STUDY_FORM_URL}" target="_blank" rel="noopener noreferrer"
           style="display:inline-block;padding:10px 20px;background:#eff6ff;
           border:1px solid #bfdbfe;border-radius:9px;color:#1d4ed8;
           font-size:14px;font-weight:700;text-decoration:none;">
          Participate in Study ↗
        </a>
      </div>
    </div>
    """)

# =========================================================
# Results
# =========================================================
if query:
    if query not in st.session_state.search_history:
        st.session_state.search_history.append(query)

    merged = build_results(query, keyword_df, parsed_df)

    render(f"""
    <div style="font-size:11px;font-weight:700;text-transform:uppercase;
        letter-spacing:.08em;color:#9ca3af;margin:10px 0 8px;">
      Search Results
    </div>
    """)

    # ── No results ──
    if merged.empty:
        render(f"""
        <div style="{CARD}text-align:center;">
          <div style="font-size:2rem;margin-bottom:10px;">🔍</div>
          {heading(f'No results found for "{query}"')}
          {body("Try a different keyword, broaden the term, or check the spelling.<br><br>"
                "<strong>Note:</strong> Empty results are part of the document usability signal — "
                "if workers cannot find what they need, that is a system-level retrieval problem.")}
        </div>
        """)

    else:
        total_results = len(merged)
        total_pages   = max(1, (total_results - 1) // RESULTS_PER_PAGE + 1)
        if st.session_state.current_page > total_pages:
            st.session_state.current_page = total_pages

        start_idx    = (st.session_state.current_page - 1) * RESULTS_PER_PAGE
        end_idx      = start_idx + RESULTS_PER_PAGE
        page_results = merged.iloc[start_idx:end_idx].copy()

        append_search_log(query, page_results, found="unknown")

        unique_sops = merged["sop_id"].nunique()

        # Stats bar
        render(f"""
        <div style="{CARD}padding:14px 20px;margin-bottom:10px;">
          <div style="display:flex;flex-wrap:wrap;gap:16px;align-items:center;">
            <div>
              <span style="font-size:22px;font-weight:700;color:#111827;">{total_results}</span>
              <span style="font-size:13px;color:#9ca3af;margin-left:4px;">sections found</span>
            </div>
            <div style="width:1px;height:24px;background:#e5e7eb;"></div>
            <div>
              <span style="font-size:22px;font-weight:700;color:#111827;">{unique_sops}</span>
              <span style="font-size:13px;color:#9ca3af;margin-left:4px;">SOPs</span>
            </div>
            <div style="width:1px;height:24px;background:#e5e7eb;"></div>
            <div style="font-size:13px;color:#9ca3af;">
              page <strong style="color:#374151;">{st.session_state.current_page}</strong>
              of <strong style="color:#374151;">{total_pages}</strong>
              · sorted by relevance
            </div>
            <div style="margin-left:auto;">
              <span style="font-size:13px;color:#6b7280;">
                results {start_idx+1}–{min(end_idx, total_results)} of {total_results}
              </span>
            </div>
          </div>
        </div>
        """)

        # Pagination
        nav_l, nav_m, nav_r = st.columns([1, 3, 1], gap="small")
        with nav_l:
            if st.button("← Previous", use_container_width=True,
                         disabled=st.session_state.current_page == 1):
                go_prev_page()
                st.rerun()
        with nav_r:
            if st.button("Next →", use_container_width=True,
                         disabled=st.session_state.current_page == total_pages):
                go_next_page(total_pages)
                st.rerun()

        render('<div style="height:4px;"></div>')

        # ── Result cards ──
        for idx, row in page_results.iterrows():
            label, score_color, score_bg = match_label(int(row["keyword_count"]))
            card_key = f"{query}_{row['sop_id']}_{row['page']}"
            feedback_val = st.session_state.feedback.get(card_key)

            feedback_tag = ""
            if feedback_val is True:
                feedback_tag = ' <span style="font-size:12px;color:#16a34a;font-weight:700;">✅ Found</span>'
            elif feedback_val is False:
                feedback_tag = ' <span style="font-size:12px;color:#dc2626;font-weight:700;">❌ Not this</span>'

            highlighted_title   = highlight_keyword(row["document_title"], query)
            highlighted_snippet = highlight_keyword(row["snippet"], query)

            render(f"""
            <div style="{CARD}border-left:4px solid {score_color};">
              <div style="display:flex;align-items:flex-start;justify-content:space-between;
                  flex-wrap:wrap;gap:12px;margin-bottom:12px;">
                <div style="flex:1;">
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="font-size:12px;font-weight:700;font-family:'IBM Plex Mono',monospace;
                        color:#9ca3af;letter-spacing:.04em;">{row['sop_id']}</span>
                    <span style="font-size:12px;color:#9ca3af;">·</span>
                    <span style="font-size:12px;color:#9ca3af;">Page {int(row['page']) if pd.notna(row['page']) else '-'}</span>
                    {feedback_tag}
                  </div>
                  <div style="font-size:17px;font-weight:700;color:#111827;line-height:1.4;">
                    {highlighted_title}
                  </div>
                </div>
                <div style="text-align:center;padding:8px 16px;background:{score_bg};
                    border:1px solid {score_color}33;border-radius:9px;flex-shrink:0;">
                  <div style="font-size:16px;font-weight:700;color:{score_color};">{label}</div>
                  <div style="font-size:11px;font-weight:600;color:{score_color};
                      text-transform:uppercase;letter-spacing:.05em;">
                    {int(row['keyword_count'])} match{"es" if row['keyword_count'] != 1 else ""}
                  </div>
                </div>
              </div>
              <div style="font-size:14px;color:#374151;line-height:1.75;padding:12px 14px;
                  background:#f9fafb;border-radius:8px;">
                {highlighted_snippet}
              </div>
            </div>
            """)

            # Feedback buttons
            if feedback_val is None:
                render(f'<div style="font-size:13px;color:#9ca3af;margin-bottom:6px;">'
                       f'Was this result helpful?</div>')
                fb1, fb2, fb3 = st.columns([1, 1, 6], gap="small")
                with fb1:
                    if st.button("✅ Found", key=f"found_{card_key}_{idx}", use_container_width=True):
                        st.session_state.feedback[card_key] = True
                        append_search_log(query, page_results[page_results.index == idx], found="yes")
                        st.session_state.toast_msg = "✅ Marked as found"
                        st.rerun()
                with fb2:
                    if st.button("❌ Not this", key=f"notfound_{card_key}_{idx}", use_container_width=True):
                        st.session_state.feedback[card_key] = False
                        append_search_log(query, page_results[page_results.index == idx], found="no")
                        st.session_state.toast_msg = "❌ Marked as not found"
                        st.rerun()

            render('<div style="height:4px;"></div>')

        # ── Overall search feedback ──
        render(f"""
        <div style="{CARD}margin-top:4px;">
          {overline("Overall Search Feedback")}
          {heading("Did this search find what you were looking for?", size="15px", mb="12px")}
        """)

        query_feedback = st.session_state.query_outcome_feedback.get(query)
        if query_feedback is None:
            q1, q2, q3 = st.columns([1, 1, 6], gap="small")
            with q1:
                if st.button("✅ Yes", key=f"qyes_{query}", use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = True
                    append_query_outcome(query, True)
                    st.session_state.toast_msg = "✅ Feedback saved"
                    st.rerun()
            with q2:
                if st.button("❌ No", key=f"qno_{query}", use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = False
                    append_query_outcome(query, False)
                    st.session_state.toast_msg = "❌ Feedback saved"
                    st.rerun()
        else:
            if query_feedback:
                render('<div style="font-size:14px;color:#16a34a;font-weight:600;">'
                       '✅ Marked as a successful search.</div>')
            else:
                render('<div style="font-size:14px;color:#dc2626;font-weight:600;">'
                       '❌ Marked as an unsuccessful search.</div>')

        render('</div>')

        # Bottom pagination
        render('<div style="height:8px;"></div>')
        bn_l, bn_m, bn_r = st.columns([1, 3, 1], gap="small")
        with bn_l:
            if st.button("← Previous ", key="prev_bot", use_container_width=True,
                         disabled=st.session_state.current_page == 1):
                go_prev_page()
                st.rerun()
        with bn_r:
            if st.button("Next → ", key="next_bot", use_container_width=True,
                         disabled=st.session_state.current_page == total_pages):
                go_next_page(total_pages)
                st.rerun()
