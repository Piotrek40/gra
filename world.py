# world.py
from typing import Dict, List, Optional, Set
import json
import random
from dataclasses import dataclass
from config import game_config
import logging

logger = logging.getLogger(__name__)

@dataclass
class Weather:
    """Klasa reprezentująca pogodę w lokacji."""
    type: str  # sunny, rainy, cloudy, stormy, etc.
    intensity: float  # 0.0 to 1.0
    effects: Dict[str, float]  # wpływ na różne aspekty gry
    description: str

@dataclass
class ResourceNode:
    """Klasa reprezentująca źródło zasobów w lokacji."""
    type: str  # ore, herbs, wood, etc.
    resource_id: str
    quantity: int
    respawn_time: int  # w minutach
    last_harvested: float = 0.0
    required_skill: Optional[str] = None
    required_skill_level: int = 0

class Location:
    def __init__(self, loc_id: str, data: dict):
        self.id = loc_id
        self.name = data['name']
        self.description = data['description']
        self.items = list(data.get('items', []))
        self.exits = list(data.get('exits', []))
        self.level_requirement = data.get('level_requirement', 1)
        self.danger_level = data.get('danger_level', 1)
        self.type = data.get('type', 'neutral')  # neutral, safe, dangerous, dungeon
        self.npcs = npcs = data.get('npcs', []) # lista ID NPC w lokacji 
        # Zaawansowane właściwości
        self.weather: Optional[Weather] = None
        self.resources: List[ResourceNode] = []
        self.discovered = False
        self.events = data.get('events', [])
        self.npcs = set(data.get('npcs', []))
        self.enemies = set(data.get('enemies', []))
        self.buildings = data.get('buildings', {})
        self.quest_triggers = data.get('quest_triggers', [])
        
        # Dynamiczne właściwości
        self.active_events = set()
        self.temporary_npcs = set()
        self.visited_count = 0
        self.last_visited = 0.0
        
        self._initialize_resources(data.get('resources', []))
        self._initialize_weather()

    def _initialize_resources(self, resource_data: List[dict]):
        """Inicjalizuje źródła zasobów w lokacji."""
        for res_data in resource_data:
            self.resources.append(ResourceNode(
                type=res_data['type'],
                resource_id=res_data['id'],
                quantity=res_data['quantity'],
                respawn_time=res_data['respawn_time'],
                required_skill=res_data.get('required_skill'),
                required_skill_level=res_data.get('required_skill_level', 0)
            ))

    def _initialize_weather(self):
        """Inicjalizuje system pogody dla lokacji."""
        weather_types = {
            'sunny': {
                'description': 'Słoneczna pogoda',
                'effects': {'visibility': 1.2, 'movement_speed': 1.1}
            },
            'rainy': {
                'description': 'Pada deszcz',
                'effects': {'visibility': 0.8, 'movement_speed': 0.9}
            },
            'stormy': {
                'description': 'Szaleje burza',
                'effects': {'visibility': 0.6, 'movement_speed': 0.7, 'combat_accuracy': 0.8}
            }
        }
        
        # Losowy wybór pogody z uwzględnieniem typu lokacji
        weather_type = random.choice(list(weather_types.keys()))
        weather_data = weather_types[weather_type]
        
        self.weather = Weather(
            type=weather_type,
            intensity=random.uniform(0.5, 1.0),
            effects=weather_data['effects'],
            description=weather_data['description']
            
    
        )

    def add_item(self, item_id: str):
        if item_id not in self.items:
            self.items.append(item_id)

    def remove_item(self, item_id: str):
        if item_id in self.items:
            self.items.remove(item_id)

    def add_npc(self, npc_id: str):
        if npc_id not in self.npcs:
            self.npcs.append(npc_id)

    def remove_npc(self, npc_id: str):
        if npc_id in self.npcs:
            self.npcs.remove(npc_id)


    def update(self, game_time: float):
        """Aktualizuje stan lokacji."""
        # Aktualizacja zasobów
        for resource in self.resources:
            if resource.quantity < 1 and (game_time - resource.last_harvested) >= resource.respawn_time:
                resource.quantity = random.randint(1, 3)

        # Aktualizacja pogody
        if random.random() < 0.1:  # 10% szansa na zmianę pogody
            self._initialize_weather()

        # Sprawdzanie i aktywacja wydarzeń
        self._check_events(game_time)

    def _check_events(self, game_time: float):
        """Sprawdza i aktywuje wydarzenia w lokacji."""
        for event_data in self.events:
            event_id = event_data['id']
            if event_id not in self.active_events:
                if self._should_trigger_event(event_data, game_time):
                    self.active_events.add(event_id)
                    logger.info(f"Aktywowano wydarzenie {event_id} w lokacji {self.name}")

    def _should_trigger_event(self, event_data: dict, game_time: float) -> bool:
        """Sprawdza czy wydarzenie powinno zostać aktywowane."""
        # Sprawdzenie warunków czasowych
        if 'time_condition' in event_data:
            time_condition = event_data['time_condition']
            if not self._check_time_condition(time_condition, game_time):
                return False

        # Sprawdzenie warunków pogodowych
        if 'weather_condition' in event_data:
            if event_data['weather_condition'] != self.weather.type:
                return False

        # Sprawdzenie innych warunków
        probability = event_data.get('probability', 1.0)
        return random.random() < probability

    def _check_time_condition(self, condition: dict, game_time: float) -> bool:
        """Sprawdza warunki czasowe dla wydarzenia."""
        # Implementacja sprawdzania warunków czasowych
        return True  # Tymczasowo zawsze True

    def add_temporary_npc(self, npc_id: str, duration: float):
        """Dodaje tymczasowego NPC do lokacji."""
        self.temporary_npcs.add(npc_id)
        # Tutaj można dodać logikę usuwania NPC po określonym czasie

    def remove_temporary_npc(self, npc_id: str):
        """Usuwa tymczasowego NPC z lokacji."""
        self.temporary_npcs.discard(npc_id)

    def get_all_npcs(self) -> Set[str]:
        """Zwraca wszystkich NPC w lokacji."""
        return self.npcs.union(self.temporary_npcs)

    def can_enter(self, player) -> tuple[bool, str]:
        """Sprawdza czy gracz może wejść do lokacji."""
        if player.level < self.level_requirement:
            return False, f"Wymagany poziom: {self.level_requirement}"
        return True, ""

    def get_location_info(self) -> dict:
        """Zwraca pełne informacje o lokacji."""
        return {
            'name': self.name,
            'description': self.description,
            'weather': f"{self.weather.description} (intensywność: {self.weather.intensity:.1f})",
            'danger_level': self.danger_level,
            'exits': self.exits,
            'resources': [
                f"{r.type} (ilość: {r.quantity})" for r in self.resources if r.quantity > 0
            ],
            'active_events': list(self.active_events),
            'npcs': list(self.get_all_npcs())
        }

class World:
    def __init__(self, data_file: str = 'data/world.json'):
        self.locations: Dict[str, Location] = {}
        self.npcs: Dict[str, NPC] = {}
        self.events: List[WorldEvent] = []
        self.time_manager = None  # Dodać zarządzanie czasem
        self.weather_system = None  # Dodać system pogody
        
    def load_world_data(self):
        """Ładowanie danych świata."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.validate_world_data(data)
                # Implementacja ładowania danych...
        except Exception as e:
            logger.error(f"Błąd ładowania świata: {e}")
            raise

    def get_location(self, loc_id: str) -> Optional[Location]:
        """Pobiera lokację po ID."""
        return self.locations.get(loc_id)

    def update(self, game_time: float):
        """Aktualizuje stan świata."""
        self.current_time = game_time
        for location in self.locations.values():
            location.update(game_time)
        self._update_global_events(game_time)

    def _update_global_events(self, game_time: float):
        """Aktualizuje globalne wydarzenia w świecie."""
        # Implementacja globalnych wydarzeń
        pass

    def discover_location(self, loc_id: str):
        """Oznacza lokację jako odkrytą."""
        if loc_id in self.locations:
            self.locations[loc_id].discovered = True

    def get_connected_locations(self, loc_id: str) -> List[str]:
        """Zwraca listę lokacji połączonych z daną lokacją."""
        if loc_id in self.locations:
            return self.locations[loc_id].exits
        return []

    def get_safe_locations(self) -> List[str]:
        """Zwraca listę bezpiecznych lokacji."""
        return [loc_id for loc_id, loc in self.locations.items() 
                if loc.type == 'safe']

    def get_dangerous_locations(self) -> List[str]:
        """Zwraca listę niebezpiecznych lokacji."""
        return [loc_id for loc_id, loc in self.locations.items() 
                if loc.type == 'dangerous']