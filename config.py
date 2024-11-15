# config.py
import os
import json
from typing import Dict, Any

class GameConfig:
    """Scentralizowana konfiguracja gry."""
    def __init__(self):
        self.config_dir = 'data'
        self.config: Dict[str, Any] = {
            'game_title': 'Fantasy RPG',
            'version': '1.0.0',
            'window_size': (1200, 800),
            'save_dir': 'saves',
            'data_files': {
                'items': 'items.json',
                'characters': 'characters.json',
                'quests': 'quests.json',
                'skills': 'skills.json',
                'world': 'world.json',
                'dialogues': 'dialogues.json'
            },
            'game_settings': {
                'difficulty': 'normal',
                'auto_save': True,
                'auto_save_interval': 300,  # w sekundach
                'music_volume': 0.7,
                'sfx_volume': 1.0,
                'fullscreen': False,
                'language': 'pl'
            },
            'gameplay': {
                'starting_location': 'miasto_startowe',
                'starting_gold': 100,
                'starting_health': 100,
                'exp_multiplier': 1.0,
                'loot_multiplier': 1.0,
                'combat': {
                    'crit_chance_base': 0.15,
                    'dodge_chance_base': 0.10,
                    'defense_bonus_base': 5
                }
            },
            'gui': {
                'theme': 'dark',
                'colors': {
                    'bg_dark': '#1E1E1E',
                    'bg_medium': '#2D2D2D',
                    'text_light': '#E0E0E0',
                    'accent': '#17a2b8',
                    'success': '#28a745',
                    'warning': '#ffc107',
                    'error': '#dc3545',
                    'health': '#dc3545',
                    'mana': '#007bff',
                    'exp': '#17a2b8'
                },
                'fonts': {
                    'main': ('Segoe UI', 10),
                    'header': ('Segoe UI', 12, 'bold'),
                    'monospace': ('Consolas', 11)
                }
            }
        }
        self.load_config()

    def load_config(self):
        """Ładuje konfigurację z pliku."""
        config_path = os.path.join(self.config_dir, 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
            except Exception as e:
                print(f"Błąd podczas ładowania konfiguracji: {e}")

    def save_config(self):
        """Zapisuje konfigurację do pliku."""
        config_path = os.path.join(self.config_dir, 'config.json')
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd podczas zapisywania konfiguracji: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Pobiera wartość z konfiguracji."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Ustawia wartość w konfiguracji."""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save_config()

    # Dodanie walidacji konfiguracji
    def validate_config(self) -> bool:
        required_settings = ['version', 'game_settings', 'gui']
        return all(setting in self.config for setting in required_settings)

# Singleton konfiguracji
game_config = GameConfig()