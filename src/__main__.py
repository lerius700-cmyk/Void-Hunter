"""Allow `python -m src` to launch the game.

Equivalent to `python main.py` at the project root.
"""
from __future__ import annotations

import sys

from main import main

if __name__ == "__main__":
    sys.exit(main())
