#!/usr/bin/env python3
"""
CoC Auto Farming Bot — entry point.
Run:  python main.py
"""

import sys
from pathlib import Path
from loguru import logger

# ── Logging setup ──────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logger.remove()
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | {name}:{function}:{line} — {message}",
    level="INFO",
    colorize=True,
)
logger.add(
    "logs/bot.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
)

# ── Launch GUI ─────────────────────────────────────────────────────────────────
from gui import BotGUI


def main():
    logger.info("=" * 60)
    logger.info("CoC Auto Farming Bot starting")
    logger.info("=" * 60)

    try:
        app = BotGUI()
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nFATAL ERROR: {e}")
        print("Check logs/bot.log for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
