from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from src.api.schemas import ImpactAnalysisResponse, SymbolNodeRead
from src.api.security import require_api_token
from src.db.models import Snapshot, SymbolNode
from src.db.session import AsyncSessionLocal
from src.graph.builder import NetworkXGraphBuilder
from src.graph.traverser import GraphImpactTraverser

router = APIRouter(prefix="/api/v1/graph", tags=["graph"], dependencies=[Depends(require_api_token)])


@router.get("/search", response_model=list[SymbolNodeRead])
async def search_graph(repository_id: str, query: str = "") -> list[SymbolNodeRead]:
    async with AsyncSessionLocal() as session:
        # Get the latest snapshot for the repository
        snapshot_result = await session.execute(
            select(Snapshot)
            .where(Snapshot.repository_id == repository_id)
            .order_by(Snapshot.created_at.desc())
            .limit(1)
        )
        snapshot = snapshot_result.scalar_one_or_none()
        if not snapshot:
            raise HTTPException(status_code=404, detail="No snapshots found for this repository")

        # Search for nodes where symbol_name or file_path matches the query
        stmt = select(SymbolNode).where(SymbolNode.snapshot_id == snapshot.id)
        stmt = stmt.where(SymbolNode.symbol_name != "__FILE__")
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                SymbolNode.symbol_name.ilike(search_term) | SymbolNode.file_path.ilike(search_term)
            )
        
        # Limit the results to prevent massive payloads
        stmt = stmt.limit(100)
        
        nodes_result = await session.execute(stmt)
        nodes = nodes_result.scalars().all()
        
        return [
            SymbolNodeRead(
                id=node.id,
                snapshot_id=node.snapshot_id,
                file_path=node.file_path,
                symbol_name=node.symbol_name,
                symbol_type=node.symbol_type,
                meta_data=node.meta_data,
            )
            for node in nodes
        ]


@router.get("/impact", response_model=ImpactAnalysisResponse)
async def get_impact_analysis(snapshot_id: str, node_id: str) -> ImpactAnalysisResponse:
    async with AsyncSessionLocal() as session:
        # Build the graph
        builder = NetworkXGraphBuilder()
        try:
            graph = await builder.build_snapshot_graph(session, snapshot_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to build graph: {exc}") from exc
            
        # Calculate blast radius
        impact_result = GraphImpactTraverser.calculate_blast_radius(graph, node_id)
        impacted_node_ids = impact_result.get("impacted_node_ids", [])
        blast_radius_score = impact_result.get("blast_radius_score", 0.0)
        
        # Fetch the full node data for the impacted nodes
        impacted_nodes = []
        if impacted_node_ids:
            # We chunk the queries if there are too many nodes
            # But usually SQLite/Postgres can handle a decent sized IN clause
            stmt = select(SymbolNode).where(SymbolNode.id.in_(impacted_node_ids))
            nodes_result = await session.execute(stmt)
            for node in nodes_result.scalars().all():
                impacted_nodes.append(
                    SymbolNodeRead(
                        id=node.id,
                        snapshot_id=node.snapshot_id,
                        file_path=node.file_path,
                        symbol_name=node.symbol_name,
                        symbol_type=node.symbol_type,
                        meta_data=node.meta_data,
                    )
                )
                
        return ImpactAnalysisResponse(
            impacted_nodes=impacted_nodes,
            blast_radius_score=blast_radius_score
        )
