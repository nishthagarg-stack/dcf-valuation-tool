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
st.markdown("""
<style>
div[data-testid="stCheckbox"]*{
    color: #60A5FA !important;
    font-weight: 700 !important:
    font-size: 15px !important;
    opacity: 1 !important;
    }
    input[type="checkbox"] {
    accent-color: #3B82F6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# -----------------------------
# State init
# -----------------------------
DEFAULT_STATE = {
    "model_loaded": False,
    "revenue_auto": True,
    "revenue_growth_pct": 5.0,
    "operating_auto": True,
    "ebit_margin_pct": 18.0,
    "tax_auto": True,
    "tax_rate_pct": 21.0,
    "da_auto": True,
    "da_pct": 3.0,
    "capex_auto": True,
    "capex_pct": 4.0,
    "nwc_auto": True,
    "nwc_pct": 1.0,
    "valuation_auto": True,
    "wacc_pct": 9.0,
    "terminal_growth_pct": 2.5,
    "net_debt_auto": True,
    "net_debt": 0.0,
    "projection_years": 5,
    "shares_auto": True,
    "shares_outstanding": 1_000_000_000.0,
    "use_auto_peers": True,
    "manual_peers": "",
}
for k, v in DEFAULT_STATE.items():
    if k not in st.session_state:
        st.session_state[k] = v


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&family=Playfair+Display:ital,wght@1,700&display=swap" rel="stylesheet">

    <style>
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at top left, #0F1B3D 0%, #0B1020 45%, #070B14 100%);
        color: #FAFAFA;
    }

    .block-container {
        padding-top: 1.7rem;
        padding-bottom: 2rem;
    }

    .brand-container {
        text-align: center;
        margin-bottom: 1.2rem;
        padding-top: 1.2rem;
    }

    .ng-italic {
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 48px;
        font-weight: 700;
        color: #F4F8FF;
        line-height: 1.2;
        margin-bottom: 8px;
        letter-spacing: 1px;
        text-shadow: 0 0 14px rgba(96,165,250,0.18);
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
        color: #BFC7D5;
        font-weight: 500;
        letter-spacing: 0.5px;
    }

    .section-label {
        font-size: 1.75rem;
        font-weight: 900;
        margin-top: 1rem;
        margin-bottom: 1rem;
        color: #FFFFFF;
    }

    .subsection-label {
        font-size: 1.15rem;
        font-weight: 800;
        color: #F3F4F6;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
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
        color: #D1D5DB;
        font-size: 0.95rem;
        font-weight: 700;
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
        color: #F9FAFB;
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
        color: #E5E7EB;
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

    label, .stMarkdown, .stText, .stNumberInput label {
        color: #E5E7EB !important;
        font-weight: 600 !important;
    }

    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stCheckbox"] label {
        color: #60A5FA !important;
        font-weight: 700 !important;
        font-size: 14px !important;
    }
    div[data-testid="stCheckbox"] label > DIV P {
        color: #BBD7F7 !important;
    }

    h3, h4 {
        color: #93C5FD !important;
        font-weight: 800 !important;
    }

    .stTextInput > div > div > input,
    .stNumberInput input,
    .stSelectbox > div > div {
        background-color: #141B2D !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: 1px solid #25304A !important;
    }

    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton > a {
        background: linear-gradient(90deg, #38BDF8 0%, #60A5FA 100%) !important;
        color: #08101F !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 0.65rem 1.2rem !important;
        border: none !important;
        text-decoration: none !important;
    }

    section[data-testid="stSidebar"] {
        background: rgba(10, 14, 25, 0.96);
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] div {
        color: #F3F4F6 !important;
    }

    .sidebar-brand {
        text-align: center;
        margin-bottom: 1rem;
        padding-top: 0.6rem;
    }

    .sidebar-ng {
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 34px;
        color: #F4F8FF;
        line-height: 1.2;
        margin-bottom: 4px;
        text-shadow: 0 0 10px rgba(96,165,250,0.18);
    }

    .small-note {
        color: #CBD5E1;
        font-size: 13px;
    }

    .home-card {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 22px;
        padding: 1.4rem;
        background: rgba(17, 24, 39, 0.84);
        margin-bottom: 1rem;
    }

    .home-intro {
        font-size: 1.05rem;
        line-height: 1.8;
        color: #E8EEF8;
        margin-bottom: 1rem;
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
        <div class="ng-italic">NG</div>
        <div class="title-text">Valuation Lab</div>
        <div class="subtitle-text">by Nishtha Garg</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Helper functions
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


def get_row_value(df: pd.DataFrame, possible_rows: List[str]) -> Optional[float]:
    if df is None or df.empty:
        return None
    for row_name in possible_rows:
        if row_name in df.index:
            try:
                return float(df.loc[row_name].iloc[0])
            except Exception:
                continue
    return None


def calculate_revenue_cagr(financials: pd.DataFrame) -> Optional[float]:
    try:
        revenues = financials.loc["Total Revenue"].dropna()
        if len(revenues) < 4:
            return None
        latest = float(revenues.iloc[0])
        three_year_old = float(revenues.iloc[3])
        if latest <= 0 or three_year_old <= 0:
            return None
        return (latest / three_year_old) ** (1 / 3) - 1
    except Exception:
        return None


def estimate_tax_rate(financials: pd.DataFrame) -> Optional[float]:
    tax_expense = get_row_value(financials, ["Tax Provision", "Income Tax Expense"])
    pretax_income = get_row_value(financials, ["Pretax Income", "Income Before Tax", "Ebt", "Pre Tax Income"])
    if tax_expense is None or pretax_income is None or pretax_income == 0:
        return None
    rate = abs(tax_expense / pretax_income)
    if 0 <= rate <= 0.5:
        return rate
    return None


def estimate_net_debt(balance_sheet: pd.DataFrame) -> Optional[float]:
    total_debt = get_row_value(
        balance_sheet,
        ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt", "Current Debt"],
    )
    cash = get_row_value(
        balance_sheet,
        ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash", "Cash And Short Term Investments"],
    )

    if total_debt is None and cash is None:
        return None

    total_debt = total_debt or 0.0
    cash = cash or 0.0
    return total_debt - cash


def estimate_wacc(info: dict, financials: pd.DataFrame, balance_sheet: pd.DataFrame, tax_rate_fallback: float) -> float:
    beta = info.get("beta")
    risk_free_rate = 0.0425
    equity_risk_premium = 0.055

    cost_of_equity = risk_free_rate + (beta * equity_risk_premium if beta is not None else equity_risk_premium)

    interest_expense = get_row_value(financials, ["Interest Expense", "Interest Expense Non Operating"])
    total_debt = get_row_value(balance_sheet, ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"])

    if interest_expense is not None and total_debt not in (None, 0):
        cost_of_debt = min(abs(interest_expense) / abs(total_debt), 0.12)
    else:
        cost_of_debt = 0.05

    market_cap = info.get("marketCap")
    debt = total_debt or 0.0
    equity = market_cap or 0.0

    if equity + debt == 0:
        return 0.09

    tax_rate_used = tax_rate_fallback if tax_rate_fallback is not None else 0.21
    wacc = (equity / (equity + debt)) * cost_of_equity + (debt / (equity + debt)) * cost_of_debt * (1 - tax_rate_used)
    return max(0.05, min(wacc, 0.15))
    # -----------------------------
# Peer logic
# -----------------------------
INDUSTRY_PEER_RULES = {
    "beauty": ["EL", "COTY", "SBH", "TGT", "COST"],
    "cosmetic": ["EL", "COTY", "SBH", "TGT", "COST"],
    "specialty retail": ["ULTA", "BBY", "ROST", "TJX", "TGT"],
    "apparel retail": ["ROST", "TJX", "BURL", "GPS", "TGT"],
    "discount stores": ["DG", "DLTR", "WMT", "TGT", "COST"],
    "semiconductor": ["NVDA", "AMD", "AVGO", "QCOM", "INTC"],
    "software": ["MSFT", "ORCL", "CRM", "ADBE", "NOW"],
    "internet content": ["GOOGL", "META", "NFLX", "SNAP", "PINS"],
    "banks": ["JPM", "BAC", "C", "WFC", "GS"],
    "oil": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "airline": ["DAL", "UAL", "AAL", "LUV", "ALK"],
    "restaurant": ["MCD", "CMG", "YUM", "SBUX", "DPZ"],
    "home improvement": ["HD", "LOW", "WSM", "RH", "FND"],
    "ecommerce": ["AMZN", "SHOP", "EBAY", "BABA", "MELI"],
    "auto": ["TSLA", "GM", "F", "RIVN", "LCID"],
}

SECTOR_FALLBACK_PEERS = {
    "Technology": ["MSFT", "AAPL", "NVDA", "ORCL", "CRM"],
    "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "TMUS"],
    "Financial Services": ["JPM", "BAC", "GS", "MS", "WFC"],
    "Consumer Defensive": ["WMT", "COST", "PG", "KO", "PEP"],
    "Consumer Cyclical": ["TGT", "COST", "HD", "LOW", "ROST"],
    "Healthcare": ["UNH", "JNJ", "PFE", "MRK", "ABBV"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Industrials": ["CAT", "DE", "GE", "HON", "MMM"],
}


def suggest_peers(symbol: str, sector: Optional[str], industry: Optional[str], company_name: Optional[str]) -> List[str]:
    symbol = normalize_symbol(symbol)
    combined = " ".join(
        [
            str(company_name or "").lower(),
            str(industry or "").lower(),
            str(sector or "").lower(),
        ]
    )

    for keyword, peers in INDUSTRY_PEER_RULES.items():
        if keyword in combined:
            return [p for p in peers if p != symbol]

    if sector in SECTOR_FALLBACK_PEERS:
        return [p for p in SECTOR_FALLBACK_PEERS[sector] if p != symbol]

    return [p for p in ["TGT", "COST", "HD", "LOW", "ROST"] if p != symbol]


# -----------------------------
# Data loaders
# -----------------------------
@st.cache_data(ttl=1800)
def resolve_company_input(query: str) -> dict:
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Please enter a company name or ticker.")

    normalized = normalize_symbol(clean_query)

    if is_probable_ticker(normalized):
        return {"symbol": normalized, "matched_name": normalized, "source": "ticker"}

    try:
        search = yf.Search(query=clean_query, max_results=8)
        quotes = getattr(search, "quotes", []) or []
        if quotes:
            best = quotes[0]
            symbol = normalize_symbol(best.get("symbol", clean_query.upper()))
            matched_name = best.get("shortname") or best.get("longname") or best.get("displayName") or symbol
            return {"symbol": symbol, "matched_name": matched_name, "source": "search"}
    except Exception:
        pass

    return {"symbol": normalized, "matched_name": clean_query, "source": "fallback"}


@st.cache_data(ttl=1800)
def get_market_and_financial_data(symbol: str, chart_period: str) -> dict:
    symbol = normalize_symbol(symbol)
    ticker = yf.Ticker(symbol)

    financials = ticker.financials
    cashflow = ticker.cashflow
    balance_sheet = ticker.balance_sheet
    hist_chart = ticker.history(period=chart_period)
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
    info = {}

    try:
        info = ticker.info
        company_name = info.get("longName") or info.get("shortName") or info.get("displayName") or symbol
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
        "balance_sheet": balance_sheet,
        "hist_chart": hist_chart,
        "info": info,
    }


@st.cache_data(ttl=1800)
def get_peer_metrics(tickers: Tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for t in tickers:
        t_norm = normalize_symbol(t)
        try:
            data = get_market_and_financial_data(t_norm, "1y")
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


@st.cache_data(ttl=1800)
def get_normalized_performance_chart_data(main_symbol: str, peer_symbols: Tuple[str, ...], period: str = "1y") -> pd.DataFrame:
    symbols = [main_symbol] + list(peer_symbols)
    rows = []

    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(period=period)
            if hist.empty or "Close" not in hist.columns:
                continue
            closes = hist["Close"].dropna()
            if closes.empty:
                continue
            base = closes.iloc[0]
            if base == 0:
                continue
            normalized = (closes / base) * 100
            for dt, value in normalized.items():
                rows.append({"Date": dt, "Ticker": sym, "Normalized": float(value)})
        except Exception:
            continue

    return pd.DataFrame(rows)


# -----------------------------
# Core model
# -----------------------------
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


def build_forecast_model(
    base_revenue,
    ebit_margin,
    da_percent,
    capex_percent,
    nwc_percent,
    tax_rate,
    growth_rate,
    projection_years,
):
    rows = []
    revenue_proj = base_revenue

    for year in range(1, projection_years + 1):
        revenue_proj = revenue_proj * (1 + growth_rate)
        ebit = revenue_proj * ebit_margin
        taxes = ebit * tax_rate
        nopat = ebit * (1 - tax_rate)
        da = revenue_proj * da_percent
        capex = revenue_proj * capex_percent
        change_nwc = revenue_proj * nwc_percent
        fcf = nopat + da - capex - change_nwc

        rows.append(
            {
                "Year": year,
                "Revenue ($M)": revenue_proj / 1_000_000,
                "EBIT ($M)": ebit / 1_000_000,
                "Taxes ($M)": taxes / 1_000_000,
                "NOPAT ($M)": nopat / 1_000_000,
                "D&A ($M)": da / 1_000_000,
                "CapEx ($M)": capex / 1_000_000,
                "Change in NWC ($M)": change_nwc / 1_000_000,
                "FCF ($M)": fcf / 1_000_000,
            }
        )

    forecast_df = pd.DataFrame(rows)
    income_df = forecast_df[["Year", "Revenue ($M)", "EBIT ($M)", "Taxes ($M)", "NOPAT ($M)"]].copy()
    cashflow_df = forecast_df[["Year", "NOPAT ($M)", "D&A ($M)", "CapEx ($M)", "Change in NWC ($M)", "FCF ($M)"]].copy()
    return forecast_df, income_df, cashflow_df


def build_balance_sheet_lite(balance_sheet: pd.DataFrame, forecast_df: pd.DataFrame):
    starting_cash = get_row_value(
        balance_sheet,
        ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash", "Cash And Short Term Investments"],
    ) or 0.0
    starting_debt = get_row_value(
        balance_sheet,
        ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt", "Current Debt"],
    ) or 0.0
    starting_ppne = get_row_value(
        balance_sheet,
        ["Net PPE", "Property Plant Equipment Net", "Gross PPE"],
    ) or 0.0

    rows = []
    cumulative_fcf = 0.0

    for _, row in forecast_df.iterrows():
        cumulative_fcf += row["FCF ($M)"] * 1_000_000
        projected_cash = max(starting_cash + cumulative_fcf, 0.0)
        projected_debt = starting_debt
        projected_net_debt = projected_debt - projected_cash
        projected_nwc = row["Change in NWC ($M)"] * 1_000_000
        projected_ppne = max(starting_ppne + row["CapEx ($M)"] * 1_000_000 - row["D&A ($M)"] * 1_000_000, 0.0)

        rows.append(
            {
                "Year": int(row["Year"]),
                "Cash ($M)": projected_cash / 1_000_000,
                "Debt ($M)": projected_debt / 1_000_000,
                "Net Debt ($M)": projected_net_debt / 1_000_000,
                "Working Capital Build ($M)": projected_nwc / 1_000_000,
                "PP&E ($M)": projected_ppne / 1_000_000,
            }
        )

    return pd.DataFrame(rows)
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
    income_df: pd.DataFrame,
    cashflow_df: pd.DataFrame,
    balance_df: pd.DataFrame,
) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        projection_df.to_excel(writer, sheet_name="DCF Projections", index=False)
        scenario_df.to_excel(writer, sheet_name="Scenarios", index=False)
        sensitivity_df.to_excel(writer, sheet_name="Sensitivity", index=False)
        peers_df.to_excel(writer, sheet_name="Peers", index=False)
        income_df.to_excel(writer, sheet_name="Income Statement Forecast", index=False)
        cashflow_df.to_excel(writer, sheet_name="Cash Flow Forecast", index=False)
        balance_df.to_excel(writer, sheet_name="Balance Sheet Forecast", index=False)
    return output.getvalue()


# -----------------------------
# Charts
# -----------------------------
def plot_price_chart(hist_df: pd.DataFrame, company_name: str, chart_label: str):
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
        title=dict(
            text=f"{company_name} Price Chart({chart_label})",
            font=dict(size=20, color="#D4AF37")
        ),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(title="Date", gridcolor="#243041"),
        yaxis=dict(title="Share Price (USD)", gridcolor="#243041"),
        height=380,
    )
    return fig


def plot_peer_pe_chart(peer_df: pd.DataFrame):
    pe_df = peer_df.copy()
    pe_df["Trailing P/E Numeric"] = pd.to_numeric(pe_df["Trailing P/E"], errors="coerce")
    pe_df = pe_df.dropna(subset=["Trailing P/E Numeric"])
    if pe_df.empty:
        return None

    fig = go.Figure(
        data=[
            go.Bar(
                x=pe_df["Ticker"],
                y=pe_df["Trailing P/E Numeric"],
                marker_color="#8B5CF6",
            )
        ]
    )
    fig.update_layout(
        title=dict(
            text="Peer Trailing P/E Comparison",
            font=dict(size=20, color="#D4AF37")
        ),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Peer",
        yaxis_title="Trailing P/E (x)",
        height=360,
    )
    return fig


def plot_income_chart(forecast_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast_df["Year"], y=forecast_df["Revenue ($M)"], mode="lines+markers", name="Revenue ($M)", line=dict(color="#38BDF8", width=4)))
    fig.add_trace(go.Scatter(x=forecast_df["Year"], y=forecast_df["EBIT ($M)"], mode="lines+markers", name="EBIT ($M)", line=dict(color="#F59E0B", width=4)))
    fig.update_layout(
        title="Revenue vs EBIT Forecast",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Year",
        yaxis_title="$M",
        height=380,
    )
    return fig


def plot_cashflow_chart(forecast_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast_df["Year"], y=forecast_df["FCF ($M)"], mode="lines+markers", name="FCF ($M)", line=dict(color="#22C55E", width=4)))
    fig.add_trace(go.Bar(x=forecast_df["Year"], y=forecast_df["CapEx ($M)"], name="CapEx ($M)", marker_color="#8B5CF6", opacity=0.75))
    fig.update_layout(
        title="Free Cash Flow Forecast",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Year",
        yaxis_title="$M",
        height=380,
        barmode="group",
    )
    return fig


def plot_balance_chart(balance_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=balance_df["Year"], y=balance_df["Cash ($M)"], mode="lines+markers", name="Cash ($M)", line=dict(color="#38BDF8", width=4)))
    fig.add_trace(go.Scatter(x=balance_df["Year"], y=balance_df["Debt ($M)"], mode="lines+markers", name="Debt ($M)", line=dict(color="#EF4444", width=4)))
    fig.add_trace(go.Scatter(x=balance_df["Year"], y=balance_df["Net Debt ($M)"], mode="lines+markers", name="Net Debt ($M)", line=dict(color="#F59E0B", width=4)))
    fig.update_layout(
        title="Balance Sheet Trend",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Year",
        yaxis_title="$M",
        height=380,
    )
    return fig


def plot_stock_vs_peers_chart(df: pd.DataFrame):
    if df.empty:
        return None

    fig = go.Figure()
    for ticker in df["Ticker"].dropna().unique():
        sub = df[df["Ticker"] == ticker]
        fig.add_trace(
            go.Scatter(
                x=sub["Date"],
                y=sub["Normalized"],
                mode="lines",
                name=ticker,
                line=dict(width=3 if ticker == df["Ticker"].iloc[0] else 2),
            )
        )

    fig.update_layout(
        title=dict(
            text="Stock vs Peers Performance (Indexed to 100 at Start Date)",
            font=dict(size=20, color="#D4AF37")
        ),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#111827",
        font=dict(color="#F9FAFB"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Date",
        yaxis_title="Normalized Price (Base = 100)",
        legend=dict(
            font=dict(size=14, color="white"),
            orientation="h",
            x=0,
            y=1.02,
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)"
        ),
        height=420,
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

    chart_range_map = {
        "1M": "1mo",
        "3M": "3mo",
        "6M": "6mo",
        "1Y": "1y",
        "3Y": "3y",
        "5Y": "5y",
        "Max": "max",
    }
    chart_label = st.selectbox("Stock Price Chart Range", list(chart_range_map.keys()), index=3)
    chart_period = chart_range_map[chart_label]

    page = st.radio(
        "Navigation",
        [
            "Home",
            "Overview",
            "Market Data",
            "Income Statement Forecast",
            "Balance Sheet Forecast",
            "Cash Flow Statement Forecast",
            "DCF Valuation",
            "Comps Valuation",
            "Sensitivity",
            "Export",
        ],
        index=0,
    )

    if st.button("Run Model", use_container_width=True):
        st.session_state["model_loaded"] = True


# -----------------------------
# Home page before model
# -----------------------------
if page == "Home" and not st.session_state["model_loaded"]:
    st.markdown('<div class="section-label">Welcome!</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="home-card">
            <div class="home-intro">
                Hello everyone, I’m <b>Nishtha (Nina) Garg</b>, a Financial Analytics graduate student at San Jose State University.
                I built <b>Valuation Lab</b> to make valuation and financial modeling more interactive, intuitive, and accessible.
                I hope you enjoy exploring the app.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button("Connect on LinkedIn", "https://www.linkedin.com/in/nishthagarg19", use_container_width=True)
    with c2:
        st.link_button("Email Me", "mailto:ninagarg19@gmail.com", use_container_width=True)
    with c3:
        st.link_button("View Portfolio", "https://gargnishtha1907.wixsite.com/my-site-1", use_container_width=True)

    st.info("Use the left sidebar to enter a company and click **Run Model** when you're ready.")

elif not st.session_state["model_loaded"]:
    st.info("Enter a company in the sidebar and click **Run Model** to load the platform.")

else:
    try:
        resolved = resolve_company_input(company_input)
        resolved_symbol = resolved["symbol"]

        data = get_market_and_financial_data(resolved_symbol, chart_period)
        company_name = data["company_name"]
        current_price = data["current_price"] or 0
        shares_outstanding_market = data["shares_outstanding"]
        market_cap = data["market_cap"]
        trailing_pe = data["trailing_pe"]
        forward_pe = data["forward_pe"]
        trailing_eps = data["trailing_eps"]
        forward_eps = data["forward_eps"]
        sector = data["sector"]
        industry = data["industry"]
        financials = data["financials"]
        cashflow = data["cashflow"]
        balance_sheet = data["balance_sheet"]
        hist_chart = data["hist_chart"]
        info = data["info"]

        revenue = financials.loc["Total Revenue"].iloc[0]
        operating_income = financials.loc["Operating Income"].iloc[0]
        depreciation = cashflow.loc["Depreciation And Amortization"].iloc[0]
        capex = abs(cashflow.loc["Capital Expenditure"].iloc[0])

        historical_revenue_cagr = calculate_revenue_cagr(financials)
        auto_tax_rate = estimate_tax_rate(financials)
        auto_net_debt = estimate_net_debt(balance_sheet)
        auto_terminal_growth = 0.025
        auto_wacc = estimate_wacc(info, financials, balance_sheet, auto_tax_rate if auto_tax_rate is not None else 0.21)

        auto_ebit_margin = operating_income / revenue
        auto_da_percent = depreciation / revenue
        auto_capex_percent = capex / revenue
        auto_nwc_percent = 0.0

        latest_historical_fcf = ((operating_income * (1 - (auto_tax_rate if auto_tax_rate is not None else 0.21))) + depreciation - capex)
        fcf_margin = latest_historical_fcf / revenue if revenue else None
        net_debt_to_market_cap = (auto_net_debt / market_cap) if auto_net_debt is not None and market_cap not in (None, 0) else None
                # -----------------------------
        # Inputs live on relevant pages
        # -----------------------------
        if page == "Income Statement Forecast":
            st.markdown('<div class="section-label">Income Statement Forecast</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.session_state["revenue_auto"] = st.checkbox(
                    "Use historical 3-year revenue CAGR automatically",
                    value=st.session_state["revenue_auto"],
                )
                st.session_state["revenue_growth_pct"] = st.number_input(
                    "Revenue Growth Rate (%)",
                    value=float(st.session_state["revenue_growth_pct"]),
                    step=0.5,
                )
            with c2:
                st.session_state["operating_auto"] = st.checkbox(
                    "Use latest operating assumptions automatically",
                    value=st.session_state["operating_auto"],
                )
                st.session_state["ebit_margin_pct"] = st.number_input(
                    "EBIT Margin (%)",
                    value=float(st.session_state["ebit_margin_pct"]),
                    step=0.5,
                )
                st.session_state["tax_auto"] = st.checkbox(
                    "Use latest tax rate automatically",
                    value=st.session_state["tax_auto"],
                )
                st.session_state["tax_rate_pct"] = st.number_input(
                    "Tax Rate (%)",
                    value=float(st.session_state["tax_rate_pct"]),
                    step=0.5,
                )

            auto_table = pd.DataFrame(
                {
                    "Automatic Input": ["Revenue Growth", "EBIT Margin", "Tax Rate"],
                    "Current Auto Value": [
                        f"{historical_revenue_cagr*100:.2f}%" if historical_revenue_cagr is not None else "N/A",
                        f"{auto_ebit_margin*100:.2f}%",
                        f"{auto_tax_rate*100:.2f}%" if auto_tax_rate is not None else "N/A",
                    ],
                }
            )
            st.markdown(html_table(auto_table), unsafe_allow_html=True)

        elif page == "Balance Sheet Forecast":
            st.markdown('<div class="section-label">Balance Sheet Forecast</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.session_state["nwc_auto"] = st.checkbox(
                    "Use latest working capital assumption automatically",
                    value=st.session_state["nwc_auto"],
                )
                st.session_state["nwc_pct"] = st.number_input(
                    "Change in NWC (% of Revenue)",
                    value=float(st.session_state["nwc_pct"]),
                    step=0.5,
                )
                st.session_state["net_debt_auto"] = st.checkbox(
                    "Use latest net debt automatically",
                    value=st.session_state["net_debt_auto"],
                )
                st.session_state["net_debt"] = st.number_input(
                    "Net Debt ($)",
                    value=float(st.session_state["net_debt"]),
                    step=1000000.0,
                )
            with c2:
                st.session_state["shares_auto"] = st.checkbox(
                    "Use latest shares outstanding automatically",
                    value=st.session_state["shares_auto"],
                )
                st.session_state["shares_outstanding"] = st.number_input(
                    "Shares Outstanding",
                    value=float(st.session_state["shares_outstanding"]),
                    step=1000000.0,
                )

            auto_table = pd.DataFrame(
                {
                    "Automatic Input": ["NWC %", "Net Debt", "Shares Outstanding"],
                    "Current Auto Value": [
                        f"{auto_nwc_percent*100:.2f}%",
                        format_dollar_short(auto_net_debt) if auto_net_debt is not None else "N/A",
                        f"{shares_outstanding_market:,.0f}" if shares_outstanding_market not in (None, 0) else "N/A",
                    ],
                }
            )
            st.markdown(html_table(auto_table), unsafe_allow_html=True)

        elif page == "Cash Flow Statement Forecast":
            st.markdown('<div class="section-label">Cash Flow Statement Forecast</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.session_state["da_auto"] = st.checkbox(
                    "Use latest D&A assumption automatically",
                    value=st.session_state["da_auto"],
                )
                st.session_state["da_pct"] = st.number_input(
                    "D&A (% of Revenue)",
                    value=float(st.session_state["da_pct"]),
                    step=0.5,
                )
            with c2:
                st.session_state["capex_auto"] = st.checkbox(
                    "Use latest CapEx assumption automatically",
                    value=st.session_state["capex_auto"],
                )
                st.session_state["capex_pct"] = st.number_input(
                    "CapEx (% of Revenue)",
                    value=float(st.session_state["capex_pct"]),
                    step=0.5,
                )

            auto_table = pd.DataFrame(
                {
                    "Automatic Input": ["D&A %", "CapEx %"],
                    "Current Auto Value": [
                        f"{auto_da_percent*100:.2f}%",
                        f"{auto_capex_percent*100:.2f}%",
                    ],
                }
            )
            st.markdown(html_table(auto_table), unsafe_allow_html=True)

        elif page == "DCF Valuation":
            st.markdown('<div class="section-label">DCF Valuation</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.session_state["valuation_auto"] = st.checkbox(
                    "Use estimated valuation assumptions automatically",
                    value=st.session_state["valuation_auto"],
                )
                st.session_state["wacc_pct"] = st.number_input(
                    "WACC (%)",
                    value=float(st.session_state["wacc_pct"]),
                    step=0.5,
                )
                st.session_state["terminal_growth_pct"] = st.number_input(
                    "Terminal Growth Rate (%)",
                    value=float(st.session_state["terminal_growth_pct"]),
                    step=0.5,
                )
            with c2:
                st.session_state["projection_years"] = int(
                    st.number_input(
                        "Projection Years",
                        min_value=3,
                        max_value=10,
                        value=int(st.session_state["projection_years"]),
                        step=1,
                    )
                )

            auto_table = pd.DataFrame(
                {
                    "Automatic Input": ["WACC", "Terminal Growth"],
                    "Current Auto Value": [
                        f"{auto_wacc*100:.2f}%",
                        f"{auto_terminal_growth*100:.2f}%",
                    ],
                }
            )
            st.markdown(html_table(auto_table), unsafe_allow_html=True)

        elif page == "Comps Valuation":
            st.markdown('<div class="section-label">Comps Valuation</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                st.session_state["use_auto_peers"] = st.checkbox(
                    "Use suggested peers automatically",
                    value=st.session_state["use_auto_peers"],
                )
            with c2:
                st.session_state["manual_peers"] = st.text_input(
                    "Custom Peer Tickers (comma-separated)",
                    value=st.session_state["manual_peers"],
                )

        # -----------------------------
        # Use assumptions
        # -----------------------------
        revenue_growth_used = historical_revenue_cagr if (st.session_state["revenue_auto"] and historical_revenue_cagr is not None) else st.session_state["revenue_growth_pct"] / 100
        ebit_margin_used = auto_ebit_margin if st.session_state["operating_auto"] else st.session_state["ebit_margin_pct"] / 100
        tax_rate_used = auto_tax_rate if (st.session_state["tax_auto"] and auto_tax_rate is not None) else st.session_state["tax_rate_pct"] / 100
        da_percent_used = auto_da_percent if st.session_state["da_auto"] else st.session_state["da_pct"] / 100
        capex_percent_used = auto_capex_percent if st.session_state["capex_auto"] else st.session_state["capex_pct"] / 100
        nwc_percent_used = auto_nwc_percent if st.session_state["nwc_auto"] else st.session_state["nwc_pct"] / 100

        wacc_used = auto_wacc if st.session_state["valuation_auto"] else st.session_state["wacc_pct"] / 100
        terminal_growth_used = auto_terminal_growth if st.session_state["valuation_auto"] else st.session_state["terminal_growth_pct"] / 100
        net_debt_used = auto_net_debt if (st.session_state["net_debt_auto"] and auto_net_debt is not None) else st.session_state["net_debt"]
        projection_years = int(st.session_state["projection_years"])

        shares_outstanding_used = shares_outstanding_market if (st.session_state["shares_auto"] and shares_outstanding_market not in (None, 0)) else st.session_state["shares_outstanding"]
        if shares_outstanding_used in (None, 0):
            raise ValueError("Could not retrieve shares outstanding for this company.")

        base_results = run_dcf(
            base_revenue=revenue,
            ebit_margin=ebit_margin_used,
            da_percent=da_percent_used,
            capex_percent=capex_percent_used,
            nwc_percent=nwc_percent_used,
            shares_outstanding=shares_outstanding_used,
            growth_rate=revenue_growth_used,
            tax_rate=tax_rate_used,
            wacc=wacc_used,
            terminal_growth=terminal_growth_used,
            net_debt=net_debt_used,
            projection_years=projection_years,
        )

        forecast_df, income_statement_df, cashflow_forecast_df = build_forecast_model(
            base_revenue=revenue,
            ebit_margin=ebit_margin_used,
            da_percent=da_percent_used,
            capex_percent=capex_percent_used,
            nwc_percent=nwc_percent_used,
            tax_rate=tax_rate_used,
            growth_rate=revenue_growth_used,
            projection_years=projection_years,
        )

        balance_df = build_balance_sheet_lite(balance_sheet, forecast_df)

        implied_price = base_results["implied_price"]
        enterprise_value = base_results["enterprise_value"]
        upside_downside = ((implied_price - current_price) / current_price) * 100 if current_price else 0
        recommendation, rec_color = get_recommendation(upside_downside)

        auto_peer_list = suggest_peers(resolved_symbol, sector, industry, company_name)
        peer_list = auto_peer_list if st.session_state["use_auto_peers"] or not st.session_state["manual_peers"].strip() else [normalize_symbol(x) for x in st.session_state["manual_peers"].split(",") if x.strip()]
        peer_df = get_peer_metrics(tuple(peer_list))

        peer_raw_rows = []
        for peer in peer_list:
            try:
                pdata = get_market_and_financial_data(peer, "1y")
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

        valid_comps_values = [x for x in [trailing_comps_value, forward_comps_value] if x is not None]
        comps_price = sum(valid_comps_values) / len(valid_comps_values) if valid_comps_values else None
        blended_price = ((implied_price + comps_price) / 2) if comps_price is not None else implied_price

        scenario_inputs = {
            "Bear": {"growth": max(revenue_growth_used - 0.02, 0), "wacc": wacc_used + 0.01, "tg": max(terminal_growth_used - 0.005, 0)},
            "Base": {"growth": revenue_growth_used, "wacc": wacc_used, "tg": terminal_growth_used},
            "Bull": {"growth": revenue_growth_used + 0.02, "wacc": max(wacc_used - 0.01, 0.01), "tg": terminal_growth_used + 0.005},
        }

        scenario_rows = []
        scenario_prices = {}
        for scenario_name, vals in scenario_inputs.items():
            try:
                scenario_result = run_dcf(
                    base_revenue=revenue,
                    ebit_margin=ebit_margin_used,
                    da_percent=da_percent_used,
                    capex_percent=capex_percent_used,
                    nwc_percent=nwc_percent_used,
                    shares_outstanding=shares_outstanding_used,
                    growth_rate=vals["growth"],
                    tax_rate=tax_rate_used,
                    wacc=vals["wacc"],
                    terminal_growth=vals["tg"],
                    net_debt=net_debt_used,
                    projection_years=projection_years,
                )
                scenario_prices[scenario_name] = scenario_result["implied_price"]
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
                scenario_prices[scenario_name] = None
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

        valuation_range_low = scenario_prices.get("Bear")
        valuation_range_mid = scenario_prices.get("Base")
        valuation_range_high = scenario_prices.get("Bull")

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
                        shares_outstanding=shares_outstanding_used,
                        growth_rate=revenue_growth_used,
                        tax_rate=tax_rate_used,
                        wacc=w,
                        terminal_growth=tg,
                        net_debt=net_debt_used,
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

        perf_df = get_normalized_performance_chart_data(resolved_symbol, tuple(peer_list[:4]), "1y")
        perf_fig = plot_stock_vs_peers_chart(perf_df)

        summary_df = pd.DataFrame(
            [
                {
                    "Company": company_name,
                    "Ticker": resolved_symbol,
                    "Current Price": current_price,
                    "DCF Price": implied_price,
                    "Comps Price": comps_price,
                    "Blended Price": blended_price,
                    "Upside/Downside %": upside_downside,
                    "Recommendation": recommendation,
                    "Enterprise Value": enterprise_value,
                    "Market Cap": market_cap,
                    "Sector": sector,
                    "Industry": industry,
                    "Revenue Growth %": revenue_growth_used * 100,
                    "Tax Rate %": tax_rate_used * 100,
                    "WACC %": wacc_used * 100,
                    "Terminal Growth %": terminal_growth_used * 100,
                    "EBIT Margin %": ebit_margin_used * 100,
                    "D&A %": da_percent_used * 100,
                    "CapEx %": capex_percent_used * 100,
                    "NWC %": nwc_percent_used * 100,
                    "Net Debt": net_debt_used,
                    "Shares Outstanding": shares_outstanding_used,
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
            income_df=income_statement_df,
            cashflow_df=cashflow_forecast_df,
            balance_df=balance_df,
        )

        st.caption(f"Matched Input: {company_name} ({resolved_symbol})")
        st.caption(f"Suggested Peers: {', '.join(peer_list)}")

        if page == "Home":
            st.markdown('<div class="section-label">Welcome!</div>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="home-card">
                    <div class="home-intro">
                        Hello everyone, I’m <b>Nishtha (Nina) Garg</b>, a Financial Analytics graduate student at San Jose State University.
                        I built <b>Valuation Lab</b> to make valuation and financial modeling more interactive, intuitive, and accessible.
                        I hope you enjoy exploring the app.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                st.link_button("Connect on LinkedIn", "https://www.linkedin.com/in/nishthagarg19", use_container_width=True)
            with c2:
                st.link_button("Email Me", "mailto:ninagarg19@gmail.com", use_container_width=True)
            with c3:
                st.link_button("View Portfolio", "https://gargnishtha1907.wixsite.com/my-site-1", use_container_width=True)

        elif page == "Overview":
            st.markdown('<div class="section-label">Overview</div>', unsafe_allow_html=True)

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Current Price</div><div class="metric-value">{format_dollar_short(current_price)}</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">DCF Price</div><div class="metric-value">{format_dollar_short(implied_price)}</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Comps Price</div><div class="metric-value">{format_dollar_short(comps_price)}</div></div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Blended Price</div><div class="metric-value">{format_dollar_short(blended_price)}</div></div>""", unsafe_allow_html=True)
            with c5:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Recommendation</div><div class="metric-value" style="color:{rec_color};">{recommendation}</div></div>""", unsafe_allow_html=True)

            r1, r2, r3 = st.columns(3)
            with r1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Low Valuation</div><div class="metric-value">{format_dollar_short(valuation_range_low)}</div></div>""", unsafe_allow_html=True)
            with r2:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Base Valuation</div><div class="metric-value">{format_dollar_short(valuation_range_mid)}</div></div>""", unsafe_allow_html=True)
            with r3:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">High Valuation</div><div class="metric-value">{format_dollar_short(valuation_range_high)}</div></div>""", unsafe_allow_html=True)

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
                    <div style="margin-top:12px; color:#E5E7EB; font-size:14px;">
                        Assumptions Used: Revenue Growth {revenue_growth_used*100:.1f}% | WACC {wacc_used*100:.1f}% | Terminal Growth {terminal_growth_used*100:.1f}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if not hist_chart.empty:
                st.plotly_chart(plot_price_chart(hist_chart, company_name, chart_label), use_container_width=True)

        elif page == "Market Data":
            st.markdown('<div class="section-label">Market Data</div>', unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Market Cap</div><div class="metric-value">{format_dollar_short(market_cap)}</div></div>""", unsafe_allow_html=True)
            with m2:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Trailing P/E</div><div class="metric-value">{trailing_pe if trailing_pe else 'N/A'}</div></div>""", unsafe_allow_html=True)
            with m3:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Forward P/E</div><div class="metric-value">{forward_pe if forward_pe else 'N/A'}</div></div>""", unsafe_allow_html=True)
            with m4:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Current Price</div><div class="metric-value">{format_dollar_short(current_price)}</div></div>""", unsafe_allow_html=True)

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">3Y Revenue CAGR</div><div class="metric-value">{format_percent((historical_revenue_cagr or 0)*100 if historical_revenue_cagr is not None else None)}</div></div>""", unsafe_allow_html=True)
            with k2:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">EBIT Margin</div><div class="metric-value">{format_percent(auto_ebit_margin*100)}</div></div>""", unsafe_allow_html=True)
            with k3:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">FCF Margin</div><div class="metric-value">{format_percent(fcf_margin*100 if fcf_margin is not None else None)}</div></div>""", unsafe_allow_html=True)
            with k4:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Net Debt / Market Cap</div><div class="metric-value">{format_percent(net_debt_to_market_cap*100 if net_debt_to_market_cap is not None else None)}</div></div>""", unsafe_allow_html=True)

            if not hist_chart.empty:
                st.plotly_chart(plot_price_chart(hist_chart, company_name, chart_label), use_container_width=True)

            if perf_fig is not None:
                st.plotly_chart(perf_fig, use_container_width=True)

            st.markdown('<div class="subsection-label">Peer Comparison</div>', unsafe_allow_html=True)
            st.markdown(html_table(peer_df), unsafe_allow_html=True)

            peer_fig = plot_peer_pe_chart(peer_df)
            if peer_fig is not None:
                st.plotly_chart(peer_fig, use_container_width=True)

        elif page == "Income Statement Forecast":
            st.plotly_chart(
                plot_income_chart(
                    build_forecast_model(
                        base_revenue=revenue,
                        ebit_margin=ebit_margin_used,
                        da_percent=da_percent_used,
                        capex_percent=capex_percent_used,
                        nwc_percent=nwc_percent_used,
                        tax_rate=tax_rate_used,
                        growth_rate=revenue_growth_used,
                        projection_years=projection_years,
                    )[0]
                ),
                use_container_width=True,
            )

            income_display = income_statement_df.copy()
            for col in income_display.columns:
                if col != "Year":
                    income_display[col] = income_display[col].map(lambda x: f"${x:,.1f}")
            st.markdown(html_table(income_display), unsafe_allow_html=True)

        elif page == "Balance Sheet Forecast":
            st.plotly_chart(plot_balance_chart(balance_df), use_container_width=True)

            balance_display = balance_df.copy()
            for col in balance_display.columns:
                if col != "Year":
                    balance_display[col] = balance_display[col].map(lambda x: f"${x:,.1f}")
            st.markdown(html_table(balance_display), unsafe_allow_html=True)

        elif page == "Cash Flow Statement Forecast":
            st.plotly_chart(
                plot_cashflow_chart(
                    build_forecast_model(
                        base_revenue=revenue,
                        ebit_margin=ebit_margin_used,
                        da_percent=da_percent_used,
                        capex_percent=capex_percent_used,
                        nwc_percent=nwc_percent_used,
                        tax_rate=tax_rate_used,
                        growth_rate=revenue_growth_used,
                        projection_years=projection_years,
                    )[0]
                ),
                use_container_width=True,
            )

            cashflow_display = cashflow_forecast_df.copy()
            for col in cashflow_display.columns:
                if col != "Year":
                    cashflow_display[col] = cashflow_display[col].map(lambda x: f"${x:,.1f}")
            st.markdown(html_table(cashflow_display), unsafe_allow_html=True)

        elif page == "DCF Valuation":
            d1, d2, d3 = st.columns(3)
            with d1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Enterprise Value</div><div class="metric-value">{format_dollar_short(enterprise_value)}</div></div>""", unsafe_allow_html=True)
            with d2:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">DCF Price</div><div class="metric-value">{format_dollar_short(implied_price)}</div></div>""", unsafe_allow_html=True)
            with d3:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Blended Price</div><div class="metric-value">{format_dollar_short(blended_price)}</div></div>""", unsafe_allow_html=True)

            assumptions_df = pd.DataFrame(
                {
                    "Assumption": [
                        "Revenue Growth",
                        "EBIT Margin",
                        "D&A %",
                        "CapEx %",
                        "NWC %",
                        "Tax Rate",
                        "WACC",
                        "Terminal Growth",
                        "Net Debt",
                        "Shares Outstanding",
                    ],
                    "Value": [
                        f"{revenue_growth_used*100:.1f}%",
                        f"{ebit_margin_used*100:.1f}%",
                        f"{da_percent_used*100:.1f}%",
                        f"{capex_percent_used*100:.1f}%",
                        f"{nwc_percent_used*100:.1f}%",
                        f"{tax_rate_used*100:.1f}%",
                        f"{wacc_used*100:.1f}%",
                        f"{terminal_growth_used*100:.1f}%",
                        format_dollar_short(net_debt_used),
                        f"{shares_outstanding_used:,.0f}",
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

        elif page == "Comps Valuation":
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Trailing P/E Price</div><div class="metric-value">{format_dollar_short(trailing_comps_value)}</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Forward P/E Price</div><div class="metric-value">{format_dollar_short(forward_comps_value)}</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card"><div class="metric-label">Comps Price</div><div class="metric-value">{format_dollar_short(comps_price)}</div></div>""", unsafe_allow_html=True)

            st.markdown(html_table(peer_df), unsafe_allow_html=True)

            peer_fig = plot_peer_pe_chart(peer_df)
            if peer_fig is not None:
                st.plotly_chart(peer_fig, use_container_width=True)

        elif page == "Sensitivity":
            st.markdown("### Sensitivity Heatmap")

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

            st.markdown('<div class="subsection-label">Scenario Analysis</div>', unsafe_allow_html=True)
            st.markdown(html_table(scenario_df), unsafe_allow_html=True)

            st.markdown('<div class="subsection-label">Scenario Narrative</div>', unsafe_allow_html=True)
            st.markdown(
                """
                <div class="summary-box">
                    <div><b>Bear Case:</b> Lower growth, higher discount rate, and softer terminal value assumptions.</div>
                    <div style="margin-top:8px;"><b>Base Case:</b> Current operating and valuation assumptions applied as the central forecast.</div>
                    <div style="margin-top:8px;"><b>Bull Case:</b> Stronger growth, lower discount rate, and better terminal value assumptions.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown('<div class="subsection-label">Sensitivity Table</div>', unsafe_allow_html=True)
            st.markdown(html_table(sensitivity_df), unsafe_allow_html=True)

        elif page == "Export":
            st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)
            st.download_button(
                label="Download Excel Model",
                data=excel_bytes,
                file_name=f"{resolved_symbol.lower()}_valuation_model.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as e:
        st.error(f"Something went wrong: {e}")
