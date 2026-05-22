import hashlib
import re
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

import modrinth
import updater
from versions import MINECRAFT_VERSIONS

console = Console()

LOADERS = ["fabric", "forge", "neoforge", "quilt"]
LOADER_TOKENS = {"fabric", "forge", "neoforge", "quilt", "neo"}


# ─── Utilities ────────────────────────────────────────────────────────────────

def compute_sha512(file_path: Path) -> str:
    """Compute the SHA-512 digest of a file for hash-based Modrinth lookup."""
    sha512 = hashlib.sha512()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha512.update(chunk)
    return sha512.hexdigest()


def extract_mod_name(filename: str) -> str:
    """
    Fallback: derive a searchable mod name from a .jar filename by stripping
    version numbers, loader tags, and MC version tags.
    Examples:
      'sodium-fabric-0.5.8+mc1.21.jar'  → 'sodium'
      'JourneyMap-1.21-5.10.0-fabric.jar' → 'journeymap'
      'bactromod-3.4.jar'                → 'bactromod'
    """
    parts = [
        token
        for token in re.split(r"[-+_ ]+", Path(filename).stem)
        if token
    ]

    while parts and _is_metadata_token(parts[-1]):
        parts.pop()

    while parts and _is_loader_token(parts[-1]):
        parts.pop()

    while parts and _is_metadata_token(parts[-1]):
        parts.pop()

    cleaned_parts = [token for token in parts if not _is_loader_token(token)]
    return "-".join(cleaned_parts).lower()


def _is_loader_token(token: str) -> bool:
    return token.lower() in LOADER_TOKENS


def _is_metadata_token(token: str) -> bool:
    lowered = token.lower()
    if lowered.startswith("mc") and _looks_like_version(lowered[2:]):
        return True
    return _looks_like_version(lowered)


def _looks_like_version(token: str) -> bool:
    return bool(
        re.fullmatch(r"v?\d+", token, re.IGNORECASE)
        or re.fullmatch(r"v?\d+(?:\.\d+)+(?:[a-z]{1,5}\d*)?", token, re.IGNORECASE)
    )


# ─── UI Helpers ───────────────────────────────────────────────────────────────

def print_banner() -> None:
    version = updater.get_local_version()
    banner_text = Text(justify="center")
    banner_text.append("Minecraft Mod Updater\n", style="bold cyan")
    banner_text.append(
        f"By NullKeeper-dev | Powered by Modrinth | Version {version}",
        style="dim",
    )
    console.print()
    console.print(
        Panel.fit(
            banner_text,
            border_style="cyan",
            padding=(1, 4),
        )
    )


def prompt_folder(label: str, must_exist: bool = True) -> Path:
    """Prompt the user for a directory path with validation."""
    while True:
        raw = Prompt.ask(f"[bold cyan]{label}[/bold cyan]").strip()
        path = Path(raw)
        if must_exist:
            if path.exists() and path.is_dir():
                return path
            console.print("[red][ERROR][/red] Path does not exist or is not a folder. Try again.")
        else:
            if path.exists() and path.is_dir():
                return path
            if not path.exists():
                if Confirm.ask(
                    f"[yellow]Folder [bold]{path}[/bold] does not exist. Create it?[/yellow]",
                    default=True,
                ):
                    path.mkdir(parents=True)
                    console.print(f"[green][OK][/green] Created: {path}")
                    return path
            else:
                console.print("[red][ERROR][/red] Not a valid directory. Try again.")


def prompt_version() -> str:
    """Loop until the user enters a supported Minecraft release version."""
    console.print(
        "\n[dim]Enter the exact release version, for example 1.21.11 or 26.1.2.[/dim]"
    )

    while True:
        version = Prompt.ask("\n[bold cyan]Target Minecraft version[/bold cyan]").strip()
        if version in MINECRAFT_VERSIONS:
            return version
        if version == "26":
            console.print(
                "[red][ERROR][/red] '26' is not a supported Modrinth release tag. "
                "Use an exact release such as 26.1, 26.1.1, or 26.1.2."
            )
            continue
        console.print(f"[red][ERROR][/red] '[bold]{version}[/bold]' is not a recognised version.")


def prompt_loader() -> str:
    """Display mod loader options and loop until the user enters a valid one."""
    console.print("\n[bold cyan]Available loaders[/bold cyan]")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="white")
    for i, loader in enumerate(LOADERS, 1):
        table.add_row(f"{i}.", loader.capitalize())
    console.print(table)

    while True:
        choice = Prompt.ask(
            "\n[bold cyan]Mod loader[/bold cyan] [dim](enter name or number)[/dim]"
        ).strip().lower()

        if choice in LOADERS:
            return choice
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(LOADERS):
                return LOADERS[idx]
        except ValueError:
            pass
        console.print(
            f"[red][ERROR][/red] Invalid choice. Enter a loader name or a number between 1 and {len(LOADERS)}."
        )


def print_step(number: int, title: str, detail: str) -> None:
    console.print(f"\n[bold white]Step {number}[/bold white] [dim]-[/dim] [bold cyan]{title}[/bold cyan]")
    console.print(f"[dim]{detail}[/dim]")


# ─── Core Logic ───────────────────────────────────────────────────────────────

def resolve_mod(jar: Path, mc_version: str, loader: str) -> tuple:
    """
    Attempt to resolve a mod to a downloadable Modrinth version.
    Strategy 1 — SHA-512 hash lookup (precise, works regardless of filename).
    Strategy 2 — Name-parsed search (fallback for mods not yet indexed by hash).
    Returns (project_id, download_url, filename) or (None, None, None).
    """
    # Strategy 1: hash
    sha512 = compute_sha512(jar)
    version_data = modrinth.lookup_by_hash(sha512)
    if version_data:
        project_id = version_data.get("project_id")
        if project_id:
            url, fname = modrinth.get_latest_version(project_id, mc_version, loader)
            if url:
                return project_id, url, fname

    # Strategy 2: name search
    name_guess = extract_mod_name(jar.name)
    project_id = modrinth.search_mod(name_guess, mc_version, loader)
    if project_id:
        url, fname = modrinth.get_latest_version(project_id, mc_version, loader)
        if url:
            return project_id, url, fname

    return None, None, None


def write_log(dest: Path, mc_version: str, loader: str, success: list, failed: list) -> Path:
    """Write a plain-text update report to the destination folder."""
    log_path = dest / "mod_update_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  Minecraft Mod Updater - Update Log\n")
        f.write(f"  Target: MC {mc_version}  |  Loader: {loader.capitalize()}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"SUCCESSFUL ({len(success)}):\n")
        for entry in success:
            f.write(f"    + {entry}\n")

        f.write(f"\nFAILED ({len(failed)}) - not found on Modrinth for {mc_version}/{loader}:\n")
        for entry in failed:
            f.write(f"    - {entry}\n")

        f.write("\n" + "=" * 60 + "\n")
    return log_path


# ─── Main Flow ────────────────────────────────────────────────────────────────

def run() -> None:
    print_banner()

    # Self-update check
    updater.check_for_updates(console)

    # ── Step 1: Source folder ──
    print_step(1, "Source mods folder", "The folder containing your current .jar mods.")
    source_path = prompt_folder("Source folder path", must_exist=True)

    # ── Step 2: Destination folder ──
    print_step(2, "Destination mods folder", "Where the updated mods will be downloaded.")
    dest_path = prompt_folder("Destination folder path", must_exist=False)

    # ── Step 3: Target MC version ──
    print_step(3, "Target Minecraft version", "Enter the release version you want to update to.")
    target_version = prompt_version()

    # ── Step 4: Mod loader ──
    print_step(4, "Mod loader", "Choose the loader that matches the target mod set.")
    loader = prompt_loader()

    # ── Confirm ──
    console.print()
    console.print(
        Panel(
            f"[bold]Source:[/bold]  {source_path}\n"
            f"[bold]Dest:[/bold]    {dest_path}\n"
            f"[bold]Version:[/bold] {target_version}\n"
            f"[bold]Loader:[/bold]  {loader.capitalize()}",
            title="[bold cyan]Review Settings[/bold cyan]",
            border_style="cyan",
        )
    )
    if not Confirm.ask("[bold]Proceed with update?[/bold]", default=True):
        console.print("[yellow][WARN][/yellow] Cancelled.")
        sys.exit(0)

    # ── Gather jars ──
    jar_files = sorted(source_path.glob("*.jar"))
    if not jar_files:
        console.print("[bold red][ERROR][/bold red] No .jar files found in the source folder.")
        sys.exit(1)

    console.print(f"\n[green][OK][/green] Found [bold]{len(jar_files)}[/bold] mod(s). Starting update.\n")

    success_list: list[str] = []
    failed_list: list[str] = []

    # ── Progress loop ──
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("[cyan]Processing mods[/cyan]", total=len(jar_files))

        for jar in jar_files:
            progress.update(task, description=f"[cyan]Processing {jar.name[:50]}[/cyan]")

            _, url, fname = resolve_mod(jar, target_version, loader)

            if url and fname:
                dest_file = dest_path / fname
                ok = modrinth.download_file(url, dest_file)
                if ok:
                    success_list.append(jar.name)
                    progress.update(task, advance=1)
                    continue

            failed_list.append(jar.name)
            progress.update(task, advance=1)

    # ── Summary table ──
    console.print()
    summary = Table(
        title="[bold]Update Summary[/bold]",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        expand=False,
    )
    summary.add_column("Status", style="bold", width=12, no_wrap=True)
    summary.add_column("Source File", style="dim")

    for mod in success_list:
        summary.add_row("[green]OK[/green]", mod)
    for mod in failed_list:
        summary.add_row("[red]FAILED[/red]", mod)

    console.print(summary)
    console.print()
    console.print(
        f"[bold green]Updated: {len(success_list)}[/bold green]  "
        f"[bold red]Failed: {len(failed_list)}[/bold red]"
    )

    # ── Write log ──
    log_path = write_log(dest_path, target_version, loader, success_list, failed_list)
    console.print(f"\n[dim]Log saved to: {log_path}[/dim]")
    console.print("\n[bold cyan]Update complete.[/bold cyan] Press Enter to exit.")
    input()


if __name__ == "__main__":
    run()
