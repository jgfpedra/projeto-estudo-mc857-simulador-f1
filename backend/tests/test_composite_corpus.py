import math
import csv

import numpy as np
import pytest

from scripts.composite_corpus import (
    CorpusError,
    FrozenTrackProvider,
    _legacy_threshold_split_episode,
    assign_episode_splits,
    audit_dataset,
    build_teacher_states,
    build_residual_input,
    convert_reconstructed,
    inspect_source,
    load_pinned_solo_actor,
    pinned_solo_forward,
    pure_professor_action,
    professor_replay,
    run_teacher_labeling,
    classify_joined_families,
    convert_1f_cli,
    join_dump_with_main_csv,
)


def _row(tick=1):
    return {
        "run": "synthetic-run",
        "drv": "ALO",
        "tick": tick,
        "t_s": tick / 5,
        "geometry_id": "interlagos_v2",
        "geometry_sha256": "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
        "source_sha256": "a" * 64,
        "source_git_sha256": "b" * 64,
        "instrument_version": "composite-corpus-v1",
        "track_id": 1,
        "compound_id": 2,
        "telemetry_edge_34": [0.0] * 34,
        "traffic_features_12": [0.0] * 12,
        "speed_mps": 20.0,
        "curvature_ahead": 0.01,
        "previous_steer": 0.0,
        "previous_longitudinal": 0.0,
        "ctx": [0.0, 0.0],
        "th": 99.0,
        "brk": 99.0,
        "steer_rad": 99.0,
    }


def test_residual_input_has_frozen_16d_layout():
    result = build_residual_input([0.0] * 12, 20.0, 0.01, 0.2, -0.3)
    assert len(result) == 16
    assert result[-4:] == [0.2, 0.25, 0.2, -0.3]


def test_professor_replay_rejects_nondeterminism():
    state = {"tick": 1}
    calls = iter(([0.1, 0.2], [0.1, 0.3]))
    with pytest.raises(CorpusError, match="nondeterministic"):
        professor_replay([state], lambda _: next(calls))


class _Profile:
    def __init__(self, value):
        self.value = value

    def at(self, _s):
        return self.value


def _teacher_state(speed=20.0, lat=0.0, traffic=()):
    return {
        "s": 100.0,
        "speed": speed,
        "lat": lat,
        "x": 100.0,
        "y": lat,
        "heading": 0.0,
        "traffic": traffic,
    }


def _teacher_action(state, profile=None):
    return pure_professor_action(
        state,
        velocity_profile=profile or _Profile(20.0),
        track_len_s=1000.0,
        point_at=lambda s: (s, 0.0, 0.0),
        steer_limit_rad=lambda _speed: 1.0,
    )


def test_pure_professor_double_pass_and_longitudinal_branches():
    states = [_teacher_state(speed=18.6), _teacher_state(speed=30.0)]
    first = professor_replay(states, _teacher_action)
    second = professor_replay(states, _teacher_action)
    assert first == second
    assert first[0][1] == 0.0
    assert first[1][1] < 0.0


def test_pure_professor_traffic_cap_and_lateral_shift():
    state = _teacher_state(
        speed=30.0,
        traffic=[{"s": 120.0, "lat": 0.0, "speed": 10.0}],
    )
    capped = _teacher_action(state, _Profile(60.0))
    assert capped[1] < 0.0
    shifted = _teacher_action(_teacher_state(
        speed=20.0,
        traffic=[{"s": 120.0, "lat": 1.0, "speed": 10.0}],
    ))
    inactive = _teacher_action(_teacher_state(
        speed=20.0,
        traffic=[{"s": 120.0, "lat": 4.0, "speed": 10.0}],
    ))
    assert shifted[0] != inactive[0]


def test_pure_professor_action_range_and_engine_inverse():
    state = _teacher_state()
    action = _teacher_action(state)
    assert len(action) == 2
    assert all(-1.0 <= value <= 1.0 for value in action)
    from backend.model_train.f1_env import F1MultiContextEnv
    throttle, brake, steer_rad = F1MultiContextEnv.action_to_controls(
        action, 20.0
    )
    assert action[1] == pytest.approx(throttle - brake)
    assert action[0] == pytest.approx(
        steer_rad / F1MultiContextEnv.steer_limit_rad(20.0)
    )


class _DeterministicActor:
    def __init__(self, value):
        self.value = np.asarray(value, dtype=np.float32)

    def forward_linear(self, telemetry, ctx, track_ids, compound_ids):
        assert telemetry.shape == (len(ctx), 34)
        assert np.array_equal(track_ids, np.zeros(len(ctx), dtype=np.int32))
        assert np.array_equal(compound_ids, np.zeros(len(ctx), dtype=np.int32))
        return np.repeat(self.value[None, :], len(ctx), axis=0)


def test_pinned_solo_forward_uses_zero_ids_and_double_pass():
    rows = [{"telemetry_edge_34": [0.0] * 34, "ctx": [0.0, 0.0]}]
    assert pinned_solo_forward(rows, _DeterministicActor([0.2, -0.3])) == [
        [0.20000000298023224, -0.30000001192092896]
    ]


def test_pinned_solo_forward_rejects_nondeterminism():
    class ChangingActor(_DeterministicActor):
        def __init__(self):
            super().__init__([0.0, 0.0])
            self.calls = 0

        def forward_linear(self, *args):
            self.calls += 1
            return np.full((1, 2), self.calls, dtype=np.float32)

    with pytest.raises(CorpusError, match="nondeterministic"):
        pinned_solo_forward(
            [{"telemetry_edge_34": [0.0] * 34, "ctx": [0.0, 0.0]}],
            ChangingActor(),
        )


class _Provider:
    track_len_s = 1000.0
    half_width = 6.0
    velocity_profile_config = {
        "grip_mult": 0.788,
        "sf": 0.80,
        "ds_target": 4.0,
        "smooth_window_m": 20.0,
    }

    def __init__(self):
        self.velocity_profile = _Profile(20.0)

    @staticmethod
    def point_at(s):
        return float(s) % 1000.0, 0.0, 0.0

    @staticmethod
    def project_on_path(x, y):
        return abs(float(y)), float(x) % 1000.0


def _joined_rows_for_state_builder():
    rows = []
    mains = []
    drivers = ["ALO", "HAM", "SAI", "RUS", "PIA",
               "PER", "GAS", "LEC", "VER", "NOR"]
    for index, drv in enumerate(drivers):
        row = _row(2)
        row["drv"] = drv
        row["s"] = 100.0 + index * 10.0
        row["speed_mps"] = 20.0 + index
        row["_main"] = {
            "tick": "2",
            "drv": drv,
            "s": str(row["s"]),
            "lat": "1.5",
            "speed": str(row["speed_mps"]),
            "t_s": "1.0",
        }
        rows.append(row)
        mains.append(row["_main"])
    return rows, mains


def test_state_builder_reconstructs_pose_and_exact_traffic_snapshot():
    joined, mains = _joined_rows_for_state_builder()
    states = build_teacher_states(
        joined,
        {2: mains},
        track_providers={"interlagos_v2": _Provider()},
    )
    assert len(states) == 10
    assert all(len(state["traffic"]) == 9 for state in states)
    state = states[0]
    assert state["x"] == pytest.approx(100.0)
    assert state["y"] == pytest.approx(1.5)
    assert _Provider.project_on_path(state["x"], state["y"]) == pytest.approx(
        (state["lat"], state["s"])
    )


def test_state_builder_rejects_incomplete_or_duplicate_tick():
    joined, mains = _joined_rows_for_state_builder()
    with pytest.raises(CorpusError, match="exactly 10"):
        build_teacher_states(
            joined[:-1],
            {2: mains[:-1]},
            track_providers={"interlagos_v2": _Provider()},
        )
    duplicate = list(mains)
    duplicate[-1] = dict(duplicate[0])
    with pytest.raises(CorpusError, match="duplicate"):
        build_teacher_states(
            joined,
            {2: duplicate},
            track_providers={"interlagos_v2": _Provider()},
        )


def test_state_builder_and_teacher_are_stateless():
    joined, mains = _joined_rows_for_state_builder()
    kwargs = {
        "track_providers": {"interlagos_v2": _Provider()},
    }
    first = build_teacher_states(joined, {2: mains}, **kwargs)
    second = build_teacher_states(joined, {2: mains}, **kwargs)
    assert first == second
    provider = _Provider()
    actions1 = professor_replay(
        first,
        lambda state: pure_professor_action(
            state,
            velocity_profile=provider.velocity_profile,
            track_len_s=provider.track_len_s,
            point_at=provider.point_at,
            steer_limit_rad=lambda _speed: 1.0,
            half_width=provider.half_width,
        ),
    )
    actions2 = professor_replay(
        second,
        lambda state: pure_professor_action(
            state,
            velocity_profile=provider.velocity_profile,
            track_len_s=provider.track_len_s,
            point_at=provider.point_at,
            steer_limit_rad=lambda _speed: 1.0,
            half_width=provider.half_width,
        ),
    )
    assert actions1 == actions2


def test_run_teacher_labeling_adds_state_builder_audit(tmp_path):
    joined, mains = _joined_rows_for_state_builder()
    dump = tmp_path / "dump.jsonl.gz"
    import gzip
    import json
    with gzip.open(dump, "wt", encoding="utf-8") as stream:
        stream.write(json.dumps({
            "_schema": "composite-corpus-dump-v3",
            "geometry_id": "interlagos_v2",
            "geometry_sha256": _row()["geometry_sha256"],
            "instrument_version": "composite-corpus-dump-v3",
            "run": "synthetic-run",
        }) + "\n")
        for row in joined:
            stream.write(json.dumps({
                key: value for key, value in row.items()
                if key != "_main"
            }) + "\n")
    main = tmp_path / "main.csv"
    with main.open("w", encoding="utf-8", newline="") as stream:
        stream.write(
            "# grid_order=['ALO', 'HAM', 'SAI', 'RUS', 'PIA', 'PER', "
            "'GAS', 'LEC', 'VER', 'NOR']\n"
        )
        stream.write("tick,t_s,drv,speed,s,lat,offtrack,authority\n")
        for item in mains:
            stream.write(
                f"{item['tick']},{item['t_s']},{item['drv']},"
                f"{item['speed']},{item['s']},{item['lat']},0,professor\n"
            )
    dataset, audit = run_teacher_labeling(
        dump,
        main,
        source_git_sha256="b" * 64,
        track_providers={"interlagos_v2": _Provider()},
        actor=_DeterministicActor([0.1, 0.2]),
        keras_path=tmp_path / "missing.keras",
        npz_path=tmp_path / "missing.npz",
    )
    assert len(dataset["records"]) == 10
    assert audit["state_builder"]["pose_formula"].startswith("point_at")
    assert audit["state_builder"]["traffic_source"] == (
        "f1_env.py:803-808:_all_cars_snapshot"
    )
    assert audit["split_rule"] == "rank-80/10/10-per-run-v1"
    assert audit["split_counts"] == {
        "train": 8, "validation": 1, "test": 1,
    }


def test_frozen_track_providers_match_verified_geometry():
    expected = {
        "interlagos": 4160.436950117386,
        "Monaco": 3335.2345774147834,
    }
    for name, length in expected.items():
        provider = FrozenTrackProvider(name)
        assert provider.track_len_s == pytest.approx(length, abs=1e-6)
        assert provider.half_width == pytest.approx(
            provider.track.width_m / 2.0, abs=1e-12
        )
        assert provider.geometry_sha256 == (
            "c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613"
            if name == "interlagos"
            else "af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2"
        )


def test_frozen_track_provider_roundtrips_real_geometry():
    for name in ("interlagos", "Monaco"):
        provider = FrozenTrackProvider(name)
        uniform = np.linspace(
            0.0, provider.track_len_s, 4000, endpoint=False
        )
        safe = []
        for s in uniform:
            checks = []
            for lat in (-3.0, 0.0, 3.0):
                x, y, _ = provider.point_at(float(s))
                heading = provider.point_at(float(s))[2]
                x += -np.sin(heading) * lat
                y += np.cos(heading) * lat
                _, projected_s, _, signed_lat = provider.project_on_path(x, y)
                delta_s = abs((projected_s - float(s) + provider.track_len_s / 2)
                              % provider.track_len_s - provider.track_len_s / 2)
                checks.append(delta_s <= 1e-6 and abs(signed_lat - lat) <= 1e-6)
            if all(checks):
                safe.append(float(s))
        assert len(safe) >= 200
        for index in np.linspace(0, len(safe) - 1, 200).astype(int):
            s = safe[index]
            for lat in (-3.0, 0.0, 3.0):
                x, y, _ = provider.point_at(float(s))
                heading = provider.point_at(float(s))[2]
                x += -np.sin(heading) * lat
                y += np.cos(heading) * lat
                _, projected_s, _, signed_lat = provider.project_on_path(x, y)
                delta_s = abs((projected_s - float(s) + provider.track_len_s / 2)
                              % provider.track_len_s - provider.track_len_s / 2)
                assert delta_s <= 1e-6
                assert abs(signed_lat - lat) <= 1e-6


def test_conversion_ignores_recorded_student_actions_and_uses_professor():
    dataset = convert_reconstructed(
        [_row()],
        professor_actions=[[0.4, -0.2]],
        solo_linear=[[0.1, -0.1]],
        episode_splits={("synthetic-run", "ALO"): "train"},
    )
    record = dataset["records"][0]
    assert record["r_targets"] == [
        math.atanh(0.4) - 0.1,
        math.atanh(-0.2) + 0.1,
    ]
    assert 99.0 not in record["r_targets"]


def test_conversion_rejects_out_of_order_episode_rows():
    with pytest.raises(CorpusError, match="out of order"):
        convert_reconstructed(
            [_row(2), _row(1)],
            professor_actions=[[0.0, 0.0], [0.0, 0.0]],
            solo_linear=[[0.0, 0.0], [0.0, 0.0]],
            episode_splits={("synthetic-run", "ALO"): "train"},
        )


def test_conversion_rejects_divergent_geometry_hash():
    row = _row()
    row["geometry_sha256"] = "0" * 64
    with pytest.raises(CorpusError, match="geometry_sha256"):
        convert_reconstructed(
            [row],
            professor_actions=[[0.0, 0.0]],
            solo_linear=[[0.0, 0.0]],
            episode_splits={("synthetic-run", "ALO"): "train"},
        )


def test_split_is_episode_stable_and_audit_has_checksums():
    rows = [_row(1), _row(2)]
    dataset = convert_reconstructed(
        rows,
        professor_actions=[[0.0, 0.0], [0.0, 0.0]],
        solo_linear=[[0.0, 0.0], [0.0, 0.0]],
        episode_splits={("synthetic-run", "ALO"): "validation"},
    )
    assert len({r["split"] for r in dataset["records"]}) == 1
    assert {r["split"] for r in dataset["records"]} == {"validation"}
    audit = audit_dataset(dataset)
    assert audit["record_count"] == 2
    assert audit["split_rule"] == "rank-80/10/10-per-run-v1"
    assert len(audit["dataset_sha256"]) == 64


def test_assign_episode_splits_rank_counts_idempotence_and_small_population():
    drivers = [f"DRV-{index:02d}" for index in range(10)]
    first = assign_episode_splits("synthetic-run", drivers)
    second = assign_episode_splits("synthetic-run", drivers)
    assert first == second
    assert {
        split: sum(value == split for value in first.values())
        for split in ("train", "validation", "test")
    } == {"train": 8, "validation": 1, "test": 1}

    assert {
        split: sum(value == split for value in assign_episode_splits(
            "three-episode-run", ("A", "B", "C")
        ).values())
        for split in ("train", "validation", "test")
    } == {"train": 1, "validation": 1, "test": 1}
    with pytest.raises(CorpusError, match="cannot split fewer than 3 episodes"):
        assign_episode_splits("two-episode-run", ("A", "B"))


def test_rank_splits_match_pinned_real_membership_and_are_per_run_stable():
    drivers = ("PIA", "NOR", "LEC", "HAM", "PER", "RUS", "GAS", "ALO", "SAI", "VER")
    expected = {
        "A_ON_dump.jsonl": {
            "train": {"PIA", "NOR", "LEC", "HAM", "PER", "RUS", "GAS", "ALO"},
            "validation": {"SAI"},
            "test": {"VER"},
        },
        "B_ON_dump.jsonl": {
            "train": {"PIA", "RUS", "GAS", "LEC", "HAM", "NOR", "PER", "ALO"},
            "validation": {"VER"},
            "test": {"SAI"},
        },
    }
    actual_by_run = {
        run: assign_episode_splits(run, drivers)
        for run in expected
    }
    for run, splits in expected.items():
        actual = actual_by_run[run]
        assert {
            split: {drv for drv, assigned in actual.items() if assigned == split}
            for split in ("train", "validation", "test")
        } == splits
    assert actual_by_run["A_ON_dump.jsonl"] == assign_episode_splits(
        "A_ON_dump.jsonl", tuple(reversed(drivers))
    )


def test_legacy_threshold_split_preserves_real_case_a_8_2_0_counts():
    drivers = ("PIA", "NOR", "LEC", "HAM", "PER", "RUS", "GAS", "ALO", "SAI", "VER")
    legacy_counts = {
        split: sum(
            _legacy_threshold_split_episode("A_ON_dump.jsonl", drv) == split
            for drv in drivers
        )
        for split in ("train", "validation", "test")
    }
    assert legacy_counts == {"train": 8, "validation": 2, "test": 0}


def test_convert_reconstructed_requires_and_uses_episode_split_map():
    row = _row()
    actions = [[0.0, 0.0]]
    with pytest.raises(CorpusError, match="episode_splits is required"):
        convert_reconstructed(
            [row], professor_actions=actions, solo_linear=actions
        )
    with pytest.raises(CorpusError, match="episode missing from episode_splits"):
        convert_reconstructed(
            [row],
            professor_actions=actions,
            solo_linear=actions,
            episode_splits={("synthetic-run", "NOR"): "test"},
        )
    dataset = convert_reconstructed(
        [row],
        professor_actions=actions,
        solo_linear=actions,
        episode_splits={("synthetic-run", "ALO"): "test"},
    )
    assert dataset["records"][0]["split"] == "test"


def test_pinned_composite_1f_dry_run_split_counts(tmp_path):
    result = convert_1f_cli(
        case="all",
        out_dir=tmp_path / "must-not-be-created",
        write=False,
        source_git_sha256="7ef87c8f4e880b979c6dc8c77915a8f57356dd03",
    )
    assert set(result) == {"A", "B"}
    for case in ("A", "B"):
        assert result[case]["record_count"] == 30000
        assert result[case]["episode_count"] == 10
        assert result[case]["split_counts"] == {
            "train": 24000,
            "validation": 3000,
            "test": 3000,
        }
    assert not (tmp_path / "must-not-be-created").exists()


def test_census_rejects_measured_res16d_without_reconstruction():
    result = inspect_source(
        "experiments/anti-d3-1/1_controle.csv",
        expected_geometry_id="interlagos_v2",
        expected_geometry_sha256="164876196eb12174",
    )
    assert result["status"] == "rejected"
    assert result["reason"].startswith("reconstruction_required:")


def test_join_classifies_launch_nose_to_tail_rejoin_and_hesitation(tmp_path):
    dump_rows = []
    main_rows = []
    for tick in range(10):
        t_s = 61.0 + tick * 0.2
        for drv, s, speed, off, authority in (
            ("ALO", 100.0 + tick, 20.0, 0, "professor"),
            ("VER", 125.0 + tick, 19.0, 0, "professor"),
            ("PIA", 200.0 + tick, 0.2, 1, "rejoin"),
        ):
            dump_rows.append({
                "run": "run-a", "drv": drv, "tick": tick,
                "source_sha256": "a" * 64,
            })
            main_rows.append({
                "tick": str(tick), "t_s": str(t_s), "drv": drv,
                "speed": str(speed),
                "s": str(s), "lat": "0.0", "offtrack": str(off),
                "authority": authority,
            })
    # Add a launch sample to prove the t<60 family is based on the main CSV.
    dump_rows.append({"run": "run-a", "drv": "ALO", "tick": 10,
                      "source_sha256": "a" * 64})
    main_rows.append({
        "tick": "10", "t_s": "30.0", "drv": "ALO", "speed": "10.0",
        "s": "50.0", "lat": "0.0", "offtrack": "0", "authority": "professor",
    })
    grid_order = ["ALO", "HAM", "SAI", "RUS", "PIA", "PER", "GAS", "LEC", "VER", "NOR"]
    grid_index = {driver: index for index, driver in enumerate(grid_order)}
    main_rows.sort(key=lambda row: (int(row["tick"]), grid_index[row["drv"]]))
    path = tmp_path / "main.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        stream.write(
            "# track_frozen_sha256=synthetic | run=run-a | note=raw | "
            "x=a=b | grid_order=['ALO', 'HAM', 'SAI', 'RUS', 'PIA', 'PER', "
            "'GAS', 'LEC', 'VER', 'NOR']\n"
        )
        writer = csv.DictWriter(stream, fieldnames=[
            "tick", "t_s", "drv", "speed", "s", "lat", "offtrack", "authority",
        ])
        writer.writeheader()
        writer.writerows(main_rows)
    joined, audit = join_dump_with_main_csv(
        dump_rows, path, track_len_s=1000.0
    )
    result = classify_joined_families(joined, track_len_s=1000.0)
    assert audit["joined_rows"] == 16
    assert audit["main_csv_metadata"] == {
        "track_frozen_sha256": "synthetic",
        "run": "run-a",
        "note": "raw",
        "x": "a=b",
        "grid_order": "['ALO', 'HAM', 'SAI', 'RUS', 'PIA', 'PER', 'GAS', 'LEC', 'VER', 'NOR']",
    }
    assert audit["paired_by_drv"]["ALO"] == {
        "paired": 6, "total": 11, "fraction": 6 / 11,
    }
    assert len(audit["pair_sha256"]) == 64
    assert result["family_counts"]["launch_t_lt_60s"] == 1
    assert result["family_counts"]["nose_to_tail_gt_60s"] >= 1
    assert result["family_counts"]["monaco_rejoin"] >= 1
    assert result["family_counts"]["hesitations_post_reentry_le_10s"] >= 1


def test_join_rejects_missing_main_key(tmp_path):
    path = tmp_path / "main.csv"
    path.write_text(
        "# track_frozen_sha256=synthetic | grid_order=['ALO']\n"
        "tick,t_s,drv,speed,s,lat,offtrack,authority\n"
        "0,0.0,ALO,1,1,0,0,professor\n",
        encoding="utf-8",
    )
    with pytest.raises(CorpusError, match="absent from dump"):
        join_dump_with_main_csv(
            [{"tick": 1, "drv": "ALO", "source_sha256": "a" * 64}],
            path,
            track_len_s=1000.0,
        )


def test_join_rejects_missing_metadata_header(tmp_path):
    path = tmp_path / "main.csv"
    path.write_text(
        "tick,t_s,drv,speed,s,lat,offtrack,authority\n",
        encoding="utf-8",
    )
    with pytest.raises(CorpusError, match="missing metadata header"):
        join_dump_with_main_csv(
            [], path, track_len_s=1000.0, dump_sha256="a" * 64
        )


def test_join_reports_physical_line_after_metadata_header(tmp_path):
    path = tmp_path / "main.csv"
    path.write_text(
        "# source=synthetic | grid_order=['ALO']\n"
        "tick,t_s,drv,speed,s,lat,offtrack,authority\n"
        "0,0.0,ALO,1,1,0,0,professor,unexpected\n",
        encoding="utf-8",
    )
    with pytest.raises(CorpusError, match=r"main\.csv:3: malformed CSV row"):
        join_dump_with_main_csv(
            [], path, track_len_s=1000.0, dump_sha256="a" * 64
        )


def test_join_reports_even_tick_stride_and_extras(tmp_path):
    path = tmp_path / "main.csv"
    path.write_text(
        "# source=synthetic | raw=a=b | grid_order=['ALO']\n"
        "tick,t_s,drv,speed,s,lat,offtrack,authority\n"
        "0,0.0,ALO,1,1,0,0,professor\n"
        "1,0.1,ALO,1,1,0,0,professor\n"
        "2,0.2,ALO,1,1,0,0,professor\n"
        "3,0.3,ALO,1,1,0,0,professor\n",
        encoding="utf-8",
    )
    dump_rows = [
        {"tick": tick, "drv": "ALO", "source_sha256": "a" * 64}
        for tick in range(4)
    ]
    joined, audit = join_dump_with_main_csv(
        dump_rows, path, track_len_s=1000.0
    )
    assert [row["tick"] for row in joined] == [0, 2]
    assert audit["unmatched_dump_rows"] == 2
    assert audit["paired_by_drv"]["ALO"] == {
        "paired": 2, "total": 4, "fraction": 0.5,
    }


def _write_grid_main(path, rows, metadata="grid_order=['ALO', 'SAI', 'RUS']"):
    with path.open("w", newline="", encoding="utf-8") as stream:
        stream.write(f"# source=synthetic | {metadata}\n")
        writer = csv.DictWriter(
            stream,
            fieldnames=["tick", "t_s", "drv", "speed", "s", "lat", "offtrack", "authority"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_join_accepts_production_grid_order(tmp_path):
    rows = [
        {"tick": "0", "t_s": "0", "drv": drv, "speed": "1", "s": "1",
         "lat": "0", "offtrack": "0", "authority": "policy"}
        for drv in ("ALO", "SAI", "RUS")
    ]
    path = tmp_path / "main.csv"
    _write_grid_main(path, rows)
    joined, _ = join_dump_with_main_csv(
        [{"tick": 0, "drv": drv, "source_sha256": "a" * 64}
         for drv in ("ALO", "SAI", "RUS")],
        path,
        track_len_s=1000.0,
    )
    assert [row["drv"] for row in joined] == ["ALO", "SAI", "RUS"]


def test_join_rejects_inverted_tick_order(tmp_path):
    path = tmp_path / "main.csv"
    _write_grid_main(path, [
        {"tick": "2", "t_s": "0", "drv": "ALO", "speed": "1", "s": "1",
         "lat": "0", "offtrack": "0", "authority": "policy"},
        {"tick": "0", "t_s": "0", "drv": "ALO", "speed": "1", "s": "1",
         "lat": "0", "offtrack": "0", "authority": "policy"},
    ])
    with pytest.raises(CorpusError, match="out of order"):
        join_dump_with_main_csv(
            [{"tick": 0, "drv": "ALO", "source_sha256": "a" * 64},
             {"tick": 2, "drv": "ALO", "source_sha256": "a" * 64}],
            path,
            track_len_s=1000.0,
        )


def test_join_rejects_duplicate_grid_key(tmp_path):
    path = tmp_path / "main.csv"
    row = {"tick": "0", "t_s": "0", "drv": "ALO", "speed": "1", "s": "1",
           "lat": "0", "offtrack": "0", "authority": "policy"}
    _write_grid_main(path, [row, row])
    with pytest.raises(CorpusError, match="duplicate JOIN key"):
        join_dump_with_main_csv(
            [{"tick": 0, "drv": "ALO", "source_sha256": "a" * 64}],
            path,
            track_len_s=1000.0,
        )


@pytest.mark.parametrize("metadata", [
    "source=synthetic",
    "grid_order=[ALO, 'SAI']",
    "grid_order=['ALO','SAI']",
])
def test_join_rejects_unparseable_grid_order(tmp_path, metadata):
    path = tmp_path / "main.csv"
    _write_grid_main(path, [], metadata=metadata)
    with pytest.raises(CorpusError, match="unparseable grid_order"):
        join_dump_with_main_csv(
            [], path, track_len_s=1000.0, dump_sha256="a" * 64
        )


def test_join_rejects_driver_outside_grid_order(tmp_path):
    path = tmp_path / "main.csv"
    _write_grid_main(path, [{
        "tick": "0", "t_s": "0", "drv": "VER", "speed": "1", "s": "1",
        "lat": "0", "offtrack": "0", "authority": "policy",
    }])
    with pytest.raises(CorpusError, match="absent from grid_order"):
        join_dump_with_main_csv(
            [{"tick": 0, "drv": "VER", "source_sha256": "a" * 64}],
            path, track_len_s=1000.0,
        )
