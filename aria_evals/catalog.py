"""Strict validation and content identity for the public catalog."""

import hashlib
import json
from pathlib import Path
import re
import shlex

import yaml

TASK_FIELDS = {"id", "prompt", "verify", "fixture", "timeout", "solve_timeout", "tags",
               "setup", "requires", "protect", "allow_green_start", "hidden"}


def inside(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Expected a relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
        raise ValueError("Path escapes the catalog")
    result = root / relative
    if any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
        raise ValueError("Catalog paths must not traverse symlinks")
    return result


def validate_catalog(root: Path) -> dict:
    root = root.resolve()
    manifest_path = inside(root, "registry.json")
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("dataset_role") != "public_demonstration":
        raise ValueError("Unsupported catalog contract")
    engine = manifest.get("engine", {})
    if not isinstance(engine, dict) or engine.get("repository") != "artheras/aria-code" or not re.fullmatch(r"[0-9a-f]{40}", str(engine.get("commit", ""))):
        raise ValueError("The public engine must be pinned to an immutable commit")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(engine.get("distribution_version", ""))):
        raise ValueError("The engine needs a distribution version")
    if not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("catalog_version", "")):
        raise ValueError("Use a semantic catalog version")
    suite_path = inside(root, manifest["suite"])
    fixture_root = inside(root, manifest["fixtures"])
    suite = yaml.safe_load(suite_path.read_text())
    if not isinstance(suite, dict) or not isinstance(suite.get("suite"), str):
        raise ValueError("Suite needs a name")
    tasks = suite.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Suite needs tasks")
    identifiers = set()
    sources = [manifest_path, suite_path]
    for task in tasks:
        if not isinstance(task, dict) or set(task) - TASK_FIELDS:
            raise ValueError("Unknown task fields")
        identifier = task.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", identifier) or identifier in identifiers:
            raise ValueError("Task identifiers must be unique lowercase names")
        identifiers.add(identifier)
        if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
            raise ValueError("Tasks need a prompt")
        for field in ("tags", "requires", "protect", "hidden"):
            values = task.get(field, [])
            if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
                raise ValueError("Task list fields need nonempty strings")
        if task.get("setup") or task.get("allow_green_start"):
            raise ValueError("Public demonstrations must start red and need no setup commands")
        for field in ("timeout", "solve_timeout"):
            if field in task and (type(task[field]) not in {int, float} or not 0 < task[field] <= 3600):
                raise ValueError("Task time limits must be positive and bounded")
        fixture = inside(fixture_root, task.get("fixture"))
        if not fixture.is_dir():
            raise ValueError("Fixture is missing")
        files = list(fixture.iterdir())
        if any(not p.is_file() or p.is_symlink() for p in files):
            raise ValueError("Use flat fixtures containing regular files")
        graders = {p.name for p in files if p.name.startswith("test_") and p.suffix == ".py"}
        if not graders or set(task.get("hidden", [])) != graders:
            raise ValueError("All grader files must be hidden during the agent's turn")
        words = shlex.split(task.get("verify", ""))
        if words[:3] != ["{python}", "-m", "pytest"]:
            raise ValueError("Verifier must invoke pytest through the selected interpreter")
        selected = {word for word in words[3:] if word.endswith(".py")}
        if selected != graders or any(word not in graders | {"-q", "--noconftest", "-p", "no:cacheprovider"} for word in words[3:]):
            raise ValueError("Verifier must select only its fixture graders")
        if not {p.name for p in files}.issubset(set(task.get("protect", []))):
            raise ValueError("Protect each input and grader explicitly")
        sources.extend(files)
    content_hash = hashlib.sha256()
    for path in sorted(sources):
        content_hash.update(path.relative_to(root).as_posix().encode())
        content_hash.update(b"\0")
        content_hash.update(path.read_bytes())
        content_hash.update(b"\0")
    return {"manifest": manifest, "suite_path": suite_path, "fixture_root": fixture_root,
            "task_ids": sorted(identifiers), "task_count": len(tasks), "content_sha256": content_hash.hexdigest()}
