import gzip
import json
import pickle

import pytest

from domain.tyre import TyreCompound, TyreModel, TyreState, TYRE_CATALOG
from scripts.composite_corpus_dump import (
    CompositeCorpusDump,
    CorpusDumpError,
    load_compound_mapping,
    resolve_compound_id,
)
from scripts.composite_corpus import audit_dump_families, load_composite_dump


def _row(writer, tick=0):
    writer.write_row(
        drv="ALO",
        tick=tick,
        t_s=tick / 10,
        track_id=0,
        compound_id=1,
        telemetry_edge_34=[0.0] * 34,
        ctx=[0.0, 0.0],
        traffic_features_12=[0.0] * 12,
        speed_mps=10.0,
        curvature_ahead=0.01,
    )


def test_dump_schema_and_previous_action_are_deterministic(tmp_path):
    path = tmp_path / "dump.jsonl.gz"
    with CompositeCorpusDump(
        path,
        run="synthetic",
        geometry_id="interlagos_v2",
        geometry_sha256="c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
    ) as dump:
        _row(dump, 0)
        dump.observe_action("ALO", [0.25, -0.5])
        _row(dump, 1)
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        records = [json.loads(line) for line in stream]
    assert records[0]["_schema"] == "composite-corpus-dump-v3"
    assert records[1]["previous_steer"] == 0.0
    assert records[2]["previous_longitudinal"] == -0.5


def test_dump_rejects_duplicate_or_out_of_order_tick(tmp_path):
    with CompositeCorpusDump(
        tmp_path / "dump.jsonl.gz",
        run="synthetic",
        geometry_id="interlagos_v2",
        geometry_sha256="c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
    ) as dump:
        _row(dump, 2)
        with pytest.raises(CorpusDumpError, match="out-of-order"):
            _row(dump, 1)


def test_dump_rejects_wrong_vector_width(tmp_path):
    with CompositeCorpusDump(
        tmp_path / "dump.jsonl.gz",
        run="synthetic",
        geometry_id="interlagos_v2",
        geometry_sha256="c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
    ) as dump:
        with pytest.raises(CorpusDumpError, match="telemetry_edge_34"):
            dump.write_row(
                drv="ALO", tick=0, t_s=0.0, track_id=0, compound_id=1,
                telemetry_edge_34=[0.0] * 23, ctx=[0.0, 0.0],
                traffic_features_12=[0.0] * 12, speed_mps=10.0,
                curvature_ahead=0.0,
            )


def test_dump_loader_attaches_provenance_and_reports_unavailable_families(tmp_path):
    path = tmp_path / "dump.jsonl.gz"
    with CompositeCorpusDump(
        path,
        run="synthetic",
        geometry_id="interlagos_v2",
        geometry_sha256="c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
    ) as dump:
        _row(dump, 0)
    rows, manifest = load_composite_dump(
        path, source_git_sha256="0123456789abcdef"
    )
    assert manifest["row_count"] == 1
    assert rows[0]["source_sha256"] == manifest["sha256"]
    assert rows[0]["source_git_sha256"] == "0123456789abcdef"
    families = audit_dump_families(rows)
    assert families["launch_t_lt_60s"] == 1
    assert families["monaco_rejoin"]["status"] == "unavailable"


def test_real_tyre_types_resolve_supplemented_compound_ids():
    mapping = {
        "SOFT": 0,
        "INTERMEDIATE": 1,
        "MEDIUM": 2,
        "HARD": 3,
    }
    for compound, expected in (
        (TyreCompound.MEDIUM, 2),
        (TyreCompound.SOFT, 0),
        (TyreCompound.HARD, 3),
    ):
        state = TyreState(model=TYRE_CATALOG[compound])
        assert resolve_compound_id(state.model.compound, mapping) == expected
    wet_state = TyreState(model=TYRE_CATALOG[TyreCompound.WET])
    with pytest.raises(ValueError, match="absent from frozen mapping"):
        resolve_compound_id(wet_state.model.compound, mapping)


def test_compound_mapping_supplement_rejects_conflicting_id(tmp_path):
    path = tmp_path / "mappings.pkl"
    path.write_bytes(
        pickle.dumps(
            {"compounds": {"SOFT": 0, "INTERMEDIATE": 1, "MEDIUM": 2, "HARD": 4}}
        )
    )
    with pytest.raises(CorpusDumpError, match="collides"):
        load_compound_mapping(path)


def test_dump_loader_rejects_divergent_v2_schema(tmp_path):
    path = tmp_path / "incomplete-v2.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump({"_schema": "composite-corpus-dump-v2"}, stream)
        stream.write("\n")
    with pytest.raises(ValueError, match="unsupported dump schema"):
        load_composite_dump(path, source_git_sha256="0123456789abcdef")


def test_missing_compound_fails_loudly():
    with pytest.raises(ValueError, match="compound is None"):
        resolve_compound_id(None, {"MEDIUM": 2})
