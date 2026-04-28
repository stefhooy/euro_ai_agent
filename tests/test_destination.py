import pytest
from tools.destination import score_destinations

def test_score_destinations():
    """Test that destination scorer filters and ranks cities properly."""
    preferences = {
        "budget": 5000,
        "duration": 5,
        "travel_style": "luxury",
        "activity_preferences": ["history", "museums"],
        "travel_month": 6
    }
    
    result = score_destinations(preferences)
    top_destinations = result.get("top_destinations", [])
    
    # Check that we got up to 5 destinations
    assert len(top_destinations) > 0
    assert len(top_destinations) <= 5
    
    # Check that the results are sorted by score in descending order
    scores = [city["score"] for city in top_destinations]
    assert scores == sorted(scores, reverse=True)
