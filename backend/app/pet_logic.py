"""Pure pet-simulation logic.

Deliberately free of any database / Redis / FastAPI imports so it can be unit
tested in isolation and reasoned about easily. Everything operates on a plain
``dict`` describing a pet ("state") plus an absolute ``now`` timestamp (epoch
seconds). Decay is computed lazily: instead of running a background ticker we
store ``last_update`` and, whenever the state is read or mutated, fast-forward
the simulation by the elapsed wall-clock time. This makes the server stateless
between requests and robust to restarts.
"""

from __future__ import annotations

import random
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Tuning constants (seconds unless noted). Tweak to taste.
# ---------------------------------------------------------------------------
HATCH_SECONDS = 21  # egg -> pet (kept short so testers aren't waiting around)
RUMBLE_AT = HATCH_SECONDS / 3        # egg starts wobbling at 1/3 of the way
CRACK_AT = HATCH_SECONDS * 2 / 3     # egg cracks at 2/3 of the way

MAX_STAT = 4.0  # hunger / happiness / health are 0..4 "hearts"

HUNGER_DECAY_SECONDS = 180.0      # lose 1 hunger heart every 3 min
HAPPINESS_DECAY_SECONDS = 240.0   # lose 1 happiness heart every 4 min
HEALTH_DECAY_SECONDS = 120.0      # lose 1 health heart per 2 min while neglected
HEALTH_REGEN_SECONDS = 300.0      # slowly recover health when well cared for
POOP_INTERVAL_SECONDS = 200.0     # a new poop appears this often
SICK_POOP_THRESHOLD = 3           # this many poops -> falls sick

SPECIES = ("dog", "cat", "frog", "rabbit")


def new_egg(now: Optional[float] = None) -> dict:
    """Return a fresh egg state. The species is chosen now but hidden until
    hatch so the reveal can be deterministic across reloads."""
    now = time.time() if now is None else now
    return {
        "species": "egg",
        # The creature the egg will become; revealed at hatch.
        "hatch_species": random.choice(SPECIES),
        "stage": "egg",
        "name": "",
        "born_at": now,
        "hatched_at": None,
        "hunger": MAX_STAT,
        "happiness": MAX_STAT,
        "health": MAX_STAT,
        "discipline": 0,
        "weight": 5,
        "age_seconds": 0.0,
        "is_sick": False,
        "poop": 0,
        "poop_timer": 0.0,
        "lights_off": False,
        "alive": True,
        "last_update": now,
    }


def _clamp(value: float, low: float = 0.0, high: float = MAX_STAT) -> float:
    return max(low, min(high, value))


def is_ready_to_hatch(state: dict, now: Optional[float] = None) -> bool:
    now = time.time() if now is None else now
    return state.get("species") == "egg" and (now - state["born_at"]) >= HATCH_SECONDS


def egg_phase(state: dict, now: Optional[float] = None) -> str:
    """Animation phase for the egg, driven entirely off elapsed time so the
    frontend and backend agree no matter when the page is loaded."""
    now = time.time() if now is None else now
    elapsed = now - state["born_at"]
    if elapsed >= HATCH_SECONDS:
        return "hatching"
    if elapsed >= CRACK_AT:
        return "cracking"
    if elapsed >= RUMBLE_AT:
        return "rumbling"
    return "idle"


def simulate(state: dict, now: Optional[float] = None) -> dict:
    """Advance ``state`` in place to ``now`` and return it."""
    now = time.time() if now is None else now
    elapsed = now - state["last_update"]
    if elapsed <= 0:
        state["last_update"] = now
        return state

    # Eggs only age; their stats are frozen until they hatch.
    if state["species"] == "egg":
        state["age_seconds"] += elapsed
        state["last_update"] = now
        return state

    # Sleeping pets (lights off) decay much more slowly.
    rate = 0.25 if state.get("lights_off") else 1.0

    state["hunger"] = _clamp(state["hunger"] - rate * elapsed / HUNGER_DECAY_SECONDS)
    state["happiness"] = _clamp(
        state["happiness"] - rate * elapsed / HAPPINESS_DECAY_SECONDS
    )

    # Poop accumulates over time (not while asleep).
    if not state.get("lights_off"):
        state["poop_timer"] += elapsed
        while state["poop_timer"] >= POOP_INTERVAL_SECONDS:
            state["poop_timer"] -= POOP_INTERVAL_SECONDS
            state["poop"] += 1

    # Health: drains when neglected (empty hunger/happiness or too much poop),
    # otherwise slowly regenerates.
    neglected = (
        state["hunger"] <= 0
        or state["happiness"] <= 0
        or state["poop"] >= SICK_POOP_THRESHOLD
    )
    if neglected:
        state["health"] = _clamp(state["health"] - elapsed / HEALTH_DECAY_SECONDS)
    else:
        state["health"] = _clamp(state["health"] + elapsed / HEALTH_REGEN_SECONDS)

    state["age_seconds"] += elapsed
    state["is_sick"] = state["health"] <= 1.0 or state["poop"] >= SICK_POOP_THRESHOLD
    state["last_update"] = now
    return state


def hatch(state: dict, now: Optional[float] = None) -> dict:
    """Turn a ready egg into its creature. No-op if not an egg/not ready."""
    now = time.time() if now is None else now
    if state["species"] != "egg" or not is_ready_to_hatch(state, now):
        return state
    state["species"] = state.get("hatch_species") or random.choice(SPECIES)
    state["stage"] = "baby"
    state["hatched_at"] = now
    state["last_update"] = now
    return state


# ---------------------------------------------------------------------------
# Actions (the three-button menu / icon actions on the device)
# ---------------------------------------------------------------------------
ACTIONS = (
    "feed_meal",
    "feed_snack",
    "play",
    "clean",
    "medicine",
    "discipline",
    "toggle_light",
)


def apply_action(state: dict, action: str, now: Optional[float] = None) -> dict:
    """Apply a user action after fast-forwarding decay. Returns the new state.

    Raises ``ValueError`` for unknown actions. Actions on an egg are ignored
    (you can't feed an egg) except ``toggle_light``.
    """
    now = time.time() if now is None else now
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {action}")

    simulate(state, now)

    if action == "toggle_light":
        state["lights_off"] = not state.get("lights_off")
        return state

    if state["species"] == "egg":
        return state  # can't interact with an egg yet

    if action == "feed_meal":
        state["hunger"] = _clamp(state["hunger"] + 1)
        state["weight"] += 2
    elif action == "feed_snack":
        state["happiness"] = _clamp(state["happiness"] + 1)
        state["weight"] += 1
    elif action == "play":
        state["happiness"] = _clamp(state["happiness"] + 1)
        state["weight"] = max(1, state["weight"] - 1)
    elif action == "clean":
        state["poop"] = 0
    elif action == "medicine":
        if state["is_sick"]:
            state["health"] = MAX_STAT
            state["is_sick"] = False
    elif action == "discipline":
        state["discipline"] = min(100, state["discipline"] + 10)

    # Re-evaluate sickness after the action.
    state["is_sick"] = state["health"] <= 1.0 or state["poop"] >= SICK_POOP_THRESHOLD
    return state


def needs_attention(state: dict) -> bool:
    """Whether the device should blink for attention."""
    if state["species"] == "egg":
        return False
    return (
        state["hunger"] <= 1
        or state["happiness"] <= 1
        or state["is_sick"]
        or state["poop"] > 0
    )


def public_view(state: dict, now: Optional[float] = None) -> dict:
    """Shape the state for the API/frontend: rounds floats to hearts, exposes
    derived fields, and hides the secret hatch species while still an egg."""
    now = time.time() if now is None else now
    phase = egg_phase(state, now) if state["species"] == "egg" else None
    return {
        "species": state["species"],
        "stage": state["stage"],
        "name": state["name"],
        "born_at": state["born_at"],
        "hatched_at": state["hatched_at"],
        "age_seconds": round(state["age_seconds"], 1),
        "hunger": round(state["hunger"], 2),
        "happiness": round(state["happiness"], 2),
        "health": round(state["health"], 2),
        "hunger_hearts": round(state["hunger"]),
        "happiness_hearts": round(state["happiness"]),
        "health_hearts": round(state["health"]),
        "discipline": state["discipline"],
        "weight": state["weight"],
        "is_sick": state["is_sick"],
        "poop": state["poop"],
        "lights_off": state["lights_off"],
        "alive": state["alive"],
        "needs_attention": needs_attention(state),
        "egg_phase": phase,
        "ready_to_hatch": is_ready_to_hatch(state, now),
        "server_time": now,
    }
