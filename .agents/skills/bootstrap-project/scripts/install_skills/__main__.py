"""Package entrypoint for install_skills.

Delegates to the canonical CLI implementation in ``.apply`` so the package has
exactly one parser/main. Invoke with ``python -m install_skills <command> ...``.
"""

from __future__ import annotations

from .apply import main

if __name__ == "__main__":
    raise SystemExit(main())
