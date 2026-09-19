# Gênesis — Forage Foundation

## Purpose

This branch prepares the Forage source for later integration into Projeto Gênesis without coupling the economic-survival layer to the Automaton runtime.

The Forage repository currently contains `forage-main.zip` as the user-supplied source artifact. The ZIP remains preserved on `main`. This branch does not delete or replace it.

## Source analysis

The upstream Forage architecture is centered on an eight-step organism loop:

1. wake
2. check vitals
3. decide
4. act
5. reflect
6. pay
7. evolve
8. sleep

The implementation separates:

- `agent/` — core loop, genome, memory, skills, survival and organism state
- `evolution/` — mutation, fitness and genome history
- `economy/` — wallet, revenue split, payout and append-only ledger
- `capabilities/` — revenue-producing actions
- `infra/` — LLM routing, scheduling, watchdog and dashboard
- `safety/` — spending limits, kill switch and audit

This makes Forage a strong candidate for the Gênesis economic-survival layer.

## Gênesis mapping

| Forage | Gênesis role |
|---|---|
| Agent loop | Economic/autonomous operating cycle |
| Survival engine | Runway and survival state |
| Wallet + ledger | Treasury accounting boundary |
| Revenue engine | Revenue allocation/reinvestment policy |
| Genome | Agent behavioral configuration |
| Evolution engine | Controlled self-improvement |
| Memory | Economic experience memory |
| Capabilities | Revenue-producing adapters |
| Spending limiter | Hard economic guardrail |
| Kill switch | Emergency shutdown |
| Audit log | Immutable operational evidence |
| LLM router | Cost-aware reasoning provider |

## Integration boundary

Forage should not own:

- global agent identity
- the primary autonomous runtime
- cross-agent orchestration
- unrestricted filesystem execution
- live trading authorization
- final treasury authority

Those responsibilities belong to the future Gênesis control plane.

Forage should expose a narrow economic interface such as:

- `get_vitals()`
- `get_balance()`
- `record_expense()`
- `record_revenue()`
- `allocate_revenue()`
- `get_runway()`
- `evaluate_survival()`
- `propose_evolution()`
- `record_audit_event()`

## Important safety decision

The current Forage configuration explicitly disables trading and crypto-yield capabilities by default. Gênesis should preserve that default during development.

Any future crypto/forex adapter must sit behind:

1. explicit capability enablement;
2. per-action limits;
3. daily loss/spend limits;
4. emergency reserve;
5. audit logging;
6. kill switch;
7. dry-run/simulation mode;
8. independent approval policy.

No live financial execution is enabled by this branch.

## Next implementation phase

1. Import/verify the ZIP source tree.
2. Compare the ZIP against the upstream Forage implementation.
3. Establish a clean Python package layout in this repository.
4. Add Gênesis adapter interfaces around economy, survival and evolution.
5. Add deterministic tests for wallet, ledger, revenue allocation and survival transitions.
6. Add a dry-run economic simulator.
7. Only after those tests pass, design the bridge to the Gênesis treasury/runtime.

## Current state

- Automaton CI remains untouched.
- Forage branch: `genesis/forage-foundation`
- User ZIP: preserved as `forage-main.zip` on `main`
- Live trading: disabled
- First integration target: economic survival + evolution, not trading
