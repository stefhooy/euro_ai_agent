from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent.parent / "assets"

# Look for any common image format in the assets folder named "hermes"
_EXTS = ("png", "jpg", "jpeg", "webp")
_HERMES_IMAGE: Path | None = next(
    (
        _ASSETS / f"hermes.{ext}"
        for ext in _EXTS
        if (_ASSETS / f"hermes.{ext}").exists()
    ),
    None,
)


def render_hero() -> None:
    # ── Agent portrait + name ─────────────────────────────────────────────
    col_img, col_intro = st.columns([1, 2], gap="large")

    with col_img:
        if _HERMES_IMAGE:
            st.image(str(_HERMES_IMAGE), use_container_width=True)
        else:
            # Placeholder until the user drops in the image
            st.markdown(
                "<div style='background:rgba(13,148,136,0.15);"
                "border:2px dashed rgba(13,148,136,0.4);"
                "border-radius:16px;padding:48px 24px;"
                "text-align:center;color:#94a3b8;font-size:0.9rem;'>"
                "🖼️<br>Add <code>ui/assets/hermes.png</code><br>"
                "to show the agent image here."
                "</div>",
                unsafe_allow_html=True,
            )

    with col_intro:
        st.markdown(
            "<h1 style='"
            "font-family:Playfair Display,Georgia,serif;"
            "font-size:clamp(2.4rem,5vw,3.6rem);"
            "background:linear-gradient("
            "135deg,#93c5fd 0%,#e0f2fe 50%,#5eead4 100%);"
            "-webkit-background-clip:text;"
            "-webkit-text-fill-color:transparent;"
            "margin:0 0 4px;line-height:1.1;'>Hermes</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color:#5eead4;font-size:1rem;"
            "font-weight:500;margin:0 0 16px;"
            "letter-spacing:0.06em;text-transform:uppercase;'>"
            "Your AI European Travel Companion</p>",
            unsafe_allow_html=True,
        )

        # Name origin
        st.markdown(
            "<div style='background:rgba(13,148,136,0.12);"
            "border-left:3px solid #0d9488;"
            "border-radius:0 8px 8px 0;"
            "padding:12px 16px;margin-bottom:18px;'>"
            "<span style='font-size:0.8rem;color:#5eead4;"
            "text-transform:uppercase;letter-spacing:0.08em;"
            "font-weight:600;'>Why Hermes?</span><br>"
            "<span style='color:#cbd5e1;font-size:0.9rem;"
            "line-height:1.6;'>"
            "In Greek mythology, Hermes was the god of <strong>"
            "roads, travel, and commerce</strong> , the divine "
            "messenger who crossed borders freely and guided "
            "travellers on their journeys. The perfect name for "
            "an agent that plans routes, compares costs, and "
            "gets you where you want to go."
            "</span></div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p style='color:#94a3b8;font-size:0.95rem;"
            "line-height:1.75;margin:0;'>"
            "Set your preferences in the sidebar and Hermes "
            "will build a complete multi-city European itinerary "
            ", selecting destinations, estimating transport and "
            "accommodation costs, and showing you the best time "
            "of year to travel."
            "</p>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='height:1px;background:linear-gradient("
        "90deg,transparent,rgba(13,148,136,0.4),transparent);"
        "margin:32px 0 28px;'></div>",
        unsafe_allow_html=True,
    )

    # ── What Hermes can do ────────────────────────────────────────────────────
    st.markdown(
        "<h3 style='font-family:Playfair Display,Georgia,serif;"
        "color:#e2e8f0;font-size:1.3rem;margin:0 0 20px;'>"
        "What Hermes does for you</h3>",
        unsafe_allow_html=True,
    )

    capabilities = [
        ("🗺️", "Picks your destinations",
         "Scores 40+ European cities against your budget, "
         "activity preferences, and travel season to find the "
         "best matches."),
        ("✈️", "Plans every leg of the journey",
         "Compares flights, trains, and buses for each route "
         "segment, applying real geographic constraints like "
         "water crossings and mountain ranges."),
        ("🏨", "Estimates accommodation",
         "Calculates realistic hotel costs by city, travel "
         "style (backpacker / mid-range / luxury), and season."),
        ("🎭", "Generates a day-by-day activity plan",
         "Uses a local AI model to suggest activities for each "
         "city, matched to your stated interests."),
        ("📅", "Shows you the cheapest time to travel",
         "A 12-month pricing calendar compares total trip cost "
         "across every month so you can pick the best window."),
        ("🌤️", "Pulls live weather data",
         "Fetches historical Open-Meteo data for each city in "
         "your travel month so you know what to pack."),
    ]

    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(capabilities):
        with cols[i % 3]:
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.04);"
                f"border:1px solid rgba(255,255,255,0.08);"
                f"border-radius:12px;padding:18px 16px;"
                f"margin-bottom:16px;height:100%;'>"
                f"<div style='font-size:1.6rem;"
                f"margin-bottom:8px;'>{icon}</div>"
                f"<div style='font-weight:600;color:#e2e8f0;"
                f"font-size:0.95rem;margin-bottom:6px;'>{title}</div>"
                f"<div style='color:#94a3b8;font-size:0.82rem;"
                f"line-height:1.55;'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Country scale note ────────────────────────────────────────────────────
    st.markdown(
        "<p style='text-align:center;color:#64748b;"
        "font-size:0.82rem;margin-top:8px;'>"
        "Hermes supports 1-6 countries per trip: a minimum of "
        "3 days per country is enforced so every stop is "
        "worth the journey."
        "</p>",
        unsafe_allow_html=True,
    )
