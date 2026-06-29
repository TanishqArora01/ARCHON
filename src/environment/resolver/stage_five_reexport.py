import re
import pathlib
from src.db.models import SymbolEdge, SymbolNode
from src.environment.parser.schemas import SymbolType

class ReExportResolutionStage:
    def resolve(
        self,
        edges: list[SymbolEdge],
        nodes: list[SymbolNode],
        path_to_nodes: dict[str, list[SymbolNode]],
    ) -> list[SymbolEdge]:
        """
        Refines IMPORTS edges to bypass re-exports.
        Returns the modified list of edges.
        """
        node_by_id = {n.id: n for n in nodes}
        
        # Build adjacency list for fast lookup of outgoing IMPORTS edges
        # from_node_id -> list of to_node_ids
        imports_graph: dict[str, list[str]] = {}
        for e in edges:
            if e.edge_type == "IMPORTS":
                imports_graph.setdefault(e.from_node_id, []).append(e.to_node_id)
        
        changed = True
        while changed:
            changed = False
            new_edges = []
            removed_edges: set[str] = set()
            
            for e in edges:
                if e.id in removed_edges:
                    continue
                    
                if e.edge_type != "IMPORTS":
                    continue
                    
                target = node_by_id.get(e.to_node_id)
                if not target:
                    continue
                
                # Case 1: Target is an IMPORT node (Python __init__.py re-export)
                if target.symbol_type == SymbolType.IMPORT.value:
                    # Find where this IMPORT node points to
                    target_edges = [te for te in edges if te.from_node_id == target.id and te.edge_type == "IMPORTS"]
                    if target_edges:
                        best_target = target_edges[0].to_node_id
                        from_node = node_by_id.get(e.from_node_id)
                        if from_node:
                            from_text = from_node.meta_data.get("literal_text", from_node.symbol_name)
                            for te in target_edges:
                                ultimate_node = node_by_id.get(te.to_node_id)
                                if ultimate_node and ultimate_node.symbol_name in from_text:
                                    best_target = te.to_node_id
                                    break
                                    
                        e.to_node_id = best_target
                        changed = True
                
                # Case 2: Target is an EXPORT node (TypeScript barrel file)
                elif target.symbol_type == SymbolType.EXPORT.value:
                    ext = pathlib.Path(target.file_path).suffix
                    if ext in [".ts", ".js"]:
                        text = target.meta_data.get("literal_text", "")
                        # e.g., export * from './module'
                        match = re.search(r"export\s+.*from\s+['\"](.*?)['\"]", text)
                        if match:
                            source = match.group(1)
                            import posixpath
                            target_file = posixpath.normpath(str(pathlib.Path(target.file_path).parent / source)).replace('\\', '/')
                            if not target_file.endswith(".ts"):
                                target_file += ".ts"
                            
                            target_file_nodes = path_to_nodes.get(target_file, [])
                            added = False
                            for tf_node in target_file_nodes:
                                if tf_node.symbol_type in [SymbolType.CLASS.value, SymbolType.FUNCTION.value, SymbolType.EXPORT.value, SymbolType.INTERFACE.value]:
                                    if not added:
                                        e.to_node_id = tf_node.id
                                        added = True
                                        changed = True
                                    else:
                                        # Clone the edge if multiple targets (consistent with TS parsing)
                                        # But doing it in-place is tricky. Let's just create a new edge
                                        new_e = SymbolEdge(
                                            snapshot_id=e.snapshot_id,
                                            from_node_id=e.from_node_id,
                                            to_node_id=tf_node.id,
                                            edge_type="IMPORTS"
                                        )
                                        new_edges.append(new_e)
                                        imports_graph.setdefault(e.from_node_id, []).append(tf_node.id)
                                        changed = True
                            
                            if added:
                                imports_graph[e.from_node_id] = [
                                    edge.to_node_id
                                    for edge in edges
                                    if edge.from_node_id == e.from_node_id and edge.edge_type == "IMPORTS"
                                ]

            if new_edges:
                edges.extend(new_edges)
        
        return edges
