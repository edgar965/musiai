"""MusicSymbol - Abstrakte Basisklasse für alle Notation-Symbole."""

from abc import ABC, abstractmethod


class MusicSymbol(ABC):
    """Basisklasse für alle zeichenbaren Musik-Symbole."""

    def __init__(self, start_time: int = 0):
        self._start_time = start_time
        self._width = 0

    @property
    def start_time(self) -> int:
        return self._start_time

    @property
    @abstractmethod
    def min_width(self) -> int:
        """Minimale Breite in Pixeln."""
        ...

    @property
    def width(self) -> int:
        return max(self._width, self.min_width)

    @width.setter
    def width(self, value: int):
        self._width = value

    @property
    def above_staff(self) -> int:
        """Pixel über dem Notensystem."""
        return 0

    @property
    def below_staff(self) -> int:
        """Pixel unter dem Notensystem."""
        return 0

    @abstractmethod
    def draw(self, painter, x: int, ytop: int, config: dict) -> None:
        """Symbol zeichnen."""
        ...
