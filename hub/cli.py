"""Command line interface.

    hub check [path ...]   validate descriptors without collecting
    hub collect            run all configured sources, write the graph
    hub schema             regenerate schema/service.schema.json from the models
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .collector import _format_validation_error, collect
from .config import DEFAULT_SERVICE_FILE, HubConfig
from .models import ServiceDoc

DEFAULT_CONFIG = Path("hub.config.yaml")
SCHEMA_PATH = Path("schema/service.schema.json")


def _check(paths: list[Path]) -> int:
    """Validate descriptors given directly, or found under the given directories."""
    targets: list[Path] = []
    for path in paths or [Path(".")]:
        if path.is_dir():
            candidate = path / DEFAULT_SERVICE_FILE
            if candidate.is_file():
                targets.append(candidate)
            else:
                targets.extend(sorted(path.glob(f"*/{DEFAULT_SERVICE_FILE}")))
        elif path.is_file():
            targets.append(path)
        else:
            print(f"not found: {path}", file=sys.stderr)
            return 2

    if not targets:
        print("no service descriptors found", file=sys.stderr)
        return 2

    failed = 0
    for target in targets:
        try:
            data = yaml.safe_load(target.read_text(encoding="utf-8"))
            ServiceDoc.model_validate(data)
        except yaml.YAMLError as exc:
            failed += 1
            print(f"FAIL {target}\n     invalid YAML: {exc}")
        except ValidationError as exc:
            failed += 1
            print(f"FAIL {target}\n     {_format_validation_error(exc)}")
        else:
            print(f"ok   {target}")

    print(f"\n{len(targets) - failed}/{len(targets)} valid")
    return 1 if failed else 0


def _collect(config_path: Path, output: Path | None) -> int:
    config = HubConfig.load(config_path)
    result = collect(config)

    destination = output or config.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    stats = result["stats"]
    print(
        f"collected {stats['services']} service(s), "
        f"{stats['edges']} edge(s) → {destination}"
    )

    problems = result["problems"]
    if problems:
        errors = sum(1 for p in problems if p["severity"] == "error")
        print(f"\n{len(problems)} problem(s), {errors} error(s):")
        for problem in problems:
            mark = "!" if problem["severity"] == "error" else "-"
            detail = f" ({problem['detail']})" if problem["detail"] else ""
            print(f" {mark} [{problem['repo']}] {problem['message']}{detail}")

    # A problem is information, not a failed run: an incomplete map that is
    # honest about being incomplete is the expected state while adopting this.
    return 0


def _schema(output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    schema = ServiceDoc.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "service.yaml"
    output.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hub", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate service descriptors")
    check.add_argument("paths", nargs="*", type=Path)

    collect_cmd = sub.add_parser("collect", help="collect all sources into a graph")
    collect_cmd.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG)
    collect_cmd.add_argument("-o", "--output", type=Path, default=None)

    schema_cmd = sub.add_parser("schema", help="regenerate the JSON Schema")
    schema_cmd.add_argument("-o", "--output", type=Path, default=SCHEMA_PATH)

    args = parser.parse_args(argv)

    if args.command == "check":
        return _check(args.paths)
    if args.command == "collect":
        return _collect(args.config, args.output)
    if args.command == "schema":
        return _schema(args.output)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
