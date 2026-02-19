"""
ui/menu.py – Main menu, How-to-Play screen, and Leaderboard screen.
"""

from __future__ import annotations
import pygame
import sys

from config import (
    WINDOW_WIDTH as WIDTH, WINDOW_HEIGHT as HEIGHT,
    BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_SPACING_X, BUTTON_SPACING_Y,
    NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT, NEW_BUTTON_SPACING,
    FONT_PATH,
)
from ui.widgets import Buttons

# ── Sorting helpers ───────────────────────────────────────────────────────────

def _insertion_sort(data: list[dict], start: int, end: int) -> None:
    for i in range(start + 1, end + 1):
        key = data[i]
        j = i - 1
        while j >= start and key["score"] > data[j]["score"]:
            data[j + 1] = data[j]
            j -= 1
        data[j + 1] = key


def _merge(data: list[dict], start: int, mid: int, end: int) -> None:
    left  = data[start : mid + 1]
    right = data[mid + 1 : end + 1]
    i = j = 0
    k = start
    while i < len(left) and j < len(right):
        if left[i]["score"] > right[j]["score"]:
            data[k] = left[i]; i += 1
        else:
            data[k] = right[j]; j += 1
        k += 1
    while i < len(left):
        data[k] = left[i]; i += 1; k += 1
    while j < len(right):
        data[k] = right[j]; j += 1; k += 1


def merge_sort_scores(data: list[dict], start: int = 0, end: int | None = None) -> None:
    if end is None:
        end = len(data) - 1
    if end - start + 1 <= 10:
        _insertion_sort(data, start, end)
        return
    if start < end:
        mid = (start + end) // 2
        merge_sort_scores(data, start, mid)
        merge_sort_scores(data, mid + 1, end)
        _merge(data, start, mid, end)


# ── Main menu ─────────────────────────────────────────────────────────────────

def draw_menu(screen: pygame.Surface, bg: pygame.Surface) -> int:
    screen.blit(bg, (0, 0))

    font_title = pygame.font.Font(FONT_PATH, 40)

    # Black drop shadow for legibility over the background image
    shadow_surf = font_title.render("Vehicle Experimental Simulator", True, (0, 0, 0))
    screen.blit(shadow_surf, shadow_surf.get_rect(center=(WIDTH // 2 + 2, 42)))

    # White title text
    title_surf = font_title.render("Vehicle Experimental Simulator", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 40)))

    total_h = 3 * BUTTON_HEIGHT + 2 * BUTTON_SPACING_Y
    sx   = (WIDTH - 2 * BUTTON_WIDTH - BUTTON_SPACING_X) // 2
    sy   = (HEIGHT - total_h) // 2
    row2y = sy + BUTTON_HEIGHT + BUTTON_SPACING_Y
    row3y = sy + 2 * (BUTTON_HEIGHT + BUTTON_SPACING_Y)
    row4y = row3y + BUTTON_HEIGHT + BUTTON_SPACING_Y
    cx   = (WIDTH - BUTTON_WIDTH) // 2

    buttons = [
        Buttons("Quick Start",      (sx,                               sy),    screen=screen),
        Buttons("Modify Vehicle",   (sx + BUTTON_WIDTH + BUTTON_SPACING_X, sy),    screen=screen),
        Buttons("Modify Driver",    (sx,                               row2y), screen=screen),
        Buttons("Settings",         (sx + BUTTON_WIDTH + BUTTON_SPACING_X, row2y), screen=screen),
        Buttons("Account",          (sx,                               row3y), screen=screen),
        Buttons("How to Play",      (sx + BUTTON_WIDTH + BUTTON_SPACING_X, row3y), screen=screen),
        Buttons("View Leaderboard", (cx,                               row4y), screen=screen),
    ]

    command = -1
    for idx, btn in enumerate(buttons):
        btn.draw(screen)
        if btn.check_clicked():
            command = idx + 1
            break

    return command


# ── How-to-Play ───────────────────────────────────────────────────────────────

def draw_how_to_play(
    screen: pygame.Surface,
    bg: pygame.Surface,
    dim: pygame.Surface,
) -> bool:
    screen.blit(bg, (0, 0))
    screen.blit(dim, (0, 0))

    font = pygame.font.Font(FONT_PATH, 20)
    lines = [
        "UP ARROW    – Drive Forward",
        "DOWN ARROW  – Reverse",
        "LEFT ARROW  – Drift Left",
        "RIGHT ARROW – Drift Right",
        "TAB         – Speed Booster",
    ]
    for i, line in enumerate(lines):
        surf = font.render(line, True, (255, 255, 255))
        screen.blit(surf, surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100 + i * 50)))

    return_btn = Buttons(
        "Return to Menu",
        ((WIDTH - NEW_BUTTON_WIDTH) // 2, HEIGHT - NEW_BUTTON_HEIGHT - 50),
        NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT, is_small=True, screen=screen,
    )
    return_btn.draw(screen)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN and return_btn.check_clicked():
            return False

    return True


# ── Leaderboard ───────────────────────────────────────────────────────────────

def draw_leaderboard(
    screen: pygame.Surface,
    bg: pygame.Surface,
    dim: pygame.Surface,
    events: list[pygame.event.Event],
    score_data: list[dict],
) -> bool:
    screen.blit(bg, (0, 0))
    screen.blit(dim, (0, 0))

    merge_sort_scores(score_data)

    title_font = pygame.font.Font(FONT_PATH, 32)
    entry_font = pygame.font.Font(FONT_PATH, 20)

    title_surf = title_font.render("Leaderboard", True, (255, 255, 255))
    screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 50)))

    for idx, entry in enumerate(score_data, start=1):
        text = f"{idx}. {entry['username']} – Score: {entry['score']:.0f}"
        surf = entry_font.render(text, True, (255, 255, 255))
        screen.blit(surf, surf.get_rect(left=50, top=80 + idx * 30))

    return_btn = Buttons(
        "Return to Menu",
        ((WIDTH - NEW_BUTTON_WIDTH) // 2, HEIGHT - NEW_BUTTON_HEIGHT - 100),
        NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT, screen=screen,
    )
    return_btn.draw(screen)

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and return_btn.check_clicked():
            return False

    return True