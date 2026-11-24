"""Catalog commands delegating execution to the pinned public Aria engine."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
import uuid

import yaml

from .catalog import validate_catalog
from .reporting import diff_summaries, load_prices, publication_summary, write_json


def provider_contract():
    from aria_code.apps.cli.providers.chat_routing import KNOWN_MODEL_PROVIDERS, normalize_provider_name
    return KNOWN_MODEL_PROVIDERS, normalize_provider_name


def resolve_model(provider: str, model: str) -> tuple[str, str]:
    known, normalize = provider_contract()
    provider = normalize(provider)
    if provider not in known:
        raise ValueError("Provider must be recognized by the pinned engine")
    model = model.strip()
    if "/" in model:
        prefix, remainder = model.split("/", 1)
        if normalize(prefix) in known:
            if normalize(prefix) != provider:
                raise ValueError("The model's provider prefix conflicts with --provider")
            model = remainder
    if not model.strip():
        raise ValueError("Model identifier must not be empty")
    return provider, provider + "/" + model


def engine_identity(engine: dict) -> dict:
    """Refuse an unpinned install or an import shadowing the installed runner."""
    try:
        distribution = importlib.metadata.distribution("aria-code")
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValueError('Install the pinned engine with pip install -e ".[dev,runner]"') from exc
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    source = urlsplit(direct.get("url", ""))
    repository = source.path.rstrip("/").removesuffix(".git").lstrip("/")
    if (source.scheme != "https" or source.netloc != "github.com"
            or repository != engine["repository"]
            or direct.get("vcs_info", {}).get("vcs") != "git"
            or direct.get("vcs_info", {}).get("commit_id") != engine["commit"]
            or distribution.version != engine["distribution_version"]):
        raise ValueError("Installed aria-code does not match registry.json's immutable source pin")
    spec = importlib.util.find_spec("aria_code.evals.runner")
    installed = Path(distribution.locate_file("aria_code/evals/runner.py")).resolve()
    if spec is None or spec.origin is None or Path(spec.origin).resolve() != installed:
        raise ValueError("The installed runner is shadowed by another import path")
    return {"engine_commit": engine["commit"], "engine_version": distribution.version}


def catalog_git(root: Path) -> dict:
    def git(*arguments):
        return subprocess.run(["git", "-C", str(root), *arguments], capture_output=True,
                              text=True, check=False)
    top = git("rev-parse", "--show-toplevel")
    if top.returncode or Path(top.stdout.strip()).resolve() != root:
        return {"catalog_commit": None, "catalog_dirty": None}
    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    return {"catalog_commit": head.stdout.strip() if head.returncode == 0 else None,
            "catalog_dirty": bool(status.stdout) if status.returncode == 0 else None}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_c_compiler() -> str | None:
    for candidate in ("cc", "gcc", "clang"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def environment_diagnostics(catalog: dict) -> dict:
    """Inspect host OS, compiler toolchain, Python dependencies, and pinned runner."""
    posix_host = os.name == "posix"
    compiler = find_c_compiler()
    missing_modules = [
        name for name in catalog.get("requires", [])
        if importlib.util.find_spec(name) is None
    ]
    runner_error = None
    try:
        identity = engine_identity(catalog["manifest"]["engine"])
    except ValueError as exc:
        identity = None
        runner_error = str(exc)
    issues = []
    if not posix_host:
        issues.append("A POSIX host is required by the isolated pytest verifier (-c /dev/null)")
    if catalog.get("requires_c_compiler") and compiler is None:
        issues.append("A C compiler (cc, gcc, or clang) is required for tasks tagged requires-c-compiler")
    if missing_modules:
        issues.append(f"Missing Python modules declared in requires: {', '.join(missing_modules)}")
    return {
        "posix_host": posix_host,
        "c_compiler": compiler,
        "missing_python_modules": missing_modules,
        "runner_ready": identity is not None,
        "runner_identity": identity,
        "runner_error": runner_error,
        "ready_for_calibration": not issues,
        "ready_for_engine": not issues and identity is not None,
        "issues": issues,
    }


def check_environment(catalog: dict) -> None:
    diag = environment_diagnostics(catalog)
    blocking = []
    if not diag["posix_host"]:
        blocking.append("A POSIX host is required by the isolated pytest verifier (-c /dev/null)")
    if catalog.get("requires_c_compiler") and diag["c_compiler"] is None:
        blocking.append("A C compiler (cc, gcc, or clang) is required for tasks tagged requires-c-compiler")
    if blocking:
        raise ValueError("; ".join(blocking))


def _load_summary_arg(path_str: str) -> dict:
    path = Path(path_str).expanduser().resolve()
    if path.is_dir():
        path = path / "summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def execute(root: Path, args) -> int:
    catalog = validate_catalog(root)
    check_environment(catalog)
    identity = engine_identity(catalog["manifest"]["engine"])
    check = args.command == "check"
    provider, model = (None, None) if check else resolve_model(args.provider, args.model)
    # Read the price table before anything runs: a typo found after the run has been paid for.
    prices = load_prices(Path(args.prices).expanduser()) if getattr(args, "prices", None) else None
    repeat = 1 if check else args.repeat
    output = (Path(args.output).expanduser().resolve() if args.output else
              root / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]))
    if output == catalog["fixture_root"] or catalog["fixture_root"] in output.parents:
        raise ValueError("Reports must be outside fixture inputs")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": 1,
                "run_kind": "model_free_preflight" if check else "model_evaluation",
                "catalog_version": catalog["manifest"]["catalog_version"],
                "catalog_sha256": catalog["content_sha256"], **catalog_git(root), **identity,
                "model": model,
                "provider": provider, "repeat": repeat,
                "solve_timeout_seconds": None if check else args.solve_timeout,
                "expected_trials": catalog["task_count"] * repeat,
                "started_at": utc_now()}
    write_json(output / "manifest.json", manifest)
    command = [sys.executable, "-I", "-m", "aria_code.evals.runner", str(catalog["suite_path"]),
               "--fixtures", str(catalog["fixture_root"]), "--report", str(output / "native.json")]
    environment = os.environ.copy()
    # The runner must resolve from the verified installed distribution in the child too.
    environment.pop("PYTHONPATH", None)
    if check:
        command.append("--check")
    else:
        command.extend(["--model", model, "--repeat", str(repeat),
                        "--solve-timeout", str(args.solve_timeout)])
        environment["ARIA_LLM_PROVIDER"] = provider
    with (output / "native.log").open("x", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=root, env=environment, stdout=log,
                                stderr=subprocess.STDOUT, text=True, check=False)
    write_json(output / "completion.json", {"finished_at": utc_now(), "exit_code": result.returncode})
    native = json.loads((output / "native.json").read_text())
    received = Counter(row.get("task_id") for row in native.get("results", []) if isinstance(row, dict))
    if received != Counter({identifier: repeat for identifier in catalog["task_ids"]}):
        raise ValueError("Native report has missing, duplicated or unexpected task attempts")
    if validate_catalog(root)["content_sha256"] != catalog["content_sha256"]:
        raise ValueError("Catalog content changed during execution")
    summary = publication_summary(native, manifest, prices)
    write_json(output / "summary.json", summary)
    performance = summary["performance"] or {}
    print(json.dumps({"run_kind": manifest["run_kind"],
                      **({"completion_rate_all_trials": performance["completion_rate_all_trials"]} if performance else {}),
                      "counts": summary["counts"], "errors": summary["errors"],
                      "summary": str(output / "summary.json"), "exit_code": result.returncode}))
    if check and summary["counts"] != {"pass": 0, "fail": catalog["task_count"], "invalid": 0, "error": 0}:
        return 1
    return result.returncode


def positive_int(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 3600:
        raise argparse.ArgumentTypeError("Use an integer from 1 through 3600")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="catalog checkout (default: current directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="validate catalog structure and content identity")
    commands.add_parser("doctor", help="check host OS, C compiler, Python deps, and pinned engine")
    diff = commands.add_parser("diff", help="compare two summary.json files or run directories")
    diff.add_argument("left", help="baseline summary.json or run directory")
    diff.add_argument("right", help="comparison summary.json or run directory")
    check = commands.add_parser("check", help="model-free native preflight; every task must fail its grader")
    check.add_argument("--output", help="new directory for local reports (default: ignored runs/)")
    run = commands.add_parser("run", help="run the real Aria agent on public demonstrations")
    run.add_argument("--model", required=True)
    run.add_argument("--provider", required=True, help="explicit provider recognized by the pinned engine")
    run.add_argument("--repeat", type=positive_int, default=1)
    run.add_argument("--solve-timeout", type=positive_int, default=900)
    run.add_argument("--output", help="new directory for local reports (default: ignored runs/)")
    run.add_argument("--prices", help="dated USD price table (JSON) to turn reported tokens into a cost")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.root.expanduser().resolve()
        if args.command == "validate":
            catalog = validate_catalog(root)
            print(json.dumps({"task_count": catalog["task_count"], "content_sha256": catalog["content_sha256"]}))
            return 0
        if args.command == "doctor":
            catalog = validate_catalog(root)
            diag = environment_diagnostics(catalog)
            print(json.dumps(diag, indent=2))
            return 0 if diag["ready_for_calibration"] else 1
        if args.command == "diff":
            result = diff_summaries(_load_summary_arg(args.left), _load_summary_arg(args.right))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "run" and any(not value.strip() or "\n" in value or "\r" in value
                                          for value in (args.model, args.provider)):
            raise ValueError("Model and provider must be explicit nonempty single-line values")
        return execute(root, args)
    except (ValueError, TypeError, OSError, KeyError, ImportError, yaml.YAMLError) as exc:
        print(f"aria-evals: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
