from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.benchmarks.runner import BenchmarkPerformanceRunner
from src.benchmarks.target_repos import BenchmarkRepoManager
from src.core.config import settings
from src.db.models import Base

TARGETS = {
    "fastapi": ("https://github.com/fastapi/fastapi.git", "c61384e3d72cc4d32050e05ee409fd8a5d345844"),
    "requests": ("https://github.com/psf/requests.git", "d64b9ad4bf1c14e21e0df3f0f4320fec81180e91"),
    "typer": ("https://github.com/fastapi/typer.git", "5ec6501a3c3bb5bf0e66ed1fafd13e368f660ed1"),
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run Archon repository intelligence benchmarks.")
    parser.add_argument("--target", choices=[*TARGETS.keys(), "all"], default="all")
    parser.add_argument("--output", default="benchmark_results.json")
    args = parser.parse_args()

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    manager = BenchmarkRepoManager()
    runner = BenchmarkPerformanceRunner()
    selected = TARGETS if args.target == "all" else {args.target: TARGETS[args.target]}
    results = {}

    async with session_factory() as session:
        for name, (repo_url, ref) in selected.items():
            repo_path = await manager.prepare_target(repo_url, ref)
            results[name] = await runner.execute_evaluation(session, repo_path)

    Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
