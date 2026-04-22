"""
TariffGuard — Tariff Exposure & Supplier Shift Simulator
=========================================================
Built by Rutwik Satish | MS Engineering Management, Northeastern University

WHY THIS EXISTS:
  On April 2, 2025 ("Liberation Day"), the US announced the largest tariff
  increases in modern trade history: China +120pp, Vietnam +46pp,
  Mexico +25pp, Canada +25pp. Mid-market manufacturers were blindsided.
  Large companies have trade compliance teams and six-figure software.
  Mid-market companies are stuck doing this in Excel.

WHAT IT DOES:
  Quantifies tariff exposure, models three strategic responses
  (Absorb / Pass-Through / Supplier Switch), and includes the transition
  cost math every other tool ignores: PPAP re-qualification timeline,
  bridge inventory cost, and production gap risk.

STACK: Python · Streamlit · Plotly · Pandas · Requests (Groq)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import date

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
TODAY_STR  = date.today().strftime("%B %d, %Y")

DEFAULT_TARIFFS = {
    "China":       {"current": 25.0, "new": 145.0},
    "Mexico":      {"current": 0.0,  "new": 25.0},
    "Canada":      {"current": 0.0,  "new": 25.0},
    "Vietnam":     {"current": 0.0,  "new": 46.0},
    "India":       {"current": 0.0,  "new": 26.0},
    "Germany":     {"current": 0.0,  "new": 20.0},
    "Taiwan":      {"current": 0.0,  "new": 32.0},
    "Japan":       {"current": 0.0,  "new": 24.0},
    "South Korea": {"current": 0.0,  "new": 25.0},
    "Brazil":      {"current": 0.0,  "new": 10.0},
}

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TariffGuard | Tariff Impact & Optimization",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DARK DESIGN SYSTEM ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="block-container"] {
    background-color: #0a0e17 !important;
    color: #c9d1d9 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #21262d !important;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #f0f6fc !important; }
[data-testid="stSidebarNav"] { display: none !important; }
h1,h2,h3,h4,h5,h6 { font-family: 'IBM Plex Sans', sans-serif !important; color: #f0f6fc !important; }

[data-testid="metric-container"] {
    background-color: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    padding: 16px !important;
}
[data-testid="stMetricValue"] {
    color: #f0f6fc !important; font-weight: 600 !important;
    font-family: 'IBM Plex Mono', monospace !important; font-size: 1.55rem !important;
}
[data-testid="stMetricLabel"] {
    color: #8b949e !important; font-size: 0.72rem !important;
    text-transform: uppercase; letter-spacing: 0.08em;
}
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stTabs"] button {
    color: #8b949e !important; background: transparent !important;
    font-family: 'IBM Plex Sans', sans-serif !important; font-size: 0.84rem !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #f85149 !important; border-bottom: 2px solid #f85149 !important;
}
[data-testid="stDataFrame"] {
    background: #0d1117 !important; border: 1px solid #21262d !important; border-radius: 8px !important;
}
.stDataFrame th {
    background: #161b22 !important; color: #8b949e !important;
    font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.06em;
}
.stDataFrame td { color: #c9d1d9 !important; background: #0d1117 !important; font-size: 0.83rem !important; }
[data-testid="stButton"] button {
    background: #b91c1c !important; color: #fff !important;
    border: none !important; border-radius: 6px !important;
    font-family: 'IBM Plex Sans', sans-serif !important; font-weight: 500 !important;
}
[data-testid="stButton"] button:hover { background: #991b1b !important; }
[data-testid="stSelectbox"] > div {
    background: #161b22 !important; border: 1px solid #30363d !important;
    border-radius: 6px !important; color: #c9d1d9 !important;
}
[data-testid="stSelectbox"] label { color: #8b949e !important; font-size: 0.78rem !important; }
[data-testid="stNumberInput"] label { color: #8b949e !important; font-size: 0.78rem !important; }
[data-testid="stNumberInput"] input {
    background: #161b22 !important; border: 1px solid #30363d !important;
    color: #c9d1d9 !important; border-radius: 6px !important;
}
[data-testid="stExpander"] {
    background: #0d1117 !important; border: 1px solid #21262d !important; border-radius: 8px !important;
}
[data-testid="stExpander"] summary { color: #f85149 !important; font-weight: 500 !important; }
[data-testid="stExpander"] * { color: #c9d1d9 !important; }
[data-testid="stAlert"] { background: #0d1117 !important; border-radius: 8px !important; }
.stSlider label { color: #8b949e !important; font-size: 0.78rem !important; }
hr { border-color: #21262d !important; }

.section-label {
    font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.16em;
    color: #f85149; font-weight: 600; margin-bottom: 8px;
    font-family: 'IBM Plex Sans', sans-serif;
}
.problem-card {
    background: #0d1117; border: 1px solid #21262d;
    border-left: 3px solid #f85149; border-radius: 8px; padding: 18px 22px; margin-bottom: 12px;
}
.solution-card {
    background: #0d1117; border: 1px solid #21262d;
    border-left: 3px solid #3fb950; border-radius: 8px; padding: 18px 22px; margin-bottom: 12px;
}
.ai-block {
    background: #0d1117; border: 1px solid #21262d; border-left: 3px solid #f85149;
    border-radius: 8px; padding: 20px 24px; font-size: 0.87rem; line-height: 1.85;
    color: #c9d1d9; white-space: pre-wrap; font-family: 'IBM Plex Sans', sans-serif;
}
.transition-box {
    background: #1c1500; border: 1px solid #3d2f0f; border-radius: 8px;
    padding: 14px 18px; font-size: 0.83rem; line-height: 1.75; color: #d29922;
}
.context-bar {
    background: #161b22; border: 1px solid #21262d; border-radius: 8px;
    padding: 14px 20px; font-size: 0.8rem; color: #8b949e; margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── PLOTLY DARK BASE ──────────────────────────────────────────────────────────
# IMPORTANT: Only safe keys here — no xaxis, yaxis, or legend.
# Those are set per-chart via update_xaxes(), update_yaxes(), update_layout(legend=...).
# Putting them here AND in update_layout(**DARK, legend=...) causes
# "multiple values for keyword argument" TypeError.
DARK_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="#0a0e17",
    plot_bgcolor="#0d1117",
    font=dict(color="#c9d1d9", family="IBM Plex Sans"),
    margin=dict(t=40, b=50, l=12, r=12),
)

# Axis style applied via update_xaxes / update_yaxes on every figure
XAXIS_STYLE = dict(gridcolor="#21262d", linecolor="#30363d", tickfont=dict(color="#8b949e", size=10))
YAXIS_STYLE = dict(gridcolor="#21262d", linecolor="#30363d", tickfont=dict(color="#8b949e"))
LEGEND_H    = dict(orientation="h", y=1.02, font=dict(color="#c9d1d9", size=11), bgcolor="rgba(0,0,0,0)")
LEGEND_OFF  = dict(font=dict(color="#c9d1d9", size=11), bgcolor="rgba(0,0,0,0)")

RISK_COLOR = {"HIGH": "#f85149", "MEDIUM": "#d29922", "LOW": "#3fb950"}


def dark_fig(fig, height=400, legend="off", xangle=0, ytitle="", xtitle="", title=""):
    """Apply consistent dark styling to any figure without keyword conflicts."""
    fig.update_layout(
        **DARK_BASE,
        height=height,
        yaxis_title=ytitle,
        xaxis_title=xtitle,
        title=dict(text=title, font=dict(color="#f0f6fc", size=13)) if title else None,
        legend=(LEGEND_H if legend == "h" else LEGEND_OFF),
        showlegend=(legend != "off"),
    )
    fig.update_xaxes(**XAXIS_STYLE)
    fig.update_yaxes(**YAXIS_STYLE)
    if xangle:
        fig.update_xaxes(tickangle=xangle)
    return fig


# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "tariffs"   not in st.session_state:
    st.session_state.tariffs   = {k: v.copy() for k, v in DEFAULT_TARIFFS.items()}
if "ai_output" not in st.session_state:
    st.session_state.ai_output = ""
if "groq_key"  not in st.session_state:
    st.session_state.groq_key  = ""


# ── SAMPLE DATA ───────────────────────────────────────────────────────────────
@st.cache_data
def get_sample_data() -> pd.DataFrame:
    rows = [
        ("Electronic Control Modules",  "SinoTech Ltd.",   "China",       "Electronics",    2400,  38.50,  89.00),
        ("Steel Structural Tubing",     "CanSteel Corp.",  "Canada",      "Raw Materials",   850, 142.00, 198.00),
        ("Injection-Molded Housings",   "MexPlast SA",     "Mexico",      "Components",     5200,   8.20,  18.50),
        ("NAND Flash Memory",           "TaiwanChip Co.",  "Taiwan",      "Semiconductors",12000,   4.80,  12.00),
        ("Woven Fabric Rolls",          "VietTex Mfg.",    "Vietnam",     "Textiles",       3100,  22.40,  48.00),
        ("Precision Bearings",          "KugelGmbH",       "Germany",     "Industrial",     1800,  31.60,  67.00),
        ("Chemical Solvents",           "ChemCo Shanghai", "China",       "Chemicals",       920,  18.90,  39.00),
        ("Auto Wiring Harnesses",       "AutoMex SA",      "Mexico",      "Auto Parts",      640,  87.50, 158.00),
        ("LED Display Panels",          "BrightTech HK",   "China",       "Electronics",    1650,  62.00, 145.00),
        ("Pharmaceutical APIs",         "IndoPharma Ltd.", "India",       "Pharma",          430, 215.00, 520.00),
    ]
    return pd.DataFrame(rows, columns=[
        "product", "supplier", "country", "category",
        "monthly_units", "unit_cost_base", "selling_price",
    ])


# ── CALCULATION ENGINE ────────────────────────────────────────────────────────
def apply_tariffs(df: pd.DataFrame, tariffs: dict) -> pd.DataFrame:
    df = df.copy()
    df["current_tariff_pct"] = df["country"].map(lambda c: tariffs.get(c, {}).get("current", 0.0))
    df["new_tariff_pct"]     = df["country"].map(lambda c: tariffs.get(c, {}).get("new",     0.0))
    df["unit_cost_curr"]     = df["unit_cost_base"] * (1 + df["current_tariff_pct"] / 100)
    df["unit_cost_new"]      = df["unit_cost_base"] * (1 + df["new_tariff_pct"]     / 100)
    df["tariff_delta_pu"]    = df["unit_cost_new"] - df["unit_cost_curr"]
    df["margin_curr_pct"]    = ((df["selling_price"] - df["unit_cost_curr"]) / df["selling_price"] * 100).round(1)
    df["margin_new_pct"]     = ((df["selling_price"] - df["unit_cost_new"])  / df["selling_price"] * 100).round(1)
    df["margin_erosion"]     = (df["margin_curr_pct"] - df["margin_new_pct"]).round(1)
    df["annual_units"]       = df["monthly_units"] * 12
    df["annual_revenue"]     = (df["annual_units"] * df["selling_price"]).round(0)
    df["annual_margin_curr"] = (df["annual_units"] * (df["selling_price"] - df["unit_cost_curr"])).round(0)
    df["annual_margin_new"]  = (df["annual_units"] * (df["selling_price"] - df["unit_cost_new"])).round(0)
    df["annual_margin_loss"] = (df["annual_margin_curr"] - df["annual_margin_new"]).round(0)
    curr_mr = (df["selling_price"] - df["unit_cost_curr"]) / df["selling_price"]
    df["price_to_maintain"]  = (df["unit_cost_new"] / (1 - curr_mr)).round(2)
    df["price_increase_pct"] = ((df["price_to_maintain"] - df["selling_price"]) / df["selling_price"] * 100).round(1)

    def tier(row):
        if row["margin_new_pct"] <   0: return "HIGH"
        if row["margin_erosion"] >= 15: return "HIGH"
        if row["margin_erosion"] >=  5: return "MEDIUM"
        return "LOW"

    df["risk_tier"] = df.apply(tier, axis=1)
    return df


# ── AI ────────────────────────────────────────────────────────────────────────
def ask_groq(system: str, user: str, api_key: str) -> str:
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "temperature": 0.2,
                "max_tokens":  2000,
            },
            timeout=90,
        )
        if resp.status_code == 401:
            return "INVALID_KEY"
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"


def build_ai_prompt(df: pd.DataFrame, tariffs: dict) -> tuple:
    total_rev  = df["annual_revenue"].sum()
    total_loss = df["annual_margin_loss"].sum()
    high_n     = len(df[df["risk_tier"] == "HIGH"])
    neg_margin = df[df["margin_new_pct"] < 0]
    top5       = df.nlargest(5, "annual_margin_loss")
    top5_text  = "\n".join([
        f"  • {r.product} ({r.country}): {r.margin_curr_pct:.1f}%→{r.margin_new_pct:.1f}% | "
        f"Loss: ${r.annual_margin_loss:,.0f} | Price hike needed: +{r.price_increase_pct:.1f}%"
        for _, r in top5.iterrows()
    ])
    ctry_text  = "\n".join([
        f"  • {c}: ${v:,.0f}"
        for c, v in df.groupby("country")["annual_margin_loss"].sum().sort_values(ascending=False).items()
    ])
    active      = {c: v for c, v in tariffs.items() if v["new"] != v["current"]}
    tariff_text = "\n".join([
        f"  • {c}: {v['current']}%→{v['new']}% (+{v['new']-v['current']:.0f}pp)"
        for c, v in active.items()
    ])
    neg_text = (
        "\nLOSS-MAKING PRODUCTS:\n" +
        "\n".join([f"  • {r.product}: {r.margin_new_pct:.1f}%" for _, r in neg_margin.iterrows()])
    ) if len(neg_margin) > 0 else ""

    system = (
        "You are a senior supply chain strategy consultant specialising in trade policy and margin "
        "optimization. Provide precise, data-driven recommendations. Always cite specific numbers. "
        "Be direct — no padding, no vague statements."
    )
    user = f"""Analyse this portfolio's 2025 tariff exposure. DATE: {TODAY_STR}
PORTFOLIO: ${total_rev:,.0f} revenue | ${total_loss:,.0f} at risk ({total_loss/total_rev*100:.1f}%)
HIGH-RISK PRODUCTS: {high_n} of {len(df)}{neg_text}

TARIFF CHANGES:
{tariff_text}

TOP 5 WORST PRODUCTS:
{top5_text}

LOSS BY COUNTRY:
{ctry_text}

Respond in EXACTLY this format:

SITUATION ASSESSMENT:
[3-4 sentences on severity, worst exposure, core strategic risk]

IMMEDIATE ACTIONS — next 30 days:
1. [action | $ impact | owner]
2. [action | $ impact | owner]
3. [action | $ impact | owner]

PRICING STRATEGY:
[Which products can absorb increases? Which cannot? Cite names and numbers.]

SOURCING DIVERSIFICATION:
[Per HIGH-risk product: alternative country, expected tariff rate, net saving estimate.]

QUICK WINS vs STRUCTURAL CHANGES:
  Quick wins (0-4 weeks): [list]
  Medium term (1-6 months): [list]

LEADERSHIP DECISION:
[What must leadership decide in 2 weeks, and what happens if they delay?]"""
    return system, user


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding:8px 0 20px">
  <div style="font-size:0.6rem;text-transform:uppercase;letter-spacing:0.18em;color:#f85149;font-weight:600;margin-bottom:4px">TRADE INTELLIGENCE</div>
  <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.4rem;font-weight:600;color:#f0f6fc">TariffGuard</div>
  <div style="font-size:0.75rem;color:#8b949e;margin-top:2px">Tariff Exposure & Supplier Shift Simulator</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 14px;
     margin-bottom:16px;font-size:0.77rem;line-height:1.75;color:#8b949e">
<span style="color:#f85149;font-weight:600">2025 US Tariff Schedule</span><br>
China +120pp · Vietnam +46pp<br>Mexico +25pp · Canada +25pp<br>Taiwan +32pp · India +26pp
</div>
""", unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.12em;color:#8b949e;font-weight:600;margin-bottom:8px">DATA SOURCE</div>', unsafe_allow_html=True)
    src = st.radio("Source", ["Demo Portfolio (10 products)", "Upload your CSV"], label_visibility="collapsed")

    uploaded_df = None
    if src == "Upload your CSV":
        uf = st.file_uploader(
            "Columns: product, supplier, country, category, monthly_units, unit_cost_base, selling_price",
            type="csv",
        )
        if uf:
            uploaded_df = pd.read_csv(uf)
            st.success(f"✅ {len(uploaded_df)} products loaded")

    st.markdown("---")
    st.markdown('<div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.12em;color:#8b949e;font-weight:600;margin-bottom:8px">AI (GROQ — FREE)</div>', unsafe_allow_html=True)

    if "GROQ_API_KEY" in st.secrets:
        st.session_state.groq_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Key loaded from secrets")
    else:
        ki = st.text_input("Groq API Key", value=st.session_state.groq_key, type="password", placeholder="gsk_...")
        if ki:
            st.session_state.groq_key = ki
        if not st.session_state.groq_key:
            st.caption("Free at [console.groq.com](https://console.groq.com) — 2 min setup")

    st.markdown("---")
    with st.expander("Edit tariff rates"):
        sidebar_base = uploaded_df if uploaded_df is not None else get_sample_data()
        active_ctry  = sidebar_base["country"].unique().tolist()
        for country in DEFAULT_TARIFFS:
            if country in active_ctry:
                st.markdown(f"**{country}**")
                c1, c2 = st.columns(2)
                cur = c1.number_input("Now", 0.0, 300.0, float(st.session_state.tariffs[country]["current"]), 0.5, key=f"cur_{country}")
                nw  = c2.number_input("New", 0.0, 300.0, float(st.session_state.tariffs[country]["new"]),     0.5, key=f"new_{country}")
                st.session_state.tariffs[country] = {"current": cur, "new": nw}


# ── LOAD & CALCULATE ──────────────────────────────────────────────────────────
raw_df = uploaded_df if uploaded_df is not None else get_sample_data()
df     = apply_tariffs(raw_df, st.session_state.tariffs)

total_rev       = df["annual_revenue"].sum()
total_loss      = df["annual_margin_loss"].sum()
avg_erosion     = df["margin_erosion"].mean()
high_n          = len(df[df["risk_tier"] == "HIGH"])
neg_n           = len(df[df["margin_new_pct"] < 0])
worst_ctry      = df.groupby("country")["annual_margin_loss"].sum().idxmax()
worst_ctry_loss = df.groupby("country")["annual_margin_loss"].sum().max()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="padding:28px 0 8px">
  <div class="section-label">TARIFF IMPACT & SUPPLIER OPTIMIZATION</div>
  <h1 style="font-size:2rem;font-weight:600;margin:0;letter-spacing:-0.02em;color:#f0f6fc">TariffGuard</h1>
  <p style="color:#8b949e;font-size:0.9rem;margin-top:6px;max-width:640px">
    Quantifies how the 2025 US tariff escalation erodes product margins, then models the true cost
    of each strategic response — including the transition costs every other tool ignores.
  </p>
</div>
""", unsafe_allow_html=True)

with st.expander("📋 The problem this solves — and how", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
<div class="problem-card">
<div class="section-label" style="color:#f85149">THE INDUSTRY PROBLEM</div>
<p style="font-size:0.87rem;line-height:1.75;color:#c9d1d9;margin:0">
The 2025 tariff escalation hit mid-market manufacturers hardest. Large companies have trade
compliance teams and expensive software. Mid-market companies are making multi-million dollar
sourcing decisions in Excel spreadsheets.
<br><br>
The hard problem isn't knowing tariff rates — those are public. It's the
<strong style="color:#f85149">decision model</strong>: if I shift from China to Mexico,
my tariff drops but unit cost rises, lead time increases, I need extra safety stock, and I
face a 90-day PPAP re-qualification. What's my actual net saving?
</p>
</div>
""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
<div class="solution-card">
<div class="section-label" style="color:#3fb950">HOW TARIFFGUARD SOLVES IT</div>
<p style="font-size:0.87rem;line-height:1.75;color:#c9d1d9;margin:0">
TariffGuard builds the full decision model procurement teams need:
<br><br>
• <strong style="color:#f0f6fc">Exposure Dashboard</strong> — Annual tariff burden per product and country<br>
• <strong style="color:#f0f6fc">Scenario Modeling</strong> — Absorb vs Pass-Through vs Supplier Switch<br>
• <strong style="color:#f0f6fc">Transition Cost Model</strong> — PPAP + bridge inventory + production gap<br>
• <strong style="color:#f0f6fc">AI Optimization Brief</strong> — Specific actions with $ impact and ownership
<br><br>
The analysis a supply chain consultant charges
<strong style="color:#3fb950">$50K to produce</strong> — generated in seconds.
</p>
</div>
""", unsafe_allow_html=True)
    st.markdown("""
<div class="context-bar">
<strong style="color:#c9d1d9">Tariff context (2025 USTR):</strong>
China +120pp · Vietnam +46pp · Mexico +25pp · Canada +25pp · Taiwan +32pp · India +26pp.
The demo shows 3 China-sourced products going <strong style="color:#f85149">negative margin</strong> —
exactly what US importers are experiencing.
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── KPI STRIP ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Annual Revenue",       f"${total_rev / 1e6:.2f}M")
c2.metric("Margin $ at Risk",     f"${total_loss / 1e3:.0f}K",   delta=f"−{total_loss/total_rev*100:.1f}% of revenue", delta_color="inverse")
c3.metric("Avg Margin Erosion",   f"{avg_erosion:.1f}pp",        delta="vs current",                                    delta_color="inverse")
c4.metric("HIGH Risk Products",   f"{high_n} / {len(df)}",       delta=f"{neg_n} in negative margin",                   delta_color="inverse")
c5.metric("Biggest Country Loss", worst_ctry,                    delta=f"${worst_ctry_loss / 1e3:.0f}K/yr",             delta_color="inverse")

st.markdown("---")

# ── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Impact Dashboard",
    "🔢  Product Analysis",
    "🔮  Scenario Modeling",
    "🤖  AI Optimization",
    "📂  Data Preview",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMPACT DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    cl, cr = st.columns(2)

    with cl:
        bar_colors = [RISK_COLOR[t] for t in df["risk_tier"]]
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Current Margin %", x=df["product"].str[:18], y=df["margin_curr_pct"],
            marker_color="#1d4ed8", opacity=0.85,
        ))
        fig_bar.add_trace(go.Bar(
            name="New Margin %", x=df["product"].str[:18], y=df["margin_new_pct"],
            marker_color=bar_colors,
        ))
        fig_bar.add_hline(y=0, line_dash="dash", line_color="#f85149", opacity=0.6,
                          annotation_text="Zero margin", annotation_font_color="#8b949e")
        dark_fig(fig_bar, height=370, legend="h", xangle=-35,
                 ytitle="Gross Margin %",
                 title="Gross Margin: Current vs After Tariffs")
        fig_bar.update_layout(barmode="group")
        st.plotly_chart(fig_bar, use_container_width=True)

    with cr:
        by_ctry = df.groupby("country")["annual_margin_loss"].sum().sort_values(ascending=False)
        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute"] + ["relative"] * len(by_ctry) + ["total"],
            x=["Current Margin"] + list(by_ctry.index) + ["New Margin"],
            y=[df["annual_margin_curr"].sum()] + [-v for v in by_ctry.values] + [0],
            connector={"line": {"color": "#30363d", "width": 1}},
            increasing={"marker": {"color": "#3fb950"}},
            decreasing={"marker": {"color": "#f85149"}},
            totals={"marker":    {"color": "#6366f1"}},
            text=(
                [f"${df['annual_margin_curr'].sum() / 1e3:.0f}K"] +
                [f"−${v / 1e3:.0f}K" for v in by_ctry.values] +
                [f"${df['annual_margin_new'].sum() / 1e3:.0f}K"]
            ),
            textposition="outside",
            textfont=dict(color="#c9d1d9", size=11),
        ))
        dark_fig(fig_wf, height=370, legend="off", title="Annual Margin Erosion by Country")
        st.plotly_chart(fig_wf, use_container_width=True)

    fig_bubble = px.scatter(
        df, x="margin_erosion", y="margin_new_pct",
        size="annual_revenue", color="risk_tier",
        color_discrete_map=RISK_COLOR,
        hover_name="product",
        hover_data={"country": True, "annual_margin_loss": ":$,.0f", "risk_tier": False, "annual_revenue": False},
        labels={"margin_erosion": "Margin Erosion (pp)", "margin_new_pct": "New Gross Margin (%)"},
    )
    fig_bubble.add_hline(y=0,  line_dash="dash", line_color="#f85149", opacity=0.5,
                         annotation_text="Zero margin", annotation_font_color="#8b949e")
    fig_bubble.add_vline(x=5,  line_dash="dot",  line_color="#d29922", opacity=0.4,
                         annotation_text="Medium risk", annotation_font_color="#8b949e")
    fig_bubble.add_vline(x=15, line_dash="dot",  line_color="#f85149", opacity=0.4,
                         annotation_text="High risk",   annotation_font_color="#8b949e")
    dark_fig(fig_bubble, height=400, legend="h",
             title="Risk Matrix: Margin Erosion vs New Margin  (bubble = annual revenue)")
    st.plotly_chart(fig_bubble, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PRODUCT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-label">FULL PORTFOLIO — TARIFF IMPACT BY PRODUCT</div>', unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    risk_f = fc1.multiselect("Risk Tier", ["HIGH","MEDIUM","LOW"],        default=["HIGH","MEDIUM","LOW"])
    ctry_f = fc2.multiselect("Country",   sorted(df["country"].unique()), default=sorted(df["country"].unique()))
    sort_f = fc3.selectbox("Sort by", ["Annual Margin Loss ↓","Margin Erosion ↓","Revenue ↓"])

    filtered = df[df["risk_tier"].isin(risk_f) & df["country"].isin(ctry_f)].copy()
    sort_key  = {"Annual Margin Loss ↓":"annual_margin_loss","Margin Erosion ↓":"margin_erosion","Revenue ↓":"annual_revenue"}
    filtered  = filtered.sort_values(sort_key[sort_f], ascending=False)

    def cr_risk(v):
        return {"HIGH":"background:#3d1f1f;color:#f85149;font-weight:600",
                "MEDIUM":"background:#3d2f0f;color:#d29922;font-weight:600",
                "LOW":"background:#0f2d1f;color:#3fb950;font-weight:600"}.get(v, "")

    def cr_margin(v):
        return "background:#3d1f1f;color:#f85149;font-weight:700" if isinstance(v, float) and v < 0 else ""

    def cr_erosion(v):
        if isinstance(v, float):
            if v >= 15: return "color:#f85149;font-weight:600"
            if v >=  5: return "color:#d29922;font-weight:600"
        return ""

    disp_cols = ["product","supplier","country","category",
                 "current_tariff_pct","new_tariff_pct","unit_cost_curr","unit_cost_new","tariff_delta_pu",
                 "margin_curr_pct","margin_new_pct","margin_erosion",
                 "annual_revenue","annual_margin_loss","price_increase_pct","risk_tier"]
    rename = {"product":"Product","supplier":"Supplier","country":"Country","category":"Category",
              "current_tariff_pct":"Tariff Now %","new_tariff_pct":"Tariff New %",
              "unit_cost_curr":"Cost Now","unit_cost_new":"Cost New","tariff_delta_pu":"Extra/Unit",
              "margin_curr_pct":"Margin Now %","margin_new_pct":"Margin New %","margin_erosion":"Erosion pp",
              "annual_revenue":"Annual Rev","annual_margin_loss":"Annual Loss",
              "price_increase_pct":"Price Hike %","risk_tier":"Risk"}

    styled = (
        filtered[disp_cols].rename(columns=rename).style
        .map(cr_risk,    subset=["Risk"])
        .map(cr_margin,  subset=["Margin New %"])
        .map(cr_erosion, subset=["Erosion pp"])
        .format({"Tariff Now %":"{:.1f}%","Tariff New %":"{:.1f}%",
                 "Cost Now":"${:.2f}","Cost New":"${:.2f}","Extra/Unit":"${:.2f}",
                 "Margin Now %":"{:.1f}%","Margin New %":"{:.1f}%","Erosion pp":"{:.1f}",
                 "Annual Rev":"${:,.0f}","Annual Loss":"${:,.0f}","Price Hike %":"{:.1f}%"})
    )
    st.dataframe(styled, use_container_width=True, height=430)
    st.download_button("📥 Download CSV", df.to_csv(index=False), f"tariffguard_{date.today()}.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SCENARIO MODELING
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-label">THREE STRATEGIC RESPONSES — WITH FULL TRANSITION COSTS</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:#0d1117;border:1px solid #21262d;border-left:3px solid #d29922;border-radius:8px;
     padding:14px 20px;font-size:0.84rem;line-height:1.7;color:#c9d1d9;margin-bottom:16px">
<strong style="color:#f0f6fc">What makes this different:</strong> Most tariff tools stop at "switch to Country X and save $Y."
TariffGuard includes PPAP supplier qualification cost, bridge inventory carrying cost, and production gap risk
— the numbers that make or break the real decision.
</div>
""", unsafe_allow_html=True)

    with st.expander("⚙️ Configure scenarios", expanded=True):
        sp1, sp2, sp3 = st.columns(3)
        with sp1:
            st.markdown('<div style="color:#f0f6fc;font-weight:500;font-size:0.88rem;margin-bottom:8px">Scenario A — Partial Absorption</div>', unsafe_allow_html=True)
            absorb_pct = st.slider("% company absorbs", 0, 100, 50, 5)
            st.caption(f"You absorb {absorb_pct}%, customers pay {100 - absorb_pct}%")
        with sp2:
            st.markdown('<div style="color:#f0f6fc;font-weight:500;font-size:0.88rem;margin-bottom:8px">Scenario B — Full Pass-Through</div>', unsafe_allow_html=True)
            vol_hit = st.checkbox("10% volume loss on products needing >15% price increase", value=True)
            st.caption("Maintains margin %, risks customer volume")
        with sp3:
            st.markdown('<div style="color:#f0f6fc;font-weight:500;font-size:0.88rem;margin-bottom:8px">Scenario C — Supplier Switch</div>', unsafe_allow_html=True)
            alt_ctry     = st.selectbox("Switch HIGH-risk to", ["Mexico","India","Vietnam","Poland","Malaysia","Indonesia","Bangladesh"])
            alt_tariff   = st.number_input("Tariff in new country (%)", 0.0, 200.0,
                                           value=float(DEFAULT_TARIFFS.get(alt_ctry, {}).get("new", 20.0)), step=0.5)
            cost_premium = st.slider("Cost premium vs current (%)", -20, 60, 15, 1)
            ppap_days    = st.number_input("PPAP qualification days", 30, 180, 90)
            ppap_cost    = st.number_input("PPAP qualification cost ($)", 0, 200000, 28000, 1000)
            only_high    = st.checkbox("Apply only to HIGH-risk products", value=True)

    # ── Calculations ──────────────────────────────────────────────────────────
    sc = df.copy()

    # A — Partial absorption
    absorbed    = sc["unit_cost_curr"] + sc["tariff_delta_pu"] * (absorb_pct / 100)
    passed      = sc["tariff_delta_pu"] * ((100 - absorb_pct) / 100)
    new_price_a = sc["selling_price"] + passed
    sc["margin_a"] = ((new_price_a - absorbed) / new_price_a * 100).round(1)
    sc["loss_a"]   = (sc["annual_units"] * (sc["selling_price"] - absorbed) - sc["annual_margin_curr"]).abs().round(0)

    # B — Full pass-through
    sc["margin_b"] = sc["margin_curr_pct"]
    sc["loss_b"]   = 0.0
    if vol_hit:
        vol_adj      = sc["price_increase_pct"].apply(lambda p: 0.9 if p > 15 else 1.0)
        rev_b        = sc["annual_units"] * vol_adj * sc["price_to_maintain"]
        sc["loss_b"] = (sc["annual_revenue"] - rev_b).clip(lower=0).round(0)

    # C — Supplier switch
    mask         = (sc["risk_tier"] == "HIGH") if only_high else pd.Series(True, index=sc.index)
    new_base_c   = sc["unit_cost_base"] * (1 + cost_premium / 100)
    new_total_c  = new_base_c * (1 + alt_tariff / 100)
    sc["unit_cost_c"] = sc["unit_cost_new"]
    sc.loc[mask, "unit_cost_c"] = new_total_c[mask]
    sc["margin_c"] = ((sc["selling_price"] - sc["unit_cost_c"]) / sc["selling_price"] * 100).round(1)
    sc["loss_c"]   = (sc["annual_units"] * (sc["selling_price"] - sc["unit_cost_c"]) - sc["annual_margin_curr"]).abs().round(0)

    # Transition cost model
    n_high           = int(mask.sum())
    bridge_inv_cost  = float(df[mask]["annual_revenue"].sum() * 0.015 * (float(ppap_days) / 365))
    avg_new_t        = float(df[mask]["new_tariff_pct"].mean()) if n_high > 0 and df[mask]["new_tariff_pct"].mean() > 0 else 1.0
    gross_saving     = float(df[mask]["annual_margin_loss"].sum() * (1 - alt_tariff / avg_new_t)) if n_high > 0 else 0.0
    total_transition = float(ppap_cost) * n_high + bridge_inv_cost
    net_saving       = max(0.0, gross_saving - total_transition)
    breakeven_mo     = (total_transition / max(gross_saving / 12.0, 1.0)) if gross_saving > 0 else 999.0

    st.markdown("---")
    st.markdown('<div class="section-label">TRANSITION COST MODEL — WHAT MOST TOOLS MISS</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="transition-box">'
        f'Switching <strong>{n_high}</strong> HIGH-risk product(s) to <strong>{alt_ctry}</strong>: '
        f'PPAP re-qualification ${ppap_cost:,} × {n_high} = <strong>${ppap_cost * n_high:,}</strong> | '
        f'Bridge inventory ({int(ppap_days)} days) = <strong>${bridge_inv_cost:,.0f}</strong> | '
        f'<strong>Total transition: ${total_transition:,.0f}</strong><br>'
        f'Gross saving post-switch: ${gross_saving:,.0f}/yr → '
        f'<strong>Net annual saving: ${net_saving:,.0f}/yr</strong> | '
        f'Break-even: <strong>{breakeven_mo:.1f} months</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown('<div class="section-label">FINANCIAL OUTCOME COMPARISON</div>', unsafe_allow_html=True)
    baseline_m = df["annual_margin_curr"].sum()
    c_base, ca, cb, cc = st.columns(4)
    c_base.metric("Baseline (no action)",     f"${df['annual_margin_new'].sum() / 1e3:.0f}K", delta=f"−${total_loss / 1e3:.0f}K",                                                             delta_color="inverse")
    ca.metric(    f"A: {absorb_pct}% Absorb", f"${(baseline_m - sc['loss_a'].sum()) / 1e3:.0f}K", delta=f"{(baseline_m - sc['loss_a'].sum()) / baseline_m * 100:.1f}% retained")
    cb.metric(    "B: Pass-Through",          f"${(baseline_m - sc['loss_b'].sum()) / 1e3:.0f}K", delta=f"{(baseline_m - sc['loss_b'].sum()) / baseline_m * 100:.1f}% retained")
    cc.metric(    f"C: Switch → {alt_ctry}",  f"${(baseline_m - sc['loss_c'].sum()) / 1e3:.0f}K", delta=f"Break-even {breakeven_mo:.1f} mo")

    scenario_df = pd.DataFrame({
        "Product":  df["product"].str[:16].tolist() * 4,
        "Scenario": (
            ["Baseline"]                 * len(df) +
            [f"A: {absorb_pct}% Absorb"] * len(df) +
            ["B: Pass-Through"]           * len(df) +
            [f"C: → {alt_ctry}"]          * len(df)
        ),
        "Margin %": (
            df["margin_new_pct"].tolist() +
            sc["margin_a"].tolist() +
            sc["margin_b"].tolist() +
            sc["margin_c"].tolist()
        ),
    })
    fig_sc = px.bar(
        scenario_df, x="Product", y="Margin %", color="Scenario", barmode="group",
        color_discrete_sequence=["#484f58","#1d4ed8","#3fb950","#8b5cf6"],
    )
    fig_sc.add_hline(y=0, line_dash="dash", line_color="#f85149", opacity=0.5,
                     annotation_text="Zero margin", annotation_font_color="#8b949e")
    dark_fig(fig_sc, height=400, legend="h", xangle=-35,
             ytitle="Gross Margin %", title="Gross Margin % by Product — All Scenarios")
    st.plotly_chart(fig_sc, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-label">AI OPTIMIZATION ROADMAP</div>', unsafe_allow_html=True)
    st.markdown("""
<p style="color:#8b949e;font-size:0.84rem;margin-bottom:16px;max-width:700px">
Groq AI (Llama 3.1, free) reads your live portfolio — actual product names, margin figures,
country exposure — and returns the same structured roadmap a supply chain consultant delivers
at $50K/engagement. Specific product names, $ figures, and ownership included.
</p>
""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Portfolio exposure**\n\n${total_loss / 1e3:.0f}K margin at risk\n\n{high_n} HIGH-risk products\n\n{neg_n} in negative margin")
    c2.markdown("**Pricing analysis**\n\nWhich products can absorb\n\nVolume risk per product\n\nBlended revenue scenarios")
    c3.markdown("**Sourcing alternatives**\n\nCountry recommendations\n\nCost vs tariff trade-offs\n\nTransition cost estimates")

    st.markdown("---")

    if not st.session_state.groq_key:
        st.warning("Add your free Groq API key in the sidebar to generate the AI brief. Free at console.groq.com — no credit card required.")
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
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.download_button(
                "📥 Download AI Report (.txt)",
                st.session_state.ai_output,
                f"tariffguard_report_{date.today()}.txt",
                "text/plain",
                use_container_width=True,
            )
            if c2.button("🔄 Regenerate", use_container_width=True):
                st.session_state.ai_output = ""
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — DATA PREVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="section-label">DEMO DATA — RAW INPUTS</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:#0d1117;border:1px solid #21262d;border-left:3px solid #58a6ff;
     border-radius:8px;padding:14px 20px;font-size:0.84rem;line-height:1.7;
     color:#c9d1d9;margin-bottom:16px">
<strong style="color:#f0f6fc">What you're looking at:</strong>
10 products across 8 countries, representative of a mid-market manufacturer's import portfolio.
<code style="background:#161b22;padding:1px 6px;border-radius:4px;font-size:0.78rem">unit_cost_base</code> is the
import cost <em>before</em> any tariff — all margin and erosion figures derive transparently from this field.
Three China-sourced products (Electronic Control Modules, Chemical Solvents, LED Display Panels)
go <strong style="color:#f85149">negative margin</strong> under 145% tariffs — replicating the exact
situation US importers face in 2025.
<br><br>
To run TariffGuard on your own data, upload a CSV in the sidebar with the same column names.
</div>
""", unsafe_allow_html=True)

    # ── Raw input data ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:4px">RAW INPUT TABLE</div>', unsafe_allow_html=True)
    input_cols = ["product", "supplier", "country", "category", "monthly_units", "unit_cost_base", "selling_price"]
    input_rename = {
        "product": "Product", "supplier": "Supplier", "country": "Country",
        "category": "Category", "monthly_units": "Monthly Units",
        "unit_cost_base": "Unit Cost (pre-tariff)", "selling_price": "Selling Price",
    }

    def hi_country(v):
        high_tariff = {"China", "Vietnam", "Taiwan", "India", "Germany", "Japan", "South Korea", "Brazil"}
        usmca       = {"Mexico", "Canada"}
        if v in {"China"}: return "background:#3d1f1f;color:#f85149;font-weight:600"
        if v in high_tariff - {"China"}: return "background:#3d2f0f;color:#d29922;font-weight:600"
        if v in usmca:  return "background:#0f2d1f;color:#3fb950;font-weight:600"
        return ""

    st.dataframe(
        raw_df[input_cols].rename(columns=input_rename).style
        .map(hi_country, subset=["Country"])
        .format({"Unit Cost (pre-tariff)": "${:.2f}", "Selling Price": "${:.2f}",
                 "Monthly Units": "{:,}"}),
        use_container_width=True,
        hide_index=True,
    )

    # ── Tariff schedule ────────────────────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:20px">TARIFF SCHEDULE (CURRENT VS 2025 NEW RATES)</div>', unsafe_allow_html=True)

    active_countries = raw_df["country"].unique().tolist()
    tariff_rows = []
    for c, v in st.session_state.tariffs.items():
        if c in active_countries:
            delta = v["new"] - v["current"]
            products_in_country = raw_df[raw_df["country"] == c]["product"].tolist()
            tariff_rows.append({
                "Country":          c,
                "Current Rate":     f"{v['current']:.1f}%",
                "New Rate":         f"{v['new']:.1f}%",
                "Change":           f"+{delta:.0f}pp" if delta > 0 else f"{delta:.0f}pp",
                "Affected Products": len(products_in_country),
                "Risk":             "HIGH" if delta >= 40 else ("MEDIUM" if delta >= 15 else "LOW"),
            })
    tariff_df = pd.DataFrame(tariff_rows).sort_values("Affected Products", ascending=False)

    def style_tariff_risk(v):
        return {"HIGH": "background:#3d1f1f;color:#f85149;font-weight:600",
                "MEDIUM": "background:#3d2f0f;color:#d29922;font-weight:600",
                "LOW": "background:#0f2d1f;color:#3fb950;font-weight:600"}.get(v, "")

    def style_change(v):
        try:
            num = float(v.replace("pp","").replace("+",""))
            if num >= 40: return "color:#f85149;font-weight:600;font-family:'IBM Plex Mono',monospace"
            if num >= 15: return "color:#d29922;font-weight:600;font-family:'IBM Plex Mono',monospace"
        except Exception:
            pass
        return "font-family:'IBM Plex Mono',monospace"

    st.dataframe(
        tariff_df.style
        .map(style_tariff_risk, subset=["Risk"])
        .map(style_change,      subset=["Change"]),
        use_container_width=True,
        hide_index=True,
    )

    # ── Calculated fields ──────────────────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:20px">CALCULATED OUTPUT — ALL DERIVED FIELDS</div>', unsafe_allow_html=True)
    st.markdown("""
<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;
     padding:10px 16px;font-size:0.78rem;color:#8b949e;margin-bottom:12px">
Every column below is derived from <code style="color:#c9d1d9">unit_cost_base × (1 + tariff%)</code>.
No hidden assumptions. Margin erosion, annual loss, and price-hike calculations are fully auditable.
</div>
""", unsafe_allow_html=True)

    calc_cols = ["product", "country", "current_tariff_pct", "new_tariff_pct",
                 "unit_cost_curr", "unit_cost_new", "tariff_delta_pu",
                 "margin_curr_pct", "margin_new_pct", "margin_erosion",
                 "annual_revenue", "annual_margin_loss", "price_increase_pct", "risk_tier"]
    calc_rename = {
        "product": "Product", "country": "Country",
        "current_tariff_pct": "Tariff Now %", "new_tariff_pct": "Tariff New %",
        "unit_cost_curr": "Cost Now", "unit_cost_new": "Cost New",
        "tariff_delta_pu": "Extra/Unit", "margin_curr_pct": "Margin Now %",
        "margin_new_pct": "Margin New %", "margin_erosion": "Erosion pp",
        "annual_revenue": "Annual Revenue", "annual_margin_loss": "Annual Loss",
        "price_increase_pct": "Price Hike %", "risk_tier": "Risk",
    }

    def cr_risk2(v):
        return {"HIGH": "background:#3d1f1f;color:#f85149;font-weight:600",
                "MEDIUM": "background:#3d2f0f;color:#d29922;font-weight:600",
                "LOW": "background:#0f2d1f;color:#3fb950;font-weight:600"}.get(v, "")

    def cr_margin2(v):
        return "background:#3d1f1f;color:#f85149;font-weight:700" if isinstance(v, float) and v < 0 else ""

    st.dataframe(
        df[calc_cols].rename(columns=calc_rename)
        .sort_values("Annual Loss", ascending=False)
        .style
        .map(cr_risk2,   subset=["Risk"])
        .map(cr_margin2, subset=["Margin New %"])
        .format({
            "Tariff Now %": "{:.1f}%", "Tariff New %": "{:.1f}%",
            "Cost Now": "${:.2f}", "Cost New": "${:.2f}", "Extra/Unit": "${:.2f}",
            "Margin Now %": "{:.1f}%", "Margin New %": "{:.1f}%", "Erosion pp": "{:.1f}",
            "Annual Revenue": "${:,.0f}", "Annual Loss": "${:,.0f}", "Price Hike %": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    # ── Download section ───────────────────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:20px">DOWNLOADS</div>', unsafe_allow_html=True)
    dl1, dl2, dl3 = st.columns(3)

    dl1.download_button(
        "📥 Raw Input Data (CSV)",
        raw_df[input_cols].to_csv(index=False),
        "tariffguard_inputs.csv",
        "text/csv",
        use_container_width=True,
        help="The base product data — use this as a template for your own upload",
    )
    dl2.download_button(
        "📥 Full Calculated Output (CSV)",
        df.to_csv(index=False),
        f"tariffguard_output_{date.today()}.csv",
        "text/csv",
        use_container_width=True,
        help="All derived fields: tariff costs, margin erosion, annual loss, risk tier",
    )
    dl3.download_button(
        "📥 Tariff Schedule (CSV)",
        tariff_df.to_csv(index=False),
        "tariffguard_tariff_schedule.csv",
        "text/csv",
        use_container_width=True,
        help="Current vs new tariff rates for all countries in this portfolio",
    )

    st.markdown("""
<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;
     padding:12px 16px;font-size:0.78rem;color:#8b949e;margin-top:12px;line-height:1.7">
<strong style="color:#c9d1d9">CSV template format for your own data:</strong><br>
<code style="color:#58a6ff">product, supplier, country, category, monthly_units, unit_cost_base, selling_price</code><br>
Country names must match the tariff schedule exactly (e.g. "China", "Mexico", "Germany").
Unknown countries default to 0% tariff. All other columns are calculated automatically.
</div>
""", unsafe_allow_html=True)


# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='font-size:0.72rem;color:#484f58;text-align:center'>"
    "TariffGuard · Tariff Exposure & Supplier Shift Simulator · "
    "AI by Groq (Llama 3.1, free) · 2025 USTR tariff schedule · "
    "Built by Rutwik Satish · MS Engineering Management, Northeastern University"
    "</p>",
    unsafe_allow_html=True,
)
