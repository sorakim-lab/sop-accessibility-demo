"""
SOP Accessibility Search — HCI Research Prototype (baseline, no AI)
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

# toast + pending query — process before any render
if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg)
    st.session_state.toast_msg = None

if st.session_state.pending_query is not None:
    st.session_state.query_input  = st.session_state.pending_query
    st.session_state.pending_query = None
    st.session_state.current_page = 1

# =========================================================
# Helpers
# =========================================================
def go_home():
    st.session_state.pending_query = ""
    st.session_state.current_page  = 1

def set_pending(term):
    st.session_state.pending_query = term
    st.session_state.current_page  = 1

def md(html):
    st.markdown(html, unsafe_allow_html=True)

# =========================================================
# Text utils
# =========================================================
def extract_title(text):
    if not text:
        return "Untitled SOP"
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

def snippet(text, n=280):
    if not text: return ""
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= n else clean[:n].rstrip() + "..."

def hl(text, query):
    if not text or not query: return text
    pat = re.compile(re.escape(query), re.IGNORECASE)
    return pat.sub(
        lambda m: '<mark style="background:#fef08a;color:#111827;'
                  'border-radius:3px;padding:0 3px;">' + m.group(0) + '</mark>',
        text
    )

def match_info(count):
    if count >= 5: return "Strong match", "#16a34a", "#f0fdf4"
    if count >= 2: return "Good match",   "#d97706", "#fefce8"
    return            "Weak match",       "#6b7280", "#f9fafb"

# =========================================================
# Search
# =========================================================
def build_results(query, kdf, pdf):
    q = query.strip().lower()
    if not q: return pd.DataFrame()
    hits = kdf[kdf["keyword"].str.contains(q, case=False, na=False, regex=False)].copy()
    if hits.empty: return pd.DataFrame()
    merged = hits.merge(pdf, left_on=["sop_id","page"],
                        right_on=["sop_id","page_number"], how="left")
    merged["text"]       = merged["text"].fillna("").astype(str)
    merged["clean"]      = merged["text"].str.replace(r"\s+", " ", regex=True).str.strip()
    merged["kcount"]     = merged["clean"].str.lower().str.count(re.escape(q))
    merged["title"]      = merged["clean"].apply(extract_title)
    merged["body"]       = merged.apply(lambda r: remove_title(r["clean"], r["title"]), axis=1)
    merged["snip"]       = merged["body"].apply(snippet)
    merged = merged.drop_duplicates(subset=["sop_id","page"]).copy()
    merged = merged.sort_values(["kcount","sop_id","page"],
                                ascending=[False,True,True]).reset_index(drop=True)
    return merged

def log_search(query, rows, found="unknown"):
    if rows.empty: return
    new = rows[["sop_id","page"]].copy()
    new.insert(0,"query",query)
    new.insert(0,"timestamp",datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    new["found"] = found
    if LOG_FILE.exists():
        ex = pd.read_csv(LOG_FILE)
        c  = pd.concat([ex,new],ignore_index=True)
        c.drop_duplicates(subset=["query","sop_id","page","found"],keep="last")\
         .to_csv(LOG_FILE,index=False,encoding="utf-8-sig")
    else:
        new.to_csv(LOG_FILE,index=False,encoding="utf-8-sig")

def log_outcome(query, found):
    row = pd.DataFrame([{"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "query":query,"found_target":"yes" if found else "no"}])
    if QUERY_OUTCOME_FILE.exists():
        ex = pd.read_csv(QUERY_OUTCOME_FILE)
        c  = pd.concat([ex,row],ignore_index=True)
        c.drop_duplicates(subset=["query","found_target"],keep="last")\
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
# CSS
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: #f4f5f7 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stHeader"],[data-testid="stDecoration"],
[data-testid="stToolbar"],footer { display:none !important; }

.block-container {
    max-width: 1300px !important;
    padding: 20px 20px 40px 20px !important;
}
[data-testid="stVerticalBlock"] > div:empty { display:none !important; }

/* strip container chrome */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border:none !important; background:transparent !important;
    box-shadow:none !important; padding:0 !important;
    border-radius:0 !important; margin:0 !important;
}

/* sidebar */
section[data-testid="stSidebar"] {
    background:#ffffff !important;
    border-right:1px solid #e5e7eb !important;
}

/* search input */
div[data-testid="stTextInput"] input {
    font-family:'Inter',sans-serif !important; font-size:15px !important;
    color:#111827 !important; background:#ffffff !important;
    border:1.5px solid #d1d5db !important; border-radius:10px !important;
    padding:12px 16px !important; height:50px !important;
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
    opacity:.4 !important; color:#9ca3af !important;
}

p, li { font-size:14px !important; color:#4b5563 !important; line-height:1.7 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# Card builder — no f-string nesting, no conflicts
# =========================================================
def card(inner, extra_style=""):
    base = ("background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;"
            "padding:20px 22px;margin-bottom:10px;"
            "box-shadow:0 1px 3px rgba(0,0,0,.05);")
    return "<div style='" + base + extra_style + "'>" + inner + "</div>"

def overline(t):
    return ("<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:.08em;color:#9ca3af;margin-bottom:8px;'>" + t + "</div>")

def h2(t, size="17px", mb="8px"):
    return ("<div style='font-size:" + size + ";font-weight:700;color:#111827;"
            "line-height:1.35;margin-bottom:" + mb + ";'>" + t + "</div>")

def para(t):
    return "<div style='font-size:14px;color:#4b5563;line-height:1.7;'>" + t + "</div>"

def slabel(t, mt="12px"):
    return ("<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:.07em;color:#9ca3af;margin:" + mt + " 0 6px;'>" + t + "</div>")

def result_card(sop_id, page_num, title_html, snip_html,
                label, score_color, score_bg, kcount, feedback_tag):
    match_suf = "es" if kcount != 1 else ""
    return (
        "<div style='background:#ffffff;border:1px solid #e5e7eb;"
        "border-left:4px solid " + score_color + ";border-radius:12px;"
        "padding:20px 22px;margin-bottom:10px;"
        "box-shadow:0 1px 3px rgba(0,0,0,.05);'>"

        "<div style='display:flex;align-items:flex-start;"
        "justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:12px;'>"

        "<div style='flex:1;min-width:0;'>"
        "<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;"
        "flex-wrap:wrap;'>"
        "<span style='font-size:12px;font-weight:700;color:#9ca3af;"
        "letter-spacing:.04em;font-family:monospace;'>" + str(sop_id) + "</span>"
        "<span style='font-size:12px;color:#9ca3af;'>·</span>"
        "<span style='font-size:12px;color:#9ca3af;'>Page " + str(page_num) + "</span>"
        + feedback_tag +
        "</div>"
        "<div style='font-size:17px;font-weight:700;color:#111827;line-height:1.4;"
        "word-break:break-word;'>" + title_html + "</div>"
        "</div>"

        "<div style='text-align:center;padding:8px 16px;background:" + score_bg + ";"
        "border:1px solid " + score_color + ";border-radius:9px;flex-shrink:0;'>"
        "<div style='font-size:15px;font-weight:700;color:" + score_color + ";'>"
        + label + "</div>"
        "<div style='font-size:11px;font-weight:600;color:" + score_color + ";"
        "text-transform:uppercase;letter-spacing:.05em;'>"
        + str(kcount) + " match" + match_suf + "</div>"
        "</div>"

        "</div>"

        "<div style='font-size:14px;color:#374151;line-height:1.75;"
        "padding:12px 14px;background:#f9fafb;border-radius:8px;"
        "word-break:break-word;'>" + snip_html + "</div>"

        "</div>"
    )

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    md(card(
        overline("Search History") +
        "<div style='font-size:13px;color:#6b7280;margin-bottom:10px;'>"
        "Tap a previous query to search again.</div>"
    ))

    if st.session_state.search_history:
        recent = list(dict.fromkeys(reversed(st.session_state.search_history)))
        for q in recent[:10]:
            if st.button("🔍  " + q, key="hist_" + q, use_container_width=True):
                set_pending(q)
                st.rerun()
    else:
        md("<div style='font-size:13px;color:#9ca3af;padding:4px;'>No searches yet.</div>")

    st.divider()

    total_s  = len(st.session_state.search_history)
    found_c  = sum(1 for v in st.session_state.feedback.values() if v is True)
    nfound_c = sum(1 for v in st.session_state.feedback.values() if v is False)

    md(overline("Session Stats") +
       "<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;'>"
       "<div style='padding:10px 8px;background:#f9fafb;border:1px solid #e5e7eb;"
       "border-radius:9px;text-align:center;'>"
       "<div style='font-size:20px;font-weight:700;color:#111827;'>" + str(total_s) + "</div>"
       "<div style='font-size:11px;color:#9ca3af;font-weight:600;'>Searches</div></div>"
       "<div style='padding:10px 8px;background:#f0fdf4;border:1px solid #86efac;"
       "border-radius:9px;text-align:center;'>"
       "<div style='font-size:20px;font-weight:700;color:#16a34a;'>" + str(found_c) + "</div>"
       "<div style='font-size:11px;color:#16a34a;font-weight:600;'>Found</div></div>"
       "<div style='padding:10px 8px;background:#fef2f2;border:1px solid #fca5a5;"
       "border-radius:9px;text-align:center;'>"
       "<div style='font-size:20px;font-weight:700;color:#dc2626;'>" + str(nfound_c) + "</div>"
       "<div style='font-size:11px;color:#dc2626;font-weight:600;'>Not found</div></div>"
       "</div>")

    st.divider()
    md(overline("Participate in Study") +
       "<a href='" + STUDY_URL + "' target='_blank' rel='noopener noreferrer'"
       " style='display:block;padding:10px 14px;background:#eff6ff;"
       "border:1px solid #bfdbfe;border-radius:9px;color:#1d4ed8;"
       "font-size:13px;font-weight:600;text-decoration:none;text-align:center;"
       "margin-bottom:8px;'>Open Study Survey ↗</a>"
       "<div style='font-size:12px;color:#9ca3af;line-height:1.55;'>"
       "Try the prototype, then share quick feedback in the survey.</div>")

# =========================================================
# Header
# =========================================================
inner_header = (
    overline("SOP Accessibility · HCI Research Prototype") +
    h2("SOP Accessibility Search", size="24px", mb="6px") +
    para("Keyword search across synthetic GMP-style SOPs. "
         "This is the baseline interface — no AI support layer. "
         "Results are ranked by keyword frequency across title, section, and body text.") +
    "<div style='margin-top:14px;'>"
    "<a href='" + STUDY_URL + "' target='_blank' rel='noopener noreferrer'"
    " style='display:inline-block;padding:10px 18px;background:#eff6ff;"
    "border:1px solid #bfdbfe;border-radius:10px;color:#1d4ed8;"
    "font-size:14px;font-weight:700;text-decoration:none;margin-right:10px;'>"
    "Participate in Study ↗</a>"
    "<span style='font-size:12px;color:#9ca3af;'>"
    "Try the prototype, then share feedback in the survey.</span>"
    "</div>"
)
md(card(inner_header, "margin-bottom:14px;"))

# =========================================================
# Search bar
# =========================================================
md(card(overline("Search") + h2("Find procedural documents"), "margin-bottom:10px;"))

sc, hc = st.columns([8, 1], gap="small")
with sc:
    query = st.text_input(
        "Search", key="query_input",
        placeholder="e.g., sterility, bioburden, endotoxin, sampling",
        label_visibility="collapsed",
    )
with hc:
    if st.button("🏠 Home", use_container_width=True):
        go_home()
        st.rerun()

# =========================================================
# Empty state — suggestions
# =========================================================
if not query:
    md("<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
       "letter-spacing:.08em;color:#9ca3af;margin:12px 0 8px;'>Suggested searches</div>")

    r1 = st.columns(4, gap="small")
    r2 = st.columns(4, gap="small")
    for col, term in zip(r1, SUGGESTIONS[:4]):
        with col:
            if st.button(term, key="s1_" + term, use_container_width=True):
                set_pending(term); st.rerun()
    for col, term in zip(r2, SUGGESTIONS[4:]):
        with col:
            if st.button(term, key="s2_" + term, use_container_width=True):
                set_pending(term); st.rerun()

    md(card(
        "<div style='text-align:center;'>"
        "<div style='font-size:2rem;margin-bottom:10px;'>🔬</div>"
        + h2("Search synthetic GMP-style SOPs") +
        para("Enter a keyword above to find relevant procedures, methods, "
             "specifications, and document sections across the SOP corpus.") +
        "<div style='margin-top:16px;'>"
        "<a href='" + STUDY_URL + "' target='_blank' rel='noopener noreferrer'"
        " style='display:inline-block;padding:10px 20px;background:#eff6ff;"
        "border:1px solid #bfdbfe;border-radius:9px;color:#1d4ed8;"
        "font-size:14px;font-weight:700;text-decoration:none;'>"
        "Participate in Study ↗</a></div></div>",
        "margin-top:12px;"
    ))

# =========================================================
# Results
# =========================================================
if query:
    if query not in st.session_state.search_history:
        st.session_state.search_history.append(query)

    merged = build_results(query, kdf, pdf)

    md("<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
       "letter-spacing:.08em;color:#9ca3af;margin:10px 0 8px;'>Search Results</div>")

    # No results
    if merged.empty:
        md(card(
            "<div style='text-align:center;'>"
            "<div style='font-size:2rem;margin-bottom:10px;'>🔍</div>"
            + h2("No results found for \"" + query + "\"") +
            para("Try a different keyword, broaden the term, or check the spelling.<br><br>"
                 "<strong>Note:</strong> Empty results are part of the document usability signal — "
                 "if workers cannot find what they need, that is a system-level retrieval problem.") +
            "</div>"
        ))

    else:
        total  = len(merged)
        pages  = max(1, (total - 1) // RESULTS_PER_PAGE + 1)
        if st.session_state.current_page > pages:
            st.session_state.current_page = pages

        start = (st.session_state.current_page - 1) * RESULTS_PER_PAGE
        end   = start + RESULTS_PER_PAGE
        page_df = merged.iloc[start:end].copy()

        log_search(query, page_df, found="unknown")
        unique_sops = merged["sop_id"].nunique()

        # Stats bar
        md(card(
            "<div style='display:flex;flex-wrap:wrap;gap:16px;align-items:center;'>"
            "<div><span style='font-size:22px;font-weight:700;color:#111827;'>"
            + str(total) + "</span>"
            "<span style='font-size:13px;color:#9ca3af;margin-left:4px;'>sections</span></div>"
            "<div style='width:1px;height:24px;background:#e5e7eb;'></div>"
            "<div><span style='font-size:22px;font-weight:700;color:#111827;'>"
            + str(unique_sops) + "</span>"
            "<span style='font-size:13px;color:#9ca3af;margin-left:4px;'>SOPs</span></div>"
            "<div style='width:1px;height:24px;background:#e5e7eb;'></div>"
            "<div style='font-size:13px;color:#9ca3af;'>page <strong style='color:#374151;'>"
            + str(st.session_state.current_page) + "</strong> of <strong style='color:#374151;'>"
            + str(pages) + "</strong> · sorted by relevance</div>"
            "<div style='margin-left:auto;font-size:13px;color:#6b7280;'>results "
            + str(start+1) + "–" + str(min(end,total)) + " of " + str(total) + "</div>"
            "</div>"
            "<div style='margin-top:12px;padding-top:12px;border-top:1px solid #f3f4f6;"
            "display:flex;gap:12px;flex-wrap:wrap;align-items:center;'>"
            "<span style='font-size:11px;font-weight:700;text-transform:uppercase;"
            "letter-spacing:.07em;color:#9ca3af;margin-right:4px;'>Match strength</span>"
            "<span style='display:inline-flex;align-items:center;gap:5px;"
            "padding:3px 10px;background:#f0fdf4;border:1px solid #86efac;"
            "border-radius:6px;font-size:12px;font-weight:600;color:#16a34a;'>"
            "Strong  <span style='font-weight:400;color:#15803d;'>5+ keyword matches</span></span>"
            "<span style='display:inline-flex;align-items:center;gap:5px;"
            "padding:3px 10px;background:#fefce8;border:1px solid #fde68a;"
            "border-radius:6px;font-size:12px;font-weight:600;color:#d97706;'>"
            "Good  <span style='font-weight:400;color:#b45309;'>2–4 matches</span></span>"
            "<span style='display:inline-flex;align-items:center;gap:5px;"
            "padding:3px 10px;background:#f9fafb;border:1px solid #e5e7eb;"
            "border-radius:6px;font-size:12px;font-weight:600;color:#6b7280;'>"
            "Weak  <span style='font-weight:400;color:#9ca3af;'>1 match</span></span>"
            "</div>",
            "padding:14px 20px;"
        ))

        # Pagination top
        nl, nm, nr = st.columns([1,3,1], gap="small")
        with nl:
            if st.button("← Previous", use_container_width=True,
                         disabled=st.session_state.current_page==1, key="prev_top"):
                st.session_state.current_page -= 1; st.rerun()
        with nr:
            if st.button("Next →", use_container_width=True,
                         disabled=st.session_state.current_page==pages, key="next_top"):
                st.session_state.current_page += 1; st.rerun()

        md("<div style='height:4px;'></div>")

        # Result cards
        for idx, row in page_df.iterrows():
            label, sc_color, sc_bg = match_info(int(row["kcount"]))
            card_key    = query + "_" + str(row["sop_id"]) + "_" + str(row["page"])
            fb_val      = st.session_state.feedback.get(card_key)
            page_n      = int(row["page"]) if pd.notna(row["page"]) else "-"

            fb_tag = ""
            if fb_val is True:
                fb_tag = ("<span style='font-size:12px;color:#16a34a;"
                          "font-weight:700;'>✅ Found</span>")
            elif fb_val is False:
                fb_tag = ("<span style='font-size:12px;color:#dc2626;"
                          "font-weight:700;'>❌ Not this</span>")

            md(result_card(
                sop_id=row["sop_id"], page_num=page_n,
                title_html=hl(row["title"], query),
                snip_html=hl(row["snip"], query),
                label=label, score_color=sc_color, score_bg=sc_bg,
                kcount=int(row["kcount"]), feedback_tag=fb_tag,
            ))

            # Feedback buttons
            if fb_val is None:
                md("<div style='font-size:13px;color:#9ca3af;margin-bottom:6px;'>"
                   "Was this result helpful?</div>")
                fb1, fb2, fb3 = st.columns([1,1,6], gap="small")
                with fb1:
                    if st.button("✅ Found", key="found_" + card_key + "_" + str(idx),
                                 use_container_width=True):
                        st.session_state.feedback[card_key] = True
                        log_search(query, page_df[page_df.index==idx], found="yes")
                        st.session_state.toast_msg = "✅ Marked as found"
                        st.rerun()
                with fb2:
                    if st.button("❌ Not this", key="nf_" + card_key + "_" + str(idx),
                                 use_container_width=True):
                        st.session_state.feedback[card_key] = False
                        log_search(query, page_df[page_df.index==idx], found="no")
                        st.session_state.toast_msg = "❌ Marked as not found"
                        st.rerun()

            md("<div style='height:4px;'></div>")

        # Overall feedback
        md(card(
            overline("Overall Search Feedback") +
            h2("Did this search find what you were looking for?", size="15px", mb="12px"),
            "margin-top:4px;"
        ))

        qfb = st.session_state.query_outcome_feedback.get(query)
        if qfb is None:
            q1, q2, q3 = st.columns([1,1,6], gap="small")
            with q1:
                if st.button("✅ Yes", key="qy_" + query, use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = True
                    log_outcome(query, True)
                    st.session_state.toast_msg = "✅ Feedback saved"
                    st.rerun()
            with q2:
                if st.button("❌ No", key="qn_" + query, use_container_width=True):
                    st.session_state.query_outcome_feedback[query] = False
                    log_outcome(query, False)
                    st.session_state.toast_msg = "❌ Feedback saved"
                    st.rerun()
        else:
            if qfb:
                md("<div style='font-size:14px;color:#16a34a;font-weight:600;'>"
                   "✅ Marked as a successful search.</div>")
            else:
                md("<div style='font-size:14px;color:#dc2626;font-weight:600;'>"
                   "❌ Marked as an unsuccessful search.</div>")

        # Pagination bottom
        md("<div style='height:8px;'></div>")
        bl, bm, br = st.columns([1,3,1], gap="small")
        with bl:
            if st.button("← Previous ", use_container_width=True,
                         disabled=st.session_state.current_page==1, key="prev_bot"):
                st.session_state.current_page -= 1; st.rerun()
        with br:
            if st.button("Next → ", use_container_width=True,
                         disabled=st.session_state.current_page==pages, key="next_bot"):
                st.session_state.current_page += 1; st.rerun()
