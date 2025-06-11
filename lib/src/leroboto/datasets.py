import lerobot.__version__ as lerobot_version

class DatasetImporter:
    """
    Imports a dataset from Hugging Face LeRobot into Roboto.
    """

    @staticmethod
    def print_lerobot_version():
        print(f"LeRobot version: {lerobot_version.__version__}")
