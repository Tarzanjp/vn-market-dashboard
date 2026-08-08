#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chỉ merge data/grok-fill.json vào snapshot (không gọi API mạng)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_update import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(skip_fetch=True))
