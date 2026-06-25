import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.app import create_app
from src.db.models import AnalysisJob, AnalysisRun, Base, ReviewReport, Snapshot, SymbolEdge, SymbolNode


@pytest_asyncio.fixture
async def api_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr("src.api.repositories.AsyncSessionLocal", SessionLocal)
    monkeypatch.setattr("src.api.analysis.AsyncSessionLocal", SessionLocal)
    monkeypatch.setattr("src.api.graph.AsyncSessionLocal", SessionLocal)

    yield SessionLocal
    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_lifecycle_api(api_db):
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/repositories",
        json={
            "provider": "github",
            "owner": "psf",
            "name": "requests",
            "clone_url": "https://github.com/psf/requests.git",
            "default_branch": "main",
        },
    )

    assert response.status_code == 200
    repo = response.json()
    assert repo["owner"] == "psf"

    list_response = client.get("/api/v1/repositories")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/v1/repositories/{repo['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "requests"


@pytest.mark.asyncio
async def test_analysis_and_job_status_api(api_db):
    async with api_db() as session:
        snapshot = Snapshot(id="snapshot-1")
        run = AnalysisRun(id="run-1", snapshot_id=snapshot.id, status="completed")
        report = ReviewReport(id="report-1", analysis_run_id=run.id, tracking_token="token", report={"findings": []})
        job = AnalysisJob(id="job-1", status="completed", attempts=1, payload={"repo_url": "x"})
        session.add_all([snapshot, run, report, job])
        await session.commit()

    client = TestClient(create_app())
    runs = client.get("/api/v1/analysis-runs")
    assert runs.status_code == 200
    assert runs.json()[0]["id"] == "run-1"

    reports = client.get("/api/v1/analysis-runs/run-1/reports")
    assert reports.status_code == 200
    assert reports.json()[0]["tracking_token"] == "token"

    jobs = client.get("/api/v1/jobs")
    assert jobs.status_code == 200
    assert jobs.json()[0]["id"] == "job-1"


@pytest.mark.asyncio
async def test_graph_search_and_impact_api(api_db):
    async with api_db() as session:
        snapshot = Snapshot(id="snapshot-graph", repository_id="repo-graph")
        node_a = SymbolNode(
            id="node-a",
            snapshot_id=snapshot.id,
            file_path="core/auth.py",
            symbol_name="AuthService",
            symbol_type="CLASS",
            meta_data={},
        )
        node_b = SymbolNode(
            id="node-b",
            snapshot_id=snapshot.id,
            file_path="api/routes.py",
            symbol_name="login",
            symbol_type="FUNCTION",
            meta_data={},
        )
        edge = SymbolEdge(
            id="edge-1",
            snapshot_id=snapshot.id,
            from_node_id=node_b.id,
            to_node_id=node_a.id,
            edge_type="CALLS",
        )
        session.add_all([snapshot, node_a, node_b, edge])
        await session.commit()

    client = TestClient(create_app())

    search = client.get("/api/v1/graph/search", params={"repository_id": "repo-graph", "query": "Auth"})
    assert search.status_code == 200
    results = search.json()
    assert len(results) == 1
    assert results[0]["symbol_name"] == "AuthService"

    impact = client.get("/api/v1/graph/impact", params={"snapshot_id": snapshot.id, "node_id": node_a.id})
    assert impact.status_code == 200
    payload = impact.json()
    assert payload["blast_radius_score"] > 0
    impacted_ids = {node["id"] for node in payload["impacted_nodes"]}
    assert node_b.id in impacted_ids
