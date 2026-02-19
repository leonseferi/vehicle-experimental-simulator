"""
ui/customization.py – Vehicle and Driver customisation menus.

Exposes:
  build_slider_tree()          – construct the BST of tuning sliders
  draw_customization_menu()    – full vehicle-tuning screen
  draw_driver_menu()           – driver-weight screen
  draw_settings_menu()         – audio / camera / FPS screen
  calculate_modified_params()  – convert slider values → parameter dict
"""

from __future__ import annotations
import pygame

from config import (
    WINDOW_WIDTH as WIDTH, WINDOW_HEIGHT as HEIGHT,
    SLIDER_WIDTH, SLIDER_HEIGHT,
    SLIDER_START_X, SLIDER_START_Y,
    SLIDER_SPACING_X, SLIDER_SPACING_Y,
    NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT, NEW_BUTTON_SPACING,
    FONT_PATH,
)
from ui.widgets import Slider, Node, Buttons
from database import STANDARD_PARAMETERS, update_standard_parameters, calculate_average_value

# ── Slider labels (customisation menu) ───────────────────────────────────────

CUSTOM_LABELS: list[str] = [
    "Adjust Torque Levels",
    "Change Tire Width",
    "Modify Drag Coefficient",
    "Adjust Gear Ratio",
    "Adjust Damping and Rebound Settings\n(Suspension System)",
    "Adjust Brake Caliper Settings",
    "Alter Weight Distribution\nThroughout Vehicle",
    "Modifying Differential Limited-Slip Settings\nfor Various Driving Conditions",
    "Adjust Fuel-Air Mixture\nand Injection Timing",
    "Modify Exhaust Diameter and Configuration",
    "Adjust ECU Parameters",
    "Adjust Vehicle Cold Air Intake (CAI)",
]

# Settings slider labels
SETTINGS_LABELS = ["Change Audio Levels", "Change Camera Depth", "Change FPS"]


# ── Tree construction ─────────────────────────────────────────────────────────

def build_slider_tree() -> Node:
    """
    Build a balanced binary tree of sliders from CUSTOM_LABELS.
    Left column: indices 0-5, right column: indices 6-11.
    """
    col_left  = [
        Slider(0, 100,
               (SLIDER_START_X, SLIDER_START_Y + i * SLIDER_SPACING_Y),
               (SLIDER_WIDTH, SLIDER_HEIGHT),
               CUSTOM_LABELS[i])
        for i in range(6)
    ]
    col_right = [
        Slider(0, 100,
               (SLIDER_START_X + SLIDER_SPACING_X, SLIDER_START_Y + i * SLIDER_SPACING_Y),
               (SLIDER_WIDTH, SLIDER_HEIGHT),
               CUSTOM_LABELS[i + 6])
        for i in range(6)
    ]

    def _build(items: list[Slider]) -> Node | None:
        if not items:
            return None
        mid = len(items) // 2
        return Node(items[mid], _build(items[:mid]), _build(items[mid + 1:]))

    return _build(col_left + col_right)  # type: ignore[arg-type]


def build_settings_sliders() -> list[Slider]:
    return [
        Slider(0, 100,
               (WIDTH // 2 - SLIDER_WIDTH // 2, HEIGHT // 2 - SLIDER_SPACING_Y + i * SLIDER_SPACING_Y),
               (SLIDER_WIDTH, SLIDER_HEIGHT),
               label)
        for i, label in enumerate(SETTINGS_LABELS)
    ]


# ── Parameter helpers ─────────────────────────────────────────────────────────

def calculate_modified_params(slider_values: dict[str, float]) -> dict[str, float]:
    """
    Map {label → slider_value (-50…+50)} onto the base standard parameters.
    Returns {label → adjusted_value}.
    """
    result: dict[str, float] = {}
    for name, (base, _) in STANDARD_PARAMETERS.items():
        pct = slider_values.get(name, 0) / 100       # -0.5 … +0.5
        result[name] = base * (1 + pct)
    return result


# ── Shared button row helper ──────────────────────────────────────────────────

def _bottom_buttons(
    screen: pygame.Surface,
    labels: list[str],
) -> list[Buttons]:
    n   = len(labels)
    bw  = NEW_BUTTON_WIDTH
    sp  = NEW_BUTTON_SPACING
    bh  = NEW_BUTTON_HEIGHT
    sx  = (WIDTH - n * bw - (n - 1) * sp) // 2
    by  = HEIGHT - bh - 50
    btns = [
        Buttons(label, (sx + i * (bw + sp), by), bw, bh, is_small=True, screen=screen)
        for i, label in enumerate(labels)
    ]
    for b in btns:
        b.draw(screen)
    return btns


# ── Customisation menu ────────────────────────────────────────────────────────

def draw_customization_menu(
    screen: pygame.Surface,
    bg: pygame.Surface,
    dim: pygame.Surface,
    events: list[pygame.event.Event],
    root: Node,
    baseline_avg: float,
) -> tuple[bool, float]:
    """
    Draw the vehicle customisation screen.

    Returns
    -------
    (stay_on_screen, calculated_change_multiplier)
      stay_on_screen = False → return to main menu
      calculated_change_multiplier = new CalculatedChange value after Save
    """
    screen.blit(bg, (0, 0))
    screen.blit(dim, (0, 0))
    root.draw(screen)

    btns = _bottom_buttons(screen, ["Return to Menu", "Save & Start", "Save & Customise Driver"])

    stay   = True
    change = 1.0   # default: no change

    for event in events:
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if btns[0].check_clicked():
                stay = False
            elif btns[1].check_clicked():
                slider_values   = root.get_all_values()
                modified        = calculate_modified_params(slider_values)
                update_standard_parameters(modified)
                new_avg         = calculate_average_value()
                if new_avg is not None and baseline_avg != 0:
                    pct    = ((new_avg - baseline_avg) / baseline_avg) * 100
                    change = pct / 100
                    print(f"[Custom] Speed multiplier change: {change:.3f}")
            else:
                root.handle_event(event)

    return stay, change


# ── Driver modification menu ──────────────────────────────────────────────────

_driver_slider = Slider(
    0, 100,
    (WIDTH // 2 - SLIDER_WIDTH // 2, HEIGHT // 2),
    (SLIDER_WIDTH, SLIDER_HEIGHT),
    "Adjust Driver Weight",
)


def draw_driver_menu(
    screen: pygame.Surface,
    bg: pygame.Surface,
    dim: pygame.Surface,
    events: list[pygame.event.Event],
) -> bool:
    """Returns False → return to main menu."""
    screen.blit(bg, (0, 0))
    screen.blit(dim, (0, 0))

    _driver_slider.draw(screen)
    for event in events:
        _driver_slider.handle_event(event)

    btns = _bottom_buttons(screen, ["Return to Menu", "Save & Start", "Save & Return"])

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if btns[0].check_clicked():
                return False
    return True


# ── Settings menu ─────────────────────────────────────────────────────────────

_settings_sliders = build_settings_sliders()


def draw_settings_menu(
    screen: pygame.Surface,
    bg: pygame.Surface,
    dim: pygame.Surface,
    events: list[pygame.event.Event],
) -> bool:
    """Returns False → return to main menu."""
    screen.blit(bg, (0, 0))
    screen.blit(dim, (0, 0))

    for s in _settings_sliders:
        s.draw(screen)
    for event in events:
        for s in _settings_sliders:
            s.handle_event(event)

    btns = _bottom_buttons(screen, ["Return to Menu", "Save & Start", "Save & Return"])
    pygame.display.flip()

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and btns[0].check_clicked():
            return False
    return True