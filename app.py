"""
TariffGuard: Supply Chain Tariff Impact & Margin Optimization
=============================================================
Quantifies how the 2025 US tariff escalation erodes product margins
and revenue, then uses AI to recommend specific optimization strategies.

Why it exists:
  China +120pp, Vietnam +46pp, Mexico +25pp, Canada +25pp.
  These are the largest tariff increases in modern US trade history.
  Supply chain teams need to quantify impact fast — this tool does that.

Features:
  1. Impact Dashboard     — margin erosion by product + waterfall + risk matrix
  2. Product Analysis     — full portfolio table with color-coded risk tiers
  3. Scenario Modeling    — compare Absorb vs Pass-Through vs Supplier Switch
  4. AI Optimization      — Groq AI reads live data, returns specific actions

AI:    Groq API (free — llama-3.1-8b-instant, no credit card)
Stack: Python · Streamlit · Plotly · Pandas · Requests
Author: Rutwik Satish | MS Engineering Management, Northeastern University
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import date

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
TODAY      = date.today().strftime("%B %d, %Y")

# 2025 US tariff schedule — current = already baked into cost, new = announced rate
# Sources: USTR announcements Jan–Apr 2025
DEFAULT_TARIFFS = {
    "China":       {"current": 25.0,  "new": 145.0},
    "Mexico":      {"current": 0.0,   "new": 25.0},
    "Canada":      {"current": 0.0,   "new": 25.0},
    "Vietnam":     {"current": 0.0,   "new": 46.0},
    "India":       {"current": 0.0,   "new": 26.0},
    "Germany":     {"current": 0.0,   "new": 20.0},
    "Taiwan":      {"current": 0.0,   "new": 32.0},
    "Japan":       {"current": 0.0,   "new": 24.0},
    "South Korea": {"current": 0.0,   "new": 25.0},
    "Brazil":      {"current": 0.0,   "new": 10.0},
}

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TariffGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.ai-output {
    background: #fefefe;
    border: 0.5px solid #e0e0dc;
    border-left: 3px solid #534AB7;
    border-radius: 8px;
    padding: 20px 26px;
    font-size: 14px;
    line-height: 1.85;
    white-space: pre-wrap;
    word-break: break-word;
}
.scenario-card {
    border: 0.5px solid #e0e0dc;
    border-radius: 10px;
    padding: 16px 18px;
    height: 100%;
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
if "df"        not in st.session_state: st.session_state.df        = None
if "tariffs"   not in st.session_state: st.session_state.tariffs   = {k: v.copy() for k, v in DEFAULT_TARIFFS.items()}
if "ai_output" not in st.session_state: st.session_state.ai_output = ""
if "groq_key"  not in st.session_state: st.session_state.groq_key  = ""

# ─── SAMPLE DATA ──────────────────────────────────────────────────────────────
def get_sample_data() -> pd.DataFrame:
    """
    10 realistic products spanning major high-tariff countries.
    unit_cost_base = import cost BEFORE any tariff duty.
    All math derives from this — transparent and auditable.

    Key story in the data:
      3 China products (Electronics, Chemicals, LED Panels) go NEGATIVE MARGIN
      under 145% tariffs — which is exactly what US importers are facing in 2025.
    """
    rows = [
        # product, supplier, country, category, monthly_units, unit_cost_base($), selling_price($)
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
    return pd.DataFrame(rows, columns=[
        "product", "supplier", "country", "category",
        "monthly_units", "unit_cost_base", "selling_price",
    ])

# ─── CORE CALCULATION ENGINE ──────────────────────────────────────────────────
def apply_tariffs(df: pd.DataFrame, tariffs: dict) -> pd.DataFrame:
    """
    Derives all financial impact metrics from base cost + tariff rates.

    Tariff math:
      unit_cost_curr = unit_cost_base × (1 + current_tariff%)
        → what the company pays TODAY (tariff already in their books)
      unit_cost_new  = unit_cost_base × (1 + new_tariff%)
        → what they'll pay AFTER new tariff takes effect
      tariff_delta   = unit_cost_new − unit_cost_curr
        → the extra cost per unit from the tariff change
    """
    df = df.copy()

    # Map tariff rates
    df["current_tariff_pct"] = df["country"].map(
        lambda c: tariffs.get(c, {}).get("current", 0.0))
    df["new_tariff_pct"] = df["country"].map(
        lambda c: tariffs.get(c, {}).get("new", 0.0))

    # Unit costs
    df["unit_cost_curr"]  = df["unit_cost_base"] * (1 + df["current_tariff_pct"] / 100)
    df["unit_cost_new"]   = df["unit_cost_base"] * (1 + df["new_tariff_pct"]     / 100)
    df["tariff_delta_pu"] = df["unit_cost_new"]  - df["unit_cost_curr"]

    # Gross margins
    df["margin_curr_pct"] = ((df["selling_price"] - df["unit_cost_curr"]) / df["selling_price"] * 100).round(1)
    df["margin_new_pct"]  = ((df["selling_price"] - df["unit_cost_new"])  / df["selling_price"] * 100).round(1)
    df["margin_erosion"]  = (df["margin_curr_pct"] - df["margin_new_pct"]).round(1)

    # Annual financials
    df["annual_units"]       = df["monthly_units"] * 12
    df["annual_revenue"]     = (df["annual_units"] * df["selling_price"]).round(0)
    df["annual_margin_curr"] = (df["annual_units"] * (df["selling_price"] - df["unit_cost_curr"])).round(0)
    df["annual_margin_new"]  = (df["annual_units"] * (df["selling_price"] - df["unit_cost_new"])).round(0)
    df["annual_margin_loss"] = (df["annual_margin_curr"] - df["annual_margin_new"]).round(0)

    # Risk tier — products going negative margin are automatically HIGH
    def tier(row):
        if row["margin_new_pct"] < 0:    return "HIGH"
        if row["margin_erosion"] >= 15:  return "HIGH"
        if row["margin_erosion"] >= 5:   return "MEDIUM"
        return "LOW"
    df["risk_tier"] = df.apply(tier, axis=1)

    # Pass-through price (raise prices to maintain current margin exactly)
    curr_margin_rate = (df["selling_price"] - df["unit_cost_curr"]) / df["selling_price"]
    df["price_to_maintain"] = (df["unit_cost_new"] / (1 - curr_margin_rate)).round(2)
    df["price_increase_pct"] = (
        (df["price_to_maintain"] - df["selling_price"]) / df["selling_price"] * 100
    ).round(1)

    return df

# ─── GROQ AI HELPER ───────────────────────────────────────────────────────────
def ask_groq(system: str, user: str, api_key: str) -> str:
    """
    Calls Groq's free LLM API.
    Free tier: 30 requests/min, 14,400 requests/day — more than enough.
    Get a key at console.groq.com — no credit card required.
    """
    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       GROQ_MODEL,
                "messages":    [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "temperature": 0.2,
                "max_tokens":  2000,
            },
            timeout=90,
        )
        if resp.status_code == 401: return "INVALID_KEY"
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "CONNECTION_ERROR"
    except Exception as e:
        return f"ERROR: {e}"


def build_ai_prompt(df: pd.DataFrame, tariffs: dict) -> tuple:
    """Packages live calculation data into a structured AI analysis prompt."""
    total_rev   = df["annual_revenue"].sum()
    total_loss  = df["annual_margin_loss"].sum()
    avg_erosion = df["margin_erosion"].mean()
    high_n      = len(df[df["risk_tier"] == "HIGH"])
    neg_margin  = df[df["margin_new_pct"] < 0]

    # Top 5 worst products
    top5 = df.nlargest(5, "annual_margin_loss")
    top5_text = "\n".join([
        f"  • {r.product} ({r.country}): "
        f"margin {r.margin_curr_pct:.1f}% → {r.margin_new_pct:.1f}% "
        f"(−{r.margin_erosion:.1f}pp) | "
        f"Annual loss: ${r.annual_margin_loss:,.0f} | "
        f"Full pass-through requires +{r.price_increase_pct:.1f}% price increase"
        for _, r in top5.iterrows()
    ])

    # Country breakdown
    by_ctry = df.groupby("country")["annual_margin_loss"].sum().sort_values(ascending=False)
    ctry_text = "\n".join([f"  • {c}: ${v:,.0f}" for c, v in by_ctry.items()])

    # Active tariff changes
    active = {c: v for c, v in tariffs.items() if v["new"] != v["current"]}
    tariff_text = "\n".join([
        f"  • {c}: {v['current']}% → {v['new']}% (+{v['new']-v['current']:.0f}pp)"
        for c, v in active.items()
    ])

    neg_text = ""
    if len(neg_margin) > 0:
        neg_text = "\nPRODUCTS NOW IN NEGATIVE MARGIN (loss-making at current prices):\n" + \
            "\n".join([f"  • {r.product}: {r.margin_new_pct:.1f}%" for _, r in neg_margin.iterrows()])

    system = (
        "You are a senior supply chain strategy consultant specialising in trade policy "
        "and margin optimization. You provide precise, data-driven recommendations. "
        "You always cite specific numbers from the data provided. "
        "You distinguish between immediate tactical actions and structural changes. "
        "You are direct — no padding, no vague statements like 'consider reviewing'."
    )

    user = f"""Analyse this supply chain portfolio's 2025 tariff exposure and provide a specific optimization roadmap.

DATE: {TODAY}
PORTFOLIO SUMMARY:
  Total Annual Revenue:       ${total_rev:,.0f}
  Total Annual Margin at Risk:${total_loss:,.0f}  ({total_loss/total_rev*100:.1f}% of revenue)
  Average Margin Erosion:     {avg_erosion:.1f} percentage points
  HIGH-Risk Products:         {high_n} of {len(df)}
{neg_text}

TARIFF CHANGES IN EFFECT:
{tariff_text}

TOP 5 WORST-AFFECTED PRODUCTS:
{top5_text}

ANNUAL MARGIN LOSS BY COUNTRY:
{ctry_text}

Respond in EXACTLY this format:

SITUATION ASSESSMENT:
[3-4 sentences. How severe is this? Which part of the portfolio is most exposed? What's the core strategic risk?]

IMMEDIATE ACTIONS — next 30 days (numbered, each with specific $ impact):
1. [action | expected $ impact | who owns it]
2. [action | expected $ impact | who owns it]
3. [action | expected $ impact | who owns it]

PRICING STRATEGY:
[Which specific products from the data above can absorb a price increase without losing customers? Which cannot? What blended revenue impact would a 50% pass-through have? Cite product names and numbers.]

SOURCING DIVERSIFICATION — by product:
[For each HIGH-risk product, recommend a specific alternative country, the expected new tariff rate, and whether the cost savings outweigh the transition cost. Be concrete.]

MARGIN DEFENCE QUICK WINS vs STRUCTURAL CHANGES:
  Quick wins (0–4 weeks): [specific list]
  Medium term (1–6 months): [specific list]
  Long term (6–18 months): [specific list]

LEADERSHIP DECISION REQUIRED:
[One focused paragraph: what decision must leadership make in the next 2 weeks, and what happens if they delay?]"""

    return system, user

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🛡️ TariffGuard")
    st.caption("Supply Chain Tariff Impact & Optimization")
    st.divider()

    # ── AI key ──────────────────────────────────────────────────────────────
    st.markdown("### 🤖 AI (Groq — free)")
    if "GROQ_API_KEY" in st.secrets:
        st.session_state.groq_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Key loaded from Streamlit secrets")
    else:
        ki = st.text_input(
            "Groq API Key",
            value=st.session_state.groq_key,
            type="password",
            placeholder="gsk_...",
        )
        if ki: st.session_state.groq_key = ki
        if not st.session_state.groq_key:
            st.caption("Free key at [console.groq.com](https://console.groq.com) — 2 min setup")

    st.divider()

    # ── Data source ──────────────────────────────────────────────────────────
    st.markdown("### 📂 Data")
    src = st.radio("Source", ["Sample Portfolio (10 products)", "Upload CSV"],
                   label_visibility="collapsed")

    if src == "Upload CSV":
        uf = st.file_uploader(
            "Columns needed: product, supplier, country, category, "
            "monthly_units, unit_cost_base, selling_price",
            type="csv",
        )
        if uf:
            st.session_state.df = pd.read_csv(uf)
            st.success(f"✅ {len(st.session_state.df)} products loaded")
    else:
        if st.button("▶ Load Sample Data", type="primary", use_container_width=True):
            st.session_state.df = get_sample_data()
            st.session_state.ai_output = ""
            st.success("✅ Sample data loaded")

    # ── Tariff config ────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📋 Tariff Rates (%)")
    st.caption("Edit current vs new rates per country.")

    active_countries = []
    if st.session_state.df is not None:
        active_countries = st.session_state.df["country"].unique().tolist()

    with st.expander("Edit rates", expanded=False):
        for country in DEFAULT_TARIFFS:
            if not active_countries or country in active_countries:
                st.markdown(f"**{country}**")
                c1, c2 = st.columns(2)
                cur = c1.number_input(
                    f"Current", 0.0, 300.0,
                    value=float(st.session_state.tariffs[country]["current"]),
                    step=0.5, key=f"cur_{country}",
                )
                nw = c2.number_input(
                    f"New", 0.0, 300.0,
                    value=float(st.session_state.tariffs[country]["new"]),
                    step=0.5, key=f"new_{country}",
                )
                st.session_state.tariffs[country] = {"current": cur, "new": nw}

# ─── LANDING ──────────────────────────────────────────────────────────────────
if st.session_state.df is None:
    st.markdown("# 🛡️ TariffGuard")
    st.markdown("### Supply Chain Tariff Impact & Margin Optimization Platform")
    st.info("👈 Click **Load Sample Data** in the sidebar to run a live analysis.")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown("**📊 Impact Dashboard**\n\nMargin erosion by product, country waterfall, risk matrix.")
    c2.markdown("**🔢 Product Analysis**\n\nFull portfolio table — current vs new margin, annual $ loss.")
    c3.markdown("**🔮 Scenario Modeling**\n\nCompare Absorb, Pass-Through, and Supplier Switch strategies.")
    c4.markdown("**🤖 AI Optimization**\n\nGroq AI reads your live data and returns a specific action plan.")

    st.divider()
    st.markdown("""
> **2025 tariff context:** China +120pp · Vietnam +46pp · Mexico +25pp · Canada +25pp  
> These are the largest tariff increases in modern US trade history.  
> For US importers, the question is no longer *whether* margins will shrink — it's *how fast* and *what to do*.
    """)
    st.stop()

# ─── CALCULATE ────────────────────────────────────────────────────────────────
df = apply_tariffs(st.session_state.df, st.session_state.tariffs)

# ─── TOP KPI BAR ──────────────────────────────────────────────────────────────
st.markdown("# 🛡️ TariffGuard")
st.caption(f"{TODAY}  ·  {len(df)} products  ·  {df['country'].nunique()} countries")

total_rev        = df["annual_revenue"].sum()
total_loss       = df["annual_margin_loss"].sum()
avg_erosion      = df["margin_erosion"].mean()
high_n           = len(df[df["risk_tier"] == "HIGH"])
neg_margin_n     = len(df[df["margin_new_pct"] < 0])
worst_ctry       = df.groupby("country")["annual_margin_loss"].sum().idxmax()
worst_ctry_loss  = df.groupby("country")["annual_margin_loss"].sum().max()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Annual Revenue",       f"${total_rev/1e6:.2f}M")
k2.metric("Margin $ at Risk",     f"${total_loss/1e3:.0f}K",
          delta=f"−{total_loss/total_rev*100:.1f}% of revenue",
          delta_color="inverse")
k3.metric("Avg Margin Erosion",   f"{avg_erosion:.1f}pp",
          delta_color="inverse", delta="vs current")
k4.metric("HIGH Risk Products",   f"{high_n} / {len(df)}",
          delta=f"{neg_margin_n} in negative margin",
          delta_color="inverse")
k5.metric("Biggest Exposure",     worst_ctry,
          delta=f"${worst_ctry_loss/1e3:.0f}K annual loss",
          delta_color="inverse")

st.divider()

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Impact Dashboard",
    "🔢 Product Analysis",
    "🔮 Scenario Modeling",
    "🤖 AI Optimization",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMPACT DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    cl, cr = st.columns(2)

    with cl:
        # Grouped bar: current vs new margin per product
        RISK_COLOR = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}
        bar_cols   = [RISK_COLOR[t] for t in df["risk_tier"]]
        labels     = df["product"].str[:20]

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name="Current Margin %", x=labels, y=df["margin_curr_pct"],
            marker_color="#93c5fd", opacity=0.9,
        ))
        fig_bar.add_trace(go.Bar(
            name="New Margin %", x=labels, y=df["margin_new_pct"],
            marker_color=bar_cols,
        ))
        fig_bar.add_hline(y=0, line_dash="dash", line_color="#dc2626",
                          opacity=0.6, annotation_text="Zero margin")
        fig_bar.update_layout(
            title="Gross Margin: Current vs New",
            barmode="group", yaxis_title="Gross Margin %",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=370, margin=dict(l=0, r=0, t=44, b=80),
        )
        fig_bar.update_xaxes(tickangle=-35, tickfont_size=10)
        st.plotly_chart(fig_bar, use_container_width=True)

    with cr:
        # Waterfall: annual margin erosion by country
        by_ctry = (df.groupby("country")["annual_margin_loss"]
                     .sum().sort_values(ascending=False))

        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute"] + ["relative"] * len(by_ctry) + ["total"],
            x=["Current Margin $"] + list(by_ctry.index) + ["New Margin $"],
            y=[df["annual_margin_curr"].sum()] + [-v for v in by_ctry.values] + [0],
            connector={"line": {"color": "#d1d5db", "width": 1}},
            increasing={"marker": {"color": "#22c55e"}},
            decreasing={"marker": {"color": "#ef4444"}},
            totals={"marker":    {"color": "#6366f1"}},
            text=(
                [f"${df['annual_margin_curr'].sum()/1e3:.0f}K"]
                + [f"−${v/1e3:.0f}K" for v in by_ctry.values]
                + [f"${df['annual_margin_new'].sum()/1e3:.0f}K"]
            ),
            textposition="outside",
        ))
        fig_wf.update_layout(
            title="Annual Margin Erosion by Country ($)",
            yaxis_title="Annual Gross Margin ($)",
            height=370, margin=dict(l=0, r=0, t=44, b=44),
            showlegend=False,
        )
        st.plotly_chart(fig_wf, use_container_width=True)

    # Risk matrix bubble chart
    fig_bubble = px.scatter(
        df,
        x="margin_erosion",
        y="margin_new_pct",
        size="annual_revenue",
        color="risk_tier",
        color_discrete_map=RISK_COLOR,
        hover_name="product",
        hover_data={
            "country": True,
            "annual_margin_loss": ":$,.0f",
            "risk_tier": False,
            "annual_revenue": False,
        },
        labels={
            "margin_erosion": "Margin Erosion (percentage points)",
            "margin_new_pct": "New Gross Margin (%)",
        },
        title="Risk Matrix: Margin Erosion vs New Margin Level  (bubble size = annual revenue)",
    )
    fig_bubble.add_hline(y=0,  line_dash="dash", line_color="#dc2626",
                         opacity=0.5, annotation_text="Zero margin line")
    fig_bubble.add_vline(x=5,  line_dash="dot",  line_color="#f59e0b",
                         opacity=0.4, annotation_text="Medium risk")
    fig_bubble.add_vline(x=15, line_dash="dot",  line_color="#ef4444",
                         opacity=0.4, annotation_text="High risk")
    fig_bubble.update_layout(height=400, margin=dict(l=0, r=0, t=44, b=0))
    st.plotly_chart(fig_bubble, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PRODUCT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Full Portfolio — Tariff Impact by Product")

    fc1, fc2, fc3 = st.columns(3)
    risk_f = fc1.multiselect("Risk Tier", ["HIGH","MEDIUM","LOW"],
                             default=["HIGH","MEDIUM","LOW"])
    ctry_f = fc2.multiselect("Country",  sorted(df["country"].unique()),
                             default=sorted(df["country"].unique()))
    sort_f = fc3.selectbox("Sort by",
                           ["Annual Margin Loss ↓","Margin Erosion ↓","Revenue ↓"])

    filtered = df[df["risk_tier"].isin(risk_f) & df["country"].isin(ctry_f)].copy()
    sort_map  = {
        "Annual Margin Loss ↓": "annual_margin_loss",
        "Margin Erosion ↓":     "margin_erosion",
        "Revenue ↓":            "annual_revenue",
    }
    filtered = filtered.sort_values(sort_map[sort_f], ascending=False)

    disp = filtered[[
        "product","supplier","country","category",
        "current_tariff_pct","new_tariff_pct",
        "unit_cost_curr","unit_cost_new","tariff_delta_pu",
        "margin_curr_pct","margin_new_pct","margin_erosion",
        "annual_revenue","annual_margin_loss",
        "price_increase_pct","risk_tier",
    ]].rename(columns={
        "product":           "Product",
        "supplier":          "Supplier",
        "country":           "Country",
        "category":          "Category",
        "current_tariff_pct":"Tariff Now %",
        "new_tariff_pct":    "Tariff New %",
        "unit_cost_curr":    "Unit Cost Now",
        "unit_cost_new":     "Unit Cost New",
        "tariff_delta_pu":   "Extra Cost/Unit",
        "margin_curr_pct":   "Margin Now %",
        "margin_new_pct":    "Margin New %",
        "margin_erosion":    "Erosion pp",
        "annual_revenue":    "Annual Rev",
        "annual_margin_loss":"Annual Loss",
        "price_increase_pct":"Price Hike %",
        "risk_tier":         "Risk",
    })

    def color_risk(val):
        m = {
            "HIGH":   "background-color:#fef2f2;color:#dc2626;font-weight:600",
            "MEDIUM": "background-color:#fffbeb;color:#d97706;font-weight:600",
            "LOW":    "background-color:#f0fdf4;color:#16a34a;font-weight:600",
        }
        return m.get(val, "")

    def color_margin(val):
        if isinstance(val, float) and val < 0:
            return "background-color:#fef2f2;color:#dc2626;font-weight:700"
        return ""

    def color_erosion(val):
        if isinstance(val, float):
            if val >= 15: return "color:#dc2626;font-weight:600"
            if val >= 5:  return "color:#d97706;font-weight:600"
        return ""

    styled = (
        disp.style
        .map(color_risk,    subset=["Risk"])
        .map(color_margin,  subset=["Margin New %"])
        .map(color_erosion, subset=["Erosion pp"])
        .format({
            "Tariff Now %":  "{:.1f}%",
            "Tariff New %":  "{:.1f}%",
            "Unit Cost Now": "${:.2f}",
            "Unit Cost New": "${:.2f}",
            "Extra Cost/Unit":"${:.2f}",
            "Margin Now %":  "{:.1f}%",
            "Margin New %":  "{:.1f}%",
            "Erosion pp":    "{:.1f}",
            "Annual Rev":    "${:,.0f}",
            "Annual Loss":   "${:,.0f}",
            "Price Hike %":  "{:.1f}%",
        })
    )
    st.dataframe(styled, use_container_width=True, height=430)

    st.download_button(
        "📥 Download Portfolio Analysis (CSV)",
        df.to_csv(index=False),
        file_name=f"tariffguard_{date.today()}.csv",
        mime="text/csv",
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SCENARIO MODELING
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 🔮 Scenario Modeling — Three Strategic Responses")
    st.caption("Configure each scenario, then compare financial outcomes side by side.")

    with st.expander("⚙️ Configure all three scenarios", expanded=True):
        sp1, sp2, sp3 = st.columns(3)

        with sp1:
            st.markdown("**Scenario A — Partial Absorption**")
            absorb_pct = st.slider(
                "% of tariff cost the company absorbs", 0, 100, 50, 5,
                help="The rest is passed to customers via price increase"
            )
            st.caption(f"You absorb {absorb_pct}%, customers pay {100-absorb_pct}%")

        with sp2:
            st.markdown("**Scenario B — Full Pass-Through**")
            vol_hit = st.checkbox(
                "Apply 10% volume loss for products requiring >15% price increase",
                value=True,
            )
            st.caption("Preserves margin % but may lose volume on price-sensitive products")

        with sp3:
            st.markdown("**Scenario C — Supplier Switch**")
            alt_ctry     = st.selectbox("Switch HIGH-risk to",
                ["India","Vietnam","Mexico","Poland","Malaysia","Indonesia","Bangladesh","Morocco"])
            alt_tariff   = st.number_input("Tariff in new country (%)", 0.0, 200.0,
                value=DEFAULT_TARIFFS.get(alt_ctry, {}).get("new", 20.0), step=0.5)
            cost_premium = st.slider("Cost premium vs current supplier (%)", -20, 60, 15, 1,
                help="Nearshore/reshore typically costs 10-20% more")
            only_high    = st.checkbox("Apply only to HIGH-risk products", value=True)

    # ── Scenario A: Partial absorption ───────────────────────────────────────
    sc = df.copy()
    absorbed_cost  = sc["unit_cost_curr"] + sc["tariff_delta_pu"] * (absorb_pct / 100)
    passed_per_unit = sc["tariff_delta_pu"] * ((100 - absorb_pct) / 100)
    new_price_a     = sc["selling_price"]  + passed_per_unit
    sc["margin_a"]  = ((new_price_a - absorbed_cost) / new_price_a * 100).round(1)
    sc["loss_a"]    = (sc["annual_units"] * (sc["selling_price"] - absorbed_cost)
                       - sc["annual_margin_curr"]).abs().round(0)

    # ── Scenario B: Full pass-through ────────────────────────────────────────
    sc["margin_b"] = sc["margin_curr_pct"]
    sc["loss_b"]   = 0.0
    if vol_hit:
        vol_adj       = sc["price_increase_pct"].apply(lambda p: 0.9 if p > 15 else 1.0)
        rev_b         = sc["annual_units"] * vol_adj * sc["price_to_maintain"]
        sc["loss_b"]  = (sc["annual_revenue"] - rev_b).clip(lower=0).round(0)

    # ── Scenario C: Supplier switch ───────────────────────────────────────────
    mask = (sc["risk_tier"] == "HIGH") if only_high else pd.Series(True, index=sc.index)
    new_base_c    = sc["unit_cost_base"] * (1 + cost_premium / 100)
    new_total_c   = new_base_c * (1 + alt_tariff / 100)
    sc["unit_cost_c"] = sc["unit_cost_new"]
    sc.loc[mask, "unit_cost_c"] = new_total_c[mask]
    sc["margin_c"] = ((sc["selling_price"] - sc["unit_cost_c"]) / sc["selling_price"] * 100).round(1)
    sc["loss_c"]   = (sc["annual_units"] * (sc["selling_price"] - sc["unit_cost_c"])
                      - sc["annual_margin_curr"]).abs().round(0)

    # ── Comparison cards ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Financial Outcome Comparison")

    ca, cb, cc, cd = st.columns(4)

    # Baseline
    with ca:
        st.markdown("**Baseline (no action)**")
        st.metric("Annual Margin", f"${df['annual_margin_new'].sum()/1e3:.0f}K",
                  delta=f"−${total_loss/1e3:.0f}K vs today", delta_color="inverse")
        st.metric("Avg Margin %", f"{df['margin_new_pct'].mean():.1f}%",
                  delta=f"−{avg_erosion:.1f}pp", delta_color="inverse")
        st.caption("All tariff costs absorbed, no pricing action")

    baseline_m = df["annual_margin_curr"].sum()

    for col, label, loss_col, margin_col, note in [
        (ca, "", None, None, None),  # already done
        (cb, f"A: {absorb_pct}% Absorb",   "loss_a", "margin_a",
              f"Absorb {absorb_pct}%, pass {100-absorb_pct}%"),
        (cc, "B: Full Pass-Through",         "loss_b", "margin_b",
              "Raise prices to preserve margin"),
        (cd, f"C: Switch to {alt_ctry}",     "loss_c", "margin_c",
              f"+{cost_premium}% cost, {alt_tariff:.0f}% tariff"),
    ]:
        if loss_col is None:
            continue
        with col:
            scenario_loss = sc[loss_col].sum()
            margin_kept   = baseline_m - scenario_loss
            st.markdown(f"**{label}**")
            st.metric("Net Margin Retained",  f"${margin_kept/1e3:.0f}K",
                      delta=f"{margin_kept/baseline_m*100:.1f}% of original",
                      delta_color="normal")
            st.metric("Avg Margin %", f"{sc[margin_col].mean():.1f}%",
                      delta=f"{sc[margin_col].mean() - df['margin_curr_pct'].mean():.1f}pp",
                      delta_color="inverse" if sc[margin_col].mean() < df["margin_curr_pct"].mean() else "normal")
            st.caption(note)

    # Scenario comparison chart
    scenario_df = pd.DataFrame({
        "Product":  df["product"].str[:18].tolist() * 4,
        "Scenario": (
            ["Baseline (no action)"] * len(df) +
            [f"A: {absorb_pct}% Absorb"]  * len(df) +
            ["B: Full Pass-Through"]       * len(df) +
            [f"C: Switch → {alt_ctry}"]   * len(df)
        ),
        "Margin %": (
            df["margin_new_pct"].tolist() +
            sc["margin_a"].tolist()       +
            sc["margin_b"].tolist()       +
            sc["margin_c"].tolist()
        ),
    })

    fig_sc = px.bar(
        scenario_df, x="Product", y="Margin %", color="Scenario",
        barmode="group",
        color_discrete_sequence=["#94a3b8","#3b82f6","#22c55e","#8b5cf6"],
        title="Gross Margin % by Product — All Scenarios",
    )
    fig_sc.add_hline(y=0, line_dash="dash", line_color="#dc2626",
                     opacity=0.5, annotation_text="Zero margin")
    fig_sc.update_layout(height=390, margin=dict(l=0,r=0,t=44,b=80))
    fig_sc.update_xaxes(tickangle=-35, tickfont_size=10)
    st.plotly_chart(fig_sc, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AI OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🤖 AI Optimization Insights")
    st.caption(
        "Groq AI (llama-3.1-8b-instant) reads your live portfolio data "
        "and returns a specific action plan. Free — no credit card required."
    )

    if not st.session_state.groq_key:
        st.warning("""
**Add your free Groq API key to unlock AI insights.**

**Step 1:** Go to [console.groq.com](https://console.groq.com) and create a free account (30 seconds)  
**Step 2:** Click **API Keys** → **Create API Key** → copy it  
**Step 3:** Paste it in the sidebar under AI Settings  

Groq's free tier: 30 requests/minute, 14,400/day. More than enough.  
For Streamlit Cloud: add `GROQ_API_KEY = "gsk_..."` to your app secrets.
        """)
    else:
        # Summary of what will be analysed
        st.markdown("#### What the AI will analyse from your live data:")
        a1, a2, a3 = st.columns(3)
        a1.markdown(
            f"**Portfolio exposure**\n\n"
            f"${total_loss/1e3:.0f}K margin at risk\n\n"
            f"{high_n} HIGH-risk products\n\n"
            f"{neg_margin_n} products in negative margin"
        )
        a2.markdown(
            "**Pricing strategy**\n\n"
            "Which products can pass through\n\n"
            "Volume risk from price increases\n\n"
            "Blended revenue impact scenarios"
        )
        a3.markdown(
            "**Sourcing alternatives**\n\n"
            "Country-specific recommendations\n\n"
            "Cost vs tariff trade-offs\n\n"
            "Transition timeline and risks"
        )

        if st.button("🔍 Generate AI Optimization Plan", type="primary", use_container_width=True):
            with st.spinner("Groq AI is analysing your tariff exposure and building recommendations..."):
                sys_p, usr_p = build_ai_prompt(df, st.session_state.tariffs)
                result = ask_groq(sys_p, usr_p, st.session_state.groq_key)

            if result == "INVALID_KEY":
                st.error("Invalid API key. Please check your key at console.groq.com.")
            elif result == "CONNECTION_ERROR":
                st.error("Connection error. Check your internet connection.")
            elif result.startswith("ERROR"):
                st.error(result)
            else:
                st.session_state.ai_output = result

        if st.session_state.ai_output:
            st.divider()
            st.markdown(
                f'<div class="ai-output">{st.session_state.ai_output}</div>',
                unsafe_allow_html=True,
            )
            st.divider()
            col_dl1, col_dl2 = st.columns(2)
            col_dl1.download_button(
                "📥 Download AI Report (.txt)",
                st.session_state.ai_output,
                file_name=f"tariffguard_report_{date.today()}.txt",
                mime="text/plain",
                use_container_width=True,
            )
            if col_dl2.button("🔄 Regenerate", use_container_width=True):
                st.session_state.ai_output = ""
                st.rerun()

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"TariffGuard · Supply Chain Tariff Impact & Margin Optimization · "
    f"AI by Groq (llama-3.1-8b-instant, free) · "
    f"2025 US tariff schedule · Built by Rutwik Satish"
)
