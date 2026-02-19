"""
game/game_window.py – Main game loop and rendering orchestration.

Features:
  • Minimap        – bottom-left, player (cyan) + AI (red) dots
  • Lap counter    – detects start/finish crossing
  • Best lap timer – tracks fastest lap
  • Q-Learning AI  – learns live using reinforcement learning,
                     rendered as a scaled front11.PNG sprite
"""

from __future__ import annotations
import sys
import time
import math
from typing import List

import pygame

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    SEGMENT_LENGTH, RENDERING_DISTANCE,
    IMG_GAME_BG, IMG_CAR_FRONT, IMG_CAR_LEFT, IMG_CAR_RIGHT,
    ROAD_SPRITES, SFX_ENGINE, FONT_MAIN,
)
from game.renderer import Line, draw_quad, build_road_lines, TOTAL_SEGMENTS
from game.physics import VehicleState
from game.ai_agent import QLearningAI
from database import save_score
from ui.widgets import TransparentButton

TRACK_LEN = TOTAL_SEGMENTS * SEGMENT_LENGTH


# ── Sound loader ──────────────────────────────────────────────────────────────

def _load_sound(path) -> pygame.mixer.Sound | None:
    try:
        return pygame.mixer.Sound(str(path))
    except pygame.error:
        print(f"[Audio] Could not load '{path}' – engine sound disabled.")
        return None


# ── Minimap ───────────────────────────────────────────────────────────────────

class Minimap:
    W, H   = 160, 120
    PAD    = 10
    BG     = (0, 0, 0, 160)
    TRACK  = (80, 80, 80)
    PLAYER = (0, 255, 255)
    AI_COL = (255, 60, 60)
    BORDER = (200, 200, 200)

    def __init__(self, lines: List[Line]):
        self._points = self._build_points(lines)
        self.rect    = pygame.Rect(
            self.PAD, WINDOW_HEIGHT - self.H - self.PAD, self.W, self.H)
        self._surf   = self._build_surface()

    def _build_points(self, lines):
        sample = lines[::8]
        xs = [l.x for l in sample]; zs = [l.z for l in sample]
        rx = (max(xs) - min(xs)) or 1; rz = (max(zs) - min(zs)) or 1
        return [((l.x - min(xs)) / rx, (l.z - min(zs)) / rz) for l in sample]

    def _build_surface(self):
        s = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        s.fill(self.BG)
        pygame.draw.rect(s, self.BORDER, s.get_rect(), 1)
        IP = 10
        pts = [(int(IP + nx*(self.W-IP*2)), int(IP + nz*(self.H-IP*2)))
               for nx, nz in self._points]
        if len(pts) > 1:
            pygame.draw.lines(s, self.TRACK, True, pts, 2)
        return s

    def _pos_to_px(self, world_pos):
        ratio = (world_pos % TRACK_LEN) / TRACK_LEN
        nx, nz = self._points[int(ratio * len(self._points)) % len(self._points)]
        IP = 10
        return int(IP + nx*(self.W-IP*2)), int(IP + nz*(self.H-IP*2))

    def draw(self, surface, player_pos, ai_pos=None):
        surface.blit(self._surf, self.rect.topleft)
        ox, oy = self.rect.topleft
        if ai_pos is not None:
            ax, ay = self._pos_to_px(ai_pos)
            pygame.draw.circle(surface, self.AI_COL, (ox+ax, oy+ay), 4)
        px, py = self._pos_to_px(player_pos)
        pygame.draw.circle(surface, self.PLAYER, (ox+px, oy+py), 5)


# ── Lap Tracker ───────────────────────────────────────────────────────────────

class LapTracker:
    TRIGGER = SEGMENT_LENGTH * 3

    def __init__(self):
        self.lap_count = 0
        self.lap_time  = 0.0
        self.best_lap  = None
        self._was_near = False

    def update(self, dt, track_pos) -> bool:
        self.lap_time += dt
        near = track_pos < self.TRIGGER
        if near and not self._was_near and self.lap_time > 2.0:
            self.lap_count += 1
            if self.best_lap is None or self.lap_time < self.best_lap:
                self.best_lap = self.lap_time
            self.lap_time  = 0.0
            self._was_near = True
            return True
        if not near:
            self._was_near = False
        return False

    def draw(self, surface, font):
        for i, (txt, col) in enumerate([
            (f"Lap: {self.lap_count}",               (255, 255, 0)),
            (f"Lap Time: {self.lap_time:.2f}s",      (255, 255, 255)),
            (f"Best: {self.best_lap:.2f}s" if self.best_lap else "Best: --",
                                                      (0, 255, 180)),
        ]):
            surface.blit(font.render(txt, True, col),
                         (WINDOW_WIDTH // 2 - 60, 10 + i * 24))


# ── GameWindow ────────────────────────────────────────────────────────────────

class GameWindow:

    def __init__(
        self,
        screen: pygame.Surface,
        sprites: List[pygame.Surface],
        speed_multiplier: float = 1.0,
        username: str = "",
        logged_in: bool = False,
    ):
        self.screen           = screen
        self.sprites          = sprites
        self.speed_multiplier = speed_multiplier
        self.username         = username
        self.logged_in        = logged_in

        self.vehicle     = VehicleState()
        self.lines       = build_road_lines(sprites)
        self.minimap     = Minimap(self.lines)
        self.lap_tracker = LapTracker()
        self._lap_flash  = 0.0

        # Q-learning AI – starts 5 % of the way around the track
        self.ai = QLearningAI(start_offset=TRACK_LEN * 0.05)

        # ── Load images ───────────────────────────────────────────────────────
        def _img(path, size):
            s = pygame.image.load(str(path)).convert_alpha()
            return pygame.transform.scale(s, size)

        SIZE = (456, 285)   # 20 % smaller than original to suit wider road
        self.img_front   = _img(IMG_CAR_FRONT, SIZE)
        self.img_right   = _img(IMG_CAR_RIGHT,  SIZE)
        self.img_left    = _img(IMG_CAR_LEFT,   SIZE)
        self.current_img = self.img_front
        self.vehicle_rect = self.img_front.get_rect(
            center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))

        # AI sprite: same image, tinted red so it's visually distinct
        ai_base = pygame.image.load(str(IMG_CAR_FRONT)).convert_alpha()
        # Apply a red tint by blending a red surface over the car image
        tint = pygame.Surface(ai_base.get_size(), pygame.SRCALPHA)
        tint.fill((180, 0, 0, 120))   # semi-transparent red overlay
        ai_base.blit(tint, (0, 0))
        self.ai_sprite_full = ai_base   # full-res; we'll scale per-frame

        # Background
        self.bg_image   = pygame.image.load(str(IMG_GAME_BG)).convert_alpha()
        self.bg_image   = pygame.transform.scale(self.bg_image, (WINDOW_WIDTH, WINDOW_HEIGHT))
        self.bg_surface = pygame.Surface((WINDOW_WIDTH * 3, WINDOW_HEIGHT))
        self.bg_rect    = self.bg_surface.get_rect(topleft=(0, 0))

        # Audio
        pygame.mixer.init()
        self.engine_snd = _load_sound(SFX_ENGINE)
        if self.engine_snd:
            self.engine_snd.set_volume(0.4)
        self.engine_ch = pygame.mixer.Channel(0) if self.engine_snd else None

        # Fonts
        self.hud_font  = pygame.font.Font(FONT_MAIN, 20)
        self.lap_font  = pygame.font.Font(FONT_MAIN, 22)
        self.dbg_font  = pygame.font.Font(FONT_MAIN, 18)

        self.performance_score = 0.0
        self.previous_segment  = 0
        self.clock     = pygame.time.Clock()
        self.last_time = time.time()

    # ── Audio ─────────────────────────────────────────────────────────────────

    def _start_engine(self):
        if self.engine_ch and not self.engine_ch.get_busy():
            self.engine_ch.play(self.engine_snd)

    def _stop_engine(self):
        if self.engine_ch and self.engine_ch.get_busy():
            self.engine_ch.stop()

    # ── HUD ───────────────────────────────────────────────────────────────────

    def _draw_hud(self):
        v = self.vehicle
        SX, SY, SW, SH = 700, 300, 255, 420
        PAD, LS = 10, 20
        bg = pygame.Surface((SW, SH), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 170))
        self.screen.blit(bg, (SX, SY))
        rows = [
            ("Vehicle Performance",               (0, 255, 255)),
            (f"Acceleration:  {v.acceleration_clamped:.1f} m/s²", (255,255,255)),
            (f"Velocity:      {v.velocity:.1f} m/s",              (255,255,255)),
            (f"Air Resist:    {v.air_resistance:.1f} N",           (255,255,255)),
            (f"Rolling Res:   {v.rolling_resistance:.1f} N",       (255,255,255)),
            (f"Fuel:          {v.fuel_consumption_rate:.1f} L/s",  (255,255,255)),
            (f"Engine Temp:   {v.engine_temperature:.0f} °C",      (255,255,255)),
            (f"Distance:      {v.total_distance:.1f} m",           (255,255,255)),
            (f"Drag Losses:   {v.drag_losses:.1f}",                (255,255,255)),
            (f"Tire Wear:     {v.tire_wear:.2f}%",                 (255,255,255)),
            (f"RR Losses:     {v.rr_losses:.1f}",                  (255,255,255)),
            (f"Nitro:         {v.nitro_level:.1f}%",               (255,255,255)),
            (f"RPM:           {v.engine_rpm}",                     (255,255,255)),
            (f"Gravity Force: {v.gf_force:.0f} N",                 (255,255,255)),
        ]
        cy = SY + PAD
        for txt, col in rows:
            self.screen.blit(self.hud_font.render(txt, True, col), (SX+PAD, cy))
            cy += LS
        self.screen.blit(
            self.hud_font.render(f"Score: {self.performance_score:.0f}",
                                 True, (255,255,255)),
            (WINDOW_WIDTH - 200, 20))

    # ── Message overlay ───────────────────────────────────────────────────────

    def _show_message(self, message, duration_ms=1500):
        font = pygame.font.Font(FONT_MAIN, 36)
        surf = font.render(message, True, (255, 20, 147))
        rect = surf.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
        end  = pygame.time.get_ticks() + duration_ms
        while pygame.time.get_ticks() < end:
            ov = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            ov.fill((0,0,0,180))
            self.screen.blit(ov, (0,0))
            self.screen.blit(surf, rect)
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

    def _draw_lap_flash(self, dt):
        if self._lap_flash > 0:
            self._lap_flash -= dt
            font = pygame.font.Font(FONT_MAIN, 48)
            surf = font.render(
                f"LAP {self.lap_tracker.lap_count} COMPLETE!", True, (255,220,0))
            self.screen.blit(surf, surf.get_rect(center=(WINDOW_WIDTH//2, 120)))

    # ── AI sprite renderer ────────────────────────────────────────────────────

    def _draw_ai_sprite(
        self,
        line: Line,
        player_x: float,
        ai_lane_x: float,
    ) -> None:
        """
        Project and draw the AI car sprite at the given road Line,
        offset laterally by ai_lane_x (same coordinate system as player_x).
        The sprite is scaled proportionally to the line's W (road width on screen),
        so it shrinks naturally with distance exactly like road markings.
        """
        if line.W <= 0:
            return

        # Map ai_lane_x (world) to screen X using the line's projection scale.
        # line.X is the road centre on screen; line.W is half the road width on screen.
        # ai_lane_x is in the same world-unit space as player_x (road half = 4500).
        road_half_world = 4500.0
        lane_ratio  = ai_lane_x / road_half_world      # -1.0 … +1.0
        screen_x    = line.X + lane_ratio * line.W      # pixel X on screen
        screen_y    = line.Y                            # pixel Y on screen

        # Scale the sprite: when line.W equals the player's road width at close range,
        # the sprite should be roughly player-car sized. We use a reference W.
        REFERENCE_W  = 400.0   # approximate line.W when the player car is drawn
        PLAYER_W     = 456     # player sprite width (SIZE[0])
        PLAYER_H     = 285

        scale        = line.W / REFERENCE_W
        sprite_w     = max(8, int(PLAYER_W * scale))
        sprite_h     = max(5, int(PLAYER_H * scale))

        # Skip if the sprite would be clipped entirely above the horizon
        if screen_y - sprite_h > WINDOW_HEIGHT or screen_y < 0:
            return

        # Scale the tinted sprite to the calculated size
        scaled = pygame.transform.scale(self.ai_sprite_full, (sprite_w, sprite_h))

        # Clip to the road's clip value (prevents sprites floating above hills)
        clip_top = max(0, int(line.clip - (screen_y - sprite_h)))
        if clip_top >= sprite_h:
            return
        if clip_top > 0:
            scaled = scaled.subsurface(0, clip_top, sprite_w, sprite_h - clip_top)

        self.screen.blit(scaled, (int(screen_x - sprite_w // 2),
                                  int(screen_y - sprite_h)))

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        N         = TOTAL_SEGMENTS
        POSITION  = 0.0
        player_x  = 0.0
        player_y  = 10_000.0
        base_y    = WINDOW_HEIGHT - 300

        quit_btn = TransparentButton("Quit",        (20, 20))
        save_btn = TransparentButton("Save Scores", (20, 70))

        # We collect the AI's projected line during the road render loop
        # so the sprite uses freshly computed screen coords.
        ai_render_line: Line | None = None

        while True:
            dt = time.time() - self.last_time
            self.last_time = time.time()
            self.clock.tick(60)

            self.screen.blit(self.bg_image, (0, 0))

            for ev in pygame.event.get([pygame.QUIT]):
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            # ── Player input ──────────────────────────────────────────────────
            keys    = pygame.key.get_pressed()
            moving  = False
            speed   = 0.0
            boost   = 0.0
            braking = False

            if keys[pygame.K_UP]:
                moving = True; boost = 500.0
                speed += SEGMENT_LENGTH * self.speed_multiplier
                self.vehicle.tire_wear += 0.01
                self._start_engine()
            else:
                self._stop_engine()

            if keys[pygame.K_DOWN]:
                moving = True; braking = True
                speed -= SEGMENT_LENGTH
                self.vehicle.tire_wear += 0.01

            if keys[pygame.K_RIGHT]:
                moving = True; player_x += 5
                speed += SEGMENT_LENGTH
                self.current_img = self.img_right
            elif keys[pygame.K_LEFT]:
                moving = True; player_x -= 5
                speed += SEGMENT_LENGTH
                self.current_img = self.img_left
            elif keys[pygame.K_w]:
                speed += SEGMENT_LENGTH * 3
            else:
                self.current_img = self.img_front

            if keys[pygame.K_TAB]:
                moving = True; boost += 500.0
                speed += SEGMENT_LENGTH
                self.vehicle.tire_wear += 0.1

            if not any([keys[pygame.K_UP], keys[pygame.K_DOWN],
                        keys[pygame.K_LEFT], keys[pygame.K_RIGHT]]):
                moving = False

            # ── Physics ───────────────────────────────────────────────────────
            self.vehicle.update(dt, moving, throttle_boost=boost, braking=braking)

            # ── Road position ─────────────────────────────────────────────────
            POSITION = (POSITION + speed) % TRACK_LEN
            start_pos    = int(POSITION // SEGMENT_LENGTH)
            current_line = self.lines[start_pos]

            # Road-width clamp (in world units: road half = line.W is screen pixels,
            # player_x is in a different unit, so we clamp against W directly)
            if player_x >  current_line.W / 2: player_x =  current_line.W / 2
            if player_x < -current_line.W / 2: player_x = -current_line.W / 2
            if player_y < 500: player_y = 500

            if speed > 0:   self.bg_rect.x -= current_line.curve * 2
            elif speed < 0: self.bg_rect.x += current_line.curve * 2
            if self.bg_rect.right < WINDOW_WIDTH: self.bg_rect.x = -WINDOW_WIDTH
            elif self.bg_rect.left > 0:           self.bg_rect.x = -WINDOW_WIDTH

            # ── Lap ───────────────────────────────────────────────────────────
            if self.lap_tracker.update(dt, POSITION):
                self._lap_flash = 2.5

            # ── AI Q-learning update ──────────────────────────────────────────
            road_half_w = current_line.W / 2   # screen pixels – used as world proxy
            self.ai.update(POSITION, road_half_w)

            # ── Score ─────────────────────────────────────────────────────────
            cur_seg = int(self.vehicle.total_distance / SEGMENT_LENGTH)
            if cur_seg != self.previous_segment and abs(self.vehicle.velocity) > 0.1:
                self.performance_score += SEGMENT_LENGTH * self.vehicle.velocity
                self.previous_segment   = cur_seg

            # ── Road rendering + AI sprite collection ─────────────────────────
            cam_h = self.lines[start_pos].y + player_y
            maxy  = WINDOW_HEIGHT
            x = dx = 0.0
            ai_render_line = None

            ai_seg_abs  = int(self.ai.position // SEGMENT_LENGTH) % N
            player_seg  = start_pos
            ai_relative = (ai_seg_abs - player_seg) % N

            for n in range(start_pos, start_pos + RENDERING_DISTANCE):
                cur   = self.lines[n % N]
                cam_z = POSITION - (TRACK_LEN if n >= N else 0)
                cur.project(player_x - x, cam_h, cam_z)
                x  += dx
                dx += cur.curve
                cur.clip = maxy

                if cur.Y >= maxy:
                    continue
                maxy = cur.Y

                prev = self.lines[(n - 1) % N]
                draw_quad(self.screen, cur.SURFACE_COLOUR,
                          0, prev.Y, WINDOW_WIDTH, 0, cur.Y, WINDOW_WIDTH)
                draw_quad(self.screen, cur.RUMBLE_COLOUR,
                          prev.X, prev.Y, prev.W * 1.2,
                          cur.X,  cur.Y,  cur.W  * 1.2)
                draw_quad(self.screen, cur.ROAD_COLOUR,
                          prev.X, prev.Y, prev.W,
                          cur.X,  cur.Y,  cur.W)

                # Capture the line we'll use to draw the AI sprite
                if ai_relative < RENDERING_DISTANCE and (n % N) == ai_seg_abs:
                    ai_render_line = cur

            # Sprites (back to front)
            for n in range(start_pos + RENDERING_DISTANCE, start_pos + 1, -1):
                self.lines[n % N].draw_sprite(self.screen)

            # ── Draw AI sprite using captured line ────────────────────────────
            if ai_render_line is not None:
                self._draw_ai_sprite(ai_render_line, player_x, self.ai.lane_x)

            # ── Player vehicle ────────────────────────────────────────────────
            self.vehicle_rect.x = (WINDOW_WIDTH / 2 + player_x
                                   - self.img_front.get_width() / 2)
            self.vehicle_rect.y = base_y
            self.screen.blit(self.current_img, self.vehicle_rect)

            # ── Overlay UI ────────────────────────────────────────────────────
            self._draw_hud()
            self.lap_tracker.draw(self.screen, self.lap_font)
            self._draw_lap_flash(dt)
            self.minimap.draw(self.screen, POSITION, self.ai.position)
            self.ai.draw_debug(self.screen, self.dbg_font)
            quit_btn.draw(self.screen)
            save_btn.draw(self.screen)

            # ── Events ────────────────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    valid = {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT,
                             pygame.K_RIGHT, pygame.K_TAB, pygame.K_w}
                    if event.key not in valid:
                        self._show_message("Use arrow keys to drive", 800)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
                    if quit_btn.is_clicked(pos):
                        pygame.quit(); sys.exit()
                    elif save_btn.is_clicked(pos):
                        if self.logged_in:
                            save_score(self.username, self.performance_score)
                        else:
                            self._show_message("Not logged in! Can't save", 2000)

            pygame.display.update()