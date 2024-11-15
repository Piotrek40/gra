# events.py
import logging
from typing import Dict, List, Callable

logger = logging.getLogger(__name__)

class EventManager:
    """Zarządza systemem zdarzeń w grze."""
    
    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = {}
        
    def register_listener(self, event_type: str, callback: Callable):
        """Rejestruje nowego słuchacza dla danego typu zdarzenia."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        
    def emit(self, event_type: str, **kwargs):
        """Emituje zdarzenie danego typu."""
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    logger.error(f"Błąd podczas obsługi zdarzenia {event_type}: {e}")