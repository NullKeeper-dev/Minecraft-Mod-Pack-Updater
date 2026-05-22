from pathlib import Path

import requests

BASE_URL = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "MinecraftModUpdater/1.0.0 (github.com/NullKeeper-dev/Minecraft-Mod-Updater)"}


def lookup_by_hash(sha512: str) -> dict | None:
    """
    Primary lookup strategy: identify a mod by the SHA-512 hash of its .jar file.
    This is 100% accurate regardless of filename formatting.
    Returns the version object if found, or None.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/version_files",
            json={"hashes": [sha512], "algorithm": "sha512"},
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if sha512 in data:
                return data[sha512]
    except requests.RequestException:
        pass
    return None


def search_mod(name: str, mc_version: str, loader: str) -> str | None:
    """
    Fallback lookup strategy: search Modrinth by mod name + version + loader.
    Returns the project_id (slug) of the best match, or None.
    """
    try:
        facets = (
            f'[["project_type:mod"],'
            f'["versions:{mc_version}"],'
            f'["categories:{loader}"]]'
        )
        params = {"query": name, "facets": facets, "limit": 1}
        resp = requests.get(
            f"{BASE_URL}/search", params=params, headers=HEADERS, timeout=10
        )
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            if hits:
                return hits[0]["project_id"]
    except requests.RequestException:
        pass
    return None


def get_latest_version(project_id: str, mc_version: str, loader: str) -> tuple:
    """
    Given a project ID, fetch the latest version compatible with mc_version + loader.
    Returns (download_url, filename) or (None, None).
    """
    try:
        params = {
            "game_versions": f'["{mc_version}"]',
            "loaders": f'["{loader}"]',
        }
        resp = requests.get(
            f"{BASE_URL}/project/{project_id}/version",
            params=params,
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            versions = resp.json()
            if versions:
                files = versions[0].get("files", [])
                # Prefer the file marked as primary
                primary = next((f for f in files if f.get("primary")), None)
                if primary is None and files:
                    primary = files[0]
                if primary:
                    return primary["url"], primary["filename"]
    except requests.RequestException:
        pass
    return None, None


def download_file(url: str, dest: Path) -> bool:
    """Stream-download a file from url into dest. Returns True on success."""
    try:
        resp = requests.get(url, stream=True, timeout=60, headers=HEADERS)
        if resp.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
    except requests.RequestException:
        pass
    return False
