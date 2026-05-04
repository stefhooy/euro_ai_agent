import base64
from pathlib import Path
from typing import Optional

import streamlit as st

_ASSETS = Path(__file__).parent.parent / "assets"

_EXTS = ("png", "jpg", "jpeg", "webp")
_HERMES_IMAGE: Optional[Path] = next(
    (
        _ASSETS / f"hermes.{ext}"
        for ext in _EXTS
        if (_ASSETS / f"hermes.{ext}").exists()
    ),
    None,
)


def _b64(path: Path) -> str:
    """Return base64-encoded bytes for a PNG, or empty string if missing."""
    try:
        return base64.b64encode(path.read_bytes()).decode()
    except Exception:
        return ""


# Pre-load card icons once at import time.
_ICON_MAP = {
    "map":          _b64(_ASSETS / "map.png"),
    "plane":        _b64(_ASSETS / "plane.png"),
    "accomodation": _b64(_ASSETS / "accomodation.png"),
    "activities":   _b64(_ASSETS / "activities.png"),
    "calendar":     _b64(_ASSETS / "calendar.png"),
    "weather":      _b64(_ASSETS / "weather.png"),
}

_ICON_SIZE = 32  # px - same visual weight as a 1.6rem text emoji


def _icon_html(key: str, fallback: str) -> str:
    """Return an <img> tag for the card icon, falling back to emoji."""
    b64 = _ICON_MAP.get(key, "")
    if b64:
        return (
            f"<img src='data:image/png;base64,{b64}' "
            f"width='{_ICON_SIZE}' height='{_ICON_SIZE}' "
            f"style='object-fit:contain;display:block;'/>"
        )
    return (
        f"<span style='font-size:1.6rem;line-height:1;'>"
        f"{fallback}</span>"
    )


def render_hero() -> None:
    # ── Agent portrait + name ─────────────────────────────────────────────
    col_img, col_intro = st.columns([1, 2], gap="large")

    with col_img:
        if _HERMES_IMAGE:
            st.image(str(_HERMES_IMAGE), use_container_width=True)
        else:
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
            "font-family:Cinzel,Georgia,serif;"
            "font-size:clamp(2.4rem,5vw,3.6rem);"
            "font-weight:900;"
            "letter-spacing:0.08em;"
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
        ("map",          "🗺️",  "Picks your destinations",
         "Scores 80 European cities against your budget, "
         "activity preferences, travel season, and proximity "
         "to your departure city to find the best matches."),
        ("plane",        "✈️",  "Plans every leg of the journey",
         "Compares flights, trains, and buses for each route "
         "segment, applying real geographic constraints like "
         "water crossings and mountain ranges."),
        ("accomodation", "🏨",  "Estimates accommodation",
         "Calculates realistic hotel costs by city, travel "
         "style (backpacker / mid-range / luxury), and season."),
        ("activities",   "🎭",  "Generates a day-by-day activity plan",
         "Uses a local AI model to suggest activities for each "
         "city, matched to your stated interests."),
        ("calendar",     "📅",  "Shows you the cheapest time to travel",
         "A 12-month pricing calendar compares total trip cost "
         "across every month so you can pick the best window."),
        ("weather",      "🌤️", "Pulls live weather data",
         "Fetches historical Open-Meteo data for each city in "
         "your travel month so you know what to pack."),
    ]

    cols = st.columns(3)
    for i, (icon_key, fallback, title, desc) in enumerate(capabilities):
        with cols[i % 3]:
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.04);"
                f"border:1px solid rgba(255,255,255,0.08);"
                f"border-radius:12px;padding:18px 16px;"
                f"margin-bottom:16px;height:100%;'>"
                f"<div style='margin-bottom:10px;'>"
                f"{_icon_html(icon_key, fallback)}"
                f"</div>"
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
