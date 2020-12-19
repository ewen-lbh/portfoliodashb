from typing import Dict

from ruamel import yaml

from portfoliodashb.console import console

METADATA_KEYS_WORTH_CHECKING = "created", "made with", "colors", "layout", "tags", "wip"


def metadata_keys_presence_map(description: str) -> Dict[str, bool]:
    """
    Parses the top of a description.md file's contents (the YAML portion).
    """
    presence_map = dict()
    parsed: dict = yaml.safe_load(_extract_metadata_part(description))

    for key in METADATA_KEYS_WORTH_CHECKING:
        presence_map[key] = key in parsed.keys() and parsed.get(key) is not None

    if "?" in str(parsed.get("created", "????-??-??")):
        presence_map["created"] = False

    made_with = parsed.get("made with", [None])
    if type(made_with) is list:
        if len(made_with) == 1 and made_with[0] is None:
            presence_map["made with"] = False

    layout = parsed.get("layout", [None])
    if type(layout) is list:
        if len(layout) == 1 and layout[0] is None:
            presence_map["layout"] = False

    colors = parsed.get("colors", dict())
    if type(colors) is dict:
        if colors.get("primary") is None and colors.get("secondary") is None:
            presence_map["colors"] = False

    return presence_map


def has_lang(description: str, lang: str) -> bool:
    lines = [line.strip() for line in description.splitlines()]
    return ":: " + lang in lines


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
