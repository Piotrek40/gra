# combat.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import random
from typing import Dict, Optional, Tuple, List
import logging
from config import game_config
from entities import Entity
from player import Player

logger = logging.getLogger(__name__)

class CombatSystem:
    """Główny system walki w grze."""
    
    def __init__(self):
        self.active_combats: Dict[str, Combat] = {}
        self.combat_log: List[Dict] = []
        self.event_manager = None  # Dodać referencję do EventManagera
        
    def initialize(self, event_manager):
        """Inicjalizacja systemu walki."""
        self.event_manager = event_manager
        self.event_manager.register_listener('entity_death', self.handle_entity_death)

    def start_combat(self, player, enemy) -> 'CombatInstance':
        """Rozpoczyna nową walkę."""
        combat_id = f"{player.id}_{enemy.id}_{len(self.combat_history)}"
        combat = CombatInstance(player, enemy, combat_id)
        self.active_combats[combat_id] = combat
        
        # Zapisz w historii
        self.combat_history.append({
            'combat_id': combat_id,
            'player_id': player.id,
            'enemy_id': enemy.id,
            'start_time': combat.start_time,
            'status': 'in_progress'
        })
        
        return combat

    def end_combat(self, combat_id: str, winner=None):
        """Kończy walkę."""
        if combat_id in self.active_combats:
            combat = self.active_combats[combat_id]
            combat.end(winner)
            
            # Aktualizuj historię
            for record in self.combat_history:
                if record['combat_id'] == combat_id:
                    record['end_time'] = combat.end_time
                    record['status'] = 'completed'
                    record['winner'] = winner.id if winner else None
                    record['duration'] = combat.end_time - combat.start_time
                    break
                        
            del self.active_combats[combat_id]

    def update(self, game_time: float):
        """Aktualizuje wszystkie aktywne walki."""
        for combat_id, combat in list(self.active_combats.items()):
            if combat.is_finished():
                self.end_combat(combat_id, combat.get_winner())
            else:
                combat.update(game_time)

    def get_combat_stats(self, entity_id: str) -> dict:
        """Zwraca statystyki walk dla danej jednostki."""
        stats = {
            'total_fights': 0,
            'victories': 0,
            'defeats': 0,
            'total_damage_dealt': 0,
            'total_damage_taken': 0,
            'longest_fight': 0,
            'fastest_victory': float('inf'),
            'most_damage_in_fight': 0
        }
        
        for record in self.combat_history:
            if record['player_id'] == entity_id or record['enemy_id'] == entity_id:
                stats['total_fights'] += 1
                
                if record['status'] == 'completed':
                    if record['winner'] == entity_id:
                        stats['victories'] += 1
                        if record['duration'] < stats['fastest_victory']:
                            stats['fastest_victory'] = record['duration']
                    else:
                        stats['defeats'] += 1
                        
                    if record['duration'] > stats['longest_fight']:
                        stats['longest_fight'] = record['duration']
                        
        return stats

class CombatInstance:
    """Reprezentuje pojedynczą instancję walki."""
    
    def __init__(self, player, enemy, combat_id: str):
        self.combat_id = combat_id
        self.player = player
        self.enemy = enemy
        self.start_time = game_config.get('game_time', 0)
        self.end_time = None
        self.turn = 1
        self.last_action_time = self.start_time
        self.combat_log = []
        self.active_effects = []
        self.ability_cooldowns = {}  # Dodane pole dla cooldownów
        
        # Stan walki
        self.player_status = {
            'stamina': 100,
            'defense_bonus': 0,
            'status_effects': [],
            'combo_counter': 0,
            'dodge_chance': player.stats.dodge_chance,
            'crit_chance': player.stats.critical_chance
        }
        
        self.enemy_status = {
            'defense_bonus': 0,
            'status_effects': [],
            'next_action': None,
            'aggression_level': random.uniform(0.5, 1.5)
        }

    def update(self, game_time: float):
        """Aktualizuje stan walki."""
        if self.is_finished():
            return
            
        # Aktualizacja efektów statusu
        self._update_status_effects(game_time)
        
        # Regeneracja zasobów
        self._update_resources()
        
        # Aktualizuj cooldowny
        self._update_cooldowns(game_time)
        
        # Sprawdź czy czas na następną turę
        if game_time - self.last_action_time >= game_config.get('combat.turn_duration', 1.0):
            self._process_turn()

    def _update_cooldowns(self, game_time: float):
        """Aktualizuje cooldowny zdolności."""
        for ability_id in list(self.ability_cooldowns.keys()):
            if game_time >= self.ability_cooldowns[ability_id]:
                del self.ability_cooldowns[ability_id]

    def _try_dodge(self) -> bool:
        """Sprawdza czy udało się uniknąć ataku."""
        dodge_chance = self.current_stats.dodge_chance
        if 'dodge_bonus' in self.active_effects:
            dodge_chance += self.active_effects['dodge_bonus']
        return random.random() < dodge_chance

    def _initialize_combat(self):
        """Inicjalizuje walkę."""
        # Ustaw stany walki
        self.player.in_combat = True
        self.enemy.in_combat = True
        
        # Aplikuj efekty przedwalką
        self._apply_pre_combat_effects()
        
        # Zapisz log rozpoczęcia
        self.add_combat_log(
            f"Rozpoczyna się walka między {self.player.name} a {self.enemy.name}!",
            "system"
        )
        
        # Opisz przeciwnika
        self.add_combat_log(self.enemy.description, "info")

    def _apply_pre_combat_effects(self):
        """Aplikuje efekty przed rozpoczęciem walki."""
        # Efekty ekwipunku
        if hasattr(self.player, 'equipment'):
            for item in self.player.equipment.values():
                if item and 'combat_start_effect' in item.properties:
                    self._apply_equipment_effect(item.properties['combat_start_effect'])

        # Efekty umiejętności
        if hasattr(self.player, 'get_active_effects'):
            for effect in self.player.get_active_effects():
                if effect.trigger == 'combat_start':
                    self._apply_status_effect(effect)

    

    def _process_turn(self):
        """Przetwarza pojedynczą turę walki."""
        self.combat_stats['rounds'] += 1
        
        # Akcja przeciwnika
        enemy_action = self.enemy.choose_action(self)
        self._execute_enemy_action(enemy_action)
        
        # Sprawdź warunki końca walki
        if self._check_combat_end():
            return
            
        self.turn += 1
        self.last_action_time = game_config.get('game_time', 0)

    def handle_player_action(self, action_type: str, **kwargs) -> Tuple[bool, str]:
        """Obsługuje akcję gracza."""
        if action_type == "attack":
            return self._handle_player_attack(**kwargs)
        elif action_type == "defend":
            return self._handle_player_defend()
        elif action_type == "use_ability":
            return self._handle_player_ability(kwargs.get('ability_name'))
        elif action_type == "use_item":
            return self._handle_use_item(kwargs.get('item_id'))
        elif action_type == "escape":
            return self._handle_escape_attempt()
        else:
            return False, "Nieznana akcja!"

    def _handle_player_attack(self, **kwargs) -> Tuple[bool, str]:
        """Obsługuje podstawowy atak gracza."""
        # Oblicz obrażenia bazowe
        base_damage = self.player.stats.strength
        if self.player.inventory and self.player.inventory.equipped.get('weapon'):
            weapon = self.player.inventory.equipped['weapon']
            base_damage += weapon.properties.get('damage', 0)
            
        # Sprawdź trafienie krytyczne
        is_crit = random.random() < self.player_status['crit_chance']
        if is_crit:
            base_damage *= 2
            self.combat_stats['critical_hits'] += 1
            self.add_combat_log("Krytyczne trafienie!", "success")
            
        # Oblicz końcowe obrażenia
        final_damage = max(1, base_damage - (self.enemy.stats.defense + self.enemy_status['defense_bonus']))
        
        # Zadaj obrażenia
        self.enemy.stats.health -= final_damage
        self.combat_stats['player_damage_dealt'] += final_damage
        
        # Aktualizuj combo
        self.player_status['combo_counter'] += 1
        if self.player_status['combo_counter'] >= 3:
            final_damage *= 1.2
            self.add_combat_log("Bonus za combo!", "success")
            
        self.add_combat_log(
            f"Zadajesz {final_damage:.1f} obrażeń{' (Krytyczne!)' if is_crit else ''}",
            "success"
        )
        
        return True, "Atak wykonany!"

    def _handle_player_defend(self) -> Tuple[bool, str]:
        """Obsługuje przyjęcie postawy obronnej."""
        defense_bonus = 5 + (self.player.get_skill_level('defense') * 1 
                           if hasattr(self.player, 'get_skill_level') else 0)
                           
        self.player_status['defense_bonus'] = defense_bonus
        self.player_status['stamina'] = min(100, self.player_status['stamina'] + 20)
        
        self.add_combat_log(
            f"Przyjmujesz postawę obronną (+{defense_bonus} do obrony)",
            "info"
        )
        return True, "Przyjęto postawę obronną!"

    def is_finished(self) -> bool:
        """Sprawdza czy walka się zakończyła."""
        return (not self.player.is_alive or not self.enemy.is_alive or 
                self.end_time is not None)

    def get_winner(self):
        """Zwraca zwycięzcę walki."""
        if not self.is_finished():
            return None
            
        if not self.enemy.is_alive:
            return self.player
        elif not self.player.is_alive:
            return self.enemy
            
        return None

    def end(self, winner=None):
        """Kończy walkę."""
        self.end_time = game_config.get('game_time', 0)
        
        # Resetuj stany walki
        self.player.in_combat = False
        self.enemy.in_combat = False
        
        # Usuń efekty walki
        self._clear_combat_effects()
        
        # Zapisz końcowy log
        if winner:
            self.add_combat_log(
                f"Walka zakończona! Zwycięzca: {winner.name}",
                "system"
            )
        else:
            self.add_combat_log("Walka przerwana!", "system")

    def add_combat_log(self, message: str, message_type: str = "info"):
        """Dodaje wpis do dziennika walki."""
        self.combat_log.append({
            'message': message,
            'type': message_type,
            'turn': self.turn,
            'time': game_config.get('game_time', 0)
        })

    def get_combat_log(self, last_n: Optional[int] = None) -> List[dict]:
        """Zwraca log walki."""
        if last_n is None:
            return self.combat_log
        return self.combat_log[-last_n:]

    def get_state(self) -> dict:
        """Zwraca obecny stan walki."""
        return {
            'combat_id': self.combat_id,
            'turn': self.turn,
            'player_status': self.player_status,
            'enemy_status': self.enemy_status,
            'combat_stats': self.combat_stats,
            'active_effects': self.active_effects,
            'is_finished': self.is_finished(),
            'winner': self.get_winner().id if self.get_winner() else None
        }

    # Dodanie systemu zapisywania stanu walki
    def save_combat_state(self) -> dict:
        return {
            'participants': [p.id for p in self.participants],
            'current_turn': self.current_turn,
            'combat_log': self.combat_log
        }


class CombatManager:
    def __init__(self, player, enemy, interface):
        self.player = player
        self.enemy = enemy
        self.interface = interface
        self.turn = 1
        self.player_stamina = 100
        self.abilities_cooldowns = {}
        self.combat_log = []
    
    def log_combat_event(self, message, message_type="info"):
        """Dodaje wpis do dziennika walki."""
        self.combat_log.append((message, message_type))
        self.interface.show_message(message, message_type)
    
    def calculate_damage(self, attacker, defender, is_player=True, ability_name: Optional[str] = None):
        """Oblicza obrażenia z efektami specjalnymi."""
        base_damage = max(0, attacker.strength - defender.defense)
        
        if is_player and ability_name:
            skill_level = self.player.get_skill_level("walka_mieczem")
            if skill_level > 0:
                base_damage += skill_level * 2
            
            if ability_name == "thrust" and skill_level >= 3:
                base_damage *= 2
                self.log_combat_event("Wykonujesz potężne pchnięcie!", "success")
            elif ability_name == "whirlwind" and skill_level >= 5:
                base_damage *= 1.5
                self.log_combat_event("Wykonujesz wirujący cios!", "success")

        # Szansa na unik
        dodge_chance = 0.10 if is_player else 0.05
        if random.random() < dodge_chance:
            self.log_combat_event(
                f"{'Unikasz ataku!' if is_player else f'{self.enemy.name} unika twojego ataku!'}", 
                "success" if is_player else "warning"
            )
            return 0, "UNIK!"
        
        # Szansa na trafienie krytyczne
        crit_chance = 0.15 if is_player else 0.05
        if random.random() < crit_chance:
            base_damage *= 2
            self.log_combat_event(
                f"{'Trafiasz krytycznie!' if is_player else f'{self.enemy.name} trafia cię krytycznie!'}",
                "success" if is_player else "error"
            )
            return base_damage, "KRYTYCZNE!"
        
        return base_damage, ""

    def use_ability(self, ability_name: str) -> Tuple[bool, str]:
        """Używa specjalnej umiejętności."""
        skill_level = self.player.get_skill_level("walka_mieczem")
        
        abilities = {
            "thrust": {
                "name": "Pchnięcie",
                "min_level": 3,
                "stamina_cost": 30,
                "cooldown": 3,
                "description": "Potężne pchnięcie zadające podwójne obrażenia"
            },
            "whirlwind": {
                "name": "Wirujący Cios",
                "min_level": 5,
                "stamina_cost": 50,
                "cooldown": 5,
                "description": "Obszarowy atak zadający 150% obrażeń"
            }
        }

        if ability_name not in abilities:
            return False, "Nieznana umiejętność!"

        ability = abilities[ability_name]
        
        if skill_level < ability["min_level"]:
            return False, f"Wymagany poziom umiejętności walki mieczem: {ability['min_level']}"
        
        if self.player_stamina < ability["stamina_cost"]:
            return False, f"Niewystarczająca stamina! (Potrzeba: {ability['stamina_cost']})"
        
        if ability_name in self.abilities_cooldowns and self.abilities_cooldowns[ability_name] > 0:
            return False, f"Umiejętność odnowi się za {self.abilities_cooldowns[ability_name]} tur!"

        self.player_stamina -= ability["stamina_cost"]
        self.abilities_cooldowns[ability_name] = ability["cooldown"]
        
        return True, f"Używasz {ability['name']}!"

    def show_combat_status(self):
        """Wyświetla status walki."""
        self.interface.clear_screen()
        self.interface.show_title(f"Walka - Tura {self.turn}", Fore.RED)
        
        # Status gracza
        print(f"\n{Fore.CYAN}=== Twój status ==={Style.RESET_ALL}")
        self.interface.draw_bar(
            self.player.health / self.player.max_health * 100,
            f"HP: {self.player.health}/{self.player.max_health}"
        )
        self.interface.draw_bar(
            self.player_stamina,
            f"Stamina: {self.player_stamina}/100",
            Fore.BLUE
        )

        # Status przeciwnika
        print(f"\n{Fore.RED}=== {self.enemy.name} ==={Style.RESET_ALL}")
        self.interface.draw_bar(
            self.enemy.health / self.enemy.max_health * 100,
            f"HP: {self.enemy.health}",
            Fore.RED
        )

        # Dziennik walki
        if self.combat_log:
            print(f"\n{Fore.YELLOW}=== Przebieg walki ==={Style.RESET_ALL}")
            for message, message_type in self.combat_log[-3:]:  # Pokazuj ostatnie 3 wydarzenia
                self.interface.show_message(message, message_type)

    def show_available_actions(self):
        """Wyświetla dostępne akcje w walce."""
        print(f"\n{Fore.GREEN}Dostępne akcje:{Style.RESET_ALL}")
        print("1. Atak podstawowy")
        print("2. Użyj przedmiotu")
        print("3. Spróbuj uciec")

        skill_level = self.player.get_skill_level("walka_mieczem")
        if skill_level >= 3:
            can_use_thrust = "thrust" not in self.abilities_cooldowns or self.abilities_cooldowns["thrust"] <= 0
            status = "" if can_use_thrust else f"(Odnowienie za {self.abilities_cooldowns['thrust']} tur)"
            print(f"4. Pchnięcie (30 staminy) {status}")

        if skill_level >= 5:
            can_use_whirlwind = "whirlwind" not in self.abilities_cooldowns or self.abilities_cooldowns["whirlwind"] <= 0
            status = "" if can_use_whirlwind else f"(Odnowienie za {self.abilities_cooldowns['whirlwind']} tur)"
            print(f"5. Wirujący Cios (50 staminy) {status}")

    def handle_player_turn(self):
        """Obsługuje turę gracza."""
        self.show_combat_status()
        self.show_available_actions()
        
        action = self.interface.show_prompt("Wybierz akcję")
        
        if action == "1":  # Atak podstawowy
            damage, special = self.calculate_damage(self.player, self.enemy)
            self.enemy.health -= damage
            message = f"Zadajesz {damage} obrażeń!"
            if special:
                message = f"{special}! {message}"
            self.log_combat_event(message, "success")
            
        elif action == "2":  # Użyj przedmiotu
            self.show_usable_items()
            return False
            
        elif action == "3":  # Ucieczka
            escape_chance = 0.3 + (self.player.level * 0.1)
            if random.random() < escape_chance:
                self.log_combat_event("Udało ci się uciec!", "success")
                return "escaped"
            self.log_combat_event("Nie udało ci się uciec!", "warning")
            
        elif action == "4" and self.player.get_skill_level("walka_mieczem") >= 3:  # Pchnięcie
            success, message = self.use_ability("thrust")
            if success:
                damage, _ = self.calculate_damage(self.player, self.enemy, ability_name="thrust")
                self.enemy.health -= damage
                self.log_combat_event(f"{message} Zadajesz {damage} obrażeń!", "success")
            else:
                self.log_combat_event(message, "error")
                return False
                
        elif action == "5" and self.player.get_skill_level("walka_mieczem") >= 5:  # Wirujący Cios
            success, message = self.use_ability("whirlwind")
            if success:
                damage, _ = self.calculate_damage(self.player, self.enemy, ability_name="whirlwind")
                self.enemy.health -= damage
                self.log_combat_event(f"{message} Zadajesz {damage} obrażeń!", "success")
            else:
                self.log_combat_event(message, "error")
                return False
        
        if self.enemy.health <= 0:
            return "victory"
        return None

    def handle_enemy_turn(self):
        """Obsługuje turę przeciwnika."""
        damage, special = self.calculate_damage(self.enemy, self.player, is_player=False)
        self.player.health -= damage
        
        message = f"{self.enemy.name} zadaje ci {damage} obrażeń!"
        if special:
            message = f"{special}! {message}"
        self.log_combat_event(message, "warning")
        
        if self.player.health <= 0:
            return "defeat"
        return None

    def show_usable_items(self):
        """Wyświetla i obsługuje użycie przedmiotów w walce."""
        usable_items = {}
        print(f"\n{Fore.CYAN}Przedmioty możliwe do użycia:{Style.RESET_ALL}")
        
        for item_id, quantity in self.player.inventory.items.items():
            item = self.player.inventory.item_manager.get_item(item_id)
            if item.type == "konsumpcyjny" and "healing" in item.properties:
                usable_items[item.name.lower()] = item_id
                print(f"- {item.name} x{quantity}")
        
        if not usable_items:
            self.log_combat_event("Nie masz przedmiotów, których możesz użyć!", "warning")
            return False
        
        item_name = input("\nKtórego przedmiotu chcesz użyć? (wpisz 'nic' aby wrócić): ").lower()
        if item_name == "nic":
            return False
            
        if item_name in usable_items:
            success, message = self.player.inventory.use_item(usable_items[item_name], self.player)
            self.log_combat_event(message, "success" if success else "error")
        else:
            self.log_combat_event("Nie ma takiego przedmiotu!", "error")
        return False

    def update_combat_state(self):
        """Aktualizuje stan walki."""
        # Regeneracja staminy
        self.player_stamina = min(100, self.player_stamina + 10)
        
        # Aktualizacja cooldownów
        for ability in list(self.abilities_cooldowns.keys()):
            if self.abilities_cooldowns[ability] > 0:
                self.abilities_cooldowns[ability] -= 1
            if self.abilities_cooldowns[ability] <= 0:
                del self.abilities_cooldowns[ability]

    def start_combat(self):
        """Rozpoczyna i prowadzi walkę."""
        self.log_combat_event(f"Rozpoczyna się walka z {self.enemy.name}!", "system")
        self.log_combat_event(self.enemy.description, "info")
        combat_dialog = CombatDialog(self.interface.root, self)
        combat_dialog.start()
        
        while True:
            # Tura gracza
            result = self.handle_player_turn()
            if result:
                return result
                
            # Tura przeciwnika
            result = self.handle_enemy_turn()
            if result:
                return result
                
            # Aktualizacja stanu walki
            self.update_combat_state()
            self.turn += 1

class CombatDialog(tk.Toplevel):
    """Interfejs walki w trybie GUI."""
    def __init__(self, parent, combat_manager):
        super().__init__(parent)
        self.title("Walka")
        self.combat_manager = combat_manager
        self.create_widgets()
        self.update_combat_status()

    def create_widgets(self):
        """Tworzy widgety interfejsu walki."""
        # Ramka statusu gracza
        self.player_frame = ttk.LabelFrame(self, text="Twój status")
        self.player_frame.pack(fill=tk.X, padx=10, pady=5)

        self.player_hp = ttk.Progressbar(self.player_frame, maximum=self.combat_manager.player.max_health)
        self.player_hp.pack(fill=tk.X, padx=5, pady=5)
        self.player_stamina = ttk.Progressbar(self.player_frame, maximum=100)
        self.player_stamina.pack(fill=tk.X, padx=5, pady=5)

        # Ramka statusu przeciwnika
        self.enemy_frame = ttk.LabelFrame(self, text=f"Przeciwnik: {self.combat_manager.enemy.name}")
        self.enemy_frame.pack(fill=tk.X, padx=10, pady=5)

        self.enemy_hp = ttk.Progressbar(self.enemy_frame, maximum=self.combat_manager.enemy.max_health)
        self.enemy_hp.pack(fill=tk.X, padx=5, pady=5)

        # Ramka akcji
        self.actions_frame = ttk.Frame(self)
        self.actions_frame.pack(fill=tk.X, padx=10, pady=5)

        self.attack_button = ttk.Button(self.actions_frame, text="Atakuj", command=self.player_attack)
        self.attack_button.pack(side=tk.LEFT, padx=5)

        self.ability_button = ttk.Button(self.actions_frame, text="Użyj umiejętności", command=self.use_ability)
        self.ability_button.pack(side=tk.LEFT, padx=5)

        self.item_button = ttk.Button(self.actions_frame, text="Użyj przedmiotu", command=self.use_item)
        self.item_button.pack(side=tk.LEFT, padx=5)

        self.run_button = ttk.Button(self.actions_frame, text="Uciekaj", command=self.attempt_escape)
        self.run_button.pack(side=tk.LEFT, padx=5)

        # Dziennik walki
        self.log = scrolledtext.ScrolledText(self, state='disabled', height=10)
        self.log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def update_combat_status(self):
        """Aktualizuje status gracza i przeciwnika."""
        self.player_hp['value'] = self.combat_manager.player.health
        self.player_hp['maximum'] = self.combat_manager.player.max_health
        self.player_stamina['value'] = self.combat_manager.player_stamina

        self.enemy_hp['value'] = self.combat_manager.enemy.health
        self.enemy_hp['maximum'] = self.combat_manager.enemy.max_health

    def log_event(self, message):
        """Dodaje wpis do dziennika walki."""
        self.log.config(state='normal')
        self.log.insert(tk.END, message + '\n')
        self.log.config(state='disabled')
        self.log.see(tk.END)

    def player_attack(self):
        """Obsługuje atak gracza."""
        self.combat_manager.player_attack()
        self.update_combat_status()
        self.check_combat_end()
        self.enemy_turn()

    def use_ability(self):
        """Pozwala graczowi użyć umiejętności."""
        abilities = ["Pchnięcie", "Wirujący Cios"]
        ability_window = AbilitySelectionDialog(self, abilities)
        self.wait_window(ability_window)
        ability_name = ability_window.selected_ability

        if ability_name:
            success, message = self.combat_manager.use_ability(ability_name.lower())
            self.log_event(message)
            if success:
                damage, special = self.combat_manager.calculate_damage(
                    self.combat_manager.player,
                    self.combat_manager.enemy,
                    ability_name=ability_name.lower()
                )
                self.combat_manager.enemy.health -= damage
                self.log_event(f"Zadajesz {damage} obrażeń! {special}")
                self.update_combat_status()
                self.check_combat_end()
                self.enemy_turn()

    def use_item(self):
        """Pozwala graczowi użyć przedmiotu."""
        # Implementuj wybór przedmiotu do użycia
        pass  # Możesz zaimplementować podobnie jak AbilitySelectionDialog

    def attempt_escape(self):
        """Próbuje ucieczki z walki."""
        if self.combat_manager.attempt_escape():
            self.log_event("Udało ci się uciec!")
            self.destroy()
        else:
            self.log_event("Nie udało ci się uciec!")
            self.enemy_turn()

    def enemy_turn(self):
        """Tura przeciwnika."""
        self.combat_manager.enemy_attack()
        self.update_combat_status()
        self.check_combat_end()

    def check_combat_end(self):
        """Sprawdza, czy walka się zakończyła."""
        if self.combat_manager.player.health <= 0:
            self.log_event("Zostałeś pokonany!")
            self.destroy()
        elif self.combat_manager.enemy.health <= 0:
            self.log_event(f"Pokonałeś {self.combat_manager.enemy.name}!")
            self.destroy()

    def start(self):
        """Rozpoczyna pętlę zdarzeń okna walki."""
        self.mainloop()

class AbilitySelectionDialog(tk.Toplevel):
    """Okno wyboru umiejętności."""
    def __init__(self, parent, abilities):
        super().__init__(parent)
        self.title("Wybierz umiejętność")
        self.selected_ability = None
        self.create_widgets(abilities)

    def create_widgets(self, abilities):
        """Tworzy widgety wyboru umiejętności."""
        label = ttk.Label(self, text="Wybierz umiejętność:")
        label.pack(padx=10, pady=5)

        self.ability_var = tk.StringVar()
        for ability in abilities:
            rb = ttk.Radiobutton(self, text=ability, value=ability, variable=self.ability_var)
            rb.pack(anchor=tk.W, padx=10)

        button = ttk.Button(self, text="OK", command=self.confirm_selection)
        button.pack(pady=10)

    def confirm_selection(self):
        """Potwierdza wybór umiejętności."""
        self.selected_ability = self.ability_var.get()
        self.destroy()

def start_combat_gui(interface, player, enemy):
    """Funkcja uruchamiająca walkę w trybie GUI."""
    combat_manager = CombatManager(player, enemy, interface)
    combat_manager.start_combat_gui()