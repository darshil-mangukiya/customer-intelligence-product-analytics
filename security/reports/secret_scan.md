# Sanitized Secret Scan

- Scanner: safe repository pattern and sensitive-file fallback scan (`gitleaks` was unavailable).
- Scope exclusions: `.git`, `.venv`, generated security reports, and the dependency lock.
- Secret values printed or retained: **NO**.
- Local `.env` file found: **NO**.
- Private key files outside excluded environments: **NO**.

| File | Finding type | Severity | Masked indicator | Action |
|---|---|---|---|---|
| `.env.example` | Environment variable placeholders | Informational | variable names only | Values were cleared; retain as a names-only template. |
| `docker-compose.yml` | Disposable development PostgreSQL defaults | Low | default development credential pair | Keep explicitly classified as local-only; never reuse for deployed environments. |

No embedded OpenAI key, customer-intelligence API key, token, private key, or non-placeholder credential was identified by the fallback scan. This does not claim the depth of a dedicated secret-scanning engine.
