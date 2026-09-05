# Customer Intelligence Lineage

All source data in this project is synthetic. The companion CSV traces each governed decision output to its source, transformation, and validation control.

The main path is synthetic raw data → validated customer features and order facts → churn, CLV, segmentation, forecast, and experiment outputs → reconciled customer insight packet → human-reviewed advisory decisions. AI responses can only consume the aggregate packet and do not recalculate statistical results.

Change control is local and file-based: model and dataset versions are recorded in the JSON registry; run stages appear in the automation manifest; contract, reconciliation, drift, UAT, and AI evaluation outputs provide test evidence. No reverse-ETL write or automated customer action is authorized.
