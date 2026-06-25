from pathlib import Path
from src.db.session import AsyncSessionLocal
from src.environment.ingestion import RepositoryIngestor
from src.vcs.git_analyzer import GitDiffAnalyzer
from src.retrieval.engine import HybridRetrievalEngine
from src.agents.workflow import build_archon_graph
from src.memory.vector_store import QdrantMemoryStore
from src.memory.providers import OllamaEmbeddingProvider
from src.agents.state import GraphState
from src.agents.llm_provider import BaseLLMProvider
from qdrant_client import AsyncQdrantClient

async def run_archon_analysis(repo_path: Path, diff_text: str, query_intent: str, llm_provider: BaseLLMProvider | None = None):
    """
    Unified Staff Engineer Gateway CLI Entrypoint
    """
    # 1. Ingest repository snapshot
    ingestor = RepositoryIngestor()
    snapshot_id = await ingestor.ingest(repo_path)

    # 2. Map git diff to exact symbol IDs
    git_analyzer = GitDiffAnalyzer()
    
    async with AsyncSessionLocal() as db_session:
        impacted_symbols = await git_analyzer.map_diff_to_symbols(db_session, snapshot_id, diff_text)
        
        # 3. Hybrid Retrieval for each modified symbol
        # Fallback empty string if not connected to actual Qdrant
        provider = OllamaEmbeddingProvider()
        engine = HybridRetrievalEngine(provider)
        qclient = AsyncQdrantClient(url="http://localhost:6333")
        qdrant_store = QdrantMemoryStore(qclient)
        
        collection_name = "archon_docs"
        
        compiled_graph = build_archon_graph(llm=llm_provider)
        
        for symbol_id in impacted_symbols:
            # 4. Compile contexts
            context = await engine.execute_fused_retrieval(
                db_session=db_session,
                qdrant_store=qdrant_store,
                snapshot_id=snapshot_id,
                collection_name=collection_name,
                target_symbol_id=symbol_id,
                query_text=query_intent,
                semantic_limit=5
            )
            
            # 5. Feed into LangGraph
            initial_state: GraphState = {
                "assembled_context": context,
                "selected_agents": [],
                "routing_rationale": "",
                "raw_specialist_reports": [],
                "final_report": None,
            }
            
            result = await compiled_graph.ainvoke(initial_state)
            
            # 6. Format and Print High-Fidelity Markdown
            report = result.get("final_report")
            if not report or not report.findings:
                print(f"No findings for symbol {symbol_id}.\n")
                continue
                
            print(f"## Analysis for Symbol: {symbol_id}\n")
            for finding in report.findings:
                severity_tag = f"**[{finding.severity.value}]**"
                print(f"### {severity_tag} {finding.issue}")
                print(f"**Evidence:**\n{finding.evidence}\n")
                print(f"**Reasoning:**\n{finding.reasoning}\n")
                print(f"**Impact:**\n{finding.impact}\n")
                print(f"**Recommendation:**\n{finding.recommendation}\n")
                print("---\n")
