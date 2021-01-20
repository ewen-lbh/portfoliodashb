#!/usr/bin/env python

from pathlib import Path
import socketserver
from http.server import BaseHTTPRequestHandler
from typing import Any, Dict, List, NamedTuple, Optional
import os
import subprocess
import re

from rich.table import Column, Table
from rich.text import Text
from typer import Argument, Typer


from portfoliodashb.config import load_config
from portfoliodashb.console import console
from portfoliodashb.constants import CONFIG_FILEPATH
from portfoliodashb.crawler import crawl
from portfoliodashb.metadata_parser import (
    METADATA_KEYS_WORTH_CHECKING, get_metadata,
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

@cli.command("web")
def webdash(directory: Optional[str] = None, port: int = 8000):
    class WebdashServer(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/":
                self.send_error(404, "Not Found")
                return
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(bytes(create_html(directory or config.projects_directory), "utf-8"))
            
            return
    server = socketserver.TCPServer(("", port), WebdashServer)
    server.serve_forever()

def create_html(directory: str) -> str:
    # Setup columns
    columns = [
        "logo",
        "project name",
        "is it a contribution? ",
        "progress state",
        "progress status",
        "latest version",
        "latest published version ",
        "technologies used",
        "tags",
        "github repo",
        "project path",
    ]
    html = f'''
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>portfoliodashb web dashboard</title>
</head>

<body><em>In directory <code>{directory}</code></em>
    <table>
        <tr>{''.join('<th>' + column + '</th>' for column in columns)}</tr>
        <!-- {{\n.join([ create_row(row) for row in projects ])}} -->
        <code>{os.getenv("GHTOK")}</code>
    </table>
</body>

</html>'''

    return html

class WebDashRow:
    directory: Path
    description: str
    metadata: Dict[str, Any]

    def __init__(self, directory: Path, description: str) -> None:
        self.directory = directory
        self.description = description
        self.metadata = get_metadata(description)
        
    @property
    def logo_src(self) -> Path:
        if (logo := self.directory / "logo.png").exists():
            return logo
        if (logo := self.directory / "visual-identity" / "logo.png").exists():
            return logo
        if self.description:
            if (match := re.match(r"[!>]\[[^\]]+\]\(([^\).]+\.(?:png|jpe?g|webp))\)", self.description)):
                return self.directory / Path(match.group(1))
        return Path(__file__) / ".." / "assets" / "default_logo.png"
    
    @property
    def project_name(self) -> str:
        return self.directory.name
    
    @property
    def is_contribution(self) -> bool:
        return self.metadata.get("contribution", False)
    
    @property
    def project_state(self) -> str:
        state: str
        # seed: has just an incubator entry (option to only show "will make" or also "not sure")
        # TODO
        # draft: has a folder or is "making" column in incubator
        state = "draft"
        # wip: has a portfoliodb description or a GitHub repo
        if self.description or 


def create_row(p: WebDashRow) -> str:
    return ("<tr>"
        f'<td><img src="{p.logo_src}"/>'
        f'<td>{p.project_name}'
        f'<td>{p.is_contribution}'
        f'<td>{p.progress_state}'
        f'<td>{p.progress_status}'
        f'<td>{p.latest_version}'
        f'<td>{p.latest_published_version}'
        f'<td>{p.made_with}'
        f'<td>{p.tags}'
        f'<td>{p.github_url}'
        f'<td>{p.project_path}'
    )

def checkmark(o: Any) -> Text:
    # return ":white_heavy_check_mark" if o else ":cross_mark:"
    return console.render_str(text="[green]yes[/green]" if o else "[red]no[/red]")


if __name__ == "__main__":
    cli()
