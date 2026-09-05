.PHONY: setup sample full analytics r-validate statistical-reconcile customer-intelligence test validate monitor app streamlit streamlit-check api orchestrate orchestrate-sample orchestrate-full registry executive-pdf experiment next-best-action forecast retention-lifecycle contracts enterprise-assets enterprise-quality activation enterprise-upgrade sql-analysis-check reports-check final-repo-check ci-check advanced postgres-load-small ci demo clean clean-local-cache

PYTHON ?= python3

setup:
	"$(PYTHON)" -m pip install -r requirements.txt

sample:
	"$(PYTHON)" -m etl.run_pipeline --customers 5000 --products 250 --orders 25000 --sessions 18000 --seed 42

full:
	"$(PYTHON)" -m etl.run_pipeline --customers 250000 --products 1500 --orders 1050000 --sessions 850000 --seed 42

analytics: experiment
	"$(PYTHON)" -m analytics.run_analysis

r-validate:
	"$(PYTHON)" -m analytics.r_validation

statistical-reconcile: r-validate

customer-intelligence:
	"$(PYTHON)" -m scripts.customer_intelligence

validate:
	"$(PYTHON)" -m validation.validate_data

monitor:
	"$(PYTHON)" -m monitoring.model_monitoring

app:
	"$(PYTHON)" -m streamlit run app/streamlit_app.py --server.port 8501

streamlit: app

streamlit-check:
	"$(PYTHON)" -m scripts.repository_check

api:
	"$(PYTHON)" -m uvicorn api.main:app --host 127.0.0.1 --port 8000

orchestrate:
	"$(PYTHON)" -m orchestration.dag_runner --downstream-only

orchestrate-sample:
	"$(PYTHON)" -m orchestration.dag_runner

orchestrate-full:
	"$(PYTHON)" -m orchestration.dag_runner --full-refresh

registry:
	"$(PYTHON)" -m model_registry.registry

executive-pdf:
	"$(PYTHON)" -m reports.executive_one_pager

experiment:
	"$(PYTHON)" -m experimentation.ab_testing

next-best-action:
	"$(PYTHON)" -m next_best_action.recommend_actions

forecast:
	"$(PYTHON)" -m forecasting.forecast_metrics

retention-lifecycle:
	"$(PYTHON)" -m retention_analytics.lifecycle_analysis

contracts:
	"$(PYTHON)" -m observability.schema_contracts

enterprise-assets:
	"$(PYTHON)" -m enterprise_assets.generate_enterprise_assets

enterprise-quality:
	"$(PYTHON)" -m observability.enterprise_quality

activation:
	"$(PYTHON)" -m activation.build_activation_exports

enterprise-upgrade: enterprise-assets enterprise-quality activation

sql-analysis-check:
	"$(PYTHON)" -m scripts.repository_check

reports-check:
	"$(PYTHON)" -m scripts.repository_check

final-repo-check:
	"$(PYTHON)" -m scripts.repository_check

advanced: analytics next-best-action forecast retention-lifecycle contracts executive-pdf

postgres-load-small:
	"$(PYTHON)" -m warehouse_loader.postgres_loader --small

ci:
	"$(PYTHON)" -m scripts.ci_check

ci-check: ci

demo:
	"$(PYTHON)" -m scripts.demo

test:
	"$(PYTHON)" -m pytest

clean: clean-local-cache

clean-local-cache:
	find . -path './.git' -prune -o -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache .cache .matplotlib dbt/target dbt/logs pytest-cache-files-*
	find . -path './.git' -prune -o -type f \( -name '*.tmp' -o -name '*.temp' -o -name '*.bak' -o -name '*~' \) -delete
