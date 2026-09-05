from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _is_external(target: str) -> bool:
    return target.startswith(("http://", "https://", "mailto:", "#"))


def _clean_target(target: str) -> str:
    target = target.strip().split()[0]
    target = target.split("#", 1)[0]
    return unquote(target)


def main() -> None:
    missing: list[str] = []
    text = README.read_text(encoding="utf-8")
    for raw_target in LINK_RE.findall(text):
        target = _clean_target(raw_target)
        if not target or _is_external(target):
            continue
        if not (ROOT / target).exists():
            missing.append(raw_target)
    if missing:
        formatted = "\n".join(f"- {item}" for item in missing)
        raise SystemExit(f"README contains missing local links:\n{formatted}")
    print("README local links are valid.")


if __name__ == "__main__":
    main()
