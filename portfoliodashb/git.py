from pathlib import Path

class Repository:
    directory: Path

    def __init__(self, directory: Path = Path(".")) -> None:
        self.directory = directory


    def _run(self, *command: str) -> Tuple[int, str, str]:
        """
        Returns (status, stdout, stderr)
        """

