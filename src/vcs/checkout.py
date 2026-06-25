from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse


class RepositoryCheckoutError(RuntimeError):
    pass


class GitRepositoryCheckout:
    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def prepare(
        self,
        repo_path_or_url: str,
        commit_sha: str | None = None,
        access_token: str | None = None,
        provider: str | None = None,
    ) -> Path:
        candidate = Path(repo_path_or_url)
        if candidate.exists():
            return candidate.resolve()

        if not self._is_supported_git_url(repo_path_or_url):
            raise RepositoryCheckoutError(f"Unsupported repository target: {repo_path_or_url}")

        target = self.cache_dir / self._cache_key(repo_path_or_url, commit_sha)
        if target.exists():
            if commit_sha:
                await self._run_git(["git", "checkout", commit_sha], cwd=target)
            return target

        clone_url = self._with_access_token(repo_path_or_url, access_token, provider)
        await self._run_git(["git", "clone", "--depth", "1", clone_url, str(target)])
        if access_token:
            await self._run_git(["git", "remote", "set-url", "origin", repo_path_or_url], cwd=target)
        if commit_sha:
            try:
                fetch_url = self._with_access_token(repo_path_or_url, access_token, provider)
                await self._run_git(["git", "fetch", "--depth", "1", fetch_url, commit_sha], cwd=target)
            except RepositoryCheckoutError:
                fetch_url = self._with_access_token(repo_path_or_url, access_token, provider)
                await self._run_git(["git", "fetch", fetch_url, commit_sha], cwd=target)
            await self._run_git(["git", "checkout", commit_sha], cwd=target)

        return target

    @staticmethod
    def _is_supported_git_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"https", "http", "ssh", "git"} and bool(parsed.netloc)

    @staticmethod
    def _cache_key(repo_url: str, commit_sha: str | None) -> str:
        parsed = urlparse(repo_url)
        repo_name = Path(parsed.path.rstrip("/")).name.removesuffix(".git") or "repository"
        digest = hashlib.sha256(f"{repo_url}:{commit_sha or 'HEAD'}".encode("utf-8")).hexdigest()[:12]
        return f"{repo_name}_{digest}"

    @staticmethod
    def _with_access_token(repo_url: str, access_token: str | None, provider: str | None) -> str:
        if not access_token:
            return repo_url
        parsed = urlparse(repo_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            return repo_url

        username = "oauth2" if provider == "gitlab" else "x-access-token"
        safe_token = quote(access_token, safe="")
        netloc = f"{username}:{safe_token}@{parsed.netloc}"
        return urlunparse(parsed._replace(netloc=netloc))

    @staticmethod
    async def _run_git(command: list[str], cwd: Path | None = None) -> None:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace") or stdout.decode("utf-8", errors="replace")
            raise RepositoryCheckoutError(message.strip())
