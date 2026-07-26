import os
import stat
import subprocess
import shutil

CLONE_DIR = "cloned_repos"


def _remove_readonly(func, path, exc_info):
    """Handler for shutil.rmtree - clears the read-only bit and retries.
    Needed on Windows because git leaves some .git files as read-only."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_repo(github_url):
    os.makedirs(CLONE_DIR, exist_ok=True)

    repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    target_path = os.path.join(CLONE_DIR, repo_name)

    if os.path.exists(target_path):
        print(f"Repo already cloned at {target_path}, removing old copy first...")
        shutil.rmtree(target_path, onerror=_remove_readonly)

    print(f"Cloning {github_url}...")
    result = subprocess.run(
        ["git", "clone", "--depth", "1", github_url, target_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")

    print(f"Cloned to {target_path}")
    return target_path


if __name__ == "__main__":
    path = clone_repo("https://github.com/AltunbasYusuf/SmartVineyard-Analytics")
    print(f"\nRepo is at: {path}")