# STELLAR HORIZON

A horizontal 16-bit space shooter built on Void-Hunter's movement library.

## Run

```bash
# Smoke test (11 gates, ~5s)
python stellar_horizon/smoke.py

# Play the game
python -m stellar_horizon.main

# Play for N seconds then quit
python -m stellar_horizon.main --duration 60

# Validate imports + settings
python -m stellar_horizon.main --check
```

## Tests

```bash
python -m pytest stellar_horizon/tests/ -v
```

## Spec

`docs/superpowers/specs/2026-08-15-stellar-horizon-design.md`
`docs/superpowers/plans/2026-08-15-stellar-horizon-phase1.md`
