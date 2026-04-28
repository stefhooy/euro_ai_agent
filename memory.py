from typing import List, Dict, Any


class TripMemory:
    """
    A simple in-memory store for the EuroTrip AI agent.
    
    Stores user preferences (budget, duration, etc.) and the 
    conversation history needed for the LangGraph agent to maintain context.
    """

    def __init__(self):
        """Initializes the TripMemory with empty preferences and history."""
        self.preferences: Dict[str, Any] = {}
        self.history: List[Dict[str, str]] = []

    def save_preferences(self, prefs: Dict[str, Any]) -> None:
        """
        Saves or updates the user's trip preferences.
        
        Args:
            prefs (dict): A dictionary containing trip parameters like:
                          - budget (float)
                          - duration (int)
                          - departure_city (str)
                          - travel_style (str)
                          - activity_preferences (list)
                          - pace (str)
                          - travel_month (int)
        """
        self.preferences.update(prefs)

    def add_message(self, role: str, content: str) -> None:
        """
        Adds a new message to the conversation history.
        
        Args:
            role (str): The role of the message sender (e.g., 'user', 'assistant', 'system').
            content (str): The content of the message.
        """
        self.history.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """
        Retrieves the full conversation history.
        
        Returns:
            list: A list of dictionaries representing the chat history.
        """
        return self.history

    def get_preferences(self) -> Dict[str, Any]:
        """
        Retrieves the currently saved user preferences.
        
        Returns:
            dict: The user's travel preferences.
        """
        return self.preferences

    def clear(self) -> None:
        """Clears all saved preferences and conversation history."""
        self.preferences = {}
        self.history = []