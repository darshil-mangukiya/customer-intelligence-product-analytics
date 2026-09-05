"""Public retention-economics interface backed by the governed decision-support implementation."""

from analytics.customer_decision_support import SCENARIOS, build_retention_economics, calculate_retention_scenarios

__all__ = ["SCENARIOS", "build_retention_economics", "calculate_retention_scenarios"]


def main() -> None:
    build_retention_economics()


if __name__ == "__main__":
    main()
