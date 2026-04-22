"""
TariffGuard — Tariff Exposure & Supplier Shift Simulator
=========================================================
Built by Rutwik Satish | MS Engineering Management, Northeastern University

WHY THIS EXISTS:
  On April 2, 2025 ("Liberation Day"), the US announced the largest tariff
  increases in modern trade history: China +120pp, Vietnam +46pp,
  Mexico +25pp, Canada +25pp. Mid-market manufacturers ($50M–$500M revenue)
  were blindsided. Large companies (Apple, Ford) have entire trade compliance
  teams and six-figure software for this. Small companies don't have enough
  volume to care. Mid-market companies are stuck doing this in Excel.

  The question every Procurement team is now asking:
  1. How much is this actually costing us annually, per component?
  2. Which supplier shifts actually pencil out when you include transition costs?
  3. What happens to our margins under each scenario?

WHAT IT DOES:
  TariffGuard quantifies tariff exposure across a product portfolio, models
  three strategic responses (Absorb / Pass-Through / Supplier Switch),
  and includes the transition cost math that every other tariff tool ignores:
  PPAP re-qualification timeline, bridge inventory cost, and production gap risk.

  The AI layer generates a structured optimization roadmap with specific
  $ impacts, product names, and ownership — the same analysis a supply chain
  strategy consultant would produce at $50K/engagement.

DATA MODEL:
  10 realistic products spanning high-tariff countries. Unit costs and selling
  prices calibrated to realistic margin profiles. Tariff rates based on 2025
  USTR announcements (Jan–Apr 2025).

STACK: Python · Streamlit · Plotly · Pandas · Requests (Groq)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import date, datetime, timedelta

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
TODAY_STR  = date.today().strftime("%B %d, %Y")

DEFAULT_TARIFFS = {
    "China":       {"current":25.0, "new":145.0},
    "Mexico":      {"current":0.0,  "new":25.0},
    "Canada":      {"current":0.0,  "new":25.0},
    "Vietnam":     {"current":0.0,  "new":46.0},
    "India":       {"current":0.0,  "new":26.0},
    "Germany":     {"current":0.0,  "new":20.0},
    "Taiwan":      {"current":0.0,  "new":32.0},
    "Japan":       {"current":0.0,  "new":24.0},
    "South Korea": {"current":0.0,  "new":25.0},
    "Brazil":      {"current":0.0,  "new":10.0},
}

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TariffGuard | Tariff Impact & Optimization",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DESIGN SYSTEM ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700&family=Inter:wght@300;400;500&display=swap');

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="block-container"] {
    background-color: #fafafa !important;
    color: #111827 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stSidebar"] {
    background-color: #111827 !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #d1d5db !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2 { color: #f9fafb !important; font-family: 'Syne', sans-serif !important; }
[data-testid="stSidebarNav"] { display: none !important; }

h1,h2,h3,h4 { font-family: 'Syne', sans-serif !important; color: #111827 !important; }

[data-testid="metric-container"] {
    background: #fff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 18px !important;
}
[data-testid="stMetricValue"]  { color: #111827 !important; font-family: 'Syne', sans-serif !important; font-weight: 600 !important; font-size: 1.6rem !important; }
[data-testid="stMetricLabel"]  { color: #6b7280 !important; font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.1em; }
[data-testid="stMetricDelta"]  svg { display: none; }

[data-testid="stTabs"] button { color: #6b7280 !important; font-family: 'Inter', sans-serif !important; font-size: 0.84rem !important; background: transparent !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #dc2626 !important; border-bottom: 2px solid #dc2626 !important; }

[data-testid="stDataFrame"] { background: #fff !important; border: 1px solid #e5e7eb !important; border-radius: 12px !important; }
.stDataFrame th { background: #f9fafb !important; color: #6b7280 !important; font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.07em; }
.stDataFrame td { color: #111827 !important; background: #fff !important; font-size: 0.83rem !important; }

[data-testid="stButton"] button {
    background: #dc2626 !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important; font-weight: 500 !important;
}
[data-testid="stButton"] button:hover { background: #b91c1c !important; }

[data-testid="stSelectbox"] > div { background: #fff !important; border: 1px solid #e5e7eb !important; border-radius: 8px !important; }
[data-testid="stSelectbox"] label { color: #6b7280 !important; font-size: 0.78rem !important; }
[data-testid="stExpander"] { background: #fff !important; border: 1px solid #e5e7eb !important; border-radius: 12px !important; }
[data-testid="stExpander"] summary { color: #dc2626 !important; font-weight: 500 !important; }

.stSlider label { color: #6b7280 !important; font-size: 0.78rem !important; }
hr { border-color: #e5e7eb !important; }
[data-testid="stAlert"] { border-radius: 10px !important; }

.section-label {
    font-size: 0.66rem; text-transform: uppercase;
    letter-spacing: 0.16em; color: #dc2626;
    font-weight: 600; margin-bottom: 8px; font-family: 'Inter', sans-serif;
}
.hero-number {
    font-family: 'Syne', sans-serif; font-size: 2.6rem;
    font-weight: 700; color: #dc2626; line-height: 1;
}
.problem-card {
    background: #fff; border: 1px solid #e5e7eb;
    border-left: 3px solid #dc2626;
    border-radius: 12px; padding: 18px 22px; margin-bottom: 12px;
}
.solution-card {
    background: #fff; border: 1px solid #e5e7eb;
    border-left: 3px solid #16a34a;
    border-radius: 12px; padding: 18px 22px; margin-bottom: 12px;
}
.context-card {
    background: #111827; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 16px;
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;
}
.context-stat-val  { font-family:'Syne',sans-serif; font-size:1.8rem; font-weight:700; color:#f9fafb; }
.context-stat-ctry { font-size:0.7rem; color:#9ca3af; text-transform:uppercase; letter-spacing:0.1em; margin-top:2px; }
.context-stat-note { font-size:0.75rem; color:#ef4444; margin-top:4px; }
.ai-block {
    background: #fff; border: 1px solid #e5e7eb;
    border-left: 3px solid #dc2626;
    border-radius: 12px; padding: 20px 24px;
    font-size: 0.87rem; line-height: 1.85;
    color: #111827; white-space: pre-wrap;
}
.scenario-metric {
    background: #fff; border: 1px solid #e5e7eb;
    border-radius: 12px; padding: 16px 20px;
}
.transition-box {
    background: #fffbeb; border: 1px solid #fde68a;
    border-radius: 10px; padding: 14px 18px;
    font-size: 0.83rem; line-height: 1.75; color: #92400e;
}
</style>
""", unsafe_allow_html=True)

CHART = dict(
    template="plotly_white",
    paper_bgcolor="#fafafa", plot_bgcolor="#fff",
    font=dict(color="#111827", family="Inter"),
    xaxis=dict(gridcolor="#f3f4f6", linecolor="#e5e7eb", tickfont=dict(color="#6b7280")),
    yaxis=dict(gridcolor="#f3f4f6", linecolor="#e5e7eb", tickfont=dict(color="#6b7280")),
    margin=dict(t=40,b=44,l=12,r=12),
)
RISK_COLOR = {"HIGH":"#ef4444","MEDIUM":"#f59e0b","LOW":"#22c55e"}

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "tariffs"   not in st.session_state: st.session_state.tariffs   = {k:v.copy() for k,v in DEFAULT_TARIFFS.items()}
if "ai_output" not in st.session_state: st.session_state.ai_output = ""
if "groq_key"  not in st.session_state: st.session_state.groq_key  = ""

# ── SAMPLE DATA (auto-loaded) ──────────────────────────────────────────────────
@st.cache_data
def get_sample_data() -> pd.DataFrame:
    """
    10 products across major high-tariff countries.
    3 China products go NEGATIVE MARGIN under 145% tariffs.
    This is the exact scenario US importers are living in 2025.
    unit_cost_base = import cost BEFORE tariff (transparent and auditable).
    """
    rows = [
        ("Electronic Control Modules",  "SinoTech Ltd.",     "China",       "Electronics",     2400,  38.50,  89.00),
        ("Steel Structural Tubing",     "CanSteel Corp.",    "Canada",      "Raw Materials",    850,  142.00, 198.00),
        ("Injection-Molded Housings",   "MexPlast SA",       "Mexico",      "Components",      5200,   8.20,  18.50),
        ("NAND Flash Memory",           "TaiwanChip Co.",    "Taiwan",      "Semiconductors", 12000,   4.80,  12.00),
        ("Woven Fabric Rolls",          "VietTex Mfg.",      "Vietnam",     "Textiles",        3100,  22.40,  48.00),
        ("Precision Bearings",          "KugelGmbH",         "Germany",     "Industrial",      1800,  31.60,  67.00),
        ("Chemical Solvents",           "ChemCo Shanghai",   "China",       "Chemicals",        920,  18.90,  39.00),
        ("Auto Wiring Harnesses",       "AutoMex SA",        "Mexico",      "Auto Parts",       640,  87.50, 158.00),
        ("LED Display Panels",          "BrightTech HK",     "China",       "Electronics",     1650,  62.00, 145.00),
        ("Pharmaceutical APIs",         "IndoPharma Ltd.",   "India",       "Pharma",           430, 215.00, 520.00),
    ]
    return pd.DataFrame(rows, columns=["product","supplier","country","category",
                                        "monthly_units","unit_cost_base","selling_price"])

# ── CORE CALCULATION ENGINE ────────────────────────────────────────────────────
def apply_tariffs(df: pd.DataFrame, tariffs: dict) -> pd.DataFrame:
    df = df.copy()
    df["current_tariff_pct"] = df["country"].map(lambda c: tariffs.get(c,{}).get("current",0.0))
    df["new_tariff_pct"]     = df["country"].map(lambda c: tariffs.get(c,{}).get("new",0.0))
    df["unit_cost_curr"]     = df["unit_cost_base"] * (1 + df["current_tariff_pct"]/100)
    df["unit_cost_new"]      = df["unit_cost_base"] * (1 + df["new_tariff_pct"]/100)
    df["tariff_delta_pu"]    = df["unit_cost_new"] - df["unit_cost_curr"]
    df["margin_curr_pct"]    = ((df["selling_price"]-df["unit_cost_curr"])/df["selling_price"]*100).round(1)
    df["margin_new_pct"]     = ((df["selling_price"]-df["unit_cost_new"]) /df["selling_price"]*100).round(1)
    df["margin_erosion"]     = (df["margin_curr_pct"] - df["margin_new_pct"]).round(1)
    df["annual_units"]       = df["monthly_units"] * 12
    df["annual_revenue"]     = (df["annual_units"] * df["selling_price"]).round(0)
    df["annual_margin_curr"] = (df["annual_units"] * (df["selling_price"]-df["unit_cost_curr"])).round(0)
    df["annual_margin_new"]  = (df["annual_units"] * (df["selling_price"]-df["unit_cost_new"])).round(0)
    df["annual_margin_loss"] = (df["annual_margin_curr"] - df["annual_margin_new"]).round(0)
    curr_mr = (df["selling_price"]-df["unit_cost_curr"]) / df["selling_price"]
    df["price_to_maintain"]  = (df["unit_cost_new"]/(1-curr_mr)).round(2)
    df["price_increase_pct"] = ((df["price_to_maintain"]-df["selling_price"])/df["selling_price"]*100).round(1)
    def tier(row):
        if row["margin_new_pct"]  <  0: return "HIGH"
        if row["margin_erosion"]  >= 15: return "HIGH"
        if row["margin_erosion"]  >=  5: return "MEDIUM"
        return "LOW"
    df["risk_tier"] = df.apply(tier, axis=1)
    return df

# ── AI ────────────────────────────────────────────────────────────────────────
def ask_groq(system: str, user: str, api_key: str) -> str:
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":GROQ_MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.2,"max_tokens":2000},
            timeout=90,
        )
        if resp.status_code == 401: return "INVALID_KEY"
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

def build_ai_prompt(df: pd.DataFrame, tariffs: dict) -> tuple:
    total_rev  = df["annual_revenue"].sum()
    total_loss = df["annual_margin_loss"].sum()
    high_n     = len(df[df["risk_tier"]=="HIGH"])
    neg_margin = df[df["margin_new_pct"]<0]
    top5 = df.nlargest(5,"annual_margin_loss")
    top5_text = "\n".join([f"  • {r.product} ({r.country}): margin {r.margin_curr_pct:.1f}%→{r.margin_new_pct:.1f}% | Annual loss: ${r.annual_margin_loss:,.0f} | Price hike needed: +{r.price_increase_pct:.1f}%" for _,r in top5.iterrows()])
    ctry_text  = "\n".join([f"  • {c}: ${v:,.0f}" for c,v in df.groupby("country")["annual_margin_loss"].sum().sort_values(ascending=False).items()])
    active = {c:v for c,v in tariffs.items() if v["new"]!=v["current"]}
    tariff_text = "\n".join([f"  • {c}: {v['current']}%→{v['new']}% (+{v['new']-v['current']:.0f}pp)" for c,v in active.items()])
    neg_text = "\nPRODUCTS NOW LOSS-MAKING:\n" + "\n".join([f"  • {r.product}: {r.margin_new_pct:.1f}%" for _,r in neg_margin.iterrows()]) if len(neg_margin)>0 else ""

    system = "You are a senior supply chain strategy consultant specialising in trade policy and margin optimization. You provide precise, data-driven recommendations. You always cite specific numbers from the data. You are direct — no padding, no vague statements like 'consider reviewing'."
    user = f"""Analyse this portfolio's 2025 tariff exposure and provide a specific optimization roadmap.

DATE: {TODAY_STR}
PORTFOLIO: ${total_rev:,.0f} revenue | ${total_loss:,.0f} margin at risk ({total_loss/total_rev*100:.1f}% of revenue)
HIGH-RISK: {high_n} of {len(df)}{neg_text}

TARIFF CHANGES:
{tariff_text}

TOP 5 WORST PRODUCTS:
{top5_text}

ANNUAL LOSS BY COUNTRY:
{ctry_text}

Respond in EXACTLY this format:

SITUATION ASSESSMENT:
[3-4 sentences on severity, worst exposure, core strategic risk]

IMMEDIATE ACTIONS — next 30 days:
1. [action | $ impact | owner]
2. [action | $ impact | owner]
3. [action | $ impact | owner]

PRICING STRATEGY:
[Which products can absorb price increases? Which cannot? Cite names and numbers.]

SOURCING DIVERSIFICATION:
[For each HIGH-risk product: recommend specific alternative country, expected tariff rate, net saving estimate.]

QUICK WINS vs STRUCTURAL CHANGES:
  Quick wins (0–4 weeks): [specific list]
  Medium term (1–6 months): [specific list]

LEADERSHIP DECISION:
[One paragraph: what must leadership decide in 2 weeks, and what happens if they delay?]"""
    return system, user

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding:8px 0 20px">
  <div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.18em;color:#f87171;font-weight:600;margin-bottom:4px">TRADE INTELLIGENCE</div>
  <div style="font-family:Syne,sans-serif;font-size:1.5rem;font-weight:700;color:#f9fafb">TariffGuard</div>
  <div style="font-size:0.75rem;color:#6b7280;margin-top:2px">Tariff Exposure & Supplier Shift Simulator</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="background:#1f2937;border-radius:8px;padding:12px 14px;margin-bottom:16px;font-size:0.78rem;line-height:1.7;color:#9ca3af">
<span style="color:#f87171;font-weight:600">2025 US Tariff Schedule</span><br>
China +120pp · Vietnam +46pp<br>
Mexico +25pp · Canada +25pp<br>
Taiwan +32pp · India +26pp
</div>
""", unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;color:#6b7280;font-weight:600;margin-bottom:8px">DATA</div>', unsafe_allow_html=True)
    src = st.radio("Source", ["Demo Portfolio (10 products)","Upload your CSV"], label_visibility="collapsed")

    uploaded_df = None
    if src == "Upload your CSV":
        uf = st.file_uploader("Columns: product, supplier, country, category, monthly_units, unit_cost_base, selling_price", type="csv")
        if uf:
            uploaded_df = pd.read_csv(uf)
            st.success(f"✅ {len(uploaded_df)} products loaded")

    st.markdown("---")
    st.markdown('<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.12em;color:#6b7280;font-weight:600;margin-bottom:8px">AI (GROQ — FREE)</div>', unsafe_allow_html=True)
    if "GROQ_API_KEY" in st.secrets:
        st.session_state.groq_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Key loaded")
    else:
        ki = st.text_input("Groq API Key", value=st.session_state.groq_key, type="password", placeholder="gsk_...")
        if ki: st.session_state.groq_key = ki
        if not st.session_state.groq_key:
            st.caption("Free at [console.groq.com](https://console.groq.com) — 2 min setup")

    st.markdown("---")
    with st.expander("Edit tariff rates"):
        raw_df = uploaded_df if uploaded_df is not None else get_sample_data()
        active_ctry = raw_df["country"].unique().tolist()
        for country in DEFAULT_TARIFFS:
            if country in active_ctry:
                st.markdown(f"**{country}**")
                c1,c2 = st.columns(2)
                cur = c1.number_input("Now",0.0,300.0,float(st.session_state.tariffs[country]["current"]),0.5,key=f"cur_{country}")
                nw  = c2.number_input("New",0.0,300.0,float(st.session_state.tariffs[country]["new"]),0.5,key=f"new_{country}")
                st.session_state.tariffs[country] = {"current":cur,"new":nw}

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
raw_df = uploaded_df if uploaded_df is not None else get_sample_data()
df     = apply_tariffs(raw_df, st.session_state.tariffs)

total_rev       = df["annual_revenue"].sum()
total_loss      = df["annual_margin_loss"].sum()
avg_erosion     = df["margin_erosion"].mean()
high_n          = len(df[df["risk_tier"]=="HIGH"])
neg_n           = len(df[df["margin_new_pct"]<0])
worst_ctry      = df.groupby("country")["annual_margin_loss"].sum().idxmax()
worst_ctry_loss = df.groupby("country")["annual_margin_loss"].sum().max()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="padding:28px 0 8px">
  <div class="section-label">TARIFF IMPACT & SUPPLIER OPTIMIZATION</div>
  <h1 style="font-size:2.2rem;font-weight:700;margin:0;letter-spacing:-0.03em">TariffGuard</h1>
  <p style="color:#6b7280;font-size:0.9rem;margin-top:6px;max-width:640px">
    Quantifies how the 2025 US tariff escalation erodes product margins, then models the true cost of each strategic response — including the transition costs every other tool ignores.
  </p>
</div>
""", unsafe_allow_html=True)

# Problem / Solution framing
with st.expander("📋 The problem this solves — and how", expanded=False):
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("""
<div class="problem-card">
<div class="section-label" style="color:#dc2626">THE INDUSTRY PROBLEM</div>
<p style="font-size:0.87rem;line-height:1.75;color:#374151;margin:0">
The 2025 tariff escalation hit mid-market manufacturers ($50M–$500M revenue) hardest.
Large companies have trade compliance teams and expensive software.
Small companies aren't affected at scale. Mid-market companies are
<strong style="color:#dc2626">making multi-million dollar sourcing decisions in Excel spreadsheets.</strong>
<br><br>
The hard problem isn't knowing tariff rates — those are public. It's the <strong>decision model</strong>:
if I shift from China to Mexico, my tariff burden drops but my unit cost rises, lead time
increases 12 days, I need extra safety stock, and I have a 90-day PPAP re-qualification.
What's my actual net saving and when do I break even?
</p>
</div>
""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
<div class="solution-card">
<div class="section-label" style="color:#16a34a">HOW TARIFFGUARD SOLVES IT</div>
<p style="font-size:0.87rem;line-height:1.75;color:#374151;margin:0">
TariffGuard builds the full decision model that procurement teams need:
<br><br>
• <strong>Exposure Dashboard</strong> — Annual tariff burden per product and country, risk tier classification<br>
• <strong>Scenario Modeling</strong> — Absorb vs. Pass-Through vs. Supplier Switch with true net savings<br>
• <strong>Transition Cost Model</strong> — PPAP re-qualification + bridge inventory + production gap risk included<br>
• <strong>AI Optimization Brief</strong> — Specific actions per product with $ impact and ownership
<br><br>
This is the analysis a supply chain consultant charges <strong style="color:#16a34a">$50K to produce</strong>. TariffGuard generates it in seconds from a CSV upload.
</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="background:#111827;border-radius:10px;padding:16px 20px;font-size:0.82rem;color:#9ca3af;margin-top:4px">
<strong style="color:#f9fafb">Tariff context:</strong> China +120pp · Vietnam +46pp · Mexico +25pp · Canada +25pp · Taiwan +32pp · India +26pp (2025 USTR announcements). These are the largest US tariff increases in modern trade history.
The demo portfolio shows 3 China-sourced products going <strong style="color:#ef4444">negative margin</strong> — which is exactly what US importers are experiencing.
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── KPI STRIP ─────────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Annual Revenue",       f"${total_rev/1e6:.2f}M")
c2.metric("Margin $ at Risk",     f"${total_loss/1e3:.0f}K", delta=f"−{total_loss/total_rev*100:.1f}% of revenue",delta_color="inverse")
c3.metric("Avg Margin Erosion",   f"{avg_erosion:.1f}pp",    delta_color="inverse",delta="vs current")
c4.metric("HIGH Risk Products",   f"{high_n} / {len(df)}",   delta=f"{neg_n} in negative margin",delta_color="inverse")
c5.metric("Biggest Country Loss", worst_ctry,                delta=f"${worst_ctry_loss/1e3:.0f}K/yr",delta_color="inverse")

st.markdown("---")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1,tab2,tab3,tab4 = st.tabs([
    "📊  Impact Dashboard",
    "🔢  Product Analysis",
    "🔮  Scenario Modeling",
    "🤖  AI Optimization",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMPACT DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    cl,cr = st.columns(2)
    with cl:
        bar_cols = [RISK_COLOR[t] for t in df["risk_tier"]]
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="Current Margin %",x=df["product"].str[:18],y=df["margin_curr_pct"],marker_color="#93c5fd",opacity=0.85))
        fig_bar.add_trace(go.Bar(name="New Margin %",    x=df["product"].str[:18],y=df["margin_new_pct"],marker_color=bar_cols))
        fig_bar.add_hline(y=0,line_dash="dash",line_color="#dc2626",opacity=0.6,annotation_text="Zero margin line")
        fig_bar.update_layout(**CHART,title="Gross Margin: Current vs After Tariffs",barmode="group",
                               yaxis_title="Gross Margin %",height=370,
                               legend=dict(orientation="h",y=1.02),
                               xaxis=dict(tickangle=-35,tickfont_size=10))
        st.plotly_chart(fig_bar, use_container_width=True)

    with cr:
        by_ctry = df.groupby("country")["annual_margin_loss"].sum().sort_values(ascending=False)
        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute"]+["relative"]*len(by_ctry)+["total"],
            x=["Current Margin"]+list(by_ctry.index)+["New Margin"],
            y=[df["annual_margin_curr"].sum()]+[-v for v in by_ctry.values]+[0],
            connector={"line":{"color":"#e5e7eb","width":1}},
            increasing={"marker":{"color":"#22c55e"}},
            decreasing={"marker":{"color":"#ef4444"}},
            totals={"marker":{"color":"#6366f1"}},
            text=(
                [f"${df['annual_margin_curr'].sum()/1e3:.0f}K"] +
                [f"−${v/1e3:.0f}K" for v in by_ctry.values] +
                [f"${df['annual_margin_new'].sum()/1e3:.0f}K"]
            ),
            textposition="outside",
        ))
        fig_wf.update_layout(**CHART,title="Annual Margin Erosion by Country",height=370,showlegend=False)
        st.plotly_chart(fig_wf, use_container_width=True)

    fig_bubble = px.scatter(
        df, x="margin_erosion", y="margin_new_pct",
        size="annual_revenue", color="risk_tier", color_discrete_map=RISK_COLOR,
        hover_name="product",
        hover_data={"country":True,"annual_margin_loss":":$,.0f","risk_tier":False,"annual_revenue":False},
        labels={"margin_erosion":"Margin Erosion (pp)","margin_new_pct":"New Gross Margin (%)"},
        title="Risk Matrix: Margin Erosion vs New Margin Level  (bubble = annual revenue)",
    )
    fig_bubble.add_hline(y=0,  line_dash="dash",line_color="#dc2626",opacity=0.5,annotation_text="Zero margin")
    fig_bubble.add_vline(x=5,  line_dash="dot", line_color="#f59e0b",opacity=0.4,annotation_text="Medium risk")
    fig_bubble.add_vline(x=15, line_dash="dot", line_color="#ef4444",opacity=0.4,annotation_text="High risk")
    fig_bubble.update_layout(**CHART,height=400)
    st.plotly_chart(fig_bubble, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PRODUCT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-label">FULL PORTFOLIO — TARIFF IMPACT BY PRODUCT</div>', unsafe_allow_html=True)
    fc1,fc2,fc3 = st.columns(3)
    risk_f = fc1.multiselect("Risk Tier",["HIGH","MEDIUM","LOW"],default=["HIGH","MEDIUM","LOW"])
    ctry_f = fc2.multiselect("Country",sorted(df["country"].unique()),default=sorted(df["country"].unique()))
    sort_f = fc3.selectbox("Sort by",["Annual Margin Loss ↓","Margin Erosion ↓","Revenue ↓"])

    filtered = df[df["risk_tier"].isin(risk_f) & df["country"].isin(ctry_f)].copy()
    filtered = filtered.sort_values({"Annual Margin Loss ↓":"annual_margin_loss","Margin Erosion ↓":"margin_erosion","Revenue ↓":"annual_revenue"}[sort_f],ascending=False)

    def cr_risk(v):
        return {"HIGH":"background:#fef2f2;color:#dc2626;font-weight:600","MEDIUM":"background:#fffbeb;color:#d97706;font-weight:600","LOW":"background:#f0fdf4;color:#16a34a;font-weight:600"}.get(v,"")
    def cr_margin(v):
        if isinstance(v,float) and v<0: return "background:#fef2f2;color:#dc2626;font-weight:700"
        return ""
    def cr_erosion(v):
        if isinstance(v,float):
            if v>=15: return "color:#dc2626;font-weight:600"
            if v>=5:  return "color:#d97706;font-weight:600"
        return ""

    disp_cols = ["product","supplier","country","category","current_tariff_pct","new_tariff_pct",
                 "unit_cost_curr","unit_cost_new","tariff_delta_pu","margin_curr_pct","margin_new_pct",
                 "margin_erosion","annual_revenue","annual_margin_loss","price_increase_pct","risk_tier"]
    rename = {"product":"Product","supplier":"Supplier","country":"Country","category":"Category",
              "current_tariff_pct":"Tariff Now %","new_tariff_pct":"Tariff New %",
              "unit_cost_curr":"Cost Now","unit_cost_new":"Cost New","tariff_delta_pu":"Extra/Unit",
              "margin_curr_pct":"Margin Now %","margin_new_pct":"Margin New %","margin_erosion":"Erosion pp",
              "annual_revenue":"Annual Rev","annual_margin_loss":"Annual Loss",
              "price_increase_pct":"Price Hike %","risk_tier":"Risk"}

    styled = (
        filtered[disp_cols].rename(columns=rename).style
        .map(cr_risk,   subset=["Risk"])
        .map(cr_margin, subset=["Margin New %"])
        .map(cr_erosion,subset=["Erosion pp"])
        .format({"Tariff Now %":"{:.1f}%","Tariff New %":"{:.1f}%","Cost Now":"${:.2f}","Cost New":"${:.2f}","Extra/Unit":"${:.2f}","Margin Now %":"{:.1f}%","Margin New %":"{:.1f}%","Erosion pp":"{:.1f}","Annual Rev":"${:,.0f}","Annual Loss":"${:,.0f}","Price Hike %":"{:.1f}%"})
    )
    st.dataframe(styled, use_container_width=True, height=430)
    st.download_button("📥 Download CSV", df.to_csv(index=False), f"tariffguard_{date.today()}.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SCENARIO MODELING (with PPAP transition cost)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-label">THREE STRATEGIC RESPONSES — WITH FULL TRANSITION COSTS</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:#fff;border:1px solid #e5e7eb;border-left:3px solid #f59e0b;border-radius:12px;padding:14px 20px;font-size:0.84rem;line-height:1.7;color:#374151;margin-bottom:16px">
<strong>What makes this different:</strong> Most tariff tools stop at "switch to Country X and save $Y." TariffGuard includes the costs that make or break the real decision:
PPAP supplier qualification timeline, bridge inventory carrying cost, and production gap risk. These are the numbers your Procurement and Supply Chain teams need to actually pull the trigger.
</div>
""", unsafe_allow_html=True)

    with st.expander("⚙️ Configure scenarios", expanded=True):
        sp1,sp2,sp3 = st.columns(3)
        with sp1:
            st.markdown("**Scenario A — Partial Absorption**")
            absorb_pct = st.slider("% company absorbs",0,100,50,5)
            st.caption(f"Absorb {absorb_pct}%, pass {100-absorb_pct}% to customer via price increase")
        with sp2:
            st.markdown("**Scenario B — Full Pass-Through**")
            vol_hit = st.checkbox("10% volume loss on products needing >15% price increase",value=True)
            st.caption("Maintains margin %, risks customer volume")
        with sp3:
            st.markdown("**Scenario C — Supplier Switch**")
            alt_ctry     = st.selectbox("Switch HIGH-risk to",["Mexico","India","Vietnam","Poland","Malaysia","Indonesia","Bangladesh"])
            alt_tariff   = st.number_input("Tariff in new country (%)",0.0,200.0,value=DEFAULT_TARIFFS.get(alt_ctry,{}).get("new",20.0),step=0.5)
            cost_premium = st.slider("Cost premium vs current (%)",-20,60,15,1)
            ppap_days    = st.number_input("PPAP qualification days",30,180,90)
            ppap_cost    = st.number_input("PPAP qualification cost ($)",0,200000,28000,1000)
            only_high    = st.checkbox("Apply only to HIGH-risk products",value=True)

    # Calculations
    sc = df.copy()
    # Scenario A
    absorbed = sc["unit_cost_curr"] + sc["tariff_delta_pu"]*(absorb_pct/100)
    passed   = sc["tariff_delta_pu"]*((100-absorb_pct)/100)
    new_price_a = sc["selling_price"] + passed
    sc["margin_a"] = ((new_price_a - absorbed)/new_price_a*100).round(1)
    sc["loss_a"]   = (sc["annual_units"]*(sc["selling_price"]-absorbed) - sc["annual_margin_curr"]).abs().round(0)
    # Scenario B
    sc["margin_b"] = sc["margin_curr_pct"]
    sc["loss_b"]   = 0.0
    if vol_hit:
        vol_adj = sc["price_increase_pct"].apply(lambda p: 0.9 if p>15 else 1.0)
        rev_b   = sc["annual_units"]*vol_adj*sc["price_to_maintain"]
        sc["loss_b"] = (sc["annual_revenue"]-rev_b).clip(lower=0).round(0)
    # Scenario C
    mask = (sc["risk_tier"]=="HIGH") if only_high else pd.Series(True, index=sc.index)
    new_base_c = sc["unit_cost_base"]*(1+cost_premium/100)
    new_total_c = new_base_c*(1+alt_tariff/100)
    sc["unit_cost_c"] = sc["unit_cost_new"]
    sc.loc[mask,"unit_cost_c"] = new_total_c[mask]
    sc["margin_c"] = ((sc["selling_price"]-sc["unit_cost_c"])/sc["selling_price"]*100).round(1)
    sc["loss_c"]   = (sc["annual_units"]*(sc["selling_price"]-sc["unit_cost_c"]) - sc["annual_margin_curr"]).abs().round(0)

    # PPAP transition cost model
    n_high = int(mask.sum())
    bridge_inv_cost = float(df[mask]["annual_revenue"].sum() * 0.015 * (ppap_days/365))
    gross_saving = float((df[mask]["annual_margin_loss"].sum() * (1 - alt_tariff/df[mask]["new_tariff_pct"].mean())) if df[mask]["new_tariff_pct"].mean()>0 else 0)
    total_transition_cost = ppap_cost * n_high + bridge_inv_cost
    net_annual_saving     = max(0, gross_saving - total_transition_cost)
    break_even_months     = (total_transition_cost / max(gross_saving/12, 1)) if gross_saving>0 else 999

    st.markdown("---")
    st.markdown('<div class="section-label">TRANSITION COST MODEL (SCENARIO C)</div>', unsafe_allow_html=True)
    st.markdown(f"""
<div class="transition-box">
<strong>Supplier shift transition costs — the numbers most tools ignore</strong><br>
Switching {n_high} HIGH-risk product(s) to {alt_ctry} requires:
PPAP re-qualification at ${ppap_cost:,}/supplier × {n_high} = <strong>${ppap_cost*n_high:,}</strong> |
Bridge inventory carrying cost ({ppap_days} days) = <strong>${bridge_inv_cost:,.0f}</strong> |
<strong>Total transition cost: ${total_transition_cost:,.0f}</strong><br>
After transition: est. <strong>${gross_saving:,.0f}/yr gross saving</strong> →
<strong>${net_annual_saving:,.0f}/yr net</strong> |
Break-even: <strong>{break_even_months:.1f} months</strong>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="section-label" style="margin-top:16px">FINANCIAL OUTCOME COMPARISON</div>', unsafe_allow_html=True)
    baseline_m = df["annual_margin_curr"].sum()
    c_base,ca,cb,cc = st.columns(4)
    c_base.metric("Baseline (no action)",  f"${df['annual_margin_new'].sum()/1e3:.0f}K", delta=f"−${total_loss/1e3:.0f}K", delta_color="inverse")
    ca.metric(f"A: {absorb_pct}% Absorb", f"${(baseline_m-sc['loss_a'].sum())/1e3:.0f}K retained", delta=f"{(baseline_m-sc['loss_a'].sum())/baseline_m*100:.1f}% of original")
    cb.metric("B: Pass-Through",          f"${(baseline_m-sc['loss_b'].sum())/1e3:.0f}K retained", delta=f"{(baseline_m-sc['loss_b'].sum())/baseline_m*100:.1f}% of original")
    cc.metric(f"C: Switch → {alt_ctry}",  f"${(baseline_m-sc['loss_c'].sum())/1e3:.0f}K retained", delta=f"Break-even {break_even_months:.1f} mo")

    scenario_df = pd.DataFrame({
        "Product":  df["product"].str[:16].tolist()*4,
        "Scenario": ["Baseline"]*len(df)+[f"A: {absorb_pct}% Absorb"]*len(df)+["B: Pass-Through"]*len(df)+[f"C: → {alt_ctry}"]*len(df),
        "Margin %": df["margin_new_pct"].tolist()+sc["margin_a"].tolist()+sc["margin_b"].tolist()+sc["margin_c"].tolist(),
    })
    fig_sc = px.bar(scenario_df,x="Product",y="Margin %",color="Scenario",barmode="group",
                    color_discrete_sequence=["#94a3b8","#3b82f6","#22c55e","#8b5cf6"],
                    title="Gross Margin % by Product — All Scenarios")
    fig_sc.add_hline(y=0,line_dash="dash",line_color="#dc2626",opacity=0.5,annotation_text="Zero margin")
    fig_sc.update_layout(**CHART,height=400,xaxis=dict(tickangle=-35,tickfont_size=10))
    st.plotly_chart(fig_sc, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-label">AI OPTIMIZATION ROADMAP</div>', unsafe_allow_html=True)
    st.markdown("""
<p style="color:#6b7280;font-size:0.84rem;margin-bottom:16px">
Groq AI (Llama 3.1, free) reads your live portfolio data — product names, actual margin figures, country exposure — and returns the same structured optimization roadmap a supply chain consultant would deliver at $50K/engagement. Specific product names, $ figures, and ownership included.
</p>
""", unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    c1.markdown(f"**Portfolio exposure**\n\n${total_loss/1e3:.0f}K margin at risk\n\n{high_n} HIGH-risk products\n\n{neg_n} in negative margin")
    c2.markdown("**Pricing analysis**\n\nWhich products absorb increases\n\nVolume risk assessment\n\nBlended revenue scenarios")
    c3.markdown("**Sourcing alternatives**\n\nCountry-specific recommendations\n\nCost vs tariff trade-offs\n\nTransition cost estimates")

    if not st.session_state.groq_key:
        st.warning("Add your free Groq API key in the sidebar to generate the AI brief. Free account at console.groq.com — no credit card required.")
    else:
        if st.button("🔍 Generate AI Optimization Plan", type="primary", use_container_width=True):
            with st.spinner("Analysing tariff exposure and building recommendations..."):
                sys_p, usr_p = build_ai_prompt(df, st.session_state.tariffs)
                result = ask_groq(sys_p, usr_p, st.session_state.groq_key)
            if result == "INVALID_KEY":
                st.error("Invalid API key. Check at console.groq.com.")
            elif result.startswith("ERROR"):
                st.error(result)
            else:
                st.session_state.ai_output = result

        if st.session_state.ai_output:
            st.markdown(f'<div class="ai-block">{st.session_state.ai_output}</div>', unsafe_allow_html=True)
            c1,c2 = st.columns(2)
            c1.download_button("📥 Download AI Report (.txt)", st.session_state.ai_output,
                               f"tariffguard_report_{date.today()}.txt","text/plain",use_container_width=True)
            if c2.button("🔄 Regenerate",use_container_width=True):
                st.session_state.ai_output = ""
                st.rerun()

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='font-size:0.75rem;color:#9ca3af;text-align:center'>"
    "TariffGuard · Tariff Exposure & Supplier Shift Simulator · "
    "AI by Groq (Llama 3.1, free) · "
    "2025 US tariff schedule (USTR) · "
    "Built by Rutwik Satish · MS Engineering Management, Northeastern University"
    "</p>",
    unsafe_allow_html=True,
)
