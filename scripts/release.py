"""Automated release script for Letter Demon.

Run from the `dev` branch. Performs pre-flight checks, generates
changelog from conventional commits, bumps version, merges dev to
main, tags, and pushes.

Usage: python scripts/release.py
"""

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

VERSION_FILE = REPO / "core" / "__init__.py"
PYPROJECT_FILE = REPO / "pyproject.toml"
RELEASE_NOTES = REPO / "RELEASE_NOTES.md"

CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|BREAKING)(\(.+\))?(!)?: (.+)$"
)


def run(cmd, capture=True, check=True):
    result = subprocess.run(
        cmd, capture_output=capture, text=True, check=check, cwd=REPO
    )
    return result.stdout.strip() if capture else result


def guard(condition, msg):
    if not condition:
        print(f"FAIL: {msg}")
        sys.exit(1)


def get_current_version():
    content = VERSION_FILE.read_text("utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    return m.group(1) if m else None


def set_core_version(version):
    content = VERSION_FILE.read_text("utf-8")
    content = re.sub(
        r'(__version__\s*=\s*)"([^"]+)"',
        lambda m: f'{m.group(1)}"{version}"',
        content,
    )
    VERSION_FILE.write_text(content, "utf-8")


def set_pyproject_version(version):
    content = PYPROJECT_FILE.read_text("utf-8")
    content = re.sub(
        r'(^version\s*=\s*)"([^"]+)"',
        lambda m: f'{m.group(1)}"{version}"',
        content,
        flags=re.MULTILINE,
    )
    PYPROJECT_FILE.write_text(content, "utf-8")


def get_last_tag():
    try:
        return run(["git", "describe", "--tags", "--abbrev=0"])
    except subprocess.CalledProcessError:
        return None


def get_commits_since(tag):
    if not tag:
        result = run(["git", "log", "--oneline"])
    else:
        result = run(["git", "log", "--oneline", f"{tag}..HEAD"])
    return [line for line in result.split("\n") if line.strip()]


def parse_commits(commit_lines):
    sections = {
        "feat": [],
        "fix": [],
        "chore": [],
        "docs": [],
        "refactor": [],
        "test": [],
        "breaking": [],
    }
    for line in commit_lines:
        sha, _, msg = line.partition(" ")
        m = CONVENTIONAL_RE.match(msg)
        if m:
            prefix = m.group(1)
            breaking_marker = m.group(3)
            description = m.group(4)
            if breaking_marker == "!" or "BREAKING" in msg.upper():
                sections["breaking"].append(description)
            elif prefix == "BREAKING":
                sections["breaking"].append(description)
            else:
                sections[prefix].append(description)
        else:
            sections.setdefault("other", []).append(msg)
    return sections


def detect_bump(sections):
    if sections["breaking"]:
        return "major"
    if sections["feat"]:
        return "minor"
    return "patch"


def bump_version(version, bump_type):
    major, minor, patch = map(int, version.split("."))
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def generate_changelog(sections, new_version):
    today = date.today().isoformat()
    lines = [f"\n## v{new_version} ({today})\n"]
    label_map = {
        "feat": "Features",
        "fix": "Bug Fixes",
        "chore": "Chores",
        "docs": "Documentation",
        "refactor": "Refactors",
        "test": "Tests",
        "breaking": "Breaking Changes",
    }
    for key, label in label_map.items():
        items = sections.get(key, [])
        if items:
            lines.append(f"\n### {label}")
            for item in items:
                lines.append(f"- {item}")
    other = sections.get("other", [])
    if other:
        lines.append("\n### Other")
        for item in other:
            lines.append(f"- {item}")
    return "\n".join(lines)


def main():
    print("=== Letter Demon Release Script ===")
    print()

    # ---- Pre-flight ----
    guard(
        run(["git", "branch", "--show-current"]) == "dev",
        "Must be on the dev branch.",
    )
    guard(
        not run(["git", "status", "--porcelain"]),
        "Working tree is dirty. Commit or stash first.",
    )

    try:
        unpushed = run(["git", "log", "--oneline", "@{u}..HEAD"])
        guard(not unpushed.strip(), "Unpushed commits on dev. Push them first.")
    except subprocess.CalledProcessError:
        pass

    print("Running pre-flight checks...")
    run(["ruff", "check", "."], check=True)
    print("  ruff: OK")
    run([sys.executable, "-m", "unittest", "discover"], check=True)
    print("  tests: OK")

    # ---- Version ----
    current_version = get_current_version()
    guard(current_version, "Could not read version from core/__init__.py")
    print(f"\nCurrent version: v{current_version}")

    # ---- Changelog ----
    last_tag = get_last_tag()
    print(f"Last tag: {last_tag or '(none)'}")
    commits = get_commits_since(last_tag)
    if not commits:
        print("No new commits since last tag. Nothing to release.")
        sys.exit(0)

    sections = parse_commits(commits)
    bump = detect_bump(sections)
    new_version = bump_version(current_version, bump)

    print(f"\nCommits since {last_tag or 'beginning'}:")
    for c in commits:
        print(f"  {c}")

    print(f"\nDetected bump type: {bump}")
    print(f"Proposed version: v{current_version} -> v{new_version}")

    changelog = generate_changelog(sections, new_version)
    print(f"\n--- Changelog Preview ---{changelog}\n------------------------")

    confirm = input("Proceed with release? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Aborted.")
        sys.exit(0)

    # ---- Execute ----
    print("\nExecuting release...")

    set_core_version(new_version)
    set_pyproject_version(new_version)
    print("  version files updated")

    if RELEASE_NOTES.exists():
        with open(RELEASE_NOTES, "a", encoding="utf-8") as f:
            f.write(changelog)
    else:
        RELEASE_NOTES.write_text(
            f"# Release Notes\n\nGenerated by scripts/release.py{changelog}",
            "utf-8",
        )
    print("  changelog appended")

    run(
        ["git", "add", str(VERSION_FILE), str(PYPROJECT_FILE), str(RELEASE_NOTES)],
        check=True,
    )
    run(
        ["git", "commit", "-m", f"chore: bump v{current_version} -> v{new_version}"],
        check=True,
    )
    print("  bump committed on dev")

    run(["git", "checkout", "main"], check=True)
    merge_msg = f"Merge dev -> main: release v{new_version}"
    try:
        run(["git", "merge", "dev", "--no-ff", "-m", merge_msg], check=True)
    except subprocess.CalledProcessError:
        print()
        print("ERROR: Merge conflict detected.")
        print("Resolve conflicts manually, then run:")
        print("  git commit")
        print(f"  git tag v{new_version}")
        print("  git push --all && git push --tags")
        print("  git checkout dev")
        sys.exit(1)
    print(f"  merged to main: {merge_msg}")

    run(["git", "tag", f"v{new_version}"], check=True)
    print(f"  tagged v{new_version}")

    run(["git", "push", "--all"], check=True)
    run(["git", "push", "--tags"], check=True)
    print("  pushed to remote")

    run(["git", "checkout", "dev"], check=True)

    print(f"\nDone. v{new_version} released successfully.")
    print("View changelog: RELEASE_NOTES.md")


if __name__ == "__main__":
    main()
