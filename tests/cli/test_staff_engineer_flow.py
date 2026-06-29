import pytest
from uuid import uuid4
import json
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import SymbolNode, Snapshot
from src.vcs.git_analyzer import GitDiffAnalyzer
from src.cli.main import run_archon_analysis
from src.agents.llm_provider import BaseLLMProvider
from src.retrieval.schemas import AssembledAgentContext, StructuralContext, SemanticContext

class MockOrchestratorLLM(BaseLLMProvider):
    async def complete(self, system_prompt: str, user_message: str) -> str:
        if "selected_agents" in system_prompt:
            return json.dumps({
                "selected_agents": ["architecture", "maintainability", "technical_debt"],
                "rationale": "Testing."
            })
        return json.dumps({
            "findings": [
                {
                    "issue": "Mocked Issue",
                    "evidence": "Mocked Evidence",
                    "reasoning": "Mocked Reasoning",
                    "impact": "Mocked Impact",
                    "recommendation": "Mocked Recommendation",
                    "severity": "HIGH"
                }
            ]
        })

@pytest.mark.asyncio
async def test_git_analyzer_parses_diff():
    analyzer = GitDiffAnalyzer()
    diff_text = """diff --git a/tests/fixtures/python/controller.py b/tests/fixtures/python/controller.py
index a23b4c..d56e7f 10064
--- a/tests/fixtures/python/controller.py
+++ b/tests/fixtures/python/controller.py
@@ -10,3 +10,4 @@
 def main():
     print("Hello")
+    print("World")
"""
    patches = analyzer.parse_diff_patches(diff_text)
    assert len(patches) == 1
    assert patches[0]["file_path"] == "tests/fixtures/python/controller.py"
    # start = 10, count = 4 -> 0-indexed [9, 12]
    assert patches[0]["line_ranges"] == [(9, 12)]

@pytest.mark.asyncio
async def test_git_analyzer_maps_to_symbol():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from src.db.models import Base
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as db_session:
        snapshot_id = uuid4()
        snap = Snapshot(id=str(snapshot_id))
        db_session.add(snap)
    
        sym = SymbolNode(
            id=f"{snapshot_id}::src/main.py::foo",
            snapshot_id=str(snapshot_id),
            file_path="src/main.py",
            symbol_name="foo",
            symbol_type="function",
            meta_data={"line_range": [8, 15]}
        )
        db_session.add(sym)
        await db_session.commit()
    
        diff_text = """diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -10,1 +10,2 @@
+    foo()
"""
        analyzer = GitDiffAnalyzer()
        impacted = await analyzer.map_diff_to_symbols(db_session, snapshot_id, diff_text)
        assert len(impacted) == 1
        assert impacted[0] == f"{snapshot_id}::src/main.py::foo"

@pytest.mark.asyncio
async def test_run_archon_analysis(tmp_path, capsys, monkeypatch):
    async def mock_ingest(self, target_dir):
        return uuid4()
        
    async def mock_map(self, db_session, snapshot_id, diff_text):
        return ["dummy_snapshot::src/main.py::dummy"]
        
    async def mock_retrieve(self, db_session, qdrant_store, snapshot_id, collection_name, target_symbol_id, query_text, semantic_limit):
        return AssembledAgentContext(
            tracking_token="token",
            repository_name="dummy_repo",
            query_text=query_text,
            structural=StructuralContext(
                impacted_file_paths=["src/main.py"],
                impacted_symbol_ids=["dummy_snapshot::src/main.py::dummy"],
                blast_radius_score=1.0,
                choke_points=[]
            ),
            semantic=SemanticContext()
        )
        
    monkeypatch.setattr("src.environment.ingestion.RepositoryIngestor.ingest", mock_ingest)
    monkeypatch.setattr("src.vcs.git_analyzer.GitDiffAnalyzer.map_diff_to_symbols", mock_map)
    monkeypatch.setattr("src.retrieval.engine.HybridRetrievalEngine.execute_fused_retrieval", mock_retrieve)

    llm = MockOrchestratorLLM()
    
    await run_archon_analysis(tmp_path, "dummy diff", "dummy intent", llm_provider=llm)
    
    captured = capsys.readouterr()
    assert "Analysis for Symbol: dummy_snapshot::src/main.py::dummy" in captured.out
    assert "**[HIGH]** Mocked Issue" in captured.out
    assert "**Evidence:**" in captured.out
    assert "**Reasoning:**" in captured.out
    assert "**Impact:**" in captured.out
    assert "**Recommendation:**" in captured.out
