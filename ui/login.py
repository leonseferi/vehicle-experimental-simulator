"""
ui/login.py – Login / Create-Account screen.

Returns a LoginResult dataclass so the caller knows what happened
without needing to peek at global state.
"""

from __future__ import annotations
from dataclasses import dataclass, field

import pygame
import sys

from config import WINDOW_WIDTH, WINDOW_HEIGHT, FONT_PATH
from database import authenticate_user, create_user
from ui.widgets import Buttons


@dataclass
class LoginResult:
    """Outcome of the login / signup flow."""
    done:           bool = False   # True when the screen should close
    logged_in:      bool = False
    username:       str  = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _show_message(surface: pygame.Surface, message: str, ms: int = 1500) -> None:
    """Overlay a pink message for *ms* milliseconds."""
    font  = pygame.font.Font(None, 30)
    surf  = font.render(message, True, (255, 20, 147))
    rect  = surf.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 100))
    end   = pygame.time.get_ticks() + ms
    while pygame.time.get_ticks() < end:
        surface.blit(surf, rect)
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()


# ── Main entry point ──────────────────────────────────────────────────────────

def run_login_screen(screen: pygame.Surface, bg: pygame.Surface) -> LoginResult:
    """
    Blocking loop that shows the login / signup UI.

    Returns a :class:`LoginResult` when the user either logs in,
    creates an account, or clicks Return.
    """
    W, H = WINDOW_WIDTH, WINDOW_HEIGHT
    INACTIVE = pygame.Color("lightskyblue3")
    ACTIVE   = pygame.Color("dodgerblue2")
    GREEN    = pygame.Color("green")

    input_font   = pygame.font.Font(None, 14)
    link_font    = pygame.font.Font(None, 18)
    label_font   = pygame.font.Font(None, 30)
    title_font   = pygame.font.Font(FONT_PATH, 32)

    BOX_W, BOX_H = 200, 50
    cy = H // 2 - BOX_H // 2
    box_user = pygame.Rect(W // 2 - BOX_W // 2, cy - 60, BOX_W, BOX_H)
    box_pass = pygame.Rect(W // 2 - BOX_W // 2, cy + 10,  BOX_W, BOX_H)

    # Signup-link text
    link_text = "Don't have an account? Sign up now"
    link_surf = link_font.render(link_text, True, GREEN)
    link_rect = link_surf.get_rect(center=(W // 2, box_pass.y + 70))

    # Labels
    lbl_user = label_font.render("Username:", True, (255, 255, 255))
    lbl_pass = label_font.render("Password:", True, (255, 255, 255))
    LBL_OX, LBL_OY = 150, 15

    from config import NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT
    action_btn  = Buttons("Login",          (W // 2 - NEW_BUTTON_WIDTH // 2, H - NEW_BUTTON_HEIGHT - 50), NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT, is_small=True)
    return_btn  = Buttons("Return to Menu", (100, 500))

    text_user   = ""
    text_pass   = ""
    active_user = False
    active_pass = False
    col_user    = INACTIVE
    col_pass    = INACTIVE
    mode        = "login"   # "login" or "signup"

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if return_btn.check_clicked():
                    return LoginResult(done=True)

                active_user = box_user.collidepoint(event.pos)
                active_pass = box_pass.collidepoint(event.pos) if not active_user else False

                col_user = ACTIVE if active_user else INACTIVE
                col_pass = ACTIVE if active_pass else INACTIVE

                if link_rect.collidepoint(event.pos):
                    mode = "signup" if mode == "login" else "login"
                    action_btn.text = "Create Account" if mode == "signup" else "Login"

            # ── action button ─────────────────────────────────────────────────
            if action_btn.check_clicked():
                if len(text_user) < 3:
                    _show_message(screen, "Username must be at least 3 characters")
                elif len(text_pass) < 8:
                    _show_message(screen, "Password must be at least 8 characters")
                elif mode == "signup":
                    ok = create_user(text_user, text_pass)
                    if ok:
                        return LoginResult(done=True)
                    else:
                        _show_message(screen, "Username already taken")
                else:  # login
                    if authenticate_user(text_user, text_pass):
                        return LoginResult(done=True, logged_in=True, username=text_user)
                    else:
                        _show_message(screen, "Invalid username or password")

            if event.type == pygame.KEYDOWN:
                if active_user:
                    if   event.key == pygame.K_RETURN:    active_user = False
                    elif event.key == pygame.K_BACKSPACE:  text_user = text_user[:-1]
                    else:                                   text_user += event.unicode
                elif active_pass:
                    if   event.key == pygame.K_RETURN:    active_pass = False
                    elif event.key == pygame.K_BACKSPACE:  text_pass = text_pass[:-1]
                    else:                                   text_pass += event.unicode

        # ── render ────────────────────────────────────────────────────────────
        screen.blit(bg, (0, 0))

        title = "Create Account" if mode == "signup" else "Login To Account"
        t_surf = title_font.render(title, True, (255, 255, 255))
        screen.blit(t_surf, t_surf.get_rect(center=(W // 2, box_user.y - 60)))

        if mode == "login":
            screen.blit(link_surf, link_rect)

        screen.blit(lbl_user, (box_user.x - LBL_OX, box_user.y + LBL_OY))
        screen.blit(lbl_pass, (box_pass.x - LBL_OX, box_pass.y + LBL_OY))

        # Input text
        u_surf = input_font.render(text_user,          True, col_user)
        p_surf = input_font.render("*" * len(text_pass), True, col_pass)
        screen.blit(u_surf, u_surf.get_rect(center=box_user.center))
        screen.blit(p_surf, p_surf.get_rect(center=box_pass.center))

        pygame.draw.rect(screen, col_user, box_user, 2)
        pygame.draw.rect(screen, col_pass, box_pass, 2)

        action_btn.draw(screen)
        return_btn.draw(screen)

        pygame.display.flip()
        clock.tick(30)


# ── "Already logged in" confirmation screen ───────────────────────────────────

def draw_logged_in_screen(
    screen: pygame.Surface,
    bg: pygame.Surface,
    dim: pygame.Surface,
    events: list[pygame.event.Event],
) -> bool:
    """Show a confirmation that the user is logged in. Returns False → go back."""
    screen.blit(bg, (0, 0))
    screen.blit(dim, (0, 0))

    from config import WINDOW_WIDTH as W, WINDOW_HEIGHT as H, NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT
    font = pygame.font.Font(FONT_PATH, 32)
    msg  = font.render("Logged in! You can now save game results.", True, (255, 255, 255))
    screen.blit(msg, msg.get_rect(center=(W // 2, H // 2 - 50)))

    btn = Buttons(
        "Return to Menu",
        ((W - NEW_BUTTON_WIDTH) // 2, H - NEW_BUTTON_HEIGHT - 50),
        NEW_BUTTON_WIDTH, NEW_BUTTON_HEIGHT, screen=screen,
    )
    btn.draw(screen)

    for event in events:
        if event.type == pygame.MOUSEBUTTONDOWN and btn.check_clicked():
            return False

    return True