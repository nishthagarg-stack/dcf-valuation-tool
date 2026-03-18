import io
import re
from typing import List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Valuation Lab",
    page_icon="📈",
    layout="wide",
)

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">

    <style>
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at top left, #0F1B3D 0%, #0B1020 45%, #070B14 100%);
        color: #FAFAFA;
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }

    .brand-container {
        text-align: center;
        margin-bottom: 1.2rem;
    }

    .ng-badge {
        display: inline-block;
        padding: 12px 18px;
        border-radius: 16px;
        font-size: 20px;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8, #6366F1);
        color: white;
        box-shadow: 0 0 20px rgba(56,189,248,0.35);
        margin-bottom: 12px;
        letter-spacing: 1px;
    }

    .title-text {
        font-size: 38px;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: 1px;
        margin-bottom: 4px;
        text-shadow: 0 0 12px rgba(255,255,255,0.08);
    }

    .subtitle-text {
        font-size: 16px;
        color: #9CA3AF;
        font-weight: 500;
        letter-spacing: 0.5px;
    }

    .section-label {
        font-size: 1.55rem;
        font-weight: 800;
        margin-top: 1rem;
        margin-bottom: 0.8rem;
        color: #FFFFFF;
    }

    .metric-card {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 1rem;
        background: rgba(17, 24, 39, 0.86);
        backdrop-filter: blur(8px);
        margin-bottom: 0.75rem;
        min-height: 110px;
    }

    .metric-label {
        color: #AAB0B6;
        font-size: 0.92rem;
        margin-bottom: 0.25rem;
    }

    .metric-value {
        font-size: 1.55rem;
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
        font-size: 14px;
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

    .stTextInput > div > div > input,
    .stNumberInput input {
        background-color: #141B2D !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #25304A !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        background: linear-gradient(90deg, #38BDF8 0%, #60A5FA 100%) !important;
        color: #08101F !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 0.65rem 1.2rem !important;
        border: none !important;
    }

    section[data-testid="stSidebar"] {
        background: rgba(10, 14, 25, 0.96);
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] div {
        color: #D7E3FF !important;
    }

    section[data-testid="stSidebar"] .small-note {
        color: #94A3B8 !important;
    }

    .sidebar-brand {
        text-align: center;
        margin-bottom: 1rem;
    }

    .sidebar-ng {
        display: inline-block;
        padding: 10px 14px;
        border-radius: 14px;
        font-size: 18px;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8, #6366F1);
        color: white;
        margin-bottom: 10px;
    }

    .small-note {
        color: #9CA3AF;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Branding
# -----------------------------
st.markdown(
    """
    <div class="brand-container">
        <div class="ng-badge">NG</div>
        <div class="title-text">Valuation Lab</div>
        <div class="subtitle-text">by Nishtha Garg</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Helpers
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


def normalize_symbol(text: str) -> str:
    raw = text.strip().upper()
    alias_map = {
        "GOOGLE": "GOOGL",
        "ALPHABET": "GOOGL",
        "FACEBOOK": "META",
        "FB": "META",
        "APPLE": "AAPL",
        "MICROSOFT": "MSFT",
        "NVIDIA": "NVDA",
        "AMAZON": "AMZN",
        "TESLA": "TSLA",
        "NETFLIX": "NFLX",
        "JP MORGAN": "JPM",
        "JPMORGAN": "JPM",
    }
    return alias_map.get(raw, raw)


PEER_MAP = {
    "AAPL": ["MSFT", "GOOGL", "NVDA", "AMZN"],
    "MSFT": ["AAPL", "GOOGL", "ORCL", "NVDA"],
    "GOOGL": ["META", "MSFT", "AMZN", "NFLX"],
    "META": ["GOOGL", "NFLX", "SNAP", "PINS"],
    "NVDA": ["AMD", "INTC", "AVGO", "QCOM"],
    "AMD": ["NVDA", "INTC", "AVGO", "QCOM"],
    "AMZN": ["WMT", "COST", "SHOP", "BABA"],
    "TSLA": ["GM", "F", "RIVN", "LCID"],
    "JPM": ["BAC", "C", "WFC", "GS"],
    "NFLX": ["DIS", "WBD", "GOOGL", "META"],
    "ORCL": ["MSFT", "SAP", "CRM", "IBM"],
    "CRM": ["ORCL", "MSFT", "ADBE", "NOW"],
}

SECTOR_PEERS = {
    "Technology": ["MSFT", "AAPL", "NVDA", "ORCL"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS"],
    "Financial Services": ["JPM", "BAC", "GS", "MS"],
    "Consumer Defensive": ["PG", "KO", "PEP", "WMT"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD"],
}


@st.cache_data(ttl=1800)
def resolve_company_input(query: str) -> dict:
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Please enter a company name or ticker.")

    normalized = normalize_symbol(clean_query)

    if is_probable_ticker(normalized):
        return {
            "symbol": normalized,
            "matched_name": normalized,
            "source": "ticker",
        }

    try:
        search = yf.Search(query=clean_query, max_results=8)
        quotes = getattr(search, "quotes", []) or []
        if quotes:
            best = quotes[0]
            symbol = normalize_symbol(best.get("symbol", clean_query.upper()))
            matched_name = (
                best.get("shortname")
                or best.get("longname")
                or best.get("displayName")
                or symbol
            )
            return {
                "symbol": symbol,
                "matched_name": matched_name,
                "source": "search",
            }
    except Exception:
        pass

    return {
        "symbol": normalized,
        "matched_name": clean_query,
        "source": "fallback",
    }


@st.cache_data(ttl=1800)
def get_market_and_financial_data(symbol: str) -> dict:
    symbol = normalize_symbol(symbol)
    ticker = yf.Ticker(symbol)

    financials = ticker.financials
    cashflow = ticker.cashflow
    hist_1y = ticker.history(period="1y")
    hist_5d = ticker.history(period="5d")

    current_price = None
    market_cap = None
    shares_outstanding = None

    try:
        fast_info = ticker.fast_info
        if hasattr(fast_info, "get"):
            current_price = fast_info.get("lastPrice") or current_price
            market_cap = fast_info.get("marketCap") or market_cap
            shares_outstanding = fast_info.get("shares") or shares_outstanding
    except Exception:
        pass

    if current_price is None and not hist_5d.empty:
        current_price = float(hist_5d["Close"].iloc[-1])

    company_name = symbol
    trailing_pe = None
    forward_pe = None
    trailing_eps = None
    forward_eps = None
    sector = None
    industry = None

    try:
        info = ticker.info
        company_name = (
            info.get("longName")
            or info.get("shortName")
            or info.get("displayName")
            or symbol
        )
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
        "symbol": symbol,
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
        "cashflow": cashflow,
        "hist_1y": hist_1y,
    }


def suggest_peers(symbol: str, sector: Optional[str]) -> List[str]:
    symbol = normalize_symbol(symbol)
    if symbol in PEER_MAP:
        return [x for x in PEER_MAP[symbol] if x != symbol]
    if sector in SECTOR_PEERS:
        return [x for x in SECTOR_PEERS[sector] if x != symbol]
    return ["MSFT", "GOOGL", "NVDA", "AMZN"] if symbol != "MSFT" else ["AAPL", "GOOGL", "NVDA", "ORCL"]


@st.cache_data(ttl=1800)
def get_peer_metrics(tickers: Tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for t in tickers:
        t_norm = normalize_symbol(t)
        try:
            data = get_market_and_financial_data(t_norm)
            rows.append(
                {
                    "Ticker": data["symbol"],
                    "Company": data["company_name"],
                    "Market Cap": format_dollar_short(data["market_cap"]),
                    "Trailing P/E": round(data["trailing_pe"], 2) if data["trailing_pe"] else "N/A",
                    "Forward P/E": round(data["forward_pe"], 2) if data["forward_pe"] else "N/A",
                    "Current Price": format_dollar_short(data["current_price"]),
                }
            )
        except Exception:
            rows.append(
                {
                    "Ticker": t_norm,
                    "Company": "Unavailable",
                    "Market Cap": "N/A",
                    "Trailing P/E": "N/A",
                    "Forward P/E": "N/A",
                    "Current Price": "N/A",
                }
            )
    return pd.DataFrame(rows)


def run_dcf(
    base_revenue,
    ebit_margin,
    da_percent,
    capex_percent,
    nwc_percent,
    shares_outstanding,
    growth_rate,
    tax_rate,
    wacc,
    terminal_growth,
    net_debt,
    projection_years,
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
        nwc = revenue_proj * nwc_percent

        fcf = nopat + da - capex_proj - nwc
        projected_fcfs.append(fcf)
        discounted_fcfs.append(fcf / ((1 + wacc) ** year))

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
        "implied_price": implied_price,
    }


def get_recommendation(upside_downside: float):
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
    peers_df: pd.DataFrame,
) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        projection_df.to_excel(writer, sheet_name="DCF Projections", index=False)
        scenario_df.to_excel(writer, sheet_name="Scenarios", index=False)
        sensitivity_df.to_excel(writer, sheet_name="Sensitivity", index=False)
        peers_df.to_excel(writer, sheet_name="Peers", index=False)
    return output.getvalue()


def plot_price_chart(hist_df: pd.DataFrame, company_name: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hist_df.index,
            y=hist_df["Close"],
            mode="lines",
            line=dict(color="#38BDF8", width=3),
            fill="tozeroy",
            fillcolor="rgba(56,189,248,0.10)",
            name="Close",
        )
    )
    fig.update_layout(
        title=f"{company_name} Price Chart (1Y)",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(title="Date", gridcolor="#243041"),
        yaxis=dict(title="Price", gridcolor="#243041"),
        height=380,
    )
    return fig


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-ng">NG</div>
            <div style="font-weight:800; font-size:18px;">Valuation Lab</div>
            <div class="small-note">by Nishtha Garg</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    company_input = st.text_input("Company Name or Ticker", "ULTA")
    growth_rate = st.number_input("Revenue Growth Rate (%)", value=5.0, step=0.5) / 100
    tax_rate = st.number_input("Tax Rate (%)", value=21.0, step=0.5) / 100
    wacc = st.number_input("WACC (%)", value=9.0, step=0.5) / 100
    terminal_growth = st.number_input("Terminal Growth Rate (%)", value=2.5, step=0.5) / 100
    projection_years = int(st.number_input("Projection Years", min_value=3, max_value=10, value=5, step=1))
    net_debt = st.number_input("Net Debt ($)", value=0.0, step=1000000.0)

    st.markdown("### DCF Assumptions")
    use_latest_company_assumptions = st.checkbox("Use latest company margins automatically", value=True)

    manual_ebit_margin = st.number_input("Manual EBIT Margin (%)", value=18.0, step=0.5) / 100
    manual_da_percent = st.number_input("Manual D&A (% of Revenue)", value=3.0, step=0.5) / 100
    manual_capex_percent = st.number_input("Manual CapEx (% of Revenue)", value=4.0, step=0.5) / 100
    manual_nwc_percent = st.number_input("Manual Change in NWC (% of Revenue)", value=1.0, step=0.5) / 100

    manual_peers = st.text_input("Override Peer Tickers", "")

    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["Overview", "Market Data", "DCF Valuation", "Comps Valuation", "Sensitivity", "Export"],
    )

    run_button = st.button("Run Model", use_container_width=True)

# -----------------------------
# Main app
# -----------------------------
if not run_button:
    st.info("Enter a company in the sidebar and click **Run Model** to load the platform.")
else:
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
        industry = data["industry"]
        financials = data["financials"]
        cashflow = data["cashflow"]
        hist_1y = data["hist_1y"]

        if shares_outstanding is None or shares_outstanding == 0:
            raise ValueError("Could not retrieve shares outstanding for this company.")

        revenue = financials.loc["Total Revenue"].iloc[0]
        operating_income = financials.loc["Operating Income"].iloc[0]
        depreciation = cashflow.loc["Depreciation And Amortization"].iloc[0]
        capex = abs(cashflow.loc["Capital Expenditure"].iloc[0])

        auto_ebit_margin = operating_income / revenue
        auto_da_percent = depreciation / revenue
        auto_capex_percent = capex / revenue
        auto_nwc_percent = 0.0

        ebit_margin_used = auto_ebit_margin if use_latest_company_assumptions else manual_ebit_margin
        da_percent_used = auto_da_percent if use_latest_company_assumptions else manual_da_percent
        capex_percent_used = auto_capex_percent if use_latest_company_assumptions else manual_capex_percent
        nwc_percent_used = auto_nwc_percent if use_latest_company_assumptions else manual_nwc_percent

        base_results = run_dcf(
            base_revenue=revenue,
            ebit_margin=ebit_margin_used,
            da_percent=da_percent_used,
            capex_percent=capex_percent_used,
            nwc_percent=nwc_percent_used,
            shares_outstanding=shares_outstanding,
            growth_rate=growth_rate,
            tax_rate=tax_rate,
            wacc=wacc,
            terminal_growth=terminal_growth,
            net_debt=net_debt,
            projection_years=projection_years,
        )

        implied_price = base_results["implied_price"]
        enterprise_value = base_results["enterprise_value"]
        upside_downside = ((implied_price - current_price) / current_price) * 100 if current_price else 0
        recommendation, rec_color = get_recommendation(upside_downside)

        suggested_peers = suggest_peers(resolved_symbol, sector)
        peer_list = [normalize_symbol(x) for x in manual_peers.split(",") if x.strip()] if manual_peers.strip() else suggested_peers
        peer_df = get_peer_metrics(tuple(peer_list))

        peer_raw_rows = []
        for peer in peer_list:
            try:
                pdata = get_market_and_financial_data(peer)
                peer_raw_rows.append(
                    {
                        "Ticker": pdata["symbol"],
                        "Trailing P/E": pdata["trailing_pe"],
                        "Forward P/E": pdata["forward_pe"],
                    }
                )
            except Exception:
                continue

        peer_raw_df = pd.DataFrame(peer_raw_rows)
        avg_trailing_pe = pd.to_numeric(peer_raw_df.get("Trailing P/E"), errors="coerce").dropna().mean() if not peer_raw_df.empty else None
        avg_forward_pe = pd.to_numeric(peer_raw_df.get("Forward P/E"), errors="coerce").dropna().mean() if not peer_raw_df.empty else None

        trailing_comps_value = avg_trailing_pe * trailing_eps if avg_trailing_pe and trailing_eps else None
        forward_comps_value = avg_forward_pe * forward_eps if avg_forward_pe and forward_eps else None

        scenario_inputs = {
            "Bear": {"growth": max(growth_rate - 0.02, 0), "wacc": wacc + 0.01, "tg": max(terminal_growth - 0.005, 0)},
            "Base": {"growth": growth_rate, "wacc": wacc, "tg": terminal_growth},
            "Bull": {"growth": growth_rate + 0.02, "wacc": max(wacc - 0.01, 0.01), "tg": terminal_growth + 0.005},
        }

        scenario_rows = []
        for scenario_name, vals in scenario_inputs.items():
            try:
                scenario_result = run_dcf(
                    base_revenue=revenue,
                    ebit_margin=ebit_margin_used,
                    da_percent=da_percent_used,
                    capex_percent=capex_percent_used,
                    nwc_percent=nwc_percent_used,
                    shares_outstanding=shares_outstanding,
                    growth_rate=vals["growth"],
                    tax_rate=tax_rate,
                    wacc=vals["wacc"],
                    terminal_growth=vals["tg"],
                    net_debt=net_debt,
                    projection_years=projection_years,
                )
                scenario_rows.append(
                    {
                        "Scenario": scenario_name,
                        "Growth Rate": f"{vals['growth']*100:.2f}%",
                        "WACC": f"{vals['wacc']*100:.2f}%",
                        "Terminal Growth": f"{vals['tg']*100:.2f}%",
                        "Implied Price": format_dollar_short(scenario_result["implied_price"]),
                    }
                )
            except Exception:
                scenario_rows.append(
                    {
                        "Scenario": scenario_name,
                        "Growth Rate": f"{vals['growth']*100:.2f}%",
                        "WACC": f"{vals['wacc']*100:.2f}%",
                        "Terminal Growth": f"{vals['tg']*100:.2f}%",
                        "Implied Price": "Invalid",
                    }
                )

        scenario_df = pd.DataFrame(scenario_rows)

        wacc_values = [0.07, 0.08, 0.09, 0.10]
        tg_values = [0.02, 0.025, 0.03]

        sensitivity_rows = []
        heatmap_values = []

        for tg in tg_values:
            row = {"Terminal Growth": f"{tg*100:.2f}%"}
            heatmap_row = []
            for w in wacc_values:
                try:
                    sens_result = run_dcf(
                        base_revenue=revenue,
                        ebit_margin=ebit_margin_used,
                        da_percent=da_percent_used,
                        capex_percent=capex_percent_used,
                        nwc_percent=nwc_percent_used,
                        shares_outstanding=shares_outstanding,
                        growth_rate=growth_rate,
                        tax_rate=tax_rate,
                        wacc=w,
                        terminal_growth=tg,
                        net_debt=net_debt,
                        projection_years=projection_years,
                    )
                    row[f"WACC {w*100:.2f}%"] = format_dollar_short(sens_result["implied_price"])
                    heatmap_row.append(sens_result["implied_price"])
                except Exception:
                    row[f"WACC {w*100:.2f}%"] = "Invalid"
                    heatmap_row.append(None)
            sensitivity_rows.append(row)
            heatmap_values.append(heatmap_row)

        sensitivity_df = pd.DataFrame(sensitivity_rows)

        summary_df = pd.DataFrame(
            [
                {
                    "Company": company_name,
                    "Ticker": resolved_symbol,
                    "Current Price": current_price,
                    "Implied Price": implied_price,
                    "Upside/Downside %": upside_downside,
                    "Recommendation": recommendation,
                    "Enterprise Value": enterprise_value,
                    "Market Cap": market_cap,
                    "Sector": sector,
                    "Industry": industry,
                    "Revenue Growth %": growth_rate * 100,
                    "WACC %": wacc * 100,
                    "Terminal Growth %": terminal_growth * 100,
                    "EBIT Margin %": ebit_margin_used * 100,
                    "D&A %": da_percent_used * 100,
                    "CapEx %": capex_percent_used * 100,
                    "NWC %": nwc_percent_used * 100,
                }
            ]
        )

        projection_export_df = pd.DataFrame(
            {
                "Year": list(range(1, projection_years + 1)),
                "Projected Revenue": base_results["projected_revenues"],
                "Projected FCF": base_results["projected_fcfs"],
                "Discounted FCF": base_results["discounted_fcfs"],
            }
        )

        excel_bytes = build_excel_file(
            summary_df=summary_df,
            projection_df=projection_export_df,
            scenario_df=scenario_df,
            sensitivity_df=sensitivity_df,
            peers_df=peer_df,
        )

        st.caption(f"Matched Input: {company_name} ({resolved_symbol})")
        st.caption(f"Suggested Peers: {', '.join(suggested_peers)}")

        if page == "Overview":
            st.markdown('<div class="section-label">Overview</div>', unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Current Price</div><div class="metric-value">{format_dollar_short(current_price)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Implied Price</div><div class="metric-value">{format_dollar_short(implied_price)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Upside / Downside</div><div class="metric-value">{format_percent(upside_downside)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with c4:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Recommendation</div><div class="metric-value" style="color:{rec_color};">{recommendation}</div></div>""",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""
                <div class="summary-box" style="border-left: 5px solid {rec_color};">
                    <div class="summary-title">Valuation Summary</div>
                    <div style="line-height:1.7; font-size:1.02rem;">
                        Company: <b>{company_name}</b><br>
                        Ticker: <b>{resolved_symbol}</b><br>
                        Market Cap: <b>{format_dollar_short(market_cap)}</b><br>
                        Sector / Industry: <b>{sector or 'N/A'}</b> / <b>{industry or 'N/A'}</b>
                    </div>
                    <div style="margin-top:12px; color:#AAB0B6; font-size:14px;">
                        Assumptions Used: EBIT Margin {ebit_margin_used*100:.1f}% | D&A {da_percent_used*100:.1f}% | CapEx {capex_percent_used*100:.1f}% | NWC {nwc_percent_used*100:.1f}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not hist_1y.empty:
                st.plotly_chart(plot_price_chart(hist_1y, company_name), use_container_width=True)

        elif page == "Market Data":
            st.markdown('<div class="section-label">Market Data</div>', unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Market Cap</div><div class="metric-value">{format_dollar_short(market_cap)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with m2:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Trailing P/E</div><div class="metric-value">{trailing_pe if trailing_pe else 'N/A'}</div></div>""",
                    unsafe_allow_html=True,
                )
            with m3:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Forward P/E</div><div class="metric-value">{forward_pe if forward_pe else 'N/A'}</div></div>""",
                    unsafe_allow_html=True,
                )
            with m4:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Current Price</div><div class="metric-value">{format_dollar_short(current_price)}</div></div>""",
                    unsafe_allow_html=True,
                )

            if not hist_1y.empty:
                st.plotly_chart(plot_price_chart(hist_1y, company_name), use_container_width=True)

            st.markdown('<div class="section-label">Peer Comparison</div>', unsafe_allow_html=True)
            st.markdown(html_table(peer_df), unsafe_allow_html=True)

        elif page == "DCF Valuation":
            st.markdown('<div class="section-label">DCF Valuation</div>', unsafe_allow_html=True)

            d1, d2, d3 = st.columns(3)
            with d1:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Enterprise Value</div><div class="metric-value">{format_dollar_short(enterprise_value)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with d2:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Implied Price</div><div class="metric-value">{format_dollar_short(implied_price)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with d3:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Recommendation</div><div class="metric-value" style="color:{rec_color};">{recommendation}</div></div>""",
                    unsafe_allow_html=True,
                )

            assumptions_df = pd.DataFrame(
                {
                    "Assumption": ["EBIT Margin", "D&A %", "CapEx %", "NWC %"],
                    "Value": [
                        f"{ebit_margin_used*100:.1f}%",
                        f"{da_percent_used*100:.1f}%",
                        f"{capex_percent_used*100:.1f}%",
                        f"{nwc_percent_used*100:.1f}%",
                    ],
                }
            )
            st.markdown(html_table(assumptions_df), unsafe_allow_html=True)

            projection_df_display = pd.DataFrame(
                {
                    "Year": list(range(1, projection_years + 1)),
                    "Projected Revenue ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["projected_revenues"]],
                    "Projected FCF ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["projected_fcfs"]],
                    "Discounted FCF ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["discounted_fcfs"]],
                }
            )
            st.markdown(html_table(projection_df_display), unsafe_allow_html=True)

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
                    name="Revenue",
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
                    name="FCF",
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

        elif page == "Comps Valuation":
            st.markdown('<div class="section-label">Comps Valuation</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Trailing P/E Implied Price</div><div class="metric-value">{format_dollar_short(trailing_comps_value)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"""<div class="metric-card"><div class="metric-label">Forward P/E Implied Price</div><div class="metric-value">{format_dollar_short(forward_comps_value)}</div></div>""",
                    unsafe_allow_html=True,
                )

            st.markdown(html_table(peer_df), unsafe_allow_html=True)

        elif page == "Sensitivity":
            st.markdown('<div class="section-label">Sensitivity</div>', unsafe_allow_html=True)

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

            st.markdown('<div class="section-label">Scenario Analysis</div>', unsafe_allow_html=True)
            st.markdown(html_table(scenario_df), unsafe_allow_html=True)

            st.markdown('<div class="section-label">Sensitivity Table</div>', unsafe_allow_html=True)
            st.markdown(html_table(sensitivity_df), unsafe_allow_html=True)

        elif page == "Export":
            st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)

            st.markdown(
                """
                <div class="summary-box">
                    <div class="summary-title">Download Model</div>
                    <div style="line-height:1.7;">
                        Export the current valuation setup into Excel, including:
                        <br>• Summary
                        <br>• DCF Projections
                        <br>• Scenario Analysis
                        <br>• Sensitivity Analysis
                        <br>• Peer Comparison
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.download_button(
                label="Download Excel Model",
                data=excel_bytes,
                file_name=f"{resolved_symbol.lower()}_valuation_model.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as e:
        st.error(f"Something went wrong: {e}")
