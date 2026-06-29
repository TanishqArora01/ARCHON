from src.retrieval.schemas import AssembledAgentContext

class ContextAssembler:
    @staticmethod
    def format_context_for_llm(context: AssembledAgentContext) -> str:
        """
        Serializes the structural and semantic context into a dense, markdown-formatted 
        string block optimized for downstream LLM consumption.
        """
        lines = []
        lines.append(f"<!-- TRACKING_TOKEN: {context.tracking_token} -->")
        lines.append(f"# ASSEMBLED CONTEXT BLOCK")
        lines.append(f"**Repository**: {context.repository_name}")
        lines.append(f"**Task/Query**: {context.query_text}\n")
        lines.append("## 1. STRUCTURAL IMPACT ANALYSIS")
        
        struct = context.structural
        lines.append(f"**Blast Radius Score**: {struct.blast_radius_score:.2f}")
        
        lines.append("\n### Impacted Files:")
        if struct.impacted_file_paths:
            for filepath in struct.impacted_file_paths:
                lines.append(f"- {filepath}")
        else:
            lines.append("- None detected.")
            
        lines.append("\n### Impacted Symbol IDs:")
        if struct.impacted_symbol_ids:
            for sym_id in struct.impacted_symbol_ids:
                lines.append(f"- {sym_id}")
        else:
            lines.append("- None detected.")
            
        if struct.choke_points:
            lines.append("\n### Structural Choke Points (Highest Technical Debt):")
            for cp in struct.choke_points:
                lines.append(
                    f"- **{cp['symbol_name']}** (`{cp['file_path']}`) -> "
                    f"TDI: {cp['tdi']:.4f} "
                    f"(Centrality: {cp['centrality_score']:.4f}, "
                    f"Blast Radius: {cp['blast_radius_score']:.2f}, "
                    f"Complexity: {cp['complexity_score']:.2f})"
                )

        if struct.architecture_violations:
            lines.append("\n### Repository Rule Violations:")
            for violation in struct.architecture_violations:
                lines.append(
                    f"- **{violation['rule_type']}**: {violation['message']} "
                    f"({violation['from_node_id']} -> {violation['to_node_id']})"
                )
                
        lines.append("\n## 2. SEMANTIC MEMORY (DOCUMENTATION)")
        
        sem = context.semantic
        if not sem.documentation_chunks:
            lines.append("No relevant documentation found.")
        else:
            for i, (chunk, source, score) in enumerate(
                zip(sem.documentation_chunks, sem.source_files, sem.relevance_scores, strict=False)
            ):
                lines.append(f"\n### Document {i+1} [Relevance: {score:.4f}]")
                lines.append(f"**Source**: {source}")
                lines.append("```markdown")
                lines.append(chunk.strip())
                lines.append("```")
                
        lines.append("\n# END ASSEMBLED CONTEXT BLOCK")
        return "\n".join(lines)
