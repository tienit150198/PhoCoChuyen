# Lag and 1,000 CCU capacity remediation

Goal: identify and fix the measured API memory/latency collapse at 1,000 authenticated players and 200 commands/s, then inspect browser frame pacing. Preserve command validation, transactions, idempotency and the soft 2.5D art.

1. Reproduce against the immutable f3ada34 baseline in a disposable PostgreSQL database. Collect per-process memory/thread counts and thread stacks during the increase. Include periodic full validations; do not use production data or the user's preview database.
2. Establish a specific root cause from the evidence. Add a regression test, make the smallest justified correction, and run storage/concurrency tests. Changes to unrelated fair files stay untouched.
3. Repeat the same fixed-arrival 1,000-player / 200-command-per-second scenario with identical fixtures and resource limits. Record failures, throughput, latency, OOM events and resource use. A run that silently reduces throughput is not a pass. Follow with a longer soak across validation cycles.
4. Inspect the real preview's frame timing and active scene work. Fix a demonstrated client bottleneck with a targeted regression/check if one is present.
5. Save an evidence report with reproducible commands and limitations. Local Docker has 8 vCPU, so a 9-core production certification is outside this test. Keep the user's preview available and remove only disposable test services and credentials.

Acceptance targets for this local workload: all 1,000 connections established, no OOM or unplanned disconnections, no command errors, sustained requested throughput, API p95 below 300 ms and peer movement p95 below 150 ms. These are test targets, not guarantees for all devices, Internet links or future careers.

Progress / evidence-driven extension:

- Reproduced allocation retention and idle HTTP admission separately. Fixed bounded reusable command workers, delta closure cycles, idle timeout and explicit command response closure. Final combined backend suite: 91 tests OK (one Node-dependent test skipped in the Linux image; host Node delta test passed separately).
- The 600-second application-only run completed 119,995 commands with zero HTTP errors/OOMs, but five scheduled slots were missed and p95 remained 846 ms. This does not meet the original latency target.
- Read-only PostgreSQL sampling captured ten COMMIT statements waiting for WALWrite for 559–603 ms. Extend step 3 to a clean, same-quota/same-fixture run with LZ4 WAL compression and a 4 GB WAL checkpoint threshold. Preserve all durability settings. No production configuration is changed. Keep the failed/default-database result in the report.
- Short browser frame-pacing checks passed without a demonstrated renderer regression; no speculative visual/runtime client changes were made.

Stop point requested by user:

- WAL/memory/CPU diagnostic failed; no production tuning profile is recommended. Preserve mixed-run metadata separately.
- Fixed confirmed statistics batch deadlock with SQL canonical lock order. Regression reproduced SQLSTATE 40P01 before the fix. Final combined suite: 98 tests, 69.410 seconds, OK with one Node-dependent skip.
- User asked to stop additional work, commit and push. No fresh 100 RPS or post-retention load run was started. Original API p95 target remains unmet; report that explicitly.
