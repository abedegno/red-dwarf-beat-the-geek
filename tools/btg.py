#!/usr/bin/env python3
"""Owner build/deployment entry point. Run python3 tools/btg.py --help."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.owner.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
