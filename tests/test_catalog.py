import json
from pathlib import Path
import shutil
import tomllib

import pytest
import yaml

from aria_evals.catalog import validate_catalog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalog(tmp_path):
    root = tmp_path / "catalog"
    root.mkdir()
    shutil.copy(ROOT / "registry.json", root)
    shutil.copytree(ROOT / "evals", root / "evals")
    return root


def change_task(root, key, value):
    path = root / "evals/suites/public.yaml"
    suite = yaml.safe_load(path.read_text())
    suite["tasks"][0][key] = value
    path.write_text(yaml.safe_dump(suite))


def test_source_dependency_matches_registry():
    result = validate_catalog(ROOT)
    dependency = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["optional-dependencies"]["runner"]
    assert dependency == ["aria-code @ git+https://github.com/artheras/aria-code.git@" + result["manifest"]["engine"]["commit"]]
    assert result["task_count"] == 3


def test_input_change_changes_catalog_identity(catalog):
    before = validate_catalog(catalog)["content_sha256"]
    (catalog / "evals/fixtures/maze_route/maze.txt").write_text("new synthetic maze\n")
    assert validate_catalog(catalog)["content_sha256"] != before


@pytest.mark.parametrize("key,value", [
    ("fixture", "../outside"), ("fixture", "/tmp/absolute"),
    ("typo_field", True), ("setup", ["echo arbitrary"]),
    ("verify", "{python} -m pytest -q test_route.py; echo bypass"),
    ("hidden", []), ("protect", []), ("allow_green_start", True),
    ("timeout", -1), ("timeout", True),
])
def test_invalid_task_contract_is_rejected(catalog, key, value):
    change_task(catalog, key, value)
    with pytest.raises(ValueError):
        validate_catalog(catalog)


def test_duplicate_identifier_is_rejected(catalog):
    path = catalog / "evals/suites/public.yaml"
    suite = yaml.safe_load(path.read_text())
    suite["tasks"][1]["id"] = suite["tasks"][0]["id"]
    path.write_text(yaml.safe_dump(suite))
    with pytest.raises(ValueError):
        validate_catalog(catalog)


def test_symlink_input_is_rejected(catalog, tmp_path):
    outside = tmp_path / "input"
    outside.write_text("external input")
    inside = catalog / "evals/fixtures/maze_route/maze.txt"
    inside.unlink()
    inside.symlink_to(outside)
    with pytest.raises(ValueError):
        validate_catalog(catalog)


def test_engine_branch_is_not_an_immutable_pin(catalog):
    path = catalog / "registry.json"
    manifest = json.loads(path.read_text())
    manifest["engine"]["commit"] = "main"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        validate_catalog(catalog)
