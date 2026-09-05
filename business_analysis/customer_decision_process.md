# Customer Decision Process

## Modeled AS-IS

Customer Data → Separate Analysis → Manual Segment Review → Manual Experiment Review → Disconnected Retention Decisions

## Implemented TO-BE reference flow

Customer Data → Governed Customer 360 → Churn / CLV / RFM → Experiment Evidence → Segment Migration → Retention Economics → Action Center → Human Review → Approved External Action

1. Validate synthetic source contracts and refresh governed analytical outputs.
2. Review quality alerts, experiment validity, Python/R reconciliation, model validation, and drift status.
3. Use churn risk, CLV exposure, segment movement, forecast evidence, and retention scenarios to frame a decision—not to automate one.
4. Query the governed aggregate insight packet when narrative support is useful. The AI layer must copy evidence values and surface uncertainty.
5. A human owner selects, rejects, or requests further analysis and records assumptions, constraints, fairness/privacy considerations, and the intended success metric.
6. Any intervention requires a prospective test, capacity check, approval, and monitoring plan. No customer activation is performed by this repository.

Decision rights remain with business and governance owners. Statistical significance is separated from practical significance, modeled economics are labeled as scenarios, observational drivers are not presented as causes, and all evidence remains synthetic.

| Modeled current issue | Target capability | P3 solution | Benefit | Residual limitation |
|---|---|---|---|---|
| Disconnected analytical outputs | Governed evidence chain | Customer insight packet and lineage | Consistent review context | Local synthetic implementation |
| Threshold chosen without capacity | Capacity-aware decision framing | Top-K and threshold economics | Transparent tradeoffs | Assumptions need real validation |
| Experiment result viewed without validity | Explicit validity gate | SRM and Python/R reconciliation | Prevents unsupported rollout language | Synthetic experiment only |
| Narrative can drift from metrics | Evidence-grounded explanation | Structured AI schema and fidelity evals | Traceable numbers and warnings | Live-provider evidence requires a recorded execution |
