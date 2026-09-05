# PostgreSQL Backup, Restore, and Replay Drill

This is a bounded local recovery exercise on deterministic synthetic data, not a production disaster-recovery test or contractual SLA.

## Measured exercise

- Source: PostgreSQL 16.15 database `analytics` in the P3 Compose service.
- Backup: PostgreSQL custom format (`pg_dump -Fc`), 4.2 MB.
- Disposable restore target: `analytics_recovery_test`.
- Baseline: 25,037 raw transactions and gross revenue of 2,367,053.785350.
- First restore: exact row-count and revenue reconciliation; 0.442 seconds locally.
- Bounded destructive test: `raw.transactions` was truncated only in the disposable restore target; observed count became 0.
- Recovery: the disposable database was recreated and restored from the backup.
- Measured recovery restore time: 0.335 seconds.
- Post-restore reconciliation: 25,037 transactions and 2,367,053.785350 gross revenue, exact match.
- Original database after drill: unchanged and exactly reconciled.

## Replay and idempotency

The existing PostgreSQL loader was executed twice against the original local warehouse. Each replay completed 19/19 table loads. Before replay, after replay 1, and after replay 2, raw transactions remained 25,037 and gross revenue remained 2,367,053.785350. The truncate-and-append contract therefore did not duplicate rows or drift deterministic totals.

## Modeled internal objectives

- Reference Recovery Point Objective (RPO): 24 hours.
- Modeled Recovery Time Objective (RTO): 30 minutes for a bounded local restore and verification.
- Measured local restore result: 0.335 seconds for the 4.2 MB custom-format backup, excluding service provisioning and human approval time.

The RPO and RTO guide this recovery exercise; measured results are reported separately above.
