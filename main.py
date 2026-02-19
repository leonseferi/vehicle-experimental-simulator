
import sys
import pygame

# ── Bootstrap ────────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

from config import (
    WINDOW_WIDTH as WIDTH, WINDOW_HEIGHT as HEIGHT,
    FPS, FONT_MAIN, DEFAULT_VEHICLE_MAKE, DEFAULT_VEHICLE_MODEL, DEFAULT_VEHICLE_YEAR,
    IMG_MENU_BG, IMG_GAME_BG, ROAD_SPRITES,
)
from database import (
    initialise_database, populate_standard_parameters,
    calculate_average_value, get_vehicle_id, load_scores,
)
from ui.menu          import draw_menu, draw_how_to_play, draw_leaderboard
from ui.login         import run_login_screen, draw_logged_in_screen
from ui.customization import (
    build_slider_tree, draw_customization_menu,
    draw_driver_menu, draw_settings_menu,
)
from game.game_window import GameWindow


# ── Database seed (idempotent) ────────────────────────────────────────────────
initialise_database()
populate_standard_parameters()

# ── Shared display / assets ───────────────────────────────────────────────────
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vehicle Experimental Simulator")

timer = pygame.time.Clock()
font  = pygame.font.Font(FONT_MAIN, 20)

bg = pygame.transform.scale(pygame.image.load(str(IMG_MENU_BG)), (WIDTH, HEIGHT))

# Dim overlay used in sub-menus
dim_surface = pygame.Surface((WIDTH, HEIGHT))
dim_surface.fill((0, 0, 0))
dim_surface.set_alpha(180)

# Sprites (used by the game road renderer)
sprites = [pygame.image.load(str(p)).convert_alpha() for p in ROAD_SPRITES]

# ── Application state ─────────────────────────────────────────────────────────
class AppState:
    main_menu           = True
    customization_menu  = False
    driver_menu         = False
    settings_menu       = False
    login_menu          = False
    logged_in_screen    = False
    leaderboard_menu    = False
    how_to_play_menu    = False

    # Auth
    user_logged_in = False
    current_user   = ""

    # Tuning
    speed_multiplier = 1.0      # CalculatedChange
    baseline_avg     = calculate_average_value() or 1.0

    # Slider tree (built lazily once)
    slider_root = None


state = AppState()


def _ensure_slider_root():
    if state.slider_root is None:
        state.slider_root = build_slider_tree()


def _start_game() -> None:
    """Launch the GameWindow (blocking until the player quits to OS)."""
    vid = get_vehicle_id(DEFAULT_VEHICLE_MAKE, DEFAULT_VEHICLE_MODEL, DEFAULT_VEHICLE_YEAR)
    if vid is None:
        print(f"[Main] Vehicle '{DEFAULT_VEHICLE_MAKE} {DEFAULT_VEHICLE_MODEL} {DEFAULT_VEHICLE_YEAR}' not in DB – using defaults.")

    gw = GameWindow(
        screen           = screen,
        sprites          = sprites,
        speed_multiplier = state.speed_multiplier,
        username         = state.current_user,
        logged_in        = state.user_logged_in,
    )
    gw.run()
    state.main_menu = True


# ── Main loop ─────────────────────────────────────────────────────────────────
run = True
while run:
    screen.fill("white")
    timer.tick(FPS)

    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            run = False

    # ── Main menu ─────────────────────────────────────────────────────────────
    if state.main_menu:
        cmd = draw_menu(screen, bg)

        if cmd == 1:    # Quick Start
            state.main_menu = False
            _start_game()

        elif cmd == 2:  # Modify Vehicle
            _ensure_slider_root()
            state.customization_menu = True
            state.main_menu          = False

        elif cmd == 3:  # Modify Driver
            state.driver_menu = True
            state.main_menu   = False

        elif cmd == 4:  # Settings
            state.settings_menu = True
            state.main_menu     = False

        elif cmd == 5:  # Account
            if state.logged_in_screen:
                state.main_menu = False
            else:
                state.login_menu = True
                state.main_menu  = False

        elif cmd == 6:  # How to Play
            state.how_to_play_menu = True
            state.main_menu        = False

        elif cmd == 7:  # Leaderboard
            state.leaderboard_menu = True
            state.main_menu        = False

    # ── Customisation ─────────────────────────────────────────────────────────
    elif state.customization_menu:
        _ensure_slider_root()
        stay, change = draw_customization_menu(
            screen, bg, dim_surface, events,
            state.slider_root,
            state.baseline_avg,
        )
        if not stay:
            state.customization_menu = False
            state.main_menu          = True
        else:
            if change != 1.0:
                state.speed_multiplier = change

    # ── Driver modification ───────────────────────────────────────────────────
    elif state.driver_menu:
        stay = draw_driver_menu(screen, bg, dim_surface, events)
        if not stay:
            state.driver_menu = False
            state.main_menu   = True

    # ── Settings ──────────────────────────────────────────────────────────────
    elif state.settings_menu:
        stay = draw_settings_menu(screen, bg, dim_surface, events)
        if not stay:
            state.settings_menu = False
            state.main_menu     = True

    # ── Login ─────────────────────────────────────────────────────────────────
    elif state.login_menu:
        result = run_login_screen(screen, bg)
        state.login_menu = False
        if result.logged_in:
            state.user_logged_in   = True
            state.current_user     = result.username
            state.logged_in_screen = True
        state.main_menu = True

    # ── Already logged in ─────────────────────────────────────────────────────
    elif state.logged_in_screen and not state.main_menu:
        stay = draw_logged_in_screen(screen, bg, dim_surface, events)
        if not stay:
            state.logged_in_screen = False
            state.main_menu        = True

    # ── How to Play ───────────────────────────────────────────────────────────
    elif state.how_to_play_menu:
        stay = draw_how_to_play(screen, bg, dim_surface)
        if not stay:
            state.how_to_play_menu = False
            state.main_menu        = True

    # ── Leaderboard ───────────────────────────────────────────────────────────
    elif state.leaderboard_menu:
        score_data = load_scores()
        stay = draw_leaderboard(screen, bg, dim_surface, events, score_data)
        if not stay:
            state.leaderboard_menu = False
            state.main_menu        = True

    pygame.display.flip()

pygame.quit()