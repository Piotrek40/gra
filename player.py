# player.py
from inventory import Inventory
import json
import random
import time
import logging
from typing import List, Optional, Dict
from entities import Entity, Stats, StatusEffect  # Dodany import Entity
from config import game_config
from quests import QuestManager
from character import Character

# Konfiguracja loggera
logger = logging.getLogger(__name__)


class Player(Character):
    def __init__(self, player_id: str, data: dict = None):
        if data is None:
            data = self._get_default_player_data()
        super().__init__(player_id, data)
        
        # Dodać brakujące inicjalizacje
        self.inventory = Inventory(capacity=20)  # Określić pojemność
        self.equipment = {}  # Dodać słownik ekwipunku
        self.status_effects = []  # Dodać efekty statusu
        self.level = data.get('level', 1)
        self.experience = data.get('experience', 0)
        self.gold = data.get('gold', 0)
        self.current_location = data.get('current_location', 'miasto_startowe')

    def _get_default_player_data(self) -> dict:
        """Zwraca domyślne dane dla nowego gracza."""
        return {
            'name': 'Hero',
            'level': 1,
            'stats': {
                'health': 100,
                'max_health': 100,
                'stamina': 100,
                'max_stamina': 100,
                'mana': 50,
                'max_mana': 50,
                'strength': 10,
                'defense': 5,
                'agility': 10,
                'intelligence': 10
            },
            'gold': 100,
            'inventory_size': 20
        }

    def _calculate_next_level_exp(self) -> int:
        """Oblicza wymagane doświadczenie do następnego poziomu."""
        return int(100 * (self.level ** 1.5))

    def gain_experience(self, amount: int) -> List[str]:
        """Dodaje doświadczenie i sprawdza awans na wyższy poziom."""
        messages = []
        self.experience += amount
        messages.append(f"Zdobyto {amount} punktów doświadczenia!")
        
        while self.experience >= self.experience_to_next_level:
            self.level_up()
            messages.append(f"Awansowałeś na poziom {self.level}!")
            self.experience -= self.experience_to_next_level
            self.experience_to_next_level = self._calculate_next_level_exp()
            
        return messages

    def level_up(self):
        """Awansuje gracza na następny poziom."""
        self.level += 1
        self.skill_points += 3
        self.talent_points += 1
        
        # Zwiększanie podstawowych statystyk
        stat_increases = {
            'max_health': 10,
            'max_stamina': 5,
            'max_mana': 5,
            'strength': 1,
            'defense': 1,
            'agility': 1,
            'intelligence': 1
        }
        
        for stat, increase in stat_increases.items():
            current_value = getattr(self.stats, stat)
            setattr(self.stats, stat, current_value + increase)
            
        # Przywrócenie zdrowia i zasobów
        self.stats.health = self.stats.max_health
        self.stats.stamina = self.stats.max_stamina
        self.stats.mana = self.stats.max_mana
        
    # Kontynuacja klasy Player

    def gain_skill_experience(self, category: str, skill: str, amount: int) -> List[str]:
        """Dodaje doświadczenie do umiejętności."""
        messages = []
        if category not in self.skills or skill not in self.skills[category]:
            return [f"Nieznana umiejętność: {category}.{skill}"]
            
        current_level = self.skills[category][skill]
        self.skill_experience[category][skill] += amount
        
        # Sprawdź czy nastąpił awans umiejętności
        exp_needed = self._calculate_skill_level_exp(current_level)
        while self.skill_experience[category][skill] >= exp_needed:
            self.skills[category][skill] += 1
            self.skill_experience[category][skill] -= exp_needed
            new_level = self.skills[category][skill]
            
            messages.append(f"Umiejętność {skill} osiągnęła poziom {new_level}!")
            
            # Odblokowanie nowych zdolności
            if new_ability := self._check_new_abilities(category, skill, new_level):
                messages.append(f"Odblokowano nową zdolność: {new_ability}")
                
            exp_needed = self._calculate_skill_level_exp(new_level)
            
        return messages

    def _calculate_skill_level_exp(self, current_level: int) -> int:
        """Oblicza wymagane doświadczenie do następnego poziomu umiejętności."""
        return int(75 * (current_level ** 1.8))

    def _check_new_abilities(self, category: str, skill: str, level: int) -> Optional[str]:
        """Sprawdza czy na danym poziomie odblokowuje się nowa zdolność."""
        ability_unlocks = {
            'combat': {
                'melee': {
                    3: 'Potężne uderzenie',
                    5: 'Wirujący cios',
                    7: 'Rozłupanie zbroi'
                },
                'ranged': {
                    3: 'Precyzyjny strzał',
                    5: 'Strzał wielokrotny',
                    7: 'Strzał osłabiający'
                },
                'defense': {
                    3: 'Blok tarczą',
                    5: 'Kontratak',
                    7: 'Niezniszczalna postawa'
                }
            },
            'crafting': {
                'smithing': {
                    3: 'Ulepszanie broni',
                    5: 'Mistrzowska naprawa',
                    7: 'Wykuwanie magicznej broni'
                },
                'alchemy': {
                    3: 'Ulepszone mikstury',
                    5: 'Trwałe eliksiry',
                    7: 'Mistyczne wywary'
                },
                'enchanting': {
                    3: 'Podstawowe zaklęcia',
                    5: 'Potężne enchant',
                    7: 'Legendarne zaklęcia'
                }
            },
            'survival': {
                'gathering': {
                    3: 'Podwójne zbiory',
                    5: 'Rzadkie zasoby',
                    7: 'Mistrzowskie zbieractwo'
                },
                'tracking': {
                    3: 'Śledzenie zwierzyny',
                    5: 'Tropienie rzadkich stworzeń',
                    7: 'Mistrzowskie tropienie'
                },
                'stealth': {
                    3: 'Cichy chód',
                    5: 'Znikanie w cieniu',
                    7: 'Mistrzowskie skradanie'
                }
            }
        }
        
        return ability_unlocks.get(category, {}).get(skill, {}).get(level)

    def spend_skill_points(self, category: str, skill: str, points: int) -> tuple[bool, str]:
        """Wydaje punkty umiejętności na rozwój konkretnej umiejętności."""
        if points > self.skill_points:
            return False, "Nie masz wystarczającej liczby punktów umiejętności!"
            
        if category not in self.skills or skill not in self.skills[category]:
            return False, f"Nieznana umiejętność: {category}.{skill}"
            
        current_level = self.skills[category][skill]
        if current_level >= 10:  # Maksymalny poziom podstawowy
            return False, "Ta umiejętność osiągnęła maksymalny poziom!"
            
        # Wydaj punkty
        self.skill_points -= points
        self.skills[category][skill] += points
        
        # Sprawdź odblokowane zdolności
        new_level = self.skills[category][skill]
        if new_ability := self._check_new_abilities(category, skill, new_level):
            return True, f"Rozwinięto {skill} do poziomu {new_level}! Odblokowano: {new_ability}"
            
        return True, f"Rozwinięto {skill} do poziomu {new_level}!"

    def get_skill_bonus(self, category: str, skill: str) -> float:
        """Zwraca bonus z umiejętności do odpowiednich akcji."""
        if category not in self.skills or skill not in self.skills[category]:
            return 0.0
            
        skill_level = self.skills[category][skill]
        base_bonus = skill_level * 0.1  # 10% bonus na poziom
        
        # Dodatkowe bonusy z talentów i ekwipunku
        equipment_bonus = self._get_equipment_skill_bonus(category, skill)
        talent_bonus = self._get_talent_skill_bonus(category, skill)
        
        return base_bonus + equipment_bonus + talent_bonus

    def _get_equipment_skill_bonus(self, category: str, skill: str) -> float:
        """Oblicza bonus do umiejętności z ekwipunku."""
        total_bonus = 0.0
        
        for slot, item in self.equipment_slots.items():
            if not item:
                continue
            
            # Sprawdź bonusy przedmiotu do umiejętności
            item_data = item.get_data()
            if 'skill_bonuses' in item_data:
                if category in item_data['skill_bonuses']:
                    if skill in item_data['skill_bonuses'][category]:
                        total_bonus += item_data['skill_bonuses'][category][skill]
                        
        return total_bonus

    def _get_talent_skill_bonus(self, category: str, skill: str) -> float:
        """Oblicza bonus do umiejętności z talentów."""
        # Ta funkcja będzie rozbudowana gdy dodamy system talentów
        return 0.0

    def get_skill_modifiers(self) -> dict:
        """Zwraca wszystkie aktywne modyfikatory umiejętności."""
        modifiers = {}
        
        for category in self.skills:
            modifiers[category] = {}
            for skill in self.skills[category]:
                base_bonus = self.get_skill_bonus(category, skill)
                equipment_bonus = self._get_equipment_skill_bonus(category, skill)
                talent_bonus = self._get_talent_skill_bonus(category, skill)
                
                modifiers[category][skill] = {
                    'base_bonus': base_bonus,
                    'equipment_bonus': equipment_bonus,
                    'talent_bonus': talent_bonus,
                    'total': base_bonus + equipment_bonus + talent_bonus
                }
                
        return modifiers
    
    # Kontynuacja klasy Player

    def equip_item(self, item_id: str) -> tuple[bool, str]:
        """Zakłada przedmiot na odpowiedni slot."""
        item = self.inventory.item_manager.get_item(item_id)
        if not item:
            return False, "Nie znaleziono przedmiotu!"
            
        # Sprawdź czy gracz ma przedmiot w ekwipunku
        if not self.inventory.has_item(item_id):
            return False, "Nie masz tego przedmiotu w ekwipunku!"
            
        # Sprawdź wymagania przedmiotu
        if not self._check_item_requirements(item):
            return False, "Nie spełniasz wymagań tego przedmiotu!"
            
        # Określ odpowiedni slot
        slot = self._determine_equipment_slot(item)
        if not slot:
            return False, "Nie możesz założyć tego przedmiotu!"
            
        # Zdejmij obecnie założony przedmiot jeśli istnieje
        if self.equipment_slots[slot]:
            self.unequip_item(slot)
            
        # Załóż nowy przedmiot
        self.equipment_slots[slot] = item_id
        self.inventory.remove_item(item_id, 1)
        
        # Aplikuj bonusy z przedmiotu
        self._apply_item_bonuses(item, True)
        
        return True, f"Założono {item.name} na slot {slot}!"

    def unequip_item(self, slot: str) -> tuple[bool, str]:
        """Zdejmuje przedmiot z podanego slotu."""
        if slot not in self.equipment_slots:
            return False, "Nieprawidłowy slot!"
            
        item_id = self.equipment_slots[slot]
        if not item_id:
            return False, "Ten slot jest pusty!"
            
        # Sprawdź czy jest miejsce w ekwipunku
        if not self.inventory.can_add_item(item_id):
            return False, "Brak miejsca w ekwipunku!"
            
        # Zdejmij bonusy przedmiotu
        item = self.inventory.item_manager.get_item(item_id)
        self._apply_item_bonuses(item, False)
        
        # Przenieś przedmiot do ekwipunku
        self.equipment_slots[slot] = None
        self.inventory.add_item(item_id, 1)
        
        return True, f"Zdjęto {item.name} ze slotu {slot}!"

    def _check_item_requirements(self, item) -> bool:
        """Sprawdza czy gracz spełnia wymagania przedmiotu."""
        if 'requirements' not in item.properties:
            return True
            
        reqs = item.properties['requirements']
        
        # Sprawdź wymagany poziom
        if 'level' in reqs and self.level < reqs['level']:
            return False
            
        # Sprawdź wymagane umiejętności
        if 'skills' in reqs:
            for category, skill_reqs in reqs['skills'].items():
                for skill, required_level in skill_reqs.items():
                    if self.skills[category][skill] < required_level:
                        return False
                        
        # Sprawdź wymagane statystyki
        if 'stats' in reqs:
            for stat, required_value in reqs['stats'].items():
                if getattr(self.stats, stat) < required_value:
                    return False
                    
        return True
    
    def use_item(self, item_id: str) -> tuple[bool, str]:
        item = self.inventory.get_item(item_id)
        if item:
            if item.type == 'consumable':
                if item.effect == 'restore_health':
                    self.health = min(self.health + item.value, self.max_health)
                    return True, f"Used {item.name} and restored {item.value} health."
                elif item.effect == 'restore_mana':
                    self.mana = min(self.mana + item.value, self.max_mana)
                    return True, f"Used {item.name} and restored {item.value} mana."
            # Add more item type handling here
        return False, "Failed to use the item."

    def _determine_equipment_slot(self, item) -> Optional[str]:
        """Określa odpowiedni slot dla przedmiotu."""
        type_to_slot = {
            'weapon': 'main_hand',
            'shield': 'off_hand',
            'helmet': 'head',
            'armor': 'chest',
            'legs': 'legs',
            'boots': 'feet',
            'ring': 'ring1',  # lub ring2
            'necklace': 'necklace'
        }
        
        item_type = item.properties.get('equipment_type')
        if not item_type:
            return None
            
        # Specjalna obsługa pierścieni
        if item_type == 'ring':
            if not self.equipment_slots['ring1']:
                return 'ring1'
            elif not self.equipment_slots['ring2']:
                return 'ring2'
            else:
                return 'ring1'  # Domyślnie zastąp pierwszy pierścień
                
        return type_to_slot.get(item_type)

    def _apply_item_bonuses(self, item, adding: bool = True):
        """Aplikuje lub usuwa bonusy z przedmiotu."""
        if 'bonuses' not in item.properties:
            return
            
        multiplier = 1 if adding else -1
        bonuses = item.properties['bonuses']
        
        # Aplikuj bonusy do statystyk
        for stat, value in bonuses.get('stats', {}).items():
            current = getattr(self.stats, stat)
            setattr(self.stats, stat, current + (value * multiplier))
            
        # Aplikuj bonusy do umiejętności
        for category, skills in bonuses.get('skills', {}).items():
            for skill, value in skills.items():
                self.skill_bonuses[category][skill] = self.skill_bonuses.get(category, {}).get(skill, 0) + (value * multiplier)

    def interact_with_object(self, object_id: str, world) -> tuple[bool, str]:
        """Interakcja z obiektami w świecie gry."""
        obj = world.get_object(object_id)
        if not obj:
            return False, "Nie znaleziono obiektu!"
            
        # Sprawdź czy obiekt jest w zasięgu
        if not world.is_object_in_range(self.position, obj.position):
            return False, "Ten obiekt jest zbyt daleko!"
            
        # Sprawdź wymagane umiejętności
        if required_skill := obj.get_required_skill():
            category, skill, level = required_skill
            if self.skills[category][skill] < level:
                return False, f"Wymagana umiejętność: {skill} poziom {level}!"
                
        # Wykonaj interakcję
        return obj.interact(self)

    def use_ability(self, ability_id: str, target=None) -> tuple[bool, str]:
        """Używa zdolności."""
        # Sprawdź czy zdolność jest dostępna
        if not self.has_ability(ability_id):
            return False, "Nie znasz tej zdolności!"
            
        ability = self.get_ability(ability_id)
        
        # Sprawdź koszty i cooldowny
        if self.stats.stamina < ability['stamina_cost']:
            return False, "Niewystarczająca stamina!"
        if self.stats.mana < ability['mana_cost']:
            return False, "Niewystarczająca mana!"
            
        if ability_id in self.ability_cooldowns:
            return False, f"Zdolność odnowi się za {self.ability_cooldowns[ability_id]} sekund!"
            
        # Użyj zdolności
        success, message = super().use_ability(ability_id, target)
        if success:
            self.stats.stamina -= ability['stamina_cost']
            self.stats.mana -= ability['mana_cost']
            self.ability_cooldowns[ability_id] = ability['cooldown']
            
            # Dodaj doświadczenie do odpowiedniej umiejętności
            if 'skill_experience' in ability:
                category, skill = ability['skill_experience']
                self.gain_skill_experience(category, skill, 10)
                
        return success, message

    def rest(self, duration: int) -> tuple[bool, str]:
        """Odpoczynek odnawiający zasoby."""
        if self.in_combat:
            return False, "Nie możesz odpoczywać podczas walki!"
            
        # Oblicz ilość odnowionych zasobów
        health_regen = min(
            self.stats.max_health - self.stats.health,
            duration * (self.stats.max_health * 0.1)
        )
        stamina_regen = min(
            self.stats.max_stamina - self.stats.stamina,
            duration * (self.stats.max_stamina * 0.2)
        )
        mana_regen = min(
            self.stats.max_mana - self.stats.mana,
            duration * (self.stats.max_mana * 0.15)
        )
        
        # Aplikuj regenerację
        self.stats.health += health_regen
        self.stats.stamina += stamina_regen
        self.stats.mana += mana_regen
        
        return True, f"Odpocząłeś przez {duration} sekund i odnowiłeś zasoby!"

    def get_state(self) -> dict:
        """Rozszerzona wersja get_state z dodatkowymi informacjami o graczu."""
        base_state = super().get_state()
        player_state = {
            'experience': self.experience,
            'experience_to_next_level': self.experience_to_next_level,
            'skill_points': self.skill_points,
            'equipment': self.equipment_slots,
            'reputation': self.reputation,
            'active_quests': [quest.id for quest in self.active_quests],
            'achievements': list(self.achievements),
            'known_locations': list(self.known_locations),
            'player_stats': self.player_stats
        }
        return {**base_state, **player_state}
    
    # Kontynuacja klasy Player

    def accept_quest(self, quest_id: str) -> tuple[bool, str]:
        """Przyjmuje nowy quest."""
        if quest_id in [quest.id for quest in self.active_quests]:
            return False, "Ten quest jest już aktywny!"
            
        if quest_id in [quest.id for quest in self.completed_quests]:
            quest = self.quest_manager.get_quest(quest_id)
            if not quest.repeatable:
                return False, "Ten quest został już ukończony!"
        
        quest = self.quest_manager.get_quest(quest_id)
        if not quest:
            return False, "Nie znaleziono questa!"
            
        # Sprawdź wymagania questa
        if not self._check_quest_requirements(quest):
            return False, f"Nie spełniasz wymagań questa! (Wymagany poziom: {quest.min_level})"
            
        # Dodaj quest do aktywnych
        self.active_quests.append(quest)
        quest.start()
        
        # Dodaj wpis do dziennika
        self.quest_log.append({
            'timestamp': time.time(),
            'type': 'quest_accepted',
            'quest_id': quest_id,
            'quest_name': quest.name
        })
        
        return True, f"Przyjęto quest: {quest.name}"

    def _check_quest_requirements(self, quest) -> bool:
        """Sprawdza czy gracz spełnia wymagania questa."""
        if self.level < quest.min_level:
            return False
            
        # Sprawdź wymagania reputacji
        if hasattr(quest, 'reputation_requirements'):
            for faction, required_rep in quest.reputation_requirements.items():
                if self.reputation.get(faction, 0) < required_rep:
                    return False
                    
        # Sprawdź wymagane umiejętności
        if hasattr(quest, 'skill_requirements'):
            for category, skill_reqs in quest.skill_requirements.items():
                for skill, required_level in skill_reqs.items():
                    if self.skills[category][skill] < required_level:
                        return False
                        
        return True

    def update_quest_progress(self, event_type: str, target_id: str, amount: int = 1) -> List[str]:
        """Aktualizuje postęp questów na podstawie wydarzeń w grze."""
        messages = []
        for quest in self.active_quests:
            if quest.check_objective(event_type, target_id):
                progress = quest.update_progress(amount)
                messages.extend(progress)
                
                # Sprawdź czy quest został ukończony
                if quest.is_completed():
                    reward_messages = self.complete_quest(quest.id)
                    messages.extend(reward_messages)
                    
        return messages

    def complete_quest(self, quest_id: str) -> List[str]:
        """Kończy quest i przyznaje nagrody."""
        messages = []
        quest = next((q for q in self.active_quests if q.id == quest_id), None)
        if not quest:
            return ["Quest nie jest aktywny!"]
            
        # Usuń z aktywnych i dodaj do ukończonych
        self.active_quests.remove(quest)
        if not quest.repeatable:
            self.completed_quests.append(quest)
            
        # Przyznaj nagrody
        rewards = quest.get_rewards()
        messages.append(f"Ukończono quest: {quest.name}!")
        
        for reward_type, value in rewards.items():
            if reward_type == 'experience':
                messages.extend(self.gain_experience(value))
            elif reward_type == 'gold':
                self.gold += value
                messages.append(f"Otrzymano {value} złota!")
            elif reward_type == 'items':
                for item_id, amount in value.items():
                    success, msg = self.inventory.add_item(item_id, amount)
                    messages.append(msg)
            elif reward_type == 'reputation':
                for faction, amount in value.items():
                    self.add_reputation(faction, amount)
                    messages.append(f"Zmiana reputacji z {faction}: {amount}")
            elif reward_type == 'skill_experience':
                for category, skill_rewards in value.items():
                    for skill, amount in skill_rewards.items():
                        messages.extend(self.gain_skill_experience(category, skill, amount))
                        
        # Aktualizuj statystyki
        self.player_stats['quests_completed'] += 1
        
        # Sprawdź osiągnięcia związane z questami
        self._check_quest_achievements()
        
        return messages

    def _check_quest_achievements(self):
        """Sprawdza i przyznaje osiągnięcia związane z questami."""
        quest_achievements = {
            'quest_novice': {
                'name': 'Początkujący poszukiwacz przygód',
                'requirement': 5,
                'type': 'quests_completed'
            },
            'quest_expert': {
                'name': 'Ekspert zadań',
                'requirement': 25,
                'type': 'quests_completed'
            },
            'quest_master': {
                'name': 'Mistrz zadań',
                'requirement': 100,
                'type': 'quests_completed'
            }
        }
        
        for achievement_id, data in quest_achievements.items():
            if (achievement_id not in self.achievements and 
                self.player_stats[data['type']] >= data['requirement']):
                self.unlock_achievement(achievement_id)

    def unlock_achievement(self, achievement_id: str) -> tuple[bool, str]:
        """Odblokowuje osiągnięcie."""
        if achievement_id in self.achievements:
            return False, "To osiągnięcie zostało już odblokowane!"
            
        achievement_data = game_config.get(f'achievements.{achievement_id}')
        if not achievement_data:
            return False, "Nieznane osiągnięcie!"
            
        self.achievements.add(achievement_id)
        
        # Przyznaj nagrody za osiągnięcie
        if 'rewards' in achievement_data:
            self._grant_achievement_rewards(achievement_data['rewards'])
            
        return True, f"Odblokowano osiągnięcie: {achievement_data['name']}!"

    def _grant_achievement_rewards(self, rewards: dict):
        """Przyznaje nagrody za osiągnięcie."""
        for reward_type, value in rewards.items():
            if reward_type == 'experience':
                self.gain_experience(value)
            elif reward_type == 'gold':
                self.gold += value
            elif reward_type == 'items':
                for item_id, amount in value.items():
                    self.inventory.add_item(item_id, amount)

    def save_game(self) -> dict:
        """Przygotowuje dane do zapisu stanu gry."""
        return {
            'player_data': {
                'basic_info': {
                    'name': self.name,
                    'level': self.level,
                    'experience': self.experience,
                    'gold': self.gold
                },
                'stats': self.stats.__dict__,
                'skills': self.skills,
                'skill_experience': self.skill_experience,
                'equipment': self.equipment_slots,
                'inventory': self.inventory.get_save_data(),
                'reputation': self.reputation,
                'quests': {
                    'active': [quest.id for quest in self.active_quests],
                    'completed': [quest.id for quest in self.completed_quests]
                },
                'achievements': list(self.achievements),
                'player_stats': self.player_stats,
                'known_locations': list(self.known_locations),
                'quest_log': self.quest_log
            },
            'game_state': {
                'current_location': self.current_location,
                'game_time': game_config.get('game_time'),
                'difficulty': game_config.get('game_settings.difficulty')
            }
        }

    def load_game(self, save_data: dict):
        """Ładuje stan gry z zapisanych danych."""
        try:
            player_data = save_data['player_data']
            
            # Podstawowe informacje
            self.name = player_data['basic_info']['name']
            self.level = player_data['basic_info']['level']
            self.experience = player_data['basic_info']['experience']
            self.gold = player_data['basic_info']['gold']
            
            # Statystyki
            for stat, value in player_data['stats'].items():
                setattr(self.stats, stat, value)
                
            # Umiejętności i doświadczenie
            self.skills = player_data['skills']
            self.skill_experience = player_data['skill_experience']
            
            # Ekwipunek i wyposażenie
            self.equipment_slots = player_data['equipment']
            self.inventory.load_save_data(player_data['inventory'])
            
            # Reputacja i osiągnięcia
            self.reputation = player_data['reputation']
            self.achievements = set(player_data['achievements'])
            
            # Questy
            self._load_quests(player_data['quests'])
            
            # Pozostałe dane
            self.player_stats = player_data['player_stats']
            self.known_locations = set(player_data['known_locations'])
            self.quest_log = player_data['quest_log']
            
            # Stan gry
            game_state = save_data['game_state']
            self.current_location = game_state['current_location']
            
            return True, "Pomyślnie wczytano stan gry!"
            
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania stanu gry: {e}")
            return False, "Wystąpił błąd podczas wczytywania stanu gry!"

    def _load_quests(self, quest_data: dict):
        """Ładuje stan questów."""
        self.active_quests = []
        self.completed_quests = []
        
        for quest_id in quest_data['active']:
            quest = self.quest_manager.get_quest(quest_id)
            if quest:
                self.active_quests.append(quest)
                
        for quest_id in quest_data['completed']:
            quest = self.quest_manager.get_quest(quest_id)
            if quest:
                self.completed_quests.append(quest)
                
    def get_loot(self) -> List[dict]:
        """Zwraca łup z gracza (w przypadku śmierci)."""
        loot = []
    
        # Dodaj część złota do łupu
        if self.gold > 0:
            gold_drop = int(self.gold * 0.1)  # 10% złota
            if gold_drop > 0:
                loot.append({
                    'id': 'gold',
                    'amount': gold_drop
                })
    
        # Dodaj losowe przedmioty z ekwipunku
        if self.inventory and self.inventory.items:
            for item_id, quantity in self.inventory.items.items():
                # 10% szansa na upuszczenie każdego przedmiotu
                if random.random() < 0.1:
                    drop_quantity = min(quantity, random.randint(1, quantity))
                    loot.append({
                        'id': item_id,
                        'amount': drop_quantity
                    })
    
        return loot
    
    def initialize_quests(self, quest_manager):
        """Inicjalizuje system questów dla gracza."""
        self.quest_manager = quest_manager
        logger.info(f"Zainicjalizowano system questów dla gracza {self.name}")

    def accept_quest(self, quest_id: str) -> tuple[bool, str]:
        """Przyjmuje nowy quest."""
        if not self.quest_manager:
            return False, "System questów nie został zainicjalizowany!"
            
        if quest_id in [quest.id for quest in self.active_quests]:
            return False, "Ten quest jest już aktywny!"
            
        quest = self.quest_manager.get_quest(quest_id)
        if not quest:
            return False, "Nie znaleziono questa!"
            
        self.active_quests.append(quest)
        self.quest_log.append({
            'timestamp': time.time(),
            'type': 'quest_accepted',
            'quest_id': quest_id,
            'quest_name': quest.name
        })
        
        return True, f"Przyjęto quest: {quest.name}"

    def complete_quest(self, quest_id: str) -> tuple[bool, str]:
        """Kończy quest."""
        quest = next((q for q in self.active_quests if q.id == quest_id), None)
        if not quest:
            return False, "Ten quest nie jest aktywny!"
            
        self.active_quests.remove(quest)
        self.completed_quests.append(quest)
        self.quest_log.append({
            'timestamp': time.time(),
            'type': 'quest_completed',
            'quest_id': quest_id,
            'quest_name': quest.name
        })
        
        return True, f"Ukończono quest: {quest.name}!"

    def get_available_quests(self) -> List[str]:
        """Zwraca listę dostępnych questów."""
        if not self.quest_manager:
            return []
            
        return self.quest_manager.get_available_quests(self)

    def update_quest_progress(self, event_type: str, target_id: str, amount: int = 1):
        """Aktualizuje postęp questów."""
        if not self.quest_manager:
            return
            
        for quest in self.active_quests:
            if quest.check_objective(event_type, target_id):
                quest.update_progress(amount)
                if quest.is_completed():
                    self.complete_quest(quest.id)

    # Dodanie serializacji stanu gracza
    def serialize(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'active_quests': self.serialize_quests(),
            'completed_quests': [q.id for q in self.completed_quests],
            'quest_log': self.quest_log
        }