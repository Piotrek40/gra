# entities.py
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import random
import logging
import time
import math
from config import game_config
from exceptions import (
    GameError, RequirementsNotMetError, 
    InsufficientFundsError, InvalidSkillError
)

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Reprezentacja pozycji w świecie gry."""
    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: 'Position') -> float:
        """Oblicza odległość do innej pozycji."""
        return math.sqrt(
            (self.x - other.x) ** 2 + 
            (self.y - other.y) ** 2 + 
            (self.z - other.z) ** 2
        )

@dataclass
class Stats:
    """Podstawowe statystyki jednostki."""
    health: int = 100
    max_health: int = 100
    stamina: int = 100
    max_stamina: int = 100
    mana: int = 0
    max_mana: int = 0
    strength: int = 10
    defense: int = 5
    agility: int = 10
    intelligence: int = 10
    critical_chance: float = 0.05
    dodge_chance: float = 0.05
    
    def modify_stat(self, stat_name: str, value: float, is_percentage: bool = False):
        """Modyfikuje wartość statystyki."""
        if hasattr(self, stat_name):
            current_value = getattr(self, stat_name)
            if is_percentage:
                new_value = current_value * (1 + value)
            else:
                new_value = current_value + value
                
            # Upewnij się, że wartości nie spadną poniżej 0
            if stat_name.startswith('max_'):
                new_value = max(1, new_value)
            else:
                max_stat = getattr(self, f"max_{stat_name}", float('inf'))
                new_value = min(max(0, new_value), max_stat)
                
            setattr(self, stat_name, new_value)

@dataclass
class StatusEffect:
    """Efekt statusu wpływający na jednostkę."""
    name: str
    type: str  # buff, debuff, dot, hot
    stat_modifiers: Dict[str, float]
    duration: int
    tick_interval: int = 1
    last_tick: float = 0.0
    description: str = ""
    is_permanent: bool = False
    can_stack: bool = False
    icon: str = ""
    
    def apply(self, target: 'Entity'):
        """Aplikuje efekt na cel."""
        for stat, modifier in self.stat_modifiers.items():
            target.stats.modify_stat(stat, modifier, is_percentage=True)

    def remove(self, target: 'Entity'):
        """Usuwa efekt z celu."""
        for stat, modifier in self.stat_modifiers.items():
            target.stats.modify_stat(stat, -modifier, is_percentage=True)

class CombatStats:
    """Statystyki związane z walką."""
    def __init__(self):
        self.damage_dealt: float = 0
        self.damage_taken: float = 0
        self.healing_done: float = 0
        self.critical_hits: int = 0
        self.dodges: int = 0
        self.kills: int = 0
        self.deaths: int = 0
        self.longest_combat: float = 0
        self.highest_damage: float = 0
        self.highest_combo: int = 0
        
    def update_damage_stats(self, damage: float, is_critical: bool = False):
        """Aktualizuje statystyki obrażeń."""
        self.damage_dealt += damage
        if damage > self.highest_damage:
            self.highest_damage = damage
        if is_critical:
            self.critical_hits += 1

class Entity:
    """Bazowa klasa dla wszystkich bytów w grze."""
    def __init__(self, entity_id: str, data: dict):
        if not isinstance(entity_id, str) or not isinstance(data, dict):
            raise ValueError("Nieprawidłowe argumenty konstruktora Entity")
            
        self.id = entity_id
        self.name = data.get('name', '')
        self.type = data.get('type', '')
        self.stats = data.get('stats', {})
        self.tags = data.get('tags', [])  # Dodać brakujący atrybut

    def get_loot(self):
        """Metoda bazowa dla zwracania łupu."""
        return []

class Entity(ABC):
    """Bazowa klasa dla wszystkich jednostek w grze."""
    
    def __init__(self, entity_id: str, data: dict):
        required_fields = ['name', 'type']
        if not all(field in data for field in required_fields):
            raise ValueError(f"Brakujące wymagane pola: {required_fields}")
        self.id = entity_id
        self.name = data.get('name', 'Unknown Entity')
        self.description = data.get('description', '')
        self.level = data.get('level', 1)
        
        # Podstawowe statystyki
        stats_data = data.get('stats', {})
        self.stats = Stats(**stats_data)
        
        # Pozycja w świecie
        position_data = data.get('position', {'x': 0, 'y': 0, 'z': 0})
        self.position = Position(**position_data)
        
        # Status i efekty
        self.status_effects: List[StatusEffect] = []
        self.is_alive = True
        self.is_stunned = False
        self.is_invisible = False
        
        # Atrybuty walki
        self.in_combat = False
        self.last_attack_time = 0.0
        self.attack_cooldown = data.get('attack_cooldown', 1.0)
        self.combat_stats = CombatStats()
        
        # Ekwipunek i zasoby
        self.inventory = None  # Będzie zainicjalizowane przez initialize_inventory
        self.gold = data.get('gold', 0)
        
        # Umiejętności i zdolności
        self.abilities = {}
        self.resistances = data.get('resistances', {})
        self.skill_bonuses = {}
        self._load_abilities(data.get('abilities', {}))
        
        # Brak inicjalizacji podstawowych systemów
        self.status_effects = []
        self.combat_stats = CombatStats()
        self._cooldowns = {}

    # Kontynuacja klasy Entity

    def initialize_inventory(self, item_manager):
        """Inicjalizuje ekwipunek jednostki."""
        from inventory import Inventory  # Import na poziomie metody aby uniknąć circular import
        self.inventory = Inventory()
        self.inventory.set_item_manager(item_manager)

    def _load_abilities(self, abilities_data: dict):
        """Ładuje zdolności jednostki."""
        for ability_id, ability_data in abilities_data.items():
            self.abilities[ability_id] = {
                'name': ability_data['name'],
                'damage': ability_data.get('damage', 0),
                'cooldown': ability_data.get('cooldown', 0),
                'cost': ability_data.get('cost', 0),
                'effects': ability_data.get('effects', []),
                'requirements': ability_data.get('requirements', {}),
                'range': ability_data.get('range', 1.0),
                'area_of_effect': ability_data.get('area_of_effect', 0),
                'cast_time': ability_data.get('cast_time', 0),
                'description': ability_data.get('description', '')
            }

    @property
    def current_stats(self) -> Stats:
        """Zwraca aktualne statystyki z uwzględnieniem efektów statusu."""
        modified_stats = Stats(
            health=self.stats.health,
            max_health=self.stats.max_health,
            stamina=self.stats.stamina,
            max_stamina=self.stats.max_stamina,
            mana=self.stats.mana,
            max_mana=self.stats.max_mana,
            strength=self.stats.strength,
            defense=self.stats.defense,
            agility=self.stats.agility,
            intelligence=self.stats.intelligence,
            critical_chance=self.stats.critical_chance,
            dodge_chance=self.stats.dodge_chance
        )
        
        # Aplikowanie modyfikatorów z efektów statusu
        for effect in self.status_effects:
            for stat, modifier in effect.stat_modifiers.items():
                current_value = getattr(modified_stats, stat, 0)
                modified_value = current_value * (1 + modifier)
                setattr(modified_stats, stat, modified_value)
        
        # Aplikowanie modyfikatorów z ekwipunku
        if self.inventory:
            equipment_modifiers = self.inventory.get_equipment_modifiers()
            for stat, modifier in equipment_modifiers.items():
                if hasattr(modified_stats, stat):
                    current_value = getattr(modified_stats, stat)
                    modified_value = current_value + modifier
                    setattr(modified_stats, stat, modified_value)
        
        return modified_stats

    def update(self, game_time: float):
        """Aktualizuje stan jednostki."""
        # Aktualizacja efektów statusu
        self._update_status_effects(game_time)
        
        # Regeneracja zasobów
        self._update_resources()
        
        # Sprawdzenie stanu życia
        if self.stats.health <= 0 and self.is_alive:
            self.die()
        
        # Aktualizacja cooldownów
        self._update_cooldowns(game_time)
        
        # Aktualizacja stanu walki
        if self.in_combat:
            self.update_combat(game_time)

    def update_combat(self, game_time: float) -> bool:
        """Aktualizuje stan jednostki w walce."""
        # Aktualizacja cooldownów
        if self.last_attack_time + self.attack_cooldown > game_time:
            return False
            
        self.last_attack_time = game_time
        return True

    def _update_status_effects(self, game_time: float):
        """Aktualizuje efekty statusu."""
        active_effects = []
        for effect in self.status_effects:
            if effect.is_permanent or effect.duration > 0:
                if not effect.is_permanent:
                    effect.duration -= 1
                
                if game_time - effect.last_tick >= effect.tick_interval:
                    self._apply_effect_tick(effect)
                    effect.last_tick = game_time
                    
                active_effects.append(effect)
            else:
                effect.remove(self)
                
        self.status_effects = active_effects

    def _update_resources(self):
        """Aktualizuje zasoby jednostki (stamina, mana, itp.)."""
        stats = self.stats
        regen_modifiers = self.get_regeneration_modifiers()
        
        # Regeneracja staminy
        if stats.stamina < stats.max_stamina:
            regen_amount = 5 * regen_modifiers.get('stamina', 1.0)
            stats.stamina = min(stats.max_stamina, stats.stamina + regen_amount)
            
        # Regeneracja many
        if stats.mana < stats.max_mana:
            regen_amount = 2 * regen_modifiers.get('mana', 1.0)
            stats.mana = min(stats.max_mana, stats.mana + regen_amount)

    def get_regeneration_modifiers(self) -> Dict[str, float]:
        """Zwraca modyfikatory regeneracji zasobów."""
        modifiers = {
            'health': 1.0,
            'stamina': 1.0,
            'mana': 1.0
        }
        
        # Modyfikatory z efektów statusu
        for effect in self.status_effects:
            if 'regeneration' in effect.stat_modifiers:
                resource = effect.stat_modifiers['regeneration']['resource']
                value = effect.stat_modifiers['regeneration']['value']
                modifiers[resource] *= (1 + value)
                
        # Modyfikatory z ekwipunku
        if self.inventory:
            equipment_regen = self.inventory.get_regeneration_modifiers()
            for resource, value in equipment_regen.items():
                modifiers[resource] *= (1 + value)
                
        return modifiers

    def _apply_effect_tick(self, effect: StatusEffect):
        """Aplikuje pojedynczy tick efektu statusu."""
        if effect.type == 'dot':  # Damage over time
            damage = sum(effect.stat_modifiers.values())
            self.take_damage(damage, 'magical')
        elif effect.type == 'hot':  # Healing over time
            healing = sum(effect.stat_modifiers.values())
            self.heal(healing)
        elif effect.type == 'resource_regen':  # Regeneracja zasobów
            for resource, value in effect.stat_modifiers.items():
                if hasattr(self.stats, resource):
                    current = getattr(self.stats, resource)
                    max_value = getattr(self.stats, f'max_{resource}')
                    new_value = min(max_value, current + value)
                    setattr(self.stats, resource, new_value)

    def _remove_effect(self, effect: StatusEffect):
        """Usuwa efekt statusu."""
        try:
            effect.remove(self)
            self.status_effects.remove(effect)
        except ValueError:
            pass

    def add_status_effect(self, effect: StatusEffect):
        """Dodaje efekt statusu."""
        # Sprawdź czy podobny efekt już istnieje
        for existing_effect in self.status_effects:
            if existing_effect.name == effect.name:
                if not effect.can_stack:
                    # Odśwież czas trwania jeśli nowy efekt jest silniejszy
                    if sum(effect.stat_modifiers.values()) > sum(existing_effect.stat_modifiers.values()):
                        existing_effect.remove(self)
                        self.status_effects.remove(existing_effect)
                        effect.apply(self)
                        self.status_effects.append(effect)
                    else:
                        existing_effect.duration = max(existing_effect.duration, effect.duration)
                    return
                
        effect.apply(self)
        self.status_effects.append(effect)
        
    # Kontynuacja klasy Entity
    
    def take_damage(self, damage: float, damage_type: str = 'physical') -> Tuple[float, bool, bool]:
        """Przyjmuje obrażenia z uwzględnieniem odporności.
        
        Returns:
            Tuple[float, bool, bool]: (otrzymane_obrażenia, czy_unik, czy_krytyczne)
        """
        if not self.is_alive:
            return 0, False, False

        # Sprawdź unik
        if self._try_dodge():
            self.combat_stats.dodges += 1
            return 0, True, False

        # Oblicz rzeczywiste obrażenia
        actual_damage = self._calculate_damage(damage, damage_type)
        
        # Aplikuj obrażenia
        self.stats.health = max(0, self.stats.health - actual_damage)
        self.combat_stats.damage_taken += actual_damage
        
        # Sprawdź stan życia
        if self.stats.health <= 0:
            self.die()
            
        logger.debug(
            f"{self.name} otrzymał {actual_damage:.1f} obrażeń typu {damage_type} "
            f"(Pozostałe HP: {self.stats.health:.1f}/{self.stats.max_health})"
        )
        
        return actual_damage, False, False

    def _try_dodge(self) -> bool:
        """Próba uniku ataku."""
        dodge_chance = self.current_stats.dodge_chance
        
        # Modyfikatory z efektów statusu
        for effect in self.status_effects:
            if 'dodge_bonus' in effect.stat_modifiers:
                dodge_chance += effect.stat_modifiers['dodge_bonus']
        
        # Nie można mieć więcej niż 75% szansy na unik
        dodge_chance = min(0.75, dodge_chance)
        
        return random.random() < dodge_chance

    def _calculate_damage(self, base_damage: float, damage_type: str) -> float:
        """Oblicza rzeczywiste obrażenia po uwzględnieniu wszystkich modyfikatorów."""
        # Podstawowa redukcja obrażeń z odporności
        resistance = self.resistances.get(damage_type, 0)
        damage = base_damage * (1 - resistance)
        
        # Modyfikatory z efektów statusu
        for effect in self.status_effects:
            if 'damage_taken_modifier' in effect.stat_modifiers:
                damage *= (1 + effect.stat_modifiers['damage_taken_modifier'])
        
        # Uwzględnij obronę
        defense_reduction = self.current_stats.defense / (self.current_stats.defense + 100)
        damage *= (1 - defense_reduction)
        
        # Zaokrąglij do jednego miejsca po przecinku
        return round(max(0, damage), 1)

    def deal_damage(self, target: 'Entity', base_damage: float, 
                   damage_type: str = 'physical') -> Tuple[float, bool, bool]:
        """Zadaje obrażenia celowi.
        
        Returns:
            Tuple[float, bool, bool]: (zadane_obrażenia, czy_unik, czy_krytyczne)
        """
        if not target.is_alive or not self.is_alive:
            return 0, False, False
            
        # Sprawdź czy atak jest krytyczny
        is_critical = self._is_critical_hit()
        if is_critical:
            base_damage *= self._get_critical_multiplier()
            self.combat_stats.critical_hits += 1
            
        # Aplikuj modyfikatory obrażeń atakującego
        damage = self._modify_outgoing_damage(base_damage, damage_type)
        
        # Zadaj obrażenia celowi
        actual_damage, was_dodged, _ = target.take_damage(damage, damage_type)
        
        # Aktualizuj statystyki walki
        self.combat_stats.update_damage_stats(actual_damage, is_critical)
        
        return actual_damage, was_dodged, is_critical

    def _is_critical_hit(self) -> bool:
        """Sprawdza czy atak jest krytyczny."""
        crit_chance = self.current_stats.critical_chance
        
        # Modyfikatory z efektów statusu
        for effect in self.status_effects:
            if 'crit_chance_bonus' in effect.stat_modifiers:
                crit_chance += effect.stat_modifiers['crit_chance_bonus']
        
        # Nie można mieć więcej niż 75% szansy na trafienie krytyczne
        crit_chance = min(0.75, crit_chance)
        
        return random.random() < crit_chance

    def _get_critical_multiplier(self) -> float:
        """Zwraca mnożnik obrażeń krytycznych."""
        base_multiplier = 2.0
        
        # Modyfikatory z umiejętności
        if hasattr(self, 'get_skill_level'):
            crit_mastery = self.get_skill_level('combat', 'critical_mastery')
            if crit_mastery > 0:
                base_multiplier += crit_mastery * 0.1
        
        # Modyfikatory z efektów statusu
        for effect in self.status_effects:
            if 'crit_damage_bonus' in effect.stat_modifiers:
                base_multiplier += effect.stat_modifiers['crit_damage_bonus']
        
        return base_multiplier

    def _modify_outgoing_damage(self, damage: float, damage_type: str) -> float:
        """Modyfikuje zadawane obrażenia."""
        # Podstawowy bonus do obrażeń
        damage_bonus = 1.0
        
        # Bonus z siły
        if damage_type == 'physical':
            strength_bonus = self.current_stats.strength / 100
            damage_bonus += strength_bonus
            
        # Bonus z inteligencji dla obrażeń magicznych
        elif 'magical' in damage_type:
            intel_bonus = self.current_stats.intelligence / 100
            damage_bonus += intel_bonus
            
        # Modyfikatory z efektów statusu
        for effect in self.status_effects:
            if 'damage_dealt_modifier' in effect.stat_modifiers:
                damage_bonus += effect.stat_modifiers['damage_dealt_modifier']
                
        # Aplikuj całkowity bonus
        return damage * damage_bonus

    def heal(self, amount: float, source: Optional[str] = None) -> float:
        """Leczy jednostkę.
        
        Args:
            amount: Ilość leczenia
            source: Źródło leczenia (np. 'potion', 'spell', 'regeneration')
        
        Returns:
            float: Rzeczywista ilość przywróconego zdrowia
        """
        if not self.is_alive:
            return 0
            
        # Modyfikatory leczenia
        healing_modifier = 1.0
        
        # Modyfikatory z efektów statusu
        for effect in self.status_effects:
            if 'healing_received_modifier' in effect.stat_modifiers:
                healing_modifier *= (1 + effect.stat_modifiers['healing_received_modifier'])
        
        # Aplikuj modyfikowane leczenie
        actual_healing = amount * healing_modifier
        old_health = self.stats.health
        self.stats.health = min(self.stats.max_health, old_health + actual_healing)
        healing_done = self.stats.health - old_health
        
        # Aktualizuj statystyki
        self.combat_stats.healing_done += healing_done
        
        logger.debug(
            f"{self.name} wyleczył {healing_done:.1f} punktów zdrowia "
            f"(źródło: {source if source else 'nieznane'})"
        )
        
        return healing_done

    def die(self):
        """Obsługuje śmierć jednostki."""
        if not self.is_alive:  # Już nie żyje
            return
            
        self.is_alive = False
        self.stats.health = 0
        self.combat_stats.deaths += 1
        
        # Usuń wszystkie tymczasowe efekty statusu
        for effect in list(self.status_effects):
            if not effect.is_permanent:
                self._remove_effect(effect)
        
        # Wywołaj dodatkowe efekty śmierci
        self._trigger_death_effects()
        
        logger.info(f"{self.name} died")

    def _trigger_death_effects(self):
        """Wywołuje dodatkowe efekty przy śmierci."""
        # Może być przeciążone przez podklasy
        pass

    def resurrect(self, health_percentage: float = 0.5):
        """Wskrzesza jednostkę."""
        if self.is_alive:
            return
            
        self.is_alive = True
        self.stats.health = self.stats.max_health * health_percentage
        
        # Przywróć część zasobów
        self.stats.stamina = self.stats.max_stamina * 0.5
        self.stats.mana = self.stats.max_mana * 0.5
        
        logger.info(f"{self.name} został wskrzeszony z {self.stats.health:.1f} HP")
        
    # Kontynuacja klasy Entity

    def use_ability(self, ability_id: str, target: Optional['Entity'] = None,
                   position: Optional[Position] = None) -> Tuple[bool, str, List[Dict]]:
        """Używa zdolności.
        
        Returns:
            Tuple[bool, str, List[Dict]]: (sukces, wiadomość, lista efektów do wyświetlenia)
        """
        # Sprawdź czy zdolność jest dostępna
        can_use, message = self.can_use_ability(ability_id)
        if not can_use:
            return False, message, []
            
        ability = self.abilities[ability_id]
        effects = []
        
        # Sprawdź zasięg jeśli jest cel
        if target and not self._is_in_ability_range(target, ability):
            return False, "Cel jest poza zasięgiem!", []
            
        # Zużyj zasoby
        self.stats.stamina -= ability['cost'].get('stamina', 0)
        self.stats.mana -= ability['cost'].get('mana', 0)
        
        # Efekt podstawowy (obrażenia)
        if target and ability['damage'] > 0:
            damage = ability['damage']
            # Modyfikatory z umiejętności
            if hasattr(self, 'get_skill_level'):
                skill_bonus = self.get_skill_bonus(ability['skill_type'])
                damage *= (1 + skill_bonus)
                
            actual_damage, was_dodged, was_crit = self.deal_damage(
                target, damage, ability.get('damage_type', 'physical')
            )
            
            if was_dodged:
                return False, f"{target.name} uniknął {ability['name']}!", []
                
            effects.append({
                'type': 'damage',
                'target': target.id,
                'amount': actual_damage,
                'critical': was_crit
            })
            
            message = f"Użyto {ability['name']} zadając {actual_damage:.1f} obrażeń"
            if was_crit:
                message += " (Krytyczne!)"
        
        # Efekty obszarowe
        if ability.get('area_of_effect', 0) > 0:
            aoe_targets = self._get_targets_in_range(position or self.position, 
                                                   ability['area_of_effect'])
            for aoe_target in aoe_targets:
                if aoe_target != target:  # Nie aplikuj dwa razy do głównego celu
                    aoe_damage = ability['damage'] * 0.5  # 50% obrażeń dla celów pobocznych
                    actual_damage, _, _ = self.deal_damage(
                        aoe_target, aoe_damage, ability.get('damage_type', 'physical')
                    )
                    effects.append({
                        'type': 'damage',
                        'target': aoe_target.id,
                        'amount': actual_damage,
                        'is_aoe': True
                    })
        
        # Efekty statusu
        for effect_data in ability.get('effects', []):
            effect = StatusEffect(**effect_data)
            if target:
                target.add_status_effect(effect)
                effects.append({
                    'type': 'effect',
                    'target': target.id,
                    'effect': effect.name
                })
            else:  # Self-buff
                self.add_status_effect(effect)
                effects.append({
                    'type': 'effect',
                    'target': self.id,
                    'effect': effect.name
                })
        
        # Efekty wizualne
        if 'visual_effects' in ability:
            effects.extend(ability['visual_effects'])
        
        # Ustaw cooldown
        self._set_ability_cooldown(ability_id)
        
        return True, message, effects

    def can_use_ability(self, ability_id: str) -> Tuple[bool, str]:
        """Sprawdza czy jednostka może użyć zdolności."""
        if ability_id not in self.abilities:
            return False, "Nieznana zdolność!"
            
        ability = self.abilities[ability_id]
        
        # Sprawdź cooldown
        if self._is_on_cooldown(ability_id):
            remaining = self._get_remaining_cooldown(ability_id)
            return False, f"Zdolność odnowi się za {remaining:.1f}s!"
            
        # Sprawdź wymagane zasoby
        if self.stats.stamina < ability['cost'].get('stamina', 0):
            return False, "Niewystarczająca stamina!"
            
        if self.stats.mana < ability['cost'].get('mana', 0):
            return False, "Niewystarczająca mana!"
            
        # Sprawdź wymagania
        if not self._check_ability_requirements(ability):
            return False, "Nie spełniasz wymagań tej zdolności!"
            
        return True, ""

    def _check_ability_requirements(self, ability: dict) -> bool:
        """Sprawdza czy spełnione są wymagania zdolności."""
        requirements = ability.get('requirements', {})
        
        # Sprawdź poziom
        if 'level' in requirements and self.level < requirements['level']:
            return False
            
        # Sprawdź statystyki
        if 'stats' in requirements:
            for stat, value in requirements['stats'].items():
                if getattr(self.current_stats, stat, 0) < value:
                    return False
                    
        # Sprawdź umiejętności
        if 'skills' in requirements and hasattr(self, 'get_skill_level'):
            for skill_type, level in requirements['skills'].items():
                if self.get_skill_level(skill_type) < level:
                    return False
                    
        # Sprawdź wymagane przedmioty
        if 'items' in requirements and self.inventory:
            for item_id, count in requirements['items'].items():
                if not self.inventory.has_item(item_id, count):
                    return False
                    
        return True

    def _is_in_ability_range(self, target: 'Entity', ability: dict) -> bool:
        """Sprawdza czy cel jest w zasięgu zdolności."""
        if not hasattr(target, 'position'):
            return True
            
        ability_range = ability.get('range', 1.0)
        distance = self.position.distance_to(target.position)
        return distance <= ability_range

    def _get_targets_in_range(self, center: Position, radius: float) -> List['Entity']:
        """Znajduje wszystkie cele w zasięgu obszarowym."""
        # Ta metoda powinna być zaimplementowana przez system gry
        return []

    def _is_on_cooldown(self, ability_id: str) -> bool:
        """Sprawdza czy zdolność jest na cooldownie."""
        return ability_id in self._cooldowns and self._cooldowns[ability_id] > time.time()

    def _get_remaining_cooldown(self, ability_id: str) -> float:
        """Zwraca pozostały czas cooldownu."""
        if not self._is_on_cooldown(ability_id):
            return 0.0
        return self._cooldowns[ability_id] - time.time()

    def _set_ability_cooldown(self, ability_id: str):
        """Ustawia cooldown zdolności."""
        ability = self.abilities[ability_id]
        cooldown = ability['cooldown']
        
        # Modyfikatory redukcji czasu odnowienia
        if hasattr(self, 'get_cooldown_reduction'):
            cooldown *= (1 - self.get_cooldown_reduction())
            
        self._cooldowns[ability_id] = time.time() + cooldown

    def get_ability_info(self, ability_id: str) -> Dict:
        """Zwraca szczegółowe informacje o zdolności."""
        if ability_id not in self.abilities:
            raise InvalidSkillError(f"Nieznana zdolność: {ability_id}")
            
        ability = self.abilities[ability_id]
        info = ability.copy()
        
        # Dodaj informacje o cooldownie
        if self._is_on_cooldown(ability_id):
            info['cooldown_remaining'] = self._get_remaining_cooldown(ability_id)
        else:
            info['cooldown_remaining'] = 0
            
        # Dodaj informacje o wymaganiach
        can_use, reason = self.can_use_ability(ability_id)
        info['can_use'] = can_use
        info['cannot_use_reason'] = reason if not can_use else ""
        
        # Dodaj informacje o modyfikatorach
        if hasattr(self, 'get_skill_bonus'):
            skill_bonus = self.get_skill_bonus(ability['skill_type'])
            if 'damage' in info:
                info['modified_damage'] = info['damage'] * (1 + skill_bonus)
                
        return info

    def get_skill_bonus(self, skill_type: str) -> float:
        """Zwraca bonus z umiejętności."""
        # Ta metoda powinna być przeciążona przez klasę Player
        return 0.0

    @abstractmethod
    def get_loot(self) -> List[dict]:
        """Zwraca łup z jednostki."""
        pass

    def get_state(self) -> dict:
        """Zwraca obecny stan jednostki."""
        state = {
            'id': self.id,
            'name': self.name,
            'level': self.level,
            'health': self.stats.health,
            'max_health': self.stats.max_health,
            'stamina': self.stats.stamina,
            'status_effects': [
                {
                    'name': effect.name,
                    'duration': effect.duration,
                    'type': effect.type
                }
                for effect in self.status_effects
            ],
            'position': {
                'x': self.position.x,
                'y': self.position.y,
                'z': self.position.z
            },
            'is_alive': self.is_alive,
            'in_combat': self.in_combat,
            'combat_stats': self.combat_stats.__dict__,
            'cooldowns': {
                ability_id: remaining 
                for ability_id, remaining in self._cooldowns.items()
                if remaining > time.time()
            }
        }
        
        # Dodaj informacje o ekwipunku jeśli istnieje
        if self.inventory:
            state['inventory'] = self.inventory.get_state()
            
        return state
    
class Character(Entity):
    """Klasa reprezentująca postacie niezależne (NPC)."""
    
    def __init__(self, char_id: str, data: dict):
        super().__init__(char_id, data)
        
        # Podstawowe atrybuty NPC
        self.faction = data.get('faction', 'neutral')
        self.relations = data.get('relations', {})
        self.dialogues = data.get('dialogues', [])
        self.shop_items = data.get('shop_items', [])
        self.quest_giver = data.get('quest_giver', False)
        self.behavior = data.get('behavior', 'friendly')
        
        # System aktywności dobowej
        self.daily_schedule = data.get('daily_schedule', {})
        self.current_activity = None
        self.home_location = data.get('home_location')
        self.work_location = data.get('work_location')
        
        # System interakcji
        self.available_services = data.get('services', [])
        self.interaction_cooldown = 0
        self.conversation_topics = data.get('conversation_topics', {})
        self.knowledge = data.get('knowledge', {})
        
        # System relacji
        self.friendship_level = {}
        self.trust_level = {}
        self.last_interaction = {}
        self.interaction_history = []
        
        # Inicjalizacja dodatkowych systemów
        self._initialize_services()
        self._initialize_schedule()
        self._initialize_ai()

    def _initialize_services(self):
        """Inicjalizuje usługi oferowane przez NPC."""
        self.services = {}
        for service_data in self.available_services:
            service_type = service_data['type']
            if service_type == 'merchant':
                self.services['trade'] = {
                    'enabled': True,
                    'specialization': service_data.get('specialization', 'general'),
                    'markup': service_data.get('markup', 1.0),
                    'min_reputation': service_data.get('min_reputation', -100)
                }
            elif service_type == 'trainer':
                self.services['training'] = {
                    'skills': service_data.get('skills', []),
                    'max_level': service_data.get('max_level', 5),
                    'cost_per_level': service_data.get('cost_per_level', 100)
                }
            elif service_type == 'questgiver':
                self.services['quests'] = {
                    'quest_types': service_data.get('quest_types', []),
                    'min_level': service_data.get('min_level', 1),
                    'reputation_requirement': service_data.get('reputation_requirement', 0)
                }

    def _initialize_schedule(self):
        """Inicjalizuje harmonogram dzienny NPC."""
        self.schedule = {}
        for time_range, activity_data in self.daily_schedule.items():
            start, end = map(int, time_range.split('-'))
            self.schedule[time_range] = {
                'activity': activity_data['type'],
                'location': activity_data.get('location'),
                'interactions': activity_data.get('available_interactions', []),
                'dialogue_set': activity_data.get('dialogue_set', 'default'),
                'conditions': activity_data.get('conditions', {})
            }

    def _initialize_ai(self):
        """Inicjalizuje system sztucznej inteligencji NPC."""
        self.ai_state = {
            'current_goal': None,
            'current_path': [],
            'known_threats': set(),
            'interest_points': {},
            'memory': {},
            'emotional_state': 'neutral',
            'behavior_flags': set()
        }

    def update(self, game_time: float):
        """Aktualizuje stan NPC."""
        super().update(game_time)
        
        # Aktualizacja aktywności
        self._update_activity(game_time)
        
        # Aktualizacja AI
        self._update_ai(game_time)
        
        # Aktualizacja relacji
        self._update_relations(game_time)
        
        # Aktualizacja usług
        self._update_services(game_time)

    def _update_activity(self, game_time: float):
        """Aktualizuje aktywność NPC na podstawie harmonogramu."""
        current_hour = int((game_time / 3600) % 24)
        
        # Znajdź odpowiednią aktywność dla aktualnej godziny
        for time_range, activity_data in self.schedule.items():
            start, end = map(int, time_range.split('-'))
            if start <= current_hour < end:
                if self.current_activity != activity_data['activity']:
                    self._change_activity(activity_data)
                break

    def _change_activity(self, activity_data: dict):
        """Zmienia aktualną aktywność NPC."""
        self.current_activity = activity_data['activity']
        target_location = activity_data.get('location')
        
        if target_location and target_location != self.position:
            self._plan_path_to(target_location)
            
        # Aktualizuj dostępne interakcje
        self.available_interactions = activity_data.get('interactions', [])
        
        # Ustaw odpowiedni zestaw dialogów
        self.current_dialogue_set = activity_data.get('dialogue_set', 'default')
        
        logger.debug(
            f"{self.name} zmienił aktywność na {self.current_activity} "
            f"w lokacji {target_location or 'obecna'}"
        )

    def _plan_path_to(self, target_location: str):
        """Planuje ścieżkę do celu."""
        self.ai_state['current_path'] = self._find_path_to(target_location)
        if self.ai_state['current_path']:
            self.ai_state['current_goal'] = {
                'type': 'move_to',
                'target': target_location,
                'reason': 'schedule'
            }

    def _find_path_to(self, target_location: str) -> List[str]:
        """Znajduje ścieżkę do celu."""
        # Ta metoda powinna być zaimplementowana przez system nawigacji świata
        return []
    
    # Kontynuacja klasy Character

    def interact(self, player: 'Player') -> Tuple[bool, str, Dict]:
        """Podstawowa interakcja z NPC."""
        if not self._can_interact(player):
            return False, f"{self.name} nie chce teraz rozmawiać.", {}
            
        # Aktualizuj historię interakcji
        self._record_interaction(player.id, 'talk')
        
        # Sprawdź specjalne dialogi dla questów
        if special_dialogue := self._get_quest_dialogue(player):
            return True, special_dialogue['text'], special_dialogue['data']
            
        # Generuj odpowiednią odpowiedź bazując na relacjach i sytuacji
        response = self._generate_response(player)
        
        # Aktualizuj relacje
        self._update_relationship(player.id, 'talk')
        
        return True, response['text'], response['data']

    def _can_interact(self, player: 'Player') -> bool:
        """Sprawdza czy interakcja jest możliwa."""
        # Sprawdź cooldown interakcji
        if time.time() < self.interaction_cooldown:
            return False
            
        # Sprawdź czy aktywność pozwala na interakcję
        if self.current_activity in ['sleeping', 'busy', 'unavailable']:
            return False
            
        # Sprawdź relacje
        if self.faction in player.reputation:
            if player.reputation[self.faction] < -75:  # Skrajna wrogość
                return False
                
        # Sprawdź warunki interakcji dla obecnej aktywności
        if not self._check_activity_conditions(player):
            return False
            
        return True

    def _check_activity_conditions(self, player: 'Player') -> bool:
        """Sprawdza warunki interakcji dla obecnej aktywności."""
        if not self.current_activity:
            return True
            
        activity_data = next(
            (data for _, data in self.schedule.items() 
             if data['activity'] == self.current_activity),
            None
        )
        
        if not activity_data:
            return True
            
        conditions = activity_data.get('conditions', {})
        
        # Sprawdź wymagany poziom gracza
        if 'min_level' in conditions and player.level < conditions['min_level']:
            return False
            
        # Sprawdź wymagane relacje
        if 'min_reputation' in conditions:
            for faction, value in conditions['min_reputation'].items():
                if player.reputation.get(faction, 0) < value:
                    return False
                    
        # Sprawdź wymagane questy
        if 'required_quests' in conditions:
            for quest_id in conditions['required_quests']:
                if quest_id not in player.completed_quests:
                    return False
                    
        return True

    def _record_interaction(self, player_id: str, interaction_type: str):
        """Zapisuje interakcję w historii."""
        self.interaction_history.append({
            'player_id': player_id,
            'type': interaction_type,
            'timestamp': time.time(),
            'location': self.position,
            'activity': self.current_activity
        })
        
        # Ogranicz historię do ostatnich 100 interakcji
        if len(self.interaction_history) > 100:
            self.interaction_history = self.interaction_history[-100:]

    def _update_relationship(self, player_id: str, interaction_type: str):
        """Aktualizuje relacje z graczem."""
        # Inicjalizuj relacje jeśli nie istnieją
        if player_id not in self.friendship_level:
            self.friendship_level[player_id] = 0
        if player_id not in self.trust_level:
            self.trust_level[player_id] = 0
            
        # Podstawowe zmiany bazowane na typie interakcji
        changes = {
            'talk': {'friendship': 1, 'trust': 0},
            'trade': {'friendship': 0, 'trust': 1},
            'quest_complete': {'friendship': 5, 'trust': 3},
            'quest_fail': {'friendship': -3, 'trust': -5},
            'gift': {'friendship': 3, 'trust': 1},
            'help': {'friendship': 2, 'trust': 2}
        }
        
        if interaction_type in changes:
            change = changes[interaction_type]
            self._modify_relationship(player_id, change['friendship'], change['trust'])

    def _modify_relationship(self, player_id: str, friendship_change: int, trust_change: int):
        """Modyfikuje poziomy przyjaźni i zaufania."""
        # Aplikuj zmiany z uwzględnieniem limitów
        self.friendship_level[player_id] = max(-100, min(100, 
            self.friendship_level[player_id] + friendship_change))
        self.trust_level[player_id] = max(-100, min(100, 
            self.trust_level[player_id] + trust_change))
            
        # Zapisz czas ostatniej interakcji
        self.last_interaction[player_id] = time.time()

    def get_relationship_status(self, player_id: str) -> Dict[str, Any]:
        """Zwraca status relacji z graczem."""
        friendship = self.friendship_level.get(player_id, 0)
        trust = self.trust_level.get(player_id, 0)
        
        # Określ ogólny status relacji
        if friendship >= 75 and trust >= 75:
            status = "Najlepszy przyjaciel"
        elif friendship >= 50:
            status = "Przyjaciel"
        elif friendship >= 25:
            status = "Znajomy"
        elif friendship >= 0:
            status = "Neutralny"
        elif friendship >= -25:
            status = "Nieufny"
        elif friendship >= -50:
            status = "Wrogi"
        else:
            status = "Nieprzyjaciel"
            
        return {
            'status': status,
            'friendship': friendship,
            'trust': trust,
            'last_interaction': self.last_interaction.get(player_id, 0),
            'interaction_count': len([x for x in self.interaction_history 
                                   if x['player_id'] == player_id])
        }

    def _generate_response(self, player: 'Player') -> Dict[str, Any]:
        """Generuje odpowiednią odpowiedź dla gracza."""
        # Weź pod uwagę aktualną aktywność
        activity_responses = self._get_activity_responses()
        
        # Weź pod uwagę relacje
        relationship = self.get_relationship_status(player.id)
        
        # Weź pod uwagę emocjonalny stan NPC
        emotional_responses = self._get_emotional_responses()
        
        # Weź pod uwagę wiedzę o questach gracza
        quest_responses = self._get_quest_related_responses(player)
        
        # Wybierz najlepszą odpowiedź bazując na priorytetach
        if quest_responses:
            response = quest_responses
        elif any(self.ai_state['known_threats']):
            response = self._get_threat_response()
        elif activity_responses:
            response = activity_responses
        else:
            response = self._get_default_response(relationship)
            
        return response

    def _get_activity_responses(self) -> Optional[Dict[str, Any]]:
        """Zwraca odpowiedzi związane z aktualną aktywnością."""
        if not self.current_activity:
            return None
            
        responses = {
            'sleeping': {
                'text': "Zzz... *NPC śpi głęboko*",
                'data': {'type': 'sleeping', 'can_wake': False}
            },
            'working': {
                'text': "Przepraszam, ale jestem teraz zajęty pracą.",
                'data': {'type': 'working', 'can_interrupt': False}
            },
            'eating': {
                'text': "Właśnie jem posiłek. Może porozmawiamy później?",
                'data': {'type': 'eating', 'can_join': True}
            },
            'shopping': {
                'text': "Rozglądam się za towarem.",
                'data': {'type': 'shopping', 'can_help': True}
            }
        }
        
        return responses.get(self.current_activity)

    def _get_emotional_responses(self) -> Optional[Dict[str, Any]]:
        """Zwraca odpowiedzi bazujące na stanie emocjonalnym."""
        emotional_state = self.ai_state['emotional_state']
        
        responses = {
            'happy': {
                'text': "Witaj! Dziś jest wspaniały dzień, prawda?",
                'data': {'mood': 'positive', 'gesture': 'smile'}
            },
            'angry': {
                'text': "Czego chcesz? Lepiej mnie dziś nie denerwuj!",
                'data': {'mood': 'negative', 'gesture': 'frown'}
            },
            'scared': {
                'text': "N-nie podchodź zbyt blisko...",
                'data': {'mood': 'negative', 'gesture': 'step_back'}
            },
            'sad': {
                'text': "*wzdycha* Tak...?",
                'data': {'mood': 'negative', 'gesture': 'sigh'}
            }
        }
        
        return responses.get(emotional_state)

class BaseEntity:
    def __init__(self):
        pass  # lub super().__init__()

class Entity:
    def __init__(self, entity_id: str, data: dict):
        if not isinstance(entity_id, str) or not isinstance(data, dict):
            raise ValueError("Nieprawidłowe argumenty konstruktora Entity")
            
        self.id = entity_id
        self.name = data.get('name', '')
        self.type = data.get('type', '')
        self.stats = data.get('stats', {})

    def get_loot(self):
        """Implementacja dla bazowej klasy."""
        return []