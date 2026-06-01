# FIRMWARE Template — Tier-Gated Identity Injection

> Generic DNA injector scaffold. **Mechanism preserved; operator paths and DNA removed.**

## What this is

The FIRMWARE layer sits between fixed identity (DNA) and runtime behavior:

- `inject.py` — tier-gated, idempotent slice injection into consumer repos
- `consumers.json` — declares which repos receive which DNA tiers
- `paths.json` — registry of logical workspace roots (BYO paths)

## BYO workflow

1. Point `dna_dir` in config to **your** DNA repository.
2. Register consumers with appropriate tier ceilings.
3. Use paired injection markers in consumer repos (see inject.py docs).
4. Never copy canonical DNA from another operator.

## Verify

Zero `block` findings from sanitizer; zero operator identity in raw grep.
