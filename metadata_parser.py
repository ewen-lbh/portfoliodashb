from typing import Dict

from ruamel import yaml

from console import console

METADATA_KEYS_WORTH_CHECKING = "created", "made with", "colors", "layout"


def metadata_keys_presence_map(description: str) -> Dict[str, bool]:
    """
    Parses the top of a description.md file's contents (the YAML portion).
    """
    presence_map = dict()
    parsed: dict = yaml.safe_load(_extract_metadata_part(description))
    for key in METADATA_KEYS_WORTH_CHECKING:
        presence_map[key] = key in parsed.keys()
    return presence_map


def _extract_metadata_part(description: str) -> str:
    in_metadata_block = False
    metadata_part = str()
    for line in description.splitlines():
        if not line.strip():
            continue
        if line == "---":
            in_metadata_block = not in_metadata_block
            continue
        if in_metadata_block:
            metadata_part += line + "\n"

    return metadata_part
