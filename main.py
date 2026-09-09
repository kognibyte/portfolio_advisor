import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from agents.orchestrator import PortfolioOrchestrator


st.set_page_config(
    page_title="Portfolio Risk Advisor",
    layout="wide",
)

st.title("Portfolio Risk Advisor")
st.caption(
    "Agentic AI risk profiling and portfolio "
    "suitability demonstration"
)


with st.sidebar:
    st.header("Investor Details")

    financial_goal = st.text_input(
        "Financial goal",
        value="Retirement",
    )

    target_amount = st.number_input(
        "Target amount",
        min_value=1.0,
        value=20000000.0,
        step=100000.0,
    )

    investment_horizon = st.number_input(
        "Investment horizon in years",
        min_value=1,
        max_value=60,
        value=20,
    )

    risk_appetite = st.selectbox(
        "Risk appetite",
        ["Low", "Medium", "High"],
        index=1,
    )

    loss_tolerance = st.slider(
        "Maximum temporary loss tolerance (%)",
        min_value=0,
        max_value=100,
        value=20,
    )

    liquidity_need = st.selectbox(
        "Liquidity need",
        ["Low", "Medium", "High"],
        index=1,
    )

    investment_experience = st.selectbox(
        "Investment experience",
        ["Low", "Medium", "High"],
        index=1,
    )

    income_stability = st.selectbox(
        "Income stability",
        ["Low", "Medium", "High"],
        index=2,
    )

    use_llm = st.checkbox(
        "Use LLM for explanation",
        value=True,
    )


st.subheader("Current Portfolio Allocation")

column1, column2 = st.columns(2)

with column1:
    equity = st.slider(
        "Equity %",
        min_value=0,
        max_value=100,
        value=75,
    )

    fixed_income = st.slider(
        "Fixed Income %",
        min_value=0,
        max_value=100,
        value=15,
    )

with column2:
    gold = st.slider(
        "Gold %",
        min_value=0,
        max_value=100,
        value=5,
    )

    cash = st.slider(
        "Cash %",
        min_value=0,
        max_value=100,
        value=5,
    )


st.subheader("Portfolio Risk Metrics")

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    annualised_volatility = st.number_input(
        "Annualised volatility %",
        min_value=0.0,
        max_value=100.0,
        value=24.5,
    )

with metric_col2:
    largest_holding = st.number_input(
        "Largest holding %",
        min_value=0.0,
        max_value=100.0,
        value=30.0,
    )

with metric_col3:
    largest_sector = st.number_input(
        "Largest sector %",
        min_value=0.0,
        max_value=100.0,
        value=48.0,
    )


total_allocation = (
    equity
    + fixed_income
    + gold
    + cash
)

st.write(
    f"Total allocation: **{total_allocation}%**"
)

if total_allocation != 100:
    st.warning(
        "Allocation must total 100% before "
        "running the assessment."
    )


if st.button(
    "Run Risk Assessment",
    type="primary",
    disabled=total_allocation != 100,
):
    investor = {
        "investor_id": "DEMO-001",
        "financial_goal": financial_goal,
        "target_amount": target_amount,
        "investment_horizon_years": int(
            investment_horizon
        ),
        "risk_appetite": risk_appetite,
        "loss_tolerance_percent": float(
            loss_tolerance
        ),
        "liquidity_need": liquidity_need,
        "investment_experience": (
            investment_experience
        ),
        "income_stability": income_stability,
    }

    portfolio_analytics = {
        "total_value": 1000000,
        "asset_allocation": {
            "Equity": float(equity),
            "Fixed Income": float(fixed_income),
            "Gold": float(gold),
            "Cash": float(cash),
        },
        "annualised_volatility": float(
            annualised_volatility
        ),
        "largest_holding_weight": float(
            largest_holding
        ),
        "largest_sector_weight": float(
            largest_sector
        ),
    }

    orchestrator = PortfolioOrchestrator(
        use_llm=use_llm
    )

    with st.spinner("Running Risk Agent..."):
        result = orchestrator.run_risk_workflow(
            investor=investor,
            portfolio_analytics=portfolio_analytics,
        )

    if result["workflow_status"] == "failed":
        st.error("Risk assessment failed.")

        for error in result["errors"]:
            st.error(error)

    else:
        risk = result["risk_assessment"]

        st.success(
            "Risk assessment completed."
        )

        card1, card2, card3 = st.columns(3)

        card1.metric(
            "Risk Score",
            f'{risk["risk_score"]}/100',
        )

        card2.metric(
            "Investor Profile",
            risk["risk_profile"],
        )

        card3.metric(
            "Portfolio Alignment",
            risk["alignment_status"],
        )

        st.subheader("Risk Summary")
        st.write(risk["summary"])

        st.subheader("Portfolio Risk Level")
        st.write(risk["portfolio_risk_level"])

        st.write(risk["alignment_reason"])

        allocation_frame = pd.DataFrame(
            {
                "Asset": list(
                    portfolio_analytics[
                        "asset_allocation"
                    ].keys()
                ),
                "Allocation": list(
                    portfolio_analytics[
                        "asset_allocation"
                    ].values()
                ),
            }
        )

        figure = px.pie(
            allocation_frame,
            names="Asset",
            values="Allocation",
            title="Current Portfolio Allocation",
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

        st.subheader("Risk Score Breakdown")

        breakdown_frame = pd.DataFrame(
            risk["score_breakdown"]
        )

        st.dataframe(
            breakdown_frame,
            use_container_width=True,
            hide_index=True,
        )

        if risk["warnings"]:
            st.subheader("Risk Warnings")

            for warning in risk["warnings"]:
                st.warning(warning)
        else:
            st.info(
                "No additional concentration warnings "
                "were detected."
            )

        st.subheader("Suitability Notice")
        st.info(risk["disclaimer"])

        report = {
            "investor": investor,
            "portfolio_analytics": (
                portfolio_analytics
            ),
            "risk_assessment": risk,
        }

        Path("reports").mkdir(
            exist_ok=True
        )

        report_path = Path(
            "reports/risk_report.json"
        )

        report_path.write_text(
            json.dumps(
                report,
                indent=2,
            ),
            encoding="utf-8",
        )

        st.download_button(
            label="Download Risk Report",
            data=json.dumps(
                report,
                indent=2,
            ),
            file_name="risk_report.json",
            mime="application/json",
        )