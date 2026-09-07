"""Create GitHub Release v1.2.6 with the .exe asset.

Uploads dist/void-hunter/void-hunter.exe to a new GitHub Release on
tag v1.2.6 (BLOQUE 58.next), with release notes extracted from
docs/changelog/CHANGELOG_v1.x.md.

BLOQUE 58.next:
- COMPOSED slot offset preservation (no stacked ships)
- minimal background redesign (1 main + 0-1 companion + 30 stars)
- 4275-pattern COMPOSED pool + ProceduralWaveManager
- spawn_interval 4.0s -> 2.0s
- MAX_ENEMIES_ON_SCREEN 12 -> 24
- leader HP scaling 3-5 hits via _leader_hits_at_wave

Idempotent: if the release already exists, fetches it and re-uploads
the asset (overwriting the previous one). Pattern adapted from
tools/create_v1_1_6_release.py.
"""
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import json
import subprocess
from pathlib import Path


REPO = "lerius700-cmyk/Void-Hunter"
TAG = "v1.2.6"
ASSET_PATH = Path(r"D:\AI\void-hunter\dist\void-hunter\void-hunter.exe")
CHANGELOG_PATH = Path(r"D:\AI\void-hunter\docs\changelog\CHANGELOG_v1.x.md")


def get_token() -> str:
    """Read the user's GitHub token. Prefers GITHUB_TOKEN / GH_TOKEN
    env vars. Also accepts STELLAR_HORIZON_TOKEN (user's local
    convention). Falls back to git credential store.

    Never prints the token (even masked) — the script's purpose is
    to authenticate, not display credentials.
    """
    env = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("STELLAR_HORIZON_TOKEN")
    )
    if env:
        return env.strip()
    try:
        out = subprocess.check_output(
            ["git", "credential", "fill"],
            input=b"protocol=https\nhost=github.com\n",
            cwd=str(Path(__file__).resolve().parent.parent),
        ).decode("utf-8")
        for line in out.splitlines():
            if line.startswith("password="):
                return line[len("password="):].strip()
    except Exception:
        pass
    raise RuntimeError(
        "No GitHub token found. Set GITHUB_TOKEN, GH_TOKEN, or "
        "STELLAR_HORIZON_TOKEN env var, or configure git credential "
        "helper for github.com."
    )


def get_release_notes() -> str:
    """Extract the v1.2.6 / BLOQUE 58.next section from CHANGELOG_v1.x.md."""
    if not CHANGELOG_PATH.exists():
        return f"Release {TAG} — BLOQUE 58.next (roguelike density + leader HP)"
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    out_lines = []
    in_section = False
    for line in text.splitlines():
        if "v1.2.6" in line or "BLOQUE 58.next" in line and "roguelike" in line:
            in_section = True
            out_lines.append(line)
            continue
        if in_section and line.startswith("##") and "v1.2.6" not in line and "BLOQUE 58.next" not in line:
            break
        if in_section:
            out_lines.append(line)
    body = "\n".join(out_lines).strip()
    return body or f"Release {TAG} — BLOQUE 58.next"


def http(method, url, headers, body=None, timeout=1200):
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    token = get_token()
    print(f"Authenticating with GitHub... (token len={len(token)})")

    print("Creating GitHub release...")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "void-hunter-release-script",
    }
    body_json = json.dumps({
        "tag_name": TAG,
        "target_commitish": "master",
        "name": f"VOID HUNTER {TAG} (BLOQUE 58.next) — roguelike density + leader HP",
        "body": get_release_notes(),
        "draft": False,
        "prerelease": False,
    }).encode("utf-8")
    status, resp = http(
        "POST", f"https://api.github.com/repos/{REPO}/releases",
        {**headers, "Content-Type": "application/json"},
        body_json,
    )
    if status == 201:
        release = json.loads(resp)
        upload_url = release["upload_url"]
        release_url = release["html_url"]
        print(f"  created release: {release_url}")
    elif status == 422:
        status2, resp2 = http(
            "GET", f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
            headers,
        )
        if status2 != 200:
            print(f"  ERROR fetching existing release: {status2} {resp2!r}")
            return 1
        release = json.loads(resp2)
        upload_url = release["upload_url"]
        release_url = release["html_url"]
        print(f"  release already exists: {release_url}")
    else:
        print(f"  ERROR creating release: {status} {resp!r}")
        return 1

    # Delete existing asset with the same name (GitHub rejects duplicates)
    status, resp = http(
        "GET", f"https://api.github.com/repos/{REPO}/releases/{release['id']}/assets",
        headers,
    )
    if status == 200:
        for asset in json.loads(resp):
            if asset["name"] == ASSET_PATH.name:
                print(f"  deleting existing asset {asset['name']}...")
                http(
                    "DELETE",
                    f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}",
                    headers,
                )

    if not ASSET_PATH.exists():
        print(f"ERROR: asset not found: {ASSET_PATH}")
        return 1
    asset_size = ASSET_PATH.stat().st_size
    asset_name = ASSET_PATH.name
    print(f"Uploading {asset_name} ({asset_size} bytes, {asset_size // (1024*1024)} MB)...")
    upload_url_clean = upload_url.split("{")[0]
    asset_url = f"{upload_url_clean}?name={urllib.parse.quote(asset_name)}"
    asset_headers = {
        **headers,
        "Content-Type": "application/octet-stream",
        "Content-Length": str(asset_size),
    }
    with open(ASSET_PATH, "rb") as f:
        data = f.read()
    status, resp = http("POST", asset_url, asset_headers, data, timeout=1200)
    if status == 201:
        asset = json.loads(resp)
        print(f"  uploaded asset: {asset['browser_download_url']}")
    else:
        print(f"  ERROR uploading asset: {status} {resp[:500]!r}")
        return 1

    print()
    print("=== DONE ===")
    print(f"Release: {release_url}")
    print(f"Asset:   {asset['browser_download_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
