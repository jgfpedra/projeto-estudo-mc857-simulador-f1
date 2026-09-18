from __future__ import annotations

import time
from pathlib import Path

from engine.controllers import CarInput
from engine.input_source import FileInputSource, InMemoryInputSource


def test_file_input_source_roundtrip(tmp_path: Path):
    file_path = tmp_path / "inputs.json"
    source_writer = FileInputSource(file_path=file_path)
    source_reader = FileInputSource(file_path=file_path)

    assert source_reader.get_last_input("drv_01") is None

    inp = CarInput(target_speed_mps=35.0, steering_yaw_rad=0.05, brake=0.0)
    source_writer.update_last_input("drv_01", inp, source="test_writer")

    entry = source_reader.get_last_input("drv_01")
    assert entry is not None
    assert entry.car_input.target_speed_mps == 35.0
    assert entry.car_input.steering_yaw_rad == 0.05
    assert entry.source == "test_writer"
    assert entry.seq == 1


def test_in_memory_input_source_cross_instance_sync(tmp_path: Path):
    race_id = f"test_sync_{time.time()}"
    mem_publisher = InMemoryInputSource(fallback_race_id=race_id)
    mem_consumer = InMemoryInputSource(fallback_race_id=race_id)

    inp = CarInput(target_speed_mps=50.0, steering_yaw_rad=-0.1, brake=0.0)
    mem_publisher.update_last_input("drv_02", inp, source="keyboard")

    # Consumer (outro objeto/processo) deve ler através do fallback IPC
    entry = mem_consumer.get_last_input("drv_02")
    assert entry is not None
    assert entry.car_input.target_speed_mps == 50.0
    assert entry.car_input.steering_yaw_rad == -0.1


def test_in_memory_poll_all(tmp_path: Path):
    race_id = f"test_poll_{time.time()}"
    source = InMemoryInputSource(fallback_race_id=race_id)
    source.update_last_input("drv_01", CarInput(target_speed_mps=20.0))
    res = source.poll_all(["drv_01", "drv_99"])
    assert res["drv_01"] is not None
    assert res["drv_01"].car_input.target_speed_mps == 20.0
    assert res["drv_99"] is None
