import streamlit as st


def render_hero() -> None:
    st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;
            justify-content:center;padding:72px 24px 56px;text-align:center;">
    <p style="font-size:3.8rem;margin:0 0 10px;line-height:1;">🌍</p>
    <h1 style="font-family:'Playfair Display',Georgia,serif;
               font-size:clamp(2rem,4.5vw,3.2rem);
               background:linear-gradient(135deg,#93c5fd 0%,#e0f2fe 50%,#bfdbfe 100%);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               margin:0 0 16px;line-height:1.15;">
        EuroTrip Agent
    </h1>
    <p style="font-size:1.1rem;color:#94a3b8;max-width:560px;line-height:1.75;margin:0 0 36px;">
        Set your travel preferences in the sidebar and let the AI build a personalised
        multi-city European itinerary with live weather, cost estimates, and a pricing calendar.
        Visit <strong style="color:#93c5fd;">1 to 6 countries</strong> - the agent enforces
        a minimum of 3 days per country so every stop is worth the journey.
        Six countries is the cap: even on a 30-day trip, more than that becomes a rushed
        airport-to-airport sprint rather than actual travel.
    </p>
    <div style="display:flex;gap:18px;flex-wrap:wrap;justify-content:center;
                color:#60a5fa;font-size:0.92rem;font-weight:500;letter-spacing:0.02em;">
        <span>✈️&nbsp; 40+ European cities</span>
        <span>🗺️&nbsp; 1-6 countries per trip</span>
        <span>💶&nbsp; Budget-aware</span>
        <span>🌤️&nbsp; Live weather</span>
        <span>📅&nbsp; Pricing calendar</span>
        <span>🤖&nbsp; Local AI</span>
    </div>
</div>
""", unsafe_allow_html=True)
