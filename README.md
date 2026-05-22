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

Primary workflow:

1. Read the user's current mods folder.
2. Identify each `.jar` with a SHA-512 hash lookup on Modrinth.
3. Fall back to parsed-name search when hash lookup fails.
4. Fetch the latest compatible version for the chosen Minecraft version and
   loader.
5. Download resolved jars into a destination folder.
6. Write a plain-text success/failure log.

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

## Build and Packaging

Install:

```bash
pip install -r requirements.txt
```

Development run:

```bash
python main.py
```

PyInstaller build:

```bash
pyinstaller --onefile --console --name "MinecraftModUpdater" --add-data "version.txt;." main.py
```

## Output Files

`mod_update_log.txt` is written into the destination folder after processing.
It contains:

- Target Minecraft version
- Selected loader
- Successful source filenames
- Failed source filenames

## Version Support

The bundled release-version set is aligned with current Modrinth release tags.
As of May 22, 2026, it includes releases through `1.21.11` and `26.1.2`.

The interface does not print a full version list. Users enter the exact target
release directly, such as `1.21.11` or `26.1.2`, and the app validates that
input against the bundled set.

## Future Enhancements

- CurseForge fallback
- Parallel downloads
- Snapshot version support
- Saved config file
- Ignore list for private or local mods
- Optional GUI wrapper
- Batch hash lookups
- macOS and Linux support
