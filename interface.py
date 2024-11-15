# interface.py

import os
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from colorama import init, Fore, Back, Style
import tkinter as tk
from tkinter import ttk, messagebox
from config import game_config
from exceptions import GameError

logger = logging.getLogger(__name__)
init(autoreset=True)  # Inicjalizacja colorama

class MessageType(Enum):
    """Typy komunikatów w grze."""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'
    SYSTEM = 'system'
    COMBAT = 'combat'
    QUEST = 'quest'
    DIALOG = 'dialog'
    ITEM = 'item'
    SKILL = 'skill'
    ACHIEVEMENT = 'achievement'

@dataclass
class DisplayConfig:
    """Konfiguracja wyświetlania."""
    colors: Dict[str, str]
    symbols: Dict[str, str]
    formatting: Dict[str, str]
    animations: Dict[str, bool]

class GameInterface:
    """Główny interfejs gry."""
    
    def __init__(self):
        self.display_config = self._load_display_config()
        self.terminal_width = os.get_terminal_size().columns
        self.last_message = ""
        self.message_history: List[Tuple[str, MessageType]] = []
        self.animation_enabled = game_config.get('gui.animations_enabled', True)
        self.color_enabled = game_config.get('gui.colors_enabled', True)
        self.debug_mode = game_config.get('game_settings.debug_mode', False)
        
        # Cache dla elementów interfejsu
        self._status_cache = {}
        self._location_cache = {}
        self._combat_cache = {}
        
        # Inicjalizacja kolorów i stylów
        self._init_styles()

    def _load_display_config(self) -> DisplayConfig:
        """Ładuje konfigurację wyświetlania."""
        return DisplayConfig(
            colors={
                'primary': Fore.CYAN,
                'secondary': Fore.YELLOW,
                'success': Fore.GREEN,
                'warning': Fore.YELLOW,
                'error': Fore.RED,
                'health': Fore.RED,
                'mana': Fore.BLUE,
                'stamina': Fore.GREEN,
                'exp': Fore.CYAN,
                'gold': Fore.YELLOW,
                'item_common': Fore.WHITE,
                'item_rare': Fore.BLUE,
                'item_epic': Fore.MAGENTA,
                'item_legendary': Fore.YELLOW
            },
            symbols={
                'health': '❤',
                'mana': '⚡',
                'stamina': '⚡',
                'gold': '⚜',
                'exp': '✧',
                'arrow': '→',
                'checkmark': '✓',
                'cross': '✗',
                'star': '★',
                'bullet': '•'
            },
            formatting={
                'header': Style.BRIGHT,
                'subheader': Style.DIM,
                'important': Style.BRIGHT + Fore.YELLOW,
                'highlight': Back.WHITE + Fore.BLACK
            },
            animations={
                'typing': True,
                'loading': True,
                'combat': True,
                'transitions': True
            }
        )

    def _init_styles(self):
        """Inicjalizuje style dla różnych typów komunikatów."""
        self.message_styles = {
            MessageType.INFO: self.display_config.colors['primary'],
            MessageType.SUCCESS: self.display_config.colors['success'],
            MessageType.WARNING: self.display_config.colors['warning'],
            MessageType.ERROR: self.display_config.colors['error'],
            MessageType.SYSTEM: Style.DIM + Fore.WHITE,
            MessageType.COMBAT: self.display_config.colors['health'],
            MessageType.QUEST: self.display_config.colors['primary'],
            MessageType.DIALOG: self.display_config.colors['secondary'],
            MessageType.ITEM: self.display_config.colors['item_common'],
            MessageType.SKILL: self.display_config.colors['mana'],
            MessageType.ACHIEVEMENT: self.display_config.colors['gold']
        }

    def clear_screen(self):
        """Czyści ekran terminala."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_message(self, message: str, message_type: MessageType = MessageType.INFO):
        """Wyświetla sformatowany komunikat."""
        style = self.message_styles.get(message_type, '')
        formatted_message = f"{style}{message}{Style.RESET_ALL}"
        
        print(formatted_message)
        self.last_message = message
        self.message_history.append((message, message_type))
        
        # Ogranicz historię komunikatów
        if len(self.message_history) > 100:
            self.message_history.pop(0)

    def animate_text(self, text: str, delay: float = 0.03):
        """Wyświetla tekst z animacją."""
        if not self.animation_enabled:
            print(text)
            return
            
        for char in text:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()

    def draw_progress_bar(self, value: float, max_value: float, width: int = 20, 
                         color: str = None, show_percentage: bool = True) -> str:
        """Rysuje pasek postępu."""
        percentage = min(100, (value / max_value) * 100)
        filled_width = int(width * percentage / 100)
        empty_width = width - filled_width
        
        bar_color = color or self.display_config.colors['primary']
        
        bar = (
            f"{bar_color}"
            f"{'█' * filled_width}{'░' * empty_width}"
            f"{Style.RESET_ALL}"
        )
        
        if show_percentage:
            bar += f" {percentage:>3.0f}%"
            
        return bar

    def draw_separator(self, char: str = "=", color: str = None):
        """Rysuje separator na całą szerokość terminala."""
        color = color or self.display_config.colors['primary']
        print(f"{color}{char * self.terminal_width}{Style.RESET_ALL}")

    def center_text(self, text: str, width: int = None) -> str:
        """Centruje tekst."""
        width = width or self.terminal_width
        return text.center(width)

    def format_table(self, headers: List[str], rows: List[List[str]], 
                    colors: List[str] = None) -> str:
        """Formatuje dane w formie tabeli."""
        if not rows:
            return ""
            
        # Oblicz szerokość kolumn
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
                
        # Utwórz separator
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        
        # Formatuj nagłówki
        header_row = "|" + "|".join(
            f" {h:<{w}} " for h, w in zip(headers, col_widths)
        ) + "|"
        
        # Formatuj wiersze
        table_rows = []
        for row in rows:
            colored_row = []
            for i, cell in enumerate(row):
                color = colors[i] if colors and i < len(colors) else ""
                reset = Style.RESET_ALL if color else ""
                colored_row.append(f"{color}{str(cell):<{col_widths[i]}}{reset}")
            table_rows.append(
                "|" + "|".join(f" {cell} " for cell in colored_row) + "|"
            )
            
        # Złącz wszystko
        return "\n".join([
            separator,
            header_row,
            separator,
            *table_rows,
            separator
        ])

    def show_error(self, error: Exception):
        """Wyświetla błąd w przyjazny dla użytkownika sposób."""
        if isinstance(error, GameError):
            self.show_message(str(error), MessageType.ERROR)
        else:
            if self.debug_mode:
                logger.exception("Wystąpił nieoczekiwany błąd:")
            self.show_message(
                "Wystąpił nieoczekiwany błąd podczas wykonywania operacji.", 
                MessageType.ERROR
            )

    def get_input(self, prompt: str = "> ", validation_func = None) -> str:
        """Pobiera dane wejściowe od użytkownika z opcjonalną walidacją."""
        while True:
            try:
                user_input = input(f"{self.display_config.colors['secondary']}{prompt}{Style.RESET_ALL}")
                if validation_func:
                    result = validation_func(user_input)
                    if result is True:
                        return user_input
                    elif isinstance(result, str):
                        self.show_message(result, MessageType.ERROR)
                        continue
                return user_input
            except KeyboardInterrupt:
                print("\n")
                return ""
            except Exception as e:
                self.show_message(
                    "Wystąpił błąd podczas wprowadzania danych.", 
                    MessageType.ERROR
                )
                if self.debug_mode:
                    logger.exception("Błąd wprowadzania:")
                    
    # Kontynuacja klasy GameInterface

    def show_game_status(self, player, world):
        """Wyświetla aktualny stan gry."""
        self.clear_screen()
        self.draw_separator()
        print(self.center_text("STATUS GRY", self.terminal_width))
        self.draw_separator()
        
        # Status gracza
        print(f"\n{self.display_config.colors['primary']}Status Postaci:{Style.RESET_ALL}")
        print(f"Imię: {player.name}")
        print(f"Poziom: {player.level} ({player.experience}/{player.experience_to_next_level} EXP)")
        
        # Paski zdrowia, many i staminy
        health_bar = self.draw_progress_bar(
            player.stats.health, 
            player.stats.max_health,
            color=self.display_config.colors['health']
        )
        mana_bar = self.draw_progress_bar(
            player.stats.mana,
            player.stats.max_mana,
            color=self.display_config.colors['mana']
        )
        stamina_bar = self.draw_progress_bar(
            player.stats.stamina,
            player.stats.max_stamina,
            color=self.display_config.colors['stamina']
        )
        
        print(f"{self.display_config.symbols['health']} Zdrowie: {health_bar}")
        print(f"{self.display_config.symbols['mana']} Mana: {mana_bar}")
        print(f"{self.display_config.symbols['stamina']} Stamina: {stamina_bar}")
        
        # Podstawowe statystyki
        print("\nStatystyki:")
        stats = [
            (f"{self.display_config.colors['primary']}Siła:{Style.RESET_ALL}", player.stats.strength),
            (f"{self.display_config.colors['primary']}Obrona:{Style.RESET_ALL}", player.stats.defense),
            (f"{self.display_config.colors['primary']}Zręczność:{Style.RESET_ALL}", player.stats.agility),
            (f"{self.display_config.colors['primary']}Inteligencja:{Style.RESET_ALL}", player.stats.intelligence)
        ]
        
        for stat, value in stats:
            print(f"{stat} {value}")
            
        # Złoto i ekwipunek
        print(f"\n{self.display_config.symbols['gold']} Złoto: {player.gold}")
        print(f"Ekwipunek: {len(player.inventory.items)}/{player.inventory.capacity}")
        
        # Aktualna lokacja
        location = world.get_location(player.current_location)
        print(f"\n{self.display_config.colors['secondary']}Obecna lokacja:{Style.RESET_ALL} {location.name}")
        
        if location.weather:
            print(f"Pogoda: {location.weather.description}")
            
        # Aktywne efekty
        if player.status_effects:
            print("\nAktywne efekty:")
            for effect in player.status_effects:
                duration = f"({effect.duration}t)" if effect.duration > 0 else "(stały)"
                print(f"- {effect.name} {duration}")

    def show_combat_interface(self, player, enemy, combat_manager):
        """Wyświetla interfejs walki."""
        self.clear_screen()
        self.draw_separator(char="═")
        print(self.center_text(f"WALKA: {player.name} vs {enemy.name}"))
        self.draw_separator(char="═")
        
        # Status gracza
        print(f"\n{self.display_config.colors['primary']}Twój status:{Style.RESET_ALL}")
        player_health = self.draw_progress_bar(
            player.stats.health,
            player.stats.max_health,
            color=self.display_config.colors['health']
        )
        player_stamina = self.draw_progress_bar(
            combat_manager.player_status['stamina'],
            100,
            color=self.display_config.colors['stamina']
        )
        
        print(f"HP: {player_health}")
        print(f"Stamina: {player_stamina}")
        
        # Status przeciwnika
        print(f"\n{self.display_config.colors['error']}Przeciwnik:{Style.RESET_ALL}")
        enemy_health = self.draw_progress_bar(
            enemy.stats.health,
            enemy.stats.max_health,
            color=self.display_config.colors['health']
        )
        print(f"{enemy.name}: {enemy_health}")
        
        # Dostępne akcje
        print("\nDostępne akcje:")
        actions = [
            "1. Atak podstawowy",
            "2. Użyj przedmiotu",
            "3. Użyj umiejętności",
            "4. Przyjmij postawę obronną",
            "5. Spróbuj uciec"
        ]
        
        for action in actions:
            print(action)
            
        # Dziennik walki
        if combat_manager.combat_log:
            print(f"\n{self.display_config.colors['secondary']}Przebieg walki:{Style.RESET_ALL}")
            for message, msg_type in combat_manager.combat_log[-3:]:
                self.show_message(message, msg_type)
                
    def show_status(self, player):
        """Wyświetla status gracza."""
        print(f"\n=== Status Postaci ===")
        print(f"Imię: {player.name}")
        print(f"Poziom: {player.level}")
        print(f"Doświadczenie: {player.experience}/{player.experience_to_next_level}")
        print(f"Zdrowie: {player.stats.health}/{player.stats.max_health}")
        print(f"Siła: {player.stats.strength}")
        print(f"Obrona: {player.stats.defense}")
        print(f"Złoto: {player.gold}")
        
        if player.equipment_slots:
            print("\nWyposażenie:")
            for slot, item_id in player.equipment_slots.items():
                if item_id:
                    item = player.inventory.item_manager.get_item(item_id)
                    print(f"{slot}: {item.name}")
                else:
                    print(f"{slot}: Puste")

    def show_inventory(self, player):
        """Wyświetla ekwipunek gracza."""
        self.clear_screen()
        print(f"\n{self.display_config.colors['primary']}=== EKWIPUNEK ==={Style.RESET_ALL}")
        
        # Założone przedmioty
        print("\nZałożone przedmioty:")
        for slot, item_id in player.equipment_slots.items():
            if item_id:
                item = player.inventory.item_manager.get_item(item_id)
                print(f"{slot}: {self._format_item_name(item)}")
            else:
                print(f"{slot}: {self.display_config.colors['secondary']}pusty{Style.RESET_ALL}")
                
        """Wyświetla ekwipunek gracza."""
        print("\n=== Ekwipunek ===")
        if not player.inventory.items:
            print("Ekwipunek jest pusty!")
            return

        for item_id, quantity in player.inventory.items.items():
            item = player.inventory.item_manager.get_item(item_id)
            print(f"- {item.name} x{quantity}: {item.description}")
                
        # Lista przedmiotów
        print("\nPrzedmioty:")
        if not player.inventory.items:
            print("Ekwipunek jest pusty!")
        else:
            items_table = []
            for item_id, quantity in player.inventory.items.items():
                item = player.inventory.item_manager.get_item(item_id)
                equipped = "*" if item_id in player.equipment_slots.values() else ""
                items_table.append([
                    f"{self._format_item_name(item)}{equipped}",
                    str(quantity),
                    item.type,
                    item.description
                ])
            
            headers = ["Przedmiot", "Ilość", "Typ", "Opis"]
            print(self.format_table(headers, items_table))
            
        print(f"\nPojemność: {len(player.inventory.items)}/{player.inventory.capacity}")
        
        
    def handle_command(self, command: str, game_state):
        """Obsługa komend gracza."""
        if command == "status":
            self.show_status(game_state.player)
        elif command == "ekwipunek":
            self.show_inventory(game_state.player)
        elif command == "questy":
            self.show_quests(game_state.player)
        elif command == "rozejrzyj się":
            location = game_state.world.get_location(game_state.player.current_location)
            print(f"\n=== {location.name} ===")
            print(location.description)
            if location.npcs:
                print("\nPostacie w pobliżu:")
                for npc_id in location.npcs:
                    npc = game_state.character_manager.get_character(npc_id)
                    print(f"- {npc.name}")
        else:
            print("Nieznana komenda!")
            
    def show_quests(self, player):
        """Wyświetla aktywne zadania."""
        print("\n=== Aktywne Questy ===")
        if not player.active_quests:
            print("Nie masz aktywnych zadań!")
            return

        for quest in player.active_quests:
            print(f"\n- {quest.name}")
            print(f"  Opis: {quest.description}")
            current_stage = quest.get_current_stage()
            print(f"  Aktualny cel: {current_stage['description']}")

    def _format_item_name(self, item) -> str:
        """Formatuje nazwę przedmiotu z odpowiednim kolorem."""
        rarity_colors = {
            'common': self.display_config.colors['item_common'],
            'rare': self.display_config.colors['item_rare'],
            'epic': self.display_config.colors['item_epic'],
            'legendary': self.display_config.colors['item_legendary']
        }
        color = rarity_colors.get(item.rarity, self.display_config.colors['item_common'])
        return f"{color}{item.name}{Style.RESET_ALL}"

    def show_trade_interface(self, merchant, player):
        """Wyświetla interfejs handlu."""
        self.clear_screen()
        print(f"\n{self.display_config.colors['primary']}=== HANDEL z {merchant.name} ==={Style.RESET_ALL}")
        print(f"\nTwoje złoto: {self.display_config.colors['gold']}{player.gold}{Style.RESET_ALL}")
        
        # Towary kupca
        print("\nDostępne towary:")
        merchant_items = []
        for item_id in merchant.inventory:
            item = player.inventory.item_manager.get_item(item_id)
            price = merchant.get_sell_price(item_id)
            can_afford = price <= player.gold
            price_color = self.display_config.colors['success'] if can_afford else self.display_config.colors['error']
            
            merchant_items.append([
                self._format_item_name(item),
                f"{price_color}{price}{Style.RESET_ALL}",
                item.description
            ])
            
        if merchant_items:
            headers = ["Przedmiot", "Cena", "Opis"]
            print(self.format_table(headers, merchant_items))
        else:
            print("Kupiec nie ma obecnie żadnych towarów.")
            
        # Opcje handlu
        print("\nOpcje:")
        print("1. Kup przedmiot")
        print("2. Sprzedaj przedmiot")
        print("3. Zakończ handel")

    def show_quest_log(self, player):
        """Wyświetla dziennik zadań."""
        self.clear_screen()
        print(f"\n{self.display_config.colors['primary']}=== DZIENNIK ZADAŃ ==={Style.RESET_ALL}")
        
        # Aktywne questy
        if player.active_quests:
            print(f"\n{self.display_config.colors['secondary']}Aktywne zadania:{Style.RESET_ALL}")
            for quest in player.active_quests:
                current_stage = quest.get_current_stage()
                progress = self.draw_progress_bar(
                    quest.current_stage,
                    len(quest.stages),
                    width=10,
                    show_percentage=False
                )
                print(f"\n- {quest.name} {progress}")
                print(f"  Cel: {current_stage['description']}")
                
                # Pokaż nagrody
                if quest.rewards:
                    print("  Nagrody:")
                    self._display_rewards(quest.rewards)
        else:
            print("\nNie masz aktywnych zadań.")
            
        # Ukończone questy
        if player.completed_quests:
            print(f"\n{self.display_config.colors['success']}Ukończone zadania:{Style.RESET_ALL}")
            for quest in player.completed_quests:
                print(f"- {quest.name} {self.display_config.symbols['checkmark']}")

    def _display_rewards(self, rewards: dict):
        """Wyświetla nagrody questa."""
        for reward_type, value in rewards.items():
            if reward_type == 'gold':
                print(f"  {self.display_config.symbols['gold']} {value} złota")
            elif reward_type == 'exp':
                print(f"  {self.display_config.symbols['exp']} {value} doświadczenia")
            elif reward_type == 'items':
                for item_id, quantity in value.items():
                    item = self.item_manager.get_item(item_id)
                    print(f"  - {self._format_item_name(item)} x{quantity}")
            elif reward_type == 'reputation':
                for faction, amount in value.items():
                    sign = '+' if amount > 0 else ''
                    print(f"  - Reputacja z {faction}: {sign}{amount}")
                    
    # Kontynuacja klasy GameInterface

    def show_dialog_interface(self, npc, player, dialog_manager):
        """Wyświetla interfejs dialogowy."""
        self.clear_screen()
        print(f"\n{self.display_config.colors['secondary']}=== Rozmowa z {npc.name} ==={Style.RESET_ALL}")
        
        # Wyświetl portret/opis NPC
        if hasattr(npc, 'description'):
            print(f"\n{npc.description}")
            
        # Sprawdź nastawienie NPC na podstawie reputacji
        if hasattr(npc, 'faction') and npc.faction in player.reputation:
            reputation = player.reputation[npc.faction]
            attitude = self._get_npc_attitude(reputation)
            print(f"Nastawienie: {attitude}")
            
        # Wyświetl aktualną wypowiedź
        current_dialog = dialog_manager.get_current_dialog()
        if current_dialog:
            print(f"\n{self.display_config.colors['dialog']}\"{current_dialog.text}\"{Style.RESET_ALL}")
            
            # Wyświetl dostępne opcje
            if current_dialog.options:
                print("\nDostępne odpowiedzi:")
                for i, option in enumerate(current_dialog.options, 1):
                    if self._check_dialog_option_requirements(option, player):
                        print(f"{i}. {option.text}")
                    else:
                        print(f"{self.display_config.colors['error']}{i}. {option.text} "
                              f"(Wymagania niespełnione){Style.RESET_ALL}")
                              
        print("\n0. Zakończ rozmowę")

    def _get_npc_attitude(self, reputation: int) -> str:
        """Zwraca tekstowy opis nastawienia NPC na podstawie reputacji."""
        attitudes = [
            (90, f"{self.display_config.colors['success']}Uwielbia cię{Style.RESET_ALL}"),
            (70, f"{self.display_config.colors['success']}Przyjazny{Style.RESET_ALL}"),
            (30, f"{self.display_config.colors['secondary']}Neutralny{Style.RESET_ALL}"),
            (-30, f"{self.display_config.colors['warning']}Nieufny{Style.RESET_ALL}"),
            (-70, f"{self.display_config.colors['error']}Wrogi{Style.RESET_ALL}"),
            (-100, f"{self.display_config.colors['error']}Nienawidzi cię{Style.RESET_ALL}")
        ]
        
        for threshold, attitude in attitudes:
            if reputation >= threshold:
                return attitude
        return attitudes[-1][1]

    def _check_dialog_option_requirements(self, option, player) -> bool:
        """Sprawdza czy gracz spełnia wymagania opcji dialogowej."""
        if not hasattr(option, 'requirements'):
            return True
            
        for req_type, req_value in option.requirements.items():
            if req_type == 'level' and player.level < req_value:
                return False
            elif req_type == 'reputation':
                for faction, value in req_value.items():
                    if player.reputation.get(faction, 0) < value:
                        return False
            elif req_type == 'items':
                for item_id, quantity in req_value.items():
                    if not player.inventory.has_item(item_id, quantity):
                        return False
            elif req_type == 'skills':
                for skill, level in req_value.items():
                    if player.get_skill_level(skill) < level:
                        return False
        return True

    def show_main_menu(self):
        """Wyświetla główne menu gry."""
        self.clear_screen()
        self._show_game_logo()
        
        options = [
            ("Nowa Gra", "Rozpocznij nową przygodę"),
            ("Wczytaj Grę", "Kontynuuj poprzednią rozgrywkę"),
            ("Opcje", "Zmień ustawienia gry"),
            ("Twórcy", "Zobacz informacje o twórcach"),
            ("Wyjście", "Zakończ grę")
        ]
        
        for i, (option, desc) in enumerate(options, 1):
            print(f"\n{i}. {self.display_config.colors['primary']}{option}{Style.RESET_ALL}")
            print(f"   {self.display_config.colors['secondary']}{desc}{Style.RESET_ALL}")

    def _show_game_logo(self):
        """Wyświetla logo gry w ASCII art."""
        # Tu możesz dodać swoje logo w ASCII art
        logo = """
        ╔═══════════════════════════════════════╗
        ║             Fantasy RPG               ║
        ╚═══════════════════════════════════════╝
        """
        print(f"{self.display_config.colors['primary']}{logo}{Style.RESET_ALL}")

    def show_notification(self, message: str, notification_type: MessageType,
                        duration: float = 3.0, sound: bool = True):
        """Wyświetla powiadomienie."""
        color = self.message_styles.get(notification_type, '')
        
        # Określ symbol na podstawie typu
        symbols = {
            MessageType.SUCCESS: self.display_config.symbols['checkmark'],
            MessageType.WARNING: '!',
            MessageType.ERROR: self.display_config.symbols['cross'],
            MessageType.ACHIEVEMENT: self.display_config.symbols['star'],
            MessageType.QUEST: '!',
            MessageType.ITEM: '+'
        }
        symbol = symbols.get(notification_type, '')
        
        # Sformatuj powiadomienie
        notification = f"\n{color}{symbol} {message}{Style.RESET_ALL}"
        
        # Wyświetl powiadomienie z animacją
        if self.animation_enabled:
            self._animate_notification(notification, duration)
        else:
            print(notification)
            
        # Odtwórz dźwięk jeśli włączony
        if sound and game_config.get('gui.sound_enabled', True):
            self._play_notification_sound(notification_type)

    def _animate_notification(self, notification: str, duration: float):
        """Animuje pojawienie się i zniknięcie powiadomienia."""
        print(notification, end='', flush=True)
        time.sleep(duration)
        print('\r' + ' ' * len(notification) + '\r', end='', flush=True)

    def _play_notification_sound(self, notification_type: MessageType):
        """Odtwarza dźwięk powiadomienia."""
        # Tu możesz dodać obsługę dźwięków
        pass

    def show_achievement_popup(self, achievement: dict):
        """Wyświetla popup o odblokowaniu osiągnięcia."""
        self.show_notification(
            f"Osiągnięcie odblokowane: {achievement['name']}!",
            MessageType.ACHIEVEMENT,
            duration=5.0
        )
        
        # Szczegóły osiągnięcia
        print(f"\n{self.display_config.colors['gold']}Nowe osiągnięcie!{Style.RESET_ALL}")
        print(f"{achievement['name']}")
        print(f"{self.display_config.colors['secondary']}{achievement['description']}{Style.RESET_ALL}")
        
        # Pokaż nagrody
        if 'rewards' in achievement:
            print("\nNagrody:")
            self._display_rewards(achievement['rewards'])

    def show_loading_screen(self, message: str = "Wczytywanie..."):
        """Wyświetla ekran ładowania."""
        if not self.animation_enabled:
            print(message)
            return
            
        frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        
        for _ in range(20):  # Animacja przez 20 klatek
            for frame in frames:
                print(f'\r{frame} {message}', end='', flush=True)
                time.sleep(0.1)

    def show_options_menu(self, current_settings: dict):
        """Wyświetla menu opcji."""
        self.clear_screen()
        print(f"\n{self.display_config.colors['primary']}=== OPCJE ==={Style.RESET_ALL}")
        
        options = [
            ('Dźwięki', 'sound_enabled', 'bool'),
            ('Muzyka', 'music_enabled', 'bool'),
            ('Animacje', 'animations_enabled', 'bool'),
            ('Kolory', 'colors_enabled', 'bool'),
            ('Głośność dźwięków', 'sound_volume', 'slider'),
            ('Głośność muzyki', 'music_volume', 'slider'),
            ('Tryb pełnoekranowy', 'fullscreen', 'bool'),
            ('Język', 'language', 'selection', ['pl', 'en']),
            ('Trudność', 'difficulty', 'selection', ['easy', 'normal', 'hard'])
        ]
        
        for i, (name, setting, type_, *args) in enumerate(options, 1):
            current_value = current_settings.get(setting)
            
            if type_ == 'bool':
                value_display = ('Włączone' if current_value else 'Wyłączone')
                color = (self.display_config.colors['success'] if current_value 
                        else self.display_config.colors['error'])
            elif type_ == 'slider':
                value_display = self.draw_progress_bar(
                    current_value * 100, 100, width=10, show_percentage=True
                )
                color = self.display_config.colors['primary']
            elif type_ == 'selection':
                value_display = current_value
                color = self.display_config.colors['secondary']
                
            print(f"{i}. {name}: {color}{value_display}{Style.RESET_ALL}")
            
        print("\n0. Powrót")

    def show_help(self):
        """Wyświetla pomoc dotyczącą sterowania i mechanik gry."""
        self.clear_screen()
        print(f"\n{self.display_config.colors['primary']}=== POMOC ==={Style.RESET_ALL}")
        
        sections = {
            'Podstawowe komendy': {
                'rozejrzyj się': 'Pokazuje opis obecnej lokacji',
                'ekwipunek': 'Zarządzaj ekwipunkiem',
                'status': 'Pokaż statystyki postaci',
                'mapa': 'Otwórz mapę świata'
            },
            'Walka': {
                'atakuj [cel]': 'Rozpocznij walkę',
                'użyj [przedmiot]': 'Użyj przedmiotu',
                'umiejętność [nazwa]': 'Użyj umiejętności specjalnej'
            },
            'Interakcje': {
                'porozmawiaj [postać]': 'Rozpocznij dialog',
                'handluj [kupiec]': 'Rozpocznij handel',
                'podnieś [przedmiot]': 'Podnieś przedmiot'
            },
            'Questy': {
                'questy': 'Pokaż aktywne zadania',
                'przyjmij quest': 'Przyjmij nowe zadanie',
                'porzuć quest': 'Porzuć aktywne zadanie'
            }
        }
        
        for section, commands in sections.items():
            print(f"\n{self.display_config.colors['secondary']}{section}:{Style.RESET_ALL}")
            for command, description in commands.items():
                print(f"  {self.display_config.colors['primary']}{command}{Style.RESET_ALL}")
                print(f"    {description}")
                
        print("\nNaciśnij Enter, aby kontynuować...")
        input()

    def show_credits(self):
        """Wyświetla informacje o twórcach."""
        self.clear_screen()
        self._show_game_logo()
        
        credits = [
            ("Twórca", ["John Doe"]),
            ("Programowanie", ["Jane Smith", "Bob Wilson"]),
            ("Grafika", ["Alice Brown"]),
            ("Muzyka", ["Mike Johnson"]),
            ("Podziękowania", ["Wszystkim testerom i społeczności!"])
        ]
        
        for section, names in credits:
            print(f"\n{self.display_config.colors['primary']}{section}:{Style.RESET_ALL}")
            for name in names:
                self.animate_text(f"  {name}", delay=0.1)
                
        print("\nNaciśnij Enter, aby wrócić...")
        input()