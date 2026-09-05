# Generated Data

This folder is the local landing area for generated raw data, processed feature bases, BI marts, dashboard exports, rejected rows, and audit manifests.

The generated CSV files are intentionally ignored by Git because the full data output is approximately 1.9 GB and several files exceed GitHub's 100 MB file limit.

Regenerate data locally:

```bash
make sample
make full
make orchestrate
```

Expected subfolders:

- `raw/`
- `processed/`
- `marts/`
- `exports/`
- `rejected/`
- `audit/`
