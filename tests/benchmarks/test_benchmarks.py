import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.db.models import Base
from src.benchmarks.target_repos import BenchmarkRepoManager
from src.benchmarks.runner import BenchmarkPerformanceRunner

@pytest.fixture(scope="module")
def fixture_path():
    # Use our local tests/fixtures/python micro-repository for fast, offline testing
    return Path(__file__).parent.parent / "fixtures" / "control_repo"

@pytest.mark.asyncio
async def test_benchmark_performance_runner_micro_repo(fixture_path, monkeypatch):
    # Set up in-memory DB for isolated testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Mock AsyncSessionLocal in ingestion to use our isolated test DB
    import src.environment.ingestion
    monkeypatch.setattr(src.environment.ingestion, "AsyncSessionLocal", AsyncSessionLocal)

    async with AsyncSessionLocal() as db_session:
        runner = BenchmarkPerformanceRunner()
        
        # We point it to the local fixture rather than cloning a real repo to avoid network failures in CI
        result = await runner.execute_evaluation(db_session, fixture_path)
        
        metrics = result["metrics"]
        perf = result["performance"]
        
        # Verify basic metric schemas exist
        assert "resolution_rate_percent" in metrics
        assert "total_resolved_edges" in metrics
        assert "total_unresolved_references" in metrics
        assert "extracted_symbols" in metrics
        assert "ingestion_duration_seconds" in perf
        assert "resolution_duration_seconds" in perf
        
        import pprint
        pprint.pprint(result)
        
        # Constitution Phase 1 Enforcer:
        # Reference Resolution > 70% minimum
        # Our micro-repository should easily pass this.
        assert metrics["resolution_rate_percent"] >= 70.0, f"Resolution rate failed constitution threshold! Got {metrics['resolution_rate_percent']}%"


@pytest.mark.asyncio
async def test_benchmark_repo_manager(tmp_path):
    """
    Test the repo manager logic by mocking out the subprocess call.
    """
    manager = BenchmarkRepoManager(cache_dir=str(tmp_path))
    
    import asyncio

    class MockProcess:
        def __init__(self, returncode=0, stdout=b"", stderr=b""):
            self.returncode = returncode
            self._stdout = stdout
            self._stderr = stderr
            
        async def communicate(self):
            return self._stdout, self._stderr

    async def mock_exec(*args, **kwargs):
        # Determine if it's clone or checkout
        if "clone" in args:
            target = args[-1]
            Path(target).mkdir(parents=True, exist_ok=True)
            return MockProcess(0)
        elif "checkout" in args:
            return MockProcess(0)
        return MockProcess(0)

    original_exec = asyncio.create_subprocess_exec
    asyncio.create_subprocess_exec = mock_exec

    try:
        target_path = await manager.prepare_target("https://github.com/dummy/repo", "dummy_sha")
        assert target_path.exists()
        assert target_path.name.startswith("repo_")
    finally:
        asyncio.create_subprocess_exec = original_exec
