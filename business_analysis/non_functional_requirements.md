# Non-Functional Requirements

| Area | Requirement | Local verification | Production consideration |
|---|---|---|---|
| Performance | Complete the governed local customer-intelligence refresh within 10 minutes on the reference laptop. | Stage timings in `customer_intelligence_run_manifest.csv`. | Size compute and partitioning against production volume. |
| Reliability | Deterministic stages must fail closed unless an existing, non-empty governed output is explicitly reused. | Workflow status and tests. | Add scheduler retries, idempotency keys, and durable state. |
| Scalability | Transformations must remain set-based and avoid customer-by-customer network calls. | Code review and full-volume synthetic run. | Benchmark warehouse execution at expected peak volume. |
| Maintainability | Model, dataset, prompt, response, and evidence versions must be explicit. | JSON registry and AI execution log. | Connect approvals to release management. |
| Observability | Runs must expose stage status, duration, drift, quality, and evaluation results without secrets. | Automation manifest, alerts, monitoring reports. | Centralize metrics, logs, traces, and paging. |
| Security | Do not expose identifiers or credentials to AI output or logs; aggregate evidence only. | Privacy evals and sanitized log schema. | Add a managed secret store, DLP, IAM, encryption, and audit retention. |
| Recoverability | Generated outputs must be reproducible from governed inputs and code. | Make targets, registry hashes, and deterministic seeds. | Define backups, RPO/RTO, and disaster-recovery drills. |
| Usability | Decision outputs must disclose assumptions, uncertainty, data quality, and human-review status. | UAT and packet-schema checks. | Validate with named business owners and accessibility testing. |
| Reproducibility | The same governed inputs, seed, and method must reproduce analytical outputs within defined numeric tolerances. | Deterministic generation, Python/R reconciliation, and tests. | Pin runtime images and external dependencies. |
| Explainability | Churn scores must have global and local contribution evidence that reconciles to predictions. | Logistic log-odds contribution report. | Reassess method after any algorithm change. |
| Auditability | Models, data, prompts, evidence schemas, outputs, and decision status must be versioned or traceable. | JSON registry, lineage, manifests, and sanitized AI log. | Connect to enterprise retention policy. |
| Data freshness | Each run must surface missing/stale inputs and must not silently publish partially validated outputs. | Source presence, validation warnings, and stage manifest. | Define measured source-specific production targets. |
| AI safety | AI must reject unsupported metrics, identifiers, injection, and writes; provider failure must use bounded retry and safe fallback. | 18-case evaluation suite and structured response validation. | Complete external red-team and live-provider monitoring before real use. |

These controls demonstrate a local reference implementation, not a production SLA or enterprise security certification.
