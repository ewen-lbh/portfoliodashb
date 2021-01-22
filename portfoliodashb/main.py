#!/usr/bin/env python

from pathlib import Path
import socketserver
from http.server import BaseHTTPRequestHandler
from typing import Any, Dict, List, NamedTuple, Optional
import os
import subprocess
import re
import github

from rich.table import Column, Table
from rich.text import Text
from typer import Argument, Typer
from semantic_version import Version

from portfoliodashb.config import load_config
from portfoliodashb.console import console
from portfoliodashb.constants import CONFIG_FILEPATH
from portfoliodashb.crawler import crawl
from portfoliodashb.metadata_parser import (
    METADATA_KEYS_WORTH_CHECKING,
    get_metadata,
    has_lang,
    metadata_keys_presence_map,
)
from portfoliodashb import git
from portfoliodashb.progressbar import ProgressBar

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
    subprocess.run(
        (
            editor,
            Path(directory or config.projects_directory)
            / project
            / ".portfoliodb"
            / "description.md",
        )
    )


@cli.command("web")
def webdash(directory: Optional[str] = None, port: int = 8000):
    with open(
        Path(__file__).parent.parent / "dist" / "index.html", "w", encoding="utf-8"
    ) as file:
        file.write(create_html(directory or config.projects_directory))
    subprocess.run(
        ["xdg-open", str(Path(__file__).parent.parent / "dist" / "index.html")]
    )

    class WebdashServer(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/":
                self.send_error(404, "Not Found")
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(
                bytes(create_html(directory or config.projects_directory), "utf-8")
            )

            return

    server = socketserver.TCPServer(("", port), WebdashServer)
    server.serve_forever()


def create_html(directory: str) -> str:
    projects = crawl(Path(directory).expanduser())
    bar = ProgressBar(total=len(projects), width=50)
    NEWLINE = "\n"  # f-string expressions cannot contain backslashes
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
    html = f"""
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
        {NEWLINE.join([ create_row(name, description, bar) for name, description in projects.items() ])}
        <code>{os.getenv("GHTOK")}</code>
    </table>
</body>

</html>"""

    return html

GH = github.Github(os.getenv("GHTOK"))

class WebDashRow:
    directory: Path
    description: str
    metadata: Dict[str, Any]
    repo: Optional[git.Repository]
    ghrepo: Optional[github.Repository.Repository]
    progress_bar: Optional[ProgressBar]

    def __init__(self, directory: Path, description: str, progress_bar: Optional[ProgressBar] = None) -> None:
        self.directory = directory
        self.description = description
        self.ghrepo = None
        self.progress_bar = progress_bar
        self.metadata = {}
        if self.description:
            self.metadata = get_metadata(description)
        try:
            self.repo = git.Repository(self.directory)
        except git.NoRepoHere:
            self.repo = None
        if self.repo and (
            github_remotes := [
                r.removeprefix("https://github.com/").removesuffix("/")
                for r in self.repo.remotes
                if r.startswith("https://github.com/")
            ]
        ):
            try:
                self.status("Loading the Github repo")
                self.ghrepo = GH.get_repo(github_remotes[0])
            except github.GithubException:
                self.ghrepo = None
        
        self.p("__init__", directory)

    def status(self, *args):
        self.progress_bar.text = f"{self.project_name}: {' '.join([str(arg) for arg in args])}" 
    
    def p(self, *args, **kwargs):
        self.progress_bar.print(*args, **kwargs)

    @property
    def logo_src(self) -> Path:
        self.status("Resolving the logo source")
        self.p("logo_src", self.project_name)
        self.p("logo_src", "try_logo.png")
        if (logo := self.directory / "logo.png").exists():
            return logo
        self.p("logo_src", "try_visual_identity")
        if (logo := self.directory / "visual-identity" / "logo.png").exists():
            return logo
        if self.description:
            self.p("logo_src", "try_from_description")
            if (
                match := re.match(
                    r"[!>]\[[^\]]+\]\(([^\).]+\.(?:png|jpe?g|webp))\)", self.description
                )
            ) :
                self.p("logo_src", "found_match", match.group(1))
                return self.directory / Path(match.group(1))
        self.p("logo_src", "use_fallback")
        return Path(__file__) / ".." / "assets" / "default_logo.png"

    @property
    def project_name(self) -> str:
        return self.directory.name

    @property
    def is_contribution(self) -> bool:
        return self.metadata.get("contribution", False)

    @property
    def project_state(self) -> str:
        self.status("Computing project state")
        state: str
        # seed: has just an incubator entry (option to only show "will make" or also "not sure")
        # TODO
        # draft: has a folder or is "making" column in incubator
        state = "draft"
        # wip: has a portfoliodb description or a GitHub repo
        if self.description or (self.repo and self.repo.remotes):
            state = "wip"
        # done: has a finished date or a wip: true in the portfoliodb description
        if self.description and (
            self.metadata.get("finished") or not self.metadata.get("wip", False)
        ):
            state = "done"

        return state

    @property
    def project_progress(self) -> float:
        self.status("Computing project progress")
        self.p("project_progress", self.project_name)
        progress = 0.0
        if self.ghrepo:
            self.p("project_progress", "has_gh")
            readme = str()
            try:
                readme = self.ghrepo.get_readme().content
            except github.GithubException:
                pass
            progress = (
                self._progress_via_milestones(self.ghrepo.get_milestones(state="open"))
                or self._progress_via_issues(self.ghrepo.get_issues())
                or self._progress_via_readme(readme)
                or 0.0
            )
            self.p("project_progress", "with_github", progress)
        if not progress:
            progress = self._progress_via_readme(self.description) or 0.0
        if not progress and (
            markdown_files := [
                f.read_text() for f in self.directory.glob("**/*.{md,mdown,markdown}")
            ]
        ):
            for markdown_file in markdown_files:
                if (progress := self._progress_via_readme(markdown_file)) :
                    self.p("project_progress", "with_local", progress)
                    return progress
        return progress

    def _progress_via_milestones(
        self, milestones: github.PaginatedList
    ) -> Optional[float]:
        self.p("project_progress", "via_milestones")
        if not milestones.totalCount:
            return None
        if milestones.totalCount == 1:
            selected_milestone = milestones[0]
        elif (
            versions_milestones := [
                m for m in milestones if re.match(r"v?(\d+\.){2}\d+", m.title)
            ]
        ) :
            selected_milestone = sorted(
                versions_milestones, key=lambda m: version_sort_key(m.title)
            )[0]
        elif (
            preferred_milestones := [
                m
                for m in milestones
                if m.title in ("Make it public", "Make it public!", "Release")
            ]
        ) :
            selected_milestone = preferred_milestones[0]
        elif milestones.totalCount:
            selected_milestone = milestones[0]
        else:
            return None
        self.p("project_progress", "via_milestones", "selected", selected_milestone)
        self.p("project_progress", "via_milestones", "verdict", selected_milestone.open_issues/(selected_milestone.closed_issues + selected_milestone.open_issues))
        return selected_milestone.open_issues / (
            selected_milestone.closed_issues + selected_milestone.open_issues
        )

    def _progress_via_issues(self, issues: github.PaginatedList) -> Optional[float]:
        self.p("project_progress", "via_issues")
        if not issues.totalCount:
            return None
        self.p("project_progress", "via_issues", "open_issues_count", len([i for i in issues if i.state == "open"]))
        self.p("project_progress", "via_issues", "verdict", len([i for i in issues if i.state == "open"]) / issues.totalCount)
        return len([i for i in issues if i.state == "open"]) / issues.totalCount

    def _progress_via_readme(self, readme: Optional[str]) -> Optional[float]:
        self.p("project_progress", "via_readme")
        done_count = 0
        todo_count = 0
        if not readme:
            return None
        for line in readme.splitlines():
            if line.strip().startswith("- [ ] "):
                self.p("project_progress", "via_readme", "found_todo")
                todo_count += 1
            elif line.strip().startswith("- [x] "):
                self.p("project_progress", "via_readme", "found_done")
                done_count += 1
        if not done_count + todo_count:
            return None
        self.p("project_progress", "via_readme", "verdict", done_count / (todo_count + done_count))
        return done_count / (todo_count + done_count)

    @property
    def latest_version(self) -> Optional[str]:
        self.status("Computing latest version number")
        self.p("latest_version", self.project_name)
        if not self.repo:
            return None
        versions = [tag for tag in self.repo.tags if re.match(r"v?\d+\.\d+\.\d+", tag)]
        self.p("latest_version", "got_tags", versions)
        if not versions:
            return None
        return list(reversed(sorted(versions, key=version_sort_key)))[0]

    @property
    def latest_published_version(self) -> Optional[str]:
        self.status("Computing latest published version number")
        self.p("latest_published_version", self.project_name)
        if not self.ghrepo:
            return None
        versions = [
            tag
            for tag in self.ghrepo.get_tags()
            if re.match(r"v?\d+\.\d+\.\d+", tag.name)
        ]
        self.p("latest_published_version", "got_tags", versions)
        if not versions:
            return None
        return list(
            reversed(sorted(versions, key=lambda tag: version_sort_key(tag.name)))
        )[0].name

    @property
    def made_with(self) -> Optional[str]:
        return self.metadata.get("made with")

    @property
    def tags(self) -> Optional[str]:
        return self.metadata.get("tags")

    @property
    def github_url(self) -> Optional[str]:
        if not self.ghrepo:
            return None
        return self.ghrepo.url

    @property
    def project_path(self) -> Optional[str]:
        return str(self.directory)


def version_sort_key(version: str) -> list[int, int, int]:
    return Version(version.strip("v"))


def create_row(name: str, description: Optional[str], bar: ProgressBar) -> str:
    bar.text = f"{name}: "
    bar.print("create_row", name)
    p = WebDashRow(Path("~/projects").expanduser() / name, description, progress_bar=bar)
    bar.advance()
    return (
        "<tr>"
        f'<td><img src="{p.logo_src}"/>'
        f"<td>{p.project_name}"
        f"<td>{p.is_contribution}"
        f"<td>{p.project_state}"
        f"<td>{p.project_progress}"
        f'<td>{p.latest_version or ""}'
        f'<td>{p.latest_published_version or ""}'
        f'<td>{", ".join(p.made_with or [])}'
        f'<td>{", ".join(p.tags or [])}'
        f'<td>{p.github_url or ""}'
        f"<td>{p.project_path}"
    )


def checkmark(o: Any) -> Text:
    # return ":white_heavy_check_mark" if o else ":cross_mark:"
    return console.render_str(text="[green]yes[/green]" if o else "[red]no[/red]")


if __name__ == "__main__":
    cli()
