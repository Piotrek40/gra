# save_load.py

from typing import List, Optional, Tuple, Dict, Any, Union, Set
import json
import os
import time
import zlib
import base64
import logging
from pathlib import Path
from dataclasses import dataclass
import hashlib
from exceptions import (
    SaveLoadError, SaveFileCorruptedError, 
    SaveVersionMismatchError, GameStateError
)
from config import game_config

logger = logging.getLogger(__name__)

@dataclass
class SaveMetadata:
    """Reprezentuje metadane zapisu gry."""
    name: str
    timestamp: float
    version: str
    player_name: str
    level: int
    play_time: float

class SaveManager:
    """Zarządza zapisem i odczytem stanu gry."""
    
    def __init__(self, save_dir: str = 'saves'):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        self.current_save: Optional[str] = None
        self.auto_backup = game_config.get('game_settings.auto_backup', True)
        self.compression_level = game_config.get('game_settings.save_compression_level', 6)
        self.max_autosaves = game_config.get('game_settings.max_autosaves', 3)
        self.save_directory = Path("saves")
        self.save_directory.mkdir(exist_ok=True)
        self.compression_level = 9
        self.max_saves = 100  # Dodać limit zapisów
        
    def save_game(self, game_state: dict, save_name: str = None) -> Tuple[bool, str]:
        """Zapisuje stan gry do pliku."""
        try:
            # Jeśli nazwa nie została podana, użyj timestampa
            if not save_name:
                save_name = f"autosave_{int(time.time())}"
            
            save_path = self.save_dir / f"{save_name}.sav"
            
            # Przygotuj dane do zapisu
            save_data = self._prepare_save_data(game_state)
            
            # Zapisz plik
            self._write_save_file(save_path, save_data)
            
            # Aktualizuj metadane
            self._update_save_metadata(save_name, save_data)
            
            # Zarządzaj automatycznymi zapisami
            if save_name.startswith('autosave'):
                self._manage_autosaves()
            
            # Utwórz kopię zapasową jeśli potrzeba
            if self.auto_backup and not save_name.startswith('autosave'):
                self._create_backup(save_data)
                
            logger.info(f"Gra została zapisana do: {save_path}")
            return True, "Gra została pomyślnie zapisana!"
            
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania gry: {e}")
            return False, f"Nie udało się zapisać gry: {str(e)}"

    def load_game(self, save_name: str) -> Tuple[bool, str, Optional[dict]]:
        """Wczytuje stan gry z pliku."""
        try:
            save_path = self.save_dir / f"{save_name}.sav"
            if not save_path.exists():
                return False, "Nie znaleziono pliku zapisu!", None
                
            # Wczytaj i zdekoduj dane
            save_data = self._read_save_file(save_path)
            
            # Sprawdź integralność danych
            if not self._verify_save_integrity(save_data):
                raise SaveFileCorruptedError("Plik zapisu jest uszkodzony!")
                
            # Sprawdź kompatybilność wersji
            if not self._check_version_compatibility(save_data['metadata']['version']):
                raise SaveVersionMismatchError("Niekompatybilna wersja zapisu!")
                
            # Ustaw aktualny zapis
            self.current_save = save_name
            
            logger.info(f"Wczytano grę z: {save_path}")
            return True, "Gra została pomyślnie wczytana!", save_data['game_state']
            
        except SaveLoadError as e:
            logger.error(f"Błąd podczas wczytywania gry: {e}")
            return False, str(e), None
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas wczytywania gry: {e}")
            return False, f"Nie udało się wczytać gry: {str(e)}", None

    def _prepare_save_data(self, game_state: dict) -> dict:
        """Przygotowuje dane do zapisu."""
        # Utwórz metadane
        metadata = {
            'version': game_config.get('version'),
            'timestamp': time.time(),
            'player_name': game_state['player']['name'],
            'player_level': game_state['player']['level'],
            'location': game_state['player']['current_location'],
            'playtime': game_state['game_time'],
            'save_name': game_state.get('save_name', 'Unnamed Save'),
        }
        
        # Skompresuj stan gry
        compressed_state = self._compress_data(game_state)
        
        # Oblicz checksum
        checksum = self._calculate_checksum(compressed_state)
        metadata['checksum'] = checksum
        
        return {
            'metadata': metadata,
            'game_state': compressed_state
        }

    def _write_save_file(self, save_path: Path, save_data: dict):
        """Zapisuje dane do pliku."""
        try:
            with save_path.open('w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
        except Exception as e:
            raise SaveLoadError(f"Nie można zapisać pliku: {e}")

    def _read_save_file(self, save_path: Path) -> dict:
        """Wczytuje dane z pliku."""
        try:
            with save_path.open('r', encoding='utf-8') as f:
                save_data = json.load(f)
                
            # Zdekompresuj stan gry
            save_data['game_state'] = self._decompress_data(save_data['game_state'])
            return save_data
            
        except json.JSONDecodeError:
            raise SaveFileCorruptedError("Plik zapisu jest uszkodzony!")
        except Exception as e:
            raise SaveLoadError(f"Nie można wczytać pliku: {e}")

    def _compress_data(self, data: dict) -> str:
        """Kompresuje dane gry."""
        try:
            json_str = json.dumps(data)
            compressed = zlib.compress(json_str.encode(), self.compression_level)
            return base64.b64encode(compressed).decode()
        except Exception as e:
            raise SaveLoadError(f"Błąd kompresji danych: {e}")

    def _decompress_data(self, compressed_data: str) -> dict:
        """Dekompresuje dane gry."""
        try:
            compressed = base64.b64decode(compressed_data)
            json_str = zlib.decompress(compressed).decode()
            return json.loads(json_str)
        except Exception as e:
            raise SaveLoadError(f"Błąd dekompresji danych: {e}")

    def _calculate_checksum(self, data: str) -> str:
        """Oblicza sumę kontrolną danych."""
        return hashlib.sha256(data.encode()).hexdigest()

    def _verify_save_integrity(self, save_data: dict) -> bool:
        """Sprawdza integralność pliku zapisu."""
        stored_checksum = save_data['metadata']['checksum']
        calculated_checksum = self._calculate_checksum(save_data['game_state'])
        return stored_checksum == calculated_checksum

    def _check_version_compatibility(self, save_version: str) -> bool:
        """Sprawdza kompatybilność wersji zapisu."""
        current_version = game_config.get('version')
        save_major_version = int(save_version.split('.')[0])
        current_major_version = int(current_version.split('.')[0])
        return save_major_version == current_major_version

    def _create_backup(self, save_data: dict):
        """Tworzy kopię zapasową zapisu."""
        try:
            backup_dir = self.save_dir / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = int(time.time())
            backup_path = backup_dir / f"backup_{timestamp}.sav"
            
            self._write_save_file(backup_path, save_data)
            logger.info(f"Utworzono kopię zapasową: {backup_path}")
            
            # Usuń stare kopie zapasowe
            self._cleanup_old_backups()
            
        except Exception as e:
            logger.error(f"Nie udało się utworzyć kopii zapasowej: {e}")

    def _manage_autosaves(self):
        """Zarządza automatycznymi zapisami."""
        autosaves = sorted([
            f for f in self.save_dir.glob("autosave_*.sav")
        ], key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Usuń najstarsze autosave'y jeśli przekroczono limit
        while len(autosaves) > self.max_autosaves:
            autosave_to_remove = autosaves.pop()
            try:
                autosave_to_remove.unlink()
                logger.info(f"Usunięto stary autosave: {autosave_to_remove}")
            except Exception as e:
                logger.error(f"Nie udało się usunąć autosave'a: {e}")

    def _cleanup_old_backups(self):
        """Usuwa stare kopie zapasowe."""
        backup_dir = self.save_dir / 'backups'
        if not backup_dir.exists():
            return
            
        max_backups = game_config.get('game_settings.max_backups', 5)
        backups = sorted([
            f for f in backup_dir.glob("backup_*.sav")
        ], key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Usuń najstarsze kopie zapasowe
        for backup in backups[max_backups:]:
            try:
                backup.unlink()
                logger.info(f"Usunięto starą kopię zapasową: {backup}")
            except Exception as e:
                logger.error(f"Nie udało się usunąć kopii zapasowej: {e}")

    def get_save_list(self) -> List[SaveMetadata]:
        """Zwraca listę dostępnych zapisów."""
        saves = []
        for save_path in self.save_dir.glob("*.sav"):
            try:
                with save_path.open('r', encoding='utf-8') as f:
                    save_data = json.load(f)
                    metadata = SaveMetadata(**save_data['metadata'])
                    saves.append(metadata)
            except Exception as e:
                logger.error(f"Błąd podczas czytania metadanych zapisu {save_path}: {e}")
                
        return sorted(saves, key=lambda x: x.timestamp, reverse=True)

    def delete_save(self, save_name: str) -> Tuple[bool, str]:
        """Usuwa plik zapisu."""
        try:
            save_path = self.save_dir / f"{save_name}.sav"
            if not save_path.exists():
                return False, "Nie znaleziono pliku zapisu!"
                
            save_path.unlink()
            logger.info(f"Usunięto zapis: {save_path}")
            return True, "Zapis został pomyślnie usunięty!"
            
        except Exception as e:
            logger.error(f"Błąd podczas usuwania zapisu: {e}")
            return False, f"Nie udało się usunąć zapisu: {str(e)}"

    def rename_save(self, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Zmienia nazwę pliku zapisu."""
        try:
            old_path = self.save_dir / f"{old_name}.sav"
            new_path = self.save_dir / f"{new_name}.sav"
            
            if not old_path.exists():
                return False, "Nie znaleziono pliku zapisu!"
                
            if new_path.exists():
                return False, "Plik o podanej nazwie już istnieje!"
                
            old_path.rename(new_path)
            
            # Aktualizuj metadane
            with new_path.open('r', encoding='utf-8') as f:
                save_data = json.load(f)
                save_data['metadata']['save_name'] = new_name
                
            with new_path.open('w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4)
                
            logger.info(f"Zmieniono nazwę zapisu z {old_name} na {new_name}")
            return True, "Nazwa zapisu została pomyślnie zmieniona!"
            
        except Exception as e:
            logger.error(f"Błąd podczas zmiany nazwy zapisu: {e}")
            return False, f"Nie udało się zmienić nazwy zapisu: {str(e)}"

    # Dodanie walidacji wersji plików zapisu
    def _validate_save_version(self, version: str) -> bool:
        try:
            major, minor = map(int, version.split('.')[:2])
            current_major, current_minor = map(int, game_config.get('version').split('.')[:2])
            return major == current_major
        except ValueError:
            return False

    # Dodać walidację stanu gry przed zapisem
    def validate_game_state(self, state: dict) -> bool:
        """Sprawdza czy stan gry jest kompletny i spójny."""
        required_keys = ['player', 'world', 'quests', 'inventory']
        return all(key in state for key in required_keys)

    def validate_save_data(self, save_data: dict) -> bool:
        """Walidacja danych zapisu."""
        required_fields = ['metadata', 'game_state']
        if not all(field in save_data for field in required_fields):
            return False
        return True