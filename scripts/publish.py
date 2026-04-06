# /// script
# requires-python = ">=3.11"
# dependencies = ["toml"]
# ///

"""Publish unicode workspace members to the Cangjie central repository and create GitHub releases."""

import hashlib
import json
import subprocess
import sys
import tarfile
import time
from io import BytesIO
from pathlib import Path

import toml

MEMBERS = [
    "unicode-case",
    "unicode-width",
]

EXCLUDE_PATTERNS = {"cjpm.lock", "cangjie-repo.toml", "target", "__pycache__"}


def get_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_toml(path: Path) -> dict:
    return toml.load(path)


def get_version(member_dir: Path) -> str:
    return read_toml(member_dir / "cjpm.toml")["package"]["version"]


def get_old_version(member: str) -> str | None:
    """Get the version from the previous commit via git show."""
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD~1:{member}/cjpm.toml"],
            capture_output=True,
            text=True,
            check=True,
        )
        return toml.loads(result.stdout)["package"]["version"]
    except (subprocess.CalledProcessError, KeyError):
        return None


def detect_changed_members(root: Path) -> list[str]:
    """Compare versions between HEAD and HEAD~1 to find changed members."""
    changed = []
    for member in MEMBERS:
        member_dir = root / member
        if not member_dir.exists():
            continue
        new_ver = get_version(member_dir)
        old_ver = get_old_version(member)
        if old_ver != new_ver:
            changed.append(member)
    return changed


def make_bundle(member_dir: Path, data: dict) -> None:
    """Manually create .cjp tarball and meta-data.json."""
    pkg = data["package"]
    name = pkg["name"]
    version = pkg["version"]
    prefix = f"{name}-{version}"

    target_dir = member_dir / "target"
    target_dir.mkdir(exist_ok=True)

    cjp_path = target_dir / f"{prefix}.cjp"

    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        toml_path = member_dir / "cjpm.toml"
        tar.add(str(toml_path), arcname=f"{prefix}/cjpm.toml")

        for readme_name in ("README.md", "README_zh.md"):
            readme_path = member_dir / readme_name
            if readme_path.exists():
                tar.add(str(readme_path), arcname=f"{prefix}/{readme_name}")

        src_dir = member_dir / "src"
        if src_dir.exists():
            for f in sorted(src_dir.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(member_dir)
                    tar.add(str(f), arcname=f"{prefix}/{rel}")

    tarball_bytes = buf.getvalue()
    cjp_path.write_bytes(tarball_bytes)

    sha256 = hashlib.sha256(tarball_bytes).hexdigest()

    meta = {
        "organization": "",
        "name": name,
        "version": version,
        "description": pkg.get("description", ""),
        "artifact-type": "src",
        "executable": False,
        "authors": [],
        "repository": "",
        "homepage": "",
        "documentation": "",
        "tag": [],
        "category": [],
        "license": [],
        "cjc-version": pkg.get("cjc-version", ""),
        "index": {
            "organization": "",
            "name": name,
            "version": version,
            "dependencies": [],
            "test-dependencies": [],
            "script-dependencies": [],
            "sha256sum": sha256,
            "yanked": False,
            "cjc-version": pkg.get("cjc-version", ""),
            "index-version": 1,
        },
        "meta-version": 1,
    }

    meta_path = target_dir / "meta-data.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Bundled {cjp_path.name} ({len(tarball_bytes)} bytes, sha256={sha256[:16]}...)")


def create_github_release(member: str, version: str) -> None:
    """Create a GitHub release with tag for a workspace member."""
    tag = f"{member}/v{version}"
    title = f"{member} v{version}"
    result = subprocess.run(
        ["gh", "release", "create", tag, "--title", title, "--generate-notes"],
    )
    if result.returncode == 0:
        print(f"  Created GitHub release {tag}")
    else:
        print(f"  Warning: failed to create GitHub release {tag}")


def publish_members(root: Path, members: list[str]) -> None:
    """Publish specified members."""
    ordered = [m for m in MEMBERS if m in members]

    if not ordered:
        print("No matching members to publish.")
        return

    published = []

    for member in ordered:
        member_dir = root / member
        data = read_toml(member_dir / "cjpm.toml")
        version = data["package"]["version"]

        print(f"=== Publishing {member} ===")
        make_bundle(member_dir, data)

        for attempt in range(1, 4):
            result = subprocess.run(
                ["cjpm", "publish"], cwd=member_dir
            )
            if result.returncode == 0:
                break
            print(f"  Attempt {attempt}/3 failed, retrying...")
            time.sleep(5 * attempt)
        else:
            raise SystemExit(f"Failed to publish {member} after 3 attempts")

        published.append((member, version))
        print(f"=== {member} published ===\n")

    for member, version in published:
        create_github_release(member, version)


def main() -> None:
    root = get_root()

    if "--detect-and-publish" in sys.argv:
        changed = detect_changed_members(root)
        if not changed:
            print("No version changes detected.")
            return
        print(f"Detected version changes: {', '.join(changed)}")
        publish_members(root, changed)
    else:
        members = [a for a in sys.argv[1:] if not a.startswith("-")]
        if not members:
            print("Usage:")
            print("  uv run scripts/publish.py <member1> [member2 ...]")
            print("  uv run scripts/publish.py --detect-and-publish")
            sys.exit(1)
        publish_members(root, members)


if __name__ == "__main__":
    main()
