"""Commit the newly built public index and let the Pages workflow deploy it.

The periodic indexer runs on Oracle because its Dropbox credentials never leave
that server.  This script is deliberately limited to generated public data.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATHS = ("frontend/data/index", "frontend/data/google-events.json.gz")
SSH_KEY = Path("/etc/miu-trace-pages-deploy.key")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, check=check, capture_output=True)


def main() -> None:
    if not SSH_KEY.is_file():
        raise SystemExit(f"Pages deploy key is missing: {SSH_KEY}")

    os.environ["GIT_SSH_COMMAND"] = (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    )
    run("git", "remote", "set-url", "origin", "git@github.com:leehk2275/miu-trace.git")
    run("git", "config", "user.name", "miu-trace-indexer")
    run("git", "config", "user.email", "miu-trace-indexer@users.noreply.github.com")
    run("git", "add", "--", *PUBLIC_PATHS)
    if run("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
        print("No public index changes to publish.")
        return

    run("git", "commit", "-m", "Sync latest MIU Trace public index")
    # Code changes and manual Google resyncs may land between timer runs.
    # Rebase our data-only commit before pushing instead of overwriting them.
    run("git", "pull", "--rebase", "origin", "main")
    run("git", "push", "origin", "HEAD:main")
    print("Published refreshed public index to GitHub Pages.")


if __name__ == "__main__":
    main()
