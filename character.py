import json
import random
from typing import Dict
from entities import Entity
from inventory import Inventory
import logging

logger = logging.getLogger(__name__)

class Character(Entity):
    def __init__(self, char_id: str, data: dict = None):
        super().__init__(char_id, data)
        self.behavior = data.get('behavior', 'neutral')
        self.dialogue = data.get('dialogue', None)
        self.inventory = Inventory()

class Merchant(Character):
    def __init__(self, char_id, data):
        super().__init__(char_id, data)
        self.prices = data.get('prices', {})  # Ceny sprzedaży
        self.buy_multiplier = 0.5  # Mnożnik ceny przy skupie (50% wartości)

    def get_sell_price(self, item_id):
        """Zwraca cenę sprzedaży przedmiotu."""
        return self.prices.get(item_id, 50)  # Domyślna cena 50 złota

    def get_buy_price(self, item_id):
        """Zwraca cenę skupu przedmiotu."""
        return int(self.get_sell_price(item_id) * self.buy_multiplier)

    def sell_item(self, item_id, player, items):
        """Sprzedaje przedmiot graczowi."""
        if item_id not in self.inventory:
            return False, "Nie mam tego przedmiotu na sprzedaż!"

        price = self.get_sell_price(item_id)
        if player.gold < price:
            return False, f"Nie masz wystarczająco złota! (Potrzeba: {price})"

        success, message = player.inventory.add_item(item_id)
        if success:
            player.gold -= price
            self.inventory.remove(item_id)
            return True, f"Kupiłeś {items.get_item(item_id).name} za {price} złota!"
        return False, message

    def buy_item(self, item_id, player, items):
        """Skupuje przedmiot od gracza."""
        if item_id not in player.inventory.items:
            return False, "Nie masz tego przedmiotu!"

        price = self.get_buy_price(item_id)
        success, message = player.inventory.remove_item(item_id)
        if success:
            player.gold += price
            self.inventory.append(item_id)
            return True, f"Sprzedałeś {items.get_item(item_id).name} za {price} złota!"
        return False, message

    def show_inventory(self, items):
        """Wyświetla towary na sprzedaż."""
        print(f"\n=== Towary {self.name} ===")
        if not self.inventory:
            print("Nie mam nic na sprzedaż!")
            return

        for item_id in self.inventory:
            item = items.get_item(item_id)
            price = self.get_sell_price(item_id)
            print(f"- {item.name}: {price} złota - {item.description}")

class Enemy(Character):
    def __init__(self, char_id, data):
        super().__init__(char_id, data)
        self.is_enemy = True
        self.loot_table = data.get('loot_table', {})  # Słownik {item_id: szansa_na_drop}

    def get_loot(self):
        """Zwraca listę przedmiotów z przeciwnika po jego śmierci."""
        loot = []
        # Sprawdź każdy przedmiot z podstawowego inventory
        if self.inventory:
            loot.extend(self.inventory)
        
        # Sprawdź przedmioty z loot_table (jeśli są)
        for item_id, chance in self.loot_table.items():
            if random.random() < chance:
                loot.append(item_id)
        
        return loot

class CharacterManager:
    def __init__(self, data_file='data/characters.json'):
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)['characters']
        self.characters: Dict[str, Character] = {}
        for char_id, char_data in data.items():
            if char_data.get('is_enemy', False):
                self.characters[char_id] = Enemy(char_id, char_data)
            elif char_data.get('prices'):
                self.characters[char_id] = Merchant(char_id, char_data)
            else:
                self.characters[char_id] = Character(char_id, char_data)

    def get_characters_in_location(self, location_id, include_enemies=False):
        return [char for char in self.characters.values() if char.location == location_id and (include_enemies or not char.is_enemy)]

    def get_character_by_name(self, name):
        for char in self.characters.values():
            if char.name.lower() == name.lower():
                return char
        return None