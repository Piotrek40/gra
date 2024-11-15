# main.py
import sys
import argparse
import logging
from typing import Optional
import tkinter as tk
from tkinter import messagebox
from config import game_config
from game import GameEngine
from gui import ModernGameGUI
from interface import GameInterface
from entities import Entity
from player import Player
from combat import CombatSystem
from world import World
from character import CharacterManager
from items import ItemManager
from quests import QuestManager

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Utwórz logger dla głównego modułu
logger = logging.getLogger(__name__)

# Ustaw poziom logowania dla innych modułów
logging.getLogger('game').setLevel(logging.INFO)
logging.getLogger('player').setLevel(logging.INFO)
logging.getLogger('world').setLevel(logging.INFO)
logging.getLogger('combat').setLevel(logging.INFO)

class GameLauncher:
    """Klasa odpowiedzialna za uruchomienie gry w odpowiednim trybie."""
    
    def __init__(self, args=None):
        self.args = args if args is not None else {}
        self.game_engine = None
        self.gui = None
        self.interface = None

    def initialize_game(self):
        try:
            logger.info("Inicjalizacja silnika gry...")
            self.game_engine = GameEngine()
            if not self.game_engine.new_game("Bohater"):
                raise RuntimeError("Nie udało się utworzyć nowej gry")
            logger.info("Inicjalizacja zakończona pomyślnie")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji gry: {e}", exc_info=True)
            return False

    def start_gui_mode(self):
        """Uruchamia grę w trybie graficznym."""
        try:
            logger.info("Uruchamianie trybu GUI...")
            if not self.gui:
                self.gui = ModernGameGUI(self.game_engine)
            # Ustaw stan gry przed uruchomieniem GUI
            self.game_engine.running = True
            self.gui.start()
            
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania GUI: {e}", exc_info=True)
            self.show_error_dialog("Błąd uruchamiania", 
                                "Wystąpił błąd podczas uruchamiania interfejsu graficznego.")
    
    def start_console_mode(self):
        """Uruchamia grę w trybie konsolowym."""
        try:
            logger.info("Uruchamianie trybu konsolowego...")
            if not self.interface:
                self.interface = GameInterface()
            self.game_engine.start_game()
            
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania trybu konsolowego: {e}", exc_info=True)
            print("Wystąpił błąd podczas uruchamiania gry.")

    def show_error_dialog(self, title: str, message: str):
        """Wyświetla okno dialogowe z błędem."""
        root = tk.Tk()
        root.withdraw()
        tk.messagebox.showerror(title, message)
        root.destroy()

def parse_arguments():
    """Parsuje argumenty wiersza poleceń."""
    parser = argparse.ArgumentParser(description='Fantasy RPG Game')
    parser.add_argument(
        '--mode',
        choices=['gui', 'console'],
        default='gui',
        help='Tryb uruchomienia gry (gui lub console)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Włącza tryb debug'
    )
    parser.add_argument(
        '--config',
        help='Ścieżka do alternatywnego pliku konfiguracyjnego'
    )
    return parser.parse_args()

# Dodanie obsługi wyjątków w głównej pętli
def main():
    try:
        args = parse_arguments()
        launcher = GameLauncher(args)  # Przekazujemy argumenty
        if not launcher.initialize_game():
            logger.error("Nie udało się zainicjalizować gry")
            sys.exit(1)
        
        if args.mode == 'gui':
            launcher.start_gui_mode()
        else:
            launcher.start_console_mode()
            
    except Exception as e:
        logger.critical(f"Krytyczny błąd: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()