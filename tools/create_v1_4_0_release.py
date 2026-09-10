"""Create GitHub Release v1.4.0 with the .exe + .zip assets.

Uploads dist/void-hunter.exe and dist/VoidHunter-v1.4.0-win64.zip
to a new GitHub Release on tag v1.4.0 (BLOQUE 71), with release
notes extracted from docs/changelog/CHANGELOG_v1.x.md.

BLOQUE 71: shape-aware 70% white hit flash (asteroid + MINE + 4 enemy
kinds). BLOQUE 71.2: fix the 'blancuscas' bug (hit_timer stuck white
permanently because decrement was only in MINE-ASTEROID branch).

Idempotent: if the release already exists, fetches it and re-uploads
the assets (overwriting the previous ones). Pattern adapted from
tools/create_v1_3_0_release.py.
"""
import os
import sys
import urllib.request
import urllib.error
import json
import subprocess
from pathlib import Path


REPO = "lerius700-cmyk/Void-Hunter"
TAG = "v1.4.0"
ASSET_EXE = Path(r"D:\AI\void-hunter\dist\void-hunter.exe")
ASSET_ZIP = Path(r"D:\AI\void-hunter\dist\VoidHunter-v1.4.0-win64.zip")
CHANGELOG_PATH = Path(r"D:\AI\void-hunter\docs\changelog\CHANGELOG_v1.x.md")


def get_token() -> str:
    """Read the user's GitHub token. Prefers GITHUB_TOKEN / GH_TOKEN
    env vars. Falls back to git credential store.

    Never prints the token (even masked) — the script's purpose is
    to authenticate, not display credentials.
    """
    env = (
        os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
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
        "No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN env var, "
        "or configure git credential helper for github.com."
    )


def get_release_notes() -> str:
    """Extract the v1.4.0 section from CHANGELOG_v1.x.md."""
    if not CHANGELOG_PATH.exists():
        return f"Release {TAG} — BLOQUE 71 (shape-aware 70% white hit flash + blancuscas bugfix)"
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    out_lines = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## [v1.4.0]"):
            in_section = True
            out_lines.append(line)
            continue
        if in_section and line.startswith("## ") and "[v1.4.0]" not in line:
            break
        if in_section:
            out_lines.append(line)
    body = "\n".join(out_lines).strip()
    return body or f"Release {TAG} — BLOQUE 71"


def http(method, url, headers, body=None, timeout=1200):
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def upload_asset(upload_url_template, asset_path, token, headers):
    """Upload a single asset to the release."""
    if not asset_path.exists():
        print(f"  asset not found, skipping: {asset_path}")
        return False
    upload_url = upload_url_template.split("{")[0]  # strip {?name,label}
    name = asset_path.name
    size_mb = asset_path.stat().st_size / 1024 / 1024
    print(f"  uploading {name} ({size_mb:.1f} MB)...")
    with asset_path.open("rb") as f:
        data = f.read()
    # The Content-Length is required by GitHub for uploads
    upload_headers = {
        **headers,
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(data)),
    }
    sep = "&" if "?" in upload_url else "?"
    status, resp = http(
        "POST", f"{upload_url}{sep}name={urllib.parse.quote(name)}",
        upload_headers, data,
    )
    if status == 201:
        asset = json.loads(resp)
        print(f"  uploaded: {asset['browser_download_url']}")
        return True
    else:
        print(f"  ERROR uploading {name}: {status} {resp[:200]!r}")
        return False


def main():
    import urllib.parse
    token = get_token()
    print(f"Authenticating with GitHub... (token len={len(token)})")

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "void-hunter-release-script",
    }

    print(f"Creating GitHub release for {TAG}...")
    body_json = json.dumps({
        "tag_name": TAG,
        "target_commitish": "master",
        "name": f"VOID HUNTER {TAG} (BLOQUE 71) - Shape-aware 70% hit flash + blancuscas fix",
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
        print(f"  created: {release['html_url']}")
    elif status == 422:
        # Already exists — fetch and update
        status2, resp2 = http(
            "GET", f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}",
            headers,
        )
        if status2 != 200:
            print(f"  ERROR fetching existing release: {status2} {resp2[:200]!r}")
            return 1
        release = json.loads(resp2)
        release_id = release["id"]
        print(f"  release exists: {release['html_url']}")
        # Optionally update the body
        update_json = json.dumps({"body": get_release_notes()}).encode("utf-8")
        s, r = http(
            "PATCH", f"https://api.github.com/repos/{REPO}/releases/{release_id}",
            {**headers, "Content-Type": "application/json"},
            update_json,
        )
        if s == 200:
            print("  release body updated")
        else:
            print(f"  WARNING: could not update body: {s} {r[:200]!r}")
    else:
        print(f"  ERROR creating release: {status} {resp[:500]!r}")
        return 1

    upload_url = release["upload_url"]
    # First, list existing assets and delete the .exe + .zip (so re-upload is clean)
    status, resp = http(
        "GET", f"https://api.github.com/repos/{REPO}/releases/{release['id']}/assets",
        headers,
    )
    if status == 200:
        existing_assets = json.loads(resp)
        for a in existing_assets:
            if a["name"] in ("void-hunter.exe", "VoidHunter-v1.4.0-win64.zip"):
                print(f"  deleting existing asset: {a['name']}")
                http(
                    "DELETE", a["url"],
                    headers,
                )

    # Re-fetch the upload_url (it may have changed after asset deletion)
    status, resp = http(
        "GET", f"https://api.github.com/repos/{REPO}/releases/{release['id']}",
        headers,
    )
    if status == 200:
        release = json.loads(resp)
        upload_url = release["upload_url"]

    ok1 = upload_asset(upload_url, ASSET_EXE, token, headers)
    ok2 = upload_asset(upload_url, ASSET_ZIP, token, headers)
    if ok1 and ok2:
        print(f"\nRelease {TAG} published: {release['html_url']}")
        return 0
    else:
        print(f"\nRelease created but some assets failed: {release['html_url']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
