"""Find and download verified installers from the project's GitHub releases."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request


VERSION = "2.6.3"
REPO = "abd-azzam/Claim-Viewer"
RELEASE = f"https://api.github.com/repos/{REPO}/releases/latest"


def _version(text):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", text)
    return tuple(map(int, match.groups())) if match else ()


def _open(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "ClaimViewer", "Accept": "application/json"}),
        timeout=30,
    )


def download_latest(directory):
    with _open(RELEASE) as response:
        release = json.loads(response.read(2 * 1024 * 1024))
    tag = release.get("tag_name", "")
    version = _version(tag)
    if release.get("draft") or release.get("prerelease") or not version:
        raise ValueError("GitHub did not return a stable Claim Viewer version.")
    if version <= _version(VERSION):
        return {"ok": True, "message": f"Claim Viewer {VERSION} is up to date."}

    label = ".".join(map(str, version))
    name = f"ClaimViewer-Setup-{label}.exe"
    asset = next((a for a in release.get("assets", []) if a.get("name") == name), {})
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    digest = re.fullmatch(r"sha256:([0-9a-f]{64})", asset.get("digest") or "")
    size = asset.get("size")
    if asset.get("browser_download_url") != url or not digest or type(size) is not int or not 0 < size <= 250 * 1024 * 1024:
        raise ValueError(f"Claim Viewer {label} is available, but GitHub has no verifiable Windows installer for it yet.")

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    result = {"ok": True, "version": label, "message": f"Claim Viewer {label} downloaded. Open the update folder to install it."}
    if target.is_file() and target.stat().st_size == size:
        with target.open("rb") as existing:
            if hashlib.file_digest(existing, "sha256").hexdigest() == digest[1]:
                return result

    pending = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".part", delete=False) as output:
            pending = Path(output.name)
            checksum = hashlib.sha256()
            total = 0
            with _open(url) as response:
                while chunk := response.read(256 * 1024):
                    total += len(chunk)
                    if total > size:
                        raise ValueError("The installer is larger than GitHub reported.")
                    checksum.update(chunk)
                    output.write(chunk)
        if total != size or checksum.hexdigest() != digest[1]:
            raise ValueError("The installer did not match the GitHub checksum. Try checking again.")
        os.replace(pending, target)
        return result
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)
