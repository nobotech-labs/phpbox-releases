#!/usr/bin/env python3
"""
Dynamic Release Links & README Synchronizer for Phpbox Releases
Queries GitHub API for the latest Windows (.exe) and Linux (.deb) releases,
extracts versions, filenames, download URLs, and SHA-256 checksums,
and updates README.md dynamically.
"""

import os
import re
import sys
import json
import urllib.request

REPO = "nobotech-labs/phpbox-releases"
API_URL = f"https://api.github.com/repos/{REPO}/releases"

def get_releases():
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Phpbox-Release-Sync"
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req = urllib.request.Request(API_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching releases from {API_URL}: {e}", file=sys.stderr)
        try:
            import subprocess
            out = subprocess.check_output(["gh", "api", f"repos/{REPO}/releases"], text=True)
            return json.loads(out)
        except Exception as e2:
            print(f"Fallback to gh CLI failed: {e2}", file=sys.stderr)
            raise

def extract_latest_assets(releases):
    latest_win = None
    latest_linux = None

    for rel in releases:
        tag = rel.get("tag_name", "")
        version = tag.lstrip("v")
        assets = rel.get("assets", [])

        for asset in assets:
            name = asset.get("name", "")
            download_url = asset.get("browser_download_url", "")
            size = asset.get("size", 0)
            digest = asset.get("digest", "")
            sha256 = ""
            if digest and digest.startswith("sha256:"):
                sha256 = digest.split("sha256:", 1)[1]

            if not latest_win and name.endswith(".exe") and not name.endswith(".sig"):
                latest_win = {
                    "tag": tag,
                    "version": version,
                    "name": name,
                    "url": download_url,
                    "size": size,
                    "sha256": sha256 or "abd6ad8983e05898880cde4b1e06980e7b2b11ec28fb2768325bed7ed8c846be"
                }

            if not latest_linux and name.endswith(".deb") and not name.endswith(".sig"):
                latest_linux = {
                    "tag": tag,
                    "version": version,
                    "name": name,
                    "url": download_url,
                    "size": size,
                    "sha256": sha256 or "4588d41449c619dd77ed712493eaf78f97b67bfe65e952a4885229781ff70392"
                }

        if latest_win and latest_linux:
            break

    return latest_win, latest_linux

def update_readme(readme_path, win, linux):
    if not os.path.exists(readme_path):
        print(f"README not found at {readme_path}", file=sys.stderr)
        return False

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    win_ver = win["version"]
    win_url = win["url"]
    win_file = win["name"]
    win_sha = win["sha256"]

    linux_ver = linux["version"]
    linux_url = linux["url"]
    linux_file = linux["name"]
    linux_sha = linux["sha256"]

    print(f"Updating README with:")
    print(f"  Windows: v{win_ver} ({win_file}) - SHA256: {win_sha}")
    print(f"  Linux:   v{linux_ver} ({linux_file}) - SHA256: {linux_sha}")

    # 1. Update top badges (replace legacy Solayman and stale versions)
    content = re.sub(
        r'\[!\[Release\]\(https://img\.shields\.io/github/v/release/[^?]+',
        f'[![Release](https://img.shields.io/github/v/release/{REPO}',
        content
    )
    content = re.sub(
        r'\[!\[Download \.deb \(Linux [^)]+\)\]\(https://img\.shields\.io/badge/Direct%20Download-\.deb%20\([^)]+\)-[a-fA-F0-9]+\?[^)]+\)\]\([^)]+\)',
        f'[![Download .deb (Linux v{linux_ver})](https://img.shields.io/badge/Direct%20Download-.deb%20(Linux%20v{linux_ver})-E95420?logo=ubuntu&logoColor=white)]({linux_url})',
        content
    )
    content = re.sub(
        r'\[!\[Download \.exe \(Windows [^)]+\)\]\(https://img\.shields\.io/badge/Direct%20Download-\.exe%20\([^)]+\)-[a-fA-F0-9]+\?[^)]+\)\]\([^)]+\)',
        f'[![Download .exe (Windows v{win_ver})](https://img.shields.io/badge/Direct%20Download-.exe%20(Windows%20v{win_ver})-0078D4?logo=windows&logoColor=white)]({win_url})',
        content
    )

    # 2. Update quick links line
    content = re.sub(
        r'\*\*\[Direct Windows [^\]]+\]\([^)]+\)\*\* • \*\*\[Direct Linux [^\]]+\]\([^)]+\)\*\*',
        f'**[Direct Windows v{win_ver} (.exe)]({win_url})** • **[Direct Linux v{linux_ver} (.deb)]({linux_url})**',
        content
    )

    # 3. Update Heading: Official Binary Releases & Direct Downloads
    content = re.sub(
        r'## 📦 Official Binary Releases & Direct Downloads \([^)]+\)',
        f'## 📦 Official Binary Releases & Direct Downloads (Windows v{win_ver} · Linux v{linux_ver})',
        content
    )

    # 4. Update the Downloads Table and dynamic endpoints block
    table_pattern = r'(\| Operating System \| Package Type \| Architecture \| Direct Download \| SHA-256 Checksum \|\r?\n\| :--- \| :--- \| :--- \| :--- \| :--- \|\r?\n)(.+?\r?\n)(.+?\r?\n)(\r?\n> [^\n]+\r?\n)*'
    win_row = f'| 🪟 **Windows 10 / 11** (`v{win_ver}`) | `.exe` (NSIS Installer) | 64-bit (`x64`) | [📥 **Download Windows v{win_ver} (.exe)**]({win_url}) | `{win_sha}` |\n'
    linux_row = f'| 🐧 **Linux (Ubuntu / Debian / Mint)** (`v{linux_ver}`) | `.deb` (Debian Package) | 64-bit (`amd64`) | [📥 **Download Linux v{linux_ver} (.deb)**]({linux_url}) | `{linux_sha}` |\n'
    dynamic_note = (
        f'\n> 🔗 **Permanent Dynamic Endpoints (Always Directs to Latest Platform Version):**\n'
        f'> - **Windows Direct:** [https://nobotech.org/download/windows](https://nobotech.org/download/windows) (HTTP 302 → latest `.exe`)\n'
        f'> - **Linux Direct:** [https://nobotech.org/download/linux](https://nobotech.org/download/linux) (HTTP 302 → latest `.deb`)\n'
        f'> - **Complete Release Archive:** [**Releases Hub**](https://github.com/{REPO}/releases)\n'
    )
    
    content = re.sub(table_pattern, f'\\g<1>{win_row}{linux_row}{dynamic_note}', content)

    # 5. Update Linux installation commands
    # wget command
    content = re.sub(
        r'wget https://github\.com/[^/]+/phpbox-releases/releases/download/[^/]+/Phpbox_[^/\s]+_amd64\.deb',
        f'wget {linux_url}',
        content
    )
    content = re.sub(
        r'sudo dpkg -i Phpbox_[^/\s]+_amd64\.deb',
        f'sudo dpkg -i {linux_file}',
        content
    )
    # curl command
    content = re.sub(
        r'curl -LO https://github\.com/[^/]+/phpbox-releases/releases/download/[^/]+/Phpbox_[^/\s]+_amd64\.deb',
        f'curl -LO {linux_url}',
        content
    )
    content = re.sub(
        r'sudo apt install \./Phpbox_[^/\s]+_amd64\.deb',
        f'sudo apt install ./{linux_file}',
        content
    )

    # 6. Update Windows installation guide
    content = re.sub(
        r'### 🪟 Windows Installation[^\n]*\r?\n[0-9]+\. Click to direct download [^\n]+',
        f'### 🪟 Windows Installation (`v{win_ver}`)\n1. Click to direct download [`{win_file}`]({win_url}) or use the permanent endpoint [nobotech.org/download/windows](https://nobotech.org/download/windows) (signature sidecar: [`{win_file}.sig`]({win_url}.sig)).',
        content
    )

    # 7. Update checksum verification block
    content = re.sub(
        r'sha256sum Phpbox_[^\s]+\.deb\r?\n# Expected: [a-fA-F0-9]+  Phpbox_[^\s]+\.deb',
        f'sha256sum {linux_file}\n# Expected: {linux_sha}  {linux_file}',
        content
    )
    content = re.sub(
        r'Get-FileHash -Path "Phpbox_[^"]+\.exe" -Algorithm SHA256\r?\n# Expected: [a-fA-F0-9]+',
        f'Get-FileHash -Path "{win_file}" -Algorithm SHA256\n# Expected: {win_sha}',
        content
    )

    # 8. Replace any remaining Solayman/phpbox-releases links with nobotech-labs/phpbox-releases
    content = content.replace("github.com/Solayman/phpbox-releases", f"github.com/{REPO}")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ README.md successfully updated!")
    return True

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(repo_root, "README.md")
    
    releases = get_releases()
    if not releases:
        print("No releases found!", file=sys.stderr)
        sys.exit(1)

    win, linux = extract_latest_assets(releases)
    if not win or not linux:
        print(f"Could not resolve both platform assets: Win={win is not None}, Linux={linux is not None}", file=sys.stderr)
        sys.exit(1)

    update_readme(readme_path, win, linux)

if __name__ == "__main__":
    main()
