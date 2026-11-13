from __future__ import annotations

import pandas as pd

from scripts.c8a_rejoin_anatomy import find_reentry_windows, gap_at_reentry


def synthetic_frame() -> pd.DataFrame:
    rows = []
    for tick in range(0, 51, 2):
        t = tick / 5.0
        rows.extend(
            [
                {
                    "tick": tick,
                    "t_s": t,
                    "drv": "EGO",
                    "s": 100.0 + tick,
                    "lat": 8.0 if 2 <= tick <= 6 else 0.0,
                    "speed": 10.0,
                    "offtrack": 1 if 2 <= tick <= 6 else 0,
                    "car_car": 1 if tick == 10 else 0,
                },
                {
                    "tick": tick,
                    "t_s": t,
                    "drv": "BEHIND",
                    "s": 80.0 + tick,
                    "lat": 0.0,
                    "speed": 10.0,
                    "offtrack": 0,
                    "car_car": 0,
                },
                {
                    "tick": tick,
                    "t_s": t,
                    "drv": "AHEAD",
                    "s": 140.0 + tick,
                    "lat": 0.0,
                    "speed": 10.0,
                    "offtrack": 0,
                    "car_car": 0,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_reentry_gap_and_direction_are_separated():
    frame = synthetic_frame()
    gap = gap_at_reentry(frame, "EGO", 8, 1000.0)
    assert gap["behind_m"] == 20.0
    assert gap["ahead_m"] == 40.0
    events = find_reentry_windows(frame, 1000.0)
    ego = [event for event in events if event["driver"] == "EGO"]
    assert len(ego) == 1
    assert ego[0]["risk_direction"] == "behind"
    assert ego[0]["offtrack_duration_s"] == 0.6
    assert ego[0]["contacts_within_5s"] == 1


def test_reentry_window_has_no_false_event_without_return():
    frame = synthetic_frame()
    frame.loc[(frame["drv"] == "EGO") & (frame["tick"] >= 8), "offtrack"] = 1
    events = find_reentry_windows(frame, 1000.0)
    assert not [event for event in events if event["driver"] == "EGO"]
