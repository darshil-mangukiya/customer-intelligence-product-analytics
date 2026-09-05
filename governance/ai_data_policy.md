# AI Data Policy

The Customer Strategy & Experiment Copilot is an advisory explanation layer over a deterministic, aggregate customer-insight packet. P3 uses synthetic data, but the controls model professional handling of customer information.

## Allowed external-LLM content

- Aggregated customer KPIs and anonymized segment summaries
- Aggregate segment migrations and churn-associated driver results
- CLV, cohort, experiment, SRM, Python/R reconciliation, and scenario outputs
- KPI definitions, methodology, data-quality warnings, and source artifact names

## Prohibited content

- Names, emails, phone numbers, street addresses, or authentication data
- Unnecessary customer-level identifiers or raw event histories
- Secrets, API keys, database credentials, or environment-variable values
- Arbitrary SQL, shell access, database writes, CRM writes, or outbound communications

The LLM must not calculate authoritative metrics, convert association into causation, approve experiments, contact customers, or change an external system. Responses are advisory and use `NEEDS_REVIEW` until a human reviewer makes a decision.

The OpenAI provider uses the Responses API with Structured Outputs and `store=false`. `OPENAI_API_KEY` and `OPENAI_MODEL` are read only from the environment and are never written to project artifacts. Local review remains available through the deterministic fake provider and AI-disabled mode without external credentials.

Implementation reference: [official OpenAI Responses API create-response documentation](https://developers.openai.com/api/reference/cli/resources/responses/methods/create). Real provider execution is recorded only when both environment variables exist and a structured call succeeds.
