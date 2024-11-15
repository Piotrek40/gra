# quests.py
import json
from typing import Dict, List, Optional

class Quest:
    def __init__(self, quest_id: str, data: dict):
        self.id = quest_id
        self.name = data['name']
        self.description = data['description']
        self.giver = data['giver']
        self.type = data['type']
        self.difficulty = data['difficulty']
        self.min_level = data.get('min_level', 1)
        self.stages = data['stages']
        self.rewards = data['rewards']
        self.current_stage = 0
        self.completed = False
        self.active = False
        self.failed = False
        self.time_limit = data.get('time_limit', None)
        self.repeatable = data.get('repeatable', False)
        self.cooldown = data.get('cooldown', None)
        self.prerequisites = data.get('prerequisites', {})
        self.choices = []
        self.failure_penalties = data.get('failure_penalties', {})

    def start(self):
        """Rozpoczyna quest."""
        self.active = True
        self.current_stage = 0
        return f"Rozpoczęto zadanie: {self.name}"

    def advance_stage(self):
        """Przechodzi do następnego etapu questa."""
        if self.current_stage < len(self.stages) - 1:
            self.current_stage += 1
            return True, f"Ukończono etap questa: {self.stages[self.current_stage-1]['description']}"
        else:
            self.complete()
            return False, "Quest ukończony!"

    def complete(self):
        """Kończy quest jako ukończony."""
        self.completed = True
        self.active = False
        return "Quest ukończony! Odbierz nagrody."

    def fail(self):
        """Oznacza quest jako nieudany."""
        self.failed = True
        self.active = False
        return "Quest nieudany!"

    def can_start(self, player) -> tuple[bool, str]:
        """Sprawdza czy gracz może rozpocząć questa."""
        if player.level < self.min_level:
            return False, f"Wymagany poziom: {self.min_level}"
        
        if self.prerequisites:
            if 'reputation' in self.prerequisites:
                for faction, required_rep in self.prerequisites['reputation'].items():
                    if player.get_reputation(faction) < required_rep:
                        return False, f"Wymagana reputacja z {faction}: {required_rep}"
        
        return True, "Możesz rozpocząć questa!"

    def get_current_stage(self) -> dict:
        """Zwraca informacje o aktualnym etapie questa."""
        if 0 <= self.current_stage < len(self.stages):
            return self.stages[self.current_stage]
        return {}

    def get_stage_objective(self) -> str:
        """Zwraca opis aktualnego celu questa."""
        stage = self.get_current_stage()
        if stage:
            return stage['description']
        return ""

class QuestManager:
    def __init__(self, data_file='data/quests.json'):
        self.quests: Dict[str, Quest] = {}
        self.active_quests: List[Quest] = []
        self.completed_quests: List[Quest] = []
        self.quest_dependencies: Dict[str, List[str]] = {}  # Dodać zależności między questami
        self.load_quests(data_file)
        
    def validate_quest_data(self, quest_data: dict) -> bool:
        """Walidacja danych questa."""
        required_fields = ['name', 'description', 'objectives', 'rewards']
        return all(field in quest_data for field in required_fields)

    def load_quests(self, data_file: str):
        """Ładuje questy z pliku JSON."""
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for quest_id, quest_data in data['quests'].items():
                    self.quests[quest_id] = Quest(quest_id, quest_data)
        except FileNotFoundError:
            print(f"Błąd: Nie znaleziono pliku {data_file}")
        except json.JSONDecodeError:
            print(f"Błąd: Nieprawidłowy format pliku {data_file}")

    def get_available_quests(self, player, location: str) -> List[Quest]:
        """Zwraca listę questów dostępnych w danej lokacji dla gracza."""
        available_quests = []
        for quest in self.quests.values():
            if not quest.active and not quest.completed and quest.giver in location:
                can_start, _ = quest.can_start(player)
                if can_start:
                    available_quests.append(quest)
        return available_quests

    def start_quest(self, quest_id: str, player) -> tuple[bool, str]:
        """Rozpoczyna quest dla gracza."""
        if quest_id not in self.quests:
            return False, "Nie znaleziono questa!"
        
        quest = self.quests[quest_id]
        
        if quest.active:
            return False, "Ten quest jest już aktywny!"
            
        if quest.completed and not quest.repeatable:
            return False, "Ten quest został już ukończony!"
            
        can_start, message = quest.can_start(player)
        if not can_start:
            return False, message
            
        quest.start()
        self.active_quests.append(quest)
        return True, f"Rozpoczęto quest: {quest.name}"

    def update_quest_progress(self, player, event_type: str, target: str, count: int = 1) -> List[str]:
        """Aktualizuje postęp questów na podstawie wydarzeń w grze."""
        messages = []
        for quest in self.active_quests:
            stage = quest.get_current_stage()
            if stage['objective'] == event_type and stage['target'] == target:
                # Sprawdź czy jest wymagana liczba
                if 'count' in stage:
                    if count >= stage['count']:
                        success, message = quest.advance_stage()
                        messages.append(message)
                        if not success:  # Quest ukończony
                            self.complete_quest(quest.id, player)
                else:
                    success, message = quest.advance_stage()
                    messages.append(message)
                    if not success:  # Quest ukończony
                        self.complete_quest(quest.id, player)
        return messages

    def complete_quest(self, quest_id: str, player) -> tuple[bool, str]:
        """Kończy questa i przyznaje nagrody."""
        if quest_id not in self.quests:
            return False, "Nie znaleziono questa!"
            
        quest = self.quests[quest_id]
        if not quest.active:
            return False, "Ten quest nie jest aktywny!"
            
        # Przyznaj nagrody
        rewards = quest.rewards
        if 'gold' in rewards:
            player.gold += rewards['gold']
        if 'exp' in rewards:
            player.gain_exp(rewards['exp'])
        if 'items' in rewards:
            for item_id in rewards['items']:
                player.inventory.add_item(item_id)
        if 'reputation' in rewards:
            for faction, value in rewards['reputation'].items():
                player.add_reputation(faction, value)
                
        quest.complete()
        self.active_quests.remove(quest)
        self.completed_quests.append(quest)
        return True, f"Ukończono quest: {quest.name}! Otrzymano nagrody."

    def get_quest_status(self, quest_id: str) -> Optional[str]:
        """Zwraca status questa."""
        if quest_id not in self.quests:
            return None
            
        quest = self.quests[quest_id]
        if quest.completed:
            return "Ukończony"
        elif quest.failed:
            return "Nieudany"
        elif quest.active:
            return f"W trakcie ({quest.get_stage_objective()})"
        else:
            return "Dostępny"

    def show_available_quests(self, player):
        """Wyświetla dostępne questy."""
        print("\n=== Dostępne Questy ===")
        available_quests = self.get_available_quests(player, player.current_location)
        if not available_quests:
            print("Brak dostępnych questów w tej lokacji.")
            return
            
        for quest in available_quests:
            print(f"\n- {quest.name} (Poziom: {quest.min_level})")
            print(f"  Trudność: {quest.difficulty}")
            print(f"  Opis: {quest.description}")

    def show_active_quests(self):
        """Wyświetla aktywne questy."""
        print("\n=== Aktywne Questy ===")
        if not self.active_quests:
            print("Nie masz aktywnych questów.")
            return
            
        for quest in self.active_quests:
            print(f"\n- {quest.name}")
            print(f"  Aktualny cel: {quest.get_stage_objective()}")
            if quest.time_limit:
                print(f"  Pozostały czas: {quest.time_limit}")

    def show_completed_quests(self):
        """Wyświetla ukończone questy."""
        print("\n=== Ukończone Questy ===")
        if not self.completed_quests:
            print("Nie masz ukończonych questów.")
            return
            
        for quest in self.completed_quests:
            print(f"- {quest.name}")

    # Dodanie serializacji stanu questów
    def serialize_state(self) -> dict:
        return {
            'active_quests': [q.serialize() for q in self.active_quests],
            'completed_quests': [q.serialize() for q in self.completed_quests],
            'quest_log': self.quest_log
        }

    # Brak metody deserializacji stanu questów
    def load_state(self, state_data: dict):
        """Wczytuje stan questów z zapisanych danych."""
        self.active_quests = [Quest(**data) for data in state_data.get('active_quests', [])]
        self.completed_quests = [Quest(**data) for data in state_data.get('completed_quests', [])]
        self.quest_log = state_data.get('quest_log', [])