"""
SOP Accessibility Search — HCI Research Prototype (baseline, no AI)
Streamlit-native design. Minimal custom HTML to avoid clipping issues.
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
    initial_sidebar_state="collapsed",
)

# =========================================================
# Config
# =========================================================
LOG_FILE           = Path("search_logs.csv")
QUERY_OUTCOME_FILE = Path("query_outcomes.csv")
RESULTS_PER_PAGE   = 5
STUDY_URL          = "https://forms.gle/ce7QgjasyPBSXudm7"
SUGGESTIONS        = ["sterility","endotoxin","bioburden","environmental",
                      "sampling","monitoring","preparation","protein"]

# =========================================================
# Session state
# =========================================================
defaults = {
    "query_input":            "",
    "pending_query":          None,
    "search_history":         [],
    "feedback":               {},
    "query_outcome_feedback": {},
    "current_page":           1,
    "toast_msg":              None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg)
    st.session_state.toast_msg = None

if st.session_state.pending_query is not None:
    st.session_state.query_input   = st.session_state.pending_query
    st.session_state.pending_query  = None
    st.session_state.current_page  = 1

# =========================================================
# Helpers
# =========================================================
def set_pending(term):
    st.session_state.pending_query = term
    st.session_state.current_page  = 1

def go_home():
    st.session_state.pending_query = ""
    st.session_state.current_page  = 1

def md(html):
    st.markdown(html, unsafe_allow_html=True)

# =========================================================
# Text utils
# =========================================================
def extract_title(text):
    if not text: return "Untitled SOP"
    clean = re.sub(r"\s+", " ", text).strip()
    for pat in [r"\b1\.\s*Purpose\b", r"\b1\.\s*Objective\b",
                r"\bPurpose\b", r"\bObjective\b", r"\bScope\b"]:
        parts = re.split(pat, clean, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1 and parts[0].strip():
            t = re.sub(r"[:\-–]\s*$", "", parts[0].strip()).strip()
            return (t or clean[:80])[:140]
    return clean[:140]

def remove_title(text, title):
    if not text: return ""
    clean = re.sub(r"\s+", " ", text).strip()
    if title and clean.lower().startswith(title.lower()):
        clean = clean[len(title):].strip(" .:-")
    return clean

def make_snippet(text, n=300):
    if not text: return ""
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= n else clean[:n].rstrip() + "..."

def highlight(text, query):
    if not text or not query: return text
    pat = re.compile(re.escape(query), re.IGNORECASE)
    return pat.sub(
        lambda m: '<mark style="background:#fef08a;padding:0 2px;border-radius:3px;">'
                  + m.group(0) + '</mark>', text)

def match_info(count):
    if count >= 5: return "🟢 Strong", "#16a34a", "#f0fdf4", "5+ keyword matches"
    if count >= 2: return "🟡 Good",   "#d97706", "#fefce8", "2–4 keyword matches"
    return            "⚪ Weak",       "#6b7280", "#f9fafb", "1 keyword match"

# =========================================================
# Search & log
# =========================================================
def build_results(query, kdf, pdf):
    q = query.strip().lower()
    if not q: return pd.DataFrame()
    hits = kdf[kdf["keyword"].str.contains(q, case=False, na=False, regex=False)].copy()
    if hits.empty: return pd.DataFrame()
    merged = hits.merge(pdf, left_on=["sop_id","page"],
                        right_on=["sop_id","page_number"], how="left")
    merged["text"]   = merged["text"].fillna("").astype(str)
    merged["clean"]  = merged["text"].str.replace(r"\s+", " ", regex=True).str.strip()
    merged["kcount"] = merged["clean"].str.lower().str.count(re.escape(q))
    merged["title"]  = merged["clean"].apply(extract_title)
    merged["body"]   = merged.apply(lambda r: remove_title(r["clean"], r["title"]), axis=1)
    merged["snip"]   = merged["body"].apply(make_snippet)
    merged = merged.drop_duplicates(subset=["sop_id","page"]).copy()
    return merged.sort_values(["kcount","sop_id","page"],
                              ascending=[False,True,True]).reset_index(drop=True)

def log_search(query, rows, found="unknown"):
    if rows.empty: return
    new = rows[["sop_id","page"]].copy()
    new.insert(0,"query",query)
    new.insert(0,"timestamp",datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    new["found"] = found
    if LOG_FILE.exists():
        ex = pd.read_csv(LOG_FILE)
        pd.concat([ex,new],ignore_index=True)\
          .drop_duplicates(subset=["query","sop_id","page","found"],keep="last")\
          .to_csv(LOG_FILE,index=False,encoding="utf-8-sig")
    else:
        new.to_csv(LOG_FILE,index=False,encoding="utf-8-sig")

def log_outcome(query, found):
    row = pd.DataFrame([{"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "query":query,"found_target":"yes" if found else "no"}])
    if QUERY_OUTCOME_FILE.exists():
        ex = pd.read_csv(QUERY_OUTCOME_FILE)
        pd.concat([ex,row],ignore_index=True)\
          .drop_duplicates(subset=["query","found_target"],keep="last")\
          .to_csv(QUERY_OUTCOME_FILE,index=False,encoding="utf-8-sig")
    else:
        row.to_csv(QUERY_OUTCOME_FILE,index=False,encoding="utf-8-sig")

# =========================================================
# Data
# =========================================================
@st.cache_data
def load_data():
    kdf = pd.read_csv("keyword_index.csv")
    pdf = pd.read_csv("parsed_pages.csv")
    kdf.columns = [c.strip() for c in kdf.columns]
    pdf.columns = [c.strip() for c in pdf.columns]
    kdf["keyword"]     = kdf["keyword"].fillna("").astype(str).str.strip().str.lower()
    kdf["sop_id"]      = kdf["sop_id"].astype(str)
    kdf["page"]        = pd.to_numeric(kdf["page"], errors="coerce")
    pdf["sop_id"]      = pdf["sop_id"].astype(str)
    pdf["page_number"] = pd.to_numeric(pdf["page_number"], errors="coerce")
    pdf["text"]        = pdf["text"].fillna("").astype(str)
    return kdf, pdf

try:
    kdf, pdf = load_data()
except Exception as e:
    st.error(f"Data loading error: {e}")
    st.stop()

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.markdown("### 🕐 Search History")
    st.caption("Tap a previous query to search again.")

    if st.session_state.search_history:
        recent = list(dict.fromkeys(reversed(st.session_state.search_history)))
        for q in recent[:10]:
            if st.button("🔍 " + q, key="hist_" + q, use_container_width=True):
                set_pending(q); st.rerun()
    else:
        st.caption("No searches yet.")

    st.divider()
    st.markdown("### 📊 Session Stats")
    total_s  = len(st.session_state.search_history)
    found_c  = sum(1 for v in st.session_state.feedback.values() if v is True)
    nfound_c = sum(1 for v in st.session_state.feedback.values() if v is False)
    c1, c2, c3 = st.columns(3)
    c1.metric("Searches", total_s)
    c2.metric("✅ Found", found_c)
    c3.metric("❌ Not found", nfound_c)

    st.divider()
    st.markdown("### 📋 Study")
    st.link_button("Open Study Survey ↗", STUDY_URL, use_container_width=True)
    st.caption("Try the prototype, then share feedback.")

# =========================================================
# Header
# =========================================================
st.markdown("## 📄 SOP Accessibility Search")
st.caption(
    "Keyword search across synthetic GMP-style SOPs · HCI research prototype · "
    "No AI support layer · Results ranked by keyword frequency"
)

col_link, col_spacer = st.columns([1, 3])
with col_link:
    st.link_button("Participate in Study ↗", STUDY_URL, use_container_width=True)

st.divider()

# =========================================================
# Search bar
# =========================================================
sc, hc = st.columns([6, 1], gap="small")
with sc:
    query = st.text_input(
        "Search procedural documents",
        key="query_input",
        placeholder="e.g., sterility, bioburden, endotoxin, sampling",
    )
with hc:
    st.write("")  # vertical align
    if st.button("🏠 Home", use_container_width=True):
        go_home(); st.rerun()

# =========================================================
# Suggestions
# =========================================================
if not query:
    st.markdown("**Suggested searches**")
    r1 = st.columns(4, gap="small")
    r2 = st.columns(4, gap="small")
    for col, term in zip(r1, SUGGESTIONS[:4]):
        with col:
            if st.button(term, key="s1_"+term, use_container_width=True):
                set_pending(term); st.rerun()
    for col, term in zip(r2, SUGGESTIONS[4:]):
        with col:
            if st.button(term, key="s2_"+term, use_container_width=True):
                set_pending(term); st.rerun()

    st.divider()
    st.info(
        "🔬 **Search synthetic GMP-style SOPs**\n\n"
        "Enter a keyword above to find relevant procedures, methods, "
        "specifications, and document sections across the SOP corpus."
    )

# =========================================================
# Results
# =========================================================
if query:
    if query not in st.session_state.search_history:
        st.session_state.search_history.append(query)

    merged = build_results(query, kdf, pdf)

    if merged.empty:
        st.warning(
            f"**No results found for \"{query}\"**\n\n"
            "Try a different keyword, broaden the term, or check the spelling.\n\n"
            "> **Note:** Empty results are part of the document usability signal — "
            "if workers cannot find what they need, that is a system-level retrieval problem."
        )
    else:
        total       = len(merged)
        pages       = max(1, (total - 1) // RESULTS_PER_PAGE + 1)
        if st.session_state.current_page > pages:
            st.session_state.current_page = pages

        start   = (st.session_state.current_page - 1) * RESULTS_PER_PAGE
        end     = start + RESULTS_PER_PAGE
        page_df = merged.iloc[start:end].copy()
        unique_sops = merged["sop_id"].nunique()

        log_search(query, page_df)

        # Stats
        st.markdown(
            f"**{total}** sections found across **{unique_sops}** SOPs · "
            f"Page **{st.session_state.current_page}** of **{pages}** · "
            f"Results {start+1}–{min(end,total)} of {total}"
        )

        # Match strength legend
        md(
            "<div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center;"
            "margin-bottom:12px;'>"
            "<span style='font-size:12px;color:#6b7280;font-weight:600;'>Match strength:</span>"
            "<span style='padding:2px 8px;background:#f0fdf4;border:1px solid #86efac;"
            "border-radius:5px;font-size:12px;color:#16a34a;font-weight:600;'>"
            "🟢 Strong — 5+ matches</span>"
            "<span style='padding:2px 8px;background:#fefce8;border:1px solid #fde68a;"
            "border-radius:5px;font-size:12px;color:#d97706;font-weight:600;'>"
            "🟡 Good — 2–4 matches</span>"
            "<span style='padding:2px 8px;background:#f9fafb;border:1px solid #e5e7eb;"
            "border-radius:5px;font-size:12px;color:#6b7280;font-weight:600;'>"
            "⚪ Weak — 1 match</span>"
            "</div>"
        )

        # Pagination top
        p1, p2, p3 = st.columns([1,3,1])
        with p1:
            if st.button("← Previous", use_container_width=True,
                         disabled=st.session_state.current_page==1, key="prev_top"):
                st.session_state.current_page -= 1; st.rerun()
        with p3:
            if st.button("Next →", use_container_width=True,
                         disabled=st.session_state.current_page==pages, key="next_top"):
                st.session_state.current_page += 1; st.rerun()

        st.write("")

        # ── Result cards ──
        for idx, row in page_df.iterrows():
            label, color, bg, desc = match_info(int(row["kcount"]))
            card_key = query + "_" + str(row["sop_id"]) + "_" + str(row["page"])
            fb_val   = st.session_state.feedback.get(card_key)
            page_n   = int(row["page"]) if pd.notna(row["page"]) else "-"

            with st.container():
                # Title row
                tc, sc2 = st.columns([4, 1])
                with tc:
                    fb_icon = " ✅" if fb_val is True else (" ❌" if fb_val is False else "")
                    st.markdown(
                        f"**{row['title']}{fb_icon}**"
                    )
                    st.caption(f"{row['sop_id']} · Page {page_n}")
                with sc2:
                    md(
                        "<div style='text-align:right;padding:6px 0;'>"
                        "<span style='padding:4px 10px;background:" + bg + ";"
                        "border:1px solid " + color + "33;border-radius:7px;"
                        "font-size:12px;font-weight:700;color:" + color + ";'>"
                        + label + " · " + str(int(row["kcount"])) + " matches"
                        "</span></div>"
                    )

                # Snippet
                md(
                    "<div style='font-size:14px;color:#374151;line-height:1.75;"
                    "padding:10px 14px;background:#f9fafb;border-radius:8px;"
                    "margin:6px 0 10px;border-left:3px solid " + color + ";'>"
                    + highlight(row["snip"], query) +
                    "</div>"
                )

                # Feedback
                if fb_val is None:
                    st.caption("Was this result helpful?")
                    fb1, fb2, fb3 = st.columns([1,1,5])
                    with fb1:
                        if st.button("✅ Found", key="f_"+card_key+"_"+str(idx),
                                     use_container_width=True):
                            st.session_state.feedback[card_key] = True
                            log_search(query, page_df[page_df.index==idx], found="yes")
                            st.session_state.toast_msg = "✅ Marked as found"
                            st.rerun()
                    with fb2:
                        if st.button("❌ Not this", key="nf_"+card_key+"_"+str(idx),
                                     use_container_width=True):
                            st.session_state.feedback[card_key] = False
                            log_search(query, page_df[page_df.index==idx], found="no")
                            st.session_state.toast_msg = "❌ Marked as not found"
                            st.rerun()

                st.divider()

        # Overall feedback
        st.markdown("**Did this search find what you were looking for?**")
        qfb = st.session_state.query_outcome_feedback.get(query)
        if qfb is None:
            qa, qb, qc = st.columns([1,1,5])
            with qa:
                if st.button("✅ Yes", key="qy_"+query, use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = True
                    log_outcome(query, True)
                    st.session_state.toast_msg = "✅ Feedback saved"
                    st.rerun()
            with qb:
                if st.button("❌ No", key="qn_"+query, use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = False
                    log_outcome(query, False)
                    st.session_state.toast_msg = "❌ Feedback saved"
                    st.rerun()
        else:
            if qfb:
                st.success("Marked as a successful search.")
            else:
                st.error("Marked as an unsuccessful search.")

        # Pagination bottom
        st.write("")
        b1, b2, b3 = st.columns([1,3,1])
        with b1:
            if st.button("← Previous ", use_container_width=True,
                         disabled=st.session_state.current_page==1, key="prev_bot"):
                st.session_state.current_page -= 1; st.rerun()
        with b3:
            if st.button("Next → ", use_container_width=True,
                         disabled=st.session_state.current_page==pages, key="next_bot"):
                st.session_state.current_page += 1; st.rerun()
