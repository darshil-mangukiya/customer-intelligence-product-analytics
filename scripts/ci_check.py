from __future__ import annotations

import pytest

from scripts.check_readme_links import main as check_readme_links
from scripts.import_smoke import main as import_smoke


def main() -> None:
    import_smoke()
    check_readme_links()
    status = pytest.main()
    if status:
        raise SystemExit(int(status))
    print("\nCI quality gate passed.")


if __name__ == "__main__":
    main()
