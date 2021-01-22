from pathlib import Path
import re
from typing import List
import subprocess

class NoRepoHere(Exception):
    pass

class Repository:
    directory: Path

    def __init__(self, directory: Path = Path(".")) -> None:
        self.directory = directory
        if not (directory / ".git").exists():
            raise NoRepoHere(f"No .git found in {directory}")

    @property
    def remotes(self) -> List[str]:
        result: List[str] = []
        status, stdout, stderr = self.run("remote", "--verbose")
        if status != 0:
            raise subprocess.SubprocessError(f"Process exited with {status}: {stderr}")
        
        pattern = re.compile(r'origin\s+(\w+://.+)\s+\((?:fetch|push)\)')
        # Parse remotes
        for line in stdout.splitlines():
            if (match := pattern.match(line)):
                result.append(match.group(1))
        
        return result
    
    @property
    def tags(self) -> list[str]:
        status, stdout, stderr = self.run("tag")
        if status != 0:
            raise subprocess.SubprocessError(f"Process exited with {status}: {stderr}")

        return list(stdout.splitlines())

    def run(self, *command: str) -> tuple[int, str, str]:
        """
        Returns (status, stdout, stderr)
        """
        if command[0] != "git":
            command = ["git"] + list(command)
        output = subprocess.run(command, capture_output=True, encoding='utf-8', cwd=self.directory)
        return output.returncode, output.stdout, output.stderr
