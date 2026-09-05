# Change Impact Assessment

This assessment compares the baseline workflow with the implemented reference process and its controls.

| Area | Fragmented/manual baseline | Governed automated target | Modeled impact | Control |
|---|---|---|---|---|
| Experimentation | Result-focused A/B output | Registry, power/MDE, SRM, readout, decision log | Stronger validity and traceability | Failed SRM blocks interpretation |
| Segmentation | Current-state segments | Historical-cutoff migration and matrix | Movement becomes reviewable | Missing history disclosed |
| Finance | Separate CLV/risk outputs | Assumption-driven scenario economics | Tradeoffs become comparable | Estimates never labeled observed |
| Retention | Multiple analytical files | Prioritized action-center export | Review queue becomes reproducible | `NEEDS_REVIEW`; no activation |
| BI | Independent exports | Reconciled machine-readable outputs | Easier semantic-layer consumption | Automated source/output checks |
| Operations | Multiple commands | `make customer-intelligence` | Reproducible refresh evidence | Stage manifest and validations |
| AI | No narrative layer | One evidence-grounded copilot | Faster governed interpretation | Aggregate-only packet and schema validation |

## Persona impacts

- Retention and Customer Strategy personas gain ranked advisory evidence, not automated campaign authority.
- Finance gains scenario comparisons with assumptions kept separate from realized-impact accounting.
- Product gains experiment validity and decision traceability, not automatic approval.
- Analysts retain ownership of deterministic metrics and statistical methods.
- BI developers gain stable exports and reconciliation without PBIX modification.

## Adoption and risk controls

Review metric definitions, execute UAT, verify source evidence, preserve holdouts, and require human approval before operational use. Rollback is local file-level reversal; no external state, CRM record, customer contact, or production allocation is changed.
