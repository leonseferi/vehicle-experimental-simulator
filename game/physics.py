"""
game/physics.py – Vehicle physics simulation.

All physics is encapsulated in VehicleState, which is updated once per
game frame by calling update(). Keeping physics separate makes it easy
to unit-test, tweak constants, and extend (e.g. adding nitrous, damage).
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field

from config import (
    GRAVITY, AIR_DENSITY, VEHICLE_MASS, FRONTAL_AREA,
    DRAG_COEFFICIENT, ROLLING_RESISTANCE_COEFF, ENGINE_FORCE,
    MAX_VELOCITY, MIN_VELOCITY, MAX_ACCELERATION, MIN_ACCELERATION,
    GEAR_RATIOS, ROAD_SLOPE,
)


@dataclass
class VehicleState:
    """
    Holds all mutable physics state for the player vehicle.
    Reset by creating a new instance; clone with dataclasses.replace().
    """
    # Dynamic values
    velocity:      float = 0.0    # m/s
    position:      float = 0.0    # m (along track)
    acceleration:  float = 0.0    # m/s² (last calculated)
    acceleration_clamped: float = 0.0

    # Derived / displayed values
    air_resistance:         float = 0.0
    rolling_resistance:     float = 0.0
    drag_losses:            float = 0.0
    rr_losses:              float = 0.0
    fuel_consumption_rate:  float = 0.0
    engine_force_current:   float = 0.0

    # Counters / wear
    total_distance: float = 0.0
    tire_wear:      float = 0.0
    lap_time:       float = 0.0

    # Fixed configuration
    mass:               float = field(default=VEHICLE_MASS, repr=False)
    frontal_area:       float = field(default=FRONTAL_AREA, repr=False)
    drag_coeff:         float = field(default=DRAG_COEFFICIENT, repr=False)
    rr_coeff:           float = field(default=ROLLING_RESISTANCE_COEFF, repr=False)
    base_engine_force:  float = field(default=ENGINE_FORCE, repr=False)
    gear_ratios:        list  = field(default_factory=lambda: list(GEAR_RATIOS), repr=False)
    current_gear:       int   = 3
    slope:              float = field(default=ROAD_SLOPE, repr=False)

    # Cosmetic / sensor
    engine_temperature: float = 90.0
    brake_temperature:  float = 30.0
    nitro_level:        float = 100.0
    engine_rpm:         int   = 0
    gf_force:           float = field(init=False)

    def __post_init__(self) -> None:
        self.gf_force = GRAVITY * self.mass

    # ── Frame update ──────────────────────────────────────────────────────────

    def update(
        self,
        dt: float,
        moving: bool,
        throttle_boost: float = 0.0,
        braking: bool = False,
    ) -> None:
        """
        Advance physics by *dt* seconds.

        Parameters
        ----------
        dt            : seconds since last frame
        moving        : True if any drive key is pressed
        throttle_boost: extra engine force (e.g. from TAB / nitrous)
        braking       : True if down-arrow held
        """
        self.lap_time += dt

        if not moving:
            # Coasting: preserve last state (no active acceleration)
            return

        slope_sin  = math.sin(math.radians(self.slope))
        slope_cos  = math.cos(math.radians(self.slope))
        slope_inf  = GRAVITY * slope_sin

        engine_f   = (self.base_engine_force + throttle_boost) if not braking else (self.base_engine_force - 1500)

        # Air resistance
        self.air_resistance = (
            0.5 * AIR_DENSITY * self.frontal_area
            * self.drag_coeff * (self.velocity ** 2)
        )

        # Rolling resistance (simplified; incorporates air drag term for realism)
        self.rolling_resistance = (
            self.rr_coeff * self.mass * GRAVITY * slope_cos
            * self.air_resistance / 10_000
        )

        net_force = engine_f - self.air_resistance - self.rolling_resistance + slope_inf * self.mass

        self.acceleration         = net_force / self.mass
        self.acceleration_clamped = max(MIN_ACCELERATION, min(self.acceleration, MAX_ACCELERATION))
        self.engine_force_current = engine_f

        # Kinematics
        self.velocity += (self.acceleration * dt) / 2
        self.position += self.velocity * dt + 0.5 * self.acceleration * (dt ** 2)
        self.velocity  = max(MIN_VELOCITY, min(MAX_VELOCITY, self.velocity))

        # Losses
        self.drag_losses = (
            0.5 * AIR_DENSITY * self.velocity * self.frontal_area * self.drag_coeff
        ) * dt
        self.rr_losses = self.rr_coeff * self.mass * GRAVITY * (self.velocity * 0.001)

        # Fuel consumption
        engine_efficiency = 0.5
        self.fuel_consumption_rate = (
            (engine_f + self.velocity) / engine_efficiency
            + self.drag_losses + self.rr_losses
        ) / 3

        # Distance & wear
        self.total_distance += self.velocity * dt

    def apply_vehicle_params(self, params: dict) -> None:
        """
        Apply a parameter dict (from slider customisation) to this state.
        Keys are matched loosely to avoid tight coupling with slider labels.
        """
        if "vehicle_mass" in params:
            self.mass = params["vehicle_mass"]
            self.gf_force = GRAVITY * self.mass
        if "drag_coefficient" in params or "Modify Drag Coefficient" in params:
            self.drag_coeff = params.get("drag_coefficient",
                              params.get("Modify Drag Coefficient", self.drag_coeff))
        if "engine_force" in params:
            self.base_engine_force = params["engine_force"]