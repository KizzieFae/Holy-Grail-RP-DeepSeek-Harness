"""Legacy V1 import-check entrypoint (no live RP scenario)."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy V1 orchestration smoke")
    parser.add_argument(
        "--check-imports",
        action="store_true",
        help="Verify fenced runtime and domain bootstrap imports resolve",
    )
    args = parser.parse_args(argv)

    if not args.check_imports:
        parser.print_help()
        return 0

    from legacy.v1_orchestration.bootstrap import ensure_v1_orchestration_paths

    ensure_v1_orchestration_paths()

    import turn_runner  # noqa: F401
    import model_client  # noqa: F401
    from character_loader import CharacterLoader  # noqa: F401

    print("legacy-v1-import-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
