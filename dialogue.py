# dialogue.py
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    
import logging
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

class DialogueManager:
    def __init__(self, interface):
        self.interface = interface
        self.current_dialog = None
        self.dialog_history = []
        self.dialogues = {}
        self.active_dialogues = {}
        self.load_dialogues()
        self.gui_available = GUI_AVAILABLE
        
    def start_dialog(self, npc, player):
        """Rozpoczyna dialog z NPC."""
        dialog = Dialog(npc, player, self.interface)
        self.current_dialog = dialog
        return dialog.start()

    def load_dialogues(self):
        # implementacja...
        pass

class Dialog:
    def __init__(self, npc, player, interface):
        self.npc = npc
        self.player = player
        self.interface = interface
        self.dialog_options = []
        self.quest_options = []

    def start(self):
        """Rozpoczyna dialog i zwraca pierwsze opcje."""
        # Przywitanie
        self.interface.show_message(f"\n{self.npc.name}: {random.choice(self.npc.dialogues)}", "dialog")
        
        # Przygotuj opcje dialogowe
        self.prepare_dialog_options()
        
        # Pokaż dostępne opcje
        self.show_options()

    def prepare_dialog_options(self):
        """Przygotowuje dostępne opcje dialogowe."""
        self.dialog_options = []
        
        # Podstawowe opcje
        self.dialog_options.append(("Jak się masz?", self.general_chat))
        
        # Opcje handlu jeśli NPC jest kupcem
        if isinstance(self.npc, Merchant):
            self.dialog_options.append(("Pokaż mi swoje towary", self.start_trade))
        
        # Opcje questów
        available_quests = [quest for quest in self.player.quest_manager.get_available_quests(self.player, self.npc.id)
                          if quest.giver == self.npc.id]
        if available_quests:
            self.quest_options = available_quests
            self.dialog_options.append(("Masz jakieś zadania?", self.show_quests))
        
        # Opcja zakończenia
        self.dialog_options.append(("Do widzenia", self.end_dialog))

    def show_options(self):
        """Wyświetla dostępne opcje dialogowe."""
        self.interface.show_message("\nDostępne opcje:", "system")
        for i, (option, _) in enumerate(self.dialog_options, 1):
            self.interface.show_message(f"{i}. {option}", "dialog")

    def handle_choice(self, choice):
        """Obsługuje wybór opcji przez gracza."""
        try:
            choice = int(choice)
            if 1 <= choice <= len(self.dialog_options):
                option, handler = self.dialog_options[choice - 1]
                handler()
            else:
                self.interface.show_message("Nieprawidłowy wybór.", "error")
        except ValueError:
            self.interface.show_message("Wprowadź numer opcji.", "error")

    def general_chat(self):
        """Obsługuje ogólną rozmowę."""
        response = random.choice([
            "Wszystko w porządku, dziękuję za pytanie.",
            "Bywało lepiej, ale nie narzekam.",
            "Interesujące czasy nastały...",
            "Mam sporo pracy ostatnio."
        ])
        self.interface.show_message(f"\n{self.npc.name}: {response}", "dialog")
        self.show_options()

    def start_trade(self):
        """Rozpoczyna handel z kupcem."""
        if isinstance(self.npc, Merchant):
            self.interface.show_trade_menu(self.npc, self.player)
        self.show_options()

    def show_quests(self):
        """Pokazuje dostępne questy."""
        if self.quest_options:
            self.interface.show_message("\nDostępne zadania:", "quest")
            for i, quest in enumerate(self.quest_options, 1):
                self.interface.show_message(f"{i}. {quest.name} - {quest.description}", "quest")
                
            self.interface.show_message("\nWprowadź numer zadania, które chcesz przyjąć (0 aby wrócić):", "system")
            return "quest_selection"
        else:
            self.interface.show_message(f"\n{self.npc.name}: Nie mam obecnie żadnych zadań dla ciebie.", "dialog")
            self.show_options()

    def handle_quest_selection(self, choice):
        """Obsługuje wybór questa przez gracza."""
        try:
            choice = int(choice)
            if choice == 0:
                self.show_options()
                return
                
            if 1 <= choice <= len(self.quest_options):
                quest = self.quest_options[choice - 1]
                success, message = self.player.quest_manager.start_quest(quest.id, self.player)
                self.interface.show_message(message, "quest" if success else "error")
            else:
                self.interface.show_message("Nieprawidłowy wybór.", "error")
        except ValueError:
            self.interface.show_message("Wprowadź numer zadania.", "error")
        
        self.show_options()

    def end_dialog(self):
        """Kończy dialog."""
        self.interface.show_message(f"\n{self.npc.name}: Do zobaczenia!", "dialog")
        return "end"

    # Dodanie obsługi przerwanych dialogów
    def handle_interrupted_dialogue(self):
        self.interface.show_message("Dialog został przerwany.", "system")
        self.cleanup_dialogue_state()

if GUI_AVAILABLE:
    class DialogGUI(tk.Toplevel):
        def __init__(self, parent, dialogue, on_close=None):
            super().__init__(parent)
            self.dialogue = dialogue
            self.on_close = on_close
            self.title("Dialog")
            self.setup_gui()
            
            self.dialog_text = tk.Text(self, height=10, width=50)
            self.dialog_text.pack(pady=10)
            
            self.options_frame = ttk.Frame(self)
            self.options_frame.pack(pady=10)
            
            self.update_dialog()
            
            self.option_buttons = []

        def setup_gui(self):
            # Implementacja GUI dialogu
            pass

        def add_text(self, text, tag=None):
            """Dodaje tekst do okna dialogowego."""
            self.dialog_text.config(state='normal')
            self.dialog_text.insert(tk.END, text + '\n', tag)
            self.dialog_text.config(state='disabled')
            self.dialog_text.see(tk.END)
            
        def update_options(self, options):
            """Aktualizuje dostępne opcje dialogowe."""
            # Usuń stare przyciski
            for button in self.option_buttons:
                button.destroy()
            self.option_buttons.clear()
            
            # Dodaj nowe przyciski
            for text, handler in options:
                btn = ttk.Button(
                    self.options_frame,
                    text=text,
                    style='Modern.TButton',
                    command=handler
                )
                btn.pack(fill=tk.X, pady=2)
                self.option_buttons.append(btn)
else:
    class DialogGUI:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("GUI nie jest dostępne - brak modułu tkinter")