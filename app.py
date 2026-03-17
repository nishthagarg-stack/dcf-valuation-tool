import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

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
# Custom styling
# -----------------------------
st.markdown(
    """
    <style>
    body {
        background-color: #0E1117;
        color: #FAFAFA;
    }

    .stApp {
        background: linear-gradient(180deg, #0E1117 0%, #121826 100%);
        color: #FAFAFA;
    }

    .main {
        padding-top: 1rem;
    }

    h1, h2, h3, h4, h5, h6, p, label, div {
        color: #FAFAFA;
    }

    .stTextInput > div > div > input,
    .stNumberInput input,
    .stTextArea textarea {
        background-color: #1A1D24 !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        border: 1px solid #2A2F3A !important;
    }

    .stButton > button {
        background-color: #4FC3F7 !important;
        color: #0E1117 !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.2rem !important;
        border: none !important;
    }

    .stButton > button:hover {
        background-color: #38BDF8 !important;
        color: #0E1117 !important;
    }

    .summary-box {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1rem 1rem;
        background: #161A22;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
    }

    .summary-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }

    .metric-card {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1rem;
        background: #161A22;
        text-align: left;
        margin-bottom: 0.75rem;
    }

    .metric-label {
        color: #AAB0B6;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
    }

    .metric-value {
        font-size: 1.7rem;
        font-weight: 800;
        color: #FFFFFF;
    }

    .section-label {
        font-size: 1.75rem;
        font-weight: 800;
        margin-top: 1.25rem;
        margin-bottom: 0.75rem;
        color: #FFFFFF;
    }

    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <h1 style='text-align: center;'>DCF Valuation Tool</h1>

    <p style='text-align: center; font-size:22px; font-weight: bold; color: #4FC3F7; margin-bottom: 5px; text-shadow: 0 0 10px rgba(79,195,247,0.35);'>
    Nishtha Garg
    </p>

    <p style='text-align: center; color: #BBBBBB; font-size:16px;'>
    Interactive discounted cash flow model with scenario and sensitivity analysis
    </p>

    <hr style='margin-top:10px; margin-bottom:20px; border: 0.5px solid #333;'>
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

# -----------------------------
# Main logic
# -----------------------------
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
            rec_color = "#16a34a"
        elif upside_downside <= -15:
            recommendation = "SELL"
            rec_color = "#dc2626"
        else:
            recommendation = "HOLD"
            rec_color = "#d97706"

        # -----------------------------
        # Results cards
        # -----------------------------
        st.markdown(f'<div class="section-label">Results for {company_name}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Current Price</div>
                    <div class="metric-value">{format_dollar_short(current_price)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Implied Price</div>
                    <div class="metric-value">{format_dollar_short(implied_price)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        col3, col4 = st.columns(2)
        with col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Enterprise Value</div>
                    <div class="metric-value">{format_dollar_short(enterprise_value)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Upside / Downside</div>
                    <div class="metric-value">{format_percent(upside_downside)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        extra1, extra2 = st.columns(2)
        with extra1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Market Cap</div>
                    <div class="metric-value">{format_dollar_short(market_cap)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with extra2:
            pe_display = f"Trailing P/E: {round(trailing_pe,2) if trailing_pe else 'N/A'} | Forward P/E: {round(forward_pe,2) if forward_pe else 'N/A'}"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Valuation Multiples</div>
                    <div style="font-size:1.1rem; font-weight:700; color:#FFFFFF;">{pe_display}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Recommendation box
        st.markdown(
            f"""
            <div class="summary-box" style="border-left: 5px solid {rec_color};">
                <div class="summary-title">Recommendation</div>
                <div style="font-size: 1.2rem; font-weight: 800; color: {rec_color}; margin-bottom: 8px;">
                    {recommendation}
                </div>
                <div style="line-height:1.6;">
                    Implied Equity Value: <b>{format_dollar_short(implied_price)}</b><br>
                    Current Market Price: <b>{format_dollar_short(current_price)}</b><br>
                    Upside / Downside: <b>{upside_downside:,.1f}%</b>
                </div>
                <div style="margin-top:10px; color:#AAAAAA; font-size:14px;">
                    Assumptions: Revenue Growth {growth_rate*100:.1f}% | WACC {wacc*100:.1f}% | Terminal Growth {terminal_growth*100:.1f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # -----------------------------
        # Projected Financials
        # -----------------------------
        st.markdown('<div class="section-label">Projected Financials</div>', unsafe_allow_html=True)

        projection_df = pd.DataFrame({
            "Year": list(range(1, projection_years + 1)),
            "Projected Revenue ($M)": [x / 1_000_000 for x in base_results["projected_revenues"]],
            "Projected FCF ($M)": [x / 1_000_000 for x in base_results["projected_fcfs"]],
            "Discounted FCF ($M)": [x / 1_000_000 for x in base_results["discounted_fcfs"]],
        })

        display_projection_df = projection_df.copy()
        display_projection_df["Projected Revenue ($M)"] = display_projection_df["Projected Revenue ($M)"].map(lambda x: f"${x:,.1f}")
        display_projection_df["Projected FCF ($M)"] = display_projection_df["Projected FCF ($M)"].map(lambda x: f"${x:,.1f}")
        display_projection_df["Discounted FCF ($M)"] = display_projection_df["Discounted FCF ($M)"].map(lambda x: f"${x:,.1f}")

        st.dataframe(display_projection_df, use_container_width=True, hide_index=True)

        # -----------------------------
        # Projection Charts
        # -----------------------------
        st.markdown('<div class="section-label">Projection Charts</div>', unsafe_allow_html=True)

        revenue_chart_df = pd.DataFrame({
            "Year": list(range(1, projection_years + 1)),
            "Revenue ($M)": [x / 1_000_000 for x in base_results["projected_revenues"]]
        })

        fcf_chart_df = pd.DataFrame({
            "Year": list(range(1, projection_years + 1)),
            "FCF ($M)": [x / 1_000_000 for x in base_results["projected_fcfs"]]
        })

        revenue_chart = (
            alt.Chart(revenue_chart_df)
            .mark_line(point=True, color="#4FC3F7", strokeWidth=3)
            .encode(
                x=alt.X("Year:Q", title="Year", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Revenue ($M):Q", title="Revenue ($M)")
            )
            .properties(height=280, title="Revenue Forecast")
        )

        fcf_chart = (
            alt.Chart(fcf_chart_df)
            .mark_bar(color="#7E57C2", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Year:Q", title="Year", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("FCF ($M):Q", title="FCF ($M)")
            )
            .properties(height=280, title="Free Cash Flow Forecast")
        )

        st.altair_chart(revenue_chart, use_container_width=True)
        st.altair_chart(fcf_chart, use_container_width=True)

        # -----------------------------
        # Scenario Analysis
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

        st.dataframe(pd.DataFrame(scenario_rows), use_container_width=True, hide_index=True)

        # -----------------------------
        # Sensitivity Analysis
        # -----------------------------
        st.markdown('<div class="section-label">Sensitivity Analysis</div>', unsafe_allow_html=True)

        wacc_input = st.text_input("WACC values (%)", "7,8,9,10")
        tg_input = st.text_input("Terminal Growth values (%)", "2,2.5,3")

        try:
            wacc_values = [float(x.strip()) / 100 for x in wacc_input.split(",")]
            tg_values = [float(x.strip()) / 100 for x in tg_input.split(",")]

            sensitivity_table = []

            for tg in tg_values:
                row = []
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
                        row.append(format_dollar_short(sens_result["implied_price"]))
                    except Exception:
                        row.append("Invalid")

                sensitivity_table.append(row)

            sensitivity_df = pd.DataFrame(
                sensitivity_table,
                index=[f"TG {x*100:.2f}%" for x in tg_values],
                columns=[f"WACC {x*100:.2f}%" for x in wacc_values]
            )

            st.dataframe(sensitivity_df, use_container_width=True)

        except Exception:
            st.warning("Please enter valid comma-separated numeric values.")

        # -----------------------------
        # Peer comps
        # -----------------------------
        st.markdown('<div class="section-label">Peer Comparison</div>', unsafe_allow_html=True)
        peer_list = [x.strip().upper() for x in peer_input.split(",") if x.strip()]
        if peer_list:
            peer_df = get_peer_metrics(peer_list)
            st.dataframe(peer_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")
