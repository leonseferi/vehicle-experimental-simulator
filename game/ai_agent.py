"""
game/ai_agent.py – Q-Learning AI opponent.

The agent learns entirely during the session (no pre-trained weights).
It starts by exploring randomly, then gradually exploits what it learned.

State space  (discrete buckets):
  • speed_bucket   : 0-4  (velocity binned into 5 levels)
  • lane_bucket    : 0-4  (lateral position binned across road width)
  • gap_bucket     : 0-4  (distance behind/ahead of player, 5 levels)

Actions (5):
  0 – accelerate
  1 – brake
  2 – steer left
  3 – steer right
  4 – coast (do nothing)

Q-update (Bellman):
  Q(s,a) ← Q(s,a) + α [r + γ·max Q(s',a') − Q(s,a)]
"""

from __future__ import annotations
import random
import math
from collections import defaultdict

from config import SEGMENT_LENGTH
from game.renderer import TOTAL_SEGMENTS


# ── Constants ────────────────────────────────────────────────────────────────
ACTIONS       = [0, 1, 2, 3, 4]
ACTION_NAMES  = ["accelerate", "brake", "left", "right", "coast"]

ALPHA         = 0.15    # learning rate
GAMMA         = 0.92    # discount factor
EPSILON_START = 1.0     # start fully random
EPSILON_MIN   = 0.05    # always keep 5 % exploration
EPSILON_DECAY = 0.9995  # multiply epsilon each frame

MAX_SPEED     = 600.0   # matches physics cap
ROAD_HALF     = 4500.0  # half of ROAD_WIDTH=9000
TRACK_LEN     = TOTAL_SEGMENTS * SEGMENT_LENGTH


# ── State discretisation ─────────────────────────────────────────────────────

def _bucket(value: float, min_v: float, max_v: float, n: int) -> int:
    """Map a continuous value into one of n integer buckets."""
    ratio = (value - min_v) / (max_v - min_v)
    return max(0, min(n - 1, int(ratio * n)))


def _make_state(
    ai_speed:   float,
    ai_lane_x:  float,
    player_pos: float,
    ai_pos:     float,
) -> tuple[int, int, int]:
    speed_b = _bucket(ai_speed,  0,             MAX_SPEED,    5)
    lane_b  = _bucket(ai_lane_x, -ROAD_HALF,    ROAD_HALF,    5)
    gap     = (player_pos - ai_pos) % TRACK_LEN
    if gap > TRACK_LEN / 2:
        gap -= TRACK_LEN          # negative = AI is ahead
    gap_b   = _bucket(gap, -TRACK_LEN / 2, TRACK_LEN / 2, 5)
    return (speed_b, lane_b, gap_b)


# ── Reward function ──────────────────────────────────────────────────────────

def _compute_reward(
    ai_speed:    float,
    ai_lane_x:   float,
    player_pos:  float,
    ai_pos:      float,
    on_road:     bool,
) -> float:
    reward = 0.0

    # Speed reward: going fast is good
    reward += ai_speed / MAX_SPEED * 2.0

    # Off-road penalty
    if not on_road:
        reward -= 3.0

    # Stay roughly centred on the road (within half the road width)
    if abs(ai_lane_x) < ROAD_HALF * 0.6:
        reward += 0.3
    else:
        reward -= 0.5

    # Closing on the player is rewarded; falling far behind is penalised
    gap = (player_pos - ai_pos) % TRACK_LEN
    if gap > TRACK_LEN / 2:
        gap -= TRACK_LEN
    if 0 < gap < TRACK_LEN * 0.1:
        reward += 1.0        # close behind player = competitive
    elif gap > TRACK_LEN * 0.3:
        reward -= 1.0        # very far behind = bad

    return reward


# ── Q-Learning Agent ─────────────────────────────────────────────────────────

class QLearningAI:
    """
    A live Q-learning agent that controls an AI car.

    Physics are kept simple so the agent can focus on learning
    the speed/steering trade-off rather than fighting the simulation.
    """

    # Steering and speed step sizes (tuned for SEGMENT_LENGTH = 400)
    STEER_STEP    = 40.0      # pixels per frame lateral movement
    ACCEL_STEP    = SEGMENT_LENGTH * 0.5
    BASE_FORWARD  = SEGMENT_LENGTH * 0.6   # always-on forward motion

    def __init__(self, start_offset: float = 0.0):
        # Track position (world units, same scale as player POSITION)
        self.position  = start_offset % TRACK_LEN
        self.lane_x    = 0.0          # lateral offset from road centre
        self.speed     = self.BASE_FORWARD

        # Q-table: state → {action: Q-value}
        self._q: dict[tuple, dict[int, float]] = defaultdict(
            lambda: {a: 0.0 for a in ACTIONS}
        )

        self.epsilon   = EPSILON_START
        self._prev_state:  tuple | None = None
        self._prev_action: int   | None = None
        self._prev_reward: float        = 0.0

        # Stats for the HUD
        self.total_reward   = 0.0
        self.episodes       = 0
        self.last_action    = "coast"
        self.explore_pct    = 100.0   # % random moves (shown in HUD)

    # ── Q helpers ─────────────────────────────────────────────────────────────

    def _best_action(self, state: tuple) -> int:
        q_row = self._q[state]
        return max(q_row, key=q_row.__getitem__)

    def _update_q(
        self,
        state:      tuple,
        action:     int,
        reward:     float,
        next_state: tuple,
    ) -> None:
        old_q    = self._q[state][action]
        best_next = max(self._q[next_state].values())
        new_q    = old_q + ALPHA * (reward + GAMMA * best_next - old_q)
        self._q[state][action] = new_q

    # ── Per-frame update ──────────────────────────────────────────────────────

    def update(
        self,
        player_pos: float,
        road_half_w: float,
    ) -> float:
        """
        Advance the AI one frame.

        Parameters
        ----------
        player_pos   : player's current POSITION (world units)
        road_half_w  : half the current road width in world units
                       (used for on-road check)

        Returns
        -------
        forward speed contribution this frame (added to POSITION)
        """
        on_road = abs(self.lane_x) < road_half_w

        # ── Build current state ───────────────────────────────────────────────
        state = _make_state(self.speed, self.lane_x, player_pos, self.position)

        # ── Compute reward for the PREVIOUS step ─────────────────────────────
        reward = _compute_reward(
            self.speed, self.lane_x, player_pos, self.position, on_road
        )
        self.total_reward += reward

        # Q-update for the previous (state, action) pair
        if self._prev_state is not None:
            self._update_q(self._prev_state, self._prev_action, reward, state)

        # ── Choose action (ε-greedy) ──────────────────────────────────────────
        if random.random() < self.epsilon:
            action = random.choice(ACTIONS)
            self.explore_pct = self.epsilon * 100
        else:
            action = self._best_action(state)
            self.explore_pct = self.epsilon * 100

        self.last_action = ACTION_NAMES[action]

        # ── Apply action ──────────────────────────────────────────────────────
        if action == 0:   # accelerate
            self.speed = min(MAX_SPEED, self.speed + self.ACCEL_STEP)
        elif action == 1: # brake
            self.speed = max(0, self.speed - self.ACCEL_STEP * 0.8)
        elif action == 2: # steer left
            self.lane_x -= self.STEER_STEP
        elif action == 3: # steer right
            self.lane_x += self.STEER_STEP
        # action 4 = coast: do nothing

        # Clamp lane to road
        self.lane_x = max(-road_half_w, min(road_half_w, self.lane_x))

        # Always move forward (AI never reverses)
        forward = self.BASE_FORWARD + max(0.0, self.speed * 0.1)
        self.position = (self.position + forward) % TRACK_LEN

        # Decay exploration
        self.epsilon = max(EPSILON_MIN, self.epsilon * EPSILON_DECAY)

        # Store for next frame's Q-update
        self._prev_state  = state
        self._prev_action = action

        return forward

    def draw_debug(self, surface: "pygame.Surface", font: "pygame.font.Font") -> None:
        """Draw a small AI debug panel in the bottom-right corner."""
        import pygame
        lines = [
            ("Q-Learning AI",          (0, 255, 255)),
            (f"Action: {self.last_action}",     (255, 255, 255)),
            (f"Explore: {self.explore_pct:.1f}%", (255, 200, 0)),
            (f"Reward:  {self.total_reward:.0f}", (180, 255, 180)),
            (f"Speed:   {self.speed:.0f}",       (255, 255, 255)),
        ]
        x, y = surface.get_width() - 210, surface.get_height() - 130
        bg = pygame.Surface((200, 120), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))
        surface.blit(bg, (x - 5, y - 5))
        for text, col in lines:
            surface.blit(font.render(text, True, col), (x, y))
            y += 22