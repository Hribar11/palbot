import logging

from palbot.client import PalBot
from palbot.settings import TOKEN, validate_startup_config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


if __name__ == "__main__":
    validate_startup_config()
    PalBot().run(TOKEN, log_handler=None)
