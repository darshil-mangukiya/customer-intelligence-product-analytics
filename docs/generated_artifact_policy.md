# Generated Artifact Policy

This policy separates reproducible source from reviewable evidence and disposable runtime state. It does not stage or commit anything automatically.

| Class | Examples | Intended handling |
|---|---|---|
| Source and configuration | Python/R/SQL/dbt code, Makefile, Dockerfile, Compose, workflow, dependency declarations | Review and commit deliberately. |
| Reproducibility inputs | `requirements.lock`, dbt package lock, env-name-only profile/template | Review and commit; never include real credentials. |
| Concise authoritative evidence | Markdown reports, audit CSVs, SBOM, dependency/secret/license reports | Review for sensitive/local-path content; commit when useful for the portfolio release. |
| Large dbt runtime evidence | `artifacts/dbt/manifest.json`, catalog and run results | Retain for this local audit, inspect size/diff, then either archive with a release or regenerate; do not commit automatically. |
| Reproducible full-volume data | `data/raw`, `data/processed`, `data/marts`, most `data/exports` | Keep ignored and regenerate from seed/configuration. Commit only curated small samples. |
| Model binaries | Existing governed `.joblib` artifacts | Preserve under the established repository policy; pair with registry hashes and regeneration evidence. |
| Runtime scratch | dbt target/packages/logs, caches, temporary benchmark roots, local Compose state | Ignore and regenerate. Disposable temporary benchmark roots may be removed after evidence is written. |
| Local secrets | `.env`, API keys, database credentials, provider tokens | Never commit or archive. Use environment variables or ignored local profiles. |
| Power BI binary | Existing PBIX under Git LFS | Preserve unchanged unless a separately authorized Power BI task is performed. |

Before any future release, review `git status`, inspect every untracked evidence file, scan for secrets, confirm large-file handling, and stage only explicitly selected artifacts.
