import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="DCF Valuation Tool",
    page_icon="📈",
    layout="centered"
)

# -----------------------------
# Helpers
# -----------------------------
def format_dollar_short(value):
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    return f"${value:,.2f}"

def format_percent(value):
    return f"{value:,.1f}%"

def html_table(df):
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

@st.cache_data(ttl=1800)
def get_market_and_financial_data(symbol):
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
    except Exception:
        pass

    return {
        "company_name": company_name,
        "current_price": current_price,
        "shares_outstanding": shares_outstanding,
        "market_cap": market_cap,
        "trailing_pe": trailing_pe,
        "forward_pe": forward_pe,
        "financials": financials,
        "cashflow": cashflow
    }

@st.cache_data(ttl=1800)
def get_peer_metrics(tickers):
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
    <h1 style='text-align: center;'>DCF Valuation Tool</h1>
    <p style='text-align: center; font-size:22px; font-weight: bold; color: #4FC3F7; margin-bottom: 5px; text-shadow: 0 0 12px rgba(79,195,247,0.35);'>
    Nishtha Garg
    </p>
    <p style='text-align: center; color: #B8C0CC; font-size:16px;'>
    Interactive discounted cash flow model with scenario and sensitivity analysis
    </p>
    <hr style='margin-top:10px; margin-bottom:24px; border: 0.5px solid #22304C;'>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Inputs
# -----------------------------
st.markdown('<div class="section-label">Inputs</div>', unsafe_allow_html=True)

symbol = st.text_input("Enter Stock Ticker", "AAPL").upper()
growth_rate = st.number_input("Revenue Growth Rate (%)", value=5.0, step=0.5) / 100
tax_rate = st.number_input("Tax Rate (%)", value=21.0, step=0.5) / 100
wacc = st.number_input("WACC (%)", value=9.0, step=0.5) / 100
terminal_growth = st.number_input("Terminal Growth Rate (%)", value=2.5, step=0.5) / 100
projection_years = int(st.number_input("Projection Years", min_value=3, max_value=10, value=5, step=1))
net_debt = st.number_input("Net Debt ($)", value=0.0, step=1000000.0)
peer_input = st.text_input("Peer Tickers (comma-separated)", "MSFT,GOOGL,NVDA")

run_button = st.button("Run Valuation")

if run_button:
    try:
        data = get_market_and_financial_data(symbol)
        company_name = data["company_name"]
        current_price = data["current_price"] or 0
        shares_outstanding = data["shares_outstanding"]
        market_cap = data["market_cap"]
        trailing_pe = data["trailing_pe"]
        forward_pe = data["forward_pe"]
        financials = data["financials"]
        cashflow = data["cashflow"]

        revenue = financials.loc["Total Revenue"].iloc[0]
        operating_income = financials.loc["Operating Income"].iloc[0]
        depreciation = cashflow.loc["Depreciation And Amortization"].iloc[0]
        capex = abs(cashflow.loc["Capital Expenditure"].iloc[0])

        if shares_outstanding is None or shares_outstanding == 0:
            raise ValueError("Could not retrieve shares outstanding for this ticker.")

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

        if upside_downside >= 15:
            recommendation = "BUY"
            rec_color = "#16A34A"
        elif upside_downside <= -15:
            recommendation = "SELL"
            rec_color = "#DC2626"
        else:
            recommendation = "HOLD"
            rec_color = "#F59E0B"

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
            pe_display = f"Trailing P/E: {round(trailing_pe,2) if trailing_pe else 'N/A'} | Forward P/E: {round(forward_pe,2) if forward_pe else 'N/A'}"
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

        st.markdown('<div class="section-label">Projected Financials</div>', unsafe_allow_html=True)

        projection_df = pd.DataFrame({
            "Year": list(range(1, projection_years + 1)),
            "Projected Revenue ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["projected_revenues"]],
            "Projected FCF ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["projected_fcfs"]],
            "Discounted FCF ($M)": [f"${x / 1_000_000:,.1f}" for x in base_results["discounted_fcfs"]],
        })

        st.markdown(html_table(projection_df), unsafe_allow_html=True)

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
            yaxis=dict(title="Revenue ($M)", gridcolor="#243041")
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
            yaxis=dict(title="FCF ($M)", gridcolor="#243041")
        )

        st.plotly_chart(revenue_fig, use_container_width=True)
        st.plotly_chart(fcf_fig, use_container_width=True)

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

        scenario_df = pd.DataFrame(scenario_rows)
        st.markdown(html_table(scenario_df), unsafe_allow_html=True)

        st.markdown('<div class="section-label">Sensitivity Analysis</div>', unsafe_allow_html=True)

        wacc_input = st.text_input("WACC values (%)", "7,8,9,10")
        tg_input = st.text_input("Terminal Growth values (%)", "2,2.5,3")

        try:
            wacc_values = [float(x.strip()) / 100 for x in wacc_input.split(",")]
            tg_values = [float(x.strip()) / 100 for x in tg_input.split(",")]

            sensitivity_table = []

            for tg in tg_values:
                row = {"Terminal Growth": f"{tg*100:.2f}%"}
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
                        row[f"WACC {w*100:.2f}%"] = format_dollar_short(sens_result["implied_price"])
                    except Exception:
                        row[f"WACC {w*100:.2f}%"] = "Invalid"
                sensitivity_table.append(row)

            sensitivity_df = pd.DataFrame(sensitivity_table)
            st.markdown(html_table(sensitivity_df), unsafe_allow_html=True)

        except Exception:
            st.warning("Please enter valid comma-separated numeric values.")

        st.markdown('<div class="section-label">Peer Comparison</div>', unsafe_allow_html=True)
        peer_list = [x.strip().upper() for x in peer_input.split(",") if x.strip()]
        if peer_list:
            peer_df = get_peer_metrics(peer_list)
            st.markdown(html_table(peer_df), unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")
