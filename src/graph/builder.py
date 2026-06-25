import uuid
import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models import SymbolNode, SymbolEdge
from src.observability.telemetry import set_knowledge_graph_nodes

class NetworkXGraphBuilder:
    async def build_snapshot_graph(self, db_session: AsyncSession, snapshot_id: uuid.UUID | str) -> nx.DiGraph:
        """
        Builds a NetworkX directed graph from a snapshot's symbols and edges.
        """
        if isinstance(snapshot_id, uuid.UUID):
            snapshot_id = str(snapshot_id)
            
        graph: nx.DiGraph = nx.DiGraph()
        
        # Query and add all nodes
        stmt_nodes = select(SymbolNode).where(SymbolNode.snapshot_id == snapshot_id)
        result_nodes = await db_session.execute(stmt_nodes)
        nodes = result_nodes.scalars().all()
        
        for node in nodes:
            # Bind properties matching the DB columns and internal JSON structure
            graph.add_node(
                node.id,
                file_path=node.file_path,
                symbol_name=node.symbol_name,
                symbol_type=node.symbol_type,
                **node.meta_data
            )
            
        # Query and add all edges
        stmt_edges = select(SymbolEdge).where(SymbolEdge.snapshot_id == snapshot_id)
        result_edges = await db_session.execute(stmt_edges)
        edges = result_edges.scalars().all()
        
        for edge in edges:
            graph.add_edge(
                edge.from_node_id,
                edge.to_node_id,
                edge_type=edge.edge_type
            )
            
        set_knowledge_graph_nodes(graph.number_of_nodes())
        return graph
