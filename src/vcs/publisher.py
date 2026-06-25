from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class BaseVCSStatusPublisher(ABC):
    @abstractmethod
    async def publish_analysis_report(self, target_url: str, commit_sha: str, report_markdown: str) -> dict:
        pass


class LoggingVCSStatusPublisher(BaseVCSStatusPublisher):
    async def publish_analysis_report(self, target_url: str, commit_sha: str, report_markdown: str) -> dict:
        payload = {
            "target_url": target_url,
            "commit_sha": commit_sha,
            "body": report_markdown,
        }
        logger.info("Publishing VCS status report to %s for commit %s", target_url, commit_sha)
        logger.debug("Payload: %s", payload)
        return payload


class GitHubStatusPublisher(BaseVCSStatusPublisher):
    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        self.token = token
        self.api_url = api_url.rstrip("/")

    async def publish_analysis_report(self, target_url: str, commit_sha: str, report_markdown: str) -> dict:
        owner, repo = self._parse_github_repo(target_url)
        payload = {
            "state": "success",
            "context": "archon/repository-intelligence",
            "description": "Archon repository intelligence analysis completed",
            "target_url": "",
        }
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            status_response = await client.post(
                f"{self.api_url}/repos/{owner}/{repo}/statuses/{commit_sha}",
                headers=headers,
                json=payload,
            )
            status_response.raise_for_status()

            issue_number = self._pull_request_number_from_url(target_url)
            if issue_number:
                comment_response = await client.post(
                    f"{self.api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                    headers=headers,
                    json={"body": report_markdown},
                )
                comment_response.raise_for_status()

        return {"provider": "github", "owner": owner, "repo": repo, "commit_sha": commit_sha}

    @staticmethod
    def _parse_github_repo(target_url: str) -> tuple[str, str]:
        parsed = urlparse(target_url)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Cannot parse GitHub repository from {target_url}")
        return parts[0], parts[1].removesuffix(".git")

    @staticmethod
    def _pull_request_number_from_url(target_url: str) -> int | None:
        parts = [p for p in urlparse(target_url).path.strip("/").split("/") if p]
        if "pull" not in parts:
            return None
        idx = parts.index("pull")
        if idx + 1 >= len(parts):
            return None
        try:
            return int(parts[idx + 1])
        except ValueError:
            return None


def build_vcs_publisher() -> BaseVCSStatusPublisher:
    provider = settings.VCS_PROVIDER.lower()
    if provider == "github":
        if not settings.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN is required when VCS_PROVIDER=github")
        return GitHubStatusPublisher(settings.GITHUB_TOKEN, settings.GITHUB_API_URL)
    return LoggingVCSStatusPublisher()


VCSStatusPublisher = LoggingVCSStatusPublisher
