from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import urlparse

import requests
from rich.console import Console
from rich.prompt import Confirm
from rich.text import Text

GITHUB_REPO = "NullKeeper-dev/Minecraft-Mod-Updater"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
REQUEST_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "MinecraftModUpdater/1.0.0 (github.com/NullKeeper-dev/Minecraft-Mod-Updater)",
}
VERSION_FILENAME = "version.txt"
PREFERRED_RELEASE_SUFFIXES = (".zip", ".rar", ".7z", ".exe")


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_version_file() -> Path:
    return get_app_dir() / VERSION_FILENAME


def get_embedded_version_file() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / VERSION_FILENAME
    return Path(__file__).resolve().parent / VERSION_FILENAME


def get_local_version() -> str:
    """Read the local version, preferring an external file over the bundled one."""
    for version_file in (get_version_file(), get_embedded_version_file()):
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


def get_latest_release() -> tuple:
    """
    Query GitHub API for the latest release.
    Returns (version_tag, download_url) or (None, None) on failure.
    """
    try:
        resp = requests.get(
            RELEASES_URL,
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            tag = data.get("tag_name", "").lstrip("v")
            return tag, _select_release_download_url(data)
    except requests.RequestException:
        pass
    return None, None


def _version_tuple(ver: str) -> tuple:
    try:
        return tuple(int(x) for x in ver.strip().split("."))
    except ValueError:
        return (0,)


def check_for_updates(console: Console) -> None:
    """
    Compare local version to the latest GitHub release.
    If a newer release is available, prompt the user to update.
    """
    console.print("\n[dim]Checking for updates...[/dim]")
    local_ver = get_local_version()
    remote_ver, download_url = get_latest_release()

    if remote_ver is None or not download_url:
        console.print("[yellow][WARN][/yellow] Could not reach GitHub; skipping update check.")
        return

    if _version_tuple(remote_ver) > _version_tuple(local_ver):
        console.print(
            Text.assemble(
                ("Update available. ", "bold yellow"),
                ("Current: ", ""),
                (f"v{local_ver}", "red"),
                ("  ->  Latest: ", ""),
                (f"v{remote_ver}", "green"),
            )
        )
        if Confirm.ask("[bold]Download and install the update now?[/bold]", default=False):
            _apply_update(console, download_url, remote_ver)
        else:
            console.print("[dim]Skipping update; continuing with current version.[/dim]")
    else:
        console.print(
            Text.assemble(
                ("[OK] ", "green"),
                ("Up to date ", ""),
                (f"(v{local_ver})", "dim"),
            )
        )


def _apply_update(console: Console, url: str, new_version: str) -> None:
    """Download the latest release package and apply it next to the running app."""
    console.print("[cyan]Downloading update...[/cyan]")
    tmp_path: Path | None = None
    staging_dir: Path | None = None
    try:
        suffix = (Path(urlparse(url).path).suffix or ".tmp").lower()
        resp = requests.get(url, stream=True, timeout=60, headers=REQUEST_HEADERS)
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in resp.iter_content(8192):
                if chunk:
                    tmp.write(chunk)
            tmp_path = Path(tmp.name)

        extract_dir = get_app_dir()
        if _is_archive_package(tmp_path):
            if getattr(sys, "frozen", False):
                staging_dir = Path(tempfile.mkdtemp(prefix="mmu-update-"))
                _extract_release_archive(tmp_path, staging_dir)
                (staging_dir / VERSION_FILENAME).write_text(f"{new_version}\n", encoding="utf-8")
                _stage_directory_update(staging_dir, extract_dir)
                staging_dir = None
            else:
                _extract_release_archive(tmp_path, extract_dir)
                get_version_file().write_text(f"{new_version}\n", encoding="utf-8")
        elif _is_executable_package(tmp_path):
            _stage_executable_update(tmp_path, extract_dir)
            tmp_path = None
            get_version_file().write_text(f"{new_version}\n", encoding="utf-8")
        else:
            raise ValueError("Release asset is not a supported archive or executable package.")

        console.print(
            f"[bold green][OK] Updated to v{new_version}.[/bold green] "
            "[dim]Please restart the application.[/dim]"
        )
        sys.exit(0)

    except Exception as exc:
        console.print(f"[bold red][ERROR] Update failed:[/bold red] {exc}")
        console.print("[dim]Continuing with current version.[/dim]")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        if staging_dir and staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)


def _select_release_download_url(release_data: dict) -> str | None:
    assets = release_data.get("assets", [])
    for suffix in PREFERRED_RELEASE_SUFFIXES:
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(suffix):
                return asset.get("browser_download_url")

    if assets:
        return assets[0].get("browser_download_url")
    return release_data.get("zipball_url")


def _is_archive_package(download_path: Path) -> bool:
    return zipfile.is_zipfile(download_path) or download_path.suffix.lower() in {".rar", ".7z"}


def _extract_release_archive(archive_path: Path, extract_dir: Path) -> None:
    if zipfile.is_zipfile(archive_path):
        _extract_zip_archive(archive_path, extract_dir)
        return
    _extract_external_archive(archive_path, extract_dir)


def _extract_zip_archive(archive_path: Path, extract_dir: Path) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        files = [member for member in archive.infolist() if not member.is_dir()]
        root_prefix = _common_root_prefix(files)

        for member in files:
            relative_path = _normalized_member_path(member.filename, root_prefix)
            target_path = (extract_dir / relative_path).resolve()

            if extract_dir.resolve() not in target_path.parents and target_path != extract_dir.resolve():
                raise ValueError(f"Unsafe archive path: {member.filename}")

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)


def _extract_external_archive(archive_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)

    commands = [
        ["tar", "-xf", str(archive_path), "-C", str(extract_dir)],
        ["7z", "x", str(archive_path), f"-o{extract_dir}", "-y"],
    ]
    errors: list[str] = []

    for command in commands:
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            return
        except FileNotFoundError:
            errors.append(f"{command[0]} not found")
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() or exc.stdout.strip() or f"exit code {exc.returncode}"
            errors.append(f"{command[0]} failed: {message}")

    raise ValueError("Could not extract release archive. " + " | ".join(errors))


def _common_root_prefix(members: list[zipfile.ZipInfo]) -> str | None:
    roots = set()
    for member in members:
        parts = PurePosixPath(member.filename).parts
        if len(parts) < 2:
            return None
        roots.add(parts[0])

    if len(roots) == 1:
        return roots.pop()
    return None


def _normalized_member_path(filename: str, root_prefix: str | None) -> Path:
    parts = list(PurePosixPath(filename).parts)
    if root_prefix and parts and parts[0] == root_prefix:
        parts = parts[1:]

    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Unsafe archive member: {filename}")

    return Path(*parts)


def _is_executable_package(download_path: Path) -> bool:
    if download_path.suffix.lower() == ".exe":
        return True

    with download_path.open("rb") as handle:
        return handle.read(2) == b"MZ"


def _stage_executable_update(download_path: Path, app_dir: Path) -> None:
    if not getattr(sys, "frozen", False):
        raise ValueError("Executable updates are only supported in the packaged .exe build.")

    current_exe = Path(sys.executable).resolve()
    staged_exe = app_dir / f"{current_exe.stem}.update.exe"
    if staged_exe.exists():
        staged_exe.unlink()

    download_path.replace(staged_exe)

    batch_path = app_dir / "_apply_update.bat"
    batch_path.write_text(
        "\n".join(
            [
                "@echo off",
                ":retry",
                f'move /Y "{staged_exe}" "{current_exe}" >nul',
                "if errorlevel 1 (",
                "  timeout /t 1 /nobreak >nul",
                "  goto retry",
                ")",
                f'start "" "{current_exe}"',
                'del "%~f0"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        ["cmd", "/c", str(batch_path)],
        creationflags=creation_flags,
    )


def _stage_directory_update(staging_dir: Path, app_dir: Path) -> None:
    if not getattr(sys, "frozen", False):
        raise ValueError("Directory updates are only supported in the packaged .exe build.")

    current_exe = Path(sys.executable).resolve()
    batch_path = app_dir / "_apply_update.bat"
    batch_path.write_text(
        "\n".join(
            [
                "@echo off",
                ":retry",
                f'xcopy /E /I /Y "{staging_dir}\\*" "{app_dir}\\" >nul',
                "if errorlevel 1 (",
                "  timeout /t 1 /nobreak >nul",
                "  goto retry",
                ")",
                f'start "" "{current_exe}"',
                f'rmdir /s /q "{staging_dir}"',
                'del "%~f0"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        ["cmd", "/c", str(batch_path)],
        creationflags=creation_flags,
    )
