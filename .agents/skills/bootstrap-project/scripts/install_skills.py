#!/usr/bin/env python3
"""Plan and apply receipt-aware skill adoption from Agent Guidance Kit.

This can be run as a script or imported as a package.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for package imports when run as script
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent))

from install_skills import main

if __name__ == "__main__":
    raise SystemExit(main())
