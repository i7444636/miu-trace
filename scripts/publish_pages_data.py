"""Commit the newly built public index and let the Pages workflow deploy it.

The periodic indexer runs on Oracle because its Dropbox credentials never leave
that server.  This script is deliberately limited to generated public data.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATHS = ("frontend/data/index", "frontend/data/google-events.json.gz")
SSH_KEY = Path("/etc/miu-trace-pages-deploy.key")


def run(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, check=check, capture_output=True)


def main() -> None:
    if not SSH_KEY.is_file():
        raise SystemExit(f"Pages deploy key is missing: {SSH_KEY}")

    os.environ["GIT_SSH_COMMAND"] = (
        f"ssh -i {SSH_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    )
    # The running service can contain locally generated/uncommitted data.
    # Publish from a clean short-lived clone, so only public data is committed.
    with tempfile.TemporaryDirectory(prefix="miu-trace-pages-") as directory:
        checkout = Path(directory) / "repo"
        run("git", "clone", "--depth=1", "git@github.com:leehk2275/miu-trace.git", str(checkout))
        shutil.copytree(ROOT / "frontend" / "data" / "index", checkout / "frontend" / "data" / "index", dirs_exist_ok=True)
        shutil.copy2(ROOT / "frontend" / "data" / "google-events.json.gz", checkout / "frontend" / "data" / "google-events.json.gz")
        run("git", "config", "user.name", "miu-trace-indexer", cwd=checkout)
        run("git", "config", "user.email", "miu-trace-indexer@users.noreply.github.com", cwd=checkout)
        run("git", "add", "--", *PUBLIC_PATHS, cwd=checkout)
        if run("git", "diff", "--cached", "--quiet", cwd=checkout, check=False).returncode == 0:
            print("No public index changes to publish.")
            return
        run("git", "commit", "-m", "Sync latest MIU Trace public index", cwd=checkout)
        run("git", "pull", "--rebase", "origin", "main", cwd=checkout)
        run("git", "push", "origin", "HEAD:main", cwd=checkout)
    print("Published refreshed public index to GitHub Pages.")


if __name__ == "__main__":
    main()
