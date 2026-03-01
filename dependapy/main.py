#!/usr/bin/env python3
"""Entry Point — delegiert an dependapy.presentation.cli."""

from __future__ import annotations

import sys

from dependapy.presentation.cli import cli_main


def main() -> int | None:
    """Einstiegspunkt für den ``dependapy``-Befehl."""
    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main() or 0)
