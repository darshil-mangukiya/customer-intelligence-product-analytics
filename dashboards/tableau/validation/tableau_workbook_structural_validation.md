# Tableau Workbook Structural Validation

**Status: PASS — AUTOMATED STRUCTURAL VALIDATION.**

This report validates XML structure and internal references. Separate manual evidence confirms Tableau Desktop rendering; it does not separately certify every parameter or action.

The final workbook is well-formed XML. Its native Tableau 18.1 document shape is validated through structural checks and confirmed Tableau Desktop 2026.1 rendering.

## Object inventory

| Object | Count |
|---|---:|
| Governed Datasources | 9 |
| Parameter Datasources | 1 |
| Worksheets | 36 |
| Dashboards | 7 |
| Storyboards | 1 |
| Story Points | 7 |
| Calculations | 33 |
| Core Calculations | 16 |
| Lod Calculations | 8 |
| Table Calculations | 7 |
| Helper Calculations | 2 |
| Parameters | 4 |
| Hierarchies | 3 |
| Worksheet Filters | 45 |
| Actions | 5 |
| Active Calculations | 1 |
| Active Lod Calculations | 0 |
| Active Table Calculations | 0 |
| Active Parameter Dependencies | 0 |

## Errors

- None.

## Warnings

- Parameter and action behavior requires separate Tableau Desktop interaction testing.
- All nine standalone-TWB CSV connection directories use the portable `../data` reference.

## Checks performed

- XML generated as UTF-8 and parsed successfully.
- All nine CSV references, named connections, relation names, and table names resolve to the governed project data folder.
- Native textscan capability records and connection child ordering match Tableau 2026.1-authored local workbooks.
- All field datatypes are supported; booleans are categorical dimensions with Count metadata.
- All 36 worksheet datasource and transitive field dependencies resolve with zero missing references.
- Runtime-critical worksheets use prepared physical fields wherever available; no worksheet actively depends on an LOD, table calculation, or parameter.
- The build fails on empty dependencies, orphaned filters, duplicate worksheet/calculation names, unsupported XML, stale source tokens, or temporary/extract paths.
- Datasource, worksheet, dashboard, storyboard, calculation, parameter, hierarchy, filter, and action names are unique/resolved.
- Dashboard worksheet zones and story-point dashboard references resolve.
- No personal filesystem path, external Tableau URL, credential, development placeholder, or assistant-development residue is present.

## Final evidence boundary

All seven dashboards and all seven Story points were manually opened successfully in Tableau Desktop 2026.1. Eight genuine screenshots are present, the unchanged portable TWBX passed close/reopen validation, and the standalone TWB passed manual reopen validation after its connection-path-only edit. Parameter/action checks remain optional interaction QA.
