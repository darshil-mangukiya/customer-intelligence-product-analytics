# Controlled Pandas Pipeline Performance Benchmark

Profiles ran in isolated disposable directories with deterministic seed 42. This is a local benchmark, not a production or cloud-scale claim.

| Profile | Customers | Transactions | Sessions | Total s | Peak RSS MB | Output MB | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| 5k | 5,000 | 25,037 | 18,018 | 26.78 | 427.17 | 40.02 | PASS |
| 50k | 50,000 | 250,375 | 180,180 | 130.69 | 1462.98 | 388.54 | PASS |

## Interpretation

Model training and scoring are reported together because the existing pipeline stages do not expose separate timing boundaries.
The 250K-customer profile was not forced during this bounded local pass because it implies substantially larger order/session volumes and was not necessary to establish representative single-node scaling.
Pandas remained adequate for the executed profiles; the largest observed bottleneck is identified from the stage timings in the CSV evidence.
