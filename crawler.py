from pathlib import Path
from typing import Dict, List, Optional

from config import load_config
from constants import CONFIG_FILEPATH

config = load_config(CONFIG_FILEPATH)


def crawl(directory: Path) -> Dict[str, Optional[str]]:
    """
    Crawls all the projects in directory and
    returns a dict mapping project IDs (folder names) to:

    - None if the project has no .portfoliodb
    - a string containing the .description.md file's contents
    """
    crawled = dict()
    for project in directory.iterdir():
        if not project.is_dir():
            continue

        if project.name.startswith(".") and config.ignore_dotfiles:
            continue

        if not (project / ".portfoliodb" / "description.md").exists():
            crawled[project.name] = None
            continue

        with open(
            project / ".portfoliodb" / "description.md", "r", encoding="utf-8"
        ) as description_file:
            crawled[project.name] = description_file.read()

    return crawled
