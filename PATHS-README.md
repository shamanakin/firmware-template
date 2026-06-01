# NEXUS Path Registry

The path registry is NEXUS's proprioceptive coordinate system: **logical names** (stable roles) map to **physical paths** (current locations on disk).

## Files

| File | Purpose |
|------|---------|
| `paths.json` | Logical name → absolute path map (generated from current reality) |
| `paths.py` | Stdlib resolver: `resolve(name)`, `verify()`, `python3 paths.py --verify` |

## Rules going forward

1. **New systems reference logical names, not absolute paths.** Add a registry entry first, then use `resolve("your_name")` in code.
2. **A directory move = one registry edit.** Update the single `paths.json` entry; consumers re-resolve on next run.
3. **Always keep fallbacks** when migrating existing systems — if the registry or a key is missing, fall back to the prior hard-coded path so nothing breaks.
4. **Verify before commit.** Run `python3 paths.py --verify` after any registry change; every entry must exist.

## Adding an entry

1. Pick a stable, role-descriptive logical name (e.g. `circuits_matthew`, not `circuits_v2`).
2. Confirm the physical path exists on disk.
3. Add `"logical_name": "/absolute/path"` to `paths.json` (absolute paths only; `~` is expanded by the resolver).
4. Run `python3 paths.py --verify`.

## Current consumers

- **Injector (`inject.py`)** — resolves `dna_dir` and consumer targets via registry keys in `consumers.json`, with string-path fallbacks.

## Follow-up migration candidates

Not migrated in FOUNDATION-001 (by design):

- `_census/census.py`
- `_reflex/common.py` and reflex orchestrator
- `_github/repo-cartographer.py`
- RSAI `MANIFEST.md` references

These can adopt the registry once the injector proof pattern is stable.
