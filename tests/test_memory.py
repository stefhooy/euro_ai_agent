import pytest
from agent.memory import TripMemory

def test_trip_memory_initialization():
    """Test that memory initializes empty."""
    memory = TripMemory()
    assert memory.get_preferences() == {}
    assert memory.get_history() == []

def test_save_preferences():
    """Test saving and updating preferences."""
    memory = TripMemory()
    prefs = {"budget": 1000, "destination": "Paris"}
    memory.save_preferences(prefs)
    assert memory.get_preferences() == prefs
    
    # Update preferences
    memory.save_preferences({"budget": 1500})
    assert memory.get_preferences() == {"budget": 1500, "destination": "Paris"}

def test_add_message():
    """Test appending messages to chat history."""
    memory = TripMemory()
    memory.add_message("user", "Hello")
    history = memory.get_history()
    assert len(history) == 1
    assert history[0] == {"role": "user", "content": "Hello"}

def test_clear_memory():
    """Test clearing all stored memory."""
    memory = TripMemory()
    memory.save_preferences({"budget": 1000})
    memory.add_message("user", "Hi")
    memory.clear()
    assert memory.get_preferences() == {}
    assert memory.get_history() == []