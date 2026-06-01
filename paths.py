#!/usr/bin/env python3
"""NEXUS path registry resolver — logical names to physical paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent / "paths.json"

_registry_cache: dict[str, str] | None = None


class PathRegistryError(KeyError):
    """Raised when a logical path name is unknown or the registry is invalid."""


def load_registry(path: Path | None = None) -> dict[str, str]:
    global _registry_cache
    registry_file = path or REGISTRY_PATH
    if path is None and _registry_cache is not None:
        return _registry_cache
    if not registry_file.is_file():
        raise PathRegistryError(f"path registry not found: {registry_file}")
    data = json.loads(registry_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PathRegistryError(f"path registry must be a JSON object: {registry_file}")
    registry = {str(k): str(v) for k, v in data.items()}
    if path is None:
        _registry_cache = registry
    return registry


def resolve(logical_name: str, registry: dict[str, str] | None = None) -> str:
    """Return the absolute path for a logical registry name."""
    mapping = registry if registry is not None else load_registry()
    if logical_name not in mapping:
        known = ", ".join(sorted(mapping))
        raise PathRegistryError(
            f"unknown logical path {logical_name!r}; known names: {known or '(none)'}"
        )
    return str(Path(mapping[logical_name]).expanduser().resolve())


def verify(registry: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Check every registry entry resolves to an existing path."""
    mapping = registry if registry is not None else load_registry()
    results: list[dict[str, Any]] = []
    for name in sorted(mapping):
        try:
            resolved = resolve(name, mapping)
            exists = Path(resolved).exists()
            results.append(
                {
                    "logical_name": name,
                    "resolved": resolved,
                    "exists": exists,
                }
            )
        except PathRegistryError as exc:
            results.append(
                {
                    "logical_name": name,
                    "resolved": None,
                    "exists": False,
                    "error": str(exc),
                }
            )
    return results


def all_present(results: list[dict[str, Any]]) -> bool:
    """Return True only when every verify() row resolved to an existing path."""
    return bool(results) and all(r.get("exists") for r in results)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args != ["--verify"]:
        print("usage: python3 paths.py --verify", file=sys.stderr)
        return 2

    try:
        results = verify()
    except PathRegistryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    missing = [r for r in results if not r.get("exists")]
    for row in results:
        status = "ok" if row.get("exists") else "MISSING"
        print(f"{row['logical_name']}: {row.get('resolved')} [{status}]")
        if row.get("error"):
            print(f"  error: {row['error']}")

    if missing:
        names = ", ".join(r["logical_name"] for r in missing)
        print(
            f"\n{len(missing)} of {len(results)} registry paths MISSING: {names}",
            file=sys.stderr,
        )
        return 1

    print(f"\nAll {len(results)} registry paths exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
