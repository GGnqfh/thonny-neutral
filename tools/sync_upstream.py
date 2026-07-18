#!/usr/bin/env python3
"""Sync upstream thonny releases to thonny-neutral.

Detects new upstream version tags (vX.Y.Z) that lack a corresponding
vX.Y.Z-neutral tag, creates a neutralized branch, applies Ukraine-content
removals, and pushes the neutral tag to trigger the build workflow.

Usage: python tools/sync_upstream.py
"""

import os
import re
import subprocess
import sys


def git(*args, check=True):
    cmd = ["git"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        if check:
            print(f"  [FAIL] git {' '.join(args)}")
            print(f"         {result.stderr.strip()}")
            result.check_returncode()
    return result


def git_output(*args):
    return git(*args).stdout.strip()


def get_upstream_tags():
    tags = [t.strip() for t in git_output("tag", "-l", "v*").split("\n") if t.strip()]
    version_tags = [t for t in tags if re.match(r"^v\d+\.\d+\.\d+$", t)]
    version_tags.sort(key=lambda t: tuple(int(x) for x in t.lstrip("v").split(".")))
    return version_tags


def get_neutral_tags():
    tags = [t.strip() for t in git_output("tag", "-l", "*-neutral").split("\n") if t.strip()]
    return set(tags)


def delete_file(path):
    if os.path.exists(path):
        git_output("rm", path)
        print(f"    [OK] Deleted {path}")
    else:
        print(f"    [SKIP] {path} not found")


def patch_file(path, pattern, replacement, description, flags=0):
    if not os.path.exists(path):
        print(f"    [SKIP] {path} not found ({description})")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(pattern, replacement, content, flags=flags)
    if new_content == content:
        print(f"    [WARN] Pattern not matched in {path} ({description})")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"    [OK] Patched {path} ({description})")


def remove_ukraine_content():
    print("  1. Deleting Ukraine PNGs...")
    for p in [
        "thonny/res/Ukraine.png",
        "thonny/res/Ukraine_2x.png",
        "thonny/plugins/pi/res/Ukraine.png",
        "thonny/plugins/pi/res/Ukraine48.png",
    ]:
        delete_file(p)

    print("\n  2. Patching workbench.py...")
    patch_file(
        "thonny/workbench.py",
        r"\n\s+self\.add_command\(\s*\n\s+\"SupportUkraine\".*?group=101,\s*\n\s+\)",
        "",
        "SupportUkraine toolbar command",
        flags=re.DOTALL,
    )
    patch_file(
        "thonny/workbench.py",
        r"\n\s+# self\._init_support_ukraine_bar\(\)",
        "",
        "commented ukraine bar call",
    )
    patch_file(
        "thonny/workbench.py",
        r"\n\s+def _init_support_ukraine_bar\(self\).*?"
        r'webbrowser\.open\("https://github\.com/thonny/thonny/wiki/Support-Ukraine"\)',
        "",
        "Ukraine support methods",
        flags=re.DOTALL,
    )

    print("\n  3. Patching pi/__init__.py...")
    patch_file(
        "thonny/plugins/pi/__init__.py",
        r'\s*"Ukraine":\s*"Ukraine(?:48)?\.png",\n',
        "",
        "Ukraine image mapping",
    )

    print("\n  4. Patching README.rst...")
    patch_file(
        "README.rst",
        r"^\.\. image:: https://github\.com/thonny/thonny/blob/master/thonny/res/Ukraine\.png"
        r"\n\n`Support Ukraine! <https://github\.com/thonny/thonny/wiki/Support-Ukraine>`_\n\n",
        "",
        "Ukraine flag + link",
        flags=re.MULTILINE,
    )

    print("\n  5. Patching CHANGELOG.rst...")
    patch_file(
        "CHANGELOG.rst",
        r"^\* Add new toolbar button which opens the wiki page describing ways to help Ukraine"
        r" survive the attack from Russia\.\n",
        "",
        "CHANGELOG entry",
        flags=re.MULTILINE,
    )

    print("\n  6. Disabling code signing in inno_setup.iss...")
    patch_file(
        "packaging/windows/inno_setup.iss",
        r"^SignTool=.*$",
        "; SignTool disabled for neutral builds",
        "SignTool directive",
        flags=re.MULTILINE,
    )


def copy_ci_files(base_commit):
    print("  7. Copying CI workflow from master...")
    result = subprocess.run(
        ["git", "show", f"{base_commit}:.github/workflows/build.yml"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"    [FAIL] build.yml not found in base commit {base_commit[:8]}")
        return False
    os.makedirs(".github/workflows", exist_ok=True)
    with open(".github/workflows/build.yml", "w", encoding="utf-8") as f:
        f.write(result.stdout)
    print("    [OK] Copied build.yml")
    return True


def fix_upstream_urls():
    """Replace upstream URLs with fork URLs."""
    print("  9. Fixing upstream URLs to point to fork...")
    URLS = [
        (
            "thonny/plugins/about.py",
            'https://github.com/thonny/thonny/blob/master/CHANGELOG.rst',
            'https://github.com/GGnqfh/thonny-neutral/releases',
            "Version history URL",
        ),
        (
            "thonny/plugins/about.py",
            'https://github.com/thonny/thonny/issues',
            'https://github.com/GGnqfh/thonny-neutral/issues',
            "Bug tracker URL",
        ),
        (
            "pyproject.toml",
            '"Bug tracker" = "https://github.com/thonny/thonny/issues"',
            '"Bug tracker" = "https://github.com/GGnqfh/thonny-neutral/issues"',
            "pyproject bug tracker",
        ),
        (
            "pyproject.toml",
            'Homepage = "https://thonny.org"',
            'Homepage = "https://github.com/GGnqfh/thonny-neutral"',
            "pyproject homepage",
        ),
        (
            "pyproject.toml",
            '"Source code" = "https://github.com/thonny/thonny"',
            '"Source code" = "https://github.com/GGnqfh/thonny-neutral"',
            "pyproject source",
        ),
        # Older versions use setup.py instead of pyproject.toml
        (
            "setup.py",
            '"Bug tracker": "https://github.com/thonny/thonny/issues"',
            '"Bug tracker": "https://github.com/GGnqfh/thonny-neutral/issues"',
            "setup.py bug tracker",
        ),
        (
            "setup.py",
            'url="https://thonny.org"',
            'url="https://github.com/GGnqfh/thonny-neutral"',
            "setup.py homepage",
        ),
        (
            "thonny/workbench.py",
            '"general.data_url_prefix", "https://raw.githubusercontent.com/thonny/thonny/master/data"',
            '"general.data_url_prefix", "https://raw.githubusercontent.com/GGnqfh/thonny-neutral/master/data"',
            "data URL prefix",
        ),
        (
            "thonny/assistance.py",
            "    def _append_feedback_link(self):\n        self._append_text(\"Was it helpful or confusing?\\n\", (\"a\", \"feedback_link\"))",
            "    def _append_feedback_link(self):\n        pass",
            "disable feedback link",
        ),
    ]
    all_ok = True
    for path, old, new, desc in URLS:
        if not os.path.exists(path):
            print(f"    [SKIP] {path} not found ({desc})")
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old not in content:
            print(f"    [FAIL] Pattern not found in {path} ({desc})")
            all_ok = False
            continue
        content = content.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        # Verify
        if new in content:
            print(f"    [OK] Fixed {desc}")
        else:
            print(f"    [FAIL] Verification failed for {desc}")
            all_ok = False
    if not all_ok:
        print("    [WARN] Some URL replacements failed (upstream may have changed the pattern)")
    return all_ok


def scan_for_ukraine():
    print("  8. Scanning for remaining Ukraine references...")
    found = []
    skip_dirs = {".git", "__pycache__", ".eggs", "node_modules", ".mypy_cache"}
    text_exts = {
        ".py", ".rst", ".md", ".iss", ".bat", ".txt",
        ".yml", ".yaml", ".cfg", ".ini", ".json", ".xml",
    }

    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in skip_dirs]

        for f in files:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, ".")

            # Skip locale files (language, not political)
            if rel.startswith("thonny\\locale") or rel.startswith("thonny/locale"):
                continue

            # Skip binary files
            ext = os.path.splitext(f)[1].lower()
            if ext in {
                ".png", ".gif", ".jpg", ".jpeg", ".ico", ".bmp",
                ".exe", ".dll", ".pyd", ".so", ".dylib",
                ".zip", ".7z", ".gz", ".tar",
                ".pyc", ".pyo",
                ".o", ".obj", ".lib", ".exp",
            }:
                continue

            # Check filename
            if "ukraine" in f.lower():
                found.append((rel, 0, f"Filename: {f}"))

            # Check content
            if ext in text_exts or ext == "":
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        for i, line in enumerate(fh, 1):
                            if "ukraine" in line.lower():
                                found.append((rel, i, line.rstrip()[:200]))
                except Exception:
                    pass

    if found:
        print(f"    [FAIL] Found {len(found)} remaining Ukraine reference(s):")
        for path, line, text in found:
            loc = f":{line}" if line else ""
            print(f"      {path}{loc}  {text}")
        return False
    else:
        print("    [OK] No Ukraine references found")
        return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    os.chdir(repo_root)

    print("=" * 60)
    print("  thonny-neutral sync upstream")
    print("=" * 60)

    original_commit = git_output("rev-parse", "HEAD")

    print("\nFetching upstream tags...")
    git("fetch", "upstream", "--tags")

    upstream_tags = get_upstream_tags()
    neutral_tags = get_neutral_tags()

    print(f"  Upstream version tags found: {len(upstream_tags)}")
    print(f"  Existing neutral tags:       {len(neutral_tags)}")

    unsynced = [t for t in upstream_tags if f"{t}-neutral" not in neutral_tags]

    if not unsynced:
        print("\nAll upstream versions are already synced. Nothing to do.")
        return

    # Only sync the latest version to prevent backfilling all historical releases
    unsynced = unsynced[-1:]

    print(f"\nNew versions to sync: {unsynced}")

    for tag in unsynced:
        neutral_tag = f"{tag}-neutral"
        branch = f"auto-sync-{tag}"

        print(f"\n{'─' * 60}")
        print(f"  Processing {tag} → {neutral_tag}")
        print(f"{'─' * 60}")

        r = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/tags/{tag}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            print(f"  [SKIP] Tag {tag} not available locally")
            continue

        git("checkout", "-D", branch, check=False)
        git("checkout", "-b", branch, tag)
        print(f"  Checked out {tag}")

        remove_ukraine_content()
        fix_upstream_urls()
        if not copy_ci_files(original_commit):
            print(f"\n  [SKIP] Tag {tag} (copy_ci_files failed)")
            git("checkout", original_commit, check=False)
            git("branch", "-D", branch, check=False)
            continue
        if not scan_for_ukraine():
            print(f"\n  [SKIP] Tag {tag} (Ukraine references remain)")
            git("checkout", original_commit, check=False)
            git("branch", "-D", branch, check=False)
            continue

        git("add", "-A")
        r = git("commit", "-m", f"Neutralize {tag}", check=False)
        if r.returncode != 0:
            print(f"  [SKIP] No changes for {tag}")
            git("checkout", original_commit, check=False)
            git("branch", "-D", branch, check=False)
            continue

        git("tag", neutral_tag)
        git("push", "fork", "HEAD:master", check=False)
        git("push", "fork", neutral_tag, check=False)
        new_tags.append(neutral_tag)
        print(f"\n  [OK] Tagged {neutral_tag}")

        git("checkout", original_commit, check=False)
        git("branch", "-D", branch, check=False)
        print(f"\n  [DONE] {tag} → {neutral_tag}")

    print(f"\n{'=' * 60}")
    print(f"  Sync complete. Created {len(unsynced)} neutral release(s).")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
