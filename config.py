"""
config.py – Central configuration for all game constants.
Edit values here to tune the simulation without touching game logic.
"""

import pygame
from pathlib import Path

# ── Project root ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# ── Asset directories ──────────────────────────────────────────────────────────
ASSETS_DIR = BASE_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR  = ASSETS_DIR / "audio"
FONTS_DIR  = ASSETS_DIR / "fonts"

# ── Image paths ───────────────────────────────────────────────────────────────
IMG_MENU_BG   = IMAGES_DIR / "background.jpg"
IMG_GAME_BG   = IMAGES_DIR / "bg.png"
IMG_CAR_FRONT = IMAGES_DIR / "front11.PNG"
IMG_CAR_LEFT  = IMAGES_DIR / "left2.png"
IMG_CAR_RIGHT = IMAGES_DIR / "right2.png"
ROAD_SPRITES  = [IMAGES_DIR / f"{i}.png" for i in range(1, 7)]

# ── Audio paths ───────────────────────────────────────────────────────────────
SFX_ENGINE = AUDIO_DIR / "car.mp3"

# ── Font paths ────────────────────────────────────────────────────────────────
FONT_MAIN = str(FONTS_DIR / "freesansbold.ttf")
FONT_PATH = FONT_MAIN   # alias kept so original ui/ files don't break

# ── Window ────────────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1000
WINDOW_HEIGHT = 750

# ── Road ──────────────────────────────────────────────────────────────────────
ROAD_WIDTH          = 9000   # wider road  (was 6000)
SEGMENT_LENGTH      = 400
CAMERA_DEPTH        = 0.84   # lower = higher POV / see further  (was 1.5)
RENDERING_DISTANCE  = 600    # more segments rendered  (was 400)

# ── Physics ───────────────────────────────────────────────────────────────────
GRAVITY                   = 9.81
AIR_DENSITY               = 1.225
VEHICLE_MASS              = 1500
FRONTAL_AREA              = 2.2
DRAG_COEFFICIENT          = 0.3
ROLLING_RESISTANCE_COEFF  = 0.015
ENGINE_FORCE              = 4000

MAX_VELOCITY     = 600
MIN_VELOCITY     = 0
MAX_ACCELERATION = 60
MIN_ACCELERATION = -60

TIRE_GRIP                 = 1.3
DOWNFORCE_COEFFICIENT     = 0.5
ENGINE_HEAT_CAPACITY      = 1.5
COOLING_COEFFICIENT       = 0.1
FUEL_CONSUMPTION_RATE     = 0.12
SPECIFIC_FUEL_CONSUMPTION = 230
GEAR_RATIOS               = [3.5, 2.1, 1.6, 1.3, 1.1]
LIFT_COEFFICIENT          = -0.1
SUSPENSION_STIFFNESS      = 20000
DAMPING_COEFFICIENT       = 1500
ROAD_SLOPE                = 1

# ── Colours ───────────────────────────────────────────────────────────────────
SURFACE_BLUE  = pygame.Color(127, 127, 127)
SURFACE_GREY  = pygame.Color(0, 255, 255)
WHITE_STREAK  = pygame.Color(255, 255, 255)
BLACK_STREAK  = pygame.Color(0, 0, 0)
DARK_ROAD     = pygame.Color(105, 105, 105)
LIGHT_ROAD    = pygame.Color(108, 108, 108)

# ── UI / Menu ─────────────────────────────────────────────────────────────────
BUTTON_WIDTH     = 300
BUTTON_HEIGHT    = 60
BUTTON_SPACING_X = 200
BUTTON_SPACING_Y = 70

SLIDER_WIDTH     = 200
SLIDER_HEIGHT    = 40
SLIDER_SPACING_X = 500
SLIDER_SPACING_Y = 70
SLIDER_START_X   = 280
SLIDER_START_Y   = 70

NEW_BUTTON_WIDTH   = 200
NEW_BUTTON_HEIGHT  = 40
NEW_BUTTON_SPACING = 20

FPS = 200

# ── Default vehicle ───────────────────────────────────────────────────────────
DEFAULT_VEHICLE_MAKE  = "Lamborghini"
DEFAULT_VEHICLE_MODEL = "Urus"
DEFAULT_VEHICLE_YEAR  = 2023

# ── Misc paths ────────────────────────────────────────────────────────────────
SCORES_FILE = BASE_DIR / "scores.json"
DATABASE    = BASE_DIR / "NEA3.db"