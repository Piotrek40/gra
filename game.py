# game.py
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from config import game_config
from world import World
from player import Player
from character import CharacterManager
from combat import CombatSystem
from quests import QuestManager
from interface import GameInterface
from inventory import Inventory  # Dodaj import
import logging  # Dodaj import
from items import ItemManager  # Dodaj import
from events import EventManager  # Dodaj ten import
from dialogue import DialogueManager  # Dodaj ten import
import tkinter as tk
from save_load import SaveManager  # Dodaj brakujący import

logger = logging.getLogger(__name__)  # Dodaj logger


@dataclass
class GameTime:
    """Zarządzanie czasem w grze."""
    real_start_time: float = 0.0
    game_start_time: float = 0.0
    time_scale: float = 24.0  # 1 minuta realna = 24 minuty w grze
    
    def get_game_time(self) -> float:
        """Zwraca aktualny czas gry w sekundach."""
        real_elapsed = time.time() - self.real_start_time
        return self.game_start_time + (real_elapsed * self.time_scale)
    
    def format_game_time(self) -> str:
        """Formatuje czas gry do czytelnej postaci."""
        total_seconds = int(self.get_game_time())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

class GameEngine:
    """Główny silnik gry integrujący wszystkie systemy."""
    
    def __init__(self):
        self.game_time = GameTime()
        self.running = False
        self.paused = False
        
        # Inicjalizacja głównych systemów
        logger.info("Inicjalizacja systemów gry...")
        
        # Tworzenie menedżerów
        self.world = World()
        self.item_manager = ItemManager()
        self.character_manager = CharacterManager()
        self.quest_manager = QuestManager()
        self.combat_system = CombatSystem()
        self.interface = GameInterface()
        self.event_manager = EventManager()
        self.dialogue_manager = DialogueManager()
        self.save_manager = SaveManager()
        
        # Inicjalizacja kolejek
        self.event_queue = []
        self.message_queue = []
        
        # Stan gry
        self.player = None
        self.active_dialogs = {}
        self.active_trades = {}
        self.active_combats = {}
        
        # Rejestracja listenerów zdarzeń
        self.event_manager.register_listener('combat_start', self.combat_system.start_combat)
        self.event_manager.register_listener('quest_complete', self.quest_manager.complete_quest)
        
        logger.info("Inicjalizacja zakończona")

    def new_game(self, player_name: str):
        try:
            logger.info(f"Rozpoczynanie nowej gry dla gracza: {player_name}")
            
            player_data = {
                'name': player_name,
                'type': 'player',
                'stats': {
                    'health': 100,
                    'max_health': 100,
                    'mana': 50,
                    'max_mana': 50,
                    'strength': 10,
                    'defense': 5
                },
                'behavior': 'player',  # Jeśli wymagane przez Character
                'dialogue': None
            }
            
            self.player = Player(player_name, player_data)
            self.player.inventory.set_item_manager(self.item_manager)
            self.player.initialize_quests(self.quest_manager)
            self.player.current_location = "miasto_startowe"
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia nowej gry: {e}")
            return False

    def _give_starting_items(self):
        """Dodaje początkowe przedmioty dla gracza."""
        starting_items = game_config.get('gameplay.starting_items', {})
        for item_id, amount in starting_items.items():
            self.player.inventory.add_item(item_id, amount)

    def load_game(self, save_data: dict) -> tuple[bool, str]:
        """Wczytuje zapisaną grę."""
        try:
            logger.info("Wczytywanie zapisanej gry...")
            
            # Wczytaj dane gracza
            self.player = Player(save_data['player_data']['basic_info']['name'])
            success, message = self.player.load_game(save_data)
            if not success:
                return False, message
            
            # Wczytaj stan świata
            self.world.load_state(save_data.get('world_state', {}))
            
            # Wczytaj stan NPCs
            self.character_manager.load_state(save_data.get('npc_state', {}))
            
            # Ustaw czas gry
            self.game_time.game_start_time = save_data['game_state']['game_time']
            self.game_time.real_start_time = time.time()
            
            self.running = True
            logger.info("Gra wczytana pomyślnie")
            return True, "Pomyślnie wczytano grę!"
            
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania gry: {e}")
            return False, "Wystąpił błąd podczas wczytywania gry!"

    def save_game(self) -> tuple[bool, str, Optional[dict]]:
        """Zapisuje stan gry."""
        try:
            logger.info("Zapisywanie stanu gry...")
            
            save_data = {
                'player_data': self.player.save_game()['player_data'],
                'world_state': self.world.get_state(),
                'npc_state': self.character_manager.get_state(),
                'game_state': {
                    'game_time': self.game_time.get_game_time(),
                    'version': game_config.get('version')
                }
            }
            
            return True, "Gra została zapisana!", save_data
            
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania gry: {e}")
            return False, "Wystąpił błąd podczas zapisywania gry!", None

    def update_game_state(self):
        """Aktualizuje stan gry."""
        if not self.running or self.paused:
            return
            
        # Aktualizacja świata
        self.world.update(self.game_time.get_game_time())
        
        # Aktualizacja gracza
        self.player.update(self.game_time.get_game_time())
        
        # Aktualizacja NPC
        self.character_manager.update(self.game_time.get_game_time())
        
        # Aktualizacja aktywnych walk
        self._update_combats()   
        
        # Przetwarzanie kolejki wydarzeń
        self._process_event_queue ()  
        
        # Przetwarzanie kolejki wiadomości
        self._process_message_queue()

    def handle_command(self, command: str) -> str:
        """Obsługuje komendy gracza."""
        if not self.running:
            return "Gra nie jest uruchomiona!"
            
        if not self.player:
            return "Gracz nie został zainicjalizowany!"
            
        command = command.lower().strip()
        
        # Podstawowe komendy
        if command == "rozejrzyj się":
            location = self.world.get_location(self.player.current_location)
            return f"\n=== {location.name} ===\n{location.description}"
        elif command == "status":
            return self.interface.show_status(self.player)
        elif command == "ekwipunek":
            return self.interface.show_inventory(self.player)
        elif command == "questy":
            return self.interface.show_quests(self.player)
        elif command == "pomoc":
            return self.interface.show_help()
        else:
            return "Nieznana komenda. Wpisz 'pomoc' aby zobaczyć dostępne komendy."

    def _update_combats(self):
        """Aktualizuje stan aktywnych walk."""
        for combat_id, combat in list(self.active_combats.items()):
            if combat.is_finished():
                self._handle_combat_end(combat)
                del self.active_combats[combat_id]
            else:
                combat.update()

    def _handle_combat_end(self, combat):
        """Obsługuje zakończenie walki."""
        result = combat.get_result()
        if result.winner == self.player:
            self._handle_combat_victory(combat)
        elif result.winner == combat.enemy:
            self._handle_combat_defeat(combat)

    def _handle_combat_victory(self, combat):
        """Obsługuje zwycięstwo w walce."""
        # Przyznaj doświadczenie
        exp_gained = combat.enemy.experience_value
        self.player.gain_experience(exp_gained)
        
        # Zbierz łup
        loot = combat.enemy.get_loot()
        for item in loot:
            self.player.inventory.add_item(item['id'], item['amount'])
            
        # Aktualizuj questy
        self.player.update_quest_progress('kill', combat.enemy.id)
        
        # Aktualizuj statystyki
        self.player.player_stats['monsters_killed'] += 1

    def _handle_combat_defeat(self, combat):
        """Obsługuje porażkę w walce."""
        # Kary za śmierć
        self.player.apply_death_penalty()
        
        # Przywróć gracza do ostatniego bezpiecznego punktu
        self._respawn_player()

    def _respawn_player(self):
        """Przywraca gracza po śmierci."""
        # Znajdź najbliższy bezpieczny punkt
        spawn_point = self.world.get_nearest_safe_location(self.player.current_location)
        
        # Teleportuj gracza
        self.player.current_location = spawn_point
        
        # Przywróć podstawowe statystyki
        self.player.stats.health = self.player.stats.max_health // 2
        self.player.stats.stamina = self.player.stats.max_stamina
        self.player.stats.mana = self.player.stats.max_mana

    def _process_event_queue(self):
        """Przetwarza kolejkę wydarzeń."""
        while self.event_queue:
            event = self.event_queue.pop(0)
            try:
                self._handle_event(event)
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania wydarzenia: {e}")

    def _handle_event(self, event):
        """Obsługuje pojedyncze wydarzenie."""
        event_type = event['type']
        
        if event_type == 'quest_update':
            self.player.update_quest_progress(
                event['objective_type'],
                event['target_id'],
                event.get('amount', 1)
            )
        elif event_type == 'world_event':
            self.world.trigger_event(event['event_id'])
        elif event_type == 'combat_start':
            self._start_combat(event['enemy_id'])
        elif event_type == 'item_pickup':
            self.player.pickup_item(event['item_id'])

    def _process_message_queue(self):
        """Przetwarza kolejkę wiadomości."""
        while self.message_queue:
            message = self.message_queue.pop(0)
            self.interface.show_message(message['text'], message['type'])

    command_handlers = {
        'idz': lambda self, args: self._handle_move(args),
        'atakuj': lambda self, args: self._handle_attack(args),
        'uzyj': lambda self, args: self._handle_use(args),
        'ekwipunek': lambda self, args: self._handle_inventory(args),
        'rozmawiaj': lambda self, args: self._handle_talk(args),
        'handluj': lambda self, args: self._handle_trade(args),
        'pomoc': lambda self, args: self._show_help(),
        'status': lambda self, args: self._show_status(),
        'questy': lambda self, args: self._show_quests(),
        'umiejetnosci': lambda self, args: self._show_skills(),
        'zapisz': lambda self, args: self._handle_save(),
        'wczytaj': lambda self, args: self._handle_load(args)
    }

    # Implementacje handlerów komend...
    # Kontynuacja klasy GameEngine

    def _handle_move(self, args: List[str]) -> str:
        """Obsługa komendy poruszania się."""
        if not args:
            available_exits = self.world.get_location(self.player.current_location).exits
            return f"Dokąd chcesz iść? Dostępne kierunki: {', '.join(available_exits)}"

        destination = ' '.join(args).lower()
        current_location = self.world.get_location(self.player.current_location)
        
        if destination not in current_location.exits:
            return "Nie możesz tam pójść!"
            
        # Sprawdź czy gracz może wejść do lokacji
        new_location = self.world.get_location(destination)
        can_enter, reason = new_location.can_enter(self.player)
        if not can_enter:
            return reason
            
        # Sprawdź czy są aktywne walki
        if self.active_combats:
            return "Nie możesz się przemieszczać podczas walki!"
            
        # Wykonaj ruch
        old_location = self.player.current_location
        self.player.current_location = destination
        self.player.known_locations.add(destination)
        
        # Aktualizuj statystyki
        self.player.player_stats['distance_traveled'] += 1
        
        # Sprawdź questy
        self.player.update_quest_progress('visit', destination)
        
        # Opisz nową lokację
        description = self._get_location_description(new_location)
        
        # Sprawdź i aktywuj wydarzenia w nowej lokacji
        self._check_location_events(new_location)
        
        return description

    def _get_location_description(self, location) -> str:
        """Generuje opis lokacji z uwzględnieniem wszystkich elementów."""
        description = [f"\n=== {location.name} ===\n"]
        description.append(location.description)
        
        # Dodaj opis pogody
        if location.weather:
            description.append(f"\nPogoda: {location.weather.description}")
            
        # Pokaż NPC
        npcs = self.character_manager.get_characters_in_location(location.id)
        if npcs:
            description.append("\nPostacie w pobliżu:")
            for npc in npcs:
                if not npc.is_enemy:
                    description.append(f"- {npc.name}")
                    
        # Pokaż przeciwników
        enemies = [npc for npc in npcs if npc.is_enemy]
        if enemies and self.player.get_skill_level('tracking') > 0:
            description.append("\nPrzeciwników w pobliżu:")
            for enemy in enemies:
                description.append(f"- {enemy.name} (Poziom {enemy.level})")
                
        # Pokaż przedmioty
        if location.items:
            description.append("\nPrzedmioty w pobliżu:")
            for item_id in location.items:
                item = self.item_manager.get_item(item_id)
                description.append(f"- {item.name}")
                
        # Pokaż zasoby
        if location.resources and self.player.get_skill_level('gathering') > 0:
            description.append("\nDostępne zasoby:")
            for resource in location.resources:
                if resource.quantity > 0:
                    description.append(f"- {resource.type} (x{resource.quantity})")
                    
        # Pokaż wyjścia
        description.append("\nMożliwe kierunki:")
        description.append(", ".join(location.exits))
        
        return "\n".join(description)

    def _handle_attack(self, args: List[str]) -> str:
        """Obsługa komendy ataku."""
        if not args:
            return "Kogo chcesz zaatakować?"
            
        target_name = ' '.join(args).lower()
        current_location = self.world.get_location(self.player.current_location)
        
        # Znajdź przeciwnika
        enemies = [npc for npc in self.character_manager.get_characters_in_location(current_location.id)
                  if npc.is_enemy and npc.name.lower() == target_name]
                  
        if not enemies:
            return "Nie ma tu takiego przeciwnika!"
            
        enemy = enemies[0]
        
        # Sprawdź czy walka jest już aktywna
        if enemy.id in self.active_combats:
            return "Już walczysz z tym przeciwnikiem!"
            
        # Rozpocznij walkę
        combat = self.combat_system.start_combat(self.player, enemy)
        self.active_combats[enemy.id] = combat
        
        # Pokaż interfejs walki
        self.interface.show_combat_interface(combat)
        
        return f"Rozpoczęto walkę z {enemy.name}!"

    def _handle_use(self, args: List[str]) -> str:
        """Obsługa komendy użycia przedmiotu lub zdolności."""
        if not args:
            return "Co chcesz użyć?"
            
        item_or_ability = ' '.join(args).lower()
        
        # Najpierw sprawdź czy to przedmiot
        item_id = self.item_manager.get_item_id_by_name(item_or_ability)
        if item_id and self.player.inventory.has_item(item_id):
            success, message = self.player.inventory.use_item(item_id, self.player)
            if success:
                self._check_item_use_achievements(item_id)
            return message
            
        # Jeśli nie przedmiot, sprawdź czy to zdolność
        for ability_id, ability in self.player.abilities.items():
            if ability['name'].lower() == item_or_ability:
                success, message = self.player.use_ability(ability_id)
                return message
                
        return "Nie możesz tego użyć!"

    def _handle_inventory(self, args: List[str]) -> str:
        """Obsługa komendy ekwipunku."""
        if not args:
            # Pokaż całe ekwipunek
            return self.interface.show_inventory(self.player.inventory, self.player.equipment_slots)
            
        action = args[0].lower()
        if len(args) < 2:
            return "Określ przedmiot!"
            
        item_name = ' '.join(args[1:])
        item_id = self.item_manager.get_item_id_by_name(item_name)
        
        if not item_id:
            return "Nie ma takiego przedmiotu!"
            
        if action == "zaloz":
            success, message = self.player.equip_item(item_id)
        elif action == "zdejmij":
            success, message = self.player.unequip_item(item_id)
        elif action == "wyrzuc":
            success, message = self.player.inventory.remove_item(item_id)
        else:
            return "Nieznana akcja! Dostępne: zaloz, zdejmij, wyrzuc"
            
        return message

    def _handle_talk(self, args: List[str]) -> str:
        """Obsługa komendy rozmowy z NPC."""
        if not args:
            return "Z kim chcesz porozmawiać?"
            
        npc_name = ' '.join(args).lower()
        npcs = self.character_manager.get_characters_in_location(self.player.current_location)
        
        npc = next((n for n in npcs if n.name.lower() == npc_name), None)
        if not npc:
            return "Nie ma tu takiej osoby!"
            
        # Sprawdź czy NPC nie jest w trakcie innej rozmowy
        if npc.id in self.active_dialogs:
            return f"{npc.name} jest zajęty rozmową z kimś innym!"
            
        # Rozpocznij dialog
        dialog = self.interface.start_dialog(npc, self.player)
        self.active_dialogs[npc.id] = dialog
        
        return dialog.get_current_text()

    def _handle_trade(self, args: List[str]) -> str:
        """Obsługa komendy handlu."""
        current_location = self.world.get_location(self.player.current_location)
        merchants = [npc for npc in self.character_manager.get_characters_in_location(current_location.id)
                    if isinstance(npc, Merchant)]
                    
        if not merchants:
            return "Nie ma tu nikogo do handlu!"
            
        merchant = merchants[0]
        if merchant.id in self.active_trades:
            return "Już handlujesz z tym kupcem!"
            
        # Rozpocznij handel
        trade_session = self.interface.start_trade(merchant, self.player)
        self.active_trades[merchant.id] = trade_session
        
        return f"Rozpoczęto handel z {merchant.name}!"

    def _show_help(self) -> str:
        """Pokazuje pomoc dotyczącą dostępnych komend."""
        return self.interface.show_help(self.command_handlers.keys())

    def _show_status(self) -> str:
        """Pokazuje status gracza."""
        return self.interface.show_status(self.player)

    def _show_quests(self) -> str:
        """Pokazuje dziennik questów."""
        return self.interface.show_quest_log(
            self.player.active_quests,
            self.player.completed_quests,
            self.quest_manager.get_available_quests(self.player)
        )

    def _show_skills(self) -> str:
        """Pokazuje umiejętności gracza."""
        return self.interface.show_skills(self.player.skills, self.player.skill_experience)

    def _handle_save(self) -> str:
        """Obsługa zapisu gry."""
        success, message, save_data = self.save_game()
        if success and game_config.get('game_settings.auto_backup', True):
            self._create_backup(save_data)
        return message

    def _handle_load(self, args: List[str]) -> str:
        """Obsługa wczytywania gry."""
        if not args:
            return "Podaj nazwę zapisu!"
            
        save_name = ' '.join(args)
        try:
            save_data = self._load_save_data(save_name)
            success, message = self.load_game(save_data)
            return message
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania zapisu: {e}")
            return "Wystąpił błąd podczas wczytywania zapisu!"

    def _check_location_events(self, location) -> None:
        """Sprawdza i aktywuje wydarzenia w lokacji."""
        current_time = self.game_time.get_game_time()
        
        for event in location.events:
            if event.should_trigger(current_time, self.player):
                self.event_queue.append({
                    'type': 'world_event',
                    'event_id': event.id,
                    'location_id': location.id
                })

    def _check_item_use_achievements(self, item_id: str) -> None:
        """Sprawdza i przyznaje osiągnięcia związane z użyciem przedmiotów."""
        item = self.item_manager.get_item(item_id)
        
        if item.type == 'potion':
            self.player.player_stats['potions_used'] += 1
            if self.player.player_stats['potions_used'] >= 100:
                self.player.unlock_achievement('potion_master')
        elif item.type == 'scroll':
            self.player.player_stats['scrolls_used'] += 1
            if self.player.player_stats['scrolls_used'] >= 50:
                self.player.unlock_achievement('scroll_sage')

    def _create_backup(self, save_data: dict) -> None:
        """Tworzy kopię zapasową stanu gry."""
        try:
            backup_path = f"saves/backup_{int(time.time())}.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
            logger.info(f"Utworzono kopię zapasową: {backup_path}")
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia kopii zapasowej: {e}")

    def _load_save_data(self, save_name: str) -> dict:
        """Wczytuje dane zapisu."""
        save_path = f"saves/{save_name}.json"
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise ValueError(f"Nie znaleziono zapisu o nazwie {save_name}")
        except json.JSONDecodeError:
            raise ValueError(f"Uszkodzony plik zapisu: {save_name}")

    # Dodanie systemu autosave
    def auto_save(self):
        if game_config.get('game_settings.auto_save_enabled', True):
            save_name = f"autosave_{int(time.time())}"
            self.save_manager.save_game(self.get_game_state(), save_name)

    def initialize_systems(self):
        """Inicjalizacja wszystkich systemów gry."""
        # Dodać inicjalizację wszystkich menedżerów
        self.save_manager = SaveManager()
        self.quest_manager = QuestManager()
        self.item_manager = ItemManager()
        # Dodać powiązania między systemami
        self.player.initialize_quests(self.quest_manager)
        self.player.inventory.set_item_manager(self.item_manager)