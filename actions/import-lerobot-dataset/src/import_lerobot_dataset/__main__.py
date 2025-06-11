from roboto import User
from leroboto import DatasetImporter

from .logging import DEFAULT_LOGGER as logger
from .logging import setup_logging

setup_logging()

user = User.for_self()
logger.info(f"Hello, {user.name}!")

DatasetImporter.print_lerobot_version()