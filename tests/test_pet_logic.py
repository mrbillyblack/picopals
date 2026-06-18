"""Unit tests for the pure simulation logic (no DB, no Redis, no HTTP)."""

import app.pet_logic as logic


def test_new_egg_defaults():
    egg = logic.new_egg(now=1000.0)
    assert egg["species"] == "egg"
    assert egg["hatch_species"] in logic.SPECIES
    assert egg["hunger"] == logic.MAX_STAT
    assert egg["born_at"] == 1000.0
    assert egg["last_update"] == 1000.0


def test_egg_does_not_decay():
    egg = logic.new_egg(now=0.0)
    logic.simulate(egg, now=10_000.0)  # way past any decay window
    assert egg["hunger"] == logic.MAX_STAT
    assert egg["happiness"] == logic.MAX_STAT
    assert egg["age_seconds"] == 10_000.0


def test_egg_phase_progression():
    egg = logic.new_egg(now=0.0)
    assert logic.egg_phase(egg, now=5) == "idle"
    assert logic.egg_phase(egg, now=25) == "rumbling"
    assert logic.egg_phase(egg, now=45) == "cracking"
    assert logic.egg_phase(egg, now=60) == "hatching"


def test_ready_to_hatch_boundary():
    egg = logic.new_egg(now=0.0)
    assert not logic.is_ready_to_hatch(egg, now=logic.HATCH_SECONDS - 1)
    assert logic.is_ready_to_hatch(egg, now=logic.HATCH_SECONDS)


def test_hatch_reveals_chosen_species():
    egg = logic.new_egg(now=0.0)
    egg["hatch_species"] = "frog"
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    assert egg["species"] == "frog"
    assert egg["stage"] == "baby"
    assert egg["hatched_at"] == logic.HATCH_SECONDS


def test_hatch_noop_before_ready():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=10)
    assert egg["species"] == "egg"


def test_hunger_decays_one_heart_per_window():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    start = egg["last_update"]
    logic.simulate(egg, now=start + logic.HUNGER_DECAY_SECONDS)
    assert abs(egg["hunger"] - (logic.MAX_STAT - 1)) < 1e-6


def test_hunger_clamps_at_zero():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    logic.simulate(egg, now=10**6)
    assert egg["hunger"] == 0.0
    assert egg["happiness"] == 0.0


def test_feeding_raises_hunger_and_weight():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    # decay a bit first
    t = egg["last_update"] + logic.HUNGER_DECAY_SECONDS
    logic.apply_action(egg, "feed_meal", now=t)
    assert egg["hunger"] == logic.MAX_STAT  # back to full (was 3, +1)
    assert egg["weight"] == 7  # 5 + 2


def test_play_raises_happiness_lowers_weight():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    egg["happiness"] = 2.0
    egg["weight"] = 5
    logic.apply_action(egg, "play", now=egg["last_update"])
    assert egg["happiness"] == 3.0
    assert egg["weight"] == 4


def test_poop_accumulates_and_clean_resets():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    t = egg["last_update"] + 2 * logic.POOP_INTERVAL_SECONDS + 1
    logic.simulate(egg, now=t)
    assert egg["poop"] >= 2
    logic.apply_action(egg, "clean", now=t)
    assert egg["poop"] == 0


def test_neglect_makes_sick_and_medicine_cures():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    logic.simulate(egg, now=10**6)  # fully neglected
    assert egg["is_sick"]
    # clean first so poop doesn't immediately re-sicken, then medicate
    logic.apply_action(egg, "clean", now=10**6)
    logic.apply_action(egg, "medicine", now=10**6)
    assert not egg["is_sick"]
    assert egg["health"] == logic.MAX_STAT


def test_lights_off_slows_decay():
    fast = logic.new_egg(now=0.0)
    slow = logic.new_egg(now=0.0)
    for e in (fast, slow):
        logic.hatch(e, now=logic.HATCH_SECONDS)
    slow["lights_off"] = True
    span = logic.HUNGER_DECAY_SECONDS
    logic.simulate(fast, now=fast["last_update"] + span)
    logic.simulate(slow, now=slow["last_update"] + span)
    assert slow["hunger"] > fast["hunger"]


def test_unknown_action_raises():
    egg = logic.new_egg(now=0.0)
    logic.hatch(egg, now=logic.HATCH_SECONDS)
    try:
        logic.apply_action(egg, "explode", now=egg["last_update"])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown action")


def test_public_view_hides_hatch_species_for_egg():
    egg = logic.new_egg(now=0.0)
    view = logic.public_view(egg, now=5)
    assert "hatch_species" not in view
    assert view["egg_phase"] == "idle"
    assert view["species"] == "egg"
