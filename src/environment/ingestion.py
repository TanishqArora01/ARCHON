import asyncio
import uuid
from pathlib import Path
from src.environment.parser.engine import ParserEngine
from src.db.session import AsyncSessionLocal
from src.db.models import Snapshot, AnalysisRun, SymbolNode
from src.environment.parser.schemas import FileAnalysisSnapshot

class RepositoryIngestor:
    def __init__(self):
        self.engine = ParserEngine()

    async def ingest(self, target_dir: Path, repository_id: str | None = None) -> str:
        snapshot_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())

        import logging
        logger = logging.getLogger(__name__)
        # Collect files
        tasks = []
        logger.info(f"Ingesting from target_dir: {target_dir}")
        for filepath in target_dir.rglob("*"):
            if filepath.is_dir():
                continue
            # Ignore hidden directories like .git, .venv within the repo
            try:
                rel_parts = filepath.relative_to(target_dir).parts
            except ValueError:
                rel_parts = filepath.parts
            
            if any(part.startswith(".") for part in rel_parts):
                continue
            
            if filepath.suffix == ".py":
                tasks.append(self.engine.parse_repository_file(filepath, "python"))
            elif filepath.suffix in [".ts", ".js"]:
                tasks.append(self.engine.parse_repository_file(filepath, "typescript"))

        logger.info(f"Collected {len(tasks)} tasks to parse")
        # Parse all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Finished parsing. Results count: {len(results)}")

        async with AsyncSessionLocal() as session:
            snapshot = Snapshot(id=snapshot_id, repository_id=repository_id, repository_path=str(target_dir))
            run = AnalysisRun(id=run_id, snapshot_id=snapshot_id, repository_id=repository_id, status="completed")
            session.add(snapshot)
            session.add(run)

            nodes = []
            for res in results:
                if not isinstance(res, FileAnalysisSnapshot):
                    print(f"Failed to parse file: {res}")
                    continue
                
                # Insert a FILE node to represent the module itself
                file_node_id = f"{snapshot_id}::{res.file_path}::__FILE__"
                nodes.append(SymbolNode(
                    id=file_node_id,
                    snapshot_id=snapshot_id,
                    file_path=res.file_path,
                    symbol_name="__FILE__",
                    symbol_type="FILE",
                    meta_data={}
                ))

                # Recursive function to flatten the hierarchy into individual rows
                def extract(tokens, path):
                    for t in tokens:
                        sym_id = f"{snapshot_id}::{path}::{t.name}::{t.byte_range[0]}"
                        nodes.append(SymbolNode(
                            id=sym_id,
                            snapshot_id=snapshot_id,
                            file_path=path,
                            symbol_name=t.name,
                            symbol_type=t.symbol_type.value,
                            meta_data={
                                "line_range": t.line_range,
                                "byte_range": t.byte_range,
                                "literal_text": t.literal_text,
                            }
                        ))
                        extract(t.children, path)
                
                extract(res.tokens, res.file_path)

            session.add_all(nodes)
            await session.commit()

        return snapshot_id
