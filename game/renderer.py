"""
game/renderer.py – Pseudo-3D road renderer.

Contains:
  Line     – a single road segment (3-D position + 2-D projected coords)
  drawQuad – draw a trapezoid road band
  build_road_lines() – construct the full list of Line objects for the circuit
"""

from __future__ import annotations
import math
import pygame
from typing import List

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    ROAD_WIDTH, SEGMENT_LENGTH, CAMERA_DEPTH,
    SURFACE_BLUE, SURFACE_GREY, WHITE_STREAK, BLACK_STREAK,
    DARK_ROAD, LIGHT_ROAD,
)

TOTAL_SEGMENTS = 1600   # road loops after this many segments


# ── Line ──────────────────────────────────────────────────────────────────────

class Line:
    """One road segment with 3-D world position and 2-D projection cache."""

    __slots__ = (
        "i", "x", "y", "z", "X", "Y", "W", "scale",
        "curve", "spriteX", "clip",
        "sprite", "sprite_rect",
        "SURFACE_COLOUR", "RUMBLE_COLOUR", "ROAD_COLOUR",
    )

    def __init__(self, i: int):
        self.i = i
        self.x = self.y = self.z = 0.0
        self.X = self.Y = self.W = 0.0
        self.scale = 0.0
        self.curve = 0.0
        self.spriteX = 0.0
        self.clip = 0.0
        self.sprite: pygame.Surface | None = None
        self.sprite_rect: pygame.Rect | None = None

        self.SURFACE_COLOUR: pygame.Color = pygame.Color("black")
        self.RUMBLE_COLOUR:  pygame.Color = pygame.Color("black")
        self.ROAD_COLOUR:    pygame.Color = pygame.Color("black")

    def project(self, cam_x: float, cam_y: float, cam_z: float) -> None:
        """Project 3-D world position into 2-D screen coords."""
        self.scale = CAMERA_DEPTH / (self.z - cam_z)
        self.X = (1 + self.scale * (self.x - cam_x)) * WINDOW_WIDTH / 2
        self.Y = (1 - self.scale * (self.y - cam_y)) * WINDOW_HEIGHT / 2
        self.W = self.scale * ROAD_WIDTH * WINDOW_WIDTH / 2

    def draw_sprite(self, surface: pygame.Surface) -> None:
        if self.sprite is None:
            return
        w = self.sprite.get_width()
        h = self.sprite.get_height()

        dest_x = self.X + self.scale * self.spriteX * WINDOW_WIDTH / 2
        dest_y = self.Y + 4
        dest_w = w * self.W / 266
        dest_h = h * self.W / 266

        dest_x += dest_w * self.spriteX
        dest_y += dest_h * -1

        clip_h = dest_y + dest_h - self.clip
        if clip_h < 0:
            clip_h = 0
        if clip_h >= dest_h or dest_w > w:
            return

        scaled = pygame.transform.scale(self.sprite, (int(dest_w), int(dest_h)))
        cropped = scaled.subsurface(0, 0, int(dest_w), int(dest_h - clip_h))
        surface.blit(cropped, (dest_x, dest_y))


# ── Quad drawing ──────────────────────────────────────────────────────────────

def draw_quad(
    surface: pygame.Surface,
    color: pygame.Color,
    x1: float, y1: float, w1: float,
    x2: float, y2: float, w2: float,
) -> None:
    """Draw a trapezoidal road band as a filled polygon."""
    pygame.draw.polygon(
        surface, color,
        [(x1 - w1, y1), (x2 - w2, y2), (x2 + w2, y2), (x1 + w1, y1)],
    )


# ── Circuit builder ───────────────────────────────────────────────────────────

def build_road_lines(sprites: List[pygame.Surface]) -> List[Line]:
    """
    Construct all Line objects for the looped circuit.

    Road layout
    -----------
    0   – 300  : straight with trees left + telegraph poles right
    300 – 700  : right curve
    750 – end  : hills (sine-wave Y)
    1100 – end : left curve
    """
    lines: List[Line] = []
    for i in range(TOTAL_SEGMENTS):
        line = Line(i)
        line.z = i * SEGMENT_LENGTH + 0.00001  # avoid div-by-zero in project()

        # Alternating colour bands every 3 segments
        band = (i // 3) % 2
        line.SURFACE_COLOUR = SURFACE_GREY if band else SURFACE_BLUE
        line.RUMBLE_COLOUR  = WHITE_STREAK  if band else BLACK_STREAK
        line.ROAD_COLOUR    = LIGHT_ROAD    if band else DARK_ROAD

        # Curves
        if 300 < i < 700:
            line.curve = 0.5
        if i > 1100:
            line.curve = -1.2

        # Hills
        if i > 750:
            line.y = math.sin(i / 30.0) * 1500

        # Sprites
        if i < 300 and i % 30 == 0:
            line.spriteX = -2.5
            line.sprite  = sprites[4]
        if i % 21 == 0:
            line.spriteX = 1
            line.sprite  = sprites[5]
        if i > 300 and i % 45 == 0:
            line.spriteX = -1
            line.sprite  = sprites[3]
        if i > 800 and i % 45 == 0:
            line.spriteX = -1.2
            line.sprite  = sprites[0]

        lines.append(line)

    return lines