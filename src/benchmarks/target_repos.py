import shutil
from pathlib import Path

from src.vcs.checkout import GitRepositoryCheckout

class BenchmarkRepoManager:
    def __init__(self, cache_dir: str = ".archon_cache/benchmarks"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.checkout = GitRepositoryCheckout(self.cache_dir)

    async def prepare_target(self, repo_url: str, commit_sha: str) -> Path:
        """
        Securely downloads or clones a public reference repository into an isolated local cache path.
        Checks out the specific commit_sha to ensure benchmark evaluations are perfectly reproducible.
        """
        try:
            return await self.checkout.prepare(repo_url, commit_sha)
        except Exception as exc:
            repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
            target_path = self.cache_dir / f"{repo_name}_{commit_sha}"
            shutil.rmtree(target_path, ignore_errors=True)
            raise RuntimeError(f"Failed to prepare benchmark repository {repo_url}@{commit_sha}: {exc}") from exc
