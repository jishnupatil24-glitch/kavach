import builtins

import pytest

from app import simulator_cli
from app.database.session import SessionLocal
from app.models.sensor_observation import SensorObservation
from app.models.simulation_run import SimulationRun


def _feed_input(monkeypatch, answers):
    it = iter(answers)

    def fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr(builtins, "input", fake_input)


def test_cli_generates_a_real_normal_simulation(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["10", "1", "555"])
    exit_code = simulator_cli.main([])
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "Simulation created" in out
    assert "Simulation ID:" in out

    run_id = int(out.split("Simulation ID:")[1].strip().splitlines()[0])

    db = SessionLocal()
    try:
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        assert run is not None
        assert run.duration_days == 10
        assert run.scenario == "normal"
        count = db.query(SensorObservation).filter(SensorObservation.simulation_run_id == run_id).count()
        assert count == 40
    finally:
        db.close()


def test_40_days_produces_exactly_160_observations(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["40", "2", "31", "10", "3", "123"])
    exit_code = simulator_cli.main([])
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "Observations: 160" in out
    assert "Scenario window: Day 31" in out


def test_day_flag_displays_exactly_four_observations(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["20", "1", "1"])
    simulator_cli.main([])
    out = capsys.readouterr().out
    run_id = int(out.split("Simulation ID:")[1].strip().splitlines()[0])

    exit_code = simulator_cli.main(["--run-id", str(run_id), "--day", "5"])
    assert exit_code == 0
    view_out = capsys.readouterr().out
    assert view_out.count("00:00") == 1
    assert view_out.count("06:00") == 1
    assert view_out.count("12:00") == 1
    assert view_out.count("18:00") == 1
    assert f"Day {5}" not in view_out or "Simulation #" in view_out  # header present, no crash


def test_invalid_duration_input_is_reprompted_not_crashed(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["0", "200", "abc", "15", "1", "7"])
    exit_code = simulator_cli.main([])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "✗" in out
    assert "Observations: 60" in out  # 15 days * 4


def test_view_day_for_nonexistent_run_fails_cleanly(seeded_db, capsys):
    exit_code = simulator_cli.main(["--run-id", "999999", "--day", "1"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "No simulation found" in out


def test_view_day_out_of_range_fails_cleanly(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["10", "1", "42"])
    simulator_cli.main([])
    out = capsys.readouterr().out
    run_id = int(out.split("Simulation ID:")[1].strip().splitlines()[0])

    exit_code = simulator_cli.main(["--run-id", str(run_id), "--day", "999"])
    assert exit_code == 1
    out2 = capsys.readouterr().out
    assert "✗" in out2
    assert "Day must be between 1 and 10" in out2


def test_only_one_of_run_id_or_day_fails_cleanly(capsys):
    exit_code = simulator_cli.main(["--day", "1"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "required together" in out


def _by_day(text: str) -> dict:
    """Splits captured CLI stdout into {day_number: chunk_of_output}."""
    import re

    chunks: dict[int, str] = {}
    matches = list(re.finditer(r"-+ DAY (\d+) -+", text))
    for i, m in enumerate(matches):
        day = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks[day] = text[start:end]
    return chunks


def test_40_days_displays_all_160_observations_in_terminal(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["40", "1", "1"])
    exit_code = simulator_cli.main([])
    assert exit_code == 0
    out = capsys.readouterr().out

    assert out.count("00:00") == 40
    assert out.count("06:00") == 40
    assert out.count("12:00") == 40
    assert out.count("18:00") == 40

    day_chunks = _by_day(out)
    assert sorted(day_chunks) == list(range(1, 41))
    for day, chunk in day_chunks.items():
        assert chunk.count("00:00") == 1
        assert chunk.count("06:00") == 1
        assert chunk.count("12:00") == 1
        assert chunk.count("18:00") == 1


def test_48_days_displays_all_192_observations_in_terminal(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["48", "4", "36", "11", "3", "123"])
    exit_code = simulator_cli.main([])
    assert exit_code == 0
    out = capsys.readouterr().out

    assert "Observations: 192" in out
    assert out.count("00:00") == 48
    assert out.count("06:00") == 48
    assert out.count("12:00") == 48
    assert out.count("18:00") == 48

    day_chunks = _by_day(out)
    assert sorted(day_chunks) == list(range(1, 49))


def test_days_are_displayed_in_chronological_order(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["15", "1", "1"])
    simulator_cli.main([])
    out = capsys.readouterr().out

    import re

    day_order = [int(m.group(1)) for m in re.finditer(r"-+ DAY (\d+) -+", out)]
    assert day_order == list(range(1, 16))


def test_summary_block_appears_after_all_day_tables(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["5", "1", "1"])
    simulator_cli.main([])
    out = capsys.readouterr().out

    last_day_marker = out.rindex("---------------- DAY 5 ----------------")
    summary_marker = out.index("SIMULATION SUMMARY")
    assert summary_marker > last_day_marker


def test_no_raw_json_or_python_objects_in_full_dataset_output(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["3", "1", "1"])
    simulator_cli.main([])
    out = capsys.readouterr().out
    assert "SensorObservation(" not in out
    assert '{"day"' not in out
    assert "object at 0x" not in out


def test_day_flag_still_works_unchanged_after_full_dump_feature(seeded_db, monkeypatch, capsys):
    _feed_input(monkeypatch, ["48", "4", "36", "11", "3", "123"])
    simulator_cli.main([])
    out = capsys.readouterr().out
    run_id = int(out.split("Simulation ID:")[1].strip().splitlines()[0])

    exit_code = simulator_cli.main(["--run-id", str(run_id), "--day", "36"])
    assert exit_code == 0
    view_out = capsys.readouterr().out
    assert view_out.count("00:00") == 1
    assert "DAY 1 " not in view_out
    assert f"Day 36" in view_out


def test_cli_reuses_existing_simulator_service_not_a_reimplementation():
    """
    Structural check: the CLI module must not define its own generation
    logic (diurnal/evap/scenario/calibration math) -- it must only
    import and call the existing simulator service.
    """
    import inspect

    source = inspect.getsource(simulator_cli)
    forbidden_fragments = [
        "evaporative_loss",
        "diurnal_temperature_offset",
        "build_calibrated_irrigation_table",
        "def generate(",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source, f"CLI appears to duplicate simulator logic: {fragment!r} found"

    assert "from app.services.simulator.config import" in source
    assert "from app.services.simulator.run_service import" in source
