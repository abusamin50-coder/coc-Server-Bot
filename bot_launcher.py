#!/usr/bin/env python3
"""Bot Launcher — web server থেকে bot run করার জন্য।"""

import sys
import json
import yaml
from pathlib import Path

# Parent directory add
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from adb_controller import ADBController
from vision import TemplateMatcher
from bot_engine import CoCBot


def main():
    if len(sys.argv) < 3:
        print("Usage: bot_launcher.py <device_id> <config_json>")
        sys.exit(1)

    device_id = sys.argv[1]
    config_json = sys.argv[2]

    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid config JSON: {e}")
        sys.exit(1)

    # Logging
    Path("logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(
        f"logs/bot_{device_id}.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    )

    logger.info(f"Starting bot for device {device_id}")

    try:
        # ADB controller
        adb_config = config.get("adb", {})
        adb = ADBController(
            device_id=adb_config.get("device_id", device_id),
        )

        # Vision
        vision = TemplateMatcher(
            templates_dir="troop_images",
        )

        # Bot engine
        bot = CoCBot(adb=adb, vision=vision, config=config)
        bot.run()

    except KeyboardInterrupt:
        logger.info("Bot interrupted")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
