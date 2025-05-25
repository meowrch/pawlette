import subprocess
from pathlib import Path

from loguru import logger


class GitManager:
    def __init__(self, repo_path: Path, config_path: Path):
        self.repo_path = repo_path
        self.config_path = config_path
        self._init_repo()

    def _run_git(self, *args: str) -> bool:
        try:
            subprocess.run(
                ["git", "-C", str(self.repo_path)] + list(args),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git error: {e.stderr}")
            return False

    def _init_repo(self):
        if not (self.repo_path / ".git").exists():
            self.repo_path.mkdir(parents=True, exist_ok=True)
            self._run_git("init", "--bare")
            self._run_git("config", "core.bare", "false")
            self._run_git("config", "core.worktree", str(self.config_path))
            self._run_git("config", "status.showUntrackedFiles", "no")
            self._run_git("commit", "--allow-empty", "-m", "Initial empty commit")

    def commit(self, message: str) -> bool:
        return self._run_git("add", "-A") and self._run_git("commit", "-m", message)

    def branch_exists(self, branch_name: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "branch", "--list", branch_name],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())

    def create_branch(self, branch_name: str) -> bool:
        return self._run_git("branch", branch_name)

    def checkout(self, branch_name: str) -> bool:
        return self._run_git("checkout", branch_name)

    def stash(self) -> bool:
        return self._run_git("stash", "-u")

    def stash_pop(self) -> bool:
        return self._run_git("stash", "pop")

    def reset_hard(self, commit: str) -> bool:
        return self._run_git("reset", "--hard", commit)

    def get_current_commit(self) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def get_branches(self) -> list:
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "branch", "--all"],
            capture_output=True,
            text=True,
        )
        return result.stdout.splitlines()

    def get_log(self, limit=10) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "log", "--oneline", f"-{limit}"],
            capture_output=True,
            text=True,
        )
        return result.stdout

    def get_status(self) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo_path), "status", "-s"],
            capture_output=True,
            text=True,
        )
        return result.stdout
