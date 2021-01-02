#!/usr/bin/env python

from pathlib import Path
from typing import Any, List, Optional
import os
import subprocess

from rich.table import Column, Table
from rich.text import Text
from typer import Argument, Typer

from portfoliodashb.config import load_config
from portfoliodashb.console import console
from portfoliodashb.constants import CONFIG_FILEPATH
from portfoliodashb.crawler import crawl
from portfoliodashb.metadata_parser import (
    METADATA_KEYS_WORTH_CHECKING,
    has_lang,
    metadata_keys_presence_map,
)

cli = Typer()
config = load_config(CONFIG_FILEPATH)


@cli.command("dash")
def health(directory: Path = Argument(None), show_all: bool = False):
    directory = Path(directory or config.projects_directory)

    table = Table(
        Column("project path"),
        # Column("enabled"),
        *(Column(key) for key in METADATA_KEYS_WORTH_CHECKING),
        ":: fr",
        ":: en",
        Column(
            "Quick link to description.md",
        ),
        title=f".portfoliodb completion status for projects in [blue]{directory}[/blue]",
    )

    for project, portfoliodb_description in crawl(directory).items():
        if not portfoliodb_description and not show_all:
            continue

        portfoliodb_description = portfoliodb_description or ""

        metadata_presence = {k: False for k in METADATA_KEYS_WORTH_CHECKING}
        if portfoliodb_description:
            metadata_presence = metadata_keys_presence_map(portfoliodb_description)

        in_french = has_lang(portfoliodb_description, "fr")
        in_english = has_lang(portfoliodb_description, "en")
        is_done = all(metadata_presence.values()) and in_english and in_french

        if not any(metadata_presence.values()) and not show_all:
            continue

        table.add_row(
            (f"[red]●[/red] " if not is_done else "  ")
            + f'[link={str(directory / project / ".portfoliodb" / "description.md")}]{project}[/link]',
            # checkmark(portfoliodb_description),
            *(
                checkmark(metadata_presence[key])
                for key in METADATA_KEYS_WORTH_CHECKING
            ),
            checkmark(in_french),
            checkmark(in_english),
            "[grey]"
            + str(directory / project / ".portfoliodb" / "description.md")
            + "[/grey]",
        )

    console.print(table)


@cli.command("fill")
def fill(directory: Path = Argument(None), ignore: List[str] = None):
    """
    Creates missing .portfoliodb/description.md files in projects
    """
    ignore = ignore or []
    directory = Path(directory or config.projects_directory)
    filled_count = 0
    for project, portfoliodb_description in crawl(directory).items():
        if portfoliodb_description:
            continue
        console.print(f"For [blue]{project}[/blue]:")
        if project in ignore:
            console.print(f"  -> [red]Ignored[/red] by --ignore")
            continue

        console.print(
            f"  -> Creating directory [cyan]{str(directory / project / '.portfoliodb')}[/cyan]"
        )
        (directory / project / ".portfoliodb").mkdir(exist_ok=True)
        console.print(
            f"  -> Creating file [cyan]{str(directory / project / '.portfoliodb' / 'description.md')}[/cyan]"
        )
        with open(
            directory / project / ".portfoliodb" / "description.md",
            "w",
            encoding="utf-8",
        ) as description_file:
            description_file.write(
                f"""\
---
created: ????-??-??
made with:
    -

colors:
    primary:
    secondary:

layout:
    - 
---

# {project.replace('-', ' ').replace('_', ' ').title()}
"""
            )
            filled_count += 1
    console.print("\n" + "[yellow] ~ [/yellow]" * 5 + "\n")
    if filled_count:
        console.print(
            f"Filled [yellow]{filled_count}[/yellow] projects with an empty description.md file"
        )
    else:
        console.print(f"Everything's already filled :smile:")

@cli.command("prune")
def prune(directory: Path = Argument(None), ignore: List[str] = None):
    """
    Removes .portfoliodb/description.md when no checks are passed (everything is "no" on the dashboard entry)
    """
    ignore = ignore or []
    directory = Path(directory or config.projects_directory)
    pruned_count = 0
    for project, portfoliodb_description in crawl(directory).items():
        if not portfoliodb_description:
            continue
        metadata_presence = metadata_keys_presence_map(portfoliodb_description)
        if any(metadata_presence.values()):
            continue
        console.print(f"For [blue]{project}[/blue]:")
        if project in ignore:
            console.print(f"  -> [red]Ignored[/red] by --ignore")
            continue
        
        console.print(
            f"  -> Removing file [cyan]{str(directory / project / '.portfoliodb' / 'description.md')}[/cyan]"
        )
        (directory / project / ".portfoliodb" / "description.md").unlink()
        pruned_count += 1
    console.print("\n" + "[yellow] ~ [/yellow]" * 5 + "\n")
    if pruned_count:
        console.print(
            f"Pruned [yellow]{pruned_count}[/yellow] projects with no valuable description.md file"
        )
    else:
        console.print(f"Everything's fine :smile:")

@cli.command("edit")
def edit(project: str, directory: Optional[str] = None):
    editor = os.getenv("EDITOR", "nano")
    subprocess.run((editor, Path(directory or config.projects_directory) / project / ".portfoliodb" / "description.md"))

def checkmark(o: Any) -> Text:
    # return ":white_heavy_check_mark" if o else ":cross_mark:"
    return console.render_str(text="[green]yes[/green]" if o else "[red]no[/red]")


if __name__ == "__main__":
    cli()
