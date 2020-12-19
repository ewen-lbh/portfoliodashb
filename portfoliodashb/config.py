from pathlib import Path

from pydantic import BaseModel
from ruamel import yaml

from portfoliodashb.console import console


class Configuration(BaseModel):
    projects_directory: str = "~/projects"
    ignore_dotfiles: bool = True


def _key_transform(key: str) -> str:
    return key.replace(" ", "_").lower().strip()


def _transform_keys(o: dict) -> dict:
    transformed = dict()
    for key, value in o.items():
        if type(value) is dict:
            value = _transform_keys(value)
        transformed[_key_transform(key)] = value
    return transformed


def load_config(filepath: Path) -> Configuration:
    with open(filepath, "r") as file:
        parsed = yaml.safe_load(file)  # TODO: parse with version 2
    parsed = _transform_keys(parsed)
    return Configuration(**parsed)
