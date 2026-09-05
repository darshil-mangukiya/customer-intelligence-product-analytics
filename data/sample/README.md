# Sample Data

This folder contains tiny committed CSV samples so reviewers can inspect table shape without generating the full synthetic dataset.

The production-scale CSV outputs are intentionally excluded from Git because the full generated data is approximately 1.9 GB.

Use these files for quick orientation only. To build real marts and model outputs, run:

```bash
make sample
make orchestrate
```
