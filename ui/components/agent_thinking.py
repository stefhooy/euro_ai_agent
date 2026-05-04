import calendar as _cal
from typing import Any, Dict

import streamlit as st

# Card HTML helpers


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
        "<div style='display:grid;"
        f"grid-template-columns:repeat({cols},1fr);"
        f"gap:12px;margin-bottom:16px;'>{inner}</div>"
    )


def _human_list(items) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _choice_phrase(index: int, total: int) -> str:
    if total <= 1:
        return "I started with"
    if index == 0:
        return "First, I chose"
    if index == total - 1:
        return "Lastly, I added"
    if index == 1:
        return "Second, I picked"
    if index == 2:
        return "Third, I brought in"
    return f"Then, for stop {index + 1}, I added"


def _city_reasoning(
    city: str,
    country: str,
    index: int,
    total: int,
    nights: int,
    score: float,
    matched: list,
    reasons: list,
    avg_daily: float,
    style: str,
    pace: str,
    month_name: str,
    weather: Dict[str, Any],
    dep: str,
    num_countries: int,
    trip_type: str,
) -> str:
    night_label = "night" if nights == 1 else "nights"
    place = f"{city}, {country}" if country else city
    choice_phrase = _choice_phrase(index, total)
    interest_text = (
        f"it lines up with your interest in {_human_list(matched)}"
        if matched else "it broadens the route beyond your exact tags"
    )
    budget_text = (
        f"the estimated daily cost is EUR {avg_daily:,.0f} for your "
        f"{style.lower()} style"
        if avg_daily else "the cost profile fits the overall route"
    )
    weather_text = ""
    if weather.get("avg_high_c") is not None:
        weather_text = (
            f" The {month_name} weather also looks usable: "
            f"{weather['condition'].lower()}, around "
            f"{weather['avg_low_c']}C to {weather['avg_high_c']}C."
        )
    if trip_type == "international":
        route_text = (
            "this stop helps keep the route international while adding "
            f"a distinct country to the {num_countries}-country plan"
        )
    elif trip_type == "domestic":
        route_text = (
            "this stop keeps the route focused on your departure country"
        )
    else:
        route_text = "this stop fits the overall route shape"

    if total <= 1:
        paragraph = (
            f"I started with {place} because it gives us a clear, confident "
            f"anchor for the whole trip. From {dep}, {route_text}, and I "
            f"gave it {nights} {night_label} so the plan feels intentional "
            f"rather than rushed. It scored {score}/100 because "
            f"{interest_text}, and {budget_text}.{weather_text}"
        )
    elif index == 0:
        paragraph = (
            f"{choice_phrase} {place} as the opening chapter of the route. "
            f"I wanted the trip to begin somewhere that immediately pays "
            f"off your preferences, so this stop gives us momentum without "
            f"losing control of the budget. From {dep}, {route_text}. I set "
            f"aside {nights} {night_label} because a {pace} pace should "
            f"feel curious, not frantic. It scored {score}/100: "
            f"{interest_text}, and {budget_text}.{weather_text}"
        )
    elif index == total - 1:
        paragraph = (
            f"{choice_phrase} {place} to close the itinerary with a clear "
            f"final note. By this point, I wanted the route to feel complete, "
            f"not just longer, so this city earns its place by balancing the "
            f"countries already chosen. From {dep}, {route_text}. I gave it "
            f"{nights} {night_label}, which keeps the ending comfortable "
            f"for your {pace} pace. It scored {score}/100 because "
            f"{interest_text}, and {budget_text}.{weather_text}"
        )
    elif index % 3 == 1:
        paragraph = (
            f"{choice_phrase} {place} because this is where the route starts "
            f"to gain texture. I am not only stacking famous cities; I am "
            f"trying to make each stop do a different job for you. Here, "
            f"{route_text}. I planned {nights} {night_label} so you have "
            f"room to explore at a {pace} pace. The score was {score}/100: "
            f"{interest_text}, and {budget_text}.{weather_text}"
        )
    elif index % 3 == 2:
        paragraph = (
            f"{choice_phrase} {place} as a deliberate change of rhythm. "
            f"This stop helps the trip avoid feeling repetitive while still "
            f"respecting what you asked for. From {dep}, {route_text}, and "
            f"{nights} {night_label} gives the city enough space in the "
            f"itinerary. It scored {score}/100 because {interest_text}, "
            f"and {budget_text}.{weather_text}"
        )
    else:
        paragraph = (
            f"{choice_phrase} {place} because it strengthens the middle of "
            f"the journey. I wanted this part of the plan to keep the route "
            f"fresh while still making practical sense. From {dep}, "
            f"{route_text}. I gave it {nights} {night_label} at your "
            f"{pace} pace, and it scored {score}/100 because "
            f"{interest_text}, and {budget_text}.{weather_text}"
        )

    bullets = [
        f"- Interest fit: {_human_list(matched)}."
        if matched else "- Interest fit: useful variety for the route.",
        f"- Budget logic: {budget_text}.",
        f"- Time allocation: {nights} {night_label} at a {pace} pace.",
        f"- Route role: {route_text}.",
    ]
    bullets.extend(f"- {reason}" for reason in reasons)
    return paragraph + "\n\n" + "\n".join(bullets)


# Main render


def render_agent_thinking(
    trip_plan: Dict[str, Any],
    budget_result: Dict[str, Any],
    preferences: Dict[str, Any],
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
    trip_type = preferences.get("trip_type", "international")
    duration = preferences.get("duration", 0)
    month_name = _cal.month_name[travel_month]

    # 1. Planning decisions
    st.markdown("#### \U0001f4cb Planning decisions")
    st.markdown(
        _grid(
            _metric_card("\U0001f6eb From", dep),
            _metric_card("\U0001f6ec Return", ret),
            _metric_card("\U0001f4c5 Duration", f"{duration} days"),
            _metric_card("\U0001f5d3️ Month", month_name),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        _grid(
            _metric_card("✨ Style", style),
            _metric_card("\U0001f6b6 Pace", pace.title()),
            _metric_card("\U0001f30d Countries", str(num_countries)),
            _metric_card("\U0001f3d9️ Cities", str(len(destinations))),
        ),
        unsafe_allow_html=True,
    )
    modes_str = ", ".join(m.title() for m in transport_modes)
    st.caption(
        f"Transport: **{modes_str}** · "
        f"Priority: **{route_priority}** · "
        f"Directness: **{directness}**"
    )

    # 2. Why these cities?
    st.markdown("---")
    st.markdown("#### \U0001f3d9️ Why these cities?")
    st.caption(
        "Scored 0-100: activity match (40 pts), "
        "budget fit (40 pts), and season (20 pts). "
        "Hermes explains how each stop fits your route."
    )

    total_destinations = len(destinations)
    for idx, city in enumerate(destinations):
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

                st.markdown(
                    _city_reasoning(
                        city=city,
                        country=country,
                        index=idx,
                        total=total_destinations,
                        nights=nights,
                        score=score,
                        matched=matched,
                        reasons=reasons,
                        avg_daily=avg_daily,
                        style=style,
                        pace=pace,
                        month_name=month_name,
                        weather=weather,
                        dep=dep,
                        num_countries=num_countries,
                        trip_type=trip_type,
                    )
                )

                if weather.get("avg_high_c") is not None:
                    cond = weather["condition"]
                    lo = weather["avg_low_c"]
                    hi = weather["avg_high_c"]
                    st.markdown(
                        "<span style='font-size:0.85rem;"
                        f"color:#7dd3fc;'>{weather['emoji']} "
                        f"**{cond}** in {month_name} - "
                        f"{lo}°C to {hi}°C</span>",
                        unsafe_allow_html=True,
                    )

                if matched:
                    st.caption(
                        f"✅ Interests matched: "
                        f"{', '.join(matched)}"
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

    # 3. Transport decisions
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
                f" · {dur:g}h"
                if isinstance(dur, (int, float)) else ""
            )
            leg_type = (
                leg.get("type", "").replace("_", " ").title()
            )
            alts = leg.get("alternatives", [])

            with st.container():
                lc1, lc2 = st.columns([3, 1])
                with lc1:
                    st.markdown(
                        f"**{leg['from']} → {leg['to']}** "
                        "<span style='color:#94a3b8;"
                        f"font-size:0.85rem;'>"
                        f"{leg_type}{dist_label}"
                        f"{dur_label}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"Chosen: **{mode}** ({direct_label})"
                    )
                    if alts:
                        alt_parts = [
                            f"{a['mode'].title()} "
                            f"€{a['cost_eur']:,.0f} "
                            f"/ {a['duration_hours']:g}h"
                            for a in alts
                        ]
                        st.caption(
                            "Alternatives: "
                            + " · ".join(alt_parts)
                        )
                with lc2:
                    cost = leg.get("cost_eur", 0)
                    st.metric("Cost", f"€{cost:,.0f}")

    # 4. Budget allocation
    st.markdown("---")
    st.markdown("#### \U0001f4b6 Budget allocation")

    grand = budget_result.get("grand_total", 1) or 1
    user_budget = budget_result.get("user_budget", 0)
    categories = [
        (
            "✈️ Transport",
            budget_result.get("flights_cost", 0),
        ),
        (
            "\U0001f3e8 Accommodation",
            budget_result.get("accommodation_cost", 0),
        ),
        (
            "\U0001f3ad Activities",
            budget_result.get("activities_cost", 0),
        ),
        (
            "\U0001f37d️ Food",
            budget_result.get("food_cost", 0),
        ),
    ]
    for label, cost in categories:
        pct = cost / grand * 100
        pct_budget = (
            cost / user_budget * 100 if user_budget else 0
        )
        st.markdown(
            f"**{label}** - €{cost:,.0f} "
            "<span style='color:#94a3b8;font-size:0.85rem;'>"
            f"({pct:.0f}% of total · "
            f"{pct_budget:.0f}% of your budget)</span>",
            unsafe_allow_html=True,
        )
        st.progress(min(int(pct), 100))
