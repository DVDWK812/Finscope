# Step 3 engineering acceptance — 5 November 2026 Sydney

**已完成当前支持环境下的工程交付；干净Windows端到端安装未验证。**

This closes the current-environment engineering delivery. Clean Windows installation
is an explicit limitation, not a prerequisite for the separately authorized SEntFiN
evaluation. No installer/model-management/performance feature expansion is included.

| Scope | Evidence and qualification |
|---|---|
| Supported machine | Windows x64, actual Python 3.12.3 environment; CI also tests Python 3.11. This is not a claim about every Windows configuration. |
| First-install entry points | Real venv creation/invocation under Chinese/space path; official missing-Python guidance; isolated server health/HTML 200; occupied-port rejection preserved the existing listener. |
| Pinned model preparation | Existing FinBERT/MiniLM files verified and reused, zero new weight transfers, 0.636 s observed. Interruption/corruption/cancel/mutex/double-click cases are mocked regression evidence. |
| Real base-model chain | Two new authored isolated records persisted and completed real FinBERT; backend released. Cold batch 66.433 s is one observation, not a throughput benchmark. |
| Cache and recovery | Reopening preserved the isolated records/results; another task reused them with zero new classification/inference. Injected resource pause/resume and classification-error independence were engineering tests, not naturally observed news failures. |
| Resource lifecycle | Three authored MiniLM/FinBERT cycles exited with verified code 0. System snapshots do not establish absence of memory leaks. User-owned LM Studio resources remain protected. |
| Optional LM Studio | Real Gemma basic authored inference and task-owned unload verified; not full semantic-classifier accuracy. Startup metadata discovery found Qwen3-1.7B Q6_K after restart without manual refresh; no startup inference or automatic model switch. |
| CI | Prior exact local baseline `d5fdc779fcaf1ce08f3fbd3f38f6ca745226a289`: all three jobs passed; subsequent annotation baseline `45e76b3778413229910cc63d9c80c8098d08d30e`: all three passed. |
| Still unverified | Clean Windows end-to-end setup without preinstalled Python, fully fresh dependencies, and first actual weight download. Existing environments/models were not deleted to simulate a new machine. |

The **41.174 s** cache task and later **15.082442 s** instrumented cache task are
different runs. They are **not a controlled optimization comparison or speedup**.
The later run separated queue, process/GPU, resource, model-state, cache and database
time; it cannot retroactively decompose the earlier receipt.

Evidence: [technical synopsis](REPORT_SYNOPSIS.md), ignored local
`reports/first_install_20261104/{result.json,server.json}`,
`reports/p0_closeout_20261104/result.json`, `reports/p0_20261104_models.json`,
and the dated startup discovery/timing receipts described in the synopsis.
Historical 2 November handoff and frozen evaluation remain unchanged.

CI references: [startup/timing baseline](https://github.com/DVDWK812/Finscope/actions/runs/41826695008),
[annotation-utilities baseline](https://github.com/DVDWK812/Finscope/actions/runs/41835478799).
