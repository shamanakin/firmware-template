<div align="center">

# FIRMWARE

### One canonical identity, injected per context — express only what each surface is allowed to see.

[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-0078D4?style=for-the-badge)]()

*A tier-gated identity-injection tool: manage who you are in one place, inject the right slice into each consumer.*

</div>

---

## What It Is

If several AI tools each need to know "who you are," you end up with identity copy-pasted everywhere — and drift the moment one copy changes. FIRMWARE is the regulatory layer that fixes that: **one canonical identity, tier-gated, injected downward** into each consumer with only the slice that context is permitted.

- **Tiers** (`core` / `clinical` / `personal` / `intimate`, or your own) scope what each consumer may see.
- The **injector** writes the permitted slice into managed blocks in each target; it **fails closed** on ambiguity rather than over-sharing.
- A **path registry** maps logical names to real locations, so moving things is a one-file edit, not a hunt-and-replace.

It sits between fixed identity (slow, deliberate) and expressed behavior (fast, contextual) — the marks that modulate *how* identity expresses without changing *who* you are.

## How It Works

You define your identity and its tiers, list your consumers in `consumers.json` (each with a permitted tier), point `paths.json` at your directories, and run `inject.py`. Each consumer gets a managed, regenerable block containing only its allowed tier. Re-running re-resolves everything from the single source.

## Quick Start

1. Clone this repository.
2. Fill your identity tiers and edit `consumers.json` (target + permitted tier per consumer) — see `TEMPLATE-README.md` and `PATHS-README.md`.
3. Set `paths.json`, then run `python inject.py` to inject the gated slices.

## Project Structure

```
firmware-template/
  inject.py          the tier-gated injector
  consumers.json     targets + permitted tier per consumer
  paths.json         logical-name → path registry
  paths.py           path resolution
  FIRMWARE-ROLE.md   what this layer is and isn't
  PATHS-README.md    registry guide
  TEMPLATE-README.md bring-your-own-identity guide
```

## License

MIT — see [LICENSE](LICENSE).
