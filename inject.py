#!/usr/bin/env python3
"""NEXUS DNA injection — versioned, idempotent, tier-gated identity propagation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "consumers.json"

RESTRICTED_TIERS = frozenset({"personal", "intimate"})
TIER_RANK = {"core": 0, "business": 1, "clinical": 2, "personal": 3, "intimate": 4}
TIER_TAG_RE = re.compile(r"`?tier:\s*([^`\n]+)`?", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+)$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def expand(path_str: str) -> Path:
    return Path(path_str).expanduser().resolve()


def resolve_registry_path(logical_name: str | None, fallback: str | None) -> Path:
    """Resolve a registry logical name with fallback to a literal path string."""
    if logical_name:
        try:
            from paths import resolve

            return Path(resolve(logical_name))
        except Exception:
            pass
    if fallback:
        return expand(fallback)
    raise ValueError(f"no registry key or fallback path for {logical_name!r}")


def resolve_dna_dir(cfg: dict[str, Any]) -> Path:
    return resolve_registry_path(cfg.get("dna_dir_key"), cfg.get("dna_dir"))


def resolve_consumer_path(consumer: dict[str, Any]) -> Path:
    return resolve_registry_path(consumer.get("path_key"), consumer.get("path"))


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def parse_tier_tokens(raw: str) -> set[str]:
    tokens: set[str] = set()
    for part in re.split(r"[/,]", raw):
        token = part.strip().lower()
        if token:
            tokens.add(token)
    return tokens


def tiers_in_heading(heading_line: str) -> set[str]:
    found: set[str] = set()
    for match in TIER_TAG_RE.finditer(heading_line):
        found.update(parse_tier_tokens(match.group(1)))
    return found


def effective_tier(tags: set[str], file_tier: str) -> str:
    if not tags:
        return (file_tier or "core").lower()
    if len(tags) > 1:
        return max(tags, key=lambda t: TIER_RANK.get(t, 99))
    return next(iter(tags))


def normalize_field(value: str) -> str:
    return value.split("#", 1)[0].strip()


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = normalize_field(value)
    return meta, text[match.end() :]


def tier_permitted(tier: str, permitted: set[str]) -> bool:
    return tier.lower() in permitted


def section_permitted(heading_line: str, file_tier: str, permitted: set[str]) -> bool:
    tags = tiers_in_heading(heading_line)
    tier = effective_tier(tags, file_tier)
    return tier_permitted(tier, permitted)


def parse_sections(body: str) -> tuple[list[str], list[tuple[int, str, list[str]]]]:
    """Split body into preamble (before first ##/###) and heading sections."""
    lines = body.splitlines()
    preamble: list[str] = []
    sections: list[tuple[int, str, list[str]]] = []
    idx = 0

    while idx < len(lines) and not HEADING_RE.match(lines[idx]):
        preamble.append(lines[idx])
        idx += 1

    current_level = 0
    current_heading = ""
    current_content: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_content, current_level
        if current_heading or current_content:
            sections.append((current_level, current_heading, current_content))
        current_heading = ""
        current_content = []
        current_level = 0

    while idx < len(lines):
        line = lines[idx]
        match = HEADING_RE.match(line)
        if match:
            flush()
            current_level = len(match.group(1))
            current_heading = line
        else:
            current_content.append(line)
        idx += 1
    flush()
    return preamble, sections


def filter_body(body: str, file_tier: str, permitted: set[str]) -> str:
    if not body.strip():
        return ""

    preamble, sections = parse_sections(body)
    kept: list[str] = []

    if preamble and section_permitted("", file_tier, permitted):
        kept.extend(preamble)

    for _level, heading, content in sections:
        if section_permitted(heading, file_tier, permitted):
            if kept and kept[-1] != "":
                kept.append("")
            kept.append(heading)
            kept.extend(content)

    return "\n".join(kept).strip()


def load_filtered_slice(dna_dir: Path, filename: str, permitted: set[str]) -> str:
    path = dna_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"DNA source missing: {path}")
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    file_tier = meta.get("tier", "core")
    filtered = filter_body(body, file_tier, permitted)
    if not filtered:
        return ""
    return f"### From `{filename}`\n\n{filtered}"


def build_payload(dna_dir: Path, source_files: list[str], permitted: set[str]) -> str:
    parts: list[str] = []
    for filename in source_files:
        slice_text = load_filtered_slice(dna_dir, filename, permitted)
        if slice_text:
            parts.append(slice_text)
    return "\n\n---\n\n".join(parts).strip()


def marker_pair(version: str) -> tuple[str, str]:
    return (
        f"",
        f"",
    )


def strip_block(text: str, version: str) -> str:
    start, end = marker_pair(version)
    result = text
    while True:
        start_idx = result.find(start)
        if start_idx == -1:
            break
        end_idx = result.find(end, start_idx)
        if end_idx == -1:
            break
        cut_start = start_idx
        cut_end = end_idx + len(end)
        heading = "## IDENTITY (BYO — see TEMPLATE-README.md)"
        pre = result[:cut_start].rstrip()
        if pre.endswith(heading):
            cut_start = pre.rfind(heading)
            if cut_start > 0 and pre[cut_start - 1] == "\n":
                cut_start -= 1
        if cut_start > 0 and result[cut_start - 1] == "\n":
            cut_start -= 1
        if cut_start > 0 and result[cut_start - 1] == "\n":
            cut_start -= 1
        if cut_end < len(result) and result[cut_end] == "\n":
            cut_end += 1
        result = result[:cut_start] + result[cut_end:]
    orphan = re.compile(
        rf"^[ \t]*[ \t]*\n?",
        re.MULTILINE,
    )
    result = orphan.sub("", result)
    result = re.sub(
        r"\n## IDENTITY \(managed by NEXUS/DNA\)\s*(?=\n## IDENTITY \(managed by NEXUS/DNA\))",
        "",
        result,
    )
    return result


def build_managed_block(version: str, payload: str) -> str:
    start, end = marker_pair(version)
    return "\n".join(
        [
            "",
            start,
            "## IDENTITY (BYO — see TEMPLATE-README.md)",
            "<!-- Managed by NEXUS/DNA — edits inside overwritten -->",
            "",
            payload,
            "",
            end,
            "",
        ]
    )


def inject_into_file(
    target: Path,
    version: str,
    payload: str,
    legacy_versions: list[str],
) -> str:
    before = target.read_text(encoding="utf-8") if target.is_file() else ""
    scrubbed = before
    for legacy in legacy_versions:
        scrubbed = strip_block(scrubbed, legacy)
    had_current = f"" in scrubbed
    without = strip_block(scrubbed, version)
    block = build_managed_block(version, payload)
    next_text = without.rstrip() + block
    if next_text == before:
        return "unchanged"
    target.write_text(next_text, encoding="utf-8")
    return "updated" if had_current else "injected"


def extract_managed_payload(text: str, version: str) -> str | None:
    """Return normalized payload inside the managed block, or None if missing/incomplete."""
    start, end = marker_pair(version)
    start_idx = text.find(start)
    if start_idx == -1:
        return None
    end_idx = text.find(end, start_idx)
    if end_idx == -1:
        return None
    inner = text[start_idx + len(start) : end_idx]
    lines = inner.splitlines()
    trimmed: list[str] = []
    skip_prefixes = (
        "## IDENTITY (BYO — see TEMPLATE-README.md)",
        "<!-- Managed by NEXUS/DNA",
    )
    for line in lines:
        if any(line.strip().startswith(prefix) for prefix in skip_prefixes):
            continue
        trimmed.append(line)
    payload = "\n".join(trimmed).strip()
    return payload or None


def normalize_payload(payload: str) -> str:
    return "\n".join(line.rstrip() for line in payload.strip().splitlines()).strip()


def compare_consumer(consumer: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    """Compare a consumer's managed block against a fresh DNA render."""
    target = resolve_consumer_path(consumer)
    version = cfg["dna_version"]
    dna_dir = resolve_dna_dir(cfg)
    permitted = set(consumer["permitted_tiers"])
    expected = build_payload(dna_dir, cfg["source_files"], permitted)

    if not target.is_file():
        return {
            "consumer_id": consumer["id"],
            "path": str(target),
            "status": "missing_file",
            "drift": True,
            "detail": "consumer target file missing",
        }

    current_text = target.read_text(encoding="utf-8")
    current = extract_managed_payload(current_text, version)
    if current is None:
        return {
            "consumer_id": consumer["id"],
            "path": str(target),
            "status": "missing_block",
            "drift": True,
            "detail": "DNA-INJECTION managed block missing or incomplete",
        }

    if normalize_payload(current) == normalize_payload(expected):
        return {
            "consumer_id": consumer["id"],
            "path": str(target),
            "status": "ok",
            "drift": False,
            "detail": "managed block matches current DNA render",
        }

    return {
        "consumer_id": consumer["id"],
        "path": str(target),
        "status": "drift",
        "drift": True,
        "detail": "managed block differs from current DNA render",
    }


def compare_all(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config()
    return [compare_consumer(consumer, cfg) for consumer in cfg["consumers"]]


def run(config: dict[str, Any] | None = None) -> int:
    cfg = config or load_config()
    version = cfg["dna_version"]
    dna_dir = resolve_dna_dir(cfg)
    source_files = cfg["source_files"]
    legacy_versions = cfg.get("legacy_marker_versions", [])

    if not dna_dir.is_dir():
        print(f"ERROR: DNA directory not found: {dna_dir}", file=sys.stderr)
        return 1

    results: list[str] = []
    for consumer in cfg["consumers"]:
        target = resolve_consumer_path(consumer)
        permitted = set(consumer["permitted_tiers"])
        if not target.is_file():
            print(f"ERROR: consumer target missing: {target}", file=sys.stderr)
            return 1
        payload = build_payload(dna_dir, source_files, permitted)
        status = inject_into_file(target, version, payload, legacy_versions)
        results.append(f"{consumer['id']}: {status}")

    for line in results:
        print(line)
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--compare":
        results = compare_all()
        print(json.dumps(results, indent=2))
        return 0
    return run()


if __name__ == "__main__":
    sys.exit(main())
