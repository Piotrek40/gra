import json

class Item:
    def __init__(self, item_id, data):
        self.id = item_id
        self.name = data['name']
        self.description = data['description']
        self.type = data['type']
        # Zapisujemy wszystkie pozostałe właściwości
        self.properties = {k: v for k, v in data.items() 
                         if k not in ['name', 'description', 'type']}
        print(f"DEBUG Item: Utworzono przedmiot: {self.name}, typ: {self.type}, właściwości: {self.properties}")  # Debug

class ItemManager:
    def __init__(self, data_file='data/items.json'):
        self._items = {}  # Słownik przechowujący obiekty Item
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)['items']
            for item_id, item_data in data.items():
                self._items[item_id] = Item(item_id, item_data)
                print(f"DEBUG ItemManager: Załadowano przedmiot: {item_id}")  # Debug

    def get_item(self, item_id):
        """Zwraca obiekt przedmiotu na podstawie jego ID."""
        item = self._items.get(item_id)
        print(f"DEBUG ItemManager: Pobrano przedmiot: {item_id}, znaleziono: {item.name if item else None}")  # Debug
        return item

    def get_item_id_by_name(self, item_name):
        """Zwraca ID przedmiotu na podstawie jego nazwy."""
        item_name = item_name.lower().strip()
        print(f"DEBUG ItemManager: Szukam przedmiotu o nazwie: {item_name}")  # Debug
        for item_id, item in self._items.items():
            if item.name.lower().strip() == item_name:
                print(f"DEBUG ItemManager: Znaleziono przedmiot: {item_id}")  # Debug
                return item_id
        print(f"DEBUG ItemManager: Nie znaleziono przedmiotu o nazwie: {item_name}")  # Debug
        return None