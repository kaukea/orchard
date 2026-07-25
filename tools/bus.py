#!/usr/bin/env python3
# Transitional shim — the bus was renamed to "courier" (Decision-085). Remove after one release.
import os, sys
from pathlib import Path
os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve().parent / "courier.py"), *sys.argv[1:]])
