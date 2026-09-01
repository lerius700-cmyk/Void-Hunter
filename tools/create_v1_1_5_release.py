"""Create GitHub Release v1.1.5 with the .zip asset.

Uploads release/VoidHunter-v1.1.5-win64.zip to a new GitHub Release
on tag v1.1.5, with release notes extracted from CHANGELOG.md.

Idempotent: if the release already exists, fetches it and re-uploads
the asset (overwriting the previous one).
"""
import os
import sys
import urllib.request
import urllib.error
import json
import subprocess
from pathlib import Path


REPO = "lerius700-cmyk/Void-Hunter"
TAG = "v1.1.5"
ZIP_PATH = Path(r"D:\AI\void-hunter\release\VoidHunter-v1.1.5-win64.zip")
CHANGELOG_PATH = Path(r"D:\AI\void-hunter\CHANGELOG.md")


def get_token() -> str:
    """Read the user's GitHub token. Prefers GITHUB_TOKEN env var.

    Order:
      1. $GITHUB_TOKEN or $GH_TOKEN env var (intentional choice)
      2. git credential store (fallback for old workflows)

    The env var is preferred so the user's explicit choice wins over
    any stale credential that might be in the git credential store
    from a previous session.
    """
    env = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
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
        "No GitHub token found. Set GITHUB_TOKEN env var or "
        "configure git credential helper for github.com."
    )


def get_release_notes() -> str:
    """Extract the [v1.1.5] section from CHANGELOG.md."""
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    in_section = False
    out_lines = []
    for line in text.splitlines():
        if line.startswith(f"## [{TAG}]"):
            in_section = True
            continue
        if in_section and line.startswith("## ["):
            break
        if in_section:
            out_lines.append(line)
    body = "\n".join(out_lines).strip()
    return body or f"Release {TAG}"


def http(method, url, headers, body=None, timeout=600):
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    token = get_token()
    # Don't print the token (even masked) — the script's purpose is
    # to authenticate, not display credentials. Length is logged
    # separately for sanity check that the token loaded correctly.
    print(f"Authenticating with GitHub... (token len={len(token)})")
    token_len = len(token)
    del token_len  # noqa: F841 (kept for future logging hooks)"

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
        "name": f"VOID HUNTER {TAG}",
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
            if asset["name"] == ZIP_PATH.name:
                print(f"  deleting existing asset {asset['name']}...")
                http(
                    "DELETE",
                    f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}",
                    headers,
                )

    if not ZIP_PATH.exists():
        print(f"ERROR: zip not found: {ZIP_PATH}")
        return 1
    zip_size = ZIP_PATH.stat().st_size
    zip_name = ZIP_PATH.name
    print(f"Uploading {zip_name} ({zip_size} bytes, {zip_size // (1024*1024)} MB)...")
    upload_url_clean = upload_url.split("{")[0]
    asset_url = f"{upload_url_clean}?name={urllib.parse.quote(zip_name)}"
    asset_headers = {
        **headers,
        "Content-Type": "application/zip",
        "Content-Length": str(zip_size),
    }
    with open(ZIP_PATH, "rb") as f:
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
    import urllib.parse
    sys.exit(main())
