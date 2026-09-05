# Model Artifact Recovery Check

Churn, segmentation, and CLV artifacts were regenerated twice from the same processed synthetic inputs, code, configuration, and seed in disposable directories.

| Model | Meaningful comparison | Observed | Required | Status |
|---|---|---:|---:|---|
| churn | maximum probability difference | 0 | 0 | PASS |
| segmentation | cluster assignment match rate | 1 | 1 | PASS |
| clv | maximum predicted CLV difference | 0 | 0 | PASS |

Meaningful predictions/assignments were compared instead of serialized bytes because serialization metadata is not the model behavior contract.
