"""Everyday tool: enforce the user's code limits on explicitly named Python files."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def length_violations(source, rules):
    errors = []
    if len(source.splitlines()) > rules["max_file_lines"]:
        errors.append("file exceeds maximum lines")
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        length = node.end_lineno - node.lineno + 1
        doc = node.body[0] if ast.get_docstring(node) else None
        if doc is not None:
            length -= doc.end_lineno - doc.lineno + 1
        if length > rules["max_function_lines"]:
            errors.append(f"{node.name}:{node.lineno}: {length} lines exceeds limit")
    return errors


def lint(paths, rules):
    args = [
        sys.executable, "-m", "ruff", "check", "--no-cache",
        "--select", "C901,PLR0912,PLR0913,PLR2004,F401,F821,F841",
    ]
    for key, value in (
        ("lint.mccabe.max-complexity", rules["max_complexity"]),
        ("lint.pylint.max-branches", rules["max_branches"]),
        ("lint.pylint.max-args", rules["max_arguments"]),
    ):
        args.extend(["--config", f"{key}={value}"])
    return subprocess.run(args + [str(p) for p in paths], check=False).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    rules = json.loads((ROOT / "configs/code_rules.json").read_text())
    errors = []
    for path in args.files:
        errors.extend(f"{path}: {e}" for e in length_violations(path.read_text("utf-8"), rules))
    for error in errors:
        print(error, file=sys.stderr)
    lint_status = lint(args.files, rules)
    return int(bool(errors or lint_status))


if __name__ == "__main__":
    raise SystemExit(main())
