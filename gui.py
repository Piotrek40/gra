# gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, font, messagebox
from functools import partial
import sys
from game import GameEngine
from colorama import Fore, Style
from typing import Optional, Dict

class ModernGameGUI:
    def __init__(self, game_engine):
        if game_engine is None:
            raise ValueError("GameEngine nie może być None")
            
        self.game = game_engine
        self.root = tk.Tk()
        self.root.title("Gra RPG")
        
        # Dodać obsługę błędów
        self.error_handler = GUIErrorHandler()
        
        # Dodać system aktualizacji GUI
        self.update_interval = 100  # ms
        self.last_update = 0
        
        if not self.game:
            raise ValueError("Game engine nie został prawidłowo zainicjalizowany")
        
        if not hasattr(self.game, 'player') or not self.game.player:
            self.game.new_game("Bohater")  # Automatycznie twórz nową grę
        
        self.setup_window()
        # Ustaw referencję do głównego okna w game engine
        self.game.root = self.root
        self.setup_styles()
        self.setup_widgets()
        self.setup_output_redirect()
        self.setup_command_buttons()
        self.setup_bindings()
        
        # Upewnij się, że gra jest uruchomiona
        if not self.game.running:
            self.game.running = True
            # Rozpocznij nową grę jeśli nie ma aktywnej
            if not self.game.player:
                self.game.new_game("Bohater")
                
        # Wyświetl początkowy opis
        self.show_initial_description()

    def setup_window(self):
        """Inicjalizacja głównego okna z nowoczesnym wyglądem."""
        self.root = tk.Tk()
        self.root.title("Fantasy RPG")
        self.root.geometry("1200x800")
        
        # Ustawienie ciemnego motywu
        self.root.configure(bg='#1E1E1E')
        
        # Konfiguracja skalowania
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def setup_styles(self):
        """Konfiguracja stylów dla nowoczesnego wyglądu."""
        style = ttk.Style()
        style.theme_use('default')
        
        # Konfiguracja czcionek
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(size=10, family="Segoe UI")
        
        # Style dla przycisków
        style.configure('Modern.TButton',
            padding=10,
            background='#2D2D2D',
            foreground='white',
            font=('Segoe UI', 10))
            
        # Style dla ramek
        style.configure('Modern.TFrame',
            background='#1E1E1E')
            
        style.configure('Dark.TLabelframe',
            background='#2D2D2D',
            foreground='white')
            
        style.configure('Dark.TLabelframe.Label',
            background='#2D2D2D',
            foreground='white',
            font=('Segoe UI', 11, 'bold'))
        
    def setup_widgets(self):
        """Tworzenie i rozmieszczanie widgetów."""
        # Główny kontener
        self.main_container = ttk.Frame(self.root, style='Modern.TFrame')
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=3)

        # Panel statystyk (lewy)
        self.stats_frame = ttk.LabelFrame(
            self.main_container,
            text="Status Postaci",
            style='Dark.TLabelframe'
        )
        self.stats_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        
        # Panel gry (środkowy)
        self.game_frame = ttk.LabelFrame(
            self.main_container, 
            text="Świat Gry", 
            style='Dark.TLabelframe'
        )
        self.game_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        self.game_frame.grid_rowconfigure(0, weight=1)
        self.game_frame.grid_columnconfigure(0, weight=1)

        # Obszar tekstu gry z ulepszoną czcionką i kolorami
        self.game_text = scrolledtext.ScrolledText(
            self.game_frame,
            wrap=tk.WORD,
            bg='#1E1E1E',
            fg='#E0E0E0',
            font=('Consolas', 11),
            insertbackground='white',
            selectbackground='#404040',
            selectforeground='white'
        )
        self.game_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Panel komend (prawy)
        self.commands_frame = ttk.LabelFrame(
            self.main_container,
            text="Akcje",
            style='Dark.TLabelframe'
        )
        self.commands_frame.grid(row=0, column=2, sticky="nsew", padx=5)

        # Panel wprowadzania
        self.input_frame = ttk.Frame(self.main_container, style='Modern.TFrame')
        self.input_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        self.input_frame.grid_columnconfigure(0, weight=1)

        # Pole wprowadzania z ulepszoną stylistyką
        self.input_entry = ttk.Entry(
            self.input_frame,
            font=('Consolas', 11),
            style='Modern.TEntry'
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        # Przycisk wysyłania
        self.send_button = ttk.Button(
            self.input_frame,
            text="Wyślij",
            style='Modern.TButton',
            command=self.handle_input
        )
        self.send_button.grid(row=0, column=1)
        
    def setup_command_buttons(self):
        """Tworzenie przycisków komend z ikonami."""
        # Podstawowe komendy
        basic_commands_frame = ttk.LabelFrame(
            self.commands_frame,
            text="Podstawowe Akcje",
            style='Dark.TLabelframe'
        )
        basic_commands_frame.pack(fill=tk.X, padx=5, pady=5)

        base_commands = {
            "rozejrzyj się": "👀 Rozejrzyj się",
            "ekwipunek": "🎒 Ekwipunek",
            "status": "📊 Status",
            "handel": "💰 Handluj",
            "questy": "📜 Questy",
            "pomoc": "❓ Pomoc"
        }

        for cmd, label in base_commands.items():
            btn = ttk.Button(
                basic_commands_frame,
                text=label,
                style='Modern.TButton',
                command=partial(self.execute_command, cmd)
            )
            btn.pack(fill=tk.X, padx=2, pady=2)

        # Komendy z parametrami
        param_commands_frame = ttk.LabelFrame(
            self.commands_frame,
            text="Akcje Zaawansowane",
            style='Dark.TLabelframe'
        )
        param_commands_frame.pack(fill=tk.X, padx=5, pady=5)

        param_commands = {
            "idź": "🚶 Idź do...",
            "porozmawiaj z": "💬 Porozmawiaj...",
            "atakuj": "⚔️ Atakuj...",
            "podnieś": "⬆️ Podnieś...",
            "użyj": "🔨 Użyj..."
        }

        for cmd, label in param_commands.items():
            btn = ttk.Button(
                param_commands_frame,
                text=label,
                style='Modern.TButton',
                command=partial(self.prompt_parameter, cmd)
            )
            btn.pack(fill=tk.X, padx=2, pady=2)

        # Panel statystyk
        self.setup_stats_panel()
        
    def handle_input(self):
        """Obsługuje wprowadzanie komend przez użytkownika."""
        command = self.input_entry.get().strip()
        if command:
            self.game_text.config(state='normal')
            self.game_text.insert(tk.END, f"\n> {command}\n", 'command')
            
            # Przekazanie komendy do silnika gry
            result = self.game.handle_command(command)
            
            # Wyświetlenie rezultatu
            if result:
                self.game_text.insert(tk.END, f"{result}\n")
            
            self.game_text.config(state='disabled')
            self.input_entry.delete(0, tk.END)
            
            # Aktualizacja statystyk
            self.update_stats()
            
            # Przewiń do końca
            self.game_text.see(tk.END)

    def execute_command(self, command):
        """Wykonuje predefiniowaną komendę."""
        if command == "użyj":
            self.prompt_parameter("użyj")
        elif command == "załóż":
            self.prompt_parameter("załóż")
        elif command == "zdejmij":
            self.prompt_parameter("zdejmij")
        
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, command)
        self.handle_input()
        
    def show_initial_description(self):
        """Wyświetla początkowy opis świata."""
        location = self.game.world.get_location(self.game.player.current_location)
        self.game_text.config(state='normal')
        self.game_text.insert(tk.END, f"\nWitaj w {location.name}!\n")
        self.game_text.insert(tk.END, f"{location.description}\n")
        self.game_text.config(state='disabled')

    def prompt_parameter(self, base_command):
        """Wyświetla okno dialogowe do wprowadzenia parametru komendy."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Wprowadź parametr")
        dialog.geometry("300x150")
    
        label = ttk.Label(dialog, text=f"Wprowadź parametr dla komendy '{base_command}':")
        label.pack(pady=10)
    
        entry = ttk.Entry(dialog)
        entry.pack(pady=10)
    
        def submit():
            param = entry.get().strip()
            if param:
                self.input_entry.delete(0, tk.END)
                self.input_entry.insert(0, f"{base_command} {param}")
                self.handle_input()
            dialog.destroy()
    
        button = ttk.Button(dialog, text="OK", command=submit)
        button.pack(pady=10)

    def setup_bindings(self):
        """Konfiguruje powiązania klawiszy."""
        self.input_entry.bind('<Return>', lambda e: self.handle_input())
        self.root.bind('<Control-l>', lambda e: self.game_text.delete(1.0, tk.END))
        
    def setup_stats_panel(self):
        """Tworzenie panelu statystyk z paskami postępu."""
        self.stats_labels = {}
        
        if not self.game.player:
            logger.error("Nie można utworzyć panelu statystyk - brak gracza")
            return
            
        # Tworzenie statystyk z paskami postępu
        stats = [
            ("Gracz", self.game.player.name),
            ("Poziom", f"{self.game.player.level}"),
            ("Exp", self.create_progress_bar("exp")),
            ("Zdrowie", self.create_progress_bar("health")),
            ("Siła", f"{self.game.player.stats.strength}"),
            ("Obrona", f"{self.game.player.stats.defense}"),
            ("Złoto", f"{self.game.player.gold}")
        ]

        for label, value in stats:
            frame = ttk.Frame(self.stats_frame, style='Modern.TFrame')
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            ttk.Label(
                frame,
                text=label + ":",
                style='Dark.TLabelframe.Label'
            ).pack(side=tk.LEFT, padx=5)
            
            if isinstance(value, tk.Widget):
                value.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
                self.stats_labels[label] = value
            else:
                value_label = ttk.Label(
                    frame,
                    text=value,
                    style='Dark.TLabelframe.Label'
                )
                value_label.pack(side=tk.RIGHT, padx=5)
                self.stats_labels[label] = value_label

    def create_progress_bar(self, stat_type):
        """Tworzy pasek postępu dla danej statystyki."""
        if stat_type == "exp":
            next_level = self.game.player.experience_to_next_level
            value = (self.game.player.experience / next_level) * 100
            max_value = 100
        elif stat_type == "health":
            value = (self.game.player.stats.health / self.game.player.stats.max_health) * 100
            max_value = 100
        else:
            value = 0
            max_value = 100
            
        progress_bar = ttk.Progressbar(self.stats_frame, length=150, maximum=max_value, value=value)
        return progress_bar
    
    def create_command_buttons(self):
        """Tworzy przyciski komend."""
        commands = [
            ("Status", "status"),
            ("Ekwipunek", "ekwipunek"),
            ("Questy", "questy"),
            ("Rozejrzyj się", "rozejrzyj się")
        ]
        
        for label, command in commands:
            btn = ttk.Button(
                self.command_frame,
                text=label,
                command=lambda cmd=command: self.execute_command(cmd)
            )
            btn.pack(fill=tk.X, padx=5, pady=2)

    def update_stats(self):
        """Aktualizacja wyświetlanych statystyk."""
        self.stats_labels['Poziom'].config(text=f"{self.game.player.level}")
        self.stats_labels['Exp'].config(
            value=(self.game.player.experience / (self.game.player.level * 100)) * 100
        )
        stats = {
            "Poziom": f"{self.game.player.level}",
            "Exp": (self.game.player.experience / (self.game.player.level * 100)) * 100,
            "Zdrowie": (self.game.player.stats.health / self.game.player.stats.max_health) * 100,
            "Siła": f"{self.game.player.stats.strength}",
            "Obrona": f"{self.game.player.stats.defense}",
            "Zręczność": f"{self.game.player.stats.agility}",
            "Inteligencja": f"{self.game.player.stats.intelligence}",
            "Stamina": f"{self.game.player.stats.stamina}/{self.game.player.stats.max_stamina}",
            "Mana": f"{self.game.player.stats.mana}/{self.game.player.stats.max_mana}",
            "Złoto": f"{self.game.player.gold}"
        }
        
        for stat, value in stats.items():
            if stat in self.stats_labels:
                if isinstance(self.stats_labels[stat], ttk.Progressbar):
                    self.stats_labels[stat]['value'] = value
                else:
                    self.stats_labels[stat].configure(text=value)

    def setup_output_redirect(self):
        """Przekierowanie wyjścia do okna gry z kolorami."""
        class TextRedirector:
            def __init__(self, widget, color=None):
                self.widget = widget
                self.color = color

            def write(self, str):
                if self.color:
                    self.widget.insert(tk.END, str, self.color)
                else:
                    self.widget.insert(tk.END, str)
                self.widget.see(tk.END)
            
            def flush(self):
                pass

        sys.stdout = TextRedirector(self.game_text)

    def start(self):
        """Uruchamia interfejs graficzny."""
        self.root.mainloop()

def main():
    """Funkcja główna uruchamiająca grę."""
    game = GameEngine()
    gui = ModernGameGUI(game)
    print("Witaj w Fantasy RPG!")
    game.player.look_around(game.world, game.character_manager)
    gui.start()

if __name__ == "__main__":
    main()