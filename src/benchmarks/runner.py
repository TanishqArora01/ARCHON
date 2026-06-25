import time
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from src.environment.ingestion import RepositoryIngestor
from src.environment.resolver.pipeline import SymbolResolverPipeline
from src.db.models import SymbolNode, SymbolEdge, UnresolvedReference

class BenchmarkPerformanceRunner:
    async def execute_evaluation(self, db_session: AsyncSession, repo_path: Path) -> dict:
        """
        Executes ingestion and resolution pipelines with high-precision timing.
        Calculates extraction and reference resolution rate metrics.
        """
        # 1. Ingestion
        ingestor = RepositoryIngestor()
        
        t0 = time.perf_counter()
        snapshot_id = await ingestor.ingest(repo_path, "00000000-0000-0000-0000-000000000000")
        t1 = time.perf_counter()
        ingestion_duration = t1 - t0

        # 2. Resolution
        resolver = SymbolResolverPipeline()
        t2 = time.perf_counter()
        await resolver.execute_pipeline(snapshot_id, db_session)
        t3 = time.perf_counter()
        resolution_duration = t3 - t2
        
        # 3. Calculate Core Metrics
        # Group symbols by type
        stmt = select(SymbolNode.symbol_type, func.count(SymbolNode.id)).where(SymbolNode.snapshot_id == snapshot_id).group_by(SymbolNode.symbol_type)
        result = await db_session.execute(stmt)
        extracted_symbols = {row[0]: row[1] for row in result.all()}
        
        # Total resolved edges
        edge_stmt = select(func.count(SymbolEdge.id)).where(SymbolEdge.snapshot_id == snapshot_id)
        edge_result = await db_session.execute(edge_stmt)
        total_edges = edge_result.scalar() or 0
        
        # Total unresolved references
        unresolved_stmt = select(func.count(UnresolvedReference.id)).where(UnresolvedReference.snapshot_id == snapshot_id)
        unresolved_result = await db_session.execute(unresolved_stmt)
        total_unresolved = unresolved_result.scalar() or 0
        
        # Breakdown of unresolved categories
        cat_stmt = select(UnresolvedReference.failure_category, func.count(UnresolvedReference.id)).where(UnresolvedReference.snapshot_id == snapshot_id).group_by(UnresolvedReference.failure_category)
        cat_result = await db_session.execute(cat_stmt)
        unresolved_breakdown = {row[0]: row[1] for row in cat_result.all()}

        total_references = total_edges + total_unresolved
        resolution_rate = 0.0
        if total_references > 0:
            resolution_rate = (total_edges / total_references) * 100.0
        elif total_edges > 0:
            resolution_rate = 100.0

        return {
            "snapshot_id": snapshot_id,
            "performance": {
                "ingestion_duration_seconds": round(ingestion_duration, 4),
                "resolution_duration_seconds": round(resolution_duration, 4),
                "total_duration_seconds": round(ingestion_duration + resolution_duration, 4)
            },
            "metrics": {
                "extracted_symbols": extracted_symbols,
                "total_resolved_edges": total_edges,
                "total_unresolved_references": total_unresolved,
                "unresolved_breakdown": unresolved_breakdown,
                "resolution_rate_percent": round(resolution_rate, 2),
                "total_references": total_references
            }
        }
