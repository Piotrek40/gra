# exceptions.py

class GameError(Exception):
    """Bazowa klasa dla wyjątków w grze."""
    pass

class ItemError(GameError):
    """Błędy związane z przedmiotami."""
    pass

class InventoryError(GameError):
    """Błędy związane z ekwipunkiem."""
    pass

class QuestError(GameError):
    """Błąd związany z questami."""
    pass

class CombatError(GameError):
    """Błąd podczas walki."""
    pass

class SaveLoadError(GameError):
    """Błąd podczas zapisu/odczytu."""
    pass

class InvalidItemError(ItemError):
    """Próba użycia nieprawidłowego przedmiotu."""
    pass

class ItemNotFoundError(ItemError):
    """Przedmiot nie został znaleziony."""
    pass

class InventoryFullError(InventoryError):
    """Ekwipunek jest pełny."""
    pass

class InsufficientFundsError(InventoryError):
    """Niewystarczająca ilość złota."""
    pass

class RequirementsNotMetError(ItemError):
    """Wymagania przedmiotu nie są spełnione."""
    pass

class QuestNotAvailableError(QuestError):
    """Quest nie jest dostępny."""
    pass

class QuestAlreadyActiveError(QuestError):
    """Quest jest już aktywny."""
    pass

class QuestNotCompleteError(QuestError):
    """Quest nie został ukończony."""
    pass

class CombatAlreadyInProgressError(CombatError):
    """Walka jest już w toku."""
    pass

class NotInCombatError(CombatError):
    """Akcja wymaga bycia w walce."""
    pass

class InvalidTargetError(CombatError):
    """Nieprawidłowy cel ataku."""
    pass

class SaveFileCorruptedError(SaveLoadError):
    """Plik zapisu jest uszkodzony."""
    pass

class SaveVersionMismatchError(SaveLoadError):
    """Niezgodna wersja pliku zapisu."""
    pass

class GameStateError(GameError):
    """Błędy związane ze stanem gry."""
    pass

class LocationError(GameError):
    """Błędy związane z lokacjami."""
    
    def __init__(self, message: str, location_id: str = None):
        super().__init__(message)
        self.location_id = location_id

class InvalidLocationError(LocationError):
    """Próba dostępu do nieprawidłowej lokacji."""
    pass

class LocationAccessError(LocationError):
    """Brak dostępu do lokacji."""
    pass

class DialogueError(GameError):
    """Błędy związane z systemem dialogów."""
    pass

class InvalidDialogueOptionError(DialogueError):
    """Wybrano nieprawidłową opcję dialogową."""
    pass

class TradeError(GameError):
    """Błędy związane z systemem handlu."""
    pass

class InvalidTradeError(TradeError):
    """Nieprawidłowa transakcja handlowa."""
    pass

class ResourceError(GameError):
    """Błędy związane z zasobami."""
    pass

class ResourceNotFoundError(ResourceError):
    """Zasób nie został znaleziony."""
    pass

class SkillError(GameError):
    """Błędy związane z umiejętnościami."""
    pass

class InvalidSkillError(SkillError):
    """Próba użycia nieprawidłowej umiejętności."""
    pass

class InsufficientSkillLevelError(SkillError):
    """Niewystarczający poziom umiejętności."""
    pass

def handle_game_error(error: GameError) -> str:
    """Konwertuje wyjątki gry na przyjazne dla użytkownika komunikaty."""
    error_messages = {
        InventoryFullError: "Twój ekwipunek jest pełny!",
        InsufficientFundsError: "Nie masz wystarczająco złota!",
        RequirementsNotMetError: "Nie spełniasz wymagań tego przedmiotu!",
        QuestNotAvailableError: "Ten quest nie jest obecnie dostępny.",
        QuestAlreadyActiveError: "Ten quest jest już aktywny!",
        CombatAlreadyInProgressError: "Już jesteś w trakcie walki!",
        InvalidTargetError: "Nieprawidłowy cel ataku!",
        LocationAccessError: "Nie możesz wejść do tej lokacji!",
        InvalidSkillError: "Nie znasz tej umiejętności!",
        InsufficientSkillLevelError: "Twój poziom umiejętności jest zbyt niski!"
    }
    
    # Znajdź najbardziej szczegółowy komunikat błędu
    for error_type, message in error_messages.items():
        if isinstance(error, error_type):
            return message
            
    # Domyślny komunikat
    return str(error)