# inventory.py
from typing import Dict, Optional, List
from items import ItemManager
import logging

logger = logging.getLogger(__name__)

class Inventory:
    def __init__(self, capacity: int = 20):
        self.capacity = capacity
        self.items: Dict[str, int] = {}
        self.equipped_items: Dict[str, str] = {}
        self.item_manager = None
        
    def set_item_manager(self, item_manager: 'ItemManager'):
        """Ustawia referencję do ItemManagera."""
        if item_manager is None:
            raise ValueError("ItemManager nie może być None")
        self.item_manager = item_manager

    def add_item(self, item_id, quantity=1):
        """Adds an item to the inventory."""
        if len(self.items) >= self.capacity and item_id not in self.items:
            return False, "Ekwipunek jest pełny!"

        if item_id in self.items:
            self.items[item_id] += quantity
        else:
            self.items[item_id] = quantity
        
        item = self.item_manager.get_item(item_id)
        return True, f"Dodano {quantity} x {item.name}"

    def remove_item(self, item_id, quantity=1):
        """Removes an item from the inventory."""
        if item_id not in self.items:
            return False, "Nie znaleziono przedmiotu w ekwipunku."
        if self.items[item_id] < quantity:
            return False, "Nie masz wystarczającej ilości tego przedmiotu."
        
        item = self.item_manager.get_item(item_id)
        self.items[item_id] -= quantity
        if self.items[item_id] <= 0:
            del self.items[item_id]
        return True, f"{item.name}"

    def equip_item(self, item_id, player):
        """Ekwipuje przedmiot jako broń lub zbroję."""
        if item_id not in self.items:
            return False, "Nie masz tego przedmiotu!"

        item = self.item_manager.get_item(item_id)
        if item.type not in ["broń", "zbroja"]:
            return False, "Nie możesz założyć tego przedmiotu!"

        slot = "weapon" if item.type == "broń" else "armor"

        # Zdejmij poprzedni przedmiot, jeśli był założony
        if self.equipped[slot]:
            old_item = self.item_manager.get_item(self.equipped[slot])
            if item.type == "broń":
                player.strength -= old_item.properties.get("damage", 0)
            else:
                player.defense -= old_item.properties.get("defense", 0)

        # Załóż nowy przedmiot
        self.equipped[slot] = item_id
        if item.type == "broń":
            player.strength += item.properties.get("damage", 0)
        else:
            player.defense += item.properties.get("defense", 0)

        return True, f"Założono {item.name}!"

    def unequip_item(self, slot, player):
        """Zdejmuje przedmiot z danego slotu."""
        if not self.equipped[slot]:
            return False, f"Nie masz niczego założonego w slocie {slot}!"
        
        item = self.item_manager.get_item(self.equipped[slot])
        if item.type == "broń":
            player.strength -= item.properties.get("damage", 0)
        else:
            player.defense -= item.properties.get("defense", 0)
        
        self.equipped[slot] = None
        return True, f"Zdjęto {item.name}!"

    def show_inventory(self, player=None):
        """Wyświetla zawartość ekwipunku z interaktywnym menu."""
        while True:
            print("\n=== Ekwipunek ===")
            
            # Pokaż założone przedmioty
            print("\nZałożone przedmioty:")
            weapon = self.item_manager.get_item(self.equipped["weapon"]) if self.equipped["weapon"] else None
            armor = self.item_manager.get_item(self.equipped["armor"]) if self.equipped["armor"] else None
            print(f"Broń: {weapon.name if weapon else 'brak'}")
            print(f"Zbroja: {armor.name if armor else 'brak'}")

            # Pokaż przedmioty w ekwipunku
            if not self.items:
                print("\nEkwipunek jest pusty!")
            else:
                print("\nPrzedmioty w ekwipunku:")
                items_list = []  # Lista do numerowania przedmiotów
                for item_id, quantity in self.items.items():
                    item = self.item_manager.get_item(item_id)
                    equipped = ""
                    if item_id == self.equipped.get("weapon") or item_id == self.equipped.get("armor"):
                        equipped = " (założone)"
                    items_list.append((item_id, item, quantity))
                    print(f"{len(items_list)}. {item.name} x{quantity}{equipped}: {item.description}")

            # Menu akcji
            print("\nAkcje:")
            print("1. Załóż przedmiot")
            print("2. Zdejmij przedmiot")
            print("3. Użyj przedmiot")
            print("4. Wyrzuć przedmiot")
            print("5. Powrót")

            choice = input("\nWybierz akcję (1-5): ").strip()

            if choice == "1":  # Załóż przedmiot
                if not self.items:
                    print("Nie masz żadnych przedmiotów do założenia!")
                    continue
                    
                item_num = input("Wybierz numer przedmiotu do założenia (0 aby anulować): ")
                try:
                    item_num = int(item_num)
                    if item_num == 0:
                        continue
                    if 1 <= item_num <= len(items_list):
                        item_id, item, _ = items_list[item_num - 1]
                        if player:
                            success, message = self.equip_item(item_id, player)
                            print(message)
                    else:
                        print("Nieprawidłowy numer przedmiotu!")
                except ValueError:
                    print("Wprowadź poprawną liczbę!")

            elif choice == "2":  # Zdejmij przedmiot
                print("\nKtóry przedmiot chcesz zdjąć?")
                print("1. Broń")
                print("2. Zbroja")
                print("3. Anuluj")
                
                slot_choice = input("Wybierz slot (1-3): ").strip()
                if slot_choice == "1":
                    if player:
                        success, message = self.unequip_item("weapon", player)
                        print(message)
                elif slot_choice == "2":
                    if player:
                        success, message = self.unequip_item("armor", player)
                        print(message)

            elif choice == "3":  # Użyj przedmiot
                if not self.items:
                    print("Nie masz żadnych przedmiotów do użycia!")
                    continue
                    
                item_num = input("Wybierz numer przedmiotu do użycia (0 aby anulować): ")
                try:
                    item_num = int(item_num)
                    if item_num == 0:
                        continue
                    if 1 <= item_num <= len(items_list):
                        item_id, item, _ = items_list[item_num - 1]
                        if player:
                            success, message = self.use_item(item_id, player)
                            print(message)
                    else:
                        print("Nieprawidłowy numer przedmiotu!")
                except ValueError:
                    print("Wprowadź poprawną liczbę!")

            elif choice == "4":  # Wyrzuć przedmiot
                if not self.items:
                    print("Nie masz żadnych przedmiotów do wyrzucenia!")
                    continue
                    
                item_num = input("Wybierz numer przedmiotu do wyrzucenia (0 aby anulować): ")
                try:
                    item_num = int(item_num)
                    if item_num == 0:
                        continue
                    if 1 <= item_num <= len(items_list):
                        item_id, item, quantity = items_list[item_num - 1]
                        if quantity > 1:
                            amount = input(f"Ile sztuk chcesz wyrzucić? (max {quantity}): ")
                            try:
                                amount = int(amount)
                                if 1 <= amount <= quantity:
                                    success, message = self.remove_item(item_id, amount)
                                    print(f"Wyrzucono {amount}x {item.name}")
                                else:
                                    print("Nieprawidłowa ilość!")
                            except ValueError:
                                print("Wprowadź poprawną liczbę!")
                        else:
                            success, message = self.remove_item(item_id)
                            print(f"Wyrzucono {item.name}")
                    else:
                        print("Nieprawidłowy numer przedmiotu!")
                except ValueError:
                    print("Wprowadź poprawną liczbę!")

            elif choice == "5":  # Powrót
                break
            
            else:
                print("Nieprawidłowa opcja!")

    def use_item(self, item_id, player):
        """Używa przedmiotu i aplikuje jego efekty."""
        if item_id not in self.items:
            return False, "Nie masz tego przedmiotu!"

        item = self.item_manager.get_item(item_id)
        if item.type == "konsumpcyjny":
            if "healing" in item.properties:
                healing = item.properties["healing"]
                if player.health == player.max_health:
                    return False, "Masz już pełne zdrowie!"
                player.health = min(player.max_health, player.health + healing)
                success, msg = self.remove_item(item_id)
                if success:
                    return True, f"Użyto {item.name}. Przywrócono {healing} punktów zdrowia."
        return False, "Nie możesz użyć tego przedmiotu!"

    # Brak obsługi serializacji/deserializacji
    def serialize(self) -> dict:
        """Serializuje stan ekwipunku."""
        return {
            'items': self.items,
            'capacity': self.capacity,
            'equipped': self.equipped
        }

    def has_item(self, item_id: str) -> bool:
        """Sprawdza czy przedmiot jest w ekwipunku."""
        return item_id in self.items and self.items[item_id] > 0

    def can_add_item(self, item_id: str) -> bool:
        """Sprawdza czy można dodać przedmiot."""
        return len(self.items) < self.capacity or item_id in self.items