import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aria_evals import cli
from aria_evals.catalog import validate_catalog

ROOT = Path(__file__).resolve().parents[1]


def fake_engine(monkeypatch):
    monkeypatch.setattr(cli, "engine_identity", lambda engine: {
        "engine_commit": engine["commit"], "engine_version": engine["distribution_version"]})
    monkeypatch.setattr(cli, "provider_contract", lambda: ({"openai", "anthropic", "ollama"}, str.lower))


def fake_runner(monkeypatch, *, missing=False):
    commands = []
    real_run = cli.subprocess.run
    def run(command, **options):
        if command[0] == "git":
            return real_run(command, **options)
        commands.append((command, options))
        path = Path(command[command.index("--report") + 1])
        identifiers = validate_catalog(ROOT)["task_ids"]
        repeat = int(command[command.index("--repeat") + 1]) if "--repeat" in command else 1
        records = [{"task_id": task, "outcome": "fail", "seconds": 0.1}
                   for task in identifiers for _ in range(repeat)]
        path.write_text(json.dumps({"results": records[:-1] if missing else records}))
        return SimpleNamespace(returncode=0 if "--check" in command else 1)
    monkeypatch.setattr(cli.subprocess, "run", run)
    return commands


def test_validate_does_not_import_or_run_engine(monkeypatch):
    monkeypatch.setattr(cli, "engine_identity", lambda _: pytest.fail("validate must be offline"))
    assert cli.main(["--root", str(ROOT), "validate"]) == 0


def test_check_delegates_to_no_model_mode_and_writes_summary(monkeypatch, tmp_path):
    fake_engine(monkeypatch)
    calls = fake_runner(monkeypatch)
    output = tmp_path / "run"
    assert cli.main(["--root", str(ROOT), "check", "--output", str(output)]) == 0
    command, options = calls[0]
    assert "--check" in command and "--model" not in command and "--trajectories" not in command
    assert "-I" in command
    assert "PYTHONPATH" not in options["env"]
    assert json.loads((output / "summary.json").read_text())["performance"] is None


def test_explicit_model_settings_reach_runner(monkeypatch, tmp_path):
    fake_engine(monkeypatch)
    calls = fake_runner(monkeypatch)
    output = tmp_path / "run"
    assert cli.main(["--root", str(ROOT), "run", "--model", "example-model", "--provider", "openai",
                     "--repeat", "2", "--solve-timeout", "60", "--output", str(output)]) == 1
    command, options = calls[0]
    assert "--check" not in command and command[command.index("--model") + 1] == "openai/example-model"
    assert command[command.index("--repeat") + 1] == "2"
    assert command[command.index("--solve-timeout") + 1] == "60"
    assert options["env"]["ARIA_LLM_PROVIDER"] == "openai"
    summary = json.loads((output / "summary.json").read_text())
    assert summary["trials"] == 6 and summary["performance"]["completion_rate_all_trials"] == 0
    assert summary["context"]["model"] == "openai/example-model"


def test_conflicting_model_provider_does_not_run(monkeypatch, tmp_path):
    fake_engine(monkeypatch)
    calls = fake_runner(monkeypatch)
    output = tmp_path / "run"
    assert cli.main(["--root", str(ROOT), "run", "--model", "anthropic/example-model",
                     "--provider", "openai", "--output", str(output)]) == 2
    assert not calls and not output.exists()


def test_partial_native_report_cannot_publish_a_full_score(monkeypatch, tmp_path):
    fake_engine(monkeypatch)
    fake_runner(monkeypatch, missing=True)
    output = tmp_path / "run"
    assert cli.main(["--root", str(ROOT), "check", "--output", str(output)]) == 2
    assert not (output / "summary.json").exists()


def test_existing_run_directory_is_preserved(monkeypatch, tmp_path):
    fake_engine(monkeypatch)
    fake_runner(monkeypatch)
    (tmp_path / "marker").write_text("keep")
    assert cli.main(["--root", str(ROOT), "check", "--output", str(tmp_path)]) == 2
    assert (tmp_path / "marker").read_text() == "keep"


@pytest.mark.parametrize("change", ["commit", "version", "origin"])
def test_unpinned_or_shadowed_engine_is_rejected(monkeypatch, tmp_path, change):
    engine = validate_catalog(ROOT)["manifest"]["engine"]
    direct = {"url": "https://github.com/artheras/aria-code.git",
              "vcs_info": {"vcs": "git", "commit_id": engine["commit"]}}
    if change == "commit":
        direct["vcs_info"]["commit_id"] = "0" * 40
    distribution = SimpleNamespace(version="0.0.0" if change == "version" else engine["distribution_version"],
                                   read_text=lambda _: json.dumps(direct),
                                   locate_file=lambda _: tmp_path / "runner.py")
    monkeypatch.setattr(cli.importlib.metadata, "distribution", lambda _: distribution)
    monkeypatch.setattr(cli.importlib.util, "find_spec", lambda _: SimpleNamespace(
        origin=str(tmp_path / ("shadow.py" if change == "origin" else "runner.py"))))
    with pytest.raises(ValueError):
        cli.engine_identity(engine)
