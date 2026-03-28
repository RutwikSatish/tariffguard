TariffGuard 🛡️
Supply Chain Tariff Impact & Margin Optimization Platform

"The 2025 US tariff escalation — China +120pp, Vietnam +46pp, Mexico +25pp, Canada +25pp — is the largest disruption to US import costs in modern trade history. For supply chain teams, the question is no longer whether margins will shrink. It's how fast, and what to do."

Live App → https://tariffguard.streamlit.app/ |  GitHub → https://github.com/RutwikSatish/tariffguard

What It Does
TariffGuard quantifies exactly how the 2025 US tariff schedule erodes product margins and annual revenue — then uses AI to recommend specific optimization strategies, sourcing alternatives, and pricing decisions.
It answers the four questions every supply chain and finance leader is asking right now:

Which products are at risk? — Risk-tiered portfolio with current vs new margin per product
How much will we lose? — Annual margin erosion in dollars, by product and by country
What are our options? — Side-by-side scenario comparison: absorb, pass through, or switch supplier
What should we do first? — AI-generated action plan with specific owners, timelines, and $ impact


The Problem It Solves
The 2025 tariff schedule hits US importers asymmetrically. Companies sourcing from China face rate increases of up to 145% — enough to turn profitable product lines negative overnight. Finance and supply chain teams need to:

Quantify the impact per SKU, not just at the portfolio level
Model strategic response options before committing to one
Communicate the risk clearly to leadership with numbers, not estimates
Move fast — tariffs are already in effect

Existing tools (SAP, Oracle, Coupa) require expensive licenses and weeks of setup. Spreadsheets can't model scenarios dynamically. TariffGuard solves both problems: free, instant, and interactive.

Features
📊 Impact Dashboard

Grouped bar chart: gross margin before and after tariffs, per product, color-coded by risk tier
Waterfall chart: annual margin erosion by country — shows exactly where the losses originate
Risk matrix bubble chart: margin erosion vs new margin level, bubble size = annual revenue

🔢 Product Analysis Table
Full portfolio breakdown with:
ColumnWhat it showsTariff Now % / New %Before and after rates for each countryUnit Cost Now / NewActual landed cost impact per unitExtra Cost/UnitThe tariff delta in dollars — what each unit costs moreMargin Now % / New %Gross margin before and after — negative values highlighted in redErosion ppPercentage point drop in marginAnnual LossDollar value of margin destroyed annuallyPrice Hike %How much you'd need to raise prices to maintain current margin exactly
Filterable by risk tier and country. One-click CSV export.
🔮 Scenario Modeling
Three configurable strategies compared side by side:
Scenario A — Partial Absorption
Configure what % of the tariff cost the company absorbs vs passes to customers. Useful for products where you have some pricing power but not full.
Scenario B — Full Pass-Through
Calculate exact price increases needed to maintain current margin. Optional: apply a 10% volume penalty to products requiring >15% price increase — models realistic demand elasticity.
Scenario C — Supplier Switch
Model switching HIGH-risk products to an alternative sourcing country. Configure the new tariff rate, cost premium vs current supplier, and whether to apply to all products or only HIGH-risk ones.
The comparison shows net margin retained and average margin % for all four outcomes (baseline + 3 scenarios) side by side, plus a grouped bar chart across the full portfolio.
🤖 AI Optimization (Groq — free)
Powered by llama-3.1-8b-instant via Groq's free API. The AI reads your live portfolio data — every product, every metric, every tariff rate — and returns a structured optimization roadmap covering:

Situation assessment with severity rating
Immediate actions (30 days) with $ impact per action
Pricing strategy: which products can absorb a hike, which cannot, blended revenue impact
Sourcing diversification: specific alternative countries per HIGH-risk product
Quick wins vs structural changes vs long-term moves
Leadership decision: what decision must be made in the next 2 weeks


The Math
All calculations are transparent and auditable:
unit_cost_curr  = unit_cost_base × (1 + current_tariff% / 100)
unit_cost_new   = unit_cost_base × (1 + new_tariff% / 100)
tariff_delta_pu = unit_cost_new − unit_cost_curr

margin_curr_pct = (selling_price − unit_cost_curr) / selling_price × 100
margin_new_pct  = (selling_price − unit_cost_new)  / selling_price × 100
margin_erosion  = margin_curr_pct − margin_new_pct

annual_margin_loss = annual_units × (unit_cost_new − unit_cost_curr)

price_to_maintain = unit_cost_new / (1 − original_margin_rate)
Risk tiers are assigned as:

HIGH — new margin < 0%, OR margin erosion ≥ 15pp
MEDIUM — margin erosion ≥ 5pp
LOW — erosion < 5pp


2025 Tariff Context
Default rates loaded in the app (source: USTR announcements Jan–Apr 2025):
CountryPrevious RateNew RateChangeChina25%145%+120ppVietnam0%46%+46ppTaiwan0%32%+32ppIndia0%26%+26ppMexico0%25%+25ppCanada0%25%+25ppSouth Korea0%25%+25ppJapan0%24%+24ppGermany0%20%+20ppBrazil0%10%+10pp
All rates are editable directly in the sidebar — update as the tariff schedule evolves.

Technology Stack
Frontend / UI:    Streamlit
Charts:           Plotly (interactive — waterfall, bubble, grouped bar, scenario comparison)
AI:               Groq API — llama-3.1-8b-instant (free tier: 14,400 requests/day)
Language:         Python 3.11
Dependencies:     streamlit · plotly · requests (3 packages total)
Why Groq instead of OpenAI / Anthropic?

Free — no credit card, 14,400 API calls/day, 30/minute
Fast — llama-3.1-8b-instant responds in 1–3 seconds
No data retention — Groq does not train on API inputs, important for commercial supply chain data
Works on Streamlit Cloud without any secrets management complexity


Installation
bash# 1. Clone the repo
git clone https://github.com/your-username/tariffguard
cd tariffguard

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install streamlit plotly requests

# 4. Get free Groq API key at console.groq.com (2 minutes)

# 5. Run
streamlit run app.py
Enter your Groq key in the sidebar, load sample data, and explore.

Deploying to Streamlit Cloud

Push to GitHub
Go to share.streamlit.io → New app
Point to app.py
Add your Groq key to Secrets:

tomlGROQ_API_KEY = "gsk_your_key_here"

Deploy — live in ~60 seconds


Bring Your Own Data
Upload a CSV with these columns:
ColumnTypeDescriptionproductstringProduct or SKU namesupplierstringSupplier namecountrystringCountry of manufacturecategorystringProduct categorymonthly_unitsintegerMonthly sales volumeunit_cost_basefloatImport cost per unit before tariffselling_pricefloatCurrent selling price
The app calculates everything else automatically. Country names must match those in the tariff table (editable in sidebar).

Research & Context
This project is grounded in current supply chain literature and 2025 trade policy developments:
Trade policy sources

USTR Section 301 tariff announcements, January–April 2025
White House Executive Orders on import tariffs (Canada, Mexico, China), February–March 2025
Peterson Institute for International Economics — tariff impact modelling framework

Industry research

IBM Institute for Business Value (2024): 89% of CSCOs investing in gen AI for supply chain
McKinsey Global Institute: up to 45% of supply chain activities automatable with current AI
Gartner CSCO Survey (2023): 40% of CSCOs cite supply chain visibility as top priority

Methodological note
Margin erosion calculations use landed cost methodology (tariff applied to FOB cost). Real-world scenarios may also include first-sale valuation, bonded warehousing, and Section 321 de minimis exemptions — which are not modelled here but can be approximated via the sidebar tariff rate editor.
