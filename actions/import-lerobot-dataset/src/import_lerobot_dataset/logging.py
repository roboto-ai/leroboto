import logging

DEFAULT_LOGGER = logging.getLogger("import_lerobot_dataset")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
