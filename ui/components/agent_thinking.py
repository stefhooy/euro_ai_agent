import calendar as _cal

import streamlit as st

# ── Card HTML helpers ─────────────────────────────────────────────────────────


def _metric_card(label: str, value: str) -> str:
    return (
        "<div style='background:rgba(255,255,255,0.06);"
        "border:1px solid rgba(255,255,255,0.10);"
        "border-radius:10px;padding:12px 14px;'>"
        "<div style='font-size:0.72rem;color:#94a3b8;"
        "margin-bottom:4px;text-transform:uppercase;"
        f"letter-spacing:0.06em;'>{label}</div>"
        "<div style='font-size:1.05rem;font-weight:600;"
        "color:#e2e8f0;white-space:nowrap;"
        f"overflow:hidden;text-overflow:ellipsis;'>{value}</div>"
        "</div>"
    )


def _grid(*cards: str, cols: int = 4) -> str:
    inner = "".join(cards)
    return (
        f"<div style='display:grid;"
        f"grid-template-columns:repeat({cols},1fr);"
        f"gap:12px;margin-bottom:16px;'>{inner}</div>"
    )


# ── Main render ───────────────────────────────────────────────────────────────


def render_agent_thinking(
    trip_plan: dict,
    budget_result: dict,
    preferences: dict,
) -> None:
    """Structured breakdown of every decision the agent made."""
    destinations = trip_plan.get("destinations", [])
    nights_per_city = trip_plan.get("nights_per_city", {})
    dest_scores = trip_plan.get("destination_scores", {})
    web_data = trip_plan.get("web_data", {})
    flight_legs = (
        trip_plan.get("flights", {}).get("transport_legs")
        or trip_plan.get("flights", {}).get("flight_legs", [])
    )
    accom_data = (
        trip_plan.get("accommodation", {}).get("city_breakdown", {})
    )

    pace = preferences.get("pace", "moderate")
    num_countries = preferences.get("num_countries", 2)
    travel_month = preferences.get("travel_month", 6)
    raw_style = preferences.get("travel_style", "mid_range")
    style = raw_style.replace("_", "-").title()
    dep = preferences.get("departure_city", "?")
    ret = preferences.get("return_city", dep)
    activity_prefs = preferences.get("activity_preferences", [])
    transport_modes = preferences.get("transport_modes", [])
    raw_priority = preferences.get("route_priority", "best_balance")
    route_priority = raw_priority.replace("_", " ")
    raw_direct = preferences.get("directness", "allow_connections")
    directness = raw_direct.replace("_", " ")
    duration = preferences.get("duration", 0)
    month_name = _cal.month_name[travel_month]

    # ── 1. Planning decisions ─────────────────────────────────────────────────
    st.markdown("#### 📋 Planning decisions")
    st.markdown(
        _grid(
            _metric_card("🛫 From", dep),
            _metric_card("🛬 Return", ret),
            _metric_card("📅 Duration", f"{duration} days"),
            _metric_card("🗓️ Month", month_name),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        _grid(
            _metric_card("✨ Style", style),
            _metric_card("🚶 Pace", pace.title()),
            _metric_card("🌍 Countries", str(num_countries)),
            _metric_card("🏙️ Cities", str(len(destinations))),
        ),
        unsafe_allow_html=True,
    )
    modes_str = ", ".join(m.title() for m in transport_modes)
    st.caption(
        f"Transport: **{modes_str}** · "
        f"Priority: **{route_priority}** · "
        f"Directness: **{directness}**"
    )

    # ── 2. Why these cities? ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🏙️ Why these cities?")
    st.caption(
        "Scored 0-100: activity match (40 pts), "
        "budget fit (40 pts), season (20 pts). "
        "Descriptions sourced live from Wikipedia."
    )

    for city in destinations:
        score_data = dest_scores.get(city, {})
        score = score_data.get("score", 0)
        reasons = score_data.get("reasons", [])
        city_tags = score_data.get("activity_tags", [])
        country = score_data.get("country", "")
        matched = [t for t in city_tags if t in activity_prefs]
        nights = nights_per_city.get(city, 0)
        avg_daily = score_data.get("avg_daily_cost", {}).get(
            raw_style, 0
        )

        city_web = web_data.get(city, {})
        wiki_desc = city_web.get("description", "")
        weather = city_web.get("weather", {})

        with st.container():
            ca, cb = st.columns([3, 1])
            with ca:
                night_label = "night" if nights == 1 else "nights"
                header = f"**{city}**"
                if country:
                    header += f", {country}"
                header += f" - {nights} {night_label}"
                st.markdown(header)
                st.progress(int(score), text=f"Score: {score}/100")

                if wiki_desc:
                    st.markdown(
                        "<p style='font-style:italic;color:#cbd5e1;"
                        "font-size:0.88rem;margin:6px 0 8px;"
                        f"line-height:1.55;'>{wiki_desc}</p>",
                        unsafe_allow_html=True,
                    )

                if weather.get("avg_high_c") is not None:
                    cond = weather["condition"]
                    lo = weather["avg_low_c"]
                    hi = weather["avg_high_c"]
                    st.markdown(
                        "<span style='font-size:0.85rem;"
                        f"color:#7dd3fc;'>{weather['emoji']} "
                        f"**{cond}** in {month_name} — "
                        f"{lo}°C to {hi}°C</span>",
                        unsafe_allow_html=True,
                    )

                reason_parts = [f"- {r}" for r in reasons]
                if avg_daily:
                    reason_parts.append(
                        f"- Est. daily cost: **€{avg_daily:,.0f}**"
                    )
                if reason_parts:
                    st.markdown("\n".join(reason_parts))

                if matched:
                    st.caption(
                        f"✅ Interests matched: {', '.join(matched)}"
                    )
                elif city_tags:
                    st.caption(
                        f"Available: {', '.join(city_tags[:4])}"
                    )

            with cb:
                accom = accom_data.get(city, {})
                if accom:
                    nightly = accom.get("nightly_cost", 0)
                    st.metric("Hotel / night", f"€{nightly:,.0f}")
                    st.caption(accom.get("recommended_area", ""))

    # ── 3. Transport decisions ────────────────────────────────────────────────
    if flight_legs:
        st.markdown("---")
        st.markdown("#### ✈️ Transport decisions")
        st.caption(
            "Each leg compares all available modes on cost, "
            "duration, and your route preference."
        )
        for leg in flight_legs:
            mode = leg.get("mode", "flight").title()
            changes = leg.get("changes", 1)
            direct_label = (
                "direct" if leg.get("direct", True)
                else f"{changes} change(s)"
            )
            dist = leg.get("distance_km")
            dist_label = f" · {dist:,} km" if dist else ""
            dur = leg.get("duration_hours")
            dur_label = (
                f" · {dur:g}h" if isinstance(dur, (int, float)) else ""
            )
            leg_type = leg.get("type", "").replace("_", " ").title()
            alts = leg.get("alternatives", [])

            with st.container():
                lc1, lc2 = st.columns([3, 1])
                with lc1:
                    st.markdown(
                        f"**{leg['from']} → {leg['to']}** "
                        "<span style='color:#94a3b8;"
                        f"font-size:0.85rem;'>"
                        f"{leg_type}{dist_label}{dur_label}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"Chosen: **{mode}** ({direct_label})")
                    if alts:
                        alt_parts = [
                            f"{a['mode'].title()} "
                            f"€{a['cost_eur']:,.0f} "
                            f"/ {a['duration_hours']:g}h"
                            for a in alts
                        ]
                        st.caption(
                            "Alternatives: " + " · ".join(alt_parts)
                        )
                with lc2:
                    cost = leg.get("cost_eur", 0)
                    st.metric("Cost", f"€{cost:,.0f}")

    # ── 4. Budget allocation ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💶 Budget allocation")

    grand = budget_result.get("grand_total", 1) or 1
    user_budget = budget_result.get("user_budget", 0)
    categories = [
        ("✈️ Transport",     budget_result.get("flights_cost", 0)),
        ("🏨 Accommodation", budget_result.get("accommodation_cost", 0)),
        ("🎭 Activities",    budget_result.get("activities_cost", 0)),
        ("🍽️ Food",          budget_result.get("food_cost", 0)),
    ]
    for label, cost in categories:
        pct = cost / grand * 100
        pct_budget = cost / user_budget * 100 if user_budget else 0
        st.markdown(
            f"**{label}** - €{cost:,.0f} "
            "<span style='color:#94a3b8;font-size:0.85rem;'>"
            f"({pct:.0f}% of total · "
            f"{pct_budget:.0f}% of your budget)</span>",
            unsafe_allow_html=True,
        )
        st.progress(min(int(pct), 100))
