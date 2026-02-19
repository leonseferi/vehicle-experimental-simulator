"""
ui/widgets.py – Reusable UI primitives.

Contains:
  • Buttons        – standard rectangular button
  • TransparentButton – text-only hit-test button (used in-game HUD)
  • Slider          – draggable value slider
  • Node            – binary-tree node for organising groups of sliders
"""

from __future__ import annotations
import pygame
from config import (
    BUTTON_WIDTH, BUTTON_HEIGHT,
    SLIDER_WIDTH, SLIDER_HEIGHT,
    FONT_PATH,
)

# Fonts are initialised lazily so this module can be imported before
# pygame.init() has been called.
_font_cache: dict[tuple[str, int], pygame.font.Font] = {}


def _font(path: str, size: int) -> pygame.font.Font:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.Font(path, size)
    return _font_cache[key]


# ── TransparentButton ─────────────────────────────────────────────────────────

class TransparentButton:
    """Text-only button with a simple rect collision test."""

    def __init__(self, text: str, position: tuple[int, int], font_size: int = 36):
        self.text = text
        self.position = position
        self.font = pygame.font.Font(None, font_size)
        self._rebuild()

    def _rebuild(self) -> None:
        self.rendered_text = self.font.render(self.text, True, pygame.Color("white"))
        self.rect = self.rendered_text.get_rect(topleft=self.position)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.rendered_text, self.rect.topleft)

    def is_clicked(self, mouse_pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(mouse_pos)


# ── Buttons ───────────────────────────────────────────────────────────────────

class Buttons:
    """Standard grey rectangular button drawn on *screen* (module-level surface)."""

    def __init__(
        self,
        txt: str,
        pos: tuple[int, int],
        width: int = BUTTON_WIDTH,
        height: int = BUTTON_HEIGHT,
        is_small: bool = False,
        screen: pygame.Surface | None = None,
    ):
        self.text = txt
        self.pos = pos
        self.width = width
        self.height = height
        self.is_small = is_small
        self._screen = screen  # surface to draw on; set via attach() or draw(surface)
        self.button = pygame.Rect(pos, (width, height))

    def attach(self, surface: pygame.Surface) -> "Buttons":
        """Bind a draw surface; enables draw() without arguments."""
        self._screen = surface
        return self

    def draw(self, surface: pygame.Surface | None = None) -> None:
        target = surface or self._screen
        if target is None:
            raise RuntimeError("Buttons.draw() requires a surface.")
        font = _font(FONT_PATH, 11 if self.is_small else 20)
        text_surf = font.render(self.text, True, "black")
        text_rect = text_surf.get_rect(
            center=(self.pos[0] + self.width // 2, self.pos[1] + self.height // 2)
        )
        pygame.draw.rect(target, "light gray", self.button, 0, 5)
        pygame.draw.rect(target, "dark gray", [*self.pos, self.width, self.height], 5, 5)
        target.blit(text_surf, text_rect)

    def check_clicked(self) -> bool:
        return (
            self.button.collidepoint(pygame.mouse.get_pos())
            and pygame.mouse.get_pressed()[0]
        )


# ── Slider ────────────────────────────────────────────────────────────────────

class Slider:
    """
    Horizontal draggable slider mapping to the range [-50, +50].

    Typical usage::

        slider = Slider(0, 100, (x, y), (200, 40), "My Parameter")
        slider.handle_event(event)
        slider.draw(screen)
        value = slider.get_value()   # float in [-50, 50]
    """

    def __init__(
        self,
        min_value: float,
        max_value: float,
        pos: tuple[int, int],
        size: tuple[int, int],
        title: str,
    ):
        self.min_value = min_value
        self.max_value = max_value
        self.value: float = 0.0
        self.pos = pos
        self.size = size
        self.handle_pos: float = pos[0] + size[0] / 2
        self.dragging = False
        self.title = title
        self._small_font = _font(FONT_PATH, 11)
        self.title_surface = self._small_font.render(title, True, (255, 255, 255))
        self.title_rect = self.title_surface.get_rect(
            right=pos[0] - 10, centery=pos[1] + size[1] // 2
        )

    # ── value access ──────────────────────────────────────────────────────────

    def get_value(self) -> float:
        return round(self.value, 1)

    def get_rounded(self) -> float:
        return round(self.value, 0)

    # ── event handling ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event) -> None:
        margin = 10
        x, y = self.pos
        w, h = self.size

        if event.type == pygame.MOUSEBUTTONDOWN:
            if (
                self.handle_pos - margin <= event.pos[0] <= self.handle_pos + margin
                and y - margin <= event.pos[1] <= y + h + margin
            ):
                self.dragging = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.handle_pos = max(x, min(event.pos[0], x + w))
            ratio = (self.handle_pos - x) / w
            self.value = -50 + ratio * 100

    # ── drawing ───────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> float:
        screen.blit(self.title_surface, self.title_rect)

        mid_y = self.pos[1] + self.size[1] // 2
        pygame.draw.line(
            screen, (255, 255, 255),
            (self.pos[0], mid_y), (self.pos[0] + self.size[0], mid_y), 5,
        )

        handle = pygame.Rect(self.handle_pos, self.pos[1], 10, self.size[1])
        pygame.draw.rect(screen, (0, 128, 255), handle)

        rounded = self.get_rounded()
        val_surf = self._small_font.render(str(int(rounded)), True, (255, 255, 255))
        val_rect = val_surf.get_rect(
            centerx=self.handle_pos, top=self.pos[1] + self.size[1] + 5
        )
        screen.blit(val_surf, val_rect)
        return rounded

    # ── parameter math ────────────────────────────────────────────────────────

    def adjustment_factor(self) -> float:
        """Return a multiplier: 0.5 (slider at -50) → 1.0 (centre) → 1.5 (+50)."""
        return (self.get_rounded() + 100) / 100


# ── Node (binary tree of sliders) ────────────────────────────────────────────

class Node:
    """
    Binary-tree node used to organise sliders in the customisation menu.
    Each leaf wraps a single Slider; branch nodes just route events.
    """

    def __init__(
        self,
        slider: Slider | None = None,
        left:   "Node | None" = None,
        right:  "Node | None" = None,
    ):
        self.slider = slider
        self.left   = left
        self.right  = right

    def draw(self, screen: pygame.Surface) -> None:
        if self.slider:
            self.slider.draw(screen)
        if self.left:
            self.left.draw(screen)
        if self.right:
            self.right.draw(screen)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.slider:
            self.slider.handle_event(event)
        if self.left:
            self.left.handle_event(event)
        if self.right:
            self.right.handle_event(event)

    def get_all_values(self) -> dict[str, float]:
        """Recursively collect {title: value} from every leaf."""
        values: dict[str, float] = {}
        if self.slider:
            values[self.slider.title] = self.slider.get_value()
        if self.left:
            values.update(self.left.get_all_values())
        if self.right:
            values.update(self.right.get_all_values())
        return values