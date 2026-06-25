import asyncio
from pathlib import Path

import pytest

from src.vcs.checkout import GitRepositoryCheckout


@pytest.mark.asyncio
async def test_checkout_returns_existing_local_path(tmp_path):
    checkout = GitRepositoryCheckout(tmp_path / "cache")
    repo = tmp_path / "repo"
    repo.mkdir()

    result = await checkout.prepare(str(repo), "abc123")

    assert result == repo.resolve()


@pytest.mark.asyncio
async def test_checkout_clones_git_url(tmp_path, monkeypatch):
    commands = []

    class MockProcess:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def mock_exec(*args, **kwargs):
        commands.append(args)
        if "clone" in args:
            Path(args[-1]).mkdir(parents=True, exist_ok=True)
        return MockProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)

    checkout = GitRepositoryCheckout(tmp_path / "cache")
    result = await checkout.prepare("https://github.com/psf/requests.git", "main")

    assert result.exists()
    assert any("clone" in command for command in commands)
    assert any("checkout" in command for command in commands)
