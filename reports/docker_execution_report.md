# Docker Compose Execution Report

- Compose configuration: PASS.
- Hash-locked image build: PASS after Linux-conditional `greenlet` and `watchdog` dependencies were made explicit.
- PostgreSQL: healthy on isolated host port 55433.
- FastAPI: healthy on isolated host port 18000.
- Streamlit: healthy on isolated host port 18501.
- Pipeline: completed all existing stages and exited 0.
- Application runtime user: non-root `app` for pipeline, API, and Streamlit.
- Security controls: `no-new-privileges`, narrow data-only API/Streamlit mounts, named PostgreSQL volume, service health checks.
- Unrelated services already using ports 8000 and 8501 were identified and left untouched.
- Container vulnerability scan: BLOCKED — Trivy or an equivalent local image scanner was unavailable.

This report records a local integration run on deterministic generated data.
