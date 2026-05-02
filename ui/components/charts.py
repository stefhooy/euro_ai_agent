import pandas as pd
import plotly.express as px
import streamlit as st

_CHART_LAYOUT = dict(
    margin=dict(t=10, b=10, l=10, r=10),
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0"),
)


def render_cost_pie(budget_result: dict) -> None:
    st.subheader("Cost Breakdown")
    costs_data = {
        "Category": ["Transport", "Accommodation", "Activities", "Food"],
        "Amount (€)": [
            budget_result.get("flights_cost", 0),
            budget_result.get("accommodation_cost", 0),
            budget_result.get("activities_cost", 0),
            budget_result.get("food_cost", 0),
        ],
    }
    fig = px.pie(
        costs_data,
        values="Amount (€)",
        names="Category",
        color_discrete_sequence=["#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b"],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=False, **_CHART_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)


def render_pricing_calendar(pricing_cal: dict) -> None:
    monthly_costs = pricing_cal.get("monthly_costs", [])
    if not monthly_costs:
        return

    st.subheader("📅 Pricing Calendar")
    cheapest = pricing_cal.get("cheapest_month", {}).get("month_name", "")
    most_exp = pricing_cal.get("most_expensive_month", {}).get("month_name", "")
    best_wx = pricing_cal.get("best_weather_months", [])

    df = pd.DataFrame(monthly_costs)
    df["highlight"] = df["month_name"].apply(
        lambda m: "Cheapest ✅" if m == cheapest
        else ("Most Expensive ❌" if m == most_exp else "Normal")
    )
    fig = px.bar(
        df,
        x="month_name",
        y="estimated_cost",
        color="highlight",
        color_discrete_map={
            "Cheapest ✅": "#22c55e",
            "Most Expensive ❌": "#ff1100",
            "Normal": "#3b82f6",
        },
        labels={"estimated_cost": "Est. Cost (€)", "month_name": ""},
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(title="", orientation="h", y=-0.25),
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickangle=-45),
        **_CHART_LAYOUT,
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    st.plotly_chart(fig, use_container_width=True)

    if best_wx:
        st.caption(f"🌤️ Best weather: {', '.join(best_wx)}")
    if cheapest:
        cheap_cost = pricing_cal.get("cheapest_month", {}).get("estimated_cost", 0)
        st.caption(f"✅ Cheapest month: **{cheapest}** (~€{cheap_cost:,.0f})")
    if most_exp:
        exp_cost = pricing_cal.get("most_expensive_month", {}).get("estimated_cost", 0)
        st.caption(f"❌ Most expensive: **{most_exp}** (~€{exp_cost:,.0f})")
