# Minecraft Mod Updater

Windows console application that migrates a Minecraft mod folder to a new game
version by identifying existing mods with SHA-512 hashes, resolving updated
files from Modrinth, and downloading the latest compatible jars into a target
folder.

Created by NullKeeper-dev.

## Project Overview

- Language: Python 3.11+
- Platform: Windows
- Packaging target: standalone `.exe` via PyInstaller
- UI: Rich-powered color console

## Feature Summary

- Rich banner, prompts, progress bar, panels, and summary tables
- Validated source and destination folder prompts
- Auto-create destination directory on confirmation
- Minecraft version selection by direct validated input against a static release set
- Loader selection for Fabric, Forge, NeoForge, and Quilt
- Hash-first mod identification with name-search fallback
- Sequential download with visible progress
- Summary table and `mod_update_log.txt` output
- GitHub release update check on launch

## Getting Started

### Download the Latest Release

If you just want to use the software, download a prebuilt release instead of
running it from source.

1. Open the releases page:

```text
https://github.com/NullKeeper-dev/Minecraft-Mod-Updater/releases
```

2. Download the latest release package or `.exe`
3. Extract the archive if needed
4. Run `MinecraftModUpdater.exe`

### Run from Source

If you want to use the software without building an `.exe`, clone the repo and
run it directly with Python.

1. Clone the repository:

```bash
git clone https://github.com/NullKeeper-dev/Minecraft-Mod-Updater.git
cd Minecraft-Mod-Updater
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

4. Start the updater:

```bash
python main.py
```

Requirements:

- Windows
- Python 3.11 or newer
- Internet connection for Modrinth and GitHub update checks

### Build the Executable

If you want a standalone Windows `.exe`, build it with PyInstaller from the
repository root.

1. Install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

2. Install PyInstaller:

```bash
python -m pip install pyinstaller
```

3. Build the executable:

```bash
pyinstaller --onefile --console --name "MinecraftModUpdater" --add-data "version.txt;." main.py
```

Build output:

- The executable will be created at `dist\MinecraftModUpdater.exe`
- `version.txt` is bundled inside the onefile executable by the `--add-data "version.txt;."` argument
- You should not expect a separate `dist\version.txt` file when using `--onefile`
- After a self-update, the app may write a new `version.txt` next to the `.exe`

Optional clean rebuild:

```bash
rmdir /s /q build
rmdir /s /q dist
del MinecraftModUpdater.spec
```

## Output Files

`mod_update_log.txt` is written into the destination folder after processing.
It contains:

- Target Minecraft version
- Selected loader
- Successful source filenames
- Failed source filenames

## Future Enhancements

- CurseForge fallback
- Parallel downloads
- Snapshot version support
- Saved config file
- Ignore list for private or local mods
- Optional GUI wrapper
- Batch hash lookups
- macOS and Linux support
