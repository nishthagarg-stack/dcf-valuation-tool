import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="DCF Valuation Tool",
    page_icon="📈",
    layout="centered"
)

st.markdown(
    """
    <h1 style='text-align: center;'>DCF Valuation Tool</h1>
    <p style='text-align: center; font-size:22px; font-weight: bold; color: #4FC3F7;'>
    By: Nishtha Garg
    </p>
    <p style='text-align: center; color: #BBBBBB;'>
    Interactive discounted cash flow model with scenario and sensitivity analysis
    </p>
    """,
    unsafe_allow_html=True
)

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

st.subheader("Inputs")

symbol = st.text_input("Enter Stock Ticker", "AAPL").upper()
growth_rate = st.number_input("Revenue Growth Rate (%)", value=5.0, step=0.5) / 100
tax_rate = st.number_input("Tax Rate (%)", value=21.0, step=0.5) / 100
wacc = st.number_input("WACC (%)", value=9.0, step=0.5) / 100
terminal_growth = st.number_input("Terminal Growth Rate (%)", value=2.5, step=0.5) / 100
projection_years = int(st.number_input("Projection Years", min_value=3, max_value=10, value=5, step=1))
net_debt = st.number_input("Net Debt ($)", value=0.0, step=1000000.0)

run_button = st.button("Run Valuation")

if run_button:
    try:
        @st.cache_data
def get_data(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info, ticker.financials, ticker.cashflow

info, financials, cashflow = get_data(symbol)

        revenue = financials.loc["Total Revenue"].iloc[0]
        operating_income = financials.loc["Operating Income"].iloc[0]
        depreciation = cashflow.loc["Depreciation And Amortization"].iloc[0]
        capex = abs(cashflow.loc["Capital Expenditure"].iloc[0])

        shares_outstanding = info.get("sharesOutstanding")
        current_price = info.get("currentPrice", 0)
        company_name = info.get("longName", symbol)

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

        st.subheader(f"Results for {company_name}")

        st.metric("Current Price", f"${current_price:,.2f}")
        st.metric("Implied Price", f"${base_results['implied_price']:,.2f}")
        st.metric("Enterprise Value", f"${base_results['enterprise_value']:,.0f}")

        if base_results["implied_price"] > current_price:
            st.success("📈 Stock appears UNDERVALUED based on your assumptions.")
        else:
            st.error("📉 Stock appears OVERVALUED based on your assumptions.")

        st.subheader("Projected Financials")
        projection_df = pd.DataFrame({
            "Year": list(range(1, projection_years + 1)),
            "Projected Revenue": base_results["projected_revenues"],
            "Projected FCF": base_results["projected_fcfs"],
            "Discounted FCF": base_results["discounted_fcfs"]
        })
        st.dataframe(projection_df, use_container_width=True)

        st.subheader("Projection Charts")
        chart_df = projection_df.set_index("Year")[["Projected Revenue", "Projected FCF"]]
        st.line_chart(chart_df)

        st.subheader("Scenario Analysis")

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
                    "Implied Price": round(scenario_result["implied_price"], 2)
                })
            except Exception:
                scenario_rows.append({
                    "Scenario": scenario_name,
                    "Growth Rate": f"{vals['growth']*100:.2f}%",
                    "WACC": f"{vals['wacc']*100:.2f}%",
                    "Terminal Growth": f"{vals['tg']*100:.2f}%",
                    "Implied Price": "Invalid"
                })

        st.dataframe(pd.DataFrame(scenario_rows), use_container_width=True)

        st.subheader("Sensitivity Analysis")
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
                        row.append(round(sens_result["implied_price"], 2))
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

    except Exception as e:
        st.error(f"Something went wrong: {e}")
