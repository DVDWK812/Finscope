# Marketaux runner preparation — 26 October 2026 Sydney

**Prepared and offline-tested; no live request authorized, executed or scheduled.** The GDELT one-shot is completed/deleted and must not be recreated or retried. Its saved transport-failure audit is preserved.

`finscope.marketaux_runner` wires the existing nonretrying Marketaux adapter into `MarketauxSampler`. It dispatches **one sector sample per explicit invocation**, never a loop, scheduled task or automatic wait. Default/no-argument mode and `--dry-run` are offline previews: they read no credentials/approval files, instantiate no sampler and create no ledger. The legacy keyed Marketaux benchmark live path remains blocked.

```powershell
.venv/Scripts/python.exe -m finscope.marketaux_runner --dry-run
```

The CLI exposes no ledger/reset/cooldown override. It uses the existing `reports/marketaux_phase15.sqlite3` and shared cooldown path, leaving shared holds unchanged. All existing committed pre-dispatch reservations, duplicate/concurrency/crash rules, three/day and verified-quota-period/nine-total caps, fixed dates/sectors/window, 60-second minimum spacing and no-retry behavior remain enforced by the original sampler. Missed rounds/windows are not automatically moved or caught up. See [the policy](PHASE15_MARKETAUX_PLAN.md).

## What a future authorized invocation requires

**This task supplies neither authorization nor quota evidence.** Do not make these files or set their approval flag on the user's behalf without a separate explicit authorization. Preparing the executable is not approval to collect data.

After authorization, the operator supplies two ignored local JSON files. Approval must contain exactly:

- `study_id`: `marketaux-phase15-v1`.
- `explicit_user_authorization`: boolean true, only after the actual human approval.
- `approved_dates`: a nonempty subset of the unchanged planned UTC dates, 26/28/31 October 2026.
- `approved_sectors`: a nonempty subset of healthcare/technology/materials, including the requested sector.

Quota evidence must contain exactly `observed_at`, `period_start`, `period_end` (timezone-aware ISO timestamps) and integer `remaining`. It must reflect a real operator-checked dashboard balance/reset period: at most five minutes old, a known 24-hour quota period containing the request, and sufficient remaining allowance after reservations since the snapshot. A published limit or numeric per-minute header is not current account balance. Other account clients still require coordination.

Only then may a future operator explicitly request `--execute --sector <approved sector> --approval-file <local file> --quota-file <local file>`. This document does not run that command. Unknown/extra fields, unsupported dates/sectors, stale quota and missing keys fail closed. A flag/file is a human attestation, not a cryptographically verified authorization or a provider licence grant. Existing provider permissions remain unresolved; no production use is approved.

The runner reports `this_invocation_request_attempted` when the dispatcher was entered. This is not proof of a server response. Pre-dispatch denials report false; an exception after dispatch reports true/unknown and the committed reservation is retained. No exception body, key, title or description is echoed. Safe result output includes HTTP/status/count/latency metadata and description categories only; SQLite retains the guard's existing safe metrics. Never delete/reinitialize the ledger to repeat a call.

## Description and AI boundary

The CLI installs no semantic annotator: missing/exact-repeat rules run in memory and other text stays **uncertain**. The Python seam supports an explicitly supplied local, nonlogging reviewer hook when review/team-retention permissions are established; it does not wire in FinBERT, embeddings or any external service. Uncertain labels are not automatically promoted to informative text. Never re-request articles to recover discarded descriptions.

Core tests inject synthetic responses, temporary ledgers and clocks. They verify offline defaults, strict approval scope, fresh quota/key requirements, durable duplicate blocking and truthful ambiguous-dispatch flags. Existing sampler tests cover spacing, shared/study holds, budgets, failure stops and crash/concurrent reservations. No live news-provider call is part of preflight or CI. Production integration stays **NO-GO**.
