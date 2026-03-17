import io
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="DCF Valuation Tool",
    page_icon="📈",
    layout="centered"
)


# -----------------------------
# Formatting helpers
# -----------------------------
def format_dollar_short(value):
    if value is None or pd.isna(value):
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    return f"${value:,.2f}"


def format_percent(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.1f}%"


def html_table(df: pd.DataFrame) -> str:
    header_html = "".join([f"<th>{col}</th>" for col in df.columns])
    body_rows = []
    for _, row in df.iterrows():
        row_html = "".join([f"<td>{val}</td>" for val in row])
        body_rows.append(f"<tr>{row_html}</tr>")
    body_html = "".join(body_rows)

    return f"""
    <div class="table-wrap">
        <table class="clean-table">
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {body_html}
            </tbody>
        </table>
    </div>
    """


def is_probable_ticker(query: str) -> bool:
    q = query.strip().upper()
    return bool(re.fullmatch(r"[A-Z.\-]{1,6}", q))


# -----------------------------
# Peer suggestion maps
# -----------------------------
PEER_MAP = {
    "AAPL": ["MSFT", "GOOGL", "NVDA", "AMZN"],
    "MSFT": ["AAPL", "GOOGL", "ORCL", "NVDA"],
    "GOOGL": ["META", "MSFT", "AMZN", "NFLX"],
    "META": ["GOOGL", "SNAP", "PINS", "NFLX"],
    "NVDA": ["AMD", "INTC", "AVGO", "QCOM"],
    "AMD": ["NVDA", "INTC", "AVGO", "QCOM"],
    "AMZN": ["WMT", "COST", "BABA", "SHOP"],
    "TSLA": ["GM", "F", "RIVN", "LCID"],
    "JPM": ["BAC", "C", "WFC", "GS"],
    "BAC": ["JPM", "C", "WFC", "MS"],
    "GS": ["MS", "JPM", "BAC", "C"],
    "NFLX": ["DIS", "WBD", "GOOGL", "META"],
    "KO": ["PEP", "MNST", "KDP", "CELH"],
    "PEP": ["KO", "KDP", "MNST", "WMT"],
    "WMT": ["TGT", "COST", "AMZN", "KR"],
    "COST": ["WMT", "TGT", "KR", "AMZN"],
    "ORCL": ["MSFT", "SAP", "CRM", "IBM"],
    "CRM": ["ORCL", "MSFT", "NOW", "ADBE"],
    "ADBE": ["CRM", "MSFT", "NOW", "INTU"],
    "INTC": ["AMD", "NVDA", "QCOM", "AVGO"],
    "AVGO": ["QCOM", "AMD", "NVDA", "INTC"],
}

SECTOR_PEERS = {
    "Technology": ["MSFT", "AAPL", "NVDA", "ORCL"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD"],
    "Financial Services": ["JPM", "BAC", "GS", "MS"],
    "Healthcare": ["JNJ", "PFE", "MRK", "ABBV"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS"],
    "Consumer Defensive": ["PG", "KO", "PEP", "WMT"],
    "Industrials": ["GE", "CAT", "DE", "HON"],
    "Energy": ["XOM", "CVX", "COP", "SLB"],
    "Utilities": ["NEE", "DUK", "SO", "AEP"],
    "Real Estate": ["PLD", "AMT", "SPG", "EQIX"],
    "Basic Materials": ["LIN", "APD", "SHW", "ECL"],
}


# -----------------------------
# Data access
# -----------------------------
@st.cache_data(ttl=1800)
def resolve_company_input(query: str) -> Dict:
    """
    Resolve user input (company name or ticker) to a ticker symbol.
    """
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Please enter a company name or ticker.")

    if is_probable_ticker(clean_query):
        symbol = clean_query.upper()
        return {
            "symbol": symbol,
            "matched_name": symbol,
            "source": "ticker"
        }

    try:
        search = yf.Search(query=clean_query, max_results=8)
        quotes = getattr(search, "quotes", []) or []
        if quotes:
            best = quotes[0]
            symbol = best.get("symbol", clean_query.upper())
            matched_name = (
                best.get("shortname")
                or best.get("longname")
                or best.get("displayName")
                or symbol
            )
            return {
                "symbol": symbol,
                "matched_name": matched_name,
                "source": "search"
            }
    except Exception:
        pass

    return {
        "symbol": clean_query.upper(),
        "matched_name": clean_query,
        "source": "fallback"
    }


@st.cache_data(ttl=1800)
def get_market_and_financial_data(symbol: str) -> Dict:
    ticker = yf.Ticker(symbol)

    financials = ticker.financials
    cashflow = ticker.cashflow
    hist = ticker.history(period="5d")

    current_price = None
    if not hist.empty:
        current_price = float(hist["Close"].iloc[-1])

    shares_outstanding = None
    company_name = symbol
    market_cap = None
    trailing_pe = None
    forward_pe = None
    trailing_eps = None
    forward_eps = None
    sector = None
    industry = None

    try:
        fast_info = ticker.fast_info
        if hasattr(fast_info, "get"):
            shares_outstanding = fast_info.get("shares")
            market_cap = fast_info.get("market_cap")
    except Exception:
        pass

    try:
        info = ticker.info
        company_name = info.get("longName", symbol)
        if current_price is None:
            current_price = info.get("currentPrice", 0)
        if shares_outstanding is None:
            shares_outstanding = info.get("sharesOutstanding")
        if market_cap is None:
            market_cap = info.get("marketCap")
        trailing_pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        trailing_eps = info.get("trailingEps")
        forward_eps = info.get("forwardEps")
        sector = info.get("sector")
        industry = info.get("industry")
    except Exception:
        pass

    return {
        "company_name": company_name,
        "current_price": current_price,
        "shares_outstanding": shares_outstanding,
        "market_cap": market_cap,
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
        "trailing_eps": trailing_eps,
        "forward_eps": forward_eps,
        "sector": sector,
        "industry": industry,
        "financials": financials,
        "cashflow": cashflow
    }


def suggest_peers(symbol: str, sector: Optional[str]) -> List[str]:
    if symbol in PEER_MAP:
        return [x for x in PEER_MAP[symbol] if x != symbol]

    if sector in SECTOR_PEERS:
        return [x for x in SECTOR_PEERS[sector] if x != symbol]

    return ["MSFT", "GOOGL", "NVDA", "AMZN"] if symbol != "MSFT" else ["AAPL", "GOOGL", "NVDA", "ORCL"]


@st.cache_data(ttl=1800)
def get_peer_metrics(tickers: Tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for t in tickers:
        try:
            data = get_market_and_financial_data(t)
            rows.append({
                "Ticker": t,
                "Company": data["company_name"],
                "Market Cap": format_dollar_short(data["market_cap"]),
                "Trailing P/E": round(data["trailing_pe"], 2) if data["trailing_pe"] else "N/A",
                "Forward P/E": round(data["forward_pe"], 2) if data["forward_pe"] else "N/A",
                "Current Price": format_dollar_short(data["current_price"])
            })
        except Exception:
            rows.append({
                "Ticker": t,
                "Company": "Unavailable",
                "Market Cap": "N/A",
                "Trailing P/E": "N/A",
                "Forward P/E": "N/A",
                "Current Price": "N/A"
            })
    return pd.DataFrame(rows)


# -----------------------------
# Valuation logic
# -----------------------------
def run_dcf(
    base_revenue,
    ebit_margin,
    da_percent,
    capex_percent,
    shares_outstanding,
    growth_rate,
    tax_rate,
    wacc,
    terminal_growth,
    net_debt,
    projection_years
):
    projected_revenues = []
    projected_fcfs = []
    discounted_fcfs = []

    revenue_proj = base_revenue

    for year in range(1, projection_years + 1):
        revenue_proj = revenue_proj * (1 + growth_rate)
        projected_revenues.append(revenue_proj)

        ebit = revenue_proj * ebit_margin
        nopat = ebit * (1 - tax_rate)
        da = revenue_proj * da_percent
        capex_proj = revenue_proj * capex_percent
        nwc = 0

        fcf = nopat + da - capex_proj - nwc
        projected_fcfs.append(fcf)

        discounted_fcf = fcf / ((1 + wacc) ** year)
        discounted_fcfs.append(discounted_fcf)

    final_fcf = projected_fcfs[-1]

    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than Terminal Growth Rate.")

    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    discounted_terminal_value = terminal_value / ((1 + wacc) ** projection_years)

    enterprise_value = sum(discounted_fcfs) + discounted_terminal_value
    equity_value = enterprise_value - net_debt
    implied_price = equity_value / shares_outstanding

    return {
        "projected_revenues": projected_revenues,
        "projected_fcfs": projected_fcfs,
        "discounted_fcfs": discounted_fcfs,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "implied_price": implied_price
    }


def get_recommendation(upside_downside: float) -> Tuple[str, str]:
    if upside_downside >= 20:
        return "STRONG BUY", "#16A34A"
    if upside_downside >= 10:
        return "BUY", "#22C55E"
    if upside_downside <= -20:
        return "STRONG SELL", "#B91C1C"
    if upside_downside <= -10:
        return "SELL", "#DC2626"
    return "HOLD", "#F59E0B"


def build_excel_file(
    summary_df: pd.DataFrame,
    projection_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    sensitivity_df: pd.DataFrame,
    peers_df: pd.DataFrame
) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        projection_df.to_excel(writer, sheet_name="DCF Projections", index=False)
        scenario_df.to_excel(writer, sheet_name="Scenarios", index=False)
        sensitivity_df.to_excel(writer, sheet_name="Sensitivity", index=False)
        peers_df.to_excel(writer, sheet_name="Peers", index=False)
    return output.getvalue()


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    body {
        background-color: #0B1020;
        color: #FAFAFA;
    }

    .stApp {
        background: radial-gradient(circle at top left, #0F1B3D 0%, #0B1020 45%, #070B14 100%);
        color: #FAFAFA;
    }

    .main {
        padding-top: 1rem;
    }

    h1, h2, h3, h4, h5, h6, p, label, div {
        color: #FAFAFA;
    }

    .stTextInput > div > div > input,
    .stNumberInput input {
        background-color: #141B2D !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #25304A !important;
    }

    .stButton > button {
        background: linear-gradient(90deg, #38BDF8 0%, #60A5FA 100%) !important;
        color: #08101F !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 0.65rem 1.2rem !important;
        border: none !important;
    }

    .stButton > button:hover {
        opacity: 0.92;
    }

    .brand-pill {
        width: 54px;
        height: 54px;
        border-radius: 16px;
        margin: 0 auto 10px auto;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 20px;
        color: #08101F;
        background: linear-gradient(135deg, #38BDF8 0%, #60A5FA 100%);
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.20);
    }

    .metric-card {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 1rem;
        background: rgba(17, 24, 39, 0.86);
        backdrop-filter: blur(8px);
        margin-bottom: 0.75rem;
    }

    .metric-label {
        color: #AAB0B6;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
    }

    .metric-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: #FFFFFF;
    }

    .summary-box {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 1.1rem;
        background: rgba(17, 24, 39, 0.86);
        margin-top: 0.8rem;
        margin-bottom: 1rem;
    }

    .summary-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .section-label {
        font-size: 1.75rem;
        font-weight: 800;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
        color: #FFFFFF;
    }

    .table-wrap {
        background: rgba(17, 24, 39, 0.86);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        overflow: hidden;
        margin-bottom: 1rem;
    }

    .clean-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 15px;
    }

    .clean-table thead tr {
        background: #131C31;
    }

    .clean-table th {
        text-align: left;
        padding: 14px 16px;
        color: #C9D1D9;
        font-weight: 700;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    .clean-table td {
        padding: 14px 16px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        color: #F5F7FA;
    }

    .clean-table tbody tr:last-child td {
        border-bottom: none;
    }

    .clean-table tbody tr:hover {
        background: rgba(255,255,255,0.03);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="brand-pill">NG</div>
    <h1 style='text-align: center;'>DCF Valuation Tool</h1>
    <p style='text-align: center; font-size:22px; font-weight: bold; color: #4FC3F7; margin-bottom: 5px; text-shadow: 0 0 12px rgba(79,195,247,0.35);'>
    Nishtha Garg
    </p>
    <p style='text-align: center; color: #B8C0CC; font-size:16px;'>
    Interactive discounted cash flow model with scenario analysis, sensitivity analysis, and comps
    </p>
    <hr style='margin-top:10px; margin-bottom:24px; border: 0.5px solid #22304C;'>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Inputs
# -----------------------------
st.markdown('<div class="section-label">Inputs</div>', unsafe_allow_html=True)

company_input = st.text_input("Enter Company Name or Ticker", "Apple")
growth_rate = st.number_input("Revenue Growth Rate (%)", value=5.0, step=0.5) / 100
tax_rate = st.number_input("Tax Rate (%)", value=21.0, step=0.5) / 100
wacc = st.number_input("WACC (%)", value=9.0, step=0.5) / 100
terminal_growth = st.number_input("Terminal Growth Rate (%)", value=2.5, step=0.5) / 100
projection_years = int(st.number_input("Projection Years", min_value=3, max_value=10, value=5, step=1))
net_debt = st.number_input("Net Debt ($)", value=0.0, step=1000000.0)
manual_peers = st.text_input("Optional: Override Peer Tickers", "")

run_button = st.button("Run Valuation")

if run_button:
    try:
        resolved = resolve_company_input(company_input)
        resolved_symbol = resolved["symbol"]

        data = get_market_and_financial_data(resolved_symbol)
        company_name = data["company_name"]
        current_price = data["current_price"] or 0
        shares_outstanding = data["shares_outstanding"]
        market_cap = data["market_cap"]
        trailing_pe = data["trailing_pe"]
        forward_pe = data["forward_pe"]
        trailing_eps = data["trailing_eps"]
        forward_eps = data["forward_eps"]
        sector = data["sector"]
        financials = data["financials"]
        cashflow = data["cashflow"]

        st.caption(f"Matched Input: {company_name} ({resolved_symbol})")

        revenue = financials.loc["Total Revenue"].iloc[0]
        operating_income = financials.loc["Operating Income"].iloc[0]
        depreciation = cashflow.loc["Depreciation And Amortization"].iloc[0]
        capex = abs(cashflow.loc["Capital Expenditure"].iloc[0])

        if shares_outstanding is None or shares_outstanding == 0:
            raise ValueError("Could not retrieve shares outstanding for this company.")

        ebit_margin = operating_income / revenue
        da_percent = depreciation / revenue
        capex_percent = capex / revenue

        base_results = run_dcf(
            base_revenue=revenue,
            ebit_margin=ebit_margin,
            da_percent=da_percent,
            capex_percent=capex_percent,
            shares_outstanding=shares_outstanding,
            growth_rate=growth_rate,
            tax_rate=tax_rate,
            wacc=wacc,
            terminal_growth=terminal_growth,
            net_debt=net_debt,
            projection_years=projection_years
        )

        implied_price = base_results["implied_price"]
        enterprise_value = base_results["enterprise_value"]
        upside_downside = ((implied_price - current_price) / current_price) * 100 if current_price else 0
        recommendation, rec_color = get_recommendation(upside_downside)

        # -----------------------------
        # Suggested peers / override
        # -----------------------------
        suggested_peers = suggest_peers(resolved_symbol, sector)
        if manual_peers.strip():
            peer_list = [x.strip().upper() for x in manual_peers.split(",") if x.strip()]
        else:
            peer_list = suggested_peers

        st.caption(f"Suggested Peers: {', '.join(suggested_peers)}")

        # -----------------------------
        # Results
        # -----------------------------
        st.markdown(f'<div class="section-label">Results for {company_name}</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Current Price</div>
                    <div class="metric-value">{format_dollar_short(current_price)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Implied Price</div>
                    <div class="metric-value">{format_dollar_short(implied_price)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        c3, c4 = st.columns(2)
        with c3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Enterprise Value</div>
                    <div class="metric-value">{format_dollar_short(enterprise_value)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Upside / Downside</div>
                    <div class="metric-value">{format_percent(upside_downside)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        c5, c6 = st.columns(2)
        with c5:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Market Cap</div>
                    <div class="metric-value">{format_dollar_short(market_cap)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c6:
            pe_display = f"Trailing P/E: {round(trailing_pe, 2) if trailing_pe else 'N/A'} | Forward P/E: {round(forward_pe, 2) if forward_pe else 'N/A'}"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Valuation Multiples</div>
                    <div style="font-size:1.05rem; font-weight:700; color:#FFFFFF;">{pe_display}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            f"""
            <div class="summary-box" style="border-left: 5px solid {rec_color};">
                <div class="summary-title">Recommendation</div>
                <div style="font-size: 1.35rem; font-weight: 800; color: {rec_color}; margin-bottom: 10px;">
                    {recommendation}
                </div>
                <div style="line-height:1.7; font-size:1.05rem;">
                    Implied Equity Value: <b>{format_dollar_short(implied_price)}</b><br>
                    Current Market Price: <b>{format_dollar_short(current_price)}</b><br>
                    Upside / Downside: <b>{upside_downside:,.1f}%</b>
                </div>
                <div style="margin-top:12px; color:#AAB0B6; font-size:14px;">
                    Assumptions: Revenue Growth {growth_rate*100:.1f}% | WACC {wacc*100:.1f}% | Terminal Growth {terminal_growth*100:.1f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # -----------------------------
        # Projected financials
        # -----------------------------
        st.markdown('<div class="section-label">Projected Financials</div>', unsafe_allow_html=True)

        projection_df_display = pd.DataFrame({
            "Year": list(range(1, projection_years + 1)),
            "Projected Revenue ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["projected_revenues"]],
            "Projected FCF ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["projected_fcfs"]],
            "Discounted FCF ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["discounted_fcfs"]],
        })
        st.markdown(html_table(projection_df_display), unsafe_allow_html=True)

        # -----------------------------
        # Charts
        # -----------------------------
        st.markdown('<div class="section-label">Projection Charts</div>', unsafe_allow_html=True)

        years = list(range(1, projection_years + 1))
        revenue_values = [x / 1_000_000 for x in base_results["projected_revenues"]]
        fcf_values = [x / 1_000_000 for x in base_results["projected_fcfs"]]

        revenue_fig = go.Figure()
        revenue_fig.add_trace(
            go.Scatter(
                x=years,
                y=revenue_values,
                mode="lines+markers",
                line=dict(color="#38BDF8", width=4),
                marker=dict(size=8, color="#38BDF8"),
                name="Revenue"
            )
        )
        revenue_fig.update_layout(
            title="Revenue Forecast",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#111827",
            font=dict(color="#F9FAFB"),
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis=dict(title="Year", gridcolor="#243041"),
            yaxis=dict(title="Revenue ($M)", gridcolor="#243041"),
        )

        fcf_fig = go.Figure()
        fcf_fig.add_trace(
            go.Bar(
                x=years,
                y=fcf_values,
                marker=dict(color="#8B5CF6"),
                name="FCF"
            )
        )
        fcf_fig.update_layout(
            title="Free Cash Flow Forecast",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#111827",
            font=dict(color="#F9FAFB"),
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis=dict(title="Year", gridcolor="#243041"),
            yaxis=dict(title="FCF ($M)", gridcolor="#243041"),
        )

        st.plotly_chart(revenue_fig, use_container_width=True)
        st.plotly_chart(fcf_fig, use_container_width=True)

        # -----------------------------
        # Scenario analysis
        # -----------------------------
        st.markdown('<div class="section-label">Scenario Analysis</div>', unsafe_allow_html=True)

        st.markdown("**Bear Case**")
        bear_growth = st.number_input("Bear Growth (%)", value=max((growth_rate * 100) - 2, 0.0), key="bear_growth") / 100
        bear_wacc = st.number_input("Bear WACC (%)", value=(wacc * 100) + 1, key="bear_wacc") / 100
        bear_tg = st.number_input("Bear Terminal Growth (%)", value=max((terminal_growth * 100) - 0.5, 0.0), key="bear_tg") / 100

        st.markdown("**Base Case**")
        base_growth_scn = st.number_input("Base Growth (%)", value=growth_rate * 100, key="base_growth") / 100
        base_wacc_scn = st.number_input("Base WACC (%)", value=wacc * 100, key="base_wacc") / 100
        base_tg_scn = st.number_input("Base Terminal Growth (%)", value=terminal_growth * 100, key="base_tg") / 100

        st.markdown("**Bull Case**")
        bull_growth = st.number_input("Bull Growth (%)", value=(growth_rate * 100) + 2, key="bull_growth") / 100
        bull_wacc = st.number_input("Bull WACC (%)", value=max((wacc * 100) - 1, 0.0), key="bull_wacc") / 100
        bull_tg = st.number_input("Bull Terminal Growth (%)", value=(terminal_growth * 100) + 0.5, key="bull_tg") / 100

        scenario_inputs = {
            "Bear": {"growth": bear_growth, "wacc": bear_wacc, "tg": bear_tg},
            "Base": {"growth": base_growth_scn, "wacc": base_wacc_scn, "tg": base_tg_scn},
            "Bull": {"growth": bull_growth, "wacc": bull_wacc, "tg": bull_tg},
        }

        scenario_rows = []
        for scenario_name, vals in scenario_inputs.items():
            try:
                scenario_result = run_dcf(
                    base_revenue=revenue,
                    ebit_margin=ebit_margin,
                    da_percent=da_percent,
                    capex_percent=capex_percent,
                    shares_outstanding=shares_outstanding,
                    growth_rate=vals["growth"],
                    tax_rate=tax_rate,
                    wacc=vals["wacc"],
                    terminal_growth=vals["tg"],
                    net_debt=net_debt,
                    projection_years=projection_years
                )
                scenario_rows.append({
                    "Scenario": scenario_name,
                    "Growth Rate": f"{vals['growth']*100:.2f}%",
                    "WACC": f"{vals['wacc']*100:.2f}%",
                    "Terminal Growth": f"{vals['tg']*100:.2f}%",
                    "Implied Price": format_dollar_short(scenario_result["implied_price"])
                })
            except Exception:
                scenario_rows.append({
                    "Scenario": scenario_name,
                    "Growth Rate": f"{vals['growth']*100:.2f}%",
                    "WACC": f"{vals['wacc']*100:.2f}%",
                    "Terminal Growth": f"{vals['tg']*100:.2f}%",
                    "Implied Price": "Invalid"
                })

        scenario_df_display = pd.DataFrame(scenario_rows)
        st.markdown(html_table(scenario_df_display), unsafe_allow_html=True)

        # -----------------------------
        # Sensitivity heatmap + table
        # -----------------------------
        st.markdown('<div class="section-label">Sensitivity Analysis</div>', unsafe_allow_html=True)

        wacc_input = st.text_input("WACC values (%)", "7,8,9,10")
        tg_input = st.text_input("Terminal Growth values (%)", "2,2.5,3")

        sensitivity_df_export = pd.DataFrame()
        try:
            wacc_values = [float(x.strip()) / 100 for x in wacc_input.split(",")]
            tg_values = [float(x.strip()) / 100 for x in tg_input.split(",")]

            heatmap_values = []
            sensitivity_rows_display = []

            for tg in tg_values:
                heatmap_row = []
                display_row = {"Terminal Growth": f"{tg*100:.2f}%"}
                for w in wacc_values:
                    try:
                        sens_result = run_dcf(
                            base_revenue=revenue,
                            ebit_margin=ebit_margin,
                            da_percent=da_percent,
                            capex_percent=capex_percent,
                            shares_outstanding=shares_outstanding,
                            growth_rate=growth_rate,
                            tax_rate=tax_rate,
                            wacc=w,
                            terminal_growth=tg,
                            net_debt=net_debt,
                            projection_years=projection_years
                        )
                        implied_val = sens_result["implied_price"]
                        heatmap_row.append(implied_val)
                        display_row[f"WACC {w*100:.2f}%"] = format_dollar_short(implied_val)
                    except Exception:
                        heatmap_row.append(None)
                        display_row[f"WACC {w*100:.2f}%"] = "Invalid"
                heatmap_values.append(heatmap_row)
                sensitivity_rows_display.append(display_row)

            sensitivity_df_display = pd.DataFrame(sensitivity_rows_display)
            sensitivity_df_export = sensitivity_df_display.copy()

            heatmap_fig = go.Figure(
                data=go.Heatmap(
                    z=heatmap_values,
                    x=[f"{w*100:.2f}%" for w in wacc_values],
                    y=[f"{tg*100:.2f}%" for tg in tg_values],
                    colorscale="Viridis",
                    colorbar=dict(title="Implied Price"),
                    hovertemplate="WACC: %{x}<br>Terminal Growth: %{y}<br>Implied Price: $%{z:.2f}<extra></extra>",
                )
            )
            heatmap_fig.update_layout(
                title="Sensitivity Heatmap",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#111827",
                font=dict(color="#F9FAFB"),
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis_title="WACC",
                yaxis_title="Terminal Growth",
            )

            st.plotly_chart(heatmap_fig, use_container_width=True)
            st.markdown(html_table(sensitivity_df_display), unsafe_allow_html=True)

        except Exception:
            st.warning("Please enter valid comma-separated numeric values.")

        # -----------------------------
        # Peer comparison + comps valuation
        # -----------------------------
        st.markdown('<div class="section-label">Peer Comparison</div>', unsafe_allow_html=True)

        peers_tuple = tuple(peer_list)
        peer_df = get_peer_metrics(peers_tuple)
        st.markdown(html_table(peer_df), unsafe_allow_html=True)

        # comps valuation
        peer_raw_rows = []
        for peer in peer_list:
            try:
                pdata = get_market_and_financial_data(peer)
                peer_raw_rows.append({
                    "Ticker": peer,
                    "Trailing P/E": pdata["trailing_pe"],
                    "Forward P/E": pdata["forward_pe"]
                })
            except Exception:
                continue

        peer_raw_df = pd.DataFrame(peer_raw_rows)
        avg_trailing_pe = pd.to_numeric(peer_raw_df.get("Trailing P/E"), errors="coerce").dropna().mean() if not peer_raw_df.empty else None
        avg_forward_pe = pd.to_numeric(peer_raw_df.get("Forward P/E"), errors="coerce").dropna().mean() if not peer_raw_df.empty else None

        trailing_comps_value = avg_trailing_pe * trailing_eps if avg_trailing_pe and trailing_eps else None
        forward_comps_value = avg_forward_pe * forward_eps if avg_forward_pe and forward_eps else None

        if trailing_comps_value is not None or forward_comps_value is not None:
            st.markdown('<div class="section-label">Comps Valuation</div>', unsafe_allow_html=True)

            comp1, comp2 = st.columns(2)
            with comp1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Trailing P/E Implied Price</div>
                        <div class="metric-value">{format_dollar_short(trailing_comps_value)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with comp2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">Forward P/E Implied Price</div>
                        <div class="metric-value">{format_dollar_short(forward_comps_value)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # -----------------------------
        # Export
        # -----------------------------
        st.markdown('<div class="section-label">Download Model</div>', unsafe_allow_html=True)

        summary_df = pd.DataFrame([{
            "Company": company_name,
            "Ticker": resolved_symbol,
            "Current Price": current_price,
            "Implied Price": implied_price,
            "Upside/Downside %": upside_downside,
            "Recommendation": recommendation,
            "Enterprise Value": enterprise_value,
            "Market Cap": market_cap,
            "Revenue Growth %": growth_rate * 100,
            "WACC %": wacc * 100,
            "Terminal Growth %": terminal_growth * 100,
        }])

        projection_df_export = pd.DataFrame({
            "Year": list(range(1, projection_years + 1)),
            "Projected Revenue": base_results["projected_revenues"],
            "Projected FCF": base_results["projected_fcfs"],
            "Discounted FCF": base_results["discounted_fcfs"],
        })

        scenario_df_export = pd.DataFrame(scenario_rows)
        peers_df_export = peer_df.copy()

        excel_bytes = build_excel_file(
            summary_df=summary_df,
            projection_df=projection_df_export,
            scenario_df=scenario_df_export,
            sensitivity_df=sensitivity_df_export,
            peers_df=peers_df_export
        )

        st.download_button(
            label="Download Excel Model",
            data=excel_bytes,
            file_name=f"{resolved_symbol.lower()}_valuation_model.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Something went wrong: {e}")
