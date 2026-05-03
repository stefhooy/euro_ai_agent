from typing import Any, Dict, List


class TripMemory:
    """In-memory store for agent preferences and conversation history."""

    def __init__(self) -> None:
        self.preferences: Dict[str, Any] = {}
        self.history: List[Dict[str, str]] = []

    def save_preferences(self, prefs: Dict[str, Any]) -> None:
        """Save or update the user's trip preferences."""
        self.preferences.update(prefs)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        self.history.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """Return the full conversation history."""
        return self.history

    def get_preferences(self) -> Dict[str, Any]:
        """Return the currently saved user preferences."""
        return self.preferences

    def clear(self) -> None:
        """Clear all saved preferences and conversation history."""
        self.preferences = {}
        self.history = []
